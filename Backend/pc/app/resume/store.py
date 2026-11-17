"""存储门面：按 STORE_BACKEND 选择 JSON 或 MySQL 实现，函数签名保持一致。"""

from __future__ import annotations

from ..config import settings
from ..models import Analysis, ResumeDoc, VersionRecord
from ..storage import store_json, store_mysql
from ..util import new_id, now

__all__ = [
    "new_id",
    "now",
    "create_doc",
    "save_edit",
    "save_doc",
    "append_version",
    "load_doc",
    "load_versions",
    "save_analysis",
    "load_analysis",
    "save_upload",
    "attach_upload",
]


def _impl():
    backend = settings().store_backend.strip().lower()
    if backend == "mysql":
        return store_mysql
    if backend == "json":
        return store_json
    raise RuntimeError(f"STORE_BACKEND 非法：{backend}（仅支持 json / mysql）")


def create_doc(doc: ResumeDoc, note: str = "初始生成") -> None:
    _impl().create_doc(doc, note)


def save_edit(doc: ResumeDoc, expected_version: int, note: str = "") -> bool:
    return _impl().save_edit(doc, expected_version, note)


def save_doc(doc: ResumeDoc) -> None:
    _impl().save_doc(doc)


def append_version(doc: ResumeDoc, note: str = "") -> None:
    _impl().append_version(doc, note)


def load_doc(resume_id: str) -> ResumeDoc | None:
    return _impl().load_doc(resume_id)


def load_versions(resume_id: str) -> list[VersionRecord]:
    return _impl().load_versions(resume_id)


def save_analysis(analysis: Analysis) -> None:
    _impl().save_analysis(analysis)


def load_analysis(analysis_id: str) -> Analysis | None:
    return _impl().load_analysis(analysis_id)


def save_upload(filename: str, data: bytes, created_by: str = "") -> str:
    return _impl().save_upload(filename, data, created_by)


def attach_upload(upload_id: str, analysis_id: str) -> None:
    _impl().attach_upload(upload_id, analysis_id)
