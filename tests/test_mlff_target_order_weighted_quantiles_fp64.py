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
        ((50, 15), 0.01, 1),
        ((2, 57), 0.25, 1),
        ((1, 6), 0.75, 4),
        ((14, 50), 0.99, 62),
    )

    for counts, quantile, expected_index in cases:
        weights = _correlation_balanced_case(*counts)
        values = np.arange(weights.size, dtype=np.float64)
        stored_sum = float(np.sum(weights, dtype=np.float64))
        assert stored_sum != 1.0

        result = _weighted_quantiles(values, weights, (quantile,))
        assert int(result[0]) == expected_index

        cumulative = np.cumsum(weights, dtype=np.float64)
        incorrectly_rescaled_index = int(
            np.searchsorted(cumulative, quantile * stored_sum, side="left")
        )
        assert incorrectly_rescaled_index != expected_index
