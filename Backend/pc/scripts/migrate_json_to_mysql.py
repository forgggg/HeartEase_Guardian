"""把 var/ 下的 JSON 历史记录导入 MySQL（幂等）。

用法：.venv/bin/python scripts/migrate_json_to_mysql.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PC_DIR))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.models import Analysis, ResumeDoc  # noqa: E402
from app.storage import store_mysql, tables as t  # noqa: E402
from app.storage.db import engine  # noqa: E402
from app.util import new_id, parse_time, to_dt  # noqa: E402

VAR = PC_DIR / "var"


def migrate_docs() -> int:
    count = 0
    for path in sorted((VAR / "resumes").glob("*.json")):
        if path.name.endswith(".versions.json"):
            continue
        doc = ResumeDoc.model_validate_json(path.read_text(encoding="utf-8"))
        with engine().connect() as conn:
            if conn.execute(
                select(t.resume_doc.c.id).where(t.resume_doc.c.id == doc.id)
            ).first():
                continue
        store_mysql.create_doc(doc, note="JSON 迁移")
        count += 1
    return count


def migrate_versions() -> int:
    count = 0
    for path in sorted((VAR / "resumes").glob("*.versions.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            version_doc = ResumeDoc.model_validate(item["doc"])
            with engine().begin() as conn:
                exists = conn.execute(
                    select(t.resume_version.c.id).where(
                        t.resume_version.c.resume_id == version_doc.id,
                        t.resume_version.c.version == item["version"],
                    )
                ).first()
                if exists:
                    continue
                conn.execute(
                    t.resume_version.insert().values(
                        resume_id=version_doc.id,
                        version=item["version"],
                        doc_json=version_doc.model_dump(mode="json"),
                        note=item.get("note", ""),
                        confirmed=bool(item.get("confirmed", False)),
                        created_by=item.get("created_by", ""),
                        created_at=to_dt(item.get("created_at", "")),
                    )
                )
            count += 1
    return count


def migrate_analyses() -> int:
    count = 0
    for path in sorted((VAR / "analyses").glob("*.json")):
        analysis = Analysis.model_validate_json(path.read_text(encoding="utf-8"))
        # 早期版本的建议没有 id，按顺序补齐，避免 (analysis_id, '') 主键冲突
        seen: set[str] = set()
        for index, suggestion in enumerate(analysis.suggestions, start=1):
            if not suggestion.id or suggestion.id in seen:
                suggestion.id = f"s{index}"
            seen.add(suggestion.id)
        store_mysql.save_analysis(analysis)
        count += 1
    return count


def migrate_audit() -> int:
    path = VAR / "audit" / "audit.jsonl"
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        with engine().begin() as conn:
            exists = conn.execute(
                select(t.audit_log.c.id).where(t.audit_log.c.id == item["id"])
            ).first()
            if exists:
                continue
            conn.execute(
                t.audit_log.insert().values(
                    id=item["id"],
                    ts=parse_time(item["ts"]),
                    actor=item.get("actor", ""),
                    action=item.get("action", ""),
                    target_type=item.get("target_type", ""),
                    target_id=item.get("target_id", ""),
                    detail=item.get("detail", {}),
                    request_id=item.get("request_id", ""),
                )
            )
        count += 1
    return count


def migrate_uploads() -> int:
    directory = VAR / "uploads"
    if not directory.exists():
        return 0
    import hashlib
    from datetime import datetime

    count = 0
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        upload_id = new_id("upl")
        data = path.read_bytes()
        with engine().begin() as conn:
            conn.execute(
                t.upload_file.insert().values(
                    id=upload_id,
                    analysis_id=None,
                    filename=path.name,
                    sha256=hashlib.sha256(data).hexdigest(),
                    size_bytes=len(data),
                    stored_path=str(path.relative_to(VAR)),
                    created_by="",
                    created_at=datetime.fromtimestamp(path.stat().st_mtime),
                )
            )
        count += 1
    return count


def main() -> None:
    if settings().store_backend != "mysql":
        raise SystemExit("请先设置 STORE_BACKEND=mysql")
    if not VAR.exists():
        raise SystemExit("没有 var/ 历史数据可迁移")

    print(
        "migrated docs=%d versions=%d analyses=%d audit=%d uploads=%d"
        % (
            migrate_docs(),
            migrate_versions(),
            migrate_analyses(),
            migrate_audit(),
            migrate_uploads(),
        )
    )


if __name__ == "__main__":
    main()
