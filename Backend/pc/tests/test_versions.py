import io

from docx import Document
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"X-User-Id": "teacher_001"}


def _bad_docx() -> bytes:
    doc = Document()
    for line in [
        "负责用户调研并输出需求文档",
        "参与后台接口开发，配合测试完成联调",
        "联系电话 13800138000",
    ]:
        doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def test_patch_creates_version_and_marks_manual():
    created = client.post(
        "/resume/write",
        json={"student_id": "202210700001"},
        headers=HEADERS,
    ).json()
    resume_id = created["resume_id"]
    assert created["llm_used"] is False
    assert created["doc"]["version"] == 1

    patched = client.patch(
        f"/resume/{resume_id}",
        json={"summary": "定制概述：后端方向", "confirm": True, "note": "辅导员改稿"},
        headers=HEADERS,
    )
    assert patched.status_code == 200, patched.text
    doc = patched.json()
    assert doc["version"] == 2
    assert doc["confirmed"] is True
    assert doc["summary"] == "定制概述：后端方向"
    assert doc["sources"]["summary"] == "manual"
    assert doc["created_by"] == "teacher_001"

    versions = client.get(f"/resume/{resume_id}/versions", headers=HEADERS).json()
    assert [v["version"] for v in versions] == [1, 2]
    assert versions[-1]["note"] == "辅导员改稿"


def test_suggestion_reject_then_accept_recomputes_text():
    analysis = client.post(
        "/resume/revise",
        files={"file": ("bad.docx", _bad_docx(), "application/octet-stream")},
        data={"target_role": "Java 后端开发工程师"},
        headers=HEADERS,
    ).json()

    privacy = next(s for s in analysis["suggestions"] if s["rule"] == "R9")
    assert privacy["id"]
    assert "13800138000" not in analysis["revised_text"]

    rejected = client.post(
        f"/resume/{analysis['id']}/suggestions/{privacy['id']}/reject",
        json={"reason": "保留联系方式"},
        headers=HEADERS,
    ).json()
    assert "13800138000" in rejected["revised_text"]
    assert rejected["suggestions"][0]["accepted"] is False
    assert rejected["suggestions"][0]["decided_by"] == "teacher_001"

    accepted = client.post(
        f"/resume/{analysis['id']}/suggestions/{privacy['id']}/accept",
        json={},
        headers=HEADERS,
    ).json()
    assert "13800138000" not in accepted["revised_text"]
    assert accepted["suggestions"][0]["accepted"] is True


def test_patch_version_conflict_returns_409(monkeypatch):
    created = client.post(
        "/resume/write", json={"student_id": "202210700004"}, headers=HEADERS
    ).json()
    resume_id = created["resume_id"]

    from app.resume import store

    monkeypatch.setattr(store, "save_edit", lambda *args, **kwargs: False)
    res = client.patch(
        f"/resume/{resume_id}", json={"summary": "并发改稿"}, headers=HEADERS
    )
    assert res.status_code == 409
    assert res.json()["code"] == "VERSION_CONFLICT"


def test_polish_is_off_by_default(monkeypatch):
    from app.resume import polish

    def boom(*_args, **_kwargs):
        raise AssertionError("默认配置不应调用模型")

    monkeypatch.setattr(polish, "_rewrite", boom)
    res = client.post(
        "/resume/write", json={"student_id": "202210700002"}, headers=HEADERS
    )
    assert res.status_code == 200
    assert res.json()["llm_used"] is False
