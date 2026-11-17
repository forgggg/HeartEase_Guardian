from __future__ import annotations

from functools import lru_cache

from ..config import settings
from ..errors import AppError
from ..models import StudentBrief, StudentProfile
from .mock_store import load
from .mocks import build_mock
from .xlsx import read_rows

EMPLOYMENT_FILE = "就业.xlsx"

# 就业.xlsx → 画像字段（白名单：身份证、家庭住址等一律不取）
REAL_FIELDS = {
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

ROLE_HINTS = {
    "后端": "Java 后端开发工程师",
    "前端": "前端开发工程师",
    "数据": "数据分析工程师",
    "测试": "测试开发工程师",
    "算法": "算法工程师",
    "产品": "产品经理",
}


def mode() -> str:
    value = settings().data_mode.strip().lower()
    if value not in {"auto", "real", "mock"}:
        raise AppError(
            500, "BAD_CONFIG", f"DATA_MODE 取值非法：{value}", "仅支持 auto / real / mock"
        )
    return value


@lru_cache
def _xlsx_rows() -> dict[str, dict[str, str]]:
    path = settings().data_dir / EMPLOYMENT_FILE
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    for row in read_rows(path):
        sid = row.get("学号")
        if not sid:
            continue
        data = {field: row.get(column, "") for field, column in REAL_FIELDS.items()}
        data["enroll_year"] = data["enroll_year"][:4]
        data["grad_year"] = data["grad_year"][:4]
        out[sid] = data
    return out


def _mock_rows() -> dict[str, dict[str, str]]:
    return {sid: student.model_dump() for sid, student in load().students.items()}


def _base(current: str) -> dict[str, dict[str, str]]:
    if current == "mock":
        return _mock_rows()
    rows = dict(_xlsx_rows())
    if rows:
        return rows
    if current == "auto":
        return _mock_rows()
    return {}


def all_students() -> list[StudentBrief]:
    return [
        StudentBrief(
            id=row["id"],
            name=row.get("name", ""),
            major=row.get("major", ""),
            degree=row.get("degree", ""),
            class_name=row.get("class_name", ""),
        )
        for row in _base(mode()).values()
    ]


def search(query: str = "") -> list[StudentBrief]:
    q = query.strip()
    items = all_students()
    if not q:
        return items
    return [
        s for s in items if q in s.id or q in s.name or q in s.major or q in s.class_name
    ]


def profile(student_id: str) -> StudentProfile:
    current = mode()
    row = _base(current).get(student_id)
    if row is None:
        raise KeyError(student_id)

    student = StudentProfile(**row)
    student.sources = {
        field: ("mock" if current == "mock" else "db") for field in REAL_FIELDS
    }

    if current == "real":
        raise AppError(
            503,
            "DATA_UNAVAILABLE",
            f"学生 {student_id} 缺学业/经历数据",
            "当前未接入真实学业库；改用 DATA_MODE=auto 或 mock 可继续演示",
        )

    mock = build_mock(student)
    for field, value in mock.items():
        setattr(student, field, value)
        student.sources[field] = "mock"

    return student


def target_role_hint(student: StudentProfile) -> str:
    direction = student.major_direction or student.job_category
    for key, role in ROLE_HINTS.items():
        if key in direction:
            return role
    return "软件工程师"
