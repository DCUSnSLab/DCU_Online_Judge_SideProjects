from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dcu_llm import LLMClient

from llm_code_review.config import Config
from llm_code_review.evaluator import EvalContext, TaskResult, evaluate_task
from llm_code_review.models import EvalTask
from llm_code_review.reporter import (
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
        "ai_usage_enabled": cfg.ai_usage_enabled,
        "started_at": now_iso(),
        "n_tasks": len(tasks),
    }
    write_run_info(out_dir, info)
    return info


def _log_result(idx: int, total: int, r: TaskResult) -> None:
    ai_str = ""
    if r.ai_usage is not None:
        if r.ai_usage.error:
            ai_str = f"  ai_usage=ERROR ({r.ai_usage.error[:60]})"
        else:
            ai_str = f"  ai_usage={r.ai_usage.likelihood_score}/{r.ai_usage.confidence}"
    err_str = f"  ERROR: {r.evaluation.error}" if r.evaluation.error else ""
    log.info(
        "[%d/%d] %s/%s overall=%s sps=%s ev_lat=%dms%s%s",
        idx,
        total,
        r.task.submission.username,
        r.task.problem.label,
        r.evaluation.overall,
        r.evaluation.suggested_partial_score,
        r.evaluation.llm_latency_ms,
        ai_str,
        err_str,
    )


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
    n_eval_failed = 0
    n_ai_failed = 0

    f_summary, w_summary = open_summary(out_dir)
    try:
        if cfg.concurrency > 1:
            with ThreadPoolExecutor(max_workers=cfg.concurrency) as ex:
                futures = {ex.submit(evaluate_task, ctx, t): t for t in tasks}
                for i, fut in enumerate(as_completed(futures), 1):
                    r = fut.result()
                    write_evaluation_json(out_dir, r)
                    write_report_md(out_dir, r)
                    w_summary.writerow(summary_row(r.task, r.evaluation, r.ai_usage))
                    f_summary.flush()
                    if r.evaluation.error:
                        n_eval_failed += 1
                    else:
                        n_evaluated += 1
                    if r.ai_usage and r.ai_usage.error:
                        n_ai_failed += 1
                    _log_result(i, len(tasks), r)
        else:
            for i, t in enumerate(tasks, 1):
                r = evaluate_task(ctx, t)
                write_evaluation_json(out_dir, r)
                write_report_md(out_dir, r)
                w_summary.writerow(summary_row(r.task, r.evaluation, r.ai_usage))
                f_summary.flush()
                if r.evaluation.error:
                    n_eval_failed += 1
                else:
                    n_evaluated += 1
                if r.ai_usage and r.ai_usage.error:
                    n_ai_failed += 1
                _log_result(i, len(tasks), r)
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
        "ai_usage_enabled": cfg.ai_usage_enabled,
        "started_at": started,
        "finished_at": now_iso(),
        "elapsed_seconds": elapsed_s,
        "n_tasks": len(tasks),
        "n_evaluated": n_evaluated,
        "n_eval_failed": n_eval_failed,
        "n_ai_usage_failed": n_ai_failed,
    }
    write_run_info(out_dir, info)
    return info
