from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.agent_outputs import (
    AcademicAssessment,
    AssessmentConclusion,
    AssessmentContext,
)
from app.schemas.responses import PossibleCause, Recommendation


class AcademicAssessmentAgent(ABC):
    """学业问题研判子智能体接口。"""

    @abstractmethod
    def assess(self, context: AssessmentContext) -> AcademicAssessment: ...


class TemplateAssessmentAgent(AcademicAssessmentAgent):
    """第一阶段的程序模板研判实现，不调用模型。"""

    def assess(self, context: AssessmentContext) -> AcademicAssessment:
        hits = [item for item in context.deterministic_findings if item.status == "hit"]
        unknowns = [
            item for item in context.deterministic_findings if item.status == "unknown"
        ]
        risk_level = (
            context.warning.warning_level
            if context.warning.warning_level != "unknown"
            else "info"
        )
        if risk_level not in {"info", "low", "medium", "high", "critical"}:
            risk_level = "info"
        summary = "；".join(item.conclusion for item in hits) or "现有数据未发现明确学业问题"
        if unknowns or context.profile.missing_fields:
            summary += "；部分数据缺失，结论需补充核实"

        possible_causes = []
        if hits:
            possible_causes.append(
                PossibleCause(
                    hypothesis="学习投入或课程适应情况可能发生变化",
                    needs_verification=True,
                    basis="学生画像中的指标命中确定性技术检测规则",
                )
            )
        recommendations: list[Recommendation] = []
        has_warning = context.warning.triggered is True
        has_missing_data = bool(unknowns or context.profile.missing_fields)

        if hits or has_warning:
            related_evidence = [item.finding_id for item in hits]
            related_evidence.extend(context.warning.triggered_rules)
            recommendations.append(
                Recommendation(
                    priority=len(recommendations) + 1,
                    action="由辅导员开展学业约谈",
                    reason="核实学业问题及预警背后的具体原因",
                    related_evidence=list(dict.fromkeys(related_evidence)),
                )
            )

        if hits:
            recommendations.append(
                Recommendation(
                    priority=len(recommendations) + 1,
                    action="与学生共同制定短期课程改进计划",
                    reason="将已识别问题转化为可跟踪目标",
                    related_evidence=[item.finding_id for item in hits],
                )
            )

        if has_missing_data:
            missing_evidence = [item.finding_id for item in unknowns]
            missing_evidence.extend(context.profile.missing_fields)
            recommendations.append(
                Recommendation(
                    priority=len(recommendations) + 1,
                    action="补齐缺失数据并安排后续复核",
                    reason="避免将缺失信息误判为无风险",
                    related_evidence=missing_evidence,
                )
            )

        return AcademicAssessment(
            summary=summary,
            risk_level=risk_level,
            conclusions=[
                AssessmentConclusion(
                    finding_id=item.finding_id,
                    conclusion=item.conclusion,
                    severity=item.severity,
                    evidence=item.evidence,
                )
                for item in hits
            ],
            possible_causes=possible_causes,
            questions_to_verify=(
                ["近期学习投入、课程困难和缺勤原因分别是什么？"]
                if hits or has_warning
                else []
            ),
            recommendations=recommendations[: context.max_suggestions],
        )


class MockAssessmentAgent(TemplateAssessmentAgent):
    def __init__(self, fail: bool = False, invalid: bool = False) -> None:
        self.fail = fail
        self.invalid = invalid

    def assess(self, context: AssessmentContext) -> AcademicAssessment:
        if self.fail:
            raise RuntimeError("Mock研判智能体不可用")
        if self.invalid:
            raise ValueError("Mock研判智能体输出结构不合法")
        return super().assess(context)
