#!/usr/bin/env python3
"""Phase 2 V3 — repeatability check.

Runs the qualitative evaluation N times on the same submission and reports the
spread of axis scores, overall, suggested_partial_score, and AI-usage likelihood.

Usage:
    python tools/repeatability.py \
      --input ../lecture-code-review/out/lecture-388_contest-6181 \
      --problem P01 --username alswo6592 --repeat 3
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dcu_llm import LLMClient  # noqa: E402

from llm_code_review.config import load_config  # noqa: E402
from llm_code_review.evaluator import EvalContext, evaluate_task  # noqa: E402
from llm_code_review.loader import (  # noqa: E402
    build_tasks,
    filter_submissions,
    load_final_submissions,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--problem", required=True)
    p.add_argument("--username", required=True)
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--no-ai-usage", action="store_true")
    p.add_argument("--out", type=Path, help="Where to write repeatability.json (default: <input>/_repeat/)")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    rows = filter_submissions(
        load_final_submissions(args.input),
        problem=args.problem,
        usernames={args.username},
    )
    if len(rows) != 1:
        print(f"expected 1 row, got {len(rows)}", file=sys.stderr)
        return 2
    task = list(build_tasks(args.input, rows))[0]

    cfg = load_config(
        profile_arg=None,
        model_arg=None,
        temperature_arg=None,
        max_tokens_arg=None,
        concurrency_arg=1,
        retries_arg=None,
        ai_usage_enabled=not args.no_ai_usage,
    )
    client = LLMClient(profile=cfg.profile, model=cfg.model)
    ctx = EvalContext(cfg=cfg, client=client)

    runs = []
    for i in range(args.repeat):
        r = evaluate_task(ctx, task)
        runs.append(r)
        ev = r.evaluation
        ai = r.ai_usage
        print(
            f"[{i+1}/{args.repeat}] scores={ev.scores}  overall={ev.overall}  sps={ev.suggested_partial_score}"
            + (f"  ai_likelihood={ai.likelihood_score}" if ai and not ai.error else "")
        )

    def _stats(values: list[float]) -> dict:
        return {
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.fmean(values), 2),
            "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        }

    axes = ("correctness", "algorithm", "readability", "problem_understanding")
    summary = {
        "task": {"username": args.username, "problem_label": args.problem},
        "n_runs": len(runs),
        "axes": {a: _stats([float(r.evaluation.scores.get(a, 0)) for r in runs]) for a in axes},
        "overall": _stats([float(r.evaluation.overall) for r in runs]),
        "suggested_partial_score": _stats([float(r.evaluation.suggested_partial_score) for r in runs]),
    }
    if not args.no_ai_usage:
        ai_scores = [
            float(r.ai_usage.likelihood_score)
            for r in runs
            if r.ai_usage and not r.ai_usage.error
        ]
        if ai_scores:
            summary["ai_likelihood_score"] = _stats(ai_scores)

    out_dir = args.out or (args.input.parent / "_repeat")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.problem}_{args.username}_repeat{args.repeat}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nrepeatability summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nsaved → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
