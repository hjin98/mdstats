---
title: "Stage 11E8a-S1 Framework-Registered Density and Attractor Pilot"
subtitle: "Na-LTA NVE-continuation gauge selection, represented-time quadrature, E1 density, and E2 attractors"
author: "mdstats"
date: "2026-07-26"
version: "0.20.11a0"
status: "implemented"
---

# 1. Scope

Stage 11E8a-S1 is the first real-trajectory execution of the analysis-specific
site-discovery coordinate gauge and the existing Stage 11E1--E2 scientific
operators. It consumes the exact raw Na-LTA NVE-continuation trajectory already admitted by
S0 and produces:

1. a selected framework-registered C0 result;
2. an independent gauge-weighting sensitivity result;
3. a deterministic represented-time pilot quadrature;
4. one periodized E1 Na density realization;
5. one support-restricted E2 attractor realization; and
6. an extended fail-closed E8a dossier.

S1 does **not** certify density convergence, attractor lineage, stationarity,
structural mapping, temporal states, transition paths, force-density agreement,
or rates. Those records remain missing or partial.

# 2. Source and composition contract

The public operation is

```python
prepare_na_lta_300k_density_attractor_pilot(
    collection,
    trajectory_path,
    *,
    options=None,
    density_options=None,
    density_resources=None,
    attractor_options=None,
    attractor_resources=None,
    audit_policy=None,
    metadata=None,
)
```

The `300k` token is retained only in the legacy public function name. The
ensemble and thermodynamic state are reconstructed from source controls.


It reuses `prepare_na_lta_300k_source_bootstrap` and therefore requires:

- trajectory semantics and a physical time axis;
- full three-dimensional periodicity;
- exactly 168 atoms with 24 Si, 24 Al, 96 O, and 24 Na;
- reader provenance referring to the exact raw path; and
- independent SHA-256 binding of the raw bytes.

The S1 registration signature replaces the physical S0 baseline signature in the
resulting dataset identity. The source digest is unchanged.

# 3. Framework registration gauge

## 3.1 Reference group

The fitted reference group is all 144 framework atoms:

$$
\mathcal F = \{i: Z_i \ne 11\}.
$$

Na atoms are the disjoint force target group. The registered cell is required to
remain fixed.

## 3.2 Selected and comparison gauges

The selected gauge is matched-reference translation using equal framework-atom
weights (`center_of_geometry`). This is the canonical geometric gauge because
site coordinates and density fields are geometric observables.

An independent matched-reference `center_of_mass` registration is executed on
the same frames. The maximum and RMS framewise translation differences are
reported as gauge sensitivity; the comparison gauge is not used to form the E1
field.

## 3.3 Exact local-convexity solver certificate

For a frame whose centered framework residuals lie inside one geodesically
convex chart of the periodic translation torus, the intrinsic least-squares
translation has a unique ordinary weighted-mean solution. The implementation
uses the sufficient radius

$$
r_{\mathrm{convex}} = \frac{\sigma_{\min}(H)}{4},
$$

where $H$ is the registered cell and $\sigma_{\min}$ its smallest singular
value. If every centered residual norm is below this radius, the frame is marked
`certified_local_convexity`, with positive
`uniqueness_radius_margin = r_convex - r_max`. Otherwise the pre-existing
exhaustive multiseed torus solver remains the fallback.

This fast path changes neither the objective nor the accepted solution. It
provides an exact sufficient uniqueness certificate and avoids an unnecessary
multiseed search for localized framework fluctuations.

## 3.4 S1 acceptance conditions

The selected gauge is admitted only when all of the following hold:

- every frame converged and is unambiguous;
- every frame has a positive local-convexity uniqueness margin;
- the largest framework residual is no larger than the declared residual limit;
- the largest CoG--CoM translation difference is no larger than the declared
  gauge-sensitivity limit;
- the largest adjacent lifted-translation step is no larger than the declared
  continuity limit; and
- temporal branch continuity is available.

Failure raises `PilotAuditInputError` before density allocation.

Default limits are:

```text
maximum framework residual       2.00 Å
maximum CoG--CoM difference      0.05 Å
maximum adjacent translation     0.05 Å
```

The comparatively loose residual ceiling is an admission guard, not a claim
that 2 Å framework motion is physically typical. The actual maxima are retained
in the signed validation record.

# 4. Deterministic represented-time quadrature

S1 first builds the complete trajectory midpoint weighting. Positive-weight
frames are partitioned into at most `representative_frame_count` contiguous
index bins. For each bin:

1. compute the represented-time weighted mean frame index;
2. choose the available frame nearest that mean, with deterministic first-index
   tie resolution; and
3. assign the entire bin weight to that representative.

All other frame weights are zero. The resulting catalog retains complete frame
and atom identity but only representative frames have temporal evidence.

The following invariant is mandatory:

$$
\sum_t w_t^{\mathrm{pilot}} = \sum_t w_t^{\mathrm{full}}.
$$

Thus frame coverage is deliberately partial while represented-time coverage is
exactly one. No claim of statistical independence or stationarity follows from
this quadrature.

# 5. E1 density pilot

The default S1 field is:

```text
species                         Na
registered coordinate measure  reference material
Cartesian Gaussian sigma       0.50 Å
grid                            16 × 16 × 16
periodic image tolerance        1e-10
maximum image radius            2
query batch                     256
sample batch                    128
```

The existing Stage 11E1 operator remains normative. S1 only supplies a fixed
registered domain, a Cartesian-isotropic covariance transformed into fractional
coordinates, and the deterministic pilot sample weights.

The dossier records:

- domain, covariance, metric, image-truncation, catalog, and estimate signatures;
- grid shape and image count;
- represented observation measure;
- mean-occupancy and probability integrals;
- support-node fraction; and
- the complete E1 error certificate.

Because only one grid and bandwidth are evaluated, `field_certificate` is
`partial` even when normalization and image-tail bounds pass.

# 6. E2 attractor pilot

The canonical Stage 11E2 operation is applied to the S1 field without changing
its topology rules. The dossier records:

- attractor, saddle, and provisional-core counts;
- attractor geometry counts;
- the single-realization topology-certificate status; and
- all core signatures and resolved flags.

Only isolated point modes contribute to `site_center_count`. Other supported
basins remain visible but unresolved as point-site centers. A single realization
cannot establish grid/bandwidth lineage, so `topology_certificate`,
`attractor_lineage`, and `provisional_cores` remain partial.

# 7. Dossier semantics

S1 replaces S0 evidence records for registration, unresolved fraction, cost, and
memory and adds:

- `kernel_metric_periodization` — resolved;
- `field_certificate` — partial;
- `topology_certificate` — partial;
- `attractor_lineage` — partial; and
- `provisional_cores` — partial.

The following evidence remains absent after S1:

```text
structural_mapping
reference_cell_sensitivity
temporal_support
force_density_agreement
transition_paths
```

Therefore the expected overall status is still
`blocked_missing_required_evidence`. Stage 11E8b remains closed.

# 8. Resource and failure semantics

Density and attractor resource policies are passed through to the existing E1
and E2 operators. Registration acceptance occurs before field allocation. The
S1 resource record reports wall time and a deterministic deduplicated recursive
NumPy-array payload estimate; it is not process RSS.

No fallback may:

- weaken a failed gauge limit;
- replace the exact source digest;
- silently discard represented time;
- infer topology lineage from one realization;
- infer stationarity from quadrature; or
- infer rates from basin adjacency.

# 9. Required validation

Focused validation must cover:

- signed options and gauge-validation round trips;
- exact source/registration/catalog/field/attractor binding;
- all-framework CoG selection and CoM sensitivity execution;
- certified-local-convexity use on localized frames;
- represented-time conservation under deterministic quadrature;
- E1 occupancy and probability normalization;
- partial E2 topology semantics;
- fail-closed continuity rejection; and
- public API exports.

The real 1,500-frame Na-LTA replay must additionally report the actual gauge,
field, attractor, cost, and unresolved-evidence diagnostics in a release audit.
