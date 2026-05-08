from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from eval_dashboard.config import get_settings


_pool: ConnectionPool | None = None


def init_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        cfg = get_settings()
        _pool = ConnectionPool(
            cfg.pg_dsn,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def conn() -> Iterator[psycopg.Connection]:
    pool = init_pool()
    with pool.connection() as c:
        c.read_only = True
        yield c
