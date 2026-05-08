from __future__ import annotations

from dataclasses import dataclass


AXES: tuple[str, ...] = (
    "correctness",
    "algorithm",
    "readability",
    "problem_understanding",
)

AXIS_DESCRIPTIONS: dict[str, str] = {
    "correctness": "정상 입출력 + 코너케이스 처리. testcase 통과 여부와 별개의 코드 단위 정합성.",
    "algorithm": "접근 방식이 문제 의도에 맞는지, 시간/공간 적합성.",
    "readability": "네이밍·들여쓰기·함수 분리·주석 등 코드 가독성.",
    "problem_understanding": "요구사항·제약조건 반영도 (입출력 형식, 단위, 정밀도 등).",
}

AXIS_RANGE: tuple[int, int] = (0, 10)


def overall_score(scores: dict[str, int]) -> int:
    """Compute overall 0-100 from per-axis 0-10."""
    total = sum(int(scores.get(a, 0)) for a in AXES)
    max_total = AXIS_RANGE[1] * len(AXES)
    return round(total / max_total * 100)


@dataclass(frozen=True)
class Rubric:
    axes: tuple[str, ...] = AXES
    range_min: int = AXIS_RANGE[0]
    range_max: int = AXIS_RANGE[1]
    descriptions: dict[str, str] = None  # type: ignore[assignment]

    def to_dict(self) -> dict:
        return {
            "axes": list(self.axes),
            "range_min": self.range_min,
            "range_max": self.range_max,
            "descriptions": dict(AXIS_DESCRIPTIONS),
            "overall": "round(sum(axes) / (range_max * len(axes)) * 100)",
            "suggested_partial_score": "integer in [0, problem.total_score]",
        }


DEFAULT_RUBRIC = Rubric(descriptions=AXIS_DESCRIPTIONS)
