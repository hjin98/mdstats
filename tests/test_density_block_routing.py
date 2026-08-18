from __future__ import annotations

import numpy as np

from mdstats.plotting.density_block_routing import (
    PeriodicKernelBlockRouting,
    bitset_int_to_words,
    bitset_popcount,
    bitset_words_to_int,
    build_periodic_kernel_block_routing,
    canonical_signed_stencil_offsets,
    clear_density_routing_cache,
    density_routing_cache_info,
    get_periodic_kernel_block_routing,
    pack_local_indices,
    unpack_local_bitset,
    validity_bitset_for_extent,
)
from mdstats.plotting.density_kernel import PeriodicGaussianStencilSupport


def _stencil(shape: tuple[int, int, int], offsets: list[tuple[int, int, int]]) -> PeriodicGaussianStencilSupport:
    canonical = np.asarray(offsets, dtype=np.int64) % np.asarray(shape, dtype=np.int64)
    flat = np.ravel_multi_index(
        (canonical[:, 0], canonical[:, 1], canonical[:, 2]), shape, order="C"
    )
    flat = np.unique(flat).astype(np.int64)
    weights = np.full(flat.size, 1.0 / flat.size, dtype=np.float64)
    return PeriodicGaussianStencilSupport(
        grid_shape=shape,
        display_cell=np.diag(np.asarray(shape, dtype=np.float64)),
        gaussian_bandwidth=1.0,
        kernel_tail_tolerance=1.0e-8,
        cutoff_radius=2.0,
        active_flat_indices=flat,
        active_weights=weights,
        pre_normalization_sum=1.0,
        normalization_factor=1.0,
        periodic_image_contribution_count=int(flat.size),
        covariance=np.eye(3, dtype=np.float64),
        metadata={"fixture": True},
    )


def test_normative_bit_order_round_trip() -> None:
    block = (4, 3, 5)
    local = np.asarray([0, 1, 4, 5, 17, 59], dtype=np.int64)
    words = pack_local_indices(local, block)
    assert bitset_popcount(words) == local.size
    assert np.array_equal(unpack_local_bitset(words, block), local)
    integer = bitset_words_to_int(words)
    assert np.array_equal(bitset_int_to_words(integer, words.size), words)


def test_terminal_validity_bitset_is_exact() -> None:
    words = validity_bitset_for_extent((2, 3, 1), (4, 4, 4))
    local = unpack_local_bitset(words, (4, 4, 4))
    coordinates = np.column_stack(np.unravel_index(local, (4, 4, 4), order="C"))
    assert coordinates.shape[0] == 6
    assert np.all(coordinates[:, 0] < 2)
    assert np.all(coordinates[:, 1] < 3)
    assert np.all(coordinates[:, 2] < 1)


def test_routing_groups_offsets_and_terminal_classes() -> None:
    stencil = _stencil(
        (9, 10, 11),
        [(0, 0, 0), (1, 0, 0), (-1, 0, 0), (3, -2, 1), (-4, 2, -3)],
    )
    routing = build_periodic_kernel_block_routing(
        stencil, storage_block_shape=(4, 4, 4)
    )
    assert routing.block_grid_shape == (3, 3, 3)
    assert routing.axis_block_extents == ((4, 4, 1), (4, 4, 2), (4, 4, 3))
    assert routing.stencil_offset_count == stencil.stencil_offset_count
    assert routing.metadata["source_field_data_present"] is False
    signed = canonical_signed_stencil_offsets(stencil)
    assert np.array_equal(routing.signed_offsets, signed.astype(np.int32))
    assert sum(group.stencil_indices.size for group in routing.grouped_stencil_ranges) == signed.shape[0]
    assert routing.terminal_extent_classes.shape[0] == 8
    assert routing.retained_array_bytes > 0

    restored = PeriodicKernelBlockRouting.from_json_dict(routing.to_json_dict())
    assert restored.cache_identity == routing.cache_identity
    assert np.array_equal(restored.signed_offsets, routing.signed_offsets)
    assert np.array_equal(restored.terminal_validity_bitsets, routing.terminal_validity_bitsets)


def test_routing_cache_is_source_independent_and_bounded() -> None:
    clear_density_routing_cache()
    stencil = _stencil((8, 8, 8), [(0, 0, 0), (1, 0, 0), (-1, 0, 0)])
    first, first_hit = get_periodic_kernel_block_routing(
        stencil, storage_block_shape=(4, 4, 4)
    )
    second, second_hit = get_periodic_kernel_block_routing(
        stencil, storage_block_shape=(4, 4, 4)
    )
    assert first_hit is False
    assert second_hit is True
    assert first is second
    info = density_routing_cache_info()
    assert info.misses == 1
    assert info.hits == 1
    assert info.current_entries == 1
    assert info.retained_array_bytes == first.retained_array_bytes
