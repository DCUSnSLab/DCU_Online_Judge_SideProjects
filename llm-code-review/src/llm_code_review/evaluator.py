from __future__ import annotations

import logging
from dataclasses import dataclass

from dcu_llm import LLMClient

from llm_code_review import ai_usage as aiu
from llm_code_review.config import Config
from llm_code_review.llm import call_with_retry, LLMResponseError, parse_response
from llm_code_review.models import (
    AIUsageAssessment,
    EvalTask,
    Evaluation,
)
from llm_code_review.prompt import build_messages

log = logging.getLogger(__name__)


@dataclass
class EvalContext:
    cfg: Config
    client: LLMClient


def _qualitative(ctx: EvalContext, task: EvalTask) -> Evaluation:
    messages = build_messages(task)
    try:
        parsed, raw, latency_ms = call_with_retry(
            ctx.client,
            messages,
            parser=lambda text: parse_response(text, total_score=task.problem.total_score),
            model=ctx.cfg.model,
            temperature=ctx.cfg.temperature,
            max_tokens=ctx.cfg.max_tokens,
            retries=ctx.cfg.retries,
        )
        return Evaluation(
            scores=parsed["scores"],
            comments=parsed["comments"],
            overall=parsed["overall"],
            summary=parsed["summary"],
            suggested_partial_score=parsed["suggested_partial_score"],
            recomputed=parsed["recomputed"],
            raw_response=raw,
            llm_latency_ms=latency_ms,
            model_used=ctx.cfg.model or "<profile-default>",
        )
    except (LLMResponseError, Exception) as e:  # noqa: BLE001
        log.error("eval failed for %s/%s: %s", task.submission.username, task.problem.label, e)
        return Evaluation(
            scores={a: 0 for a in ("correctness", "algorithm", "readability", "problem_understanding")},
            comments={},
            overall=0,
            summary="",
            suggested_partial_score=0,
            raw_response=getattr(e, "last_raw", ""),
            llm_latency_ms=0,
            model_used=ctx.cfg.model or "<profile-default>",
            error=f"{type(e).__name__}: {e}",
        )


def _ai_usage(ctx: EvalContext, task: EvalTask) -> AIUsageAssessment:
    messages = aiu.build_messages(task)
    model = ctx.cfg.model or "<profile-default>"
    try:
        parsed, raw, latency_ms = call_with_retry(
            ctx.client,
            messages,
            parser=aiu.parse_response,
            model=ctx.cfg.model,
            temperature=ctx.cfg.temperature,
            max_tokens=ctx.cfg.max_tokens,
            retries=ctx.cfg.retries,
        )
        return aiu.make_assessment(parsed, raw=raw, latency_ms=latency_ms, model=model)
    except (LLMResponseError, Exception) as e:  # noqa: BLE001
        log.error("ai-usage failed for %s/%s: %s", task.submission.username, task.problem.label, e)
        return aiu.make_failed_assessment(f"{type(e).__name__}: {e}", model=model)


@dataclass
class TaskResult:
    task: EvalTask
    evaluation: Evaluation
    ai_usage: AIUsageAssessment | None


def evaluate_task(ctx: EvalContext, task: EvalTask) -> TaskResult:
    """Run the qualitative evaluation, then AI-usage if enabled.

    Both calls run sequentially within the task. Cross-task concurrency lives
    in runner.py (ThreadPoolExecutor).  Sequential within a task keeps the
    response stream order predictable for logging and avoids over-subscribing
    the LLM endpoint when concurrency=4 already saturates it.
    """
    evaluation = _qualitative(ctx, task)
    ai = _ai_usage(ctx, task) if ctx.cfg.ai_usage_enabled else None
    return TaskResult(task=task, evaluation=evaluation, ai_usage=ai)
