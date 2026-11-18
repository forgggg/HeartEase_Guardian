from __future__ import annotations

from dataclasses import dataclass

from app.schemas.responses import Finding, IndicatorSet


@dataclass(frozen=True)
class Rule:
    rule_id: str
    finding_type: str
    field: str
    operator: str
    threshold: float
    severity: str
    hit_text: str


RULES = [
    Rule("MOCK_ACAD_001", "multiple_failed_courses", "failed_course_count", ">=", 2, "high", "本学期存在多门课程未通过问题"),
    Rule("MOCK_ACAD_002", "attendance_anomaly", "absence_count", ">=", 5, "high", "本学期缺勤次数达到技术检测阈值"),
    Rule("MOCK_ACAD_003", "credit_progress_lag", "credit_completion_rate", "<", 0.85, "medium", "本学期学分完成进度落后"),
    Rule("MOCK_ACAD_004", "score_decline", "average_score_change", "<=", -10, "medium", "本学期平均成绩明显下降"),
]


def _hit(value: float, operator: str, threshold: float) -> bool:
    return {">=": value >= threshold, "<": value < threshold, "<=": value <= threshold}[operator]


def identify_findings(indicators: IndicatorSet) -> list[Finding]:
    findings: list[Finding] = []
    for index, rule in enumerate(RULES, 1):
        value = getattr(indicators, rule.field)
        if value is None:
            status, evidence, missing = "unknown", [], [rule.field]
            conclusion = f"缺少 {rule.field}，无法判断"
            severity = "info"
        elif _hit(float(value), rule.operator, rule.threshold):
            status, evidence, missing = "hit", [f"{rule.field}={value}"], []
            conclusion, severity = rule.hit_text, rule.severity
        else:
            status, evidence, missing = "miss", [f"{rule.field}={value}"], []
            conclusion, severity = "未命中该项技术检测规则", "info"
        findings.append(
            Finding(
                finding_id=f"finding_{index:03d}",
                type=rule.finding_type,
                rule_id=rule.rule_id,
                rule_version="mock-tech-v1",
                status=status,
                severity=severity,
                conclusion=conclusion,
                actual_value=value,
                threshold=f"{rule.operator} {rule.threshold:g}",
                evidence=evidence,
                source="xuehai_deterministic_rule",
                missing_facts=missing,
            )
        )
    return findings
