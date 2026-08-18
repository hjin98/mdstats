#!/usr/bin/env python3
"""Execute the Stage-11E8a-S1 real Na-LTA density/attractor pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mdstats import read_vasp_frames
from mdstats.analysis.density import (
    NaLta300KDensityAttractorPilotOptions,
    prepare_na_lta_300k_density_attractor_pilot,
    render_na_lta_300k_pilot_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trajectory", type=Path, help="Exact 300 K Na-LTA vasprun.xml")
    parser.add_argument("--json", type=Path, default=Path("na_lta_300K_stage11e8a_s1.json"))
    parser.add_argument("--markdown", type=Path, default=Path("na_lta_300K_stage11e8a_s1.md"))
    parser.add_argument("--products", type=Path, default=Path("na_lta_300K_stage11e8a_s1_products.json"))
    parser.add_argument("--representative-frames", type=int, default=60)
    parser.add_argument("--grid", type=int, default=16)
    parser.add_argument("--sigma", type=float, default=0.50)
    args = parser.parse_args()

    trajectory_path = args.trajectory.resolve()
    collection = read_vasp_frames(
        str(trajectory_path), format="vasp-xml", frame_semantics="trajectory"
    )
    options = NaLta300KDensityAttractorPilotOptions(
        representative_frame_count=args.representative_frames,
        grid_shape=(args.grid, args.grid, args.grid),
        kernel_sigma_angstrom=args.sigma,
    )
    result = prepare_na_lta_300k_density_attractor_pilot(
        collection, trajectory_path, options=options
    )

    for path in (args.json, args.markdown, args.products):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result.report.to_dict(), indent=2, sort_keys=True) + "\n")
    args.markdown.write_text(render_na_lta_300k_pilot_markdown(result.report))
    args.products.write_text(
        json.dumps(
            {
                "options": options.to_dict(),
                "gauge_validation": result.gauge_validation.to_dict(),
                "representative_frame_indices": list(result.representative_frame_indices),
                "density": result.density.to_dict(include_values=False),
                "attractors": result.attractors.to_dict(),
            },
            indent=2,
            sort_keys=True,
        ) + "\n"
    )

    print(f"status={result.report.overall_status.value}")
    print(f"registration={result.source_bootstrap.registration.signature}")
    print(f"gauge_validation={result.gauge_validation.signature}")
    print(f"representative_frames={len(result.representative_frame_indices)}")
    print(f"density={result.density.signature}")
    print(f"attractors={len(result.attractors.attractors)}")
    print(f"saddles={len(result.attractors.saddles)}")
    print(f"wall_seconds={result.wall_seconds:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
