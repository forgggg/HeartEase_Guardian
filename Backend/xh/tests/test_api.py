from conftest import request_body


def test_health(make_client):
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "xuehai-academic"


def test_full_risk_workflow_and_contract(make_client, body):
    response = make_client().post("/api/v1/agents/academic/analyze", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial"  # Mock 明确存在一项缺失考勤
    assert data["data_snapshot"]["indicators"]["failed_course_count"] == 3
    assert len([f for f in data["findings"] if f["status"] == "hit"]) == 4
    assert data["regulation_results"][0]["source_locator"].startswith("mock://")
    assert data["warning"]["triggered"] is True
    assert len(data["recommendations"]) <= 3
    assert data["analysis"]["possible_causes"][0]["needs_verification"] is True


def test_normal_student_has_no_hit(make_client):
    response = make_client().post(
        "/api/v1/agents/academic/analyze",
        json=request_body("S002", "req_normal"),
    )
    data = response.json()
    assert data["status"] == "completed"
    assert all(f["status"] == "miss" for f in data["findings"])
    assert data["warning"]["triggered"] is False
    assert data["recommendations"] == []
    assert data["analysis"]["questions_to_verify"] == []


def test_partial_data_returns_unknown(make_client):
    response = make_client().post(
        "/api/v1/agents/academic/analyze",
        json=request_body("S003", "req_partial"),
    )
    data = response.json()
    assert data["status"] == "partial"
    assert any(f["status"] == "unknown" for f in data["findings"])
    assert "ACADEMIC_DATA_PARTIAL" in data["degradation_reasons"]


def test_unauthorized_scope(make_client, body):
    body["counselor_id"] = "T999"
    response = make_client().post("/api/v1/agents/academic/analyze", json=body)
    assert response.status_code == 403
    assert response.json()["code"] == "UNAUTHORIZED_SCOPE"


def test_student_not_found(make_client):
    response = make_client().post(
        "/api/v1/agents/academic/analyze",
        json=request_body("S404", "req_missing"),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "STUDENT_NOT_FOUND"


def test_request_validation(make_client, body):
    body["student_scope"] = {"type": "batch", "student_ids": ["S001", "S002"]}
    assert make_client().post("/api/v1/agents/academic/analyze", json=body).status_code == 422


def test_duplicate_request_is_idempotent(make_client, body, tmp_path):
    client = make_client()
    first = client.post("/api/v1/agents/academic/analyze", json=body)
    second = client.post("/api/v1/agents/academic/analyze", json=body)
    assert first.json() == second.json()
    assert len((tmp_path / "assessments.json").read_text(encoding="utf-8").split('"request_id"')) - 1 == 1


def test_cached_result_still_requires_permission(make_client, body):
    client = make_client()
    first = client.post("/api/v1/agents/academic/analyze", json=body)
    assert first.status_code == 200

    body["counselor_id"] = "T999"
    second = client.post("/api/v1/agents/academic/analyze", json=body)
    assert second.status_code == 403
    assert second.json()["code"] == "UNAUTHORIZED_SCOPE"


def test_request_id_cannot_be_reused_for_another_task(make_client):
    client = make_client()
    first = request_body("S001", "req_conflict")
    second = request_body("S002", "req_conflict")

    assert client.post(
        "/api/v1/agents/academic/analyze", json=first
    ).status_code == 200
    response = client.post("/api/v1/agents/academic/analyze", json=second)
    assert response.status_code == 409
    assert response.json()["code"] == "REQUEST_ID_CONFLICT"


def test_openapi_exposes_main_contract(make_client):
    spec = make_client().get("/openapi.json").json()
    assert "/api/v1/agents/academic/analyze" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "AcademicAnalyzeRequest" in schemas
    assert "AcademicAnalyzeResponse" in schemas
