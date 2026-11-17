import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)
PC_DIR = Path(__file__).resolve().parents[1]


def test_openapi_covers_resume_contract():
    spec = app.openapi()
    paths = spec["paths"]

    for path in [
        "/resume/write",
        "/resume/revise",
        "/resume/{resume_id}",
        "/resume/{resume_id}/versions",
        "/resume/{resume_id}/export",
        "/resume/{resume_id}/suggestions/{suggestion_id}/accept",
        "/resume/{resume_id}/suggestions/{suggestion_id}/reject",
        "/resume/rules",
    ]:
        assert path in paths, path

    schemas = spec["components"]["schemas"]
    for name in ["ResumeDoc", "Analysis", "ErrorResponse", "StudentProfile", "WriteResponse"]:
        assert name in schemas, name

    assert "tags" in paths["/resume/write"]["post"]


def test_frozen_openapi_matches_implementation():
    frozen = json.loads((PC_DIR / "openapi.json").read_text(encoding="utf-8"))
    assert frozen == app.openapi()


def test_real_mode_without_academic_data_returns_503(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "real")
    settings.cache_clear()
    try:
        res = client.get("/students/202210700001")
        assert res.status_code == 503
        assert res.json()["code"] == "DATA_UNAVAILABLE"
    finally:
        settings.cache_clear()


def test_mock_mode_is_self_contained(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "mock")
    settings.cache_clear()
    try:
        items = client.get("/students").json()
        assert len(items) == 20
        detail = client.get(f"/students/{items[0]['id']}").json()
        assert detail["sources"]["name"] == "mock"
        assert detail["gpa"] is not None
    finally:
        settings.cache_clear()


def test_examples_and_sse_schema_are_documented():
    spec = app.openapi()
    schemas = spec["components"]["schemas"]

    for name in ("WriteRequest", "WriteResponse", "Analysis", "AuditPage"):
        assert schemas[name].get("examples"), name

    body = schemas["Body_revise_resume_resume_revise_post"]["properties"]
    assert body["target_role"]["examples"] == ["Java 后端开发工程师"]
    assert body["student_id"]["examples"] == ["202210700001"]

    for path in ("/resume/write/stream", "/resume/revise/stream"):
        content = spec["paths"][path]["post"]["responses"]["200"]["content"]
        assert "text/event-stream" in content, path
        examples = content["text/event-stream"]["examples"]
        assert "event: done" in examples["write_stream"]["value"]
        assert "event: finding" in examples["revise_stream"]["value"]

    audit_params = {p["name"]: p for p in spec["paths"]["/audit"]["get"]["parameters"]}
    assert audit_params["actor"]["schema"]["examples"] == ["teacher_001"]
