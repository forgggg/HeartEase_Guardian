import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_id_is_echoed_and_logged(caplog):
    with caplog.at_level(logging.INFO):
        res = client.get("/health", headers={"X-Request-Id": "rid-test-1"})

    assert res.headers["X-Request-Id"] == "rid-test-1"

    records = [
        r for r in caplog.records if getattr(r, "request_id", None) == "rid-test-1"
    ]
    assert records
    assert any(getattr(r, "path", "") == "/health" for r in records)
    assert any(getattr(r, "duration_ms", None) is not None for r in records)


def test_generated_request_id_when_header_missing():
    res = client.get("/health")
    assert len(res.headers["X-Request-Id"]) >= 8


def test_audit_emits_structured_log(caplog):
    with caplog.at_level(logging.INFO):
        client.post("/resume/write", json={"student_id": "202210700003"})

    audit_logs = [r for r in caplog.records if getattr(r, "action", None) == "resume.create"]
    assert audit_logs
    assert getattr(audit_logs[0], "actor", "") == "teacher_001"
