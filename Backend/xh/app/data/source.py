from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AcademicFacts:
    student: dict[str, Any]
    term: str
    current_courses: list[dict[str, Any]] | None
    previous_courses: list[dict[str, Any]] | None
    attendance: list[dict[str, Any]] | None
    credits: dict[str, Any] | None
    remedial_records: list[dict[str, Any]] | None
    missing_fields: list[str]
    sources: list[str]
    as_of: str


class AcademicDataSource(ABC):
    @abstractmethod
    def is_authorized(self, counselor_id: str, student_id: str) -> bool: ...

    @abstractmethod
    def get_facts(self, student_id: str, term: str) -> AcademicFacts | None: ...
