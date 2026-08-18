---
title: "Fixed-Kernel Scientific Density-Grid Refinement"
subtitle: "Stage 11E-GR3 implementation specification"
author: "mdstats"
date: "2026-07-27"
version: "0.20.26a0"
status: "implemented under architecture revision 56"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.82in
fontsize: 10pt
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose

Stage 11E-GR3 replaces pilot-only hard-coded grid comparisons with one
source-bound, fixed-kernel scientific refinement contract. It asks whether a
single density hypothesis is numerically stable as only the logical periodic
grid is refined.

GR3 does **not** select a bandwidth, alter the Gaussian covariance, choose a
rendering backend, simplify a mesh, or admit a browser scene. Those operations
belong to other stages. A visual field may be useful without satisfying GR3,
and a GR3 certificate may be generated without Plotly or any rendering library.

The implementation owner is:

```text
mdstats.analysis.density.refinement
```

# Scope and ownership

GR3 consumes:

- one source/signature context;
- one SAMP0 cross-fit partition signature;
- one fixed positive-definite Cartesian kernel covariance and its signature;
- one scientific resource-policy signature;
- GR0 cell-metric geometry and numerical diagnostics;
- one GR1 exactly nested logical-grid ladder;
- per-level field evidence and, when available, E2 basin and corridor evidence.

GR3 emits orthogonal signed decisions for:

1. scalar density-field resolution;
2. basin-catalog convergence; and
3. corridor/bottleneck convergence.

A converged basin catalog does not imply a converged corridor catalog. Missing
or unstable corridor evidence therefore blocks saddle or barrier promotion but
does not erase separately converged basin evidence.

# Persistent runtime records

The public GR3 records are immutable, canonically serializable, and SHA-256
signed:

```text
GridConvergenceStoppingPolicy
ScientificGridRefinementPolicy
DensityFieldLevelEvidence
FeatureGridCorrespondence
BasinGridPairComparison
CorridorGridLevelEvidence
CorridorGridPairComparison
DensityFieldResolutionCertificate
BasinGridConvergenceCertificate
CorridorGridConvergenceCertificate
ScientificGridRefinementBundle
```

Every `from_json_dict` replay validates schema and signature. Tampered payloads
fail with `DensityNumericalSerializationError` rather than being accepted as
new evidence.

# Frozen numerical hypothesis

`ScientificGridRefinementPolicy` binds the complete numerical hypothesis before
refinement begins:

```text
fixed_kernel_covariance_cartesian
fixed_kernel_signature
scientific_resource_policy_signature
crossfit_partition_signature
coarsest_interval
GridConvergenceStoppingPolicy
FeatureCorrespondencePolicy
metadata
```

The covariance is symmetrized and required to be positive definite. Its
smallest standard-deviation scale is

$$
\sigma_{\min}=\sqrt{\lambda_{\min}(\Sigma_K)}.
$$

A kernel-signature change at any level is a hard input error. Dense and
local-sparse field realizations may be compared only when they represent the
same source, weights, kernel, logical grid, and normalization semantics.
Backend identity is retained as evidence but is not itself a convergence
criterion.

# `stage11_grid_stopping_v1`

The initial `GridConvergenceStoppingPolicy` preset is identified exactly as:

```text
stage11_grid_stopping_v1
```

Its normative defaults are:

| Quantity | Default |
|---|---:|
| Grid refinement factor | 2 |
| Physical-resolution gate | $\Delta_{\max}/\sigma_{\min}\le 0.5$ |
| Maximum number of levels | 8 |
| Consecutive passing level pairs | 2 |
| Maximum probability-field $L^1$ change | 0.02 |
| Maximum normalization residual | $10^{-6}$ |
| Basin count | unchanged |
| Maximum basin-anchor motion | $0.10\sigma_{\min}$ |
| Minimum matched-basin overlap | 0.95 |
| Maximum basin-probability change | 0.02 |
| Basin ambiguity/split/merge/unmatched | prohibited |
| Corridor adjacency | unchanged |
| Minimum matched-corridor overlap | 0.90 |
| Maximum bottleneck motion | $0.15\sigma_{\min}$ |
| Maximum relative width change | 0.10 |
| Maximum relative bottleneck-density change | 0.10 |
| Corridor ambiguity/split/merge | prohibited |

These are versioned conservative defaults, not universal physical constants.
Any altered preset must receive a new policy identifier and regression fixtures.
An explicit custom policy retains all resolved numerical values in its signed
certificate.

# Deterministic nested ladder

`plan_scientific_grid_refinement` delegates logical-grid construction to GR1.
For the initial preset, each level refines every grid axis by exactly a factor of
two. The realized Cartesian interval is computed in the full cell metric.

The minimum physical-resolution interval is

$$
\Delta_{\mathrm{physical}}
=0.5\sigma_{\min}.
$$

Because GR3 requires **two consecutive** passing level-pair comparisons after
that gate, the planner requests an additional post-gate level. With refinement
factor $r$ and $m$ required consecutive comparisons,

$$
\Delta_{\mathrm{requested}}
=
\frac{\Delta_{\mathrm{physical}}}{r^{m-1}}.
$$

For `stage11_grid_stopping_v1`, this is
$\Delta_{\mathrm{requested}}=0.25\sigma_{\min}$. This is not a stronger
physical-resolution assertion; it merely ensures that two eligible comparisons
can exist.

The ladder preserves GR1 status:

```text
target_reached
budget_limited
level_limited
```

A finest affordable level is retained as diagnostic evidence but cannot be
silently promoted to convergence.

# Field-level evidence

`DensityFieldLevelEvidence` binds each logical-grid level to:

```text
level index and grid shape
realized Cartesian intervals
field-estimate signature
fixed-kernel signature
backend label
probability and number normalization residuals
probability-field L1 and optional Linf changes from the previous level
CIC covariance
periodic Gaussian-stencil covariance
effective artificial-broadening covariance
metadata
```

For direct periodized-Gaussian estimators that do not use CIC deposition or a
separate discrete convolution, CIC and stencil covariance are explicitly zero.
Nested-field comparisons restrict the fine field to the exactly corresponding
coarse nodes; interpolation is not introduced as an unrecorded hypothesis.

A field pair is eligible only when the fine level satisfies
$\Delta_{\max}/\sigma_{\min}\le0.5$. It passes when:

- both coarse and fine normalization residuals do not exceed $10^{-6}$; and
- the probability-field $L^1$ change does not exceed 0.02.

`DensityFieldResolutionCertificate` is `converged` only when the tail of the
eligible ladder contains at least two consecutive passing pairs. The certificate
retains pair eligibility, pair pass/fail values, the accepted level, and reason
codes.

# Basin correspondence and convergence

Basin comparisons use the signed SAMP0
`stage11_feature_correspondence_v1` policy. Its normalized assignment cost is

$$
C_{ij}
=
1\left(\frac{d_{ij}}{\sigma_{\min}}\right)^2
+2(1-O_{ij})
+1\frac{|p_i-p_j|}{p_{\mathrm{scale}}}.
$$

The initial correspondence preset uses:

```text
maximum assignment cost = 3.0
ambiguity margin = 0.10
deterministic tie break = lexicographic_feature_id
admissible types = point-to-point and ridge-to-ridge
explicit outcomes = matched, ambiguous, unmatched, split, merge
```

`compare_basin_catalog_pair` evaluates periodic anchor distance in the exact
cell metric, overlap of nested owner maps, integrated probability change,
candidate type, assignment cost, ambiguity, unmatched features, and positive-
overlap split/merge alternatives. Unsupported nodes remain outside overlap
claims.

A basin pair passes only when all `stage11_grid_stopping_v1` basin tolerances
hold. `BasinGridConvergenceCertificate` then applies the same physical-resolution
eligibility and two-consecutive-pair rule as the field certificate.

# Corridor evidence and convergence

`CorridorGridLevelEvidence` records, per accepted basin pair:

```text
adjacency identity
periodic bottleneck position
corridor width
bottleneck density
optional support-node identity
catalog signature
```

`compare_corridor_level_pair` records adjacency equality, minimum support
intersection-over-union when support nodes are supplied, periodic bottleneck
motion, maximum relative width and density changes, split/merge records,
ambiguity, and evidence completeness.

A corridor pair passes only when the initial corridor thresholds hold. Missing
width, bottleneck, density, or support evidence is not converted into a zero or
a passing value. It yields an unresolved corridor certificate with the reason:

```text
corridor_width_or_support_evidence_unavailable
```

Thus the valid combined outcome

```text
field numerics: converged
basins: converged
corridors: unresolved_due_to_missing_evidence
```

is preserved rather than collapsed into one Boolean.

# Convergence statuses

GR3 uses the exact `GridConvergenceStatus` values:

```text
converged
unresolved_due_to_resolution_budget
unresolved_due_to_refinement_limit
unresolved_due_to_insufficient_passing_levels
unresolved_due_to_metric_failure
unresolved_due_to_missing_evidence
```

The distinction is normative:

- `unresolved_due_to_resolution_budget` means GR1 could not allocate the
  requested ladder under the signed scientific resource policy;
- `unresolved_due_to_refinement_limit` means the configured level depth was
  exhausted;
- `unresolved_due_to_insufficient_passing_levels` means too few eligible passing
  comparisons exist despite a valid ladder;
- `unresolved_due_to_metric_failure` means one or more required comparisons
  failed their numerical or topology tolerances; and
- `unresolved_due_to_missing_evidence` means the relevant field, basin, or
  corridor inputs were not supplied completely.

These are scientific outcomes, not substitutes for exceptions caused by invalid
cells, malformed records, signature mismatch, or a kernel change.

# Source, resource, and cross-fit binding

The bundle binds:

```text
source bundle signature
scientific refinement-policy signature
scientific resource-policy signature
cross-fit partition signature
GR1 ladder signature
field certificate signature
basin certificate signature
corridor certificate signature
```

A caller-supplied resource policy must match the policy's signed resource
identity before planning. Evidence from another source or cross-fit partition
must not be pooled implicitly.

GR3 operates only within the discovery/model-selection domains authorized by
SAMP0. Held-out basin or corridor validation cannot retune the kernel, ladder,
candidate count, correspondence policy, or accepted grid. Final candidate
selection and freezing remain Stage 11E-GR4 responsibilities.

# Integration with E1 and E2

E1 provides fixed-kernel density realizations and normalization/numerical
metrics for the GR1 ladder. E2 provides deterministic per-level basin and
density-boundary candidates. GR3 certifies only numerical grid stability.

GR3 does not replace:

- bandwidth/model selection;
- SAMP1 basin recurrence and effective-sample adequacy;
- SAMP2 passage/corridor support;
- STAT2/STAT3 thermodynamic admissibility;
- E3 force or mean-force evidence; or
- GR4 final hypothesis freeze.

# Failure behavior

Fail closed for:

- a nonfinite or singular cell;
- a non-positive-definite kernel covariance;
- malformed or non-SHA-256 source, kernel, resource, or partition signatures;
- a kernel change inside one ladder;
- non-nested or level-misaligned evidence;
- source/resource/cross-fit identity mismatch;
- corrupted canonical JSON or signature mismatch;
- a rendering/browser budget presented as a scientific resource policy; or
- held-out evidence used to tune the numerical hypothesis.

A valid but unconverged ladder returns a signed unresolved certificate instead
of raising an exception.

# Acceptance tests

The focused GR3 boundary requires:

- exact default values and policy replay;
- one additional post-gate ladder level for the two-comparison rule;
- two consecutive eligible passing field comparisons;
- diagnostic-only treatment of one passing pair under a budget limit;
- metric-failure rejection without finest-level promotion;
- fail-closed kernel change;
- periodic basin correspondence with ambiguity, split, merge, and unmatched
  handling;
- independent basin and corridor convergence;
- unresolved corridor evidence without deleting basin convergence;
- source/resource/cross-fit signature rejection;
- canonical bundle replay and tamper rejection;
- public API and documentation-contract tests; and
- import isolation from plotting and rendering policy.

The broader compatibility boundary includes GR0--GR2, density estimators,
atomic/framework density, E0a--E8a structural contracts, and clean-wheel replay.

# Implementation status and next stage

Implemented in `0.20.26a0` under architecture revision 56. The implementation
adds the common fixed-kernel scientific refinement runtime without changing the
GR2 visual-policy outputs or promoting the historical Stage 11E8a pilot.

The next implementation stage is **Stage 11E-GR4: cross-fitted numerical-
hypothesis selection and freeze**.
