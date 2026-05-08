#!/usr/bin/env python3
"""Phase 2 V4 — evaluate the hand-written reference solution alongside students.

Wraps the reference C source into a synthetic EvalTask using P01 metadata, runs
it through the same evaluator the students go through, and prints likelihood
distribution side-by-side with student scores already on disk.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dcu_llm import LLMClient  # noqa: E402

from llm_code_review.config import load_config  # noqa: E402
from llm_code_review.evaluator import EvalContext, evaluate_task  # noqa: E402
from llm_code_review.loader import load_problem  # noqa: E402
from llm_code_review.models import EvalTask, FinalSubmissionRow  # noqa: E402


REF_USERNAME = "_ref_solution"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path,
                   help="lecture-code-review run dir (problem metadata source)")
    p.add_argument("--problem", default="P01")
    p.add_argument("--refsol", default=str(Path(__file__).parent / "refsol" / "P01_clean.c"))
    p.add_argument("--students-eval", required=True, type=Path,
                   help="llm-code-review run dir whose summary.csv is the comparison set")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    refsol_path = Path(args.refsol)
    code = refsol_path.read_text(encoding="utf-8")
    problem = load_problem(args.input, args.problem)

    fake_row = FinalSubmissionRow(
        submission_id="_REF_" + args.problem,
        user_id=-1,
        username=REF_USERNAME,
        problem_label=args.problem,
        problem_id=problem.label.__hash__(),  # not used downstream
        language="C",
        result=0,
        result_label="REF",
        score=problem.total_score,
        time_cost_ms=0,
        memory_cost_kb=0,
        create_time=None,
        final_code_path=str(refsol_path),
    )
    task = EvalTask(problem=problem, submission=fake_row, code=code)

    cfg = load_config(
        profile_arg=None,
        model_arg=None,
        temperature_arg=None,
        max_tokens_arg=None,
        concurrency_arg=1,
        retries_arg=None,
        ai_usage_enabled=True,
    )
    client = LLMClient(profile=cfg.profile, model=cfg.model)
    ctx = EvalContext(cfg=cfg, client=client)

    print("Evaluating reference solution...")
    r = evaluate_task(ctx, task)
    ev = r.evaluation
    ai = r.ai_usage

    print(f"\n[reference solution]  overall={ev.overall}  sps={ev.suggested_partial_score}")
    if ai and not ai.error:
        print(f"  ai_likelihood={ai.likelihood_score}  confidence={ai.confidence}")
        print(f"  signals: {len(ai.signals)} | counter_signals: {len(ai.counter_signals)}")

    # Compare with students' summary.csv
    student_csv = args.students_eval / "_meta" / "summary.csv"
    if not student_csv.is_file():
        print(f"\nno student summary at {student_csv}; skipping comparison")
        return 0

    rows = list(csv.DictReader(open(student_csv, encoding="utf-8")))
    rows = [r for r in rows if r.get("problem_label") == args.problem]

    def _ints(field: str) -> list[int]:
        out = []
        for r in rows:
            v = r.get(field)
            if v not in (None, ""):
                try:
                    out.append(int(v))
                except ValueError:
                    pass
        return out

    overall_ints = _ints("overall")
    ai_ints = _ints("ai_likelihood_score")

    print(f"\n[students {args.problem}]  n={len(rows)}")
    if overall_ints:
        print(
            f"  overall: min={min(overall_ints)} max={max(overall_ints)} "
            f"mean={statistics.fmean(overall_ints):.1f}"
        )
    if ai_ints:
        print(
            f"  ai_likelihood: min={min(ai_ints)} max={max(ai_ints)} "
            f"mean={statistics.fmean(ai_ints):.1f}"
        )

    if ai and not ai.error and ai_ints:
        diff = ai.likelihood_score - statistics.fmean(ai_ints)
        print(f"\n→ refsol ai_likelihood vs student mean: {diff:+.1f}")
        print("  (양수가 클수록 refsol 이 LLM-clean 패턴으로 인식되었다는 신호.")
        print("   고정 임계값이 아닌 상대 차이로 해석.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
