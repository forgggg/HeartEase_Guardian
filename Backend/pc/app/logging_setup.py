"""结构化日志：stdout + var/logs/app.log，每条带 request_id。"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import PC_DIR, settings

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")

_EXTRA_KEYS = (
    "request_id",
    "actor",
    "method",
    "path",
    "status",
    "duration_ms",
    "model",
    "input_tokens",
    "output_tokens",
    "action",
    "target_type",
    "target_id",
    "error",
    "data_mode",
    "identity_mode",
    "llm_ready",
    "store_backend",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings().log_level.upper(), logging.INFO))
    formatter = JsonFormatter()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    root.addHandler(stream)

    log_file = settings().log_file.strip()
    if log_file:
        path = Path(log_file)
        if not path.is_absolute():
            path = PC_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _configured = True
