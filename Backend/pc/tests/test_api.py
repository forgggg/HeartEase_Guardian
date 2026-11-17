import io

from docx import Document
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _bad_resume_docx() -> bytes:
    doc = Document()
    for line in [
        "负责用户调研并输出需求文档",
        "熟练掌握 Java 与 SQL",
        "参与后台接口开发，配合测试完成联调",
        "联系电话 13800138000",
    ]:
        doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def test_students_merge_real_and_mock():
    items = client.get("/students").json()
    assert items

    detail = client.get(f"/students/{items[0]['id']}").json()
    assert detail["sources"]["name"] == "db"
    assert detail["sources"]["gpa"] == "mock"
    assert detail["gpa"] is not None


def test_write_export_revise_roundtrip():
    sid = client.get("/students").json()[0]["id"]
    body = client.post("/resume/write", json={"student_id": sid}).json()

    doc = body["doc"]
    assert doc["name"] and doc["education"]["school"]
    assert body["template"]["id"] in {"tech", "general", "soe"}

    for fmt in ("docx", "pdf"):
        out = client.get(f"/resume/{body['resume_id']}/export", params={"format": fmt})
        assert out.status_code == 200
        assert len(out.content) > 1000

    res = client.post(
        "/resume/revise",
        files={"file": ("bad.docx", _bad_resume_docx(), "application/octet-stream")},
        data={"target_role": "Java 后端开发工程师"},
    )
    assert res.status_code == 200, res.text
    analysis = res.json()
    rules = {f["rule"] for f in analysis["findings"]}
    assert {"R2", "R9"} <= rules
    assert analysis["quality"]["score"] < 100

    export = client.get(f"/resume/{analysis['id']}/export", params={"format": "pdf"})
    assert export.status_code == 200 and len(export.content) > 1000
