from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from llm_code_review.config import load_config
from llm_code_review.loader import (
    build_tasks,
    filter_submissions,
    load_final_submissions,
)
from llm_code_review.runner import run_dry, run_eval

log = logging.getLogger("llm_code_review")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="llm-code-review",
        description="Qualitative LLM evaluation of student final submissions exported by lecture-code-review.",
    )
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a lecture-code-review run dir, e.g. .../out/lecture-388_contest-6181",
    )
    p.add_argument("--out", type=Path, help="Output root (default: ./out/<input-run-name>)")
    p.add_argument("--problem", help="Problem label filter, e.g. P01")
    p.add_argument(
        "--username",
        action="append",
        default=[],
        help="Filter to specific username(s). Can be passed multiple times.",
    )
    p.add_argument("--profile", default=None, help="dcu_llm profile (default: onprem)")
    p.add_argument("--model", default=None, help="Override model name")
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--concurrency", type=int, default=None, help="1..4 (default 4)")
    p.add_argument("--retries", type=int, default=None, help="LLM/parsing retries (default 2)")
    p.add_argument(
        "--no-ai-usage",
        action="store_true",
        help="Skip the AI-usage assessment pass (qualitative evaluation only).",
    )
    p.add_argument("--dry-run", action="store_true", help="Build prompts only; no LLM calls.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    input_dir: Path = args.input.resolve()
    if not input_dir.is_dir():
        log.error("input dir not found: %s", input_dir)
        return 2

    final_csv = input_dir / "_meta" / "final_submissions.csv"
    if not final_csv.is_file():
        log.error("not a lecture-code-review run dir (missing %s)", final_csv)
        return 2

    out_dir = (args.out.resolve() if args.out else (Path("out").resolve() / input_dir.name))
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("input:  %s", input_dir)
    log.info("output: %s", out_dir)

    rows = load_final_submissions(input_dir)
    rows = filter_submissions(
        rows,
        problem=args.problem,
        usernames=set(args.username) if args.username else None,
    )
    if not rows:
        log.error("no submissions match filter (problem=%s, usernames=%s)", args.problem, args.username)
        return 3

    tasks = list(build_tasks(input_dir, rows))
    log.info("tasks: %d   ai_usage=%s", len(tasks), "off" if args.no_ai_usage else "on")

    cfg = load_config(
        profile_arg=args.profile,
        model_arg=args.model,
        temperature_arg=args.temperature,
        max_tokens_arg=args.max_tokens,
        concurrency_arg=args.concurrency,
        retries_arg=args.retries,
        ai_usage_enabled=not args.no_ai_usage,
    )

    if args.dry_run:
        info = run_dry(out_dir, tasks, cfg, input_dir)
        log.info("dry-run wrote %d prompt(s) to %s/prompts/", info["n_tasks"], out_dir)
        return 0

    info = run_eval(out_dir, tasks, cfg, input_dir)
    log.info(
        "done. evaluated=%d eval_failed=%d ai_failed=%d elapsed=%ss",
        info["n_evaluated"],
        info["n_eval_failed"],
        info["n_ai_usage_failed"],
        info["elapsed_seconds"],
    )
    return 0 if info["n_eval_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
