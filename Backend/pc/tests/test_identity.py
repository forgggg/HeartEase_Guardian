from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_default_user_can_list_students():
    res = client.get("/students")
    assert res.status_code == 200
    assert len(res.json()) == 20


def test_unknown_identity_is_rejected():
    res = client.get("/students", headers={"X-User-Id": "ghost"})
    assert res.status_code == 401
    assert res.json()["code"] == "UNKNOWN_USER"


def test_student_sees_only_self_and_is_forbidden_elsewhere():
    headers = {"X-User-Id": "student_001"}

    listed = client.get("/students", headers=headers).json()
    assert [s["id"] for s in listed] == ["202210700001"]

    assert client.get("/students/202210700001", headers=headers).status_code == 200

    forbidden = client.get("/students/202210700002", headers=headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "FORBIDDEN_STUDENT"


def test_counselor_scope_prefix_is_enforced():
    headers = {"X-User-Id": "teacher_002"}
    assert client.get("/students/202210700001", headers=headers).status_code == 200
