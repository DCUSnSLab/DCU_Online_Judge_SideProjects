from __future__ import annotations

import csv
import dataclasses
import json
import re
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from lecture_code_review.lang import ext_for, result_label
from lecture_code_review.models import (
    Contest,
    Lecture,
    Problem,
    Student,
    Submission,
)


_UNSAFE_FS = re.compile(r"[^A-Za-z0-9._\-]")


def _safe(name: str) -> str:
    """Make a string safe for use as a file/dir component."""
    s = _UNSAFE_FS.sub("_", name.strip())
    return s or "_"


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if dataclasses.is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"not serializable: {type(obj)!r}")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def export_meta(
    base: Path,
    lecture: Lecture,
    contest: Contest,
    problems: list[Problem],
    students: list[Student],
) -> None:
    meta = base / "_meta"
    meta.mkdir(parents=True, exist_ok=True)

    _write_json(meta / "lecture.json", asdict(lecture))
    _write_json(meta / "contest.json", asdict(contest))

    # Full problem content per file (used for grounding in Phase 2 evaluation).
    problems_dir = meta / "problems"
    problems_dir.mkdir(exist_ok=True)
    for p in problems:
        _write_json(problems_dir / f"{_safe(p.label)}.json", asdict(p))

    # Compact CSV index of problems.
    _write_csv(
        meta / "problems.csv",
        [asdict(p) for p in problems],
        fieldnames=[
            "id",
            "label",
            "title",
            "difficulty",
            "total_score",
            "time_limit",
            "memory_limit",
        ],
    )
    _write_csv(
        meta / "students.csv",
        [asdict(s) for s in students],
        fieldnames=["user_id", "username", "realname", "schoolssn", "enrolled"],
    )


def export_submissions(
    base: Path,
    submissions: Iterable[Submission],
) -> dict:
    """Stream submissions to disk; returns summary stats.

    Writes:
      - codes/<user>/<problem>/<ts>_<short_id>__<RESULT>.<ext>  (every submission)
      - final_codes/<user>/<problem>.<ext>                      (final per user/problem)
      - _meta/submissions.csv                                   (all rows, includes is_final)
      - _meta/final_submissions.csv                             (final rows only)
    """
    codes_root = base / "codes"
    final_codes_root = base / "final_codes"
    codes_root.mkdir(parents=True, exist_ok=True)
    final_codes_root.mkdir(parents=True, exist_ok=True)

    meta_dir = base / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    sub_fieldnames = [
        "id",
        "user_id",
        "username",
        "problem_label",
        "problem_id",
        "language",
        "result",
        "result_label",
        "score",
        "time_cost_ms",
        "memory_cost_kb",
        "create_time",
        "is_final",
    ]
    final_fieldnames = sub_fieldnames + ["final_code_path"]

    total = 0
    by_result: Counter[str] = Counter()
    by_language: Counter[str] = Counter()
    by_problem: Counter[str] = Counter()
    by_user: Counter[str] = Counter()

    n_final = 0
    final_by_result: Counter[str] = Counter()
    final_by_problem: Counter[str] = Counter()

    submissions_csv = meta_dir / "submissions.csv"
    final_submissions_csv = meta_dir / "final_submissions.csv"

    with submissions_csv.open("w", encoding="utf-8", newline="") as f_all, \
         final_submissions_csv.open("w", encoding="utf-8", newline="") as f_final:
        w_all = csv.DictWriter(f_all, fieldnames=sub_fieldnames, extrasaction="ignore")
        w_final = csv.DictWriter(f_final, fieldnames=final_fieldnames, extrasaction="ignore")
        w_all.writeheader()
        w_final.writeheader()

        for s in submissions:
            stat = s.statistic_info or {}
            label = result_label(s.result)
            ext = ext_for(s.language)

            row = {
                "id": s.id,
                "user_id": s.user_id,
                "username": s.username,
                "problem_label": s.problem_label,
                "problem_id": s.problem_id,
                "language": s.language,
                "result": s.result,
                "result_label": label,
                "score": stat.get("score"),
                "time_cost_ms": stat.get("time_cost"),
                "memory_cost_kb": stat.get("memory_cost"),
                "create_time": s.create_time.isoformat() if s.create_time else None,
                "is_final": s.is_final,
            }
            w_all.writerow(row)

            # Full code archive: every submission, named with timestamp + result.
            ts = s.create_time.strftime("%Y%m%d-%H%M%S") if s.create_time else "no-time"
            short_id = s.id[:8]
            fname = f"{ts}_{short_id}__{label}.{ext}"
            sub_dir = codes_root / _safe(s.username) / _safe(s.problem_label)
            sub_dir.mkdir(parents=True, exist_ok=True)
            (sub_dir / fname).write_text(s.code or "", encoding="utf-8")

            # Final-only mirror: flat per-problem file, easy to iterate for evaluation.
            if s.is_final:
                final_user_dir = final_codes_root / _safe(s.username)
                final_user_dir.mkdir(parents=True, exist_ok=True)
                final_path = final_user_dir / f"{_safe(s.problem_label)}.{ext}"
                final_path.write_text(s.code or "", encoding="utf-8")

                rel_final = final_path.relative_to(base).as_posix()
                w_final.writerow({**row, "final_code_path": rel_final})

                n_final += 1
                final_by_result[label] += 1
                final_by_problem[s.problem_label] += 1

            total += 1
            by_result[label] += 1
            by_language[s.language or "unknown"] += 1
            by_problem[s.problem_label] += 1
            by_user[s.username] += 1

    return {
        "n_submissions": total,
        "n_users_with_submissions": len(by_user),
        "by_result": dict(by_result),
        "by_language": dict(by_language),
        "by_problem": dict(by_problem),
        "by_user": dict(by_user),
        "n_final_submissions": n_final,
        "final_by_result": dict(final_by_result),
        "final_by_problem": dict(final_by_problem),
    }


def write_summary(
    base: Path,
    lecture: Lecture,
    contest: Contest,
    problems: list[Problem],
    students: list[Student],
    sub_stats: dict,
) -> None:
    summary = {
        "lecture": asdict(lecture),
        "contest": asdict(contest),
        "n_problems": len(problems),
        "n_students_in_lecture": len(students),
        "n_students_enrolled": sum(1 for s in students if s.enrolled),
        **sub_stats,
    }
    _write_json(base / "_meta" / "summary.json", summary)


def base_dir(out_root: Path, lecture_id: int, contest_id: int) -> Path:
    return out_root / f"lecture-{lecture_id}_contest-{contest_id}"
