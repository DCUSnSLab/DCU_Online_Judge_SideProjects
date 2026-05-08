from __future__ import annotations

import logging
from dataclasses import dataclass

from dcu_llm import LLMClient

from llm_code_review.config import Config
from llm_code_review.llm import call_with_retry, LLMResponseError
from llm_code_review.models import EvalTask, Evaluation
from llm_code_review.prompt import build_messages

log = logging.getLogger(__name__)


@dataclass
class EvalContext:
    cfg: Config
    client: LLMClient


def evaluate_task(ctx: EvalContext, task: EvalTask) -> Evaluation:
    messages = build_messages(task)
    try:
        parsed, raw, latency_ms = call_with_retry(
            ctx.client,
            messages,
            model=ctx.cfg.model,
            temperature=ctx.cfg.temperature,
            max_tokens=ctx.cfg.max_tokens,
            retries=ctx.cfg.retries,
            total_score=task.problem.total_score,
        )
        return Evaluation(
            scores=parsed["scores"],
            comments=parsed["comments"],
            overall=parsed["overall"],
            summary=parsed["summary"],
            suggested_partial_score=parsed["suggested_partial_score"],
            raw_response=raw,
            llm_latency_ms=latency_ms,
            model_used=ctx.cfg.model or "<profile-default>",
        )
    except (LLMResponseError, Exception) as e:  # noqa: BLE001
        log.error("evaluation failed for %s/%s: %s", task.submission.username, task.problem.label, e)
        return Evaluation(
            scores={a: 0 for a in ("correctness", "algorithm", "readability", "problem_understanding")},
            comments={},
            overall=0,
            summary="",
            suggested_partial_score=0,
            raw_response="",
            llm_latency_ms=0,
            model_used=ctx.cfg.model or "<profile-default>",
            error=f"{type(e).__name__}: {e}",
        )
