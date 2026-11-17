from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_resume_lifecycle_is_audited():
    created = client.post(
        "/resume/write", json={"student_id": "202210700001"}
    ).json()
    resume_id = created["resume_id"]

    client.patch(f"/resume/{resume_id}", json={"note": "审计用例"})
    client.get(f"/resume/{resume_id}/export", params={"format": "pdf"})

    page = client.get("/audit", params={"target_id": resume_id}).json()
    actions = {item["action"] for item in page["items"]}
    assert {"resume.create", "resume.patch", "resume.export"} <= actions
    assert page["total"] >= 3
    assert all(item["actor"] == "teacher_001" for item in page["items"])
    assert all(item["request_id"] for item in page["items"])


def test_audit_filters_and_pagination():
    created = client.post(
        "/resume/write", json={"student_id": "202210700002"}
    ).json()
    resume_id = created["resume_id"]
    client.patch(f"/resume/{resume_id}", json={"note": "第二次"})

    only_patch = client.get(
        "/audit", params={"action": "resume.patch", "target_id": resume_id}
    ).json()
    assert only_patch["total"] == 1
    assert only_patch["items"][0]["detail"]["version"] == 2

    page = client.get(
        "/audit", params={"target_id": resume_id, "limit": 1, "offset": 0}
    ).json()
    assert len(page["items"]) == 1
    assert page["total"] == 2


def test_forbidden_access_is_audited_and_blocked():
    client.get("/students/202210700002", headers={"X-User-Id": "student_001"})

    page = client.get(
        "/audit",
        params={"action": "auth.denied", "target_id": "202210700002"},
    ).json()
    assert page["total"] >= 1
    assert page["items"][0]["actor"] == "student_001"


def test_students_cannot_read_audit():
    res = client.get("/audit", headers={"X-User-Id": "student_001"})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN_AUDIT"
