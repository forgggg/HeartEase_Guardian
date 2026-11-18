from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.responses import (
    Finding,
    IndicatorSet,
    PossibleCause,
    Recommendation,
    RegulationResult,
    StudentInfo,
    WarningResult,
)


class CoordinationResult(BaseModel):
    """主智能体对一次明确学业任务的受限调度计划。"""

    student_id: str
    term: str
    required_data: list[Literal["grades", "attendance", "credits"]]
    query_regulations: bool
    run_warning_detection: bool
    max_suggestions: int = Field(ge=1, le=3)


class AcademicTrend(BaseModel):
    metric: str
    current_value: float | None
    previous_value: float | None
    change: float | None
    direction: Literal["up", "down", "stable", "unknown"]


class CourseRisk(BaseModel):
    course_id: str
    course_name: str
    course_type: str
    score: float | None
    passed: bool | None


class AcademicProfile(BaseModel):
    """画像智能体输出；只描述事实、指标、趋势和数据完整性。"""

    student: StudentInfo
    term: str
    indicators: IndicatorSet
    trends: list[AcademicTrend]
    course_risks: list[CourseRisk]
    missing_fields: list[str]
    sources: list[str]
    data_as_of: str


class AssessmentContext(BaseModel):
    """研判智能体可见的画像、确定性问题及外部模块结果。"""

    requirement: str
    profile: AcademicProfile
    deterministic_findings: list[Finding]
    regulations: list[RegulationResult]
    warning: WarningResult
    max_suggestions: int = Field(ge=1, le=3)


class AssessmentConclusion(BaseModel):
    finding_id: str
    conclusion: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    evidence: list[str]


class AcademicAssessment(BaseModel):
    """研判智能体输出；不得修改画像、制度或烽火结果。"""

    summary: str
    risk_level: Literal["info", "low", "medium", "high", "critical"]
    conclusions: list[AssessmentConclusion]
    possible_causes: list[PossibleCause]
    questions_to_verify: list[str]
    recommendations: list[Recommendation] = Field(max_length=3)
