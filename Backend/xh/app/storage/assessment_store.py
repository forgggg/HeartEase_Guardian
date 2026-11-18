from __future__ import annotations

import json
import threading
from pathlib import Path

from app.schemas.responses import AcademicAnalyzeResponse


class JsonAssessmentStore:
    def __init__(self, var_dir: Path) -> None:
        self.path = var_dir / "assessments.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def get_by_request_id(self, request_id: str) -> AcademicAnalyzeResponse | None:
        rows = self._read()
        row = next((item for item in rows if item["request_id"] == request_id), None)
        return AcademicAnalyzeResponse.model_validate(row) if row else None

    def save(self, response: AcademicAnalyzeResponse) -> None:
        with self._lock:
            rows = self._read()
            if any(item["request_id"] == response.request_id for item in rows):
                return
            rows.append(response.model_dump(mode="json"))
            self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
