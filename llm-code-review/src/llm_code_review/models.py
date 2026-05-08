from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProblemMeta:
    label: str
    title: str
    description: str
    input_description: str
    output_description: str
    samples: list[dict[str, Any]]
    hint: str | None
    languages: list[str]
    time_limit: int
    memory_limit: int
    difficulty: str
    total_score: int


@dataclass(frozen=True)
class FinalSubmissionRow:
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
    final_code_path: str


@dataclass(frozen=True)
class EvalTask:
    problem: ProblemMeta
    submission: FinalSubmissionRow
    code: str


@dataclass
class Evaluation:
    """LLM-produced qualitative evaluation for a single (user, problem)."""

    scores: dict[str, int]
    # Phase 2: comments are now a 2-key object per axis (assessment + suggestion).
    comments: dict[str, dict[str, str]]
    overall: int
    summary: str
    suggested_partial_score: int
    raw_response: str = ""
    llm_latency_ms: int = 0
    model_used: str = ""
    error: str | None = None

    # Phase 2: track when post-processing overrode model-provided overall/sps.
    recomputed: dict[str, Any] = field(default_factory=dict)

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
            "recomputed": self.recomputed,
        }


@dataclass
class AIUsageSignal:
    category: str
    observation: str
    weight: str   # low | medium | high


@dataclass
class AIUsageAssessment:
    """Companion assessment, ALWAYS kept separate from `Evaluation` and never
    fed into score calculations. Reference signal for graders."""

    likelihood_score: int          # [0, 100]
    confidence: str                # low | medium | high
    signals: list[AIUsageSignal]
    counter_signals: list[str]
    summary: str
    disclaimer: str
    raw_response: str = ""
    llm_latency_ms: int = 0
    model_used: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "likelihood_score": self.likelihood_score,
            "confidence": self.confidence,
            "signals": [s.__dict__ for s in self.signals],
            "counter_signals": self.counter_signals,
            "summary": self.summary,
            "disclaimer": self.disclaimer,
            "model_used": self.model_used,
            "llm_latency_ms": self.llm_latency_ms,
            "error": self.error,
        }
