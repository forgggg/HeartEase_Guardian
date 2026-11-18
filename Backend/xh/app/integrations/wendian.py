from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.integrations import WendianRequest, WendianResponse
from app.schemas.responses import RegulationResult


class WendianAdapter(ABC):
    @abstractmethod
    def query(self, request: WendianRequest) -> WendianResponse: ...


class MockWendianAdapter(WendianAdapter):
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def query(self, request: WendianRequest) -> WendianResponse:
        if self.fail:
            raise TimeoutError("Mock 问典不可用")
        return WendianResponse(
            status="completed",
            regulations=[
                RegulationResult(
                    rule_id="REG_ACAD_003",
                    title="学业预警管理办法第三条",
                    content_summary="Mock 制度摘要；仅用于联调，不代表正式学校规定。",
                    source_document="Mock 制度文件",
                    version="mock-v1",
                    effective_date="2026-09-01",
                    applicability="possible",
                    source_locator="mock://regulations/REG_ACAD_003",
                )
            ],
        )
