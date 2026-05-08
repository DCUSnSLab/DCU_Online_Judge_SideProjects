from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from lecture_code_review.config import load_config
from lecture_code_review.db import connect
from lecture_code_review.exporter import (
    base_dir,
    export_meta,
    export_submissions,
    write_summary,
)
from lecture_code_review.queries import (
    fetch_contest,
    fetch_lecture,
    fetch_problems,
    fetch_students,
    iter_submissions,
)

log = logging.getLogger("lecture_code_review")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="lecture-code-review",
        description="Export DCU OJ lecture/contest student submissions to disk.",
    )
    p.add_argument("-L", "--lecture-id", type=int, required=True)
    p.add_argument("-C", "--contest-id", type=int, required=True)
    p.add_argument("--dsn", help="PostgreSQL DSN (overrides .env LCR_PG_DSN)")
    p.add_argument("--out", help="Output root directory (default: ./out)")
    p.add_argument(
        "--include-pending",
        action="store_true",
        help="Include submissions with result PENDING (6) or JUDGING (7).",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    cfg = load_config(args.dsn, args.out)
    out_base = base_dir(cfg.out_dir, args.lecture_id, args.contest_id)
    log.info("Output: %s", out_base)

    with connect(cfg.dsn) as conn:
        lecture = fetch_lecture(conn, args.lecture_id)
        if lecture is None:
            log.error("lecture id=%s not found", args.lecture_id)
            return 2

        contest = fetch_contest(conn, args.contest_id)
        if contest is None:
            log.error("contest id=%s not found", args.contest_id)
            return 2

        if contest.lecture_id is not None and contest.lecture_id != lecture.id:
            log.warning(
                "contest.lecture_id=%s != lecture.id=%s (proceeding anyway)",
                contest.lecture_id,
                lecture.id,
            )

        problems = fetch_problems(conn, args.contest_id)
        students = fetch_students(conn, args.lecture_id)

        log.info(
            "Lecture: %s [%d-%d]  Contest: %s",
            lecture.title,
            lecture.year,
            lecture.semester,
            contest.title,
        )
        log.info(
            "Problems: %d   Students(in lecture_signup_class): %d",
            len(problems),
            len(students),
        )

        out_base.mkdir(parents=True, exist_ok=True)
        export_meta(out_base, lecture, contest, problems, students)

        log.info("Streaming submissions to %s ...", out_base)
        sub_stats = export_submissions(
            out_base,
            iter_submissions(
                conn,
                args.lecture_id,
                args.contest_id,
                include_pending=args.include_pending,
            ),
        )

        write_summary(out_base, lecture, contest, problems, students, sub_stats)

    log.info(
        "Done. Submissions=%d  Users=%d  by_result=%s",
        sub_stats["n_submissions"],
        sub_stats["n_users_with_submissions"],
        sub_stats["by_result"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
