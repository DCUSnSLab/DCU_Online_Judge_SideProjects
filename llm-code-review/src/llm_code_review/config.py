from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    profile: str
    model: str | None
    temperature: float
    max_tokens: int
    concurrency: int
    retries: int


def load_config(
    *,
    profile_arg: str | None,
    model_arg: str | None,
    temperature_arg: float | None,
    max_tokens_arg: int | None,
    concurrency_arg: int | None,
    retries_arg: int | None,
) -> Config:
    load_dotenv()

    profile = profile_arg or os.environ.get("DCU_LLM_PROFILE") or "onprem"
    model = model_arg  # None means: let dcu_llm pick the profile default

    return Config(
        profile=profile,
        model=model,
        temperature=0.2 if temperature_arg is None else float(temperature_arg),
        max_tokens=1500 if max_tokens_arg is None else int(max_tokens_arg),
        concurrency=max(1, min(4, concurrency_arg or 4)),
        retries=2 if retries_arg is None else max(0, int(retries_arg)),
    )
