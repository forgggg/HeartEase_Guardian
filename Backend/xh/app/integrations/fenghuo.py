from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.integrations import FenghuoRequest
from app.schemas.responses import WarningResult


class FenghuoAdapter(ABC):
    @abstractmethod
    def detect(self, request: FenghuoRequest) -> WarningResult: ...


class MockFenghuoAdapter(FenghuoAdapter):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def detect(self, request: FenghuoRequest) -> WarningResult:
        if self.fail:
            raise TimeoutError("Mock 烽火不可用")
        hits = [item for item in request.findings if item["status"] == "hit"]
        high = any(item["severity"] in {"high", "critical"} for item in hits)
        triggered = bool(hits)
        return WarningResult(
            triggered=triggered,
            warning_level="high" if high else ("medium" if triggered else "none"),
            warning_type="academic_risk",
            triggered_rules=[r["rule_id"] for r in request.regulations] if triggered else [],
            reason="Mock 预警检测命中学业风险" if triggered else "Mock 预警检测未命中",
            requires_human_review=True,
        )
