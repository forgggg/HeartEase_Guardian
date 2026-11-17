from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import settings
from .data import source
from . import audit
from .errors import AppError, error_responses
from .identity import CurrentUser, can_access, get_current_user, require_access, require_auditor
from .models import (
    Analysis,
    AuditPage,
    DecisionRequest,
    Health,
    ResumeDoc,
    ResumePatch,
    RuleCatalog,
    StudentBrief,
    StudentProfile,
    Template,
    VersionSummary,
    WriteResponse,
)
from .resume import polish, render, store
from .resume.assemble import assemble
from .resume.parse import extract_text
from .resume.rules import (
    JD_VERSION,
    RULE_META,
    RULE_VERSION,
    THRESHOLDS,
    analyze,
    evaluate,
)
from .resume.suggest import apply_to_text, for_findings
from .resume.templates import TEMPLATES, pick_template

router = APIRouter()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class WriteRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "student_id": "202210700001",
                    "template_id": "general",
                    "target_role": "Java 后端开发工程师",
                }
            ]
        }
    )

    student_id: str = Field(description="学号，例如 202210700001")
    template_id: str | None = Field(
        default=None, description="tech / general / soe，留空按岗位自动匹配"
    )
    target_role: str | None = Field(
        default=None, description="目标岗位，留空按专业方向推断"
    )


SSE_RESPONSES = {
    200: {
        "description": (
            "Server-Sent Events。每条消息格式为 `event: <name>\\ndata: <json>\\n\\n`。"
            "撰写流：stage(load) → stage(assemble) → done；"
            "修改流：stage(diagnose) → finding×n → stage(suggest) → suggestion×n → done。"
        ),
        "content": {
            "text/event-stream": {
                "schema": {"type": "string", "description": "SSE 原始事件流"},
                "examples": {
                    "write_stream": {
                        "summary": "撰写流",
                        "value": (
                            'event: stage\ndata: {"stage": "load"}\n\n'
                            'event: stage\ndata: {"stage": "assemble"}\n\n'
                            'event: done\ndata: {"resume_id": "res_20261117161000_ab12cd", '
                            '"template": {"id": "tech", "name": "技术岗 · 单页", "sections": []}, '
                            '"llm_used": false}\n\n'
                        ),
                    },
                    "revise_stream": {
                        "summary": "修改流",
                        "value": (
                            'event: stage\ndata: {"stage": "diagnose"}\n\n'
                            'event: finding\ndata: {"rule": "R2", "name": "弱动词开头", '
                            '"severity": "medium", "original": "负责用户调研并输出需求文档", '
                            '"evidence": "以弱动词开头"}\n\n'
                            'event: stage\ndata: {"stage": "suggest"}\n\n'
                            'event: suggestion\ndata: {"id": "s1", "rule": "R2", '
                            '"original": "负责用户调研并输出需求文档", '
                            '"revised": "主导用户调研并输出需求文档", "reason": "动词开头"}\n\n'
                            'event: done\ndata: {"id": "anl_20261117161200_9f8e7d", '
                            '"revised_text": "主导用户调研并输出需求文档", '
                            '"quality": {"score": 46}}\n\n'
                        ),
                    },
                },
            }
        },
    }
}


def _profile(student_id: str) -> StudentProfile:
    try:
        return source.profile(student_id)
    except KeyError:
        raise AppError(404, "STUDENT_NOT_FOUND", f"学生不存在：{student_id}")


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_write(req: WriteRequest, user: CurrentUser) -> WriteResponse:
    require_access(user, req.student_id)
    student = _profile(req.student_id)
    role = (req.target_role or "").strip() or source.target_role_hint(student)
    template_id = pick_template(role, req.template_id)
    resume_id = store.new_id("res")

    doc = assemble(student, template_id, role, resume_id)
    doc.created_by = user.id
    doc, used = polish.apply(doc)

    store.create_doc(doc, "初始生成")
    audit.record(
        user.id,
        audit.RESUME_CREATE,
        "resume",
        resume_id,
        {"template": template_id, "target_role": role, "llm_used": used},
    )
    return WriteResponse(
        resume_id=resume_id,
        template=Template(**TEMPLATES[template_id]),
        doc=doc,
        llm_ready=settings().llm_ready,
        llm_used=used,
    )


def _build_analysis(
    text: str,
    target_role: str,
    filename: str,
    user: CurrentUser,
    student_id: str = "",
    findings=None,
    suggestions=None,
) -> Analysis:
    findings = analyze(text, target_role) if findings is None else findings
    suggestions = for_findings(findings, target_role) if suggestions is None else suggestions
    quality = evaluate(findings, target_role, text)

    analysis = Analysis(
        id=store.new_id("anl"),
        student_id=student_id,
        filename=filename,
        target_role=target_role,
        original_text=text,
        revised_text=apply_to_text(text, suggestions),
        findings=findings,
        suggestions=suggestions,
        quality=quality,
        created_by=user.id,
        created_at=store.now(),
    )
    store.save_analysis(analysis)
    audit.record(
        user.id,
        audit.RESUME_REVISE,
        "analysis",
        analysis.id,
        {
            "filename": filename,
            "target_role": target_role,
            "findings": len(findings),
            "suggestions": len(suggestions),
            "score": quality.score,
        },
    )
    return analysis


@router.get("/health", response_model=Health, tags=["元数据"], summary="健康检查")
def health() -> Health:
    return Health(
        status="ok",
        llm_ready=settings().llm_ready,
        polish_enabled=polish.enabled(),
        model=settings().llm_model if settings().llm_ready else "fake",
        data_mode=source.mode(),
        store_backend=settings().store_backend,
        students=len(source.all_students()),
    )


@router.get(
    "/students",
    response_model=list[StudentBrief],
    tags=["学生"],
    summary="学生检索（姓名/学号/专业/班级）",
    responses=error_responses(503),
)
def list_students(q: str = "", user: CurrentUser = Depends(get_current_user)):
    return [s for s in source.search(q) if can_access(user, s.id)]


@router.get(
    "/students/{student_id}",
    response_model=StudentProfile,
    tags=["学生"],
    summary="学生画像（含每字段来源 db/mock）",
    responses=error_responses(403, 404, 503),
)
def get_student(student_id: str, user: CurrentUser = Depends(get_current_user)):
    require_access(user, student_id)
    profile = _profile(student_id)
    audit.record(user.id, audit.STUDENT_VIEW, "student", student_id)
    return profile


@router.get(
    "/resume/templates",
    response_model=list[Template],
    tags=["元数据"],
    summary="简历模板列表",
)
def list_templates() -> list[Template]:
    return [Template(**item) for item in TEMPLATES.values()]


@router.post(
    "/resume/write",
    response_model=WriteResponse,
    tags=["简历撰写"],
    summary="5.1 按学生信息生成简历（默认不调用模型）",
    responses=error_responses(403, 404, 503),
)
def write_resume(req: WriteRequest, user: CurrentUser = Depends(get_current_user)):
    return _build_write(req, user)


@router.post(
    "/resume/write/stream",
    tags=["简历撰写"],
    summary="5.1 流式生成（SSE）",
    response_class=StreamingResponse,
    responses={**SSE_RESPONSES, **error_responses(403, 404, 503)},
)
def write_resume_stream(req: WriteRequest, user: CurrentUser = Depends(get_current_user)):
    def events():
        yield _sse("stage", {"stage": "load"})
        require_access(user, req.student_id)
        student = _profile(req.student_id)
        yield _sse("stage", {"stage": "assemble"})
        result = _build_write(req, user)
        yield _sse("done", result.model_dump())

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post(
    "/resume/revise",
    response_model=Analysis,
    tags=["简历修改"],
    summary="5.2 上传简历并逐条给出修改建议",
    responses=error_responses(403, 415, 422),
)
def revise_resume(
    file: UploadFile = File(..., description="文本型 .pdf / .docx，≤8MB"),
    target_role: str = Form(
        "", description="目标岗位", examples=["Java 后端开发工程师"]
    ),
    student_id: str = Form(
        "", description="可选：关联学生，用于权限校验", examples=["202210700001"]
    ),
    user: CurrentUser = Depends(get_current_user),
):
    if student_id:
        require_access(user, student_id)
    raw = file.file.read()
    text = extract_text(file.filename or "", raw)
    upload_id = store.save_upload(file.filename or "resume", raw, user.id)
    analysis = _build_analysis(text, target_role, file.filename or "", user, student_id)
    store.attach_upload(upload_id, analysis.id)
    return analysis


@router.post(
    "/resume/revise/stream",
    tags=["简历修改"],
    summary="5.2 流式修改（SSE：stage/finding/suggestion/done）",
    response_class=StreamingResponse,
    responses={**SSE_RESPONSES, **error_responses(403, 415, 422)},
)
def revise_resume_stream(
    file: UploadFile = File(...),
    target_role: str = Form(""),
    student_id: str = Form(""),
    user: CurrentUser = Depends(get_current_user),
):
    if student_id:
        require_access(user, student_id)
    raw = file.file.read()
    text = extract_text(file.filename or "", raw)
    upload_id = store.save_upload(file.filename or "resume", raw, user.id)

    def events():
        yield _sse("stage", {"stage": "diagnose"})
        findings = analyze(text, target_role)
        for finding in findings:
            yield _sse("finding", finding.model_dump())
        yield _sse("stage", {"stage": "suggest"})
        suggestions = for_findings(findings, target_role)
        for suggestion in suggestions:
            yield _sse("suggestion", suggestion.model_dump())
        analysis = _build_analysis(
            text,
            target_role,
            file.filename or "",
            user,
            student_id,
            findings=findings,
            suggestions=suggestions,
        )
        store.attach_upload(upload_id, analysis.id)
        yield _sse("done", analysis.model_dump())

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get(
    "/resume/rules",
    response_model=RuleCatalog,
    tags=["元数据"],
    summary="诊断规则与阈值（含版本号）",
)
def list_rules() -> RuleCatalog:
    return RuleCatalog(
        version=RULE_VERSION,
        rules=[meta.model_dump() for meta in RULE_META.values()],
        thresholds=THRESHOLDS.model_dump(),
        jd_version=JD_VERSION,
    )


@router.get(
    "/audit",
    response_model=AuditPage,
    tags=["审计"],
    summary="审计日志查询（操作人/动作/对象/时间/分页）",
    responses=error_responses(403),
)
def list_audit(
    actor: str = Query("", description="操作人 ID", examples=["teacher_001"]),
    action: str = Query(
        "", description="动作", examples=["resume.patch", "auth.denied"]
    ),
    target_id: str = Query(
        "", description="对象 ID（简历/分析/学号）", examples=["res_20261117161000_ab12cd"]
    ),
    since: str = Query("", description="起始时间，ISO 前缀", examples=["2026-11-17"]),
    until: str = Query("", description="截止时间，ISO 前缀", examples=["2026-11-18"]),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> AuditPage:
    require_auditor(user)
    return audit.query(
        actor=actor,
        action=action,
        target_id=target_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/resume/{resume_id}",
    response_model=ResumeDoc | Analysis,
    tags=["简历撰写"],
    summary="读取简历或修改记录",
    responses=error_responses(404),
)
def get_resume(resume_id: str, user: CurrentUser = Depends(get_current_user)):
    doc = store.load_doc(resume_id)
    if doc is not None:
        require_access(user, doc.student_id)
        return doc
    analysis = store.load_analysis(resume_id)
    if analysis is not None:
        if analysis.student_id:
            require_access(user, analysis.student_id)
        return analysis
    raise AppError(404, "RESUME_NOT_FOUND", "记录不存在")


@router.patch(
    "/resume/{resume_id}",
    response_model=ResumeDoc,
    tags=["简历撰写"],
    summary="人工编辑（生成新版本，记录操作人）",
    responses=error_responses(403, 404, 409),
)
def patch_resume(
    resume_id: str,
    patch: ResumePatch,
    user: CurrentUser = Depends(get_current_user),
):
    doc = store.load_doc(resume_id)
    if doc is None:
        raise AppError(404, "RESUME_NOT_FOUND", "简历不存在")
    require_access(user, doc.student_id)

    updated = doc.model_copy(deep=True)
    for field in (
        "target_role",
        "summary",
        "skills",
        "projects",
        "internships",
        "certificates",
        "awards",
    ):
        value = getattr(patch, field)
        if value is not None:
            setattr(updated, field, value)
            updated.sources[field] = "manual"

    updated.version = doc.version + 1
    updated.confirmed = patch.confirm or doc.confirmed
    updated.created_by = user.id
    updated.created_at = store.now()

    if not store.save_edit(updated, doc.version, patch.note or "人工编辑"):
        raise AppError(
            409,
            "VERSION_CONFLICT",
            f"简历已被修改（当前版本 {doc.version}）",
            "请重新读取最新版本后再提交",
        )
    audit.record(
        user.id,
        audit.RESUME_PATCH,
        "resume",
        resume_id,
        {"version": updated.version, "note": patch.note, "confirmed": updated.confirmed},
    )
    return updated


@router.get(
    "/resume/{resume_id}/versions",
    response_model=list[VersionSummary],
    tags=["简历撰写"],
    summary="版本历史",
    responses=error_responses(403, 404),
)
def get_versions(resume_id: str, user: CurrentUser = Depends(get_current_user)):
    records = store.load_versions(resume_id)
    if not records:
        raise AppError(404, "RESUME_NOT_FOUND", "暂无版本记录")
    require_access(user, records[-1].doc.student_id)
    return [
        VersionSummary(
            version=r.version,
            created_at=r.created_at,
            created_by=r.created_by,
            note=r.note,
            confirmed=r.confirmed,
        )
        for r in records
    ]


def _decide(
    resume_id: str, suggestion_id: str, accept: bool, reason: str, user: CurrentUser
) -> Analysis:
    analysis = store.load_analysis(resume_id)
    if analysis is None:
        raise AppError(404, "RESUME_NOT_FOUND", "修改记录不存在")
    if analysis.student_id:
        require_access(user, analysis.student_id)

    target = next((s for s in analysis.suggestions if s.id == suggestion_id), None)
    if target is None:
        raise AppError(404, "SUGGESTION_NOT_FOUND", f"建议不存在：{suggestion_id}")

    target.accepted = accept
    target.decided_by = user.id
    target.decided_at = store.now()
    if not accept and reason:
        target.reason = f"{target.reason}（驳回理由：{reason}）"

    analysis.revised_text = apply_to_text(analysis.original_text, analysis.suggestions)
    store.save_analysis(analysis)
    audit.record(
        user.id,
        audit.SUGGESTION_ACCEPT if accept else audit.SUGGESTION_REJECT,
        "suggestion",
        resume_id,
        {
            "suggestion_id": target.id,
            "rule": target.rule,
            "reason": reason,
            "changed": target.revised != target.original,
        },
    )
    return analysis


@router.post(
    "/resume/{resume_id}/suggestions/{suggestion_id}/accept",
    response_model=Analysis,
    tags=["简历修改"],
    summary="采纳建议并重算美化稿",
    responses=error_responses(403, 404),
)
def accept_suggestion(
    resume_id: str,
    suggestion_id: str,
    body: DecisionRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return _decide(resume_id, suggestion_id, True, (body.reason if body else ""), user)


@router.post(
    "/resume/{resume_id}/suggestions/{suggestion_id}/reject",
    response_model=Analysis,
    tags=["简历修改"],
    summary="驳回建议并重算美化稿",
    responses=error_responses(403, 404),
)
def reject_suggestion(
    resume_id: str,
    suggestion_id: str,
    body: DecisionRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    return _decide(resume_id, suggestion_id, False, (body.reason if body else ""), user)


@router.get(
    "/resume/{resume_id}/export",
    tags=["导出"],
    summary="导出 docx / pdf",
    response_class=Response,
    responses={
        200: {
            "description": "简历文件",
            "content": {"application/pdf": {}, DOCX_MIME: {}},
        },
        **error_responses(403, 404),
    },
)
def export_resume(
    resume_id: str,
    format: Literal["docx", "pdf"] = Query("docx", description="导出格式"),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    doc = store.load_doc(resume_id)
    if doc is not None:
        require_access(user, doc.student_id)
        blocks, title = render.blocks_from_doc(doc), doc.name
    else:
        analysis = store.load_analysis(resume_id)
        if analysis is None:
            raise AppError(404, "RESUME_NOT_FOUND", "记录不存在")
        if analysis.student_id:
            require_access(user, analysis.student_id)
        blocks, title = render.blocks_from_text(analysis.revised_text), "简历（美化稿）"

    if format == "docx":
        content, media = render.docx_from_blocks(blocks), DOCX_MIME
    else:
        content, media = render.pdf_from_blocks(blocks, title), "application/pdf"

    audit.record(
        user.id,
        audit.RESUME_EXPORT,
        "resume" if doc is not None else "analysis",
        resume_id,
        {"format": format},
    )

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{resume_id}.{format}"'},
    )
