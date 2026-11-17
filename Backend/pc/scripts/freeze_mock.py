"""一次性冻结 mock 数据：把身份与学业数据写入 data/mock/，之后运行时不依赖随机数。

用法：.venv/bin/python scripts/freeze_mock.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

PC_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = PC_DIR.parent.parent
sys.path.insert(0, str(PC_DIR))

from app.data.mocks import build_mock  # noqa: E402
from app.data.xlsx import read_rows  # noqa: E402
from app.models import StudentProfile  # noqa: E402

MOCK_DIR = REPO_DIR / "data" / "mock"
SOURCE = REPO_DIR / "data" / "就业.xlsx"

IDENTITY = {
    "id": "学号",
    "name": "姓名",
    "gender": "性别",
    "major": "专业",
    "degree": "学历",
    "school": "院校名称",
    "college": "所在院系",
    "class_name": "所在班级",
    "hometown": "生源所在地",
    "major_direction": "专业方向",
    "job_category": "工作职位类别",
    "phone": "手机号码",
    "email": "电子邮箱",
    "enroll_year": "入学时间",
    "grad_year": "毕业时间",
}


def main() -> None:
    rows = [r for r in read_rows(SOURCE) if r.get("学号")]
    MOCK_DIR.mkdir(parents=True, exist_ok=True)

    students: dict[str, dict] = {}
    academic: dict[str, dict] = {}

    for row in rows:
        sid = row["学号"]
        identity = {field: row.get(column, "") for field, column in IDENTITY.items()}
        identity["enroll_year"] = identity["enroll_year"][:4]
        identity["grad_year"] = identity["grad_year"][:4]
        students[sid] = identity

        student = StudentProfile(**identity)
        mock = build_mock(student)
        academic[sid] = {
            "gpa": mock["gpa"],
            "rank": mock["rank"],
            "cet4": mock["cet4"],
            "cet6": mock["cet6"],
            "courses": [c.model_dump() for c in mock["courses"]],
        }

    (MOCK_DIR / "students.json").write_text(
        json.dumps(students, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MOCK_DIR / "academic.json").write_text(
        json.dumps(academic, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "version": 1,
        "generated_at": date.today().isoformat(),
        "data_as_of": "2026-11-16",
        "source_file": SOURCE.name,
        "students": len(students),
        "note": "students/academic 由 freeze_mock.py 冻结；覆盖字段见 app/data/source.py REAL_FIELDS",
    }
    (MOCK_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"frozen {len(students)} students -> {MOCK_DIR}")


if __name__ == "__main__":
    main()
