---
title: "LD6 Multilevel Density Research-Gate Specification"
subtitle: "Phase-robust coarse/fine profiling, evidence policy, and the decision to retain the single-level architecture"
author: "mdstats development specification"
date: "2026-07-20"
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

# Status and scope

This specification governs architecture gate **LD6** for `mdstats`. It begins from
`mdstats 0.19.51a0`, where dense, single-level block-sparse, automatic backend
selection, periodic sparse rendering, exact scientific planning, and bounded sparse
optimization are complete for atomic, framework-vertex, and framework-edge density
fields.

**Implementation status: completed in `mdstats 0.19.52a0`.**

LD6 is an evidence gate. It does not add a production multilevel field. It adds a
bounded, deterministic research profiler that asks whether a dyadic coarse/fine
hierarchy offers enough additional benefit over the completed dense plus single-level
block-sparse architecture to justify a separate specification for transfer,
conservation, HDR integration, and crack-free coarse/fine contouring.

The implemented evidence policy concludes:

```text
retain_single_level
```

Therefore no production multilevel AMR implementation is authorized by this stage.

# Scientific and architectural question

The completed architecture already chooses between:

1. a dense periodic logical-node field for broad support; and
2. a single-level block-sparse field for localized support.

A multilevel hierarchy is justified only if representative fields remain poorly served
by both choices and if a phase-robust coarse/fine surrogate provides a substantial
additional storage reduction while preserving field and HDR semantics.

The patch-hierarchy motivation follows block-structured local adaptive refinement
(Berger and Colella, 1989). The periodic phase sweep, HDR-driven refinement rule,
conservative averaging, evidence thresholds, and decision policy are project-specific
`mdstats` definitions. The profiler is deliberately optimistic: passing it is necessary
but not sufficient for a future production hierarchy.

# Non-objectives

LD6 does not implement:

- multilevel field storage;
- prolongation or restriction operators used in production;
- coarse/fine Gaussian convolution;
- multilevel HDR integration;
- adaptive marching cubes or dual contouring;
- coarse/fine crack stitching;
- a new backend identifier;
- changes to the LD4 selector;
- changes to density values, meshes, or scene schemas.

No output of the profiler may be passed to a renderer as a scientific field.

# Public research API

```python
@dataclass(frozen=True)
class MultilevelResearchOptions:
    coarsening_factors: tuple[int, ...] = (2, 4)
    fine_mass_fractions: tuple[float, ...] = (0.90, 0.95, 0.99)
    block_shapes: tuple[tuple[int, int, int], ...] = (
        (4, 4, 4),
        (8, 8, 8),
        (16, 16, 16),
    )
    hdr_fractions: tuple[float, ...] = (0.50, 0.80, 0.95)
    max_relative_l1_error: float = 2.0e-3
    max_relative_linf_error: float = 1.0e-2
    max_relative_hdr_threshold_error: float = 1.0e-2
    max_hdr_mass_fraction_error: float = 1.0e-3
    minimum_incremental_storage_reduction: float = 2.0
    localized_active_fraction: float = 0.20
    broad_active_fraction: float = 0.50
    minimum_adoption_cases: int = 2
    max_profile_nodes: int = 4_000_000
    max_phase_evaluations: int = 2_000
    max_workspace_bytes: int = 512_000_000
```

Primary entry points are:

```python
profile_multilevel_field(field, *, options=None)
decide_multilevel_research(profiles, *, options=None)
```

The profiler accepts any realized scalar field satisfying `ScalarField3D` and
`PeriodicNodeFieldAccess`. All records are immutable, schema-versioned, canonically
JSON-serializable, and independent of renderer state.

# Baseline single-level profiling

For a logical grid with $N=N_1N_2N_3$ nodes, let $N_+$ be the positive-node count.
The active fraction is

$$
f_{+}=\frac{N_+}{N}.
$$

For the realized backend with $N_s$ stored scalar slots, the stored fraction is

$$
f_s=\frac{N_s}{N}.
$$

Support is classified as:

```text
f+ <= 0.20  -> localized
f+ >= 0.50  -> broad
otherwise   -> intermediate
```

The profiler recomputes exact single-level block-packing plans for $4^3$, $8^3$, and
$16^3$ blocks. This prevents block padding in one user-selected block size from being
misidentified as evidence for a multilevel hierarchy.

A field is considered already served by the completed architecture when:

- broad support uses the dense backend; or
- localized support uses block-sparse storage and either the realized block shape or
  one profiled single-level block shape stores no more than 20% of the logical grid.

This is an architecture-sufficiency classification, not a claim that one block shape
is universally fastest.

# Dyadic coarse/fine research surrogate

## Eligibility

A coarsening factor $r\in\{2,4\}$ is profiled only when every logical-grid dimension is
divisible by $r$. A production implementation for nondivisible hierarchies would
require a separate boundary and ownership specification.

## Fine-region selection

For requested fine mass fraction $q_f$, let $c_{q_f}$ be the field's existing HDR
threshold. Every positive node with

$$
\rho_i\ge c_{q_f}
$$

marks its coarse bin as fine-owned. A fine-owned bin retains all $r^3$ logical-node
slots exactly, including implicit zeros. This is conservative with respect to local
fine support and intentionally overestimates fine storage near threshold boundaries.

## Coarse-region restriction

A non-fine bin $B$ is represented by one piecewise-constant value

$$
\bar\rho_B=\frac{1}{r^3}\sum_{i\in B}\rho_i.
$$

The reconstructed fine-grid mass in the bin is exactly

$$
r^3\bar\rho_B\Delta V
=\sum_{i\in B}\rho_i\Delta V.
$$

Thus the surrogate preserves total measure to floating-point tolerance. Fine-owned
bins are exact; only coarse-owned bins contribute approximation error.

## Periodic coarse-grid phase sweep

A dyadic hierarchy anchored at one logical origin is not translation-neutral. For each
factor $r$, LD6 evaluates every periodic coarse-grid phase

$$
\mathbf p\in\{0,\ldots,r-1\}^3.
$$

There are $r^3$ phases. A candidate passes only when **every** phase satisfies the
scientific tolerances. Storage benefit is evaluated using the worst phase. This avoids
approving a hierarchy whose apparent advantage depends on an arbitrary coarse-grid
origin.

# Error and HDR criteria

For the reconstructed fine-grid surrogate $\tilde\rho$, LD6 requires

$$
\frac{\|\tilde\rho-\rho\|_1}{\|\rho\|_1}
\le 2\times10^{-3},
$$

$$
\frac{\|\tilde\rho-\rho\|_\infty}{\max\rho}
\le 10^{-2}.
$$

For HDR fractions $q\in\{0.50,0.80,0.95\}$,

$$
\frac{|\tilde c_q-c_q|}{\max\rho}\le10^{-2},
$$

and the achieved-mass-fraction difference is at most $10^{-3}$.

Total-measure error is bounded by

$$
|\tilde M-M|\le5\times10^{-13}\max(1,M).
$$

HDR calculations account exactly for the multiplicity $r^3$ of one coarse value.
Implicit zero nodes do not affect positive thresholds but are included in the $L^1$
and $L^\infty$ reconstruction error.

# Optimistic storage estimate

For one phase, let $N_f$ be the number of fine-owned bins and $N_c$ the number of
positive coarse-owned bins. The optimistic value count is

$$
N_{\mathrm{ML}}=r^3N_f+N_c.
$$

The estimated bytes include float64 values and one three-int64 region index per fine or
coarse region:

$$
B_{\mathrm{ML}}
=8N_{\mathrm{ML}}+24(N_f+N_c).
$$

This estimate excludes transfer stencils, refinement masks, tree links, ghost zones,
coarse/fine interpolation state, and adaptive-mesh contouring state. It is therefore a
lower bound. Failure to show a strong gain under this optimistic estimate is decisive
evidence against immediate multilevel implementation.

Two reductions are reported:

1. reduction relative to the currently realized field; and
2. incremental reduction relative to the best profiled single-level block shape.

The adoption gate uses the second and requires a worst-phase reduction of at least
$2\times$.

# Evidence decision policy

The benchmark set must include at least one localized and one broad field. The outcome
is:

```text
insufficient_evidence
    if localized or broad coverage is missing

write_multilevel_specification
    if at least two fields are not adequately served by the completed
    single-level architecture and each has a phase-robust candidate with
    >= 2x incremental storage reduction within every scientific tolerance

retain_single_level
    otherwise
```

This decision is intentionally conservative. One promising field does not justify the
new conservation and contouring machinery required by a production hierarchy.

# Implemented benchmark matrix

The deterministic benchmark uses a $48^3$ logical grid and covers:

1. a localized atomic cloud;
2. separated framework-vertex clouds;
3. overlapping oxygen clouds;
4. multimodal Na hopping occupancy;
5. projected framework-edge density;
6. atom-resolved framework-path density;
7. a smooth broad mobile-ion field.

The observed decision is `retain_single_level`.

| Field | Production backend | Active fraction | Current stored fraction | Best profiled single-level values | Best passing multilevel candidate |
|---|---:|---:|---:|---:|---:|
| atomic localized | sparse | 0.0136 | 0.1481 | 3,136 | none |
| framework vertices separated | sparse | 0.0321 | 0.4815 | 8,192 | none |
| oxygen clouds overlapping | sparse | 0.0300 | 0.1852 | 6,400 | none |
| Na multimodal hopping | sparse | 0.0438 | 0.1481 | 9,280 | none |
| framework edges projected | sparse | 0.1009 | 0.7037 | 23,360 | none |
| framework atomic paths | sparse | 0.1148 | 0.7037 | 22,016 | $r=4$, $q_f=0.99$, 2.90x |
| mobile ion broad | dense | 1.0000 | 1.0000 | 110,592 | $r=2$, $q_f=0.90$, 1.09x |

The projected-edge field is the only representative field not classified as adequately
served by the current backend or an alternative single-level block size. It has no
coarse/fine candidate that passes all scientific tolerances. The atom-resolved path
field has a passing optimistic candidate, but the best $4^3$ single-level block plan is
already within the localized-storage policy anchor. The broad field remains properly
served by dense storage and offers only 1.09x worst-phase incremental reduction.

The required two insufficient cases with at least 2x phase-robust incremental benefit
are therefore absent.

# Resource and failure policy

Profiling is bounded independently of production field preparation:

```text
max_profile_nodes          4,000,000
max_phase_evaluations      2,000
max_workspace_bytes        512,000,000
```

The profiler fails before candidate evaluation when node or workspace limits are
exceeded. It never alters a field, backend decision, cache, renderer, or scene plan.

Candidate factors incompatible with the logical shape are skipped and recorded by the
absence of that factor. A benchmark with no localized or no broad field returns
`insufficient_evidence` rather than a positive or negative architecture decision.

# Determinism and serialization

Positive nodes are collected through the public node-access protocol and sorted by
global C-order logical index. Coarse phases, factors, fine mass fractions, block
shapes, and HDR fractions are evaluated in sorted deterministic order.

Every options, phase, candidate, block, field, and decision record is immutable and
schema-versioned. Full field profiles round-trip through canonical JSON when phase
records are included. Decision records always round-trip through canonical JSON.

# Focused validation

LD6 focused tests certify:

- options and evidence-record JSON round trips;
- exact mass preservation;
- exact broad-uniform coarse reconstruction;
- deterministic repeated profiles;
- every periodic phase for factors two and four;
- factor skipping for incompatible logical shapes;
- bounded node-resource failure;
- localized/broad benchmark coverage requirements;
- `retain_single_level` and `write_multilevel_specification` policy branches;
- unchanged dense and sparse scientific production paths;
- unchanged LD4 selector and LD5 cache behavior.

# Completion decision

LD6 completes the adaptive-density roadmap with the following normative conclusion:

> Retain the single-level dense plus block-sparse architecture. Do not implement a
> general multilevel hierarchy at this time.

Future multilevel work may be reopened only with new representative evidence showing
at least two production-relevant cases that fail the current resource policy and retain
at least 2x phase-robust incremental benefit under the LD6 tolerances. Such work must
begin with a new specification for conservative transfer, multilevel HDR integration,
periodic coarse/fine ownership, and crack-free adaptive contouring.

# Reference

1. Berger, M. J., and P. Colella. "Local Adaptive Mesh Refinement for Shock
   Hydrodynamics." *Journal of Computational Physics* **82** (1989): 64-84.
   DOI: 10.1016/0021-9991(89)90035-1.
