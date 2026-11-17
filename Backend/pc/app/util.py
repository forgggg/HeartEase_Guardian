from __future__ import annotations

import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")


def now() -> str:
    """上海时间，naive ISO（保持与既有接口字符串契约一致）。"""
    return datetime.now(TZ).replace(tzinfo=None).isoformat(timespec="seconds")


def parse_time(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def to_dt(value: str) -> datetime:
    return parse_time(value) or datetime.now(TZ).replace(tzinfo=None)


def new_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(TZ):%Y%m%d%H%M%S}_{secrets.token_hex(3)}"
