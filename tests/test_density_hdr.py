from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting.density_contracts import DensitySourceProvenance
from mdstats.plotting.density_hdr import (
    DensityHDRBatch,
    prepare_contour_support_many,
    select_hdr_details_many,
)
from mdstats.plotting.density_packed_field import pack_sparse_reference_field
from mdstats.plotting.density_sparse_reference import SparseCanonicalDensityReference3D
from mdstats.plotting.graph_errors import GraphComplexityError


def _field(
    *,
    shape: tuple[int, int, int] = (8, 4, 4),
    coordinates: np.ndarray | None = None,
    values: np.ndarray | None = None,
):
    if coordinates is None:
        coordinates = np.asarray(
            [(0, 0, 0), (7, 0, 0), (3, 2, 2), (4, 2, 2), (1, 1, 1)],
            dtype=np.int64,
        )
    if values is None:
        values = np.asarray([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float64)
    flat = np.ravel_multi_index(np.asarray(coordinates).T, shape, order="C")
    order = np.argsort(flat)
    values = np.asarray(values, dtype=np.float64)[order]
    flat = flat[order]
    reference = SparseCanonicalDensityReference3D(
        field_key="hdr-fixture",
        label="HDR fixture",
        physical_units="count / angstrom^3",
        logical_grid_shape=shape,
        active_flat_indices=flat,
        active_values=values,
        display_cell=np.diag(np.asarray(shape, dtype=np.float64)),
        total_measure=float(np.sum(values)),
        gaussian_bandwidth=0.2,
        broadening_metric="effective_cic_stencil_rms_v1",
        source_provenance=DensitySourceProvenance(source_kind="test"),
    )
    return pack_sparse_reference_field(reference, storage_block_shape=(4, 4, 4))


def _sorted_reference(field, fraction: float):
    descending = np.sort(field.packed_values)[::-1]
    cumulative = np.cumsum(descending) * field.voxel_volume
    index = int(np.searchsorted(cumulative, fraction * field.total_measure, side="left"))
    threshold = float(descending[index])
    chosen = field.packed_values >= threshold
    measure = float(np.sum(field.packed_values[chosen])) * field.voxel_volume
    return threshold, int(np.count_nonzero(chosen)), measure


def test_multi_hdr_matches_exact_sorted_reference_with_one_bounded_sort() -> None:
    field = _field()
    fractions = (0.20, 0.50, 0.80, 0.95)
    batch = field.hdr_details_many(fractions, chunk_size=2)
    assert batch.algorithm == "single_sort_chunked_multi_hdr_v1"
    assert batch.sort_workspace_bytes == field.packed_values.nbytes
    assert batch.peak_cumulative_chunk_bytes <= 2 * 8
    for fraction, details in zip(fractions, batch.details, strict=True):
        threshold, count, measure = _sorted_reference(field, fraction)
        assert details.threshold == threshold
        assert details.selected_node_count == count
        assert details.selected_measure == measure
    restored = DensityHDRBatch.from_json_dict(batch.to_json_dict())
    assert restored.to_json_dict() == batch.to_json_dict()


def test_multi_hdr_rejects_workspace_before_sort() -> None:
    field = _field()
    with pytest.raises(GraphComplexityError, match="max_workspace_bytes"):
        select_hdr_details_many(field, (0.5, 0.8), max_workspace_bytes=8)


def test_contour_support_is_nested_and_periodic_components_are_lazy() -> None:
    field = _field()
    batch = field.hdr_details_many((0.30, 0.80), chunk_size=2)
    supports = prepare_contour_support_many(field, batch, compute_components=True)
    inner, outer = supports
    assert inner.selected_block_indices.shape[0] <= outer.selected_block_indices.shape[0]
    assert inner.crossing_block_indices.shape[0] > 0
    assert outer.halo_block_indices.shape[0] >= outer.crossing_block_indices.shape[0]
    assert inner.component_count is not None
    # The blocks at x=0 and x=1 are neighbours in this two-block periodic grid.
    assert outer.component_count == 1
    assert outer.metadata["scientific_field_modified"] is False
