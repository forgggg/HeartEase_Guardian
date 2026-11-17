from __future__ import annotations

from typing import Literal

from fastapi import Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from . import audit
from .config import settings
from .data.mock_store import load
from .errors import AppError

api_key = APIKeyHeader(
    name="X-User-Id",
    auto_error=False,
    description="演示身份：teacher_001（全量）/ teacher_002（前缀范围）/ student_001（仅本人）",
)


class CurrentUser(BaseModel):
    id: str
    name: str
    role: Literal["counselor", "student", "admin"]
    scope: list[str] = []


def get_current_user(
    request: Request, key: str | None = Security(api_key)
) -> CurrentUser:
    if settings().identity_mode.lower() == "off":
        user = CurrentUser(id="anonymous", name="匿名", role="admin", scope=["*"])
        request.state.actor = user.id
        return user

    bundle = load().identity
    uid = key or settings().default_user or bundle.default_user
    found = bundle.users.get(uid)
    if found is None:
        audit.record(
            actor=uid,
            action=audit.AUTH_DENIED,
            target_type="auth",
            target_id=uid,
            detail={"code": "UNKNOWN_USER"},
        )
        raise AppError(
            401,
            "UNKNOWN_USER",
            f"未知身份：{uid}",
            "可用身份见 data/mock/identity.json",
        )

    user = CurrentUser(id=found.id, name=found.name, role=found.role, scope=found.student_scope)
    request.state.actor = user.id
    return user


def can_access(user: CurrentUser, student_id: str) -> bool:
    if "*" in user.scope:
        return True
    return any(student_id.startswith(prefix) for prefix in user.scope)


def require_access(user: CurrentUser, student_id: str) -> None:
    if can_access(user, student_id):
        return
    audit.record(
        actor=user.id,
        action=audit.AUTH_DENIED,
        target_type="student",
        target_id=student_id,
        detail={"code": "FORBIDDEN_STUDENT"},
    )
    raise AppError(
        403,
        "FORBIDDEN_STUDENT",
        f"{user.name} 无权查看学生 {student_id}",
        "辅导员只能查看 student_scope 覆盖的学生",
    )


def require_auditor(user: CurrentUser) -> None:
    if user.role in ("counselor", "admin"):
        return
    audit.record(
        actor=user.id,
        action=audit.AUTH_DENIED,
        target_type="audit",
        target_id=user.id,
        detail={"code": "FORBIDDEN_AUDIT"},
    )
    raise AppError(
        403,
        "FORBIDDEN_AUDIT",
        "仅辅导员/管理员可查询审计日志",
    )
