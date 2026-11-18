import pytest


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"wendian_fail": True}, "WENDIAN_UNAVAILABLE"),
        ({"fenghuo_fail": True}, "FENGHUO_UNAVAILABLE"),
        ({"assessment_fail": True}, "ASSESSMENT_AGENT_UNAVAILABLE_OR_INVALID"),
        ({"assessment_invalid": True}, "ASSESSMENT_AGENT_UNAVAILABLE_OR_INVALID"),
    ],
)
def test_dependency_failure_degrades_to_partial(make_client, body, kwargs, reason):
    response = make_client(**kwargs).post("/api/v1/agents/academic/analyze", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial"
    assert reason in data["degradation_reasons"]
    assert data["recommendations"]


def test_fenghuo_failure_is_explicit_unknown(make_client, body):
    data = make_client(fenghuo_fail=True).post(
        "/api/v1/agents/academic/analyze", json=body
    ).json()
    assert data["warning"]["triggered"] is None
    assert data["warning"]["warning_level"] == "unknown"
