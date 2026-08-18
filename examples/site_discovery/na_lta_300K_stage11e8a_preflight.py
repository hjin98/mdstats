#!/usr/bin/env python3
"""Audit the real derived 300 K Na-LTA evidence bundled with mdstats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mdstats.analysis.density import (
    audit_bundled_na_lta_300k_legacy_evidence,
    render_na_lta_300k_pilot_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()
    root = args.package_root.resolve()
    json_path = args.json or root / "benchmarks" / "na_lta_300K_stage11e8a_preflight.json"
    md_path = args.markdown or root / "benchmarks" / "na_lta_300K_stage11e8a_preflight.md"
    report = audit_bundled_na_lta_300k_legacy_evidence(root)
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_na_lta_300k_pilot_markdown(report), encoding="utf-8")
    print(report.overall_status.value)
    print(report.signature)
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
