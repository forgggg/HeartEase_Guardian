from __future__ import annotations

from abc import ABC, abstractmethod

from app.data.source import AcademicFacts
from app.domain.academic.indicators import calculate_indicators
from app.schemas.agent_outputs import AcademicProfile, AcademicTrend, CourseRisk
from app.schemas.responses import StudentInfo


class AcademicProfileAgent(ABC):
    """学生画像子智能体接口。"""

    @abstractmethod
    def build_profile(self, facts: AcademicFacts) -> AcademicProfile: ...


class RuleBasedProfileAgent(AcademicProfileAgent):
    """基于确定性Python计算的第一阶段画像实现。"""

    def build_profile(self, facts: AcademicFacts) -> AcademicProfile:
        indicators = calculate_indicators(facts)
        change = indicators.average_score_change
        if change is None:
            direction = "unknown"
        elif change > 0:
            direction = "up"
        elif change < 0:
            direction = "down"
        else:
            direction = "stable"

        trends = [
            AcademicTrend(
                metric="average_score",
                current_value=indicators.average_score,
                previous_value=indicators.previous_average_score,
                change=change,
                direction=direction,
            )
        ]
        course_risks = [
            CourseRisk(
                course_id=str(course.get("course_id", "")),
                course_name=str(course.get("course_name", "")),
                course_type=str(course.get("course_type", "")),
                score=course.get("score"),
                passed=course.get("passed"),
            )
            for course in (facts.current_courses or [])
            if course.get("passed") is False or course.get("score") is None
        ]
        return AcademicProfile(
            student=StudentInfo.model_validate(facts.student),
            term=facts.term,
            indicators=indicators,
            trends=trends,
            course_risks=course_risks,
            missing_fields=facts.missing_fields,
            sources=facts.sources,
            data_as_of=facts.as_of,
        )
