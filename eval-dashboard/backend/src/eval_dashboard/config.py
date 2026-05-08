from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


_DEFAULT_DSN = "postgresql://onlinejudge:onlinejudge@127.0.0.1:5432/onlinejudge"


@dataclass(frozen=True)
class Settings:
    pg_dsn: str
    lecture_cr_dir: Path
    llm_cr_dir: Path
    cors_origins: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        pg_dsn=os.environ.get("PG_DSN") or _DEFAULT_DSN,
        lecture_cr_dir=Path(os.environ.get("LECTURE_CR_DIR", "")).resolve(),
        llm_cr_dir=Path(os.environ.get("LLM_CR_DIR", "")).resolve(),
        cors_origins=tuple(
            o.strip() for o in (os.environ.get("CORS_ORIGINS") or "http://localhost:5173").split(",") if o.strip()
        ),
    )
