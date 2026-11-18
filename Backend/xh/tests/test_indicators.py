from pathlib import Path

from app.data.mock_source import MockAcademicDataSource
from app.domain.academic.indicators import calculate_indicators


DATA = Path(__file__).parents[1] / "app" / "data" / "mock" / "academic.json"


def test_calculates_required_indicators():
    facts = MockAcademicDataSource(DATA).get_facts("S001", "2026-autumn")
    result = calculate_indicators(facts)
    assert result.average_score == 62.4
    assert result.previous_average_score == 74.0
    assert result.average_score_change == -11.6
    assert result.failed_course_count == 3
    assert result.core_failed_course_count == 2
    assert result.absence_count == 8
    assert result.earned_credits == 48
    assert result.credit_completion_rate == 0.8
    assert result.remedial_course_count == 1
    assert result.retake_course_count == 1


def test_missing_data_remains_unknown():
    facts = MockAcademicDataSource(DATA).get_facts("S003", "2026-autumn")
    result = calculate_indicators(facts)
    assert result.previous_average_score is None
    assert result.average_score_change is None
    assert result.absence_count is None
    assert result.credit_completion_rate is None
