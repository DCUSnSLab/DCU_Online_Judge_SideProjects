from __future__ import annotations

import json
import re
from html import unescape

from llm_code_review.models import EvalTask
from llm_code_review.rubric import AXES, AXIS_DESCRIPTIONS, AXIS_RANGE


_HTML_TAG = re.compile(r"<[^>]+>")
_LANG_MD = {
    "C": "c",
    "C++": "cpp",
    "Java": "java",
    "Python3": "python",
    "Python2": "python",
    "Go": "go",
    "Rust": "rust",
    "JavaScript": "javascript",
    "Kotlin": "kotlin",
    "C#": "csharp",
}


def html_to_text(s: str) -> str:
    if not s:
        return ""
    s = unescape(s)
    s = _HTML_TAG.sub(" ", s)
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def _samples_block(samples: list[dict]) -> str:
    if not samples:
        return "(없음)"
    parts = []
    for i, s in enumerate(samples, 1):
        inp = (s.get("input") or "").rstrip()
        outp = (s.get("output") or "").rstrip()
        parts.append(f"예제 {i}:\n  입력: {inp}\n  출력: {outp}")
    return "\n".join(parts)


def _schema_json(total_score: int) -> str:
    schema = {
        "scores": {a: f"int in [{AXIS_RANGE[0]},{AXIS_RANGE[1]}]" for a in AXES},
        "comments": {a: "string (1~2 문장 한국어)" for a in AXES},
        "overall": "int in [0,100]",
        "summary": "string (한국어 2~3문장 종합 평)",
        "suggested_partial_score": f"int in [0,{total_score}]",
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


SYSTEM_PROMPT = (
    "당신은 C 프로그래밍 과목의 조교(TA)입니다. "
    "학생이 제출한 코드를 정성적으로 평가하세요. "
    "출력은 반드시 단일 JSON 객체로만 응답하고, JSON 외 다른 텍스트(설명, 마크다운, ``` 펜스 포함)는 절대 포함하지 마세요. "
    "평가 코멘트와 summary는 한국어로 작성하세요."
)


def build_user_prompt(task: EvalTask) -> str:
    p = task.problem
    s = task.submission

    desc = html_to_text(p.description)
    inp = html_to_text(p.input_description)
    outp = html_to_text(p.output_description)

    lang_md = _LANG_MD.get(s.language, "")

    axes_block = "\n".join(f"- {a}: {AXIS_DESCRIPTIONS[a]}" for a in AXES)

    return f"""[문제]
{p.label} (난이도 {p.difficulty}, 배점 {p.total_score})
제목: {p.title}

설명:
{desc}

입력 형식:
{inp}

출력 형식:
{outp}

{_samples_block(p.samples)}

[자동 채점 결과]
결과: {s.result_label}   testcase 점수: {s.score if s.score is not None else "-"}/{p.total_score}
시간: {s.time_cost_ms if s.time_cost_ms is not None else "-"} ms   메모리: {s.memory_cost_kb if s.memory_cost_kb is not None else "-"} KB

[학생 코드]
사용자: {s.username}   언어: {s.language}
```{lang_md}
{task.code}
```

[평가 지시]
다음 4개 축에 대해 각각 0~10의 정수 점수를 매기고, 각 축에 1~2문장 한국어 코멘트를 작성하세요.
{axes_block}

또한 `suggested_partial_score`를 0 이상 {p.total_score} 이하의 정수로 산출하세요.
이는 testcase 결과와 무관하게, 코드의 의도·접근이 옳다면 줄 수 있는 부분점수입니다.

응답은 다음 JSON 스키마를 따르는 단일 JSON 객체로만 출력하세요. 다른 어떤 텍스트도 출력하지 마세요.

{_schema_json(p.total_score)}
"""


def build_messages(task: EvalTask) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(task)},
    ]
