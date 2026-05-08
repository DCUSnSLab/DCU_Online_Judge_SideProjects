from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from llm_code_review.evaluator import TaskResult
from llm_code_review.models import AIUsageAssessment, EvalTask, Evaluation
from llm_code_review.prompt import build_user_prompt
from llm_code_review.rubric import AXES, DEFAULT_RUBRIC


_UNSAFE_FS = re.compile(r"[^A-Za-z0-9._\-]")


def _safe(name: str) -> str:
    s = _UNSAFE_FS.sub("_", name.strip())
    return s or "_"


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_rubric(out_dir: Path) -> None:
    p = _ensure(out_dir / "_meta") / "rubric.json"
    p.write_text(
        json.dumps(DEFAULT_RUBRIC.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_run_info(out_dir: Path, info: dict) -> None:
    p = _ensure(out_dir / "_meta") / "run_info.json"
    p.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


SUMMARY_FIELDS = [
    "username",
    "problem_label",
    "testcase_result",
    "testcase_score",
    "total_score",
    "correctness",
    "algorithm",
    "readability",
    "problem_understanding",
    "overall",
    "suggested_partial_score",
    "llm_latency_ms",
    "ai_likelihood_score",
    "ai_confidence",
    "ai_latency_ms",
    "error",
]


def open_summary(out_dir: Path):
    path = _ensure(out_dir / "_meta") / "summary.csv"
    f = path.open("w", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
    w.writeheader()
    return f, w


def summary_row(task: EvalTask, ev: Evaluation, ai: AIUsageAssessment | None) -> dict:
    s = task.submission
    return {
        "username": s.username,
        "problem_label": task.problem.label,
        "testcase_result": s.result_label,
        "testcase_score": s.score,
        "total_score": task.problem.total_score,
        "correctness": ev.scores.get("correctness"),
        "algorithm": ev.scores.get("algorithm"),
        "readability": ev.scores.get("readability"),
        "problem_understanding": ev.scores.get("problem_understanding"),
        "overall": ev.overall,
        "suggested_partial_score": ev.suggested_partial_score,
        "llm_latency_ms": ev.llm_latency_ms,
        "ai_likelihood_score": (ai.likelihood_score if ai and ai.error is None else ""),
        "ai_confidence": (ai.confidence if ai and ai.error is None else ""),
        "ai_latency_ms": (ai.llm_latency_ms if ai else ""),
        "error": ev.error or "",
    }


def write_evaluation_json(out_dir: Path, result: TaskResult) -> None:
    task = result.task
    ev = result.evaluation
    ai = result.ai_usage

    user_dir = _ensure(out_dir / "evaluations" / _safe(task.submission.username))
    payload = {
        "submission_id": task.submission.submission_id,
        "username": task.submission.username,
        "problem": {
            "label": task.problem.label,
            "title": task.problem.title,
            "total_score": task.problem.total_score,
            "difficulty": task.problem.difficulty,
        },
        "testcase": {
            "result": task.submission.result_label,
            "score": task.submission.score,
            "time_cost_ms": task.submission.time_cost_ms,
            "memory_cost_kb": task.submission.memory_cost_kb,
        },
        "evaluation": ev.to_dict(),
        "raw_response": ev.raw_response,
        "ai_usage_assessment": (ai.to_dict() if ai is not None else None),
        "ai_usage_raw_response": (ai.raw_response if ai is not None else None),
    }
    (user_dir / f"{_safe(task.problem.label)}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _lang_md(language: str) -> str:
    return {
        "C": "c",
        "C++": "cpp",
        "Java": "java",
        "Python3": "python",
        "Python2": "python",
    }.get(language, "")


_PIPE = "\\|"


def _md_escape_pipe(s: str) -> str:
    return (s or "").replace("|", _PIPE)


def write_report_md(out_dir: Path, result: TaskResult) -> None:
    task = result.task
    ev = result.evaluation
    ai = result.ai_usage
    p = task.problem
    s = task.submission

    user_dir = _ensure(out_dir / "reports" / _safe(s.username))

    score_lines = []
    for a in AXES:
        score_lines.append(f"| {a} | {ev.scores.get(a)} | (코멘트는 아래 ↓) |")
    score_table = (
        "| 축 | 점수 (0~10) | |\n"
        "|---|---|---|\n" + "\n".join(score_lines)
    )

    detail_blocks = []
    for a in AXES:
        c = (ev.comments or {}).get(a, {})
        assessment = _md_escape_pipe(c.get("assessment", ""))
        suggestion = _md_escape_pipe(c.get("suggestion", ""))
        detail_blocks.append(
            f"### {a} — {ev.scores.get(a)}/10\n"
            f"- **현재 상태**: {assessment or '(없음)'}\n"
            f"- **개선 방향**: {suggestion or '(없음)'}"
        )

    header = f"""# {s.username} — {p.label} {p.title}

- **종합 점수 (0~100)**: **{ev.overall}**
- **자동 채점**: {s.result_label} ({s.score if s.score is not None else "-"} / {p.total_score}점)
- **부분점수 제안 (0~{p.total_score})**: **{ev.suggested_partial_score}**
- **모델**: {ev.model_used}    LLM 응답 시간: {ev.llm_latency_ms} ms
"""
    err_block = f"\n> ⚠ 평가 오류: {ev.error}\n" if ev.error else ""

    recompute_block = ""
    if ev.recomputed:
        items = []
        for k, v in ev.recomputed.items():
            items.append(f"- `{k}`: 모델값 {v.get('model')} → 산식값 {v.get('formula')} (차이 {v.get('diff')})")
        recompute_block = "\n> 산식 재계산으로 모델값이 덮어써졌습니다.\n" + "\n".join(items) + "\n"

    body = f"""
## 정성 점수 (요약)

{score_table}

## 축별 상세

{chr(10).join(detail_blocks)}

## 종합 평
{ev.summary or "(없음)"}

## 학생 코드 ({s.language})

```{_lang_md(s.language)}
{task.code}
```
"""

    ai_block = ""
    if ai is not None:
        if ai.error:
            ai_block = f"\n---\n\n## AI 사용 가능성 평가 — 참고용 · 점수 미반영\n\n> ⚠ AI-usage 평가 실패: {ai.error}\n"
        else:
            sig_lines = "\n".join(
                f"- ({sg.weight}) **{sg.category}**: {sg.observation}" for sg in ai.signals
            ) or "- (관찰된 신호 없음)"
            counter_lines = "\n".join(f"- {c}" for c in ai.counter_signals) or "- (반대 신호 없음)"
            ai_block = f"""
---

## AI 사용 가능성 평가 — 참고용 · 점수 미반영

> {ai.disclaimer}

- **likelihood_score**: **{ai.likelihood_score}/100**    confidence: **{ai.confidence}**

### 신호
{sig_lines}

### 반대 신호 (counter_signals)
{counter_lines}

### 종합
{ai.summary}
"""

    (user_dir / f"{_safe(p.label)}.md").write_text(header + err_block + recompute_block + body + ai_block, encoding="utf-8")


def write_dryrun_prompt(out_dir: Path, task: EvalTask) -> None:
    user_dir = _ensure(out_dir / "prompts" / _safe(task.submission.username))
    text = build_user_prompt(task)
    (user_dir / f"{_safe(task.problem.label)}.md").write_text(text, encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
