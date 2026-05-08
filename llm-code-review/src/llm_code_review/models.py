from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProblemMeta:
    label: str          # e.g. "P01"
    title: str
    description: str
    input_description: str
    output_description: str
    samples: list[dict[str, Any]]
    hint: str | None
    languages: list[str]
    time_limit: int     # ms
    memory_limit: int   # MB
    difficulty: str
    total_score: int


@dataclass(frozen=True)
class FinalSubmissionRow:
    """A row from lecture-code-review's _meta/final_submissions.csv."""

    submission_id: str
    user_id: int
    username: str
    problem_label: str
    problem_id: int
    language: str
    result: int
    result_label: str
    score: int | None
    time_cost_ms: int | None
    memory_cost_kb: int | None
    create_time: str | None
    final_code_path: str    # relative to input_dir


@dataclass(frozen=True)
class EvalTask:
    problem: ProblemMeta
    submission: FinalSubmissionRow
    code: str


@dataclass
class Evaluation:
    """LLM-produced evaluation for a single (user, problem)."""

    scores: dict[str, int]
    comments: dict[str, str]
    overall: int
    summary: str
    suggested_partial_score: int
    raw_response: str = ""
    llm_latency_ms: int = 0
    model_used: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "scores": self.scores,
            "comments": self.comments,
            "overall": self.overall,
            "summary": self.summary,
            "suggested_partial_score": self.suggested_partial_score,
            "model_used": self.model_used,
            "llm_latency_ms": self.llm_latency_ms,
            "error": self.error,
        }
