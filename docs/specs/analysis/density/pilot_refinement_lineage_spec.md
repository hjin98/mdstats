---
title: "Stage 11E8a-S2 Density Refinement, Reference-Cell Sensitivity, and Attractor Lineage"
subtitle: "Source-bound Na-LTA multi-scale spatial certification"
author: "mdstats"
date: "2026-07-26"
version: "0.20.12a0"
status: "implemented"
---

# 1. Scope

Stage 11E8a-S2 extends the accepted S1 framework-registered Na-density pilot with
three spatial robustness products:

1. an explicit Cartesian bandwidth ladder and deterministic attractor lineage;
2. a fixed-bandwidth logical-grid refinement series; and
3. a modest reference-cell sensitivity certificate using a declared production
   frame as the comparison reference.

S2 does not infer stationarity, temporal states, transition paths, force-density
agreement, rates, or a global PMF. It only removes the missing spatial-lineage
and reference-cell-evidence blockers.

# 2. Public operation

```python
prepare_na_lta_300k_refinement_lineage_pilot(
    collection,
    trajectory_path,
    *,
    options=None,
    s1_options=None,
    density_resources=None,
    attractor_options=None,
    attractor_resources=None,
    audit_policy=None,
    metadata=None,
)
```

The operation first executes the complete S1 source/gauge/quadrature contract.
Every S2 field is bound to the S1 pilot sample catalog and therefore represents
the same exact raw trajectory digest and the same complete represented-time
measure.

# 3. Bandwidth ladder

The default physical Cartesian Gaussian widths are

```text
0.40 Å, 0.50 Å, 0.60 Å
```

on one declared lineage grid. Each covariance is constructed independently by
`GaussianKernelCovariance.isotropic_cartesian`; grid spacing is not used as a
bandwidth. The Stage 11E1 ladder and Stage 11E2 lineage operators are normative.
Catalog correspondence retains basin overlap, periodic mode displacement,
unmatched source/target attractors, and survival intervals.

Scale consensus is resolved only when one unique topology-stable interval spans
at least two adjacent bandwidths and the lineage is unambiguous. Otherwise the
result is explicitly `scale_ambiguous`.

# 4. Grid refinement

At the declared central bandwidth, S2 evaluates at least two monotonically
refined logical grids. The default shapes are

```text
12 × 12 × 12
16 × 16 × 16
```

The 12-cubed lineage grid limits repeated multi-bandwidth cost. When the 16-cubed central-bandwidth member is identical to the already source-bound S1 realization, S2 reuses the signed S1 density/attractor product rather than recomputing it. Other requested grids are evaluated normally.

The existing `certify_topology_refinement` contract compares attractor count,
geometry multiset, numerically supported density-boundary adjacency, and basin overlap. A failed
certificate remains scientific evidence of nonconvergence; it is not converted
into a runtime failure.

# 5. Reference-cell sensitivity

The selected S1 fixed registered cell is compared with the gauge-validated cell
of one declared production frame. The default comparison frame is the middle S1
representative frame.

The same physical Cartesian kernel width is reconstructed in each domain, so
changing reference-cell coordinates does not silently redefine smoothing. For
identical cell matrices, S2 uses an exact identity shortcut and reuses the
selected field/catalog. Otherwise it executes a full reference-material
registration, sample-catalog reconstruction, central-bandwidth density, and
attractor catalog.

The certificate reports:

- selected and comparison registration signatures;
- selected and comparison cell digests;
- comparison source-frame index;
- relative Frobenius cell difference and relative volume difference;
- fractional-measure probability-density L1 difference;
- matched and unmatched attractor counts;
- maximum and RMS matched-anchor displacement; and
- exact-identity-shortcut use.

The dimensionless density comparison uses the fractional-coordinate probability
fields `p_cartesian * det(cell)` on homologous logical nodes.

Default acceptance limits are:

```text
relative cell difference       0.02
fractional probability L1      0.10
maximum anchor displacement    0.30 Å
unmatched attractors           0
```

Failure is retained as partial or blocked reference-cell evidence; it does not
silently select the more favorable cell.

# 6. Dossier semantics

S2 replaces the S1 spatial records as follows:

- `reference_cell_sensitivity` becomes present and resolved when accepted;
- `field_certificate` reports the full bandwidth and grid realizations;
- `topology_certificate` reports grid-refinement stability;
- `attractor_lineage` reports the executed lineage and scale decision;
- `provisional_cores` remains partial unless the selected spatial hypothesis is
  stable and unambiguous; and
- `unresolved_fraction`, cost, and memory are recomputed from S2 products.

After S2, the expected missing required evidence is:

```text
structural_mapping
temporal_support
force_density_agreement
transition_paths
```

The report therefore remains `blocked_missing_required_evidence`. Stage 11E8b
remains prohibited.

# 7. Determinism and failure rules

- Bandwidths and grid shapes are canonicalized and signed.
- The central bandwidth must be a member of the ladder.
- Grid shapes must be unique and componentwise nondecreasing.
- Reference comparison uses a valid source-frame index.
- Resource preflight remains delegated to Stage 11E1/E2 policies.
- No failed spatial certificate is weakened or hidden.
- No scale-ambiguous catalog is promoted to an authoritative rate model.

# 8. Required validation

Focused tests cover:

- signed option and reference-certificate round trips;
- exact S1/sample/domain/ladder/catalog/lineage binding;
- deterministic bandwidth ordering and survival records;
- grid-refinement stable and unstable outcomes;
- exact-cell reference identity shortcut;
- fail-closed reference-limit diagnostics;
- dossier missing-evidence reduction; and
- root and analysis public API exports.

The real 1,500-frame ASE-backed Na-LTA replay records all scale, refinement,
reference-cell, resource, and unresolved-evidence diagnostics in release
benchmark and audit artifacts.
