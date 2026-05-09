from __future__ import annotations

from fastapi import APIRouter, HTTPException

from eval_dashboard import queries as q
from eval_dashboard.db import conn
from eval_dashboard.models import Contest, Lecture

router = APIRouter()


@router.get("/years")
def years() -> list[int]:
    with conn() as c:
        return q.list_years(c)


@router.get("/years/{year}/semesters")
def semesters(year: int) -> list[int]:
    with conn() as c:
        return q.list_semesters(c, year)


@router.get("/years/{year}/semesters/{semester}/lectures")
def lectures(year: int, semester: int) -> list[Lecture]:
    with conn() as c:
        rows = q.list_lectures(c, year, semester)
    return [Lecture(**r) for r in rows]


@router.get("/lectures/{lecture_id}/contests")
def contests(lecture_id: int) -> list[Contest]:
    with conn() as c:
        if not q.get_lecture(c, lecture_id):
            raise HTTPException(404, "lecture not found")
        rows = q.list_contests(c, lecture_id)
    return [Contest(**r) for r in rows]


@router.get("/lectures/{lecture_id}")
def get_lecture(lecture_id: int) -> Lecture:
    with conn() as c:
        row = q.get_lecture(c, lecture_id)
    if not row:
        raise HTTPException(404, "lecture not found")
    return Lecture(**row)
