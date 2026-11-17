from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["db", "mock", "derived", "llm", "manual"]


class Bullet(BaseModel):
    text: str
    source: Source = "mock"


class Experience(BaseModel):
    title: str
    org: str = ""
    start: str = ""
    end: str = ""
    bullets: list[Bullet] = []


class Course(BaseModel):
    name: str
    score: float
    credit: float = 0.0


class StudentBrief(BaseModel):
    id: str
    name: str
    major: str = ""
    degree: str = ""
    class_name: str = ""


class StudentProfile(BaseModel):
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
    gpa: float | None = None
    rank: str = ""
    cet4: int | None = None
    cet6: int | None = None
    courses: list[Course] = []
    skills: list[str] = []
    projects: list[Experience] = []
    internships: list[Experience] = []
    certificates: list[str] = []
    awards: list[str] = []
    sources: dict[str, Source] = {}


class Education(BaseModel):
    school: str = ""
    major: str = ""
    degree: str = ""
    start: str = ""
    end: str = ""
    gpa: str = ""
    rank: str = ""
    courses: list[str] = []


class ResumeDoc(BaseModel):
    id: str = ""
    student_id: str = ""
    template: str = ""
    target_role: str = ""
    name: str = ""
    gender: str = ""
    phone: str = ""
    email: str = ""
    summary: str = ""
    education: Education | None = None
    skills: list[str] = []
    projects: list[Experience] = []
    internships: list[Experience] = []
    certificates: list[str] = []
    awards: list[str] = []
    sources: dict[str, Source] = {}
    version: int = 1
    confirmed: bool = False
    needs_review: bool = False
    created_by: str = ""
    created_at: str = ""


class Finding(BaseModel):
    rule: str
    name: str
    severity: Literal["high", "medium", "low"] = "medium"
    original: str
    evidence: str = ""


class Suggestion(BaseModel):
    id: str = ""
    rule: str
    rules: list[str] = []
    original: str
    revised: str
    reason: str
    accepted: bool | None = None
    decided_by: str | None = None
    decided_at: str | None = None


class QualityReport(BaseModel):
    score: int = 100
    keyword_coverage: float = 0.0
    missing_keywords: list[str] = []
    findings: int = 0
    rules_version: int = 0


class Analysis(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "anl_20261117161200_9f8e7d",
                    "student_id": "202210700001",
                    "filename": "resume_bad.docx",
                    "target_role": "Java 后端开发工程师",
                    "original_text": "负责用户调研并输出需求文档\n联系电话 13800138000",
                    "revised_text": "主导用户调研并输出需求文档\n联系电话 ",
                    "findings": [
                        {
                            "rule": "R2",
                            "name": "弱动词开头",
                            "severity": "medium",
                            "original": "负责用户调研并输出需求文档",
                            "evidence": "以弱动词开头，改为动作动词并补结果",
                        }
                    ],
                    "suggestions": [
                        {
                            "id": "s1",
                            "rule": "R2",
                            "rules": ["R1", "R2"],
                            "original": "负责用户调研并输出需求文档",
                            "revised": "主导用户调研并输出需求文档",
                            "reason": "动词开头，结果前置",
                            "accepted": None,
                            "decided_by": None,
                            "decided_at": None,
                        }
                    ],
                    "quality": {
                        "score": 46,
                        "keyword_coverage": 0.17,
                        "missing_keywords": ["Spring", "MySQL", "Redis"],
                        "findings": 7,
                        "rules_version": 1,
                    },
                    "created_by": "teacher_001",
                    "created_at": "2026-11-17T16:12:00",
                }
            ]
        }
    )
    id: str = ""
    student_id: str = ""
    filename: str = ""
    target_role: str = ""
    original_text: str = ""
    revised_text: str = ""
    findings: list[Finding] = []
    suggestions: list[Suggestion] = []
    quality: QualityReport | None = None
    created_by: str = ""
    created_at: str = ""


class VersionRecord(BaseModel):
    version: int
    created_at: str
    created_by: str
    note: str = ""
    confirmed: bool = False
    doc: ResumeDoc


class VersionSummary(BaseModel):
    version: int
    created_at: str
    created_by: str = ""
    note: str = ""
    confirmed: bool = False


class ResumePatch(BaseModel):
    target_role: str | None = None
    summary: str | None = None
    skills: list[str] | None = None
    projects: list[Experience] | None = None
    internships: list[Experience] | None = None
    certificates: list[str] | None = None
    awards: list[str] | None = None
    note: str = ""
    confirm: bool = False


class DecisionRequest(BaseModel):
    reason: str = ""


class Health(BaseModel):
    status: str
    llm_ready: bool
    polish_enabled: bool
    model: str
    data_mode: str
    store_backend: str = "json"
    students: int


class Template(BaseModel):
    id: str
    name: str
    sections: list[str]


class WriteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "resume_id": "res_20261117161000_ab12cd",
                    "template": {
                        "id": "tech",
                        "name": "技术岗 · 单页",
                        "sections": ["education", "skills", "projects", "internships", "certificates", "awards"],
                    },
                    "doc": {
                        "id": "res_20261117161000_ab12cd",
                        "student_id": "202210700001",
                        "template": "tech",
                        "target_role": "Java 后端开发工程师",
                        "name": "张晨",
                        "gender": "男",
                        "phone": "138****0001",
                        "email": "graduate001@example.com",
                        "summary": "",
                        "education": {
                            "school": "西安理工大学",
                            "major": "计算机科学与技术",
                            "degree": "本科",
                            "start": "2022.09",
                            "end": "2026.06",
                            "gpa": "3.57/4.0",
                            "rank": "28/96",
                            "courses": ["Java 程序设计", "软件工程", "机器学习基础"],
                        },
                        "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Docker", "Git"],
                        "projects": [
                            {
                                "title": "校园二手交易平台",
                                "org": "课程设计",
                                "start": "",
                                "end": "",
                                "bullets": [
                                    {
                                        "text": "基于 Spring Boot + Vue 实现商品发布、检索与订单流程，覆盖 3 个学院 1200+ 注册用户",
                                        "source": "mock",
                                    }
                                ],
                            }
                        ],
                        "internships": [],
                        "certificates": ["CET-4 528", "软件设计师（中级）"],
                        "awards": ["校级一等奖学金"],
                        "sources": {"name": "db", "gpa": "mock", "summary": "derived"},
                        "version": 1,
                        "confirmed": False,
                        "needs_review": False,
                        "created_by": "teacher_001",
                        "created_at": "2026-11-17T16:10:00",
                    },
                    "llm_ready": True,
                    "llm_used": False,
                }
            ]
        }
    )
    resume_id: str
    template: Template
    doc: ResumeDoc
    llm_ready: bool
    llm_used: bool


class AuditRecord(BaseModel):
    id: str
    ts: str
    actor: str
    action: str
    target_type: str
    target_id: str
    detail: dict = {}
    request_id: str = ""


class AuditPage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total": 2,
                    "items": [
                        {
                            "id": "aud_20261117161200_1a2b3c",
                            "ts": "2026-11-17T16:12:00",
                            "actor": "teacher_001",
                            "action": "resume.patch",
                            "target_type": "resume",
                            "target_id": "res_20261117161000_ab12cd",
                            "detail": {"version": 2, "note": "人工改稿", "confirmed": True},
                            "request_id": "d7ef09695b05",
                        },
                        {
                            "id": "aud_20261117161000_4d5e6f",
                            "ts": "2026-11-17T16:10:00",
                            "actor": "teacher_001",
                            "action": "resume.create",
                            "target_type": "resume",
                            "target_id": "res_20261117161000_ab12cd",
                            "detail": {"template": "tech", "target_role": "Java 后端开发工程师", "llm_used": False},
                            "request_id": "2296048a219a",
                        },
                    ],
                }
            ]
        }
    )
    total: int
    items: list[AuditRecord] = []


class RuleCatalog(BaseModel):
    version: int
    rules: list[dict] = Field(default_factory=list)
    thresholds: dict = Field(default_factory=dict)
    jd_version: int = 0
