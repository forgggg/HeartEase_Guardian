"""JSON 文件后端：本地演示/离线测试用，接口与 MySQL 后端一致。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import settings
from ..models import Analysis, ResumeDoc, VersionRecord
from ..util import new_id


def _dir(name: str) -> Path:
    path = settings().var_dir / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_doc(doc: ResumeDoc) -> None:
    (_dir("resumes") / f"{doc.id}.json").write_text(
        doc.model_dump_json(indent=2), encoding="utf-8"
    )


def load_doc(resume_id: str) -> ResumeDoc | None:
    path = settings().var_dir / "resumes" / f"{resume_id}.json"
    return ResumeDoc.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def _versions_path(resume_id: str) -> Path:
    return settings().var_dir / "resumes" / f"{resume_id}.versions.json"


def append_version(doc: ResumeDoc, note: str = "") -> None:
    records = load_versions(doc.id)
    records.append(
        VersionRecord(
            version=doc.version,
            created_at=doc.created_at,
            created_by=doc.created_by,
            note=note,
            confirmed=doc.confirmed,
            doc=doc,
        )
    )
    _versions_path(doc.id).write_text(
        json.dumps([r.model_dump(mode="json") for r in records], ensure_ascii=False),
        encoding="utf-8",
    )


def load_versions(resume_id: str) -> list[VersionRecord]:
    path = _versions_path(resume_id)
    if not path.exists():
        return []
    return [VersionRecord.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def create_doc(doc: ResumeDoc, note: str = "初始生成") -> None:
    save_doc(doc)
    append_version(doc, note)


def save_edit(doc: ResumeDoc, expected_version: int, note: str = "") -> bool:
    """单进程 JSON 后端无并发写，等价于总是成功。"""
    save_doc(doc)
    append_version(doc, note)
    return True


def save_analysis(analysis: Analysis) -> None:
    (_dir("analyses") / f"{analysis.id}.json").write_text(
        analysis.model_dump_json(indent=2), encoding="utf-8"
    )


def load_analysis(analysis_id: str) -> Analysis | None:
    path = settings().var_dir / "analyses" / f"{analysis_id}.json"
    return Analysis.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def save_upload(filename: str, data: bytes, created_by: str = "") -> str:
    upload_id = new_id("upl")
    safe = re.sub(r"[^\w.\-\u4e00-\u9fa5]", "_", filename or "upload")[-60:]
    path = _dir("uploads") / f"{upload_id}_{safe}"
    path.write_bytes(data)
    return upload_id


def attach_upload(upload_id: str, analysis_id: str) -> None:
    return None
