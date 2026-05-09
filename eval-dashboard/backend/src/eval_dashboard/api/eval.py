from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from eval_dashboard import eval_runner, eval_store, queries as q
from eval_dashboard.db import conn
from eval_dashboard.models import EvalJobStarted, EvalStartRequest, EvalStatus

router = APIRouter()


@router.get("/contests/{contest_id}/eval-status")
def eval_status(contest_id: int) -> EvalStatus:
    with conn() as c:
        contest = q.get_contest(c, contest_id)
        if not contest:
            raise HTTPException(404, "contest not found")
        lecture_id = contest["lecture_id"]

    has_export = eval_store.has_lecture_cr_export(lecture_id, contest_id)
    pairs = eval_store.list_evaluated_pairs(lecture_id, contest_id)
    last_run_at: datetime | None = None
    run_info_path = eval_store.run_dir(lecture_id, contest_id) / "_meta" / "run_info.json"
    if run_info_path.is_file():
        try:
            data = json.loads(run_info_path.read_text(encoding="utf-8"))
            t = data.get("finished_at") or data.get("started_at")
            if t:
                last_run_at = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    active = eval_runner.get_active_for_contest(contest_id)
    return EvalStatus(
        has_lecture_export=has_export,
        n_evaluated=len(pairs),
        n_pairs=0,  # filled by frontend from scoreboard if needed; cheap to keep 0 here
        last_run_at=last_run_at,
        running_job_id=active.id if active and active.status == "running" else None,
    )


@router.post("/contests/{contest_id}/qualitative-eval")
def start_eval(contest_id: int, body: EvalStartRequest | None = None) -> EvalJobStarted:
    body = body or EvalStartRequest()
    with conn() as c:
        contest = q.get_contest(c, contest_id)
        if not contest:
            raise HTTPException(404, "contest not found")
        lecture_id = contest["lecture_id"]

    active = eval_runner.get_active_for_contest(contest_id)
    if active and active.status in ("queued", "running"):
        raise HTTPException(409, f"job already running: {active.id}")

    job = eval_runner.start_job(lecture_id, contest_id, force=body.force)
    return EvalJobStarted(
        job_id=job.id,
        n_total=job.n_total,
        n_already_evaluated=0,    # client reads from /eval-status separately if needed
        n_to_run=job.n_total,
    )


@router.get("/jobs/{job_id}/stream")
async def stream(job_id: str):
    job = eval_runner.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    async def event_generator():
        async for ev in eval_runner.event_iter(job):
            yield {"event": ev["event"], "data": json.dumps(ev["data"])}

    return EventSourceResponse(event_generator())


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = eval_runner.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "id": job.id,
        "lecture_id": job.lecture_id,
        "contest_id": job.contest_id,
        "force": job.force,
        "status": job.status,
        "n_total": job.n_total,
        "n_done": job.n_done,
        "n_failed": job.n_failed,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error,
    }
