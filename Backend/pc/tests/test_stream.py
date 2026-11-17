import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_stream_emits_stage_and_done():
    body = client.post(
        "/resume/write/stream",
        json={"student_id": "202210700001"},
    ).text

    assert "event: stage" in body
    assert "event: done" in body


def test_revise_stream_emits_findings():
    from docx import Document

    doc = Document()
    for line in ["负责用户调研并输出需求文档", "联系电话 13800138000"]:
        doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)

    body = client.post(
        "/resume/revise/stream",
        files={"file": ("x.docx", buffer.getvalue(), "application/octet-stream")},
        data={"target_role": "Java 后端开发工程师"},
    ).text

    assert "event: finding" in body
    assert "event: suggestion" in body
    assert "event: done" in body


def test_unsupported_upload_returns_structured_error():
    res = client.post(
        "/resume/revise",
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert res.status_code == 415
    assert res.json()["code"] == "UNSUPPORTED_FILE_TYPE"
