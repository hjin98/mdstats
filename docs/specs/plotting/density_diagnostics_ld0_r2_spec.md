---
title: "Density Registration and Resolution Diagnostics Specification"
subtitle: "LD0-R2 laboratory-cell validation, deterministic periodic means, spread references, reciprocal resolution, and node coordinates"
author: "mdstats"
date: "2026-07-20"
geometry: margin=0.80in
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

# Purpose and status

This document is the normative stage specification for **LD0-R2** of the
`mdstats` dynamical-framework and density plotting architecture.

Target package version:

```text
0.19.41a0
```

Primary implementation module:

```text
mdstats/plotting/density_diagnostics.py
```

Integrated modules:

```text
mdstats/plotting/atomic_density.py
mdstats/plotting/framework_density.py
mdstats/plotting/framework_dynamics.py
```

LD0-R2 adds diagnostic and registration policy around the existing dense field. It
does not change CIC deposition, the `legacy_spectral_v1` Fourier multiplier,
normalization, scientific HDR thresholds, dense mesh extraction, or Plotly trace
composition. The only intentional rendering correction is that diagnostic density
cloud points now use the logical-node positions $i/N_i$ rather than displaced
half-cell centers.

# Authority

The governing plan is:

```text
docs/arch_manuals/mdstats_dynamical_framework_density_architecture_standard.md
```

This stage specification refines only LD0-R2. The architecture standard governs if
the two documents conflict.

# Motivation

The previous implementation had four unresolved scientific risks:

1. variable-cell laboratory density folded Cartesian samples into a display cell
   with a different periodic identification;
2. the periodic mean used one circular start and emitted no convergence or
   nonuniqueness diagnostics;
3. adaptive smearing included every item in its spread quantile, even when the
   periodic mean was ambiguous or did not converge;
4. the lattice-vector interval $h_{\max}$ did not expose adverse reciprocal-plane
   resolution in a skew sampling lattice.

A separate rendering inconsistency placed voxel-cloud points at
$(i+1/2)/N_i$ although CIC values and marching-cubes samples live at $i/N_i$.

# Scope

## Included

LD0-R2 provides:

- exact architecture-standard cell-equivalence reports;
- rejection of variable-cell laboratory **periodic density**;
- continued support for variable-cell laboratory trajectories and mean geometry;
- deterministic multi-start periodic Fréchet/Karcher means;
- exact chunked weighted-sample medoid selection;
- convergence, objective, multiplicity, and ambiguity diagnostics;
- validity-filtered per-item positional spread;
- explicit `numpy.quantile(method="linear")` policy;
- minimum valid-count and valid-fraction rules;
- explicit zero-spread handling;
- a certified shortest reciprocal sampling-vector diagnostic;
- density metadata for means, spreads, reciprocal resolution, and registration;
- atomic-mean-graph diagnostics;
- logical-node voxel-cloud coordinates;
- focused numerical, registration, and rendering tests.

## Excluded

LD0-R2 does not provide:

- the three-phase global resource planner (LD0-R3);
- `discrete_periodized_v1` (LD0-K);
- CIC-plus-stencil effective broadening (LD0-B);
- sparse CIC, block storage, sparse HDR, or sparse meshing (LD1-LD2);
- a real-space covering-radius diagnostic;
- a nonperiodic laboratory Cartesian-box density estimator.

# Dependency direction

```text
density_diagnostics
    -> analysis._neighbors.minimum_image_geometry
    -> graph_errors
    -> NumPy / Python standard library
```

The module imports neither Plotly nor scikit-image and contains no density
estimator.

# Laboratory periodic-density validation

## Geometry

At frame $t$, laboratory Cartesian positions are

$$
\mathbf x_t=\mathbf f_tH_t.
$$

Their physical periodic images differ by $\mathbf nH_t$. A density represented on
display cell $H_d$ identifies points modulo $\mathbf nH_d$. These quotient spaces
are the same only when the selected source cells equal the display cell within the
declared tolerance.

## Cell-equivalence rule

For every selected frame,

$$
\|H_t-H_d\|_F
\le
10^{-10}\ \text{\AA}
+10^{-10}\|H_d\|_F.
$$

The report is:

```python
@dataclass(frozen=True, slots=True)
class CellEquivalenceReport:
    equivalent: bool
    tolerance: float
    maximum_mismatch: float
    maximum_mismatch_frame_position: int
    mismatch_by_frame: NDArray[np.float64]
    schema_version: str
```

Public functions:

```python
evaluate_cell_equivalence(source_cells, display_cell) -> CellEquivalenceReport

require_equivalent_laboratory_density_cells(
    source_cells,
    display_cell,
    *,
    field_context,
) -> CellEquivalenceReport
```

The second function raises `GraphAdapterError` when the rule fails.

## Application boundary

The check is required when all of the following hold:

- a periodic density channel is requested;
- registration is `laboratory`;
- selected source cells are not display-equivalent.

The check does **not** reject:

- laboratory trajectories;
- laboratory mean-framework geometry;
- material density;
- framework-registered material density;
- laboratory density in a constant display-equivalent cell.

# Periodic Fréchet/Karcher mean

## Mathematical objective

For folded fractional samples $\mathbf f_t$, Cartesian samples
$\mathbf x_t=\mathbf f_tH$, normalized weights $w_t$, and periodic geodesic distance
$d_{\mathrm{MIC}}$, the mean minimizes

$$
J(\mathbf x)=\sum_tw_t d_{\mathrm{MIC}}(\mathbf x_t,\mathbf x)^2.
$$

An iteration updates by the weighted mean minimum-image tangent vector,

$$
\Delta\mathbf x
=
\sum_tw_t\operatorname{MIC}(\mathbf x_t-\mathbf x),
\qquad
\mathbf x\leftarrow\mathbf x+\Delta\mathbf x,
$$

followed by periodic folding.

This is the flat-torus specialization of the Fréchet/Karcher mean construction
(Fréchet, 1948; Karcher, 1977). The deterministic start policy, ambiguity test, and
chunked medoid implementation are project-specific.

## Numerical policy

```python
@dataclass(frozen=True, slots=True)
class PeriodicMeanPolicy:
    max_iterations: int = 128
    update_tolerance_scale: float = 1e-12
    objective_relative_tolerance: float = 1e-12
    mean_separation_tolerance_scale: float = 1e-8
    medoid_block_size: int = 64
    minimum_valid_reference_fraction: float = 0.50
    minimum_valid_reference_count: int = 1
```

With

$$
L_{\mathrm{ref}}
=
\max\left(1\ \text{\AA},\max_i\|\mathbf a_i\|_2\right),
$$

the update and solution-separation tolerances are the corresponding scale factors
times $L_{\mathrm{ref}}$.

## Deterministic starts

Starts are generated in this exact order:

1. component-wise circular mean on periodic axes and weighted linear mean otherwise;
2. weighted sample medoid;
3. first sample in stable frame order;
4. sample farthest from the medoid, with `numpy.argmax` first-index tie breaking.

Starts equivalent within the update tolerance are removed in stable order.

## Exact bounded-memory medoid

The weighted medoid is the sample $j$ minimizing

$$
J_j=\sum_tw_t d_{\mathrm{MIC}}(\mathbf x_t,\mathbf x_j)^2.
$$

The implementation evaluates candidate samples in fixed blocks. It is exact and has
$O(T^2)$ distance work but only $O(BT)$ temporary storage for block size $B$. No
$T\times T$ distance matrix is allocated.

## Solution selection and ambiguity

Every unique start is iterated. If at least one start converges, the converged
solution with smallest objective is selected; otherwise the lowest-objective final
iterate is returned and marked nonconverged. Objective ties use start order.

Converged solutions are deduplicated by minimum-image separation. The selected mean
is ambiguous when at least two separated converged solutions have objectives agreeing
within

$$
|J_a-J_b|
\le
10^{-12}\max(1,|J_{\min}|).
$$

## Result record

```python
@dataclass(frozen=True, slots=True)
class PeriodicMeanDiagnostic:
    mean_cartesian: NDArray[np.float64]
    mean_fractional: NDArray[np.float64]
    mean_converged: bool
    iteration_count: int
    final_update_norm: float
    objective_value: float
    mean_ambiguity_detected: bool
    candidate_solution_count: int
    start_count: int
    schema_version: str
```

A mean is valid for the adaptive spread reference only when it converged and is not
ambiguous.

# Per-item spread and automatic reference

For item $i$, with selected mean $\bar{\mathbf x}_i$,

$$
s_i
=
\sqrt{
\frac{1}{3}
\sum_tw_t
\|\operatorname{MIC}(\mathbf x_{ti}-\bar{\mathbf x}_i)\|_2^2
}.
$$

Values no larger than $10^{-12}L_{\mathrm{ref}}$ are stored as zero.

The record is:

```python
@dataclass(frozen=True, slots=True)
class PeriodicSpreadDiagnostics:
    standard_deviations: NDArray[np.float64]
    valid_reference_mask: NDArray[np.bool_]
    means_cartesian: NDArray[np.float64]
    mean_diagnostics: tuple[PeriodicMeanDiagnostic, ...]
    reference_standard_deviation: float | None
    quantile: float
    quantile_method: str
    valid_reference_count: int
    required_reference_count: int
    adaptive_target_defined: bool
    schema_version: str
```

The required valid count is

$$
N_{\mathrm{required}}
=
\max\left(
N_{\min},
\left\lceil f_{\min}N_{\mathrm{items}}\right\rceil
\right).
$$

When enough valid items exist and at least two frames are present,

$$
s_q
=
Q_q\left(\{s_i:i\text{ valid}\}\right),
$$

using exactly:

```python
numpy.quantile(valid_values, q, method="linear")
```

If the valid count is insufficient, `reference_standard_deviation=None` and
adaptive refinement is disabled with a warning. If $s_q=0$, the reference is stored
as zero but `adaptive_target_defined=False`; nominal or explicit resolution is
retained and unbounded refinement is forbidden.

LD0-R2 retains the versioned baseline broadening rule
`gaussian_sigma_v1`. It does not yet substitute the future CIC-plus-stencil width.

# Reciprocal-resolution diagnostic

## Sampling lattice

For row-vector cell matrix $H$ and logical grid $N=(N_1,N_2,N_3)$, the real-space
sampling basis is

$$
B=\operatorname{diag}(N)^{-1}H.
$$

Its angular reciprocal basis is

$$
G=2\pi B^{-T}
=2\pi\operatorname{diag}(N)H^{-T}.
$$

For nonzero $\mathbf m\in\mathbb Z^3$, the reciprocal sampling vector is

$$
\mathbf k(\mathbf m)=\mathbf mG.
$$

The diagnostic uses

$$
k_{\min}=\min_{\mathbf m\ne0}\|\mathbf mG\|_2,
\qquad
h_{\mathrm{reciprocal}}=\frac{2\pi}{k_{\min}}.
$$

This is a reciprocal-plane/Nyquist diagnostic. It is not a real-space nearest-node
distance or covering radius.

## Certified enumeration

Let

$$
U=\min_i\|\mathbf g_i\|_2
$$

be the shortest reciprocal basis-row norm, and let $s_{\min}(G)$ be the smallest
singular value. Since

$$
\|\mathbf mG\|_2\ge s_{\min}(G)\|\mathbf m\|_2,
$$

no integer vector with

$$
\|\mathbf m\|_2>U/s_{\min}(G)
$$

can improve $U$. The implementation exhaustively enumerates the containing integer
cube, removes sign duplicates by requiring the first nonzero component to be
positive, and resolves equal norms lexicographically. This proof and enumeration
policy are project-specific.

The result records the integer vector, Cartesian reciprocal vector, norm, derived
interval, and enumeration bound.

# Metadata integration

Every atomic and framework density field records:

```text
h_reciprocal
shortest reciprocal integer and Cartesian vectors
reciprocal enumeration bound
sample SD quantile and method
all per-item sample SDs
periodic-mean convergence flags
periodic-mean ambiguity flags
iteration counts and final update norms
objective values and candidate-solution counts
valid-reference mask/count/requirement
adaptive_target_defined
```

Laboratory density and scene metadata additionally record the cell-equivalence
tolerance and maximum mismatch.

The atomic mean graph records convergence, ambiguity, iteration, and candidate-count
tuples for its mean vertices.

# Logical-node cloud correction

A density array entry `values[i, j, k]` is located at

$$
\mathbf f_{ijk}
=
\left(\frac{i}{N_1},\frac{j}{N_2},\frac{k}{N_3}\right),
\qquad
\mathbf x_{ijk}=\mathbf f_{ijk}H_d.
$$

The previous fallback used $(i+1/2)/N_i$. LD0-R2 removes the half-grid displacement.
This correction intentionally changes voxel-cloud rendering coordinates but not field
values, thresholds, meshes, or sample positions.

# Input constraints and failures

The diagnostics require:

- finite nonsingular $3\times3$ cells;
- nonempty finite sample arrays ending in Cartesian/fractional dimension three;
- nonnegative weights with positive sum;
- a Boolean PBC vector of shape `(3,)`;
- positive integer grid dimensions;
- finite positive numerical tolerances;
- a certified reciprocal enumeration bound not exceeding the hard safety ceiling.

Failures use:

- `GraphAdapterError` for malformed scientific inputs or invalid laboratory periodic
  identification;
- `GraphStyleError` for invalid policy values;
- `GraphComplexityError` when reciprocal enumeration exceeds its certified safety
  ceiling.

No failure changes registration, drops frames/items, silently loosens tolerances, or
changes the density estimator.

# Determinism

For identical inputs on one supported platform/library version, the following are
stable:

- start generation and duplicate removal;
- medoid and farthest-sample tie breaking;
- mean selection;
- ambiguity classification;
- valid-reference masks;
- reciprocal integer-vector selection;
- node-cloud logical indices and coordinates;
- metadata tuple ordering.

# Compatibility

LD0-R2 must preserve, within the architecture-standard tolerances:

- dense atomic values and integrals;
- framework vertex and edge values and integrals;
- HDR thresholds;
- dense mesh vertices and faces;
- field keys, labels, provenance, and normalization.

Adaptive grid choice may intentionally differ only when the old reference included a
nonconverged/ambiguous mean or attempted refinement from a zero spread. Voxel-cloud
Cartesian positions intentionally differ by the corrected half-grid offset.

# Focused tests

Required tests include:

1. cell-equivalent and nonequivalent source-cell reports;
2. rejection of atomic and framework variable-cell laboratory density;
3. continued variable-cell laboratory trajectory support;
4. periodic boundary-crossing mean convergence and image invariance;
5. equal-weight antipodal ambiguity;
6. controlled nonconvergence under a one-iteration policy;
7. exclusion of ambiguous means from the spread quantile;
8. insufficient valid-reference policy;
9. zero-spread target handling;
10. orthogonal reciprocal interval equality with the longest axis interval;
11. skew-cell shortest-vector agreement with exhaustive reference enumeration;
12. exact logical-node voxel-cloud coordinates;
13. existing dense field, mesh, framework scene, and contract regression suites.

# Acceptance gate

LD0-R2 passes only when:

```text
variable-cell laboratory periodic density is rejected
variable-cell laboratory trajectories pass
mean fixtures have stable exact diagnostic flags/counts
invalid means are excluded under the 50% / one-item policy
node-cloud fractional coordinates equal i/N_i within 1e-14
legacy dense arrays satisfy relative L1 <= 2e-11
legacy dense arrays satisfy relative Linf <= 5e-11
integrals differ by <= 5e-13 * max(1, total_measure)
focused tests and Ruff checks pass
wheel build and clean import pass
```

# Stop conditions

Do not proceed to LD0-R3 if:

- a density channel can bypass laboratory cell validation;
- the mean result depends on hash order or unbounded pairwise storage;
- ambiguous/nonconverged means still influence the automatic spread reference;
- zero spread triggers progressively finer allocation;
- the reciprocal diagnostic is approximate without declaring that fact;
- cloud correction changes scientific field values or dense mesh geometry;
- diagnostic metadata contains nonfinite values or unstable ordering.

# References

1. Fréchet, M. "Les éléments aléatoires de nature quelconque dans un espace
   distancié." *Annales de l'Institut Henri Poincaré* **10** (1948): 215-310.
2. Karcher, H. "Riemannian Center of Mass and Mollifier Smoothing." *Communications
   on Pure and Applied Mathematics* **30** (1977): 509-541.
   DOI: 10.1002/cpa.3160300502.
3. Hockney, R. W., and J. W. Eastwood. *Computer Simulation Using Particles*.
   Taylor & Francis, 1988. The existing CIC estimator is unchanged by LD0-R2.
