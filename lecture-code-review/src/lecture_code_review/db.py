from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connect(dsn: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        conn.read_only = True
        yield conn
