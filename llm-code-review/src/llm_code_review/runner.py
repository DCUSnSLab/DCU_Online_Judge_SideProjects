from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from dcu_llm import LLMClient

from llm_code_review.config import Config
from llm_code_review.evaluator import EvalContext, evaluate_task
from llm_code_review.models import EvalTask
from llm_code_review.reporter import (
    SUMMARY_FIELDS,
    now_iso,
    open_summary,
    summary_row,
    write_dryrun_prompt,
    write_evaluation_json,
    write_report_md,
    write_rubric,
    write_run_info,
)

log = logging.getLogger(__name__)


def run_dry(out_dir: Path, tasks: list[EvalTask], cfg: Config, input_dir: Path) -> dict:
    write_rubric(out_dir)
    for t in tasks:
        write_dryrun_prompt(out_dir, t)
    info = {
        "mode": "dry-run",
        "input_dir": str(input_dir),
        "model": cfg.model or "<profile-default>",
        "profile": cfg.profile,
        "started_at": now_iso(),
        "n_tasks": len(tasks),
    }
    write_run_info(out_dir, info)
    return info


def run_eval(
    out_dir: Path,
    tasks: list[EvalTask],
    cfg: Config,
    input_dir: Path,
) -> dict:
    write_rubric(out_dir)
    started = now_iso()
    t_start = time.monotonic()

    client = LLMClient(profile=cfg.profile, model=cfg.model)
    ctx = EvalContext(cfg=cfg, client=client)

    n_evaluated = 0
    n_failed = 0

    f_summary, w_summary = open_summary(out_dir)
    try:
        if cfg.concurrency > 1:
            with ThreadPoolExecutor(max_workers=cfg.concurrency) as ex:
                futures = {ex.submit(evaluate_task, ctx, t): t for t in tasks}
                for fut in as_completed(futures):
                    t = futures[fut]
                    ev = fut.result()
                    write_evaluation_json(out_dir, t, ev)
                    write_report_md(out_dir, t, ev)
                    w_summary.writerow(summary_row(t, ev))
                    f_summary.flush()
                    if ev.error:
                        n_failed += 1
                    else:
                        n_evaluated += 1
                    log.info(
                        "[%d/%d] %s/%s overall=%s sps=%s%s",
                        n_evaluated + n_failed,
                        len(tasks),
                        t.submission.username,
                        t.problem.label,
                        ev.overall,
                        ev.suggested_partial_score,
                        f"  ERROR: {ev.error}" if ev.error else "",
                    )
        else:
            for i, t in enumerate(tasks, 1):
                ev = evaluate_task(ctx, t)
                write_evaluation_json(out_dir, t, ev)
                write_report_md(out_dir, t, ev)
                w_summary.writerow(summary_row(t, ev))
                f_summary.flush()
                if ev.error:
                    n_failed += 1
                else:
                    n_evaluated += 1
                log.info(
                    "[%d/%d] %s/%s overall=%s sps=%s latency=%dms%s",
                    i,
                    len(tasks),
                    t.submission.username,
                    t.problem.label,
                    ev.overall,
                    ev.suggested_partial_score,
                    ev.llm_latency_ms,
                    f"  ERROR: {ev.error}" if ev.error else "",
                )
    finally:
        f_summary.close()

    elapsed_s = round(time.monotonic() - t_start, 1)
    info = {
        "mode": "eval",
        "input_dir": str(input_dir),
        "model": cfg.model or "<profile-default>",
        "profile": cfg.profile,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "concurrency": cfg.concurrency,
        "retries": cfg.retries,
        "started_at": started,
        "finished_at": now_iso(),
        "elapsed_seconds": elapsed_s,
        "n_tasks": len(tasks),
        "n_evaluated": n_evaluated,
        "n_failed": n_failed,
    }
    write_run_info(out_dir, info)
    return info
