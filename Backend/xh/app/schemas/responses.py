from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["completed", "partial", "failed"]
FindingStatus = Literal["hit", "miss", "unknown"]
Severity = Literal["info", "low", "medium", "high", "critical"]


class StudentInfo(BaseModel):
    student_id: str
    name: str
    major: str
    grade: str
    class_name: str


class IndicatorSet(BaseModel):
    average_score: float | None
    previous_average_score: float | None
    average_score_change: float | None
    failed_course_count: int | None
    core_failed_course_count: int | None
    absence_count: int | None
    late_count: int | None
    earned_credits: float | None
    expected_credits: float | None
    credit_gap: float | None
    credit_completion_rate: float | None
    remedial_course_count: int | None
    retake_course_count: int | None


class DataSnapshot(BaseModel):
    term: str
    as_of: str
    indicators: IndicatorSet
    missing_fields: list[str]
    sources: list[str]
    calculation_version: str = "academic-indicators-v1"


class Finding(BaseModel):
    finding_id: str
    type: str
    rule_id: str
    rule_version: str
    status: FindingStatus
    severity: Severity
    conclusion: str
    actual_value: float | int | None
    threshold: str
    evidence: list[str]
    source: str
    missing_facts: list[str]


class RegulationResult(BaseModel):
    rule_id: str
    title: str
    content_summary: str
    source_document: str
    version: str
    effective_date: str
    applicability: str
    source_locator: str


class PossibleCause(BaseModel):
    hypothesis: str
    needs_verification: bool = True
    basis: str


class Analysis(BaseModel):
    summary: str
    risk_level: Severity
    possible_causes: list[PossibleCause]
    questions_to_verify: list[str]


class WarningResult(BaseModel):
    checked_by: str = "fenghuo"
    triggered: bool | None
    warning_level: Literal["none", "low", "medium", "high", "critical", "unknown"]
    warning_type: str
    triggered_rules: list[str]
    reason: str
    requires_human_review: bool = True


class Recommendation(BaseModel):
    priority: int = Field(ge=1, le=3)
    action: str
    reason: str
    related_evidence: list[str]


class Collaboration(BaseModel):
    needed: bool = False
    target_agent: str | None = None
    reason: str | None = None


class AcademicAnalyzeResponse(BaseModel):
    request_id: str
    assessment_id: str
    status: Status
    student: StudentInfo
    data_snapshot: DataSnapshot
    findings: list[Finding]
    regulation_results: list[RegulationResult]
    analysis: Analysis
    warning: WarningResult
    recommendations: list[Recommendation] = Field(max_length=3)
    collaboration: Collaboration = Field(default_factory=Collaboration)
    degradation_reasons: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "xuehai-academic"
    version: str = "0.1.0"
