"""审计：MySQL 写 audit_log；json 后端写 JSONL。查询走对应后端。"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from sqlalchemy import func, select

from .config import settings
from .logging_setup import REQUEST_ID
from .models import AuditPage, AuditRecord
from .util import new_id, now, to_dt

logger = logging.getLogger(__name__)
_lock = threading.Lock()

RESUME_CREATE = "resume.create"
RESUME_REVISE = "resume.revise"
RESUME_PATCH = "resume.patch"
RESUME_EXPORT = "resume.export"
SUGGESTION_ACCEPT = "suggestion.accept"
SUGGESTION_REJECT = "suggestion.reject"
STUDENT_VIEW = "student.view"
AUTH_DENIED = "auth.denied"


def _uses_mysql() -> bool:
    return settings().store_backend.strip().lower() == "mysql"


def _jsonl_path() -> Path:
    path = settings().var_dir / "audit" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record(
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict | None = None,
) -> AuditRecord:
    entry = AuditRecord(
        id=new_id("aud"),
        ts=now(),
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
        request_id=REQUEST_ID.get(),
    )

    if _uses_mysql():
        from .storage import tables as t
        from .storage.db import engine

        with engine().begin() as conn:
            conn.execute(
                t.audit_log.insert().values(
                    id=entry.id,
                    ts=to_dt(entry.ts),
                    actor=entry.actor,
                    action=entry.action,
                    target_type=entry.target_type,
                    target_id=entry.target_id,
                    detail=entry.detail,
                    request_id=entry.request_id,
                )
            )
    else:
        with _lock:
            with _jsonl_path().open("a", encoding="utf-8") as handle:
                handle.write(entry.model_dump_json() + "\n")

    logger.info(
        "audit",
        extra={
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "actor": actor,
        },
    )
    return entry


def query(
    actor: str = "",
    action: str = "",
    target_id: str = "",
    since: str = "",
    until: str = "",
    limit: int = 50,
    offset: int = 0,
) -> AuditPage:
    if _uses_mysql():
        return _query_mysql(actor, action, target_id, since, until, limit, offset)
    return _query_jsonl(actor, action, target_id, since, until, limit, offset)


def _query_mysql(actor, action, target_id, since, until, limit, offset) -> AuditPage:
    from .storage import tables as t
    from .storage.db import engine

    conditions = []
    if actor:
        conditions.append(t.audit_log.c.actor == actor)
    if action:
        conditions.append(t.audit_log.c.action == action)
    if target_id:
        conditions.append(t.audit_log.c.target_id == target_id)
    if since:
        conditions.append(t.audit_log.c.ts >= to_dt(since))
    if until:
        conditions.append(t.audit_log.c.ts <= to_dt(until))

    with engine().connect() as conn:
        total = conn.execute(
            select(func.count()).select_from(t.audit_log).where(*conditions)
        ).scalar_one()
        rows = conn.execute(
            select(t.audit_log)
            .where(*conditions)
            .order_by(t.audit_log.c.ts.desc(), t.audit_log.c.seq.desc())
            .limit(limit)
            .offset(offset)
        ).mappings().all()

    items = [
        AuditRecord(
            id=row["id"],
            ts=row["ts"].isoformat(timespec="seconds"),
            actor=row["actor"],
            action=row["action"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            detail=row["detail"] or {},
            request_id=row["request_id"],
        )
        for row in rows
    ]
    return AuditPage(total=total, items=items)


def _query_jsonl(actor, action, target_id, since, until, limit, offset) -> AuditPage:
    path = _jsonl_path()
    items: list[AuditRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = AuditRecord.model_validate(json.loads(line))
            except Exception:
                logger.warning("跳过损坏的审计记录")
                continue
            if actor and item.actor != actor:
                continue
            if action and item.action != action:
                continue
            if target_id and item.target_id != target_id:
                continue
            if since and item.ts < since:
                continue
            if until and item.ts > until:
                continue
            items.append(item)

    items.sort(key=lambda r: (r.ts, r.id), reverse=True)
    return AuditPage(total=len(items), items=items[offset : offset + limit])
