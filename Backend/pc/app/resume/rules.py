from __future__ import annotations

import re

from ..data.mock_store import load
from ..models import Finding, QualityReport

_CATALOG = load().rules
THRESHOLDS = _CATALOG.thresholds
RULE_META = {rule.id: rule for rule in _CATALOG.rules}
RULE_NAMES = {rule.id: rule.name for rule in _CATALOG.rules}
RULE_VERSION = _CATALOG.version
JD_ROLES = load().jd.roles
JD_VERSION = load().jd.version

SKILL_PREFIX = ("熟悉", "熟练掌握", "精通", "了解")
WEAK_PREFIX = ("负责", "参与", "协助", "配合", "帮助")
ACTION_VERBS = (
    "开发", "设计", "实现", "搭建", "优化", "主导", "推动", "完成", "负责", "参与",
    "协助", "配合", "编写", "清洗", "定位", "接入", "构建", "输出", "调研", "分析",
    "维护", "部署", "测试", "复现", "改造", "拆分", "抽离", "重构", "落地", "交付",
    "上线", "支持", "整理",
)
# STAR 的 Result：有结果但缺数字 → R1；连结果都没有 → R3
OUTCOME_MARKERS = (
    "提升", "降低", "下降", "减少", "增长", "节省", "缩短", "覆盖", "上线",
    "交付", "通过", "获奖", "达成", "优于", "沉淀", "落地", "修复", "替代",
)
VAGUE = (
    "熟练掌握", "沟通能力强", "学习能力强", "认真负责", "积极主动",
    "吃苦耐劳", "抗压能力强", "良好的团队",
)
PRIVACY = (
    (r"\d{17}[\dXx]", "身份证号"),
    (r"(?<!\d)1[3-9]\d{9}(?!\d)", "完整手机号"),
)

MAX_FINDINGS = 25


def split_bullets(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"^[\-\u2022\*·\s]+", "", raw.strip())
        for seg in re.split(r"[。；;]", line):
            seg = seg.strip(" ，,、\t")
            if len(seg) >= THRESHOLDS.min_bullet_chars:
                out.append(seg)
    return out


def is_description(bullet: str) -> bool:
    if " | " in bullet or " · " in bullet or bullet.count(" / ") >= 2:
        return False
    return any(verb in bullet for verb in ACTION_VERBS)


def keywords_for(target_role: str) -> list[str]:
    for key, words in JD_ROLES.items():
        if key in target_role:
            return words
    return []


def coverage(text: str, target_role: str) -> tuple[float, list[str]]:
    words = keywords_for(target_role)
    if not words:
        return 0.0, []
    lowered = text.lower()
    missing = [w for w in words if w.lower() not in lowered]
    return round(1 - len(missing) / len(words), 2), missing


def analyze(text: str, target_role: str = "") -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    def add(rule: str, original: str, evidence: str) -> None:
        key = (rule, original)
        if key in seen or len(findings) >= MAX_FINDINGS:
            return
        seen.add(key)
        meta = RULE_META.get(rule)
        findings.append(
            Finding(
                rule=rule,
                name=RULE_NAMES.get(rule, rule),
                severity=meta.severity if meta else "medium",
                original=original,
                evidence=evidence,
            )
        )

    for pattern, label in PRIVACY:
        for match in re.finditer(pattern, text):
            add("R9", match.group(0), f"简历不应出现{label}")

    for bullet in split_bullets(text):
        is_skill = bullet.startswith(SKILL_PREFIX)
        is_action = not is_skill and is_description(bullet)
        if is_action and len(bullet) > THRESHOLDS.max_bullet_chars:
            add("R5", bullet, f"长度 {len(bullet)} 字，建议拆分为两条")
        if is_action and not re.search(r"\d", bullet):
            if any(marker in bullet for marker in OUTCOME_MARKERS):
                add("R1", bullet, "有结果表述但没有数字/比例/规模")
            else:
                add("R3", bullet, "缺少 STAR 的 Result，读者无法判断产出")
        if is_action and bullet.startswith(WEAK_PREFIX):
            add("R2", bullet, "以弱动词开头，改为动作动词并补结果")
        for phrase in VAGUE:
            if phrase in bullet:
                add("R4", bullet, f"出现无证据表述「{phrase}」")
                break

    cov, missing = coverage(text, target_role)
    if missing and cov < THRESHOLDS.keyword_coverage_warn:
        add("R6", "、".join(missing), f"目标岗位关键词缺失 {len(missing)} 个")

    return findings


def evaluate(findings: list[Finding], target_role: str, text: str) -> QualityReport:
    score = 100 - sum(
        {"high": 12, "medium": 6, "low": 3}.get(f.severity, 6) for f in findings
    )
    cov, missing = coverage(text, target_role)
    if target_role:
        score -= int((1 - cov) * 15)
    return QualityReport(
        score=max(0, min(100, score)),
        keyword_coverage=cov,
        missing_keywords=missing,
        findings=len(findings),
        rules_version=RULE_VERSION,
    )
