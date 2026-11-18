from __future__ import annotations

import hashlib

from app.agents.assessment import AcademicAssessmentAgent, TemplateAssessmentAgent
from app.agents.coordinator import AcademicCoordinator
from app.agents.profile import AcademicProfileAgent
from app.audit import record_audit
from app.config import Settings
from app.data.source import AcademicDataSource
from app.domain.academic.findings import identify_findings
from app.errors import AppError
from app.integrations.fenghuo import FenghuoAdapter
from app.integrations.wendian import WendianAdapter
from app.schemas.agent_outputs import AssessmentContext
from app.schemas.integrations import FenghuoRequest, WendianRequest
from app.schemas.requests import AcademicAnalyzeRequest
from app.schemas.responses import (
    AcademicAnalyzeResponse,
    Analysis,
    Collaboration,
    DataSnapshot,
    WarningResult,
)
from app.storage.assessment_store import JsonAssessmentStore


class AcademicService:
    def __init__(
        self,
        settings: Settings,
        data_source: AcademicDataSource,
        coordinator: AcademicCoordinator,
        profile_agent: AcademicProfileAgent,
        wendian: WendianAdapter,
        fenghuo: FenghuoAdapter,
        assessment_agent: AcademicAssessmentAgent,
        store: JsonAssessmentStore,
    ) -> None:
        self.settings = settings
        self.data_source = data_source
        self.coordinator = coordinator
        self.profile_agent = profile_agent
        self.wendian = wendian
        self.fenghuo = fenghuo
        self.assessment_agent = assessment_agent
        self.store = store

    def analyze(self, request: AcademicAnalyzeRequest) -> AcademicAnalyzeResponse:
        plan = self.coordinator.coordinate(request)
        student_id = plan.student_id
        if not self.data_source.is_authorized(request.counselor_id, student_id):
            record_audit(
                self.settings.var_dir,
                request.counselor_id,
                "academic.scope_denied",
                student_id,
                {"request_id": request.request_id, "term": request.term},
                {"code": "UNAUTHORIZED_SCOPE"},
            )
            raise AppError(403, "UNAUTHORIZED_SCOPE", "辅导员无权访问该学生数据")

        previous = self.store.get_by_request_id(request.request_id)
        if previous:
            if (
                previous.student.student_id != student_id
                or previous.data_snapshot.term != plan.term
            ):
                raise AppError(
                    409,
                    "REQUEST_ID_CONFLICT",
                    "request_id已被其他分析任务使用",
                )
            return previous

        facts = self.data_source.get_facts(student_id, plan.term)
        if facts is None:
            raise AppError(404, "STUDENT_NOT_FOUND", "未找到学生")
        if facts.current_courses is None and facts.attendance is None and facts.credits is None:
            raise AppError(503, "ACADEMIC_DATA_UNAVAILABLE", "关键学业数据全部不可用")

        profile = self.profile_agent.build_profile(facts)
        indicators = profile.indicators
        findings = identify_findings(indicators)
        regulations = []
        degradation_reasons: list[str] = []

        if plan.query_regulations:
            try:
                regulations = self.wendian.query(
                    WendianRequest(
                        request_id=request.request_id,
                        query="查询与课程不及格、缺勤、学分进度和成绩下降相关的有效制度",
                        student_facts={**indicators.model_dump(), "term": plan.term},
                    )
                ).regulations
            except Exception:
                degradation_reasons.append("WENDIAN_UNAVAILABLE")

        if plan.run_warning_detection:
            try:
                warning = self.fenghuo.detect(
                    FenghuoRequest(
                        request_id=request.request_id,
                        facts=indicators.model_dump(),
                        findings=[f.model_dump() for f in findings],
                        regulations=[r.model_dump() for r in regulations],
                    )
                )
            except Exception:
                degradation_reasons.append("FENGHUO_UNAVAILABLE")
                warning = self._unknown_warning("烽火预警检测不可用")
        else:
            warning = self._unknown_warning("请求未启用预警检测")

        try:
            assessment = self.assessment_agent.assess(
                AssessmentContext(
                    requirement=request.requirement,
                    profile=profile,
                    deterministic_findings=findings,
                    regulations=regulations,
                    warning=warning,
                    max_suggestions=plan.max_suggestions,
                )
            )
        except Exception:
            degradation_reasons.append("ASSESSMENT_AGENT_UNAVAILABLE_OR_INVALID")
            assessment = TemplateAssessmentAgent().assess(
                AssessmentContext(
                    requirement=request.requirement,
                    profile=profile,
                    deterministic_findings=findings,
                    regulations=regulations,
                    warning=warning,
                    max_suggestions=plan.max_suggestions,
                )
            )

        if facts.missing_fields:
            degradation_reasons.append("ACADEMIC_DATA_PARTIAL")
        response = AcademicAnalyzeResponse(
            request_id=request.request_id,
            assessment_id=self._assessment_id(request.request_id),
            status="partial" if degradation_reasons else "completed",
            student=profile.student,
            data_snapshot=DataSnapshot(
                term=profile.term,
                as_of=profile.data_as_of,
                indicators=profile.indicators,
                missing_fields=profile.missing_fields,
                sources=profile.sources,
            ),
            findings=findings,
            regulation_results=regulations,
            analysis=Analysis(
                summary=assessment.summary,
                risk_level=assessment.risk_level,
                possible_causes=assessment.possible_causes,
                questions_to_verify=assessment.questions_to_verify,
            ),
            warning=warning,
            recommendations=assessment.recommendations,
            collaboration=Collaboration(),
            degradation_reasons=list(dict.fromkeys(degradation_reasons)),
        )
        self.store.save(response)
        record_audit(
            self.settings.var_dir,
            request.counselor_id,
            "academic.assess",
            student_id,
            {"request_id": request.request_id, "term": request.term, "focus": request.focus},
            {
                "assessment_id": response.assessment_id,
                "status": response.status,
                "hit_count": sum(f.status == "hit" for f in findings),
            },
        )
        return response

    @staticmethod
    def _assessment_id(request_id: str) -> str:
        digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:12]
        return f"acad_{digest}"

    @staticmethod
    def _unknown_warning(reason: str) -> WarningResult:
        return WarningResult(
            triggered=None,
            warning_level="unknown",
            warning_type="academic_risk",
            triggered_rules=[],
            reason=reason,
            requires_human_review=True,
        )
