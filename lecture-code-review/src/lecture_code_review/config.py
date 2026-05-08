from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_DSN = "postgresql://onlinejudge:onlinejudge@127.0.0.1:5432/onlinejudge"


@dataclass(frozen=True)
class Config:
    dsn: str
    out_dir: Path


def load_config(dsn_override: str | None, out_override: str | None) -> Config:
    load_dotenv()

    dsn = dsn_override or os.environ.get("LCR_PG_DSN") or DEFAULT_DSN
    out_dir = Path(out_override or os.environ.get("LCR_OUT_DIR") or "./out").resolve()

    return Config(dsn=dsn, out_dir=out_dir)
