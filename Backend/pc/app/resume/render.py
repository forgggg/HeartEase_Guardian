from __future__ import annotations

import io
from xml.sax.saxutils import escape

from ..models import Experience, ResumeDoc
from .templates import TEMPLATES


def _join(*parts: str, sep: str = " · ") -> str:
    return sep.join(p for p in parts if p)


def _period(start: str, end: str) -> str:
    return f"{start}–{end}" if start and end else (start or end)


def _experience_blocks(title: str, items: list[Experience]) -> list[tuple[str, str]]:
    if not items:
        return []
    blocks: list[tuple[str, str]] = [("h2", title)]
    for item in items:
        blocks.append(("body", _join(item.title, item.org, _period(item.start, item.end))))
        blocks.extend(("bullet", b.text) for b in item.bullets)
    return blocks


def blocks_from_doc(doc: ResumeDoc) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = [("name", doc.name)]
    contact = _join(
        doc.gender,
        doc.phone,
        doc.email,
        f"求职意向：{doc.target_role}" if doc.target_role else "",
        sep=" | ",
    )
    if contact:
        blocks.append(("contact", contact))

    for section in TEMPLATES[doc.template]["sections"]:
        if section == "summary" and doc.summary:
            blocks += [("h2", "个人概述"), ("body", doc.summary)]
        elif section == "education" and doc.education:
            edu = doc.education
            blocks.append(("h2", "教育背景"))
            blocks.append(("body", _join(edu.school, edu.major, edu.degree, _period(edu.start, edu.end))))
            extra = _join(
                f"GPA {edu.gpa}" if edu.gpa else "",
                f"专业排名 {edu.rank}" if edu.rank else "",
                f"主修课程：{'、'.join(edu.courses)}" if edu.courses else "",
                sep=" | ",
            )
            if extra:
                blocks.append(("body", extra))
        elif section == "skills" and doc.skills:
            blocks += [("h2", "专业技能"), ("body", " / ".join(doc.skills))]
        elif section == "projects":
            blocks += _experience_blocks("项目经历", doc.projects)
        elif section == "internships":
            blocks += _experience_blocks("实习经历", doc.internships)
        elif section == "certificates" and doc.certificates:
            blocks += [("h2", "证书与荣誉"), ("body", " / ".join(doc.certificates))]
        elif section == "awards" and doc.awards:
            blocks += [("h2", "获奖情况"), ("body", " / ".join(doc.awards))]

    return blocks


def docx_from_blocks(blocks: list[tuple[str, str]]) -> bytes:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Pt

    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(10.5)
    normal.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    for kind, text in blocks:
        if kind == "name":
            run = document.add_paragraph().add_run(text)
            run.bold = True
            run.font.size = Pt(20)
        elif kind == "contact":
            run = document.add_paragraph().add_run(text)
            run.font.size = Pt(9.5)
        elif kind == "h2":
            run = document.add_paragraph().add_run(text)
            run.bold = True
            run.font.size = Pt(12)
        elif kind == "bullet":
            document.add_paragraph(text, style="List Bullet")
        else:
            document.add_paragraph(text)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pdf_styles():
    from reportlab.lib.styles import ParagraphStyle

    font = "STSong-Light"
    return {
        "name": ParagraphStyle("name", fontName=font, fontSize=20, leading=26, spaceAfter=4),
        "contact": ParagraphStyle(
            "contact", fontName=font, fontSize=9.5, leading=14, textColor="#444444", spaceAfter=10
        ),
        "h2": ParagraphStyle(
            "h2", fontName=font, fontSize=12, leading=16, spaceBefore=10, spaceAfter=4
        ),
        "body": ParagraphStyle("body", fontName=font, fontSize=10, leading=15, spaceAfter=2),
        "bullet": ParagraphStyle(
            "bullet", fontName=font, fontSize=10, leading=15, leftIndent=10, spaceAfter=2
        ),
    }


def pdf_from_blocks(blocks: list[tuple[str, str]], title: str = "简历") -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = _pdf_styles()

    story = []
    for kind, text in blocks:
        if kind == "bullet":
            story.append(Paragraph("• " + escape(text), styles["bullet"]))
        else:
            story.append(Paragraph(escape(text), styles[kind]))
    if not story:
        story.append(Spacer(1, 1))

    buffer = io.BytesIO()
    SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
    ).build(story)
    return buffer.getvalue()


def blocks_from_text(text: str) -> list[tuple[str, str]]:
    return [("body", line.strip()) for line in text.splitlines() if line.strip()]
