"""初始化数据库：建库 + 按序执行 sql/*.sql（幂等）。

用法：.venv/bin/python scripts/init_db.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

PC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PC_DIR))

from app.config import settings  # noqa: E402

SQL_DIR = PC_DIR / "sql"


def split_statements(sql: str) -> list[str]:
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    statements = []
    for chunk in "\n".join(lines).split(";"):
        statement = chunk.strip()
        if statement:
            statements.append(statement)
    return statements


def main() -> None:
    url = make_url(settings().database_url)
    database = url.database
    if not database:
        raise SystemExit("DATABASE_URL 缺少数据库名")

    server = create_engine(url.set(database=None), connect_args={"connect_timeout": 5})
    with server.begin() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
        )

    engine = create_engine(
        url,
        connect_args={
            "connect_timeout": 5,
            "init_command": "SET time_zone = '+08:00'",
        },
    )
    applied = 0
    for file in sorted(SQL_DIR.glob("*.sql")):
        for statement in split_statements(re.sub(r"/\*.*?\*/", "", file.read_text(encoding="utf-8"), flags=re.S)):
            with engine.begin() as conn:
                conn.execute(text(statement))
            applied += 1
        print(f"applied {file.name}")

    with engine.connect() as conn:
        tables = [
            row[0]
            for row in conn.execute(text("SHOW TABLES"))
        ]
    print(f"database={database} statements={applied} tables={len(tables)}")
    for name in tables:
        print(" -", name)


if __name__ == "__main__":
    main()
