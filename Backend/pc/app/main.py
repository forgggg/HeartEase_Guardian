from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import errors
from .api import router
from .config import settings
from .data.mock_store import load as load_mock
from .logging_setup import REQUEST_ID, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    current = settings()
    load_mock()  # 坏 mock 文件在启动时直接失败
    if current.data_mode not in {"auto", "real", "mock"}:
        raise RuntimeError(f"DATA_MODE 非法：{current.data_mode}")
    if current.app_env == "prod" and current.identity_mode == "mock":
        raise RuntimeError("生产环境禁止 IDENTITY_MODE=mock（身份会被伪造）")
    if current.store_backend == "mysql":
        from .storage.db import ping

        ping()
    elif current.store_backend != "json":
        raise RuntimeError(f"STORE_BACKEND 非法：{current.store_backend}")
    logger.info(
        "startup",
        extra={
            "data_mode": current.data_mode,
            "identity_mode": current.identity_mode,
            "llm_ready": current.llm_ready,
            "store_backend": current.store_backend,
        },
    )
    yield


app = FastAPI(
    title="鹏程 · 就业指导模块2（简历优化）",
    version="0.3.0",
    description="5.1 简历撰写 + 5.2 简历修改。默认不调用模型；身份通过 X-User-Id 传入。",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "学生", "description": "学生检索与画像（字段级来源：db/mock）"},
        {"name": "简历撰写", "description": "5.1 生成、编辑、版本、导出"},
        {"name": "简历修改", "description": "5.2 上传诊断、逐条建议、采纳/驳回"},
        {"name": "导出", "description": "docx / pdf"},
        {"name": "审计", "description": "操作留痕查询，仅辅导员/管理员"},
        {"name": "元数据", "description": "健康检查、模板、规则清单"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.install(app)


@app.middleware("http")
async def access_log(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
    token = REQUEST_ID.set(request_id)
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-Id"] = request_id
        return response
    except Exception:
        logger.exception(
            "http.error", extra={"method": request.method, "path": request.url.path}
        )
        raise
    finally:
        logger.info(
            "http",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "actor": getattr(request.state, "actor", "-"),
            },
        )
        REQUEST_ID.reset(token)


app.include_router(router)
