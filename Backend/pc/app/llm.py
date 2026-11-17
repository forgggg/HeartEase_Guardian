from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .config import settings

logger = logging.getLogger(__name__)


def build_llm() -> BaseChatModel:
    """OpenAI 兼容客户端；未配置 key 时上层走 fallback，不会构造模型。"""
    from langchain_openai import ChatOpenAI

    s = settings()
    headers = {"User-Agent": s.llm_client_name}
    if s.llm_session_header and s.llm_session_id:
        headers[s.llm_session_header] = s.llm_session_id
    return ChatOpenAI(
        model=s.llm_model,
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
        temperature=s.llm_temperature,
        timeout=60,
        default_headers=headers,
    )


def _extract_json(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("模型输出不含 JSON")
    return json.loads(text[start : end + 1])


def complete_json(system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
    """一次模型调用 → JSON。离线返回 _fallback，调用失败返回 _error，均保留原始 fallback。"""
    s = settings()
    if not s.llm_ready:
        return {**fallback, "_fallback": True}

    start = time.perf_counter()
    try:
        msg = build_llm().invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        usage = getattr(msg, "usage_metadata", None) or {}
        logger.info(
            "llm.call",
            extra={
                "model": s.llm_model,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            },
        )
        return _extract_json(str(msg.content))
    except Exception as exc:
        logger.warning(
            "llm.error",
            extra={
                "model": s.llm_model,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "error": f"{type(exc).__name__}: {str(exc)[:160]}",
            },
        )
        return {**fallback, "_error": f"{type(exc).__name__}: {str(exc)[:160]}"}
