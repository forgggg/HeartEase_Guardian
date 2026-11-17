from app.models import Finding
from app.resume import suggest


def test_one_model_call_per_original(monkeypatch):
    calls: list[str] = []

    def fake_complete(system, user, fallback):
        calls.append(user)
        return {"revised": "主导用户调研并输出需求文档", "reason": "动词开头，结果前置"}

    monkeypatch.setattr(suggest, "complete_json", fake_complete)
    findings = [
        Finding(rule="R1", name="缺少量化结果", original="负责用户调研并输出需求文档", evidence="无数字"),
        Finding(rule="R2", name="弱动词开头", original="负责用户调研并输出需求文档", evidence="弱动词"),
    ]

    out = suggest.for_findings(findings, "Java 后端开发工程师")

    assert len(calls) == 1
    assert len(out) == 1
    assert out[0].rules == ["R1", "R2"]
    assert out[0].revised == "主导用户调研并输出需求文档"


def test_fidelity_rollback_reports_reason(monkeypatch):
    monkeypatch.setattr(
        suggest,
        "complete_json",
        lambda *a, **k: {"revised": "主导调研并覆盖 500+ 用户", "reason": "补充规模"},
    )
    finding = Finding(rule="R1", name="缺少量化结果", original="负责用户调研", evidence="无数字")

    out = suggest.for_findings([finding], "Java 后端开发工程师")

    assert out[0].revised == finding.original
    assert "500" in out[0].reason
