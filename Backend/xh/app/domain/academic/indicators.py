from __future__ import annotations

from app.data.source import AcademicFacts
from app.schemas.responses import IndicatorSet


def _average(courses: list[dict] | None) -> float | None:
    if not courses or any(course.get("score") is None for course in courses):
        return None
    return round(sum(float(course["score"]) for course in courses) / len(courses), 2)


def calculate_indicators(facts: AcademicFacts) -> IndicatorSet:
    current_average = _average(facts.current_courses)
    previous_average = _average(facts.previous_courses)
    score_change = (
        round(current_average - previous_average, 2)
        if current_average is not None and previous_average is not None
        else None
    )
    failed_count = None
    core_failed_count = None
    if facts.current_courses is not None:
        failed_count = sum(not bool(course.get("passed")) for course in facts.current_courses)
        core_failed_count = sum(
            not bool(course.get("passed")) and course.get("course_type") == "core"
            for course in facts.current_courses
        )
    absence_count = (
        sum(int(row.get("absence_count", 0)) for row in facts.attendance)
        if facts.attendance is not None
        else None
    )
    late_count = (
        sum(int(row.get("late_count", 0)) for row in facts.attendance)
        if facts.attendance is not None
        else None
    )
    earned = facts.credits.get("earned_credits") if facts.credits else None
    expected = facts.credits.get("expected_credits") if facts.credits else None
    gap = round(float(expected) - float(earned), 2) if earned is not None and expected is not None else None
    rate = round(float(earned) / float(expected), 4) if earned is not None and expected else None
    remedial = facts.remedial_records
    return IndicatorSet(
        average_score=current_average,
        previous_average_score=previous_average,
        average_score_change=score_change,
        failed_course_count=failed_count,
        core_failed_course_count=core_failed_count,
        absence_count=absence_count,
        late_count=late_count,
        earned_credits=earned,
        expected_credits=expected,
        credit_gap=gap,
        credit_completion_rate=rate,
        remedial_course_count=(sum(r.get("type") == "remedial" for r in remedial) if remedial is not None else None),
        retake_course_count=(sum(r.get("type") == "retake" for r in remedial) if remedial is not None else None),
    )
