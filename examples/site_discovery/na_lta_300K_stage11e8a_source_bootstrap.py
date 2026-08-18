#!/usr/bin/env python3
"""Bind a real 300 K Na-LTA vasprun.xml to the Stage-11E8a-S0 dossier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mdstats import read_vasp_frames
from mdstats.analysis.density import (
    prepare_na_lta_300k_source_bootstrap,
    render_na_lta_300k_pilot_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trajectory", type=Path, help="Path to the exact 300 K Na-LTA vasprun.xml")
    parser.add_argument("--json", type=Path, default=Path("na_lta_300K_stage11e8a_s0.json"))
    parser.add_argument("--markdown", type=Path, default=Path("na_lta_300K_stage11e8a_s0.md"))
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--stop", type=int, default=None)
    parser.add_argument("--stride", type=int, default=1)
    args = parser.parse_args()

    trajectory_path = args.trajectory.resolve()
    collection = read_vasp_frames(
        str(trajectory_path),
        format="vasp-xml",
        start=args.start,
        stop=args.stop,
        stride=args.stride,
        frame_semantics="trajectory",
    )
    result = prepare_na_lta_300k_source_bootstrap(collection, trajectory_path)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(result.report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(
        render_na_lta_300k_pilot_markdown(result.report),
        encoding="utf-8",
    )

    print(f"status={result.report.overall_status.value}")
    print(f"trajectory_sha256={result.trajectory_sha256}")
    print(f"registration_signature={result.registration.signature}")
    print(f"na_sample_catalog_signature={result.na_samples.signature}")
    print(f"na_samples={result.na_samples.n_samples}")
    print(f"json={args.json.resolve()}")
    print(f"markdown={args.markdown.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
