"""Run lecture-code-review (if needed) + llm-code-review as subprocesses.

Job state is in-memory: this Phase 1 deliberately avoids Redis/Celery.
A Job has:
  - status:   queued | running | done | failed
  - n_total / n_done / n_failed
  - an asyncio.Queue[Event] for SSE streaming (thread-safe via call_soon_threadsafe)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
import shutil
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator

from eval_dashboard import eval_store
from eval_dashboard.config import get_settings

log = logging.getLogger(__name__)


_PROGRESS_RE = re.compile(
    r"\[(\d+)/(\d+)\]\s+(\S+?)/(\S+?)\s+overall=(\S+)\s+sps=(\S+)"
    r"(?:\s+ev_lat=(\d+)ms)?"
    r"(?:\s+ai_usage=(\S+))?"
)


@dataclass
class Job:
    id: str
    lecture_id: int
    contest_id: int
    force: bool
    n_total: int
    n_done: int = 0
    n_failed: int = 0
    status: str = "queued"   # queued | running | done | failed
    started_at: str = ""
    finished_at: str = ""
    error: str | None = None
    # Buffer of historical events so a late SSE subscriber sees what already happened.
    history: list[dict] = field(default_factory=list)
    # Per-subscriber asyncio queues. The producer thread fans events out via
    # loop.call_soon_threadsafe(queue.put_nowait, ...). All entries are pruned
    # when the job ends.
    subscribers: list[asyncio.Queue] = field(default_factory=list)


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()
_main_loop: asyncio.AbstractEventLoop | None = None
# Track currently running job per contest, to enforce single-flight.
_active_by_contest: dict[int, str] = {}


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called from FastAPI lifespan startup so the producer thread can schedule
    asyncio.Queue.put_nowait on the right loop."""
    global _main_loop
    _main_loop = loop


def _emit(job: Job, event_type: str, payload: dict) -> None:
    ev = {"event": event_type, "data": payload}
    # 1) keep the last N events for late subscribers (cap to avoid unbounded growth).
    job.history.append(ev)
    if len(job.history) > 500:
        del job.history[: len(job.history) - 500]
    # 2) fan out to subscribers via main loop.
    if _main_loop is None:
        return
    for q in list(job.subscribers):
        try:
            _main_loop.call_soon_threadsafe(q.put_nowait, ev)
        except RuntimeError:
            # loop might be closing
            pass


def _shell_lecture_cr(lecture_id: int, contest_id: int) -> tuple[int, str]:
    cfg = get_settings()
    venv_python = cfg.lecture_cr_dir / ".venv" / "bin" / "python3"
    if not venv_python.is_file():
        return 1, f"missing venv python: {venv_python}"
    cmd = [str(venv_python), "-m", "lecture_code_review", "-L", str(lecture_id), "-C", str(contest_id)]
    log.info("running: %s (cwd=%s)", " ".join(shlex.quote(p) for p in cmd), cfg.lecture_cr_dir)
    proc = subprocess.run(
        cmd,
        cwd=str(cfg.lecture_cr_dir),
        capture_output=True,
        text=True,
        timeout=600,
        env={**os.environ},
    )
    return proc.returncode, (proc.stdout + "\n" + proc.stderr)[-2000:]


def _archive_existing(lecture_id: int, contest_id: int) -> None:
    base = eval_store.run_dir(lecture_id, contest_id)
    if not base.is_dir():
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    archive_root = base.parent.parent / "out_archive" / f"{base.name}_{ts}"
    archive_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(base), str(archive_root))
    log.info("archived previous run to %s", archive_root)


def _missing_pairs(
    lecture_id: int, contest_id: int, all_pairs: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    have = eval_store.list_evaluated_pairs(lecture_id, contest_id)
    return [pair for pair in all_pairs if pair not in have]


def _read_final_submissions_csv(
    lecture_id: int, contest_id: int
) -> list[tuple[str, str]]:
    """Read lecture-code-review's final_submissions.csv → [(username, problem_label), ...]"""
    import csv

    path = (
        eval_store.lecture_cr_run_dir(lecture_id, contest_id)
        / "_meta"
        / "final_submissions.csv"
    )
    if not path.is_file():
        return []
    out: list[tuple[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out.append((row["username"], row["problem_label"]))
    return out


def _run_llm_cr(job: Job, problem: str | None, usernames: list[str] | None) -> int:
    cfg = get_settings()
    venv_python = cfg.llm_cr_dir / ".venv" / "bin" / "python3"
    if not venv_python.is_file():
        return 1
    input_dir = eval_store.lecture_cr_run_dir(job.lecture_id, job.contest_id)
    # `-u` forces unbuffered stdout/stderr so we can read progress lines in real time.
    cmd = [
        str(venv_python),
        "-u",
        "-m",
        "llm_code_review",
        "--input",
        str(input_dir),
    ]
    if problem:
        cmd.extend(["--problem", problem])
    for u in usernames or []:
        cmd.extend(["--username", u])

    log.info("subprocess: %s", " ".join(shlex.quote(p) for p in cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=str(cfg.llm_cr_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,                # parent-side line buffering on read
        env={
            **os.environ,
            # Belt-and-suspenders alongside `-u`: any nested Python process inherits
            # this and stays unbuffered, so logging.StreamHandler flushes per record.
            "PYTHONUNBUFFERED": "1",
        },
    )
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        line = raw_line.rstrip()
        if not line:
            continue
        m = _PROGRESS_RE.search(line)
        if m:
            username, plabel, overall, sps = m.group(3), m.group(4), m.group(5), m.group(6)
            ev_lat = m.group(7)
            ai_str = m.group(8)
            job.n_done += 1
            _emit(
                job,
                "progress",
                {
                    "n": job.n_done,
                    "total": job.n_total,
                    "current_user": username,
                    "current_problem": plabel,
                    "ev_overall": overall,
                    "ev_sps": sps,
                    "ev_latency_ms": int(ev_lat) if ev_lat else None,
                    "ai_usage": ai_str,
                    "log_line": line[:500],
                },
            )
            log.debug("progress %d/%d %s/%s", job.n_done, job.n_total, username, plabel)
        elif "ERROR" in line and "evaluate" in line:
            job.n_failed += 1
            _emit(job, "warn", {"message": line[:500]})
        else:
            # Forward any other interesting line as a low-noise log message
            # (visible in the GUI's collapsible log tail).
            if "INFO" in line or "WARN" in line or "ERROR" in line:
                _emit(job, "log", {"line": line[:500]})
    rc = proc.wait()
    return rc


def _run_job(job: Job) -> None:
    job.status = "running"
    job.started_at = datetime.now(timezone.utc).isoformat()
    _emit(job, "started", {"lecture_id": job.lecture_id, "contest_id": job.contest_id, "n_total": job.n_total})

    try:
        # Step 1: ensure lecture-code-review export exists (or refresh on force).
        if job.force or not eval_store.has_lecture_cr_export(job.lecture_id, job.contest_id):
            _emit(job, "stage", {"name": "lecture-code-review export"})
            rc, tail = _shell_lecture_cr(job.lecture_id, job.contest_id)
            if rc != 0:
                raise RuntimeError(f"lecture-code-review export failed (rc={rc}): {tail}")

        # Step 2: archive existing llm-code-review out/ on force.
        if job.force:
            _emit(job, "stage", {"name": "archiving previous evaluations"})
            _archive_existing(job.lecture_id, job.contest_id)

        # Step 3: figure out which pairs need evaluation, group by problem for CLI calls.
        all_pairs = _read_final_submissions_csv(job.lecture_id, job.contest_id)
        missing = all_pairs if job.force else _missing_pairs(job.lecture_id, job.contest_id, all_pairs)

        # Refresh n_total now that we know the precise scope.
        job.n_total = len(missing)
        _emit(job, "stage", {"name": "qualitative+ai_usage", "n_to_run": job.n_total})

        if job.n_total == 0:
            job.status = "done"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            _emit(job, "done", {"n_evaluated": 0, "n_failed": 0, "skipped": True})
            return

        # Step 4: group missing by problem (llm-code-review accepts --problem + multiple --username).
        by_problem: dict[str, list[str]] = {}
        for username, plabel in missing:
            by_problem.setdefault(plabel, []).append(username)

        for plabel, users in by_problem.items():
            _emit(job, "stage", {"name": f"problem {plabel}", "n_users": len(users)})
            rc = _run_llm_cr(job, problem=plabel, usernames=users)
            if rc != 0:
                _emit(job, "warn", {"message": f"llm-code-review for {plabel} returned rc={rc}"})

        job.status = "done"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        _emit(job, "done", {"n_evaluated": job.n_done, "n_failed": job.n_failed, "skipped": False})
    except Exception as e:  # noqa: BLE001
        job.status = "failed"
        job.error = f"{type(e).__name__}: {e}"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        _emit(job, "error", {"message": job.error})
        log.exception("job failed")
    finally:
        with _jobs_lock:
            _active_by_contest.pop(job.contest_id, None)


def start_job(lecture_id: int, contest_id: int, *, force: bool) -> Job:
    with _jobs_lock:
        if contest_id in _active_by_contest:
            existing = _jobs[_active_by_contest[contest_id]]
            return existing  # caller checks status

        # Compute n_total upfront if export exists, otherwise leave 0 and refresh after stage 1.
        all_pairs = _read_final_submissions_csv(lecture_id, contest_id)
        if force:
            n_total = len(all_pairs)
        else:
            n_total = len(_missing_pairs(lecture_id, contest_id, all_pairs))

        job = Job(
            id=str(uuid.uuid4()),
            lecture_id=lecture_id,
            contest_id=contest_id,
            force=force,
            n_total=n_total,
        )
        _jobs[job.id] = job
        _active_by_contest[contest_id] = job.id

    t = threading.Thread(target=_run_job, args=(job,), daemon=True)
    t.start()
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def get_active_for_contest(contest_id: int) -> Job | None:
    with _jobs_lock:
        jid = _active_by_contest.get(contest_id)
        return _jobs.get(jid) if jid else None


async def event_iter(job: Job, ping_interval: float = 10.0) -> AsyncIterator[dict]:
    """Async generator: yield events for one SSE subscriber.

    Each subscriber has its own asyncio.Queue, fed by the producer thread via
    loop.call_soon_threadsafe. The history buffer is replayed on connect so
    clients that subscribe mid-flight see prior events too.
    Terminates after a 'done' or 'error' event.
    """
    # Replay history so a late subscriber sees prior events.
    for ev in list(job.history):
        yield ev
        if ev["event"] in ("done", "error"):
            return

    q: asyncio.Queue = asyncio.Queue()
    job.subscribers.append(q)
    try:
        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=ping_interval)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": {"ts": "keepalive"}}
                continue
            yield ev
            if ev["event"] in ("done", "error"):
                break
    finally:
        try:
            job.subscribers.remove(q)
        except ValueError:
            pass
