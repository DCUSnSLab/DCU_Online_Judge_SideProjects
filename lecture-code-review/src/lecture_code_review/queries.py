from __future__ import annotations

from typing import Iterable

import psycopg

from lecture_code_review.models import (
    Contest,
    Lecture,
    Problem,
    Student,
    Submission,
)


def fetch_lecture(conn: psycopg.Connection, lecture_id: int) -> Lecture | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, year, semester, status
            FROM lecture WHERE id = %s
            """,
            (lecture_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return Lecture(**row)


def fetch_contest(conn: psycopg.Connection, contest_id: int) -> Contest | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, lecture_id, lecture_contest_type, start_time, end_time
            FROM contest WHERE id = %s
            """,
            (contest_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return Contest(**row)


def fetch_problems(conn: psycopg.Connection, contest_id: int) -> list[Problem]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,
                   _id AS label,
                   title,
                   description,
                   input_description,
                   output_description,
                   samples,
                   hint,
                   languages,
                   time_limit,
                   memory_limit,
                   difficulty,
                   total_score,
                   test_case_score,
                   io_mode,
                   spj,
                   rule_type
            FROM problem WHERE contest_id = %s
            ORDER BY _id
            """,
            (contest_id,),
        )
        rows = cur.fetchall()
    return [Problem(**row) for row in rows]


def fetch_students(conn: psycopg.Connection, lecture_id: int) -> list[Student]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.user_id,
                   u.username,
                   u.realname,
                   u.schoolssn,
                   COALESCE(s.isallow, false) AS enrolled
            FROM lecture_signup_class s
            JOIN "user" u ON u.id = s.user_id
            WHERE s.lecture_id = %s
            ORDER BY u.username
            """,
            (lecture_id,),
        )
        rows = cur.fetchall()
    return [Student(**row) for row in rows]


def iter_submissions(
    conn: psycopg.Connection,
    lecture_id: int,
    contest_id: int,
    *,
    include_pending: bool,
) -> Iterable[Submission]:
    """Yield submissions ordered by (username, problem_label, create_time).

    `is_final` is True for the latest submission per (user_id, problem_id)
    within the export scope (PENDING/JUDGING are excluded unless
    include_pending=True, which means "final" is the latest *included* row).
    """
    pending_filter = "" if include_pending else " AND s.result NOT IN (6, 7)"
    sql = f"""
        SELECT s.id,
               s.user_id,
               s.username,
               s.problem_id,
               p._id AS problem_label,
               s.language,
               s.result,
               s.statistic_info,
               s.create_time,
               s.code,
               (ROW_NUMBER() OVER (
                    PARTITION BY s.user_id, s.problem_id
                    ORDER BY s.create_time DESC, s.id DESC
                ) = 1) AS is_final
        FROM submission s
        JOIN problem p ON p.id = s.problem_id
        WHERE s.lecture_id = %s AND s.contest_id = %s
              {pending_filter}
        ORDER BY s.username, p._id, s.create_time
    """

    with conn.cursor(name="lcr_submissions") as cur:
        cur.itersize = 200
        cur.execute(sql, (lecture_id, contest_id))
        for row in cur:
            yield Submission(**row)
