from app.domain.academic.findings import identify_findings
from app.schemas.responses import IndicatorSet


def values(**overrides):
    data = dict(
        average_score=62.4,
        previous_average_score=74,
        average_score_change=-11.6,
        failed_course_count=3,
        core_failed_course_count=2,
        absence_count=8,
        late_count=3,
        earned_credits=48,
        expected_credits=60,
        credit_gap=12,
        credit_completion_rate=0.8,
        remedial_course_count=1,
        retake_course_count=1,
    )
    data.update(overrides)
    return IndicatorSet(**data)


def test_all_four_rules_can_hit():
    findings = identify_findings(values())
    assert [item.status for item in findings] == ["hit", "hit", "hit", "hit"]
    assert all(item.rule_version == "mock-tech-v1" for item in findings)


def test_missing_value_is_unknown_not_miss():
    findings = identify_findings(values(absence_count=None))
    attendance = next(item for item in findings if item.type == "attendance_anomaly")
    assert attendance.status == "unknown"
    assert attendance.missing_facts == ["absence_count"]
