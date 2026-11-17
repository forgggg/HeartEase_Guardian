from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..config import settings


@lru_cache
def engine() -> Engine:
    url = settings().database_url.strip()
    if not url:
        raise RuntimeError("STORE_BACKEND=mysql 时必须配置 DATABASE_URL")
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings().db_pool_size,
        max_overflow=2,
        connect_args={
            "connect_timeout": 5,
            "init_command": "SET time_zone = '+08:00'",
        },
    )


def ping() -> None:
    with engine().connect() as conn:
        conn.execute(text("SELECT 1"))
