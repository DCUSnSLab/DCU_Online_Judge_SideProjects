from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from sse_starlette.sse import EventSourceResponse

from eval_dashboard import eval_runner, eval_store, queries as q
from eval_dashboard.db import conn
from eval_dashboard.models import (
    EvalJobStarted,
    EvalStartRequest,
    EvalStatus,
    QueueSnapshot,
)

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
        n_pairs=0,
        last_run_at=last_run_at,
        running_job_id=active.id if active and active.status in ("queued", "running") else None,
    )


@router.post("/contests/{contest_id}/qualitative-eval")
def start_eval(
    contest_id: int,
    body: EvalStartRequest | None = None,
    x_requester: Annotated[str | None, Header(alias="X-Requester")] = None,
) -> EvalJobStarted:
    body = body or EvalStartRequest()
    with conn() as c:
        contest = q.get_contest(c, contest_id)
        if not contest:
            raise HTTPException(404, "contest not found")
        lecture_id = contest["lecture_id"]

    job, joined = eval_runner.start_job(
        lecture_id, contest_id, force=body.force, requester_id=x_requester
    )
    sched = eval_runner.get_scheduler()
    pos = sched.position_of(job)
    return EvalJobStarted(
        job_id=job.id,
        n_total=job.n_total,
        n_already_evaluated=0,
        n_to_run=job.n_total,
        joined_existing=joined,
        queue_position=pos,
        slots_in_use=sched.slots_in_use(),
        slots_total=sched.slots_total,
    )


@router.get("/queue")
def queue_snapshot() -> QueueSnapshot:
    return QueueSnapshot(**eval_runner.queue_snapshot())


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
    sched = eval_runner.get_scheduler()
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
        "enqueued_at": job.enqueued_at,
        "error": job.error,
        "requester_ids": list(job.requester_ids),
        "queue_position": sched.position_of(job),
    }
