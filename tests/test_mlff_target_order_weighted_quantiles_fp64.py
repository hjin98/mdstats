from __future__ import annotations

import numpy as np

from mdstats.training_data.target_order.coverage_reference import (
    _weighted_quantiles,
    correlation_balanced_weights,
)


def _correlation_balanced_case(*counts: int) -> np.ndarray:
    unit_ids: list[str] = []
    for unit, count in enumerate(counts):
        unit_ids.extend([f"unit-{unit}"] * count)
    return correlation_balanced_weights(unit_ids)


def test_weighted_quantiles_compare_stored_mass_directly_to_governed_q() -> None:
    cases = (
        ((2, 6), 0.25, 0),
        ((50, 1), 0.01, 0),
        ((1, 6), 0.75, 4),
        ((1, 150), 0.99, 148),
    )

    for counts, quantile, expected_index in cases:
        weights = _correlation_balanced_case(*counts)
        values = np.arange(weights.size, dtype=np.float64)
        cumulative = np.cumsum(weights, dtype=np.float64)
        terminal_mass = float(cumulative[-1])
        assert terminal_mass != 1.0

        result = _weighted_quantiles(values, weights, (quantile,))
        assert int(result[0]) == expected_index

        incorrectly_rescaled_index = int(
            np.searchsorted(cumulative, quantile * terminal_mass, side="left")
        )
        assert incorrectly_rescaled_index != expected_index
