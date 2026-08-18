"""Quantify legacy-spectral versus canonical-discrete density migration."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from mdstats.plotting import (
    DISCRETE_PERIODIZED_OPERATOR,
    LEGACY_SPECTRAL_OPERATOR,
    DensityKernelOptions,
    smooth_periodic_node_masses,
)
from mdstats.plotting.atomic_density import _deposit_cic


def _relative_errors(reference: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    delta = np.abs(candidate - reference)
    return (
        float(np.sum(delta)) / float(np.sum(np.abs(reference))),
        float(np.max(delta)) / float(np.max(np.abs(reference))),
    )


def _case(name: str, cell: np.ndarray, ratio: float) -> dict[str, object]:
    shape = (64, 64, 64)
    longest_interval = float(np.max(np.linalg.norm(cell, axis=1) / np.asarray(shape)))
    sigma = ratio * longest_interval
    mass = _deposit_cic(
        np.asarray([[0.173, 0.289, 0.413]], dtype=np.float64),
        np.asarray([1.0], dtype=np.float64),
        shape,
    )
    legacy, _ = smooth_periodic_node_masses(
        mass,
        cell,
        sigma,
        DensityKernelOptions(smoothing_operator=LEGACY_SPECTRAL_OPERATOR),
    )
    canonical, metadata = smooth_periodic_node_masses(
        mass,
        cell,
        sigma,
        DensityKernelOptions(smoothing_operator=DISCRETE_PERIODIZED_OPERATOR),
    )
    l1, linf = _relative_errors(legacy, canonical)
    return {
        "cell": name,
        "grid_shape": list(shape),
        "sigma_to_longest_grid_interval": ratio,
        "longest_grid_interval": longest_interval,
        "gaussian_bandwidth": sigma,
        "relative_l1_difference": l1,
        "relative_linf_difference": linf,
        "canonical_stencil_offset_count": int(metadata["stencil_offset_count"]),
        "canonical_periodic_image_contribution_count": int(
            metadata["periodic_image_contribution_count"]
        ),
    }


def main() -> None:
    orthogonal = np.diag([10.0, 10.0, 10.0])
    lta = np.asarray(
        [
            [10.0, 0.0, 0.0],
            [5.0, 8.660254037844386, 0.0],
            [5.0, 2.886751345948129, 8.16496580927726],
        ]
    )
    results = [
        _case(name, cell, ratio)
        for name, cell in (("orthogonal", orthogonal), ("lta_primitive", lta))
        for ratio in (2.0, 1.0, 0.5)
    ]
    destination = Path(__file__).with_suffix(".json")
    destination.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(destination)


if __name__ == "__main__":
    main()
