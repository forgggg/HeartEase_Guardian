from __future__ import annotations

import hashlib
import re

from sqlalchemy import Integer, cast, delete, func, insert, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert

from ..config import settings
from ..models import Analysis, ResumeDoc, Suggestion, VersionRecord
from ..util import new_id, now, parse_time, to_dt
from . import tables as t
from .db import engine


def _ts(value: str):
    return to_dt(value)


def _doc_row(doc: ResumeDoc) -> dict:
    return {
        "id": doc.id,
        "student_id": doc.student_id,
        "template": doc.template,
        "target_role": doc.target_role,
        "version": doc.version,
        "confirmed": doc.confirmed,
        "needs_review": doc.needs_review,
        "doc_json": doc.model_dump(mode="json"),
        "created_by": doc.created_by,
        "created_at": _ts(doc.created_at),
    }


def save_doc(doc: ResumeDoc) -> None:
    row = {**_doc_row(doc), "updated_at": _ts(now())}
    stmt = mysql_insert(t.resume_doc).values(**row)
    stmt = stmt.on_duplicate_key_update(
        **{key: stmt.inserted[key] for key in row if key != "id"}
    )
    with engine().begin() as conn:
        conn.execute(stmt)


def load_doc(resume_id: str) -> ResumeDoc | None:
    with engine().connect() as conn:
        row = conn.execute(
            select(t.resume_doc.c.doc_json).where(t.resume_doc.c.id == resume_id)
        ).first()
    return ResumeDoc.model_validate(row[0]) if row else None


def _version_row(doc: ResumeDoc, note: str) -> dict:
    return {
        "resume_id": doc.id,
        "version": doc.version,
        "doc_json": doc.model_dump(mode="json"),
        "note": note,
        "confirmed": doc.confirmed,
        "created_by": doc.created_by,
        "created_at": _ts(doc.created_at),
    }


def append_version(doc: ResumeDoc, note: str = "") -> None:
    stmt = mysql_insert(t.resume_version).values(**_version_row(doc, note))
    stmt = stmt.on_duplicate_key_update(
        doc_json=stmt.inserted.doc_json,
        note=stmt.inserted.note,
        confirmed=stmt.inserted.confirmed,
        created_by=stmt.inserted.created_by,
        created_at=stmt.inserted.created_at,
    )
    with engine().begin() as conn:
        conn.execute(stmt)


def load_versions(resume_id: str) -> list[VersionRecord]:
    with engine().connect() as conn:
        rows = conn.execute(
            select(t.resume_version)
            .where(t.resume_version.c.resume_id == resume_id)
            .order_by(t.resume_version.c.version)
        ).mappings().all()
    return [
        VersionRecord(
            version=row["version"],
            created_at=row["created_at"].isoformat(timespec="seconds"),
            created_by=row["created_by"],
            note=row["note"],
            confirmed=row["confirmed"],
            doc=ResumeDoc.model_validate(row["doc_json"]),
        )
        for row in rows
    ]


def create_doc(doc: ResumeDoc, note: str = "初始生成") -> None:
    row = {**_doc_row(doc), "updated_at": _ts(now())}
    with engine().begin() as conn:
        stmt = mysql_insert(t.resume_doc).values(**row)
        conn.execute(
            stmt.on_duplicate_key_update(
                **{key: stmt.inserted[key] for key in row if key != "id"}
            )
        )
        version_stmt = mysql_insert(t.resume_version).values(**_version_row(doc, note))
        conn.execute(
            version_stmt.on_duplicate_key_update(note=version_stmt.inserted.note)
        )


def save_edit(doc: ResumeDoc, expected_version: int, note: str = "") -> bool:
    """乐观锁：version 不匹配返回 False（上层映射 409）。"""
    row = _doc_row(doc)
    with engine().begin() as conn:
        result = conn.execute(
            update(t.resume_doc)
            .where(
                t.resume_doc.c.id == doc.id,
                t.resume_doc.c.version == expected_version,
            )
            .values(
                target_role=row["target_role"],
                version=row["version"],
                confirmed=row["confirmed"],
                needs_review=row["needs_review"],
                doc_json=row["doc_json"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                updated_at=_ts(now()),
            )
        )
        if result.rowcount != 1:
            return False
        stmt = mysql_insert(t.resume_version).values(**_version_row(doc, note))
        conn.execute(
            stmt.on_duplicate_key_update(
                doc_json=stmt.inserted.doc_json,
                note=stmt.inserted.note,
                confirmed=stmt.inserted.confirmed,
                created_by=stmt.inserted.created_by,
                created_at=stmt.inserted.created_at,
            )
        )
    return True


def save_analysis(analysis: Analysis) -> None:
    quality = analysis.quality
    with engine().begin() as conn:
        stmt = mysql_insert(t.resume_analysis).values(
            id=analysis.id,
            student_id=analysis.student_id,
            filename=analysis.filename,
            target_role=analysis.target_role,
            original_text=analysis.original_text,
            revised_text=analysis.revised_text,
            quality_json=quality.model_dump() if quality else {},
            rules_version=quality.rules_version if quality else 0,
            created_by=analysis.created_by,
            created_at=_ts(analysis.created_at),
        )
        conn.execute(
            stmt.on_duplicate_key_update(
                filename=stmt.inserted.filename,
                target_role=stmt.inserted.target_role,
                revised_text=stmt.inserted.revised_text,
                quality_json=stmt.inserted.quality_json,
                rules_version=stmt.inserted.rules_version,
                created_by=stmt.inserted.created_by,
            )
        )
        conn.execute(
            delete(t.resume_finding).where(t.resume_finding.c.analysis_id == analysis.id)
        )
        conn.execute(
            delete(t.resume_suggestion).where(
                t.resume_suggestion.c.analysis_id == analysis.id
            )
        )
        if analysis.findings:
            conn.execute(
                insert(t.resume_finding),
                [
                    {
                        "analysis_id": analysis.id,
                        "seq": index,
                        "rule": item.rule,
                        "name": item.name,
                        "severity": item.severity,
                        "original_text": item.original,
                        "evidence": item.evidence,
                    }
                    for index, item in enumerate(analysis.findings, start=1)
                ],
            )
        if analysis.suggestions:
            conn.execute(
                insert(t.resume_suggestion),
                [
                    {
                        "analysis_id": analysis.id,
                        "suggestion_id": item.id,
                        "rule": item.rule,
                        "rules_json": item.rules,
                        "original_text": item.original,
                        "revised_text": item.revised,
                        "reason": item.reason,
                        "accepted": item.accepted,
                        "decided_by": item.decided_by,
                        "decided_at": parse_time(item.decided_at or ""),
                    }
                    for item in analysis.suggestions
                ],
            )


def load_analysis(analysis_id: str) -> Analysis | None:
    with engine().connect() as conn:
        row = conn.execute(
            select(t.resume_analysis).where(t.resume_analysis.c.id == analysis_id)
        ).mappings().first()
        if row is None:
            return None
        findings = conn.execute(
            select(t.resume_finding)
            .where(t.resume_finding.c.analysis_id == analysis_id)
            .order_by(t.resume_finding.c.seq)
        ).mappings().all()
        suggestions = conn.execute(
            select(t.resume_suggestion)
            .where(t.resume_suggestion.c.analysis_id == analysis_id)
            .order_by(
                cast(
                    func.substring(t.resume_suggestion.c.suggestion_id, 2),
                    Integer,
                )
            )
        ).mappings().all()

    return Analysis(
        id=row["id"],
        student_id=row["student_id"],
        filename=row["filename"],
        target_role=row["target_role"],
        original_text=row["original_text"],
        revised_text=row["revised_text"],
        findings=[
            {
                "rule": item["rule"],
                "name": item["name"],
                "severity": item["severity"],
                "original": item["original_text"],
                "evidence": item["evidence"],
            }
            for item in findings
        ],
        suggestions=[
            Suggestion(
                id=item["suggestion_id"],
                rule=item["rule"],
                rules=item["rules_json"] or [],
                original=item["original_text"],
                revised=item["revised_text"],
                reason=item["reason"],
                accepted=item["accepted"],
                decided_by=item["decided_by"],
                decided_at=(
                    item["decided_at"].isoformat(timespec="seconds")
                    if item["decided_at"]
                    else None
                ),
            )
            for item in suggestions
        ],
        quality=row["quality_json"],
        created_by=row["created_by"],
        created_at=row["created_at"].isoformat(timespec="seconds"),
    )


def save_upload(filename: str, data: bytes, created_by: str = "") -> str:
    upload_id = new_id("upl")
    safe = re.sub(r"[^\w.\-\u4e00-\u9fa5]", "_", filename or "upload")[-60:]
    relative = f"uploads/{upload_id}_{safe}"
    path = settings().var_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    with engine().begin() as conn:
        conn.execute(
            insert(t.upload_file).values(
                id=upload_id,
                analysis_id=None,
                filename=filename or "upload",
                sha256=hashlib.sha256(data).hexdigest(),
                size_bytes=len(data),
                stored_path=relative,
                created_by=created_by,
                created_at=_ts(now()),
            )
        )
    return upload_id


def attach_upload(upload_id: str, analysis_id: str) -> None:
    with engine().begin() as conn:
        conn.execute(
            update(t.upload_file)
            .where(t.upload_file.c.id == upload_id)
            .values(analysis_id=analysis_id)
        )
