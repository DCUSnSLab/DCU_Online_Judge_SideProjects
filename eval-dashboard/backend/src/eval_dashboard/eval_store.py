"""Read llm-code-review's output directory.

Layout (per docs/04-deploy.md):
    <LLM_CR_DIR>/out/<run_label>/
        _meta/{rubric,run_info,summary}.csv|json
        evaluations/<username>/<P0n>.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval_dashboard.config import get_settings


def run_label(lecture_id: int, contest_id: int) -> str:
    return f"lecture-{lecture_id}_contest-{contest_id}"


def run_dir(lecture_id: int, contest_id: int) -> Path:
    return get_settings().llm_cr_dir / "out" / run_label(lecture_id, contest_id)


def lecture_cr_run_dir(lecture_id: int, contest_id: int) -> Path:
    return get_settings().lecture_cr_dir / "out" / run_label(lecture_id, contest_id)


def has_lecture_cr_export(lecture_id: int, contest_id: int) -> bool:
    """Has lecture-code-review been run for this scope?"""
    p = lecture_cr_run_dir(lecture_id, contest_id) / "_meta" / "final_submissions.csv"
    return p.is_file()


def evaluations_dir(lecture_id: int, contest_id: int) -> Path:
    return run_dir(lecture_id, contest_id) / "evaluations"


def eval_path(lecture_id: int, contest_id: int, username: str, problem_label: str) -> Path:
    return evaluations_dir(lecture_id, contest_id) / username / f"{problem_label}.json"


def has_evaluation(lecture_id: int, contest_id: int, username: str, problem_label: str) -> bool:
    return eval_path(lecture_id, contest_id, username, problem_label).is_file()


def load_evaluation(
    lecture_id: int, contest_id: int, username: str, problem_label: str
) -> dict[str, Any] | None:
    p = eval_path(lecture_id, contest_id, username, problem_label)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def short_eval_for_scoreboard(eval_doc: dict | None) -> dict | None:
    """Extract just the fields the scoreboard cells need."""
    if not eval_doc:
        return None
    ev = eval_doc.get("evaluation") or {}
    ai = eval_doc.get("ai_usage_assessment") or {}
    out: dict[str, Any] = {
        "overall": ev.get("overall"),
        "suggested_partial_score": ev.get("suggested_partial_score"),
        "ai_likelihood_score": ai.get("likelihood_score") if ai and not ai.get("error") else None,
        "ai_confidence": ai.get("confidence") if ai and not ai.get("error") else None,
        "has_error": bool(ev.get("error")),
    }
    return out


def list_evaluated_pairs(lecture_id: int, contest_id: int) -> set[tuple[str, str]]:
    """Returns set of (username, problem_label) that have an evaluation file on disk."""
    base = evaluations_dir(lecture_id, contest_id)
    out: set[tuple[str, str]] = set()
    if not base.is_dir():
        return out
    for user_dir in base.iterdir():
        if not user_dir.is_dir():
            continue
        for f in user_dir.glob("*.json"):
            out.add((user_dir.name, f.stem))
    return out
