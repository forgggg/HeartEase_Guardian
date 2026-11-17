from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

resume_doc = Table(
    "resume_doc",
    metadata,
    Column("id", String(40), primary_key=True),
    Column("student_id", String(32), nullable=False, index=True),
    Column("template", String(16), nullable=False),
    Column("target_role", String(64), nullable=False, server_default=""),
    Column("version", Integer, nullable=False, default=1),
    Column("confirmed", Boolean, nullable=False, default=False),
    Column("needs_review", Boolean, nullable=False, default=False),
    Column("doc_json", JSON, nullable=False),
    Column("created_by", String(32), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

resume_version = Table(
    "resume_version",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("resume_id", String(40), nullable=False),
    Column("version", Integer, nullable=False),
    Column("doc_json", JSON, nullable=False),
    Column("note", String(255), nullable=False, server_default=""),
    Column("confirmed", Boolean, nullable=False, default=False),
    Column("created_by", String(32), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False),
)

resume_analysis = Table(
    "resume_analysis",
    metadata,
    Column("id", String(40), primary_key=True),
    Column("student_id", String(32), nullable=False, server_default=""),
    Column("filename", String(255), nullable=False, server_default=""),
    Column("target_role", String(64), nullable=False, server_default=""),
    Column("original_text", Text, nullable=False),
    Column("revised_text", Text, nullable=False),
    Column("quality_json", JSON, nullable=False),
    Column("rules_version", Integer, nullable=False, default=0),
    Column("created_by", String(32), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False),
)

resume_finding = Table(
    "resume_finding",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("analysis_id", String(40), nullable=False, index=True),
    Column("seq", Integer, nullable=False),
    Column("rule", String(8), nullable=False),
    Column("name", String(64), nullable=False),
    Column("severity", String(8), nullable=False),
    Column("original_text", Text, nullable=False),
    Column("evidence", String(255), nullable=False, server_default=""),
)

resume_suggestion = Table(
    "resume_suggestion",
    metadata,
    Column("analysis_id", String(40), primary_key=True),
    Column("suggestion_id", String(16), primary_key=True),
    Column("rule", String(8), nullable=False),
    Column("rules_json", JSON, nullable=False),
    Column("original_text", Text, nullable=False),
    Column("revised_text", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("accepted", Boolean, nullable=True),
    Column("decided_by", String(32), nullable=True),
    Column("decided_at", DateTime, nullable=True),
)

upload_file = Table(
    "upload_file",
    metadata,
    Column("id", String(40), primary_key=True),
    Column("analysis_id", String(40), nullable=True, index=True),
    Column("filename", String(255), nullable=False),
    Column("sha256", CHAR(64), nullable=False, index=True),
    Column("size_bytes", Integer, nullable=False),
    Column("stored_path", String(512), nullable=False),
    Column("created_by", String(32), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("seq", BigInteger, nullable=True),
    Column("id", String(40), primary_key=True),
    Column("ts", DateTime, nullable=False, index=True),
    Column("actor", String(64), nullable=False, server_default=""),
    Column("action", String(32), nullable=False, index=True),
    Column("target_type", String(16), nullable=False),
    Column("target_id", String(64), nullable=False, index=True),
    Column("detail", JSON, nullable=False),
    Column("request_id", String(64), nullable=False, server_default=""),
)
