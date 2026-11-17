from app.resume.fidelity import new_entities, preserve_ratio
from app.resume.rules import analyze, coverage, evaluate


def test_flags_weak_verb_and_missing_result():
    rules = {f.rule for f in analyze("负责用户调研并输出需求文档")}
    assert {"R2", "R3"} <= rules


def test_flags_missing_number_when_result_present():
    rules = {f.rule for f in analyze("优化接口响应速度，显著提升用户体验")}
    assert "R1" in rules and "R3" not in rules


def test_skill_line_only_checks_vague_words():
    rules = {f.rule for f in analyze("熟练掌握 Java 与 SQL，沟通能力强")}
    assert "R4" in rules
    assert "R1" not in rules and "R2" not in rules


def test_titles_and_skill_lists_are_not_flagged():
    for line in [
        "学生成绩分析看板 · 院系勤工助学",
        "Java / Spring Boot / MySQL / Redis / Docker / Git",
        "男 | 138****0001 | graduate001@example.com | 求职意向：Java 后端开发工程师",
        "校级一等奖学金 / 优秀学生干部",
    ]:
        assert not analyze(line), line


def test_privacy_is_high_severity():
    findings = analyze("联系方式 13800138000，可随时到岗")
    privacy = [f for f in findings if f.rule == "R9"]
    assert privacy and privacy[0].severity == "high"


def test_keyword_coverage_counts_missing_terms():
    cov, missing = coverage("使用 Java 参与订单模块开发，修复慢查询", "Java 后端开发工程师")
    assert 0 < cov < 1
    assert "Redis" in missing


def test_quality_drops_with_findings():
    text = "负责用户调研并输出需求文档"
    findings = analyze(text, "Java 后端开发工程师")
    report = evaluate(findings, "Java 后端开发工程师", text)
    assert report.score < 100
    assert report.findings == len(findings)


def test_fidelity_blocks_new_numbers():
    assert new_entities("负责用户调研", "主导 500 名用户调研") == ["500"]
    assert new_entities("主导调研并输出报告", "主导调研并输出报告") == []


def test_preserve_ratio_blocks_unrelated_rewrite():
    assert preserve_ratio("负责用户调研并输出需求文档", "主导用户调研并输出需求文档，推动需求落地") >= 0.35
    assert preserve_ratio("参与后台接口开发，配合测试完成联调", "主导用户调研并输出需求文档，推动需求落地") < 0.35
