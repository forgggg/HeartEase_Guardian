"""5.1 的可选润色：默认关闭；开启后只改措辞，事实型字段不动。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from ..llm import complete_json
from ..models import ResumeDoc
from .fidelity import new_entities, preserve_ratio

SYSTEM = """你在润色简历句子，只允许改措辞，必须遵守：
1. 不得新增原文没有的数字、公司/学校名、时间、证书、技术名词；
2. 不得改变事实、职责范围与成果归属；
3. 动词开头，单条不超过 60 字；
4. 只输出 JSON：{"revised": "..."}。"""

MAX_SENTENCES = 7


def enabled() -> bool:
    return settings().resume_llm_polish.strip().lower() in {"on", "1", "true"} and settings().llm_ready


def _rewrite(text: str, target_role: str) -> str:
    payload = complete_json(
        SYSTEM, f"目标岗位：{target_role}\n原文：{text}", {"revised": text}
    )
    if payload.get("_error") or payload.get("_fallback"):
        return text
    revised = str(payload.get("revised", "")).strip()
    if not revised or revised == text:
        return text
    if new_entities(text, revised):
        return text
    if preserve_ratio(text, revised) < 0.35:
        return text
    return revised


def apply(doc: ResumeDoc) -> tuple[ResumeDoc, bool]:
    """返回（可能被润色的文档, 是否真的用了模型）。"""
    if not enabled():
        return doc, False

    targets: list[str] = []
    if doc.summary:
        targets.append(doc.summary)
    bullets = [
        bullet
        for exp in [*doc.projects, *doc.internships]
        for bullet in exp.bullets
    ]
    targets.extend(b.text for b in bullets[:MAX_SENTENCES])

    if not targets:
        return doc, False

    with ThreadPoolExecutor(max_workers=4) as pool:
        rewritten = list(pool.map(lambda text: _rewrite(text, doc.target_role), targets))

    changed = False
    index = 0
    if doc.summary:
        if rewritten[0] != doc.summary:
            doc.summary = rewritten[0]
            doc.sources["summary"] = "llm"
            changed = True
        index = 1

    for bullet in bullets[:MAX_SENTENCES]:
        text = rewritten[index]
        index += 1
        if text != bullet.text:
            bullet.text = text
            bullet.source = "llm"
            changed = True

    if changed:
        doc.needs_review = True
    return doc, changed
