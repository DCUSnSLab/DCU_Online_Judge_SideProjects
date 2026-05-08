from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from llm_code_review.models import EvalTask, FinalSubmissionRow, ProblemMeta


def _coerce_int(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


def load_problem(input_dir: Path, label: str) -> ProblemMeta:
    path = input_dir / "_meta" / "problems" / f"{label}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProblemMeta(
        label=data["label"],
        title=data["title"],
        description=data.get("description", "") or "",
        input_description=data.get("input_description", "") or "",
        output_description=data.get("output_description", "") or "",
        samples=list(data.get("samples") or []),
        hint=data.get("hint") or None,
        languages=list(data.get("languages") or []),
        time_limit=int(data.get("time_limit", 0)),
        memory_limit=int(data.get("memory_limit", 0)),
        difficulty=str(data.get("difficulty", "")),
        total_score=int(data.get("total_score", 0)),
    )


def load_final_submissions(input_dir: Path) -> list[FinalSubmissionRow]:
    csv_path = input_dir / "_meta" / "final_submissions.csv"
    out: list[FinalSubmissionRow] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out.append(
                FinalSubmissionRow(
                    submission_id=row["id"],
                    user_id=int(row["user_id"]),
                    username=row["username"],
                    problem_label=row["problem_label"],
                    problem_id=int(row["problem_id"]),
                    language=row["language"],
                    result=int(row["result"]),
                    result_label=row["result_label"],
                    score=_coerce_int(row.get("score")),
                    time_cost_ms=_coerce_int(row.get("time_cost_ms")),
                    memory_cost_kb=_coerce_int(row.get("memory_cost_kb")),
                    create_time=row.get("create_time") or None,
                    final_code_path=row["final_code_path"],
                )
            )
    return out


def filter_submissions(
    rows: Iterable[FinalSubmissionRow],
    *,
    problem: str | None = None,
    usernames: set[str] | None = None,
) -> list[FinalSubmissionRow]:
    out = []
    for r in rows:
        if problem and r.problem_label != problem:
            continue
        if usernames and r.username not in usernames:
            continue
        out.append(r)
    return out


def build_tasks(
    input_dir: Path,
    rows: Iterable[FinalSubmissionRow],
) -> Iterable[EvalTask]:
    problem_cache: dict[str, ProblemMeta] = {}
    for r in rows:
        if r.problem_label not in problem_cache:
            problem_cache[r.problem_label] = load_problem(input_dir, r.problem_label)
        code = (input_dir / r.final_code_path).read_text(encoding="utf-8", errors="replace")
        yield EvalTask(problem=problem_cache[r.problem_label], submission=r, code=code)
