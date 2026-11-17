from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MockCourse(BaseModel):
    name: str
    score: float
    credit: float = 0.0


class AcademicEntry(BaseModel):
    gpa: float
    rank: str
    cet4: int = 0
    cet6: int = 0
    courses: list[MockCourse] = []


class ExperienceItem(BaseModel):
    title: str
    org: str = ""
    start: str = ""
    end: str = ""
    tags: list[str] = []
    bullets: list[str] = []


class ExperienceFile(BaseModel):
    projects: list[ExperienceItem] = []
    internships: list[ExperienceItem] = []


class ProfilePools(BaseModel):
    courses: list[str] = []
    skills: list[str] = []
    certificates: list[str] = []
    awards: list[str] = []


class TemplateDef(BaseModel):
    id: str
    name: str
    sections: list[str]


class JdFile(BaseModel):
    version: int
    roles: dict[str, list[str]]


class RuleDef(BaseModel):
    id: str
    name: str
    severity: Literal["high", "medium", "low"]
    rewritable: bool


class Thresholds(BaseModel):
    min_bullet_chars: int = 10
    max_bullet_chars: int = 60
    min_preserve_ratio: float = 0.35
    keyword_coverage_warn: float = 0.5


class RulesFile(BaseModel):
    version: int
    thresholds: Thresholds
    rules: list[RuleDef]


class MockStudent(BaseModel):
    id: str
    name: str
    gender: str = ""
    major: str = ""
    degree: str = ""
    school: str = ""
    college: str = ""
    class_name: str = ""
    hometown: str = ""
    major_direction: str = ""
    job_category: str = ""
    phone: str = ""
    email: str = ""
    enroll_year: str = ""
    grad_year: str = ""


class MockUser(BaseModel):
    id: str
    name: str
    role: Literal["counselor", "student", "admin"]
    student_scope: list[str] = []


class IdentityFile(BaseModel):
    mode: str = "mock"
    default_user: str
    users: dict[str, MockUser]


class MockBundle(BaseModel):
    students: dict[str, MockStudent]
    academic: dict[str, AcademicEntry]
    experiences: ExperienceFile
    pools: ProfilePools
    templates: dict[str, TemplateDef]
    jd: JdFile
    rules: RulesFile
    identity: IdentityFile
    manifest: dict = {}
