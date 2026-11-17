"""MySQL 仓储集成测试：需要本机 3306 与 *_test 库，连不上自动 skip。"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import audit
from app.config import settings
from app.models import Analysis, Finding, QualityReport, ResumeDoc, Suggestion
from app.storage import db, store_mysql
from app.util import now

SQL_FILE = __import__("pathlib").Path(__file__).resolve().parents[1] / "sql" / "001_schema.sql"


def _test_url():
    url = make_url(settings().database_url)
    if not url.database:
        pytest.skip("未配置 DATABASE_URL")
    return url.set(database=f"{url.database}_test")


def _statements() -> list[str]:
    raw = SQL_FILE.read_text(encoding="utf-8")
    lines = [line for line in raw.splitlines() if not line.strip().startswith("--")]
    return [chunk.strip() for chunk in "\n".join(lines).split(";") if chunk.strip()]


@pytest.fixture(scope="session")
def _schema():
    url = _test_url()
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in (
                "resume_suggestion",
                "resume_finding",
                "resume_analysis",
                "resume_version",
                "resume_doc",
                "upload_file",
                "audit_log",
            ):
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            for statement in _statements():
                conn.execute(text(statement))
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - 环境缺失时跳过
        pytest.skip(f"MySQL 不可用：{exc}")


@pytest.fixture
def mysql_backend(monkeypatch, _schema):
    url = _test_url()
    monkeypatch.setenv("STORE_BACKEND", "mysql")
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    settings.cache_clear()
    db.engine.cache_clear()

    engine = create_engine(url, connect_args={"connect_timeout": 3})
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in (
            "resume_version",
            "resume_doc",
            "resume_suggestion",
            "resume_finding",
            "resume_analysis",
            "upload_file",
            "audit_log",
        ):
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    engine.dispose()

    try:
        yield
    finally:
        settings.cache_clear()
        db.engine.cache_clear()


def _doc(version: int = 1) -> ResumeDoc:
    return ResumeDoc(
        id="res_mysql_test",
        student_id="202210700001",
        template="tech",
        target_role="Java 后端开发工程师",
        name="张晨",
        phone="138****0001",
        summary="后端方向",
        skills=["Java", "MySQL"],
        sources={"name": "db", "summary": "derived"},
        version=version,
        created_by="teacher_001",
        created_at=now(),
    )


def _analysis() -> Analysis:
    return Analysis(
        id="anl_mysql_test",
        student_id="202210700001",
        filename="resume.docx",
        target_role="Java 后端开发工程师",
        original_text="负责用户调研并输出需求文档",
        revised_text="输出需求文档",
        findings=[
            Finding(
                rule="R2",
                name="弱动词开头",
                severity="medium",
                original="负责用户调研并输出需求文档",
                evidence="弱动词",
            )
        ],
        suggestions=[
            Suggestion(
                id="s1",
                rule="R2",
                rules=["R2"],
                original="负责用户调研并输出需求文档",
                revised="输出需求文档",
                reason="动词开头",
            )
        ],
        quality=QualityReport(score=88, rules_version=1, findings=1),
        created_by="teacher_001",
        created_at=now(),
    )


def test_doc_and_version_roundtrip(mysql_backend):
    doc = _doc()
    store_mysql.create_doc(doc, "初始生成")
    assert store_mysql.load_doc(doc.id).name == "张晨"
    assert [v.version for v in store_mysql.load_versions(doc.id)] == [1]

    updated = doc.model_copy(deep=True)
    updated.version = 2
    updated.summary = "人工改稿"
    updated.created_by = "teacher_001"

    assert store_mysql.save_edit(updated, expected_version=1, note="人工编辑") is True
    assert store_mysql.save_edit(doc, expected_version=1, note="过期提交") is False

    stored = store_mysql.load_doc(doc.id)
    assert stored.version == 2 and stored.summary == "人工改稿"
    assert [v.version for v in store_mysql.load_versions(doc.id)] == [1, 2]


def test_analysis_roundtrip_and_decision(mysql_backend):
    analysis = _analysis()
    store_mysql.save_analysis(analysis)

    loaded = store_mysql.load_analysis(analysis.id)
    assert loaded.original_text.startswith("负责")
    assert loaded.findings[0].rule == "R2"
    assert loaded.suggestions[0].id == "s1"
    assert loaded.suggestions[0].accepted is None

    loaded.suggestions[0].accepted = True
    loaded.suggestions[0].decided_by = "teacher_001"
    loaded.suggestions[0].decided_at = now()
    loaded.revised_text = "输出需求文档"
    store_mysql.save_analysis(loaded)

    reloaded = store_mysql.load_analysis(analysis.id)
    assert reloaded.suggestions[0].accepted is True
    assert reloaded.suggestions[0].decided_by == "teacher_001"
    assert len(reloaded.findings) == 1


def test_audit_query_uses_sql(mysql_backend):
    audit.record("teacher_001", audit.RESUME_CREATE, "resume", "res_x", {"a": 1})
    audit.record("teacher_001", audit.RESUME_PATCH, "resume", "res_x", {"version": 2})
    audit.record("student_001", audit.AUTH_DENIED, "student", "202210700002", {})

    page = audit.query(target_id="res_x")
    assert page.total == 2
    assert [item.action for item in page.items] == ["resume.patch", "resume.create"]

    denied = audit.query(action=audit.AUTH_DENIED)
    assert denied.total == 1 and denied.items[0].actor == "student_001"

    paged = audit.query(target_id="res_x", limit=1, offset=1)
    assert paged.total == 2 and len(paged.items) == 1

    assert audit.query(since="2999-01-01").total == 0


def test_upload_metadata_and_attach(mysql_backend):
    upload_id = store_mysql.save_upload("resume.docx", b"hello mysql", "teacher_001")
    analysis = _analysis()
    store_mysql.save_analysis(analysis)
    store_mysql.attach_upload(upload_id, analysis.id)

    from app.storage import tables as t

    with db.engine().connect() as conn:
        row = conn.execute(
            t.upload_file.select().where(t.upload_file.c.id == upload_id)
        ).mappings().first()

    assert row["analysis_id"] == analysis.id
    assert row["size_bytes"] == len(b"hello mysql")
    assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
