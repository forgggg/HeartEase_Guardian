from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents.assessment import TemplateAssessmentAgent
from app.agents.coordinator import RuleBasedAcademicCoordinator
from app.agents.profile import RuleBasedProfileAgent
from app.config import Settings
from app.data.mock_source import MockAcademicDataSource
from app.domain.academic.findings import identify_findings
from app.schemas.agent_outputs import AssessmentContext
from app.schemas.requests import AcademicAnalyzeRequest
from app.schemas.responses import (
    WarningResult,
)


DATA = Path(__file__).parents[1] / "app" / "data" / "mock" / "academic.json"


def test_template_mode_needs_no_api_key():
    current = Settings(agent_mode="template", llm_api_key="")
    assert current.agent_mode == "template"
    assert current.llm_api_key == ""


def test_unimplemented_agent_mode_is_rejected():
    with pytest.raises(ValidationError):
        Settings(agent_mode="langchain")


def test_rule_based_coordinator_builds_bounded_plan(body):
    request = AcademicAnalyzeRequest.model_validate(body)
    plan = RuleBasedAcademicCoordinator().coordinate(request)
    assert plan.student_id == "S001"
    assert plan.term == "2026-autumn"
    assert plan.required_data == ["grades", "attendance", "credits"]
    assert plan.max_suggestions == 3


def test_profile_agent_builds_factual_profile():
    facts = MockAcademicDataSource(DATA).get_facts("S001", "2026-autumn")
    profile = RuleBasedProfileAgent().build_profile(facts)
    assert profile.indicators.average_score == 62.4
    assert profile.trends[0].direction == "down"
    assert len(profile.course_risks) == 3
    assert profile.missing_fields == ["第4周某课程考勤记录"]


def test_assessment_agent_uses_profile_and_limits_suggestions():
    facts = MockAcademicDataSource(DATA).get_facts("S001", "2026-autumn")
    profile = RuleBasedProfileAgent().build_profile(facts)
    findings = identify_findings(profile.indicators)
    warning = WarningResult(
        triggered=True,
        warning_level="high",
        warning_type="academic_risk",
        triggered_rules=["REG_ACAD_003"],
        reason="Mock预警",
    )
    output = TemplateAssessmentAgent().assess(
        AssessmentContext(
            requirement="分析学业风险",
            profile=profile,
            deterministic_findings=findings,
            regulations=[],
            warning=warning,
            max_suggestions=2,
        )
    )
    assert output.risk_level == "high"
    assert output.possible_causes[0].needs_verification is True
    assert len(output.conclusions) == 4
    assert len(output.recommendations) == 2
