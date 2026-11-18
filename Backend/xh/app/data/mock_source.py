from __future__ import annotations

import json
from pathlib import Path

from .source import AcademicDataSource, AcademicFacts


class MockAcademicDataSource(AcademicDataSource):
    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def is_authorized(self, counselor_id: str, student_id: str) -> bool:
        return any(
            row["counselor_id"] == counselor_id
            and row["student_id"] == student_id
            and row["active"]
            for row in self._load()["counselor_scopes"]
        )

    def get_facts(self, student_id: str, term: str) -> AcademicFacts | None:
        data = self._load()
        student = next((s for s in data["students"] if s["student_id"] == student_id), None)
        if student is None:
            return None
        term_data = next(
            (t for t in data["terms"] if t["student_id"] == student_id and t["term"] == term),
            None,
        )
        if term_data is None:
            return AcademicFacts(
                student=student,
                term=term,
                current_courses=None,
                previous_courses=None,
                attendance=None,
                credits=None,
                remedial_records=None,
                missing_fields=["term_academic_data"],
                sources=["mock_students"],
                as_of=data["as_of"],
            )
        return AcademicFacts(
            student=student,
            term=term,
            current_courses=term_data.get("courses"),
            previous_courses=term_data.get("previous_courses"),
            attendance=term_data.get("attendance"),
            credits=term_data.get("credits"),
            remedial_records=term_data.get("remedial_records"),
            missing_fields=term_data.get("missing_fields", []),
            sources=term_data.get("sources", []),
            as_of=term_data.get("as_of", data["as_of"]),
        )
