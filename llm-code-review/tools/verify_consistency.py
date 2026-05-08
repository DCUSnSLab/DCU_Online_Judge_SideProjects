#!/usr/bin/env python3
"""Phase 2 V1 — score consistency verifier.

Walks an llm-code-review output tree and verifies that every evaluation JSON's
`overall` and `suggested_partial_score` match the canonical formulas.

Usage:
    python tools/verify_consistency.py out/lecture-388_contest-6181
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Reuse formula source of truth.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from llm_code_review.rubric import overall_score, partial_score  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_consistency.py <out-run-dir>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    eval_dir = root / "evaluations"
    if not eval_dir.is_dir():
        print(f"no evaluations/ under {root}", file=sys.stderr)
        return 2

    n = 0
    fail = 0
    for path in sorted(eval_dir.rglob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        ev = d.get("evaluation") or {}
        scores = ev.get("scores") or {}
        if not scores:
            continue   # error case — no scores

        n += 1
        total_score = int((d.get("problem") or {}).get("total_score", 0))
        expected_overall = overall_score(scores)
        expected_sps = partial_score(total_score, scores)
        if ev.get("overall") != expected_overall:
            fail += 1
            print(f"[FAIL] {path}: overall {ev.get('overall')} != {expected_overall}")
        if ev.get("suggested_partial_score") != expected_sps:
            fail += 1
            print(f"[FAIL] {path}: sps {ev.get('suggested_partial_score')} != {expected_sps}")

    print(f"checked {n} evaluations, {fail} mismatches")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
