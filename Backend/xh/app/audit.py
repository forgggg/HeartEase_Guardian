from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_lock = threading.Lock()


def record_audit(
    var_dir: Path,
    actor: str,
    action: str,
    target: str,
    input_summary: dict,
    output_summary: dict,
) -> None:
    path = var_dir / "audit" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "actor": actor,
        "action": action,
        "target": target,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _lock, path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
