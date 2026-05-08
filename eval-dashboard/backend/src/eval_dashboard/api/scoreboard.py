from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException

from eval_dashboard import eval_store, queries as q
from eval_dashboard.db import conn
from eval_dashboard.models import (
    Contest,
    Lecture,
    Problem,
    QualitativeShort,
    ScoreboardCell,
    ScoreboardResponse,
    ScoreboardRow,
    Student,
    TestcaseCell,
)

router = APIRouter()


# Mirrors llm-code-review/src/llm_code_review/lang.py RESULT_LABELS — keep in sync if
# JudgeStatus changes upstream. We don't import that module to keep projects isolated.
_RESULT_LABELS = {
    -2: "CE",
    -1: "WA",
    0: "AC",
    1: "TLE",
    2: "RTLE",
    3: "MLE",
    4: "RE",
    5: "SE",
    6: "PENDING",
    7: "JUDGING",
    8: "PA",
}


def _result_label(code: int | None) -> str | None:
    if code is None:
        return None
    return _RESULT_LABELS.get(code, f"R{code}")


def _build_scoreboard(c, lecture_id: int, contest_id: int) -> ScoreboardResponse:
    lecture_row = q.get_lecture(c, lecture_id)
    if not lecture_row:
        raise HTTPException(404, "lecture not found")
    contest_row = q.get_contest(c, contest_id)
    if not contest_row or contest_row.get("lecture_id") not in (None, lecture_id):
        raise HTTPException(404, "contest not found or not in lecture")

    problems = q.list_problems(c, contest_id)
    if not problems:
        raise HTTPException(404, "no problems in contest")

    roster = q.list_students(c, lecture_id)
    submissions = q.list_final_submissions(c, lecture_id, contest_id)

    # Pre-build user lookup, augment roster with users that submitted but aren't in signup_class.
    by_uid: dict[int, dict] = {r["user_id"]: r for r in roster}
    for s in submissions:
        if s["user_id"] not in by_uid:
            by_uid[s["user_id"]] = {
                "user_id": s["user_id"],
                "username": s["username"],
                "realname": None,
                "schoolssn": None,
                "enrolled": False,
            }

    # Group submissions by user_id.
    subs_by_user: dict[int, list[dict]] = defaultdict(list)
    for s in submissions:
        subs_by_user[s["user_id"]].append(s)

    evaluated_pairs = eval_store.list_evaluated_pairs(lecture_id, contest_id)

    rows: list[ScoreboardRow] = []
    for uid in sorted(by_uid.keys(), key=lambda i: (by_uid[i].get("username") or "")):
        user = by_uid[uid]
        cells: dict[str, ScoreboardCell] = {}
        # Initialize all problems with empty cells (so the matrix is rectangular).
        for p in problems:
            cells[p["label"]] = ScoreboardCell()
        for s in subs_by_user.get(uid, []):
            stat = s.get("statistic_info") or {}
            cells[s["problem_label"]] = ScoreboardCell(
                testcase=TestcaseCell(
                    submission_id=s["id"],
                    result=s["result"],
                    result_label=_result_label(s["result"]),
                    score=stat.get("score"),
                    time_cost_ms=stat.get("time_cost"),
                    memory_cost_kb=stat.get("memory_cost"),
                    language=s.get("language"),
                ),
            )
        # Attach qualitative info from disk.
        for p in problems:
            if (user["username"], p["label"]) in evaluated_pairs:
                doc = eval_store.load_evaluation(lecture_id, contest_id, user["username"], p["label"])
                short = eval_store.short_eval_for_scoreboard(doc)
                if short:
                    cells[p["label"]].qualitative = QualitativeShort(**short)
        rows.append(
            ScoreboardRow(
                user_id=uid,
                username=user["username"],
                realname=user.get("realname"),
                by_problem=cells,
            )
        )

    n_total_pairs = len(rows) * len(problems)
    return ScoreboardResponse(
        contest=Contest(**contest_row),
        lecture=Lecture(**lecture_row),
        problems=[Problem(**p) for p in problems],
        students=rows,
        n_evaluated_pairs=len(evaluated_pairs),
        n_total_pairs=n_total_pairs,
    )


@router.get("/contests/{contest_id}/scoreboard")
def scoreboard(contest_id: int) -> ScoreboardResponse:
    with conn() as c:
        contest = q.get_contest(c, contest_id)
        if not contest:
            raise HTTPException(404, "contest not found")
        lecture_id = contest.get("lecture_id")
        if lecture_id is None:
            raise HTTPException(400, "contest has no lecture_id")
        return _build_scoreboard(c, lecture_id, contest_id)


@router.get("/contests/{contest_id}/students/{user_id}/problems/{problem_id}")
def cell_detail(contest_id: int, user_id: int, problem_id: int) -> dict[str, Any]:
    """Detail for a single (user, problem) cell — code + testcase + qualitative + ai-usage."""
    with conn() as c:
        contest = q.get_contest(c, contest_id)
        if not contest:
            raise HTTPException(404, "contest not found")
        lecture_id = contest["lecture_id"]
        problem = q.get_problem(c, problem_id)
        if not problem or problem["contest_id"] != contest_id:
            raise HTTPException(404, "problem not in contest")

        # Find latest submission for (user, problem) within this contest.
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT id, code, language, result, statistic_info, create_time, username
                FROM submission
                WHERE lecture_id = %s AND contest_id = %s AND user_id = %s AND problem_id = %s
                  AND result NOT IN (6, 7)
                ORDER BY create_time DESC, id DESC
                LIMIT 1
                """,
                (lecture_id, contest_id, user_id, problem_id),
            )
            sub = cur.fetchone()

    qualitative_doc = None
    if sub:
        qualitative_doc = eval_store.load_evaluation(
            lecture_id, contest_id, sub["username"], problem["label"]
        )

    return {
        "lecture_id": lecture_id,
        "contest_id": contest_id,
        "problem": {
            "id": problem["id"],
            "label": problem["label"],
            "title": problem["title"],
            "description": problem["description"],
            "input_description": problem["input_description"],
            "output_description": problem["output_description"],
            "samples": problem["samples"],
            "total_score": problem["total_score"],
            "difficulty": problem["difficulty"],
            "time_limit": problem["time_limit"],
            "memory_limit": problem["memory_limit"],
        },
        "submission": (
            {
                "id": sub["id"],
                "code": sub["code"],
                "language": sub["language"],
                "result": sub["result"],
                "result_label": _result_label(sub["result"]),
                "statistic_info": sub["statistic_info"],
                "create_time": sub["create_time"].isoformat() if sub.get("create_time") else None,
            }
            if sub
            else None
        ),
        "qualitative": (qualitative_doc.get("evaluation") if qualitative_doc else None),
        "ai_usage_assessment": (
            qualitative_doc.get("ai_usage_assessment") if qualitative_doc else None
        ),
    }
