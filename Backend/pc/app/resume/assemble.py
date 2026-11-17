from __future__ import annotations

from datetime import datetime

from ..models import Course, Education, ResumeDoc, StudentProfile
from .templates import TEMPLATES


def _courses(student: StudentProfile, limit: int = 6) -> list[str]:
    top: list[Course] = sorted(student.courses, key=lambda c: c.score, reverse=True)
    return [c.name for c in top[:limit]]


def _summary(student: StudentProfile) -> str:
    """只用已有事实拼句子，不做任何无来源的形容词堆砌。"""
    parts = [f"{student.major}{student.degree}".strip()]
    if student.gpa:
        parts.append(f"GPA {student.gpa}/4.0")
    if student.rank:
        parts.append(f"专业排名 {student.rank}")
    if student.skills:
        parts.append(f"熟悉 {'、'.join(student.skills[:4])}")
    if student.projects:
        parts.append(f"完成 {len(student.projects)} 个课程/实验室项目")
    if student.internships:
        parts.append(f"具备 {len(student.internships)} 段实习经历")
    return "，".join(p for p in parts if p) + "。"


def _certificates(student: StudentProfile) -> list[str]:
    items = list(student.certificates)
    if student.cet4:
        items.insert(0, f"CET-4 {student.cet4}")
    if student.cet6:
        items.insert(1 if student.cet4 else 0, f"CET-6 {student.cet6}")
    return items


def assemble(
    student: StudentProfile,
    template_id: str,
    target_role: str,
    resume_id: str,
) -> ResumeDoc:
    edu = Education(
        school=student.school,
        major=student.major,
        degree=student.degree,
        start=f"{student.enroll_year}.09" if student.enroll_year else "",
        end=f"{student.grad_year}.06" if student.grad_year else "",
        gpa=f"{student.gpa}/4.0" if student.gpa else "",
        rank=student.rank,
        courses=_courses(student),
    )

    doc = ResumeDoc(
        id=resume_id,
        student_id=student.id,
        template=template_id,
        target_role=target_role,
        name=student.name,
        gender=student.gender,
        phone=student.phone,
        email=student.email,
        summary=_summary(student),
        education=edu,
        skills=list(student.skills),
        projects=list(student.projects),
        internships=list(student.internships),
        certificates=_certificates(student),
        awards=list(student.awards),
        sources=dict(student.sources),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    doc.sources["summary"] = "derived"

    # 模板未包含的板块不输出，保证结构符合所选模板
    allowed = set(TEMPLATES[template_id]["sections"])
    if "summary" not in allowed:
        doc.summary = ""
    return doc
