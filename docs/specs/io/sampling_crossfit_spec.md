---
title: "Stage 11E-SAMP0 Complete-System Cross-Fit Sampling Foundation"
author: "mdstats"
date: "2026-07-27"
version: "0.20.22a0"
status: "implemented"
---

# Purpose

Stage 11E-SAMP0 converts one accepted Stage 11E-STAT1 production regime and one or
more immutable Stage 11E0b registered species-sample catalogs into a signed
`EvidenceCrossfitPartition`. The partition prevents density, grid, candidate, force,
thermodynamic, and later kinetic model choices from using the evidence reserved for
held-out validation.

SAMP0 does not discover sites, choose a density bandwidth, construct a grid, validate a
basin, count a passage, estimate a free energy, or fit a rate. It owns only the sampling
and correspondence policies needed by those later stages.

# Runtime ownership

```text
mdstats/io/sampling_crossfit.py
    EvidenceCrossfitPolicy
    SamplingAdequacyPolicy
    FeatureCorrespondencePolicy
    CompleteSystemBlock
    LocalDecorrelationDiagnostic
    DomainSamplingDiagnostic
    NestedSelectionFold
    NestedSelectionPlan
    EvidenceCrossfitPartition
    build_evidence_crossfit_partition
```

The runtime depends on:

```text
ProductionRegimeCatalog     (STAT1)
FrameworkAlignedIonSampleCatalog[] (E0b)
```

It does not mutate either dependency.

# Source and regime binding

A partition is valid only when every input sample catalog carries the same signed
`source_identity_signature` as the `ProductionRegimeCatalog`. All catalogs must have
identical frame indices, frame IDs, temporal masks, represented-time weights, and weight
units.

Exactly one STAT1 regime is selected. If the catalog contains multiple selected regimes,
the caller must name one explicitly. SAMP0 never pools regimes implicitly. The selected
regime must have:

```text
scientific_use_permitted = true
production_interval_status = scientific_candidate
```

Diagnostic-only, rejected, or insufficient regimes cannot create a scientific SAMP0
partition.

# Complete-system block invariant

A block is owned by source frames, not by ion samples. For every frame in a block, all
mobile-ion samples represented by every supplied E0b catalog are included in that same
block. A two-ion frame and a twenty-ion frame therefore remain one complete-system time
sample for effective-sample accounting.

Each `CompleteSystemBlock` records:

```text
block and regime identity
contiguous source-frame interval
exact frame IDs
represented time and units
one contiguous frame-major sample span per E0b catalog
selected mobile-atom count
raw sample count
replica support
```

Ion multiplicity may increase spatial-density precision but cannot multiply the number of
independent complete-system trajectory samples.

# Block-length selection

SAMP0 derives frame observables from the registered species centroids. Callers may add
other finite frame-aligned observables. For every contiguous eligible run, the
initial-positive-sequence integrated autocorrelation time is estimated. The automatic
block length is

$$
L = \max\left(L_{\min},\left\lceil m\max_j\tau_j\right\rceil\right),
$$

where `m` is the versioned autocorrelation multiplier. An explicit block length is
permitted for controlled studies, but adequacy remains fail-closed when local
correlation is too large relative to that block length.

No autocorrelation is computed across a temporal-mask gap or trajectory-segment reset.
Remainder frames are distributed deterministically among blocks rather than discarded.

# Cross-fit domains

The primary domains are:

```text
discovery
model_selection
basin_validation
corridor_validation
thermodynamic_estimation
thermodynamic_validation
```

An optional `final_refit` domain contains every block. It is explicitly a new lineage and
must not inherit any held-out parameter-validation certificate.

## Explicit holdout mode

In `explicit_holdout` mode, the six primary domains are disjoint and together cover every
complete-system block. Deterministic balanced round-robin assignment is used so that the
mapping is reproducible and independent of feature order.

## Nested discovery/model-selection mode

In `nested_discovery_selection` mode, discovery and model selection share one signed pool.
All basin, corridor, and thermodynamic domains remain disjoint from that pool and from one
another. `NestedSelectionPlan` supplies deterministic folds whose training,
model-selection, and optional purged block sets partition only the shared pool.

Held-out validation blocks never enter a nested fold.

# Local decorrelation and effective samples

`LocalDecorrelationDiagnostic` is computed for every block/observable pair. Its effective
sample count is

$$
N_{\mathrm{eff},b,j}=\min\left(N_b,\frac{N_b}{2\tau_{b,j}}\right).
$$

For a domain, complete-system effective support is the minimum over observables of the sum
of blockwise effective counts. The count is never multiplied by the number of ions.

Each `DomainSamplingDiagnostic` also records:

```text
block support
frame support
represented time
weight units
replica identities
maximum local autocorrelation time
effective sample count
adequate / insufficient / unavailable status
machine-readable reasons
```

# Sampling adequacy policy

`SamplingAdequacyPolicy` is immutable, serialized, and signed. The initial version requires
for every primary domain:

```text
minimum block support: 2
minimum complete-system effective samples: 2
minimum replica support: 1
positive represented time
maximum local tau / shortest block length: 0.5
```

These are conservative versioned defaults, not physical constants. Overrides produce a
new policy signature and are retained in the partition.

A partition may be constructed for diagnostics when support is inadequate, but its status
is `insufficient`; later stages must not promote it as accepted sampling evidence.

# Feature correspondence policy

The initial preset is exactly `stage11_feature_correspondence_v1`. For an admissible pair
of candidate features $a,b$,

$$
C_{ab}=w_d(d_{ab}/\sigma_{\min})^2+w_o(1-O_{ab})
+w_p|P_a-P_b|/P_{\mathrm{scale}},
$$

with:

```text
(w_d, w_o, w_p) = (1, 2, 1)
maximum assignment cost = 3.0
ambiguity margin = 0.10
tie breaking = lexicographic feature ID
admissible pairs = point-point and ridge-ridge
```

Point-to-ridge correspondence is prohibited by this preset. The policy explicitly
enumerates `matched`, `ambiguous`, `unmatched_left`, `unmatched_right`, `split`, and
`merge` outcomes. Exact values are serialized and never inferred from candidate order.

The runtime policy supplies type admissibility and normalized-cost evaluation. Later GR
and validation stages own feature-set assignment and lineage certificates.

# Serialization and replay

All policies, blocks, diagnostics, nested folds, plans, and the final partition use
canonical JSON and SHA-256 signatures. `from_dict` reconstructs the complete object and
rejects any payload whose stored signature does not replay.

The partition additionally exposes:

```text
block_ids_for(domain)
frame_indices_for(domain)
sample_mask_for(catalog, domain)
domain_signature(domain)
```

`sample_mask_for` can select only a catalog already signed into the partition.

# Fail-closed conditions

SAMP0 raises a source-control error when:

- source identities disagree;
- frame, time-weight, temporal-mask, or frame-ID axes disagree;
- no accepted regime is uniquely selected;
- the selected regime is not a scientific candidate;
- an E0b catalog is not frame-major and complete for a block;
- a nested plan would inspect held-out domains;
- primary-domain coverage or disjointness invariants are violated;
- a final-refit domain does not contain all blocks.

Insufficient block, represented-time, replica, or effective-sample support produces a
signed `insufficient` partition rather than an exception.

# Acceptance tests

The focused SAMP0 boundary must cover:

1. explicit disjoint-domain coverage;
2. complete-system ion/frame ownership;
3. nested selection confined to discovery/model-selection evidence;
4. all-block final-refit lineage separation;
5. fail-closed insufficient support;
6. cross-source rejection;
7. no implicit multi-regime pooling;
8. exact serialization replay and tamper rejection;
9. exact `stage11_feature_correspondence_v1` values and type restrictions;
10. stable public exports;
11. custom replica-metadata-key replay;
12. rejection of overlapping mobile-atom catalogs;
13. signed insufficient nested-selection output for a too-short shared pool.

# Next stage

Stage 11E-GR0 is implemented in `0.20.23a0`, Stage 11E-GR1 in `0.20.24a0`, Stage 11E-GR2 in `0.20.25a0`, and Stage 11E-GR3 in `0.20.26a0`. GR0 extracts analysis-owned common grid geometry and numerical diagnostics; GR1 adds scientific budgeted planning and exact nested ladders; GR2 adapts atomic/framework plotting while preserving exact visual behavior; GR3 certifies fixed-kernel field, basin, and corridor grid convergence. Stage 11E-GR4 is next.
