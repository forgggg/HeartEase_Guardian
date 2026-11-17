from pathlib import Path

from app.resume.parse import extract_text
from app.resume.rules import analyze

SAMPLES = Path(__file__).resolve().parents[3] / "data" / "samples"


def test_good_sample_has_no_structural_noise():
    text = extract_text("resume_good.docx", (SAMPLES / "resume_good.docx").read_bytes())
    rules = {f.rule for f in analyze(text, "Java 后端开发工程师")}
    assert "R9" not in rules
    assert "R2" not in rules
    assert len(rules) <= 3


def test_bad_sample_hits_core_rules():
    text = extract_text("resume_bad.docx", (SAMPLES / "resume_bad.docx").read_bytes())
    rules = {f.rule for f in analyze(text, "Java 后端开发工程师")}
    assert {"R2", "R3", "R4", "R9"} <= rules
