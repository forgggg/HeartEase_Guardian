from __future__ import annotations

import re


ENTITY_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}|\d+(?:\.\d+)?%?")


def entities(text: str) -> set[str]:
    return {m.group(0).lower() for m in ENTITY_RE.finditer(text)}


def new_entities(original: str, revised: str) -> list[str]:
    """改写不得引入原文没有的数字/英文实体（公司、学校、技术名词）。"""
    return sorted(entities(revised) - entities(original))


def _bigrams(text: str) -> set[str]:
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
    return {cjk[i : i + 2] for i in range(len(cjk) - 1)}


def preserve_ratio(original: str, revised: str) -> float:
    """原文中文二元组在改写稿中的保留比例；过低说明经历被改写成了另一件事。"""
    base = _bigrams(original)
    if not base:
        return 1.0
    return round(len(base & _bigrams(revised)) / len(base), 2)
