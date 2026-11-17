"""按天清理审计日志。

用法：.venv/bin/python scripts/prune_audit.py --days 180
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete

PC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PC_DIR))

from app.config import settings  # noqa: E402
from app.storage import tables as t  # noqa: E402
from app.storage.db import engine  # noqa: E402
from app.util import TZ  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()

    if settings().store_backend != "mysql":
        raise SystemExit("仅 mysql 后端支持此脚本")

    cutoff = datetime.now(TZ).replace(tzinfo=None) - timedelta(days=args.days)
    with engine().begin() as conn:
        result = conn.execute(delete(t.audit_log).where(t.audit_log.c.ts < cutoff))
    print(f"deleted {result.rowcount} audit rows older than {cutoff.isoformat()}")


if __name__ == "__main__":
    main()
