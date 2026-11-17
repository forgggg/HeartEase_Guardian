"""生成回归样本：data/samples/resume_good.docx / resume_bad.docx

用法：.venv/bin/python scripts/make_samples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PC_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = PC_DIR.parent.parent
sys.path.insert(0, str(PC_DIR))

from docx import Document  # noqa: E402

from app.data import source  # noqa: E402
from app.resume import render  # noqa: E402
from app.resume.assemble import assemble  # noqa: E402

BAD_LINES = [
    "个人简历",
    "负责用户调研并输出需求文档",
    "熟练掌握 Java 与 SQL，沟通能力强",
    "参与后台接口开发，配合测试完成联调",
    "联系电话 13800138000",
]


def main() -> None:
    out_dir = REPO_DIR / "data" / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    student = source.profile("202210700001")
    role = source.target_role_hint(student)
    doc = assemble(student, "tech", role, "sample_good")
    (out_dir / "resume_good.docx").write_bytes(render.docx_from_blocks(render.blocks_from_doc(doc)))

    bad = Document()
    for line in BAD_LINES:
        bad.add_paragraph(line)
    bad.save(out_dir / "resume_bad.docx")

    print(f"samples -> {out_dir}")


if __name__ == "__main__":
    main()
