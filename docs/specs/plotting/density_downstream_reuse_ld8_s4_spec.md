---
title: "LD8-S4 Production Dispatch, Shared HDR Reuse, and Four-Species Acceptance Specification"
subtitle: "Normal-dispatch migration, exact finite-support planning, bounded fallback, and downstream contour queries"
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

# LD8-S4 - Production dispatch and downstream numerical reuse

**Package target:** `mdstats 0.19.58a0`  
**Status:** implemented; LD8 hybrid realization is the normal local-sparse production path  
**Primary modules:**

```text
mdstats.plotting.atomic_density
mdstats.plotting.framework_density
mdstats.plotting.density_hdr
mdstats.plotting.density_support_atlas
mdstats.plotting.density_packed_field
```

## Purpose

LD8-S4 completes migration of the exact LD8 finite-support estimator into normal atomic and framework density dispatch. It also removes repeated downstream work when several highest-density-region (HDR) shells are requested.

The stage preserves the scientific operator established by LD1--LD8-S3:

- the resolved logical grid is unchanged;
- periodic CIC deposition is unchanged;
- the normalized finite Gaussian stencil retains
  $\varepsilon_{\mathrm{tail}}=10^{-8}$;
- the effective CIC-plus-stencil broadening diagnostic is unchanged;
- inactive logical nodes remain exact implicit zeros;
- total measure, physical units, and HDR probability-mass semantics are unchanged.

S4 changes execution, storage, query reuse, and production dispatch only.

## Normal local-sparse dispatch

For `grid_backend="local_sparse"` and
`sparse_realization_mode="hybrid"`, normal atomic, framework-vertex, and
framework-edge preparation performs:

1. one global periodic CIC aggregation;
2. exact normalized stencil construction;
3. packed CIC source construction;
4. source-independent block routing;
5. exact field-specific finite-support atlas construction;
6. S3 hybrid tiled direct/FFT realization;
7. immediate packed positive-field output;
8. one global normalization and residual correction.

The returned field is

```python
PeriodicPackedBlockScalarField3D
```

and records

```text
production_backend = true
ld8_s4_normal_dispatch = true
sparse_realization_backend = "ld8_s3_hybrid"
```

The normal path may not allocate a complete dense logical field or a complete
source-node by stencil-offset pair array.

## Dispatch controls

```python
@dataclass(frozen=True, slots=True)
class DensityOptimizationOptions:
    sparse_evaluation_mode: Literal["optimized", "reference"]
    cache_stencil_supports: bool
    sparse_pair_chunk_size: int
    sparse_group_batch_size: int
    sparse_realization_mode: Literal["hybrid", "ld7"]
    allow_ld7_fallback: bool
    hybrid_compute_tile_shape: tuple[int, int, int]
    hybrid_min_fft_source_nodes: int
    hybrid_fft_workers: int
```

The defaults select the hybrid path. `sparse_realization_mode="ld7"` remains an
explicit compatibility and diagnostic control.

## Fallback policy

LD7 fallback is intentionally narrow. If `allow_ld7_fallback=True`, fallback is
permitted only for declared resource or complexity failures such as:

- support-atlas planning exceeding a hard limit;
- executor preflight exceeding a hard limit;
- package-owned allocation failure.

Identity, scientific, normalization, support, or invariant errors are never
hidden by fallback. In particular, `GraphAdapterError` propagates directly.

A fallback field records:

```text
ld8_s4_fallback_used = true
sparse_realization_backend = "ld7"
```

The production acceptance gate requires no fallback.

## Exact support realization optimization

### Scientific support

For occupied CIC nodes $\mathcal S$ and retained stencil offsets
$\mathcal K_\varepsilon$, the exact periodic support remains

$$
\mathcal A
=
\left\{
(\mathbf n+\boldsymbol\delta)\bmod\mathbf N:
\mathbf n\in\mathcal S,
\boldsymbol\delta\in\mathcal K_\varepsilon
\right\}.
$$

### Binary FFT execution path

For production-size stencils, each occupied source block is represented by a
binary local array and the signed stencil is represented by a binary kernel.
A zero-padded linear convolution counts how many source/stencil pairs reach
each lifted-brick node. The support is the set of nodes with a positive integer
count.

Because both inputs are binary, the exact convolution is integer-valued. Before
thresholding, the implementation requires

$$
\max_i |c_i-\operatorname{round}(c_i)|\le 10^{-6}.
$$

Failure of this certificate raises `GraphAdapterError`. Accepted values are
rounded and support is selected by $\operatorname{round}(c_i)\ge1$. The result is
then folded into canonical periodic target-block bitsets.

This is an execution optimization of exact binary dilation. The retained
Python-integer shift implementation remains the small-case and validation
oracle. `dilation_backend="auto"` selects binary FFT dilation for sufficiently
large stencils and bitset dilation for small fixtures.

The use of FFT convolution follows the standard convolution theorem and
zero-padding requirement for linear convolution; applying it to exact periodic
support planning is an mdstats-specific design. The general FFT algorithm is
classically associated with Cooley and Tukey (1965).

## Shared multi-HDR selection

### Contract

```python
@dataclass(frozen=True, slots=True)
class DensityHDRBatch:
    field_identity: str
    fractions: tuple[float, ...]
    details: tuple[DensityHDRDetails, ...]
    sorted_value_count: int
    workspace_bytes: int
    metadata: FrozenJSONMapping


def select_hdr_details_many(
    field: PeriodicPackedBlockScalarField3D,
    fractions: tuple[float, ...],
    *,
    chunk_size: int = 1_048_576,
    max_workspace_bytes: int = 512 * 1024**2,
) -> DensityHDRBatch
```

All requested fractions share one bounded ordering of the positive packed
values. A full cumulative-mass array is not retained. Chunked sums locate each
threshold and preserve exact tie handling.

For a requested mass fraction $q$, the threshold $t_q$ satisfies

$$
\sum_{\rho_i\ge t_q}\rho_i\Delta V\ge qM,
$$

with the same discrete semantics as the pre-S4 single-HDR method.

Input fractions must be finite, unique after canonical ordering, and strictly
between zero and one. Workspace preflight occurs before the ordering copy is
allocated.

## Lazy contour support

```python
@dataclass(frozen=True, slots=True)
class DensityContourSupport:
    field_identity: str
    fraction: float
    threshold: float
    candidate_block_indices: NDArray[np.int32]
    connected_component_labels: NDArray[np.int32] | None
    metadata: FrozenJSONMapping
```

Candidate blocks are selected from stored block extrema and periodic neighbor
relations. Components are computed only when requested. This stage plans
contour support; it does not yet replace the LD9 renderer or simplify meshes.

The block set is conservative: every contour-crossing cell is covered, while
blocks that cannot participate in the selected level are excluded from later
render planning.

## Packed-field additions

`PeriodicPackedBlockScalarField3D` provides:

```python
field.hdr_details_many((0.50, 0.80, 0.95))
field.contour_support_many((0.50, 0.80, 0.95), compute_components=False)
field.to_dense_values(max_nodes=...)
```

The packed field may retain selected atom indices and source sample positions
for downstream plotting provenance. These arrays are included in retained-byte
accounting and serialization.

## Resource and memory rules

- No complete logical-grid scalar array may be allocated by normal sparse dispatch.
- No complete fine-pair array may be allocated.
- Support-atlas realization is bounded by the approved S1 plan.
- Binary FFT dilation owns one source-block workspace at a time.
- Multi-HDR selection owns at most one packed-value ordering copy plus its declared chunk workspace.
- Contour components are lazy.
- Per-field cache entries remain source-independent; a field-specific support atlas is never placed in a global cache.

## Production acceptance gate

The canonical gate uses all 1,500 frames of the saved Na-LTA stress scene, all
four species, the effective CIC-aware refinement rule, and
$\varepsilon_{\mathrm{tail}}=10^{-8}$.

Required checks are:

1. Na, Si, Al, and O are all prepared through normal hybrid dispatch;
2. no field uses LD7 fallback;
3. every integral recovers its selected atomic measure within existing tolerance;
4. three HDR levels are resolved per field;
5. aggregate scientific preparation is at most 120 s;
6. aggregate speedup over the recorded 339.686 s LD7 baseline is at least 3x;
7. per-channel peak RSS is at most 1.5 GiB.

### Recorded `0.19.58a0` evidence

| Species | Grid | Scientific time | Multi-HDR | Active blocks | Nonzero nodes | Direct/FFT tiles | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Na | $540^3$ | 11.189 s | 0.101 s | 1,322 | 1,728,706 | 16 / 99 | 0.973 GiB |
| Si | $1038^3$ | 11.172 s | 0.114 s | 1,381 | 1,833,591 | 18 / 90 | 0.969 GiB |
| Al | $1037^3$ | 12.658 s | 0.120 s | 1,432 | 1,952,525 | 19 / 100 | 0.987 GiB |
| O | $646^3$ | 45.496 s | 0.556 s | 5,625 | 7,274,190 | 99 / 402 | 1.218 GiB |

The aggregate scientific time is

$$
80.515\ \mathrm{s},
$$

corresponding to a

$$
4.219\times
$$

speedup over the recorded LD7 baseline. All acceptance checks pass.

The full benchmark wall time includes resolution, HDR, contour-support queries,
garbage collection, monitoring, and reporting; the scientific gate applies to
the four normal-dispatch realization times specified above.

## Errors and edge cases

- unsupported dilation backend: `GraphStyleError`;
- binary FFT integer-certificate failure: `GraphAdapterError`;
- mismatched source, stencil, routing, atlas, or plan identities: `GraphAdapterError`;
- support or normalization disagreement: `GraphAdapterError`;
- authorized planning/resource exceedance: `GraphComplexityError`, optionally followed by recorded LD7 fallback;
- unauthorized fallback or any hidden scientific error: test failure;
- repeated or invalid HDR fractions: `GraphStyleError` or `GraphAdapterError` as defined by the HDR contract;
- HDR workspace overrun: `GraphComplexityError` before sorting allocation;
- partial terminal blocks and periodic face/edge/corner crossings must preserve exact support.

## Required tests

- hybrid normal dispatch versus LD7 on small periodic fields;
- public atomic preparation returning packed production fields;
- framework vertex and edge integration;
- fallback only for declared resource failures;
- identity errors never hidden by fallback;
- bitset and binary-FFT support equality, including partial terminal blocks;
- explicit modular-Minkowski-sum verification;
- deterministic packed output and metadata;
- exact batch HDR agreement with the retained single-level definition;
- bounded HDR workspace failure;
- nested contour support and periodic components;
- complete four-species production gate.

## External method attribution

- J. W. Cooley and J. W. Tukey, “An Algorithm for the Machine Calculation of Complex Fourier Series,” *Mathematics of Computation* **19**, 297--301 (1965).
- R. W. Hockney and J. W. Eastwood, *Computer Simulation Using Particles*, Taylor & Francis (1988), for cloud-in-cell deposition background.

The exact packed support atlas, binary integer-certificate rule, dispatch/fallback
contract, and shared HDR/contour reuse are mdstats-specific designs.
