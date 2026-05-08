from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from dcu_llm import LLMClient, LLMClientError

from llm_code_review.rubric import AXES, overall_score, partial_score

log = logging.getLogger(__name__)


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class LLMResponseError(Exception):
    """Raised when the LLM response cannot be parsed into the expected schema."""


# Qwen3 chat template option to disable reasoning content (the "thinking" mode).
QWEN_NO_THINK_EXTRA = {"chat_template_kwargs": {"enable_thinking": False}}


def _strip_fence(s: str) -> str:
    m = _FENCE.search(s)
    return m.group(1) if m else s


def _largest_json_object(s: str) -> str | None:
    best: tuple[int, int] | None = None
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    span = (start, i + 1)
                    if best is None or (span[1] - span[0]) > (best[1] - best[0]):
                        best = span
    return s[best[0] : best[1]] if best else None


def extract_json_object(text: str) -> dict[str, Any]:
    """Pull the largest top-level JSON object from a model response."""
    raw = _strip_fence(text).strip()
    candidate = raw if raw.startswith("{") else _largest_json_object(text)
    if not candidate:
        raise LLMResponseError("no JSON object in response")
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise LLMResponseError(f"invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMResponseError("response is not a JSON object")
    return data


def _check_nonempty_str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMResponseError(f"{where} must be a non-empty string")
    return value.strip()


def parse_response(text: str, *, total_score: int) -> dict[str, Any]:
    """Validate Phase 2 schema and recompute overall/sps with the canonical formulas.

    Always overrides model-provided overall/sps with formula values.
    Records discrepancies in `recomputed` for debugging.
    """
    data = extract_json_object(text)

    scores = data.get("scores")
    comments = data.get("comments")
    if not isinstance(scores, dict) or not isinstance(comments, dict):
        raise LLMResponseError("missing 'scores' or 'comments' object")

    norm_scores: dict[str, int] = {}
    norm_comments: dict[str, dict[str, str]] = {}
    for axis in AXES:
        v = scores.get(axis)
        try:
            iv = int(v)
        except (TypeError, ValueError):
            raise LLMResponseError(f"score for '{axis}' is not an int: {v!r}")
        norm_scores[axis] = max(0, min(10, iv))

        cobj = comments.get(axis)
        if not isinstance(cobj, dict):
            raise LLMResponseError(f"comments['{axis}'] must be an object with 'assessment' and 'suggestion'")
        norm_comments[axis] = {
            "assessment": _check_nonempty_str(cobj.get("assessment"), f"comments['{axis}'].assessment"),
            "suggestion": _check_nonempty_str(cobj.get("suggestion"), f"comments['{axis}'].suggestion"),
        }

    # Always recompute via canonical formulas. Model-provided values are kept for comparison only.
    canonical_overall = overall_score(norm_scores)
    canonical_sps = partial_score(total_score, norm_scores)

    model_overall = data.get("overall")
    model_sps = data.get("suggested_partial_score")
    try:
        model_overall_int = int(model_overall) if model_overall is not None else None
    except (TypeError, ValueError):
        model_overall_int = None
    try:
        model_sps_int = int(model_sps) if model_sps is not None else None
    except (TypeError, ValueError):
        model_sps_int = None

    recomputed: dict[str, Any] = {}
    if model_overall_int is None or model_overall_int != canonical_overall:
        recomputed["overall"] = {
            "model": model_overall_int,
            "formula": canonical_overall,
            "diff": (canonical_overall - model_overall_int) if model_overall_int is not None else None,
        }
    if model_sps_int is None or model_sps_int != canonical_sps:
        recomputed["suggested_partial_score"] = {
            "model": model_sps_int,
            "formula": canonical_sps,
            "diff": (canonical_sps - model_sps_int) if model_sps_int is not None else None,
        }

    return {
        "scores": norm_scores,
        "comments": norm_comments,
        "overall": canonical_overall,
        "summary": _check_nonempty_str(data.get("summary"), "summary"),
        "suggested_partial_score": canonical_sps,
        "recomputed": recomputed,
    }


def _backoff(attempt: int) -> float:
    return min(8.0, 1.5 ** attempt)


def call_with_retry(
    client: LLMClient,
    messages: list[dict[str, str]],
    *,
    parser,                     # callable: text -> parsed dict (raises LLMResponseError)
    model: str | None,
    temperature: float,
    max_tokens: int,
    retries: int,
) -> tuple[dict[str, Any], str, int]:
    """Generic retry loop for any LLM call that returns a parseable JSON object.

    Returns (parsed, raw_text, latency_ms).
    On exhausted retries, raises LLMResponseError with `last_raw` attached as
    attribute for debugging.
    """
    last_err: Exception | None = None
    last_raw: str = ""
    for attempt in range(retries + 1):
        try:
            t0 = time.monotonic()
            text = client.complete(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=QWEN_NO_THINK_EXTRA,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            last_raw = text
            parsed = parser(text)
            return parsed, text, latency_ms
        except LLMResponseError as e:
            last_err = e
            log.warning("attempt %d/%d: parse error: %s", attempt + 1, retries + 1, e)
        except LLMClientError as e:
            last_err = e
            log.warning("attempt %d/%d: client error: %s", attempt + 1, retries + 1, e)
        if attempt < retries:
            time.sleep(_backoff(attempt))
    err = last_err if last_err else LLMResponseError("unknown failure")
    setattr(err, "last_raw", last_raw)
    raise err
