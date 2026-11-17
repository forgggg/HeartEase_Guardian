from __future__ import annotations

from ..data.mock_store import load

TEMPLATES: dict[str, dict] = {
    key: value.model_dump() for key, value in load().templates.items()
}


def pick_template(target_role: str = "", template_id: str | None = None) -> str:
    if template_id and template_id in TEMPLATES:
        return template_id
    if any(k in target_role for k in ("国企", "事业单位", "公务员", "银行")):
        return "soe" if "soe" in TEMPLATES else next(iter(TEMPLATES))
    if any(k in target_role for k in ("开发", "算法", "测试", "数据", "运维")):
        return "tech" if "tech" in TEMPLATES else next(iter(TEMPLATES))
    return "general" if "general" in TEMPLATES else next(iter(TEMPLATES))
