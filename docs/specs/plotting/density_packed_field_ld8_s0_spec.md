---
title: "LD8-S0 Packed Scientific Field Contract Specification"
subtitle: "Positive-value block packing, backend-neutral access, serialization, and S2 realization target"
author: "mdstats development specification"
date: "2026-07-21"
geometry: margin=0.78in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \usepackage{fvextra}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
    \RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small}
---

# LD8-S0 - Packed scientific scalar-field contract

**Package target:** `mdstats 0.19.55a0`  
**Status:** contract and reference adapter implemented; target-owned production realization deferred to LD8-S2  
**Primary module:** `mdstats.plotting.density_packed_field`

## Purpose

The existing fixed-block sparse field stores every valid value inside each active block, including many exact zeros. LD8 defines a packed positive-value field that retains one occupancy bit per local node and stores `float64` values only for positive nodes.

S0 implements the immutable record, public field protocol, serialization, and an adapter from the current sparse reference field. It does not yet change the production realization path.

## Record

```python
@dataclass(frozen=True, slots=True)
class PeriodicPackedBlockScalarField3D:
    logical_grid_shape: tuple[int, int, int]
    storage_block_shape: tuple[int, int, int]
    active_block_indices: NDArray[np.int32]
    occupancy_bitsets: NDArray[np.uint64]
    block_value_offsets: NDArray[np.int64]
    packed_values: NDArray[np.float64]
    block_min_values: NDArray[np.float64]
    block_max_values: NDArray[np.float64]
    display_cell: NDArray[np.float64]
    total_measure: float
    voxel_volume: float
    physical_units: str
    source_provenance: DensitySourceProvenance
    metadata: FrozenJSONMapping
```

Schema:

```text
mdstats.periodic-packed-block-scalar-field.v1
```

## Invariants

- block indices are unique and globally C-order sorted;
- every active block has at least one positive node;
- occupancy uses the normative S0 local bit layout;
- `np.diff(block_value_offsets)` equals the occupancy popcount of each block;
- packed values are finite and strictly positive;
- values within a block follow increasing local C-order bit index;
- `block_min_values` and `block_max_values` equal the realized positive extrema;
- terminal invalid local positions are always zero and unoccupied;
- the scientific integral satisfies
  
  $$
  \Delta V\sum_i\rho_i=M
  $$
  
  within the existing normalization tolerance.

Inactive nodes and unoccupied local positions are exact implicit zeros.

## Public field protocols

The record implements the backend-neutral scalar-field and periodic-node-access contracts used by current density operations.

Required behavior includes:

```python
field.integral()
field.hdr_details(fraction)
field.iter_positive_nodes(...)
field.gather_node_values(flat_indices)
field.to_dense_values(max_nodes=...)
field.storage_summary()
```

`gather_node_values` applies periodic modulo to requested global flat indices through logical coordinates, matching the existing periodic-node protocol.

Dense conversion is a guarded debugging operation and fails when the caller's `max_nodes` limit would be exceeded.

## Reference adapter

```python
pack_sparse_reference_field(
    field: PeriodicBlockScalarField3D,
) -> PeriodicPackedBlockScalarField3D
```

The adapter preserves:

- exact positive logical node indices;
- exact positive `float64` values;
- total measure and voxel volume;
- display cell and physical units;
- source provenance;
- canonical block and local-node order.

This adapter is the S0 compatibility oracle. LD8-S2 will produce the packed field directly as each target block is completed.

## Memory model

For $N_b$ active blocks, $N_+$ positive nodes, block-word count $W$, and four-byte block coordinates, retained array bytes are approximately

$$
12N_b+8WN_b+8(N_b+1)+8N_++16N_b,
$$

excluding small object metadata. The fixed-block representation instead stores approximately

$$
8N_bB_xB_yB_z
$$

value bytes plus masks and coordinates.

Packed storage is therefore favored when the positive-node fill fraction inside active blocks is low. Scientific values remain `float64`; `float32` is not authorized for scientific fields.

## HDR compatibility

S0 preserves the current exact HDR semantics. The compatibility implementation may collect and sort positive values. It is not the final LD8-S4 multi-selection implementation.

Tie behavior remains deterministic: a threshold includes all nodes with values at least the selected threshold, and the record reports requested fraction, achieved fraction, selected measure, selected count, and threshold tie count.

## Serialization

Canonical JSON includes all arrays required to reproduce the field. Arrays are serialized in normative block/local order. Deserialization revalidates every invariant and reconstructs immutable C-contiguous arrays.

The SHA-256 content identity includes:

- schema version;
- logical and storage shapes;
- block indices;
- occupancy bitsets;
- offsets;
- packed values;
- extrema;
- display cell;
- measure and voxel volume;
- physical units.

## Failure behavior

Construction rejects:

- malformed shapes or cells;
- unsorted or duplicate blocks;
- invalid terminal bits;
- occupancy/value-count mismatches;
- zero, negative, NaN, or infinite packed values;
- incorrect extrema;
- nonpositive voxel volume or measure;
- integral mismatch;
- malformed provenance or schema;
- oversized dense debugging conversion.

## Focused validation

Tests verify:

- exact positive-node identity and values against a fixed-block source;
- exact integral and HDR behavior;
- periodic gathers;
- terminal partial blocks;
- storage summaries;
- JSON and content-identity round trips;
- rejection of malformed occupancy, offsets, extrema, and measure.

## Scope exclusions

S0 does not yet:

- realize a field directly from the support atlas;
- execute direct or FFT convolution;
- normalize target blocks;
- compute exact multi-HDR thresholds without sorting;
- become the production default.

Those changes are authorized only in LD8-S2 through S4 after equivalence and performance gates pass.
