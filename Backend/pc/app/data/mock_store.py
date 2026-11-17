"""data/mock/*.json 的加载与校验：坏文件在启动/首次访问时直接报错，不静默降级。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from ..config import settings
from .mock_schema import (
    AcademicEntry,
    ExperienceFile,
    IdentityFile,
    JdFile,
    MockBundle,
    MockStudent,
    ProfilePools,
    RulesFile,
    TemplateDef,
)

logger = logging.getLogger(__name__)


class MockDataError(RuntimeError):
    pass


def _read_raw(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise MockDataError(f"缺少 mock 文件：{path}")
    except json.JSONDecodeError as exc:
        raise MockDataError(f"mock 文件不是合法 JSON：{path}（{exc}）")


def _read(path: Path, model):
    try:
        return model.model_validate(_read_raw(path))
    except ValidationError as exc:
        raise MockDataError(f"mock 文件校验失败：{path}\n{exc}")


def _read_map(path: Path, model) -> dict:
    raw = _read_raw(path)
    if not isinstance(raw, dict):
        raise MockDataError(f"{path} 应为对象（键 → 数据）")
    out = {}
    for key, value in raw.items():
        try:
            out[key] = model.model_validate(value)
        except ValidationError as exc:
            raise MockDataError(f"{path} 键 {key} 校验失败\n{exc}")
    return out


@lru_cache
def load() -> MockBundle:
    root = Path(settings().mock_dir)

    bundle = MockBundle(
        students=_read_map(root / "students.json", MockStudent),
        academic=_read_map(root / "academic.json", AcademicEntry),
        experiences=_read(root / "experiences.json", ExperienceFile),
        pools=_read(root / "profile_pools.json", ProfilePools),
        templates=_read_map(root / "templates.json", TemplateDef),
        jd=_read(root / "jd_keywords.json", JdFile),
        rules=_read(root / "rules.json", RulesFile),
        identity=_read(root / "identity.json", IdentityFile),
        manifest=_read_raw(root / "manifest.json"),
    )

    _cross_check(bundle, root)
    return bundle


def _cross_check(bundle: MockBundle, root: Path) -> None:
    unknown = set(bundle.academic) - set(bundle.students)
    if unknown:
        raise MockDataError(f"{root}/academic.json 含未定义学号：{sorted(unknown)[:5]}")

    missing = set(bundle.students) - set(bundle.academic)
    if missing:
        logger.warning(
            "以下学号无冻结学业数据，将按池子生成：%s", sorted(missing)[:5]
        )

    if not bundle.templates:
        raise MockDataError(f"{root}/templates.json 为空")

    if bundle.identity.default_user not in bundle.identity.users:
        raise MockDataError(
            f"{root}/identity.json 的 default_user 不存在：{bundle.identity.default_user}"
        )

    declared = bundle.manifest.get("students")
    if isinstance(declared, int) and declared != len(bundle.students):
        logger.warning(
            "manifest.students=%s 与 students.json 条数 %s 不一致",
            declared,
            len(bundle.students),
        )
