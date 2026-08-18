#!/usr/bin/env python3
"""Build deterministic indexes for MLFF architecture/release lineage."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "docs" / "history" / "mlff"
REV_DIR = HIST / "architecture_revisions"
REL_DIR = HIST / "release_notes"


def first_heading(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def field(text: str, name: str) -> str:
    patterns = [
        rf"\*\*{re.escape(name)}:\*\*\s*`?([^`\n]+?)`?\s*$",
        rf"\*\*{re.escape(name)}\*\*\s*[:\-]\s*`?([^`\n]+?)`?\s*$",
    ]
    for line in text.splitlines():
        for pat in patterns:
            m = re.search(pat, line, flags=re.I)
            if m:
                return m.group(1).strip()
    return ""


def build_revision_index() -> None:
    rows = []
    for md in sorted(REV_DIR.glob("ARCHITECTURE_NOTES_MLFF_REV*.md")):
        m = re.search(r"REV(\d+)\.md$", md.name)
        if not m:
            continue
        rev = int(m.group(1))
        text = md.read_text(encoding="utf-8", errors="replace")
        title = first_heading(md)
        gate = field(text, "Gate")
        release = field(text, "Release")
        meta = " / ".join(x for x in (gate, release) if x) or "-"
        pdf = md.with_suffix(".pdf")
        render = f"[{pdf.name}]({pdf.name})" if pdf.exists() else "-"
        rows.append((rev, meta, title, md.name, render))
    lines = [
        "# MLFF architecture revision index",
        "",
        "Historical revision notes are non-normative. Current authority is `docs/arch_manuals/mlff_training_data_architecture.md`.",
        "",
        "| Rev | Gate/release | Note | Render |",
        "|---:|---|---|---|",
    ]
    for rev, meta, title, name, render in sorted(rows):
        safe_title = title.replace("|", "\\|")
        safe_meta = meta.replace("|", "\\|")
        lines.append(f"| {rev} | {safe_meta} | [{safe_title}]({name}) | {render} |")
    (REV_DIR / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def version_key(name: str):
    m = re.search(r"PATCH_NOTES_(\d+)\.(\d+)\.(\d+)a(\d+)\.md$", name)
    return tuple(map(int, m.groups())) if m else (10**9, name)


def build_release_index() -> None:
    rows = []
    for md in sorted(REL_DIR.glob("PATCH_NOTES_*.md"), key=lambda p: version_key(p.name)):
        version = md.stem.removeprefix("PATCH_NOTES_")
        pdf = md.with_suffix(".pdf")
        render = f"[{pdf.name}]({pdf.name})" if pdf.exists() else "-"
        rows.append((version, md.name, render))
    lines = [
        "# MLFF release-note index",
        "",
        "Release notes record deltas and migration context; they are not current architecture authority.",
        "",
        "| Release | Note | Render |",
        "|---|---|---|",
    ]
    for version, name, render in rows:
        lines.append(f"| `{version}` | [{name}]({name}) | {render} |")
    (REL_DIR / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_revision_index()
    build_release_index()
    print(REV_DIR / "INDEX.md")
    print(REL_DIR / "INDEX.md")


if __name__ == "__main__":
    main()
