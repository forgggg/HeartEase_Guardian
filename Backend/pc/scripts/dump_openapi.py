"""导出冻结的 OpenAPI 契约。

用法：
  .venv/bin/python scripts/dump_openapi.py          # 写入 openapi.json
  .venv/bin/python scripts/dump_openapi.py --check  # 与文件比较，漂移则退出码 1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PC_DIR))

from app.main import app  # noqa: E402

OUT = PC_DIR / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    expected = render()
    if "--check" in sys.argv:
        if not OUT.exists():
            print(f"{OUT} 不存在，请先运行 dump_openapi.py")
            return 1
        if OUT.read_text(encoding="utf-8") != expected:
            print("OpenAPI 契约与实现不一致，请重新生成 openapi.json")
            return 1
        print("OpenAPI 契约一致")
        return 0

    OUT.write_text(expected, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
