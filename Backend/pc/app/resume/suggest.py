from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from ..llm import complete_json
from ..models import Finding, Suggestion
from .fidelity import new_entities, preserve_ratio

MIN_PRESERVE_RATIO = 0.35
MAX_WORKERS = 4

SYSTEM = """你是资深简历顾问，只做措辞层面的改写，必须遵守：
1. 不得新增原文中没有的数字、公司/学校名、时间、证书、技术名词；
2. 不得改变事实、职责范围与成果归属；
3. 动词开头；原文已有数据时把结果前置；单条不超过 60 字；
4. 只输出 JSON：{"revised": "...", "reason": "..."}，不要任何多余文字。"""

REWRITABLE = {"R1", "R2", "R4", "R5"}


def _user_prompt(original: str, findings: list[Finding], target_role: str) -> str:
    issues = "；".join(f"{f.name}：{f.evidence}" for f in findings)
    return (
        f"目标岗位：{target_role or '未指定'}\n"
        f"诊断出的问题：{issues}\n"
        f"原文：{original}\n"
        "请改写这一条，说明修改理由。"
    )


def _rewrite(original: str, findings: list[Finding], target_role: str) -> Suggestion | None:
    rules = [f.rule for f in findings]
    payload = complete_json(
        SYSTEM,
        _user_prompt(original, findings, target_role),
        {"revised": original, "reason": "未配置模型，保留原文"},
    )

    if payload.get("_error"):
        return Suggestion(
            rule=rules[0],
            rules=rules,
            original=original,
            revised=original,
            reason=f"模型调用失败：{payload['_error']}",
        )

    revised = str(payload.get("revised", "")).strip() or original
    reason = str(payload.get("reason", "")).strip()

    added = new_entities(original, revised)
    if added:
        return Suggestion(
            rule=rules[0],
            rules=rules,
            original=original,
            revised=original,
            reason=f"改写引入原文没有的 {'、'.join(added)}，已回退为原文",
        )

    # 空话套话本就是删改，中文重合度不适用；其余规则必须保留原意
    if "R4" not in rules:
        ratio = preserve_ratio(original, revised)
        if ratio < MIN_PRESERVE_RATIO:
            return Suggestion(
                rule=rules[0],
                rules=rules,
                original=original,
                revised=original,
                reason=f"改写偏离原意（内容重合度 {ratio}），已回退为原文",
            )

    if revised == original and not settings().llm_ready:
        return None

    return Suggestion(
        rule=rules[0], rules=rules, original=original, revised=revised, reason=reason
    )


def for_findings(findings: list[Finding], target_role: str = "") -> list[Suggestion]:
    out: list[Suggestion] = []

    for finding in findings:
        if finding.rule == "R9":
            out.append(
                Suggestion(
                    rule=finding.rule,
                    rules=[finding.rule],
                    original=finding.original,
                    revised="",
                    reason="证件号/手机号属于隐私，应从简历中删除",
                )
            )

    groups: dict[str, list[Finding]] = {}
    for finding in findings:
        if finding.rule in REWRITABLE:
            groups.setdefault(finding.original, []).append(finding)

    items = list(groups.items())[: settings().max_suggestions]
    if not items:
        return out

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = pool.map(lambda item: _rewrite(item[0], item[1], target_role), items)

    out.extend(s for s in results if s is not None)
    for index, item in enumerate(out, start=1):
        item.id = f"s{index}"
    return out


def apply_to_text(text: str, suggestions: list[Suggestion]) -> str:
    """按采纳状态应用建议：accepted=False 跳过，其余（待定/已采纳）生效。"""
    for item in suggestions:
        if item.accepted is False:
            continue
        if not item.original or item.revised == item.original:
            continue
        if item.rule == "R9":
            text = text.replace(item.original, "")
        else:
            text = text.replace(item.original, item.revised, 1)
    return text
