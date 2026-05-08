from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Lecture:
    id: int
    title: str
    year: int
    semester: int
    status: bool


@dataclass(frozen=True)
class Contest:
    id: int
    title: str
    lecture_id: int | None
    lecture_contest_type: str
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class Problem:
    id: int
    label: str          # _id (e.g. "P01")
    title: str
    description: str
    input_description: str
    output_description: str
    samples: list[dict[str, Any]]
    hint: str | None
    languages: list[str]
    time_limit: int      # ms
    memory_limit: int    # MB
    difficulty: str
    total_score: int
    test_case_score: list[dict[str, Any]]
    io_mode: dict[str, Any]
    spj: bool
    rule_type: str


@dataclass(frozen=True)
class Student:
    user_id: int
    username: str
    realname: str | None
    schoolssn: int | None
    enrolled: bool


@dataclass(frozen=True)
class Submission:
    id: str
    user_id: int
    username: str
    problem_id: int
    problem_label: str
    language: str
    result: int
    statistic_info: dict[str, Any]
    create_time: datetime
    code: str
    is_final: bool      # latest submission per (user, problem) within the export scope
