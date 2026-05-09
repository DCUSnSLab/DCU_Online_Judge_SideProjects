"""Run lecture-code-review (if needed) + llm-code-review as subprocesses.

Job state is in-memory: this Phase 1 deliberately avoids Redis/Celery.
A Job has:
  - status:   queued | running | done | failed
  - n_total / n_done / n_failed
  - an asyncio.Queue per SSE subscriber (thread-safe via call_soon_threadsafe)
  - requester_ids:  free-form identifiers (browser uuid). Multiple users that
    asked for the same contest are coalesced into a single Job.

Concurrency:
  A process-wide GpuScheduler caps simultaneously *running* jobs to
  Settings.max_concurrent_eval_jobs (default 3). Excess jobs sit in
  status=queued and broadcast their queue position to subscribers via
  `queued` / `queue-update` events.
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
    enqueued_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    error: str | None = None
    requester_ids: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()
_main_loop: asyncio.AbstractEventLoop | None = None
_active_by_contest: dict[int, str] = {}      # contest_id → job_id (queued OR running)


# ---------- Event fan-out ----------

def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def _emit(job: Job, event_type: str, payload: dict) -> None:
    ev = {"event": event_type, "data": payload}
    job.history.append(ev)
    if len(job.history) > 500:
        del job.history[: len(job.history) - 500]
    if _main_loop is None:
        return
    for q in list(job.subscribers):
        try:
            _main_loop.call_soon_threadsafe(q.put_nowait, ev)
        except RuntimeError:
            pass


# ---------- GPU concurrency scheduler ----------

class GpuScheduler:
    """Process-wide FIFO queue + bounded slots.

    Producer threads call enqueue/wait_for_slot/release. Subscribers see
    `queued` (on enqueue) and `queue-update` events (on every slot transition).
    """

    def __init__(self, slots: int):
        self._slots_total = slots
        self._sem = threading.BoundedSemaphore(slots)
        self._lock = threading.Lock()
        self._pending: list[Job] = []
        self._running: set[str] = set()    # job_ids currently holding a slot

    @property
    def slots_total(self) -> int:
        return self._slots_total

    def slots_in_use(self) -> int:
        with self._lock:
            return len(self._running)

    def queue_size(self) -> int:
        with self._lock:
            return len(self._pending)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "slots_total": self._slots_total,
                "slots_in_use": len(self._running),
                "running_job_ids": list(self._running),
                "pending_job_ids": [j.id for j in self._pending],
            }

    def position_of(self, job: Job) -> int | None:
        """1-based queue position; None if not pending."""
        with self._lock:
            try:
                return self._pending.index(job) + 1
            except ValueError:
                return None

    def enqueue(self, job: Job) -> int:
        with self._lock:
            self._pending.append(job)
            return len(self._pending)

    def wait_for_slot(self, job: Job) -> None:
        # Blocks until acquire (FIFO is ensured by acquisition order — sem doesn't
        # guarantee FIFO across threads, but the rough order is preserved because
        # all jobs spend most of their time blocking here).
        self._sem.acquire()
        with self._lock:
            try:
                self._pending.remove(job)
            except ValueError:
                pass
            self._running.add(job.id)
        self._broadcast_positions()

    def release(self, job: Job) -> None:
        with self._lock:
            self._running.discard(job.id)
        self._sem.release()
        self._broadcast_positions()

    def _broadcast_positions(self) -> None:
        with self._lock:
            snapshot_pending = list(self._pending)
            in_use = len(self._running)
        for i, j in enumerate(snapshot_pending, 1):
            _emit(
                j,
                "queue-update",
                {
                    "queue_position": i,
                    "queue_size": len(snapshot_pending),
                    "slots_in_use": in_use,
                    "slots_total": self._slots_total,
                },
            )


_scheduler: GpuScheduler | None = None


def get_scheduler() -> GpuScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = GpuScheduler(get_settings().max_concurrent_eval_jobs)
    return _scheduler


# ---------- Subprocess invocations ----------

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
    cmd = [str(venv_python), "-u", "-m", "llm_code_review", "--input", str(input_dir)]
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
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
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
        elif "ERROR" in line and "evaluate" in line:
            job.n_failed += 1
            _emit(job, "warn", {"message": line[:500]})
        else:
            if "INFO" in line or "WARN" in line or "ERROR" in line:
                _emit(job, "log", {"line": line[:500]})
    rc = proc.wait()
    return rc


# ---------- Job lifecycle ----------

def _run_job(job: Job) -> None:
    sched = get_scheduler()
    job.enqueued_at = datetime.now(timezone.utc).isoformat()
    pos = sched.enqueue(job)

    job.status = "queued"
    _emit(
        job,
        "queued",
        {
            "queue_position": pos,
            "queue_size": sched.queue_size(),
            "slots_in_use": sched.slots_in_use(),
            "slots_total": sched.slots_total,
        },
    )

    try:
        sched.wait_for_slot(job)

        job.status = "running"
        job.started_at = datetime.now(timezone.utc).isoformat()
        _emit(
            job,
            "started",
            {
                "lecture_id": job.lecture_id,
                "contest_id": job.contest_id,
                "n_total": job.n_total,
                "slots_in_use": sched.slots_in_use(),
                "slots_total": sched.slots_total,
            },
        )

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

        # Step 3: figure out missing pairs.
        all_pairs = _read_final_submissions_csv(job.lecture_id, job.contest_id)
        missing = all_pairs if job.force else _missing_pairs(job.lecture_id, job.contest_id, all_pairs)

        job.n_total = len(missing)
        _emit(job, "stage", {"name": "qualitative+ai_usage", "n_to_run": job.n_total})

        if job.n_total == 0:
            job.status = "done"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            _emit(job, "done", {"n_evaluated": 0, "n_failed": 0, "skipped": True})
            return

        # Step 4: group missing by problem and run llm-code-review per problem.
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
        # Slot release (only if we ever acquired). pending list cleanup happens
        # inside wait_for_slot; if we errored before acquire, _pending may still
        # contain the job — drop it explicitly.
        with sched._lock:
            try:
                sched._pending.remove(job)
            except ValueError:
                pass
            had_slot = job.id in sched._running
        if had_slot:
            sched.release(job)
        else:
            sched._broadcast_positions()
        with _jobs_lock:
            _active_by_contest.pop(job.contest_id, None)


def start_job(
    lecture_id: int,
    contest_id: int,
    *,
    force: bool,
    requester_id: str | None = None,
) -> tuple[Job, bool]:
    """Returns (job, joined_existing).

    If a non-force job for this contest is already queued/running, the requester
    is added to that job's subscriber list (no GPU work duplicated). force=True
    always creates a new job.
    """
    with _jobs_lock:
        existing_id = _active_by_contest.get(contest_id)
        if existing_id and not force:
            existing = _jobs.get(existing_id)
            if existing and existing.status in ("queued", "running"):
                if requester_id and requester_id not in existing.requester_ids:
                    existing.requester_ids.append(requester_id)
                _emit(existing, "log", {"line": f"requester joined: {requester_id or 'anon'}"})
                return existing, True

        all_pairs = _read_final_submissions_csv(lecture_id, contest_id)
        n_total = len(all_pairs) if force else len(_missing_pairs(lecture_id, contest_id, all_pairs))

        job = Job(
            id=str(uuid.uuid4()),
            lecture_id=lecture_id,
            contest_id=contest_id,
            force=force,
            n_total=n_total,
            requester_ids=[requester_id] if requester_id else [],
        )
        _jobs[job.id] = job
        _active_by_contest[contest_id] = job.id

    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return job, False


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def get_active_for_contest(contest_id: int) -> Job | None:
    with _jobs_lock:
        jid = _active_by_contest.get(contest_id)
        return _jobs.get(jid) if jid else None


def queue_snapshot() -> dict:
    sched = get_scheduler()
    snap = sched.snapshot()
    running = []
    for jid in snap["running_job_ids"]:
        j = _jobs.get(jid)
        if not j:
            continue
        running.append({
            "job_id": j.id,
            "lecture_id": j.lecture_id,
            "contest_id": j.contest_id,
            "requester_ids": list(j.requester_ids),
            "n_done": j.n_done,
            "n_total": j.n_total,
            "started_at": j.started_at,
        })
    pending = []
    for i, jid in enumerate(snap["pending_job_ids"], 1):
        j = _jobs.get(jid)
        if not j:
            continue
        pending.append({
            "job_id": j.id,
            "lecture_id": j.lecture_id,
            "contest_id": j.contest_id,
            "requester_ids": list(j.requester_ids),
            "queue_position": i,
            "enqueued_at": j.enqueued_at,
        })
    return {
        "slots_total": snap["slots_total"],
        "slots_in_use": snap["slots_in_use"],
        "queue_size": len(pending),
        "running": running,
        "pending": pending,
    }


# ---------- SSE async iteration ----------

async def event_iter(job: Job, ping_interval: float = 10.0) -> AsyncIterator[dict]:
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
