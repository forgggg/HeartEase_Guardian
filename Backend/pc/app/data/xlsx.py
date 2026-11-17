from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_COL = re.compile(r"[A-Z]+")


def _first_sheet_path(z: zipfile.ZipFile) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    sheet = next(iter(wb.find(f"{NS}sheets")))
    rid = sheet.get(f"{REL_NS}id")
    target = next(r.get("Target") for r in rels if r.get("Id") == rid)
    target = target.lstrip("/")
    return target if target.startswith("xl/") else f"xl/{target}"


def read_rows(path: Path) -> list[dict[str, str]]:
    """读取 xlsx 首个工作表为 [{表头: 值}]，仅依赖标准库（不引入 pandas）。"""
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))

        grid: list[dict[str, str]] = []
        for row in ET.fromstring(z.read(_first_sheet_path(z))).iter(f"{NS}row"):
            cells: dict[str, str] = {}
            for c in row:
                value = c.find(f"{NS}v")
                inline = c.find(f"{NS}is")
                if c.get("t") == "s" and value is not None:
                    text = shared[int(value.text)]
                elif inline is not None:
                    text = "".join(t.text or "" for t in inline.iter(f"{NS}t"))
                else:
                    text = value.text if value is not None else ""
                if text:
                    cells[_COL.match(c.get("r")).group(0)] = str(text).strip()
            grid.append(cells)

    if not grid:
        return []
    header = grid[0]
    return [{header[k]: r.get(k, "") for k in header} for r in grid[1:]]
