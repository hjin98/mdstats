#!/usr/bin/env python3
"""Assemble the current MLFF architecture from ordered chapter sources."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "arch_manuals" / "mlff_training_data"
OUT = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
ORDER = [
    "00_front_matter.md",
    "10_foundations.md",
    "20_data_contracts.md",
    "30_statistical_design.md",
    "40_training_evaluation.md",
    "50_target_multiview.md",
    "60_execution_performance.md",
    "70_status_and_gates.md",
    "80_ownership_and_decisions.md",
    "90_references.md",
]


def main() -> None:
    parts = []
    for name in ORDER:
        path = SRC / name
        if not path.is_file():
            raise SystemExit(f"missing architecture chapter: {path}")
        parts.append(path.read_text(encoding="utf-8").rstrip())
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
