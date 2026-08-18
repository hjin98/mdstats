"""Quantify gaussian_sigma_v1 versus effective_cic_stencil_rms_v1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from mdstats.plotting.density_broadening import effective_artificial_broadening


def main() -> None:
    cells = {
        "orthogonal": np.diag([12.0, 10.0, 8.0]),
        "lta_primitive": np.asarray(
            [
                [17.3630, 0.0, 0.0],
                [8.6815, 15.0368, 0.0],
                [8.6815, 5.0123, 14.1768],
            ]
        ),
    }
    shape = (64, 64, 64)
    phases = {
        "on_node": np.asarray([[0.0, 0.0, 0.0]]),
        "half_node": np.asarray([[0.5 / 64.0, 0.5 / 64.0, 0.5 / 64.0]]),
        "mixed": np.asarray(
            [
                [0.13, 0.27, 0.39],
                [0.71, 0.44, 0.92],
                [0.33, 0.58, 0.16],
            ]
        ),
    }
    weights = {
        "on_node": np.ones(1),
        "half_node": np.ones(1),
        "mixed": np.asarray([0.2, 0.5, 0.3]),
    }
    rows: list[dict[str, object]] = []
    for cell_name, cell in cells.items():
        h_max = max(np.linalg.norm(cell, axis=1) / np.asarray(shape))
        for ratio in (0.0, 1.0, 2.0):
            sigma = ratio * h_max
            for phase_name, positions in phases.items():
                diagnostic = effective_artificial_broadening(
                    positions,
                    weights[phase_name],
                    shape,
                    cell,
                    sigma,
                )
                rows.append(
                    {
                        "cell": cell_name,
                        "phase": phase_name,
                        "grid_shape": list(shape),
                        "h_max": h_max,
                        "sigma_to_h_max": ratio,
                        "gaussian_sigma": sigma,
                        "cic_rms": diagnostic.cic_rms,
                        "stencil_rms": diagnostic.stencil_rms,
                        "effective_rms": diagnostic.effective_rms,
                        "effective_to_sigma": (
                            None if sigma == 0.0 else diagnostic.effective_rms / sigma
                        ),
                    }
                )
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps({"rows": rows}, indent=2) + "\n")

    lines = [
        "# Density Broadening Migration Benchmark",
        "",
        "This benchmark compares the legacy Gaussian-width diagnostic with the",
        "effective CIC-plus-canonical-stencil RMS width. The density operator itself",
        "is not changed by this benchmark.",
        "",
        "| Cell | Phase | sigma/h_max | CIC RMS (A) | Stencil RMS (A) | Effective RMS (A) | Effective/sigma |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        ratio_value = row["effective_to_sigma"]
        ratio_text = "n/a" if ratio_value is None else f"{float(ratio_value):.8f}"
        lines.append(
            "| {cell} | {phase} | {sigma_to_h_max:.1f} | {cic_rms:.8g} | "
            "{stencil_rms:.8g} | {effective_rms:.8g} | {ratio} |".format(
                **row, ratio=ratio_text
            )
        )
    lines.extend(
        [
            "",
            "At sigma/h_max = 2, the effective width equals sigma for on-node",
            "samples and is modestly larger for off-node CIC phases. At sigma = 0,",
            "the artificial width is the CIC contribution alone.",
        ]
    )
    Path(__file__).with_suffix(".md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
