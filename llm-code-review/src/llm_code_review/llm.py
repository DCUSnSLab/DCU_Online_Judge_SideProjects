from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from dcu_llm import LLMClient, LLMClientError

from llm_code_review.rubric import AXES

log = logging.getLogger(__name__)


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class LLMResponseError(Exception):
    """Raised when the LLM response cannot be parsed into the expected schema."""


def _strip_fence(s: str) -> str:
    m = _FENCE.search(s)
    return m.group(1) if m else s


def _largest_json_object(s: str) -> str | None:
    """Return the largest top-level {...} substring."""
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


def parse_response(text: str, *, total_score: int) -> dict[str, Any]:
    """Extract and validate a JSON object from the LLM response text."""
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

    scores = data.get("scores")
    comments = data.get("comments")
    if not isinstance(scores, dict) or not isinstance(comments, dict):
        raise LLMResponseError("missing 'scores' or 'comments' object")

    norm_scores: dict[str, int] = {}
    norm_comments: dict[str, str] = {}
    for axis in AXES:
        v = scores.get(axis)
        try:
            iv = int(v)
        except (TypeError, ValueError):
            raise LLMResponseError(f"score for '{axis}' is not an int: {v!r}")
        norm_scores[axis] = max(0, min(10, iv))
        norm_comments[axis] = str(comments.get(axis, "")).strip()

    overall_v = data.get("overall")
    try:
        overall = max(0, min(100, int(overall_v)))
    except (TypeError, ValueError):
        # Recompute if missing or not int.
        overall = round(sum(norm_scores.values()) / 40 * 100)

    sps = data.get("suggested_partial_score")
    try:
        sps_int = int(sps)
    except (TypeError, ValueError):
        raise LLMResponseError(f"suggested_partial_score not int: {sps!r}")
    sps_int = max(0, min(int(total_score), sps_int))

    return {
        "scores": norm_scores,
        "comments": norm_comments,
        "overall": overall,
        "summary": str(data.get("summary", "")).strip(),
        "suggested_partial_score": sps_int,
    }


# Qwen3 chat template option to disable reasoning content (the "thinking" mode).
# Without this the model returns reasoning in message.reasoning_content and
# leaves message.content empty, which OpenAI SDK exposes as "".
_QWEN_NO_THINK_EXTRA = {"chat_template_kwargs": {"enable_thinking": False}}


def call_with_retry(
    client: LLMClient,
    messages: list[dict[str, str]],
    *,
    model: str | None,
    temperature: float,
    max_tokens: int,
    retries: int,
    total_score: int,
) -> tuple[dict[str, Any], str, int]:
    """Returns (parsed, raw_text, latency_ms)."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            t0 = time.monotonic()
            text = client.complete(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=_QWEN_NO_THINK_EXTRA,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            parsed = parse_response(text, total_score=total_score)
            return parsed, text, latency_ms
        except LLMResponseError as e:
            last_err = e
            log.warning("attempt %d/%d: parse error: %s", attempt + 1, retries + 1, e)
        except LLMClientError as e:
            last_err = e
            log.warning("attempt %d/%d: client error: %s", attempt + 1, retries + 1, e)
        if attempt < retries:
            time.sleep(min(8.0, 1.5 ** attempt))
    raise last_err if last_err else LLMResponseError("unknown failure")
