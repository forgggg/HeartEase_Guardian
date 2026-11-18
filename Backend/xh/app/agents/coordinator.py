from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.agent_outputs import CoordinationResult
from app.schemas.requests import AcademicAnalyzeRequest


class AcademicCoordinator(ABC):
    """主智能体接口；未来的 LangChain 实现必须遵守相同契约。"""

    @abstractmethod
    def coordinate(self, request: AcademicAnalyzeRequest) -> CoordinationResult: ...


class RuleBasedAcademicCoordinator(AcademicCoordinator):
    """第一阶段的确定性调度器，不调用模型。"""

    def coordinate(self, request: AcademicAnalyzeRequest) -> CoordinationResult:
        return CoordinationResult(
            student_id=request.student_scope.student_ids[0],
            term=request.term,
            required_data=list(dict.fromkeys(request.focus)),
            query_regulations=request.options.query_regulations,
            run_warning_detection=request.options.run_warning_detection,
            max_suggestions=request.options.max_suggestions,
        )
