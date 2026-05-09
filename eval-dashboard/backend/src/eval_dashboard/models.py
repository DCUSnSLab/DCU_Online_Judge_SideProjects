from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Lecture(BaseModel):
    id: int
    title: str
    year: int
    semester: int


class Contest(BaseModel):
    id: int
    title: str
    lecture_id: int | None = None
    lecture_contest_type: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None


class Problem(BaseModel):
    id: int
    label: str
    title: str
    total_score: int
    difficulty: str = ""


class Student(BaseModel):
    user_id: int
    username: str
    realname: str | None = None
    schoolssn: int | None = None
    enrolled: bool = False


class TestcaseCell(BaseModel):
    submission_id: str | None = None
    result: int | None = None
    result_label: str | None = None
    score: int | None = None
    time_cost_ms: int | None = None
    memory_cost_kb: int | None = None
    language: str | None = None


class QualitativeShort(BaseModel):
    overall: int | None = None
    suggested_partial_score: int | None = None
    ai_likelihood_score: int | None = None
    ai_confidence: str | None = None
    has_error: bool = False


class ScoreboardCell(BaseModel):
    testcase: TestcaseCell | None = None
    qualitative: QualitativeShort | None = None


class ScoreboardRow(BaseModel):
    user_id: int
    username: str
    realname: str | None = None
    by_problem: dict[str, ScoreboardCell] = {}


class ScoreboardResponse(BaseModel):
    contest: Contest
    lecture: Lecture
    problems: list[Problem]
    students: list[ScoreboardRow]
    n_evaluated_pairs: int
    n_total_pairs: int


class EvalStartRequest(BaseModel):
    force: bool = False


class EvalJobStarted(BaseModel):
    job_id: str
    n_total: int
    n_already_evaluated: int
    n_to_run: int
    joined_existing: bool = False
    queue_position: int | None = None     # 1-based; None if running already
    slots_in_use: int = 0
    slots_total: int = 0


class EvalStatus(BaseModel):
    has_lecture_export: bool
    n_evaluated: int
    n_pairs: int
    last_run_at: datetime | None = None
    running_job_id: str | None = None


class QueueRunningItem(BaseModel):
    job_id: str
    lecture_id: int
    contest_id: int
    requester_ids: list[str] = []
    n_done: int = 0
    n_total: int = 0
    started_at: str | None = None


class QueuePendingItem(BaseModel):
    job_id: str
    lecture_id: int
    contest_id: int
    requester_ids: list[str] = []
    queue_position: int
    enqueued_at: str | None = None


class QueueSnapshot(BaseModel):
    slots_total: int
    slots_in_use: int
    queue_size: int
    running: list[QueueRunningItem] = []
    pending: list[QueuePendingItem] = []
