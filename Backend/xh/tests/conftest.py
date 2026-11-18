from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from app.agents.assessment import MockAssessmentAgent
from app.agents.coordinator import RuleBasedAcademicCoordinator
from app.agents.profile import RuleBasedProfileAgent
from app.api.academic import get_service
from app.config import Settings
from app.data.mock_source import MockAcademicDataSource
from app.domain.academic.service import AcademicService
from app.integrations.fenghuo import MockFenghuoAdapter
from app.integrations.wendian import MockWendianAdapter
from app.main import app
from app.storage.assessment_store import JsonAssessmentStore


def request_body(student_id: str = "S001", request_id: str = "req_test_001") -> dict:
    return {
        "request_id": request_id,
        "counselor_id": "T001",
        "student_scope": {"type": "single", "student_ids": [student_id]},
        "term": "2026-autumn",
        "task_type": "academic_risk_analysis",
        "requirement": "分析该生本学期成绩下降和缺勤情况，判断是否存在学业问题，并给出处置建议",
        "focus": ["grades", "attendance", "credits"],
        "options": {
            "query_regulations": True,
            "run_warning_detection": True,
            "max_suggestions": 3,
        },
    }


@pytest.fixture
def make_client(tmp_path):
    clients = []

    def factory(
        *,
        wendian_fail=False,
        fenghuo_fail=False,
        assessment_fail=False,
        assessment_invalid=False,
    ):
        current = Settings(var_dir=tmp_path)
        service = AcademicService(
            current,
            MockAcademicDataSource(current.data_file),
            RuleBasedAcademicCoordinator(),
            RuleBasedProfileAgent(),
            MockWendianAdapter(fail=wendian_fail),
            MockFenghuoAdapter(fail=fenghuo_fail),
            MockAssessmentAgent(
                fail=assessment_fail,
                invalid=assessment_invalid,
            ),
            JsonAssessmentStore(tmp_path),
        )
        app.dependency_overrides[get_service] = lambda: service
        client = TestClient(app)
        clients.append(client)
        return client

    yield factory
    app.dependency_overrides.clear()


@pytest.fixture
def body():
    return copy.deepcopy(request_body())
