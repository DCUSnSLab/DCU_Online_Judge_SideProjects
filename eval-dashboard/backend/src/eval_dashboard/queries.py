"""SQL queries for OJ PostgreSQL.

Read-only. Schema reference: see lecture-code-review/src/lecture_code_review/queries.py
and DCU_Online_Judge_SideProjects/docs/01-backend.md.
"""

from __future__ import annotations

from typing import Any

import psycopg


def list_years(c: psycopg.Connection) -> list[int]:
    with c.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT year FROM lecture WHERE status = true ORDER BY year DESC"
        )
        return [r["year"] for r in cur.fetchall()]


def list_semesters(c: psycopg.Connection, year: int) -> list[int]:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT semester FROM lecture
            WHERE year = %s AND status = true
            ORDER BY semester
            """,
            (year,),
        )
        return [r["semester"] for r in cur.fetchall()]


def list_lectures(c: psycopg.Connection, year: int, semester: int) -> list[dict]:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, year, semester
            FROM lecture
            WHERE year = %s AND semester = %s AND status = true
            ORDER BY title
            """,
            (year, semester),
        )
        return cur.fetchall()


def list_contests(c: psycopg.Connection, lecture_id: int) -> list[dict]:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, lecture_id, lecture_contest_type, start_time, end_time
            FROM contest
            WHERE lecture_id = %s
            ORDER BY start_time DESC NULLS LAST, id DESC
            """,
            (lecture_id,),
        )
        return cur.fetchall()


def get_contest(c: psycopg.Connection, contest_id: int) -> dict | None:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, lecture_id, lecture_contest_type, start_time, end_time, rule_type
            FROM contest WHERE id = %s
            """,
            (contest_id,),
        )
        return cur.fetchone()


def get_lecture(c: psycopg.Connection, lecture_id: int) -> dict | None:
    with c.cursor() as cur:
        cur.execute(
            "SELECT id, title, year, semester, status FROM lecture WHERE id = %s",
            (lecture_id,),
        )
        return cur.fetchone()


def list_problems(c: psycopg.Connection, contest_id: int) -> list[dict]:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT id, _id AS label, title, total_score, difficulty
            FROM problem WHERE contest_id = %s ORDER BY _id
            """,
            (contest_id,),
        )
        return cur.fetchall()


def get_problem(c: psycopg.Connection, problem_id: int) -> dict | None:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT id, _id AS label, title, description, input_description, output_description,
                   samples, hint, languages, time_limit, memory_limit, difficulty, total_score,
                   contest_id
            FROM problem WHERE id = %s
            """,
            (problem_id,),
        )
        return cur.fetchone()


def list_students(c: psycopg.Connection, lecture_id: int) -> list[dict]:
    """Roster (signup_class) joined with user. Includes non-allowed signups too — UI can filter."""
    with c.cursor() as cur:
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
        return cur.fetchall()


def list_final_submissions(
    c: psycopg.Connection, lecture_id: int, contest_id: int, *, include_pending: bool = False
) -> list[dict]:
    """Latest (user, problem) submission within scope. ROW_NUMBER over create_time DESC."""
    pending_filter = "" if include_pending else " AND s.result NOT IN (6, 7)"
    sql = f"""
        WITH ranked AS (
            SELECT s.id,
                   s.user_id,
                   s.username,
                   s.problem_id,
                   p._id AS problem_label,
                   p.total_score,
                   s.language,
                   s.result,
                   s.statistic_info,
                   s.create_time,
                   ROW_NUMBER() OVER (
                       PARTITION BY s.user_id, s.problem_id
                       ORDER BY s.create_time DESC, s.id DESC
                   ) AS rn
            FROM submission s
            JOIN problem p ON p.id = s.problem_id
            WHERE s.lecture_id = %s AND s.contest_id = %s
                  {pending_filter}
        )
        SELECT id, user_id, username, problem_id, problem_label, total_score,
               language, result, statistic_info, create_time
        FROM ranked WHERE rn = 1
        ORDER BY username, problem_label
    """
    with c.cursor() as cur:
        cur.execute(sql, (lecture_id, contest_id))
        return cur.fetchall()


def get_submission_code(c: psycopg.Connection, submission_id: str) -> dict | None:
    with c.cursor() as cur:
        cur.execute(
            """
            SELECT id, code, language, result, statistic_info, create_time, user_id, username,
                   problem_id, contest_id, lecture_id
            FROM submission WHERE id = %s
            """,
            (submission_id,),
        )
        return cur.fetchone()
