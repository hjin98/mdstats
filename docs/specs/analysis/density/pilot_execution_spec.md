---
title: "Stage 11E8a-S0 Real-Trajectory Source Bootstrap"
subtitle: "Raw-byte binding, C0 registration, E0b Na position-force samples, and fail-closed pilot continuation"
version: "1.0"
date: "2026-07-25"
status: "implemented"
---

# Purpose

Stage 11E8a-S0 is the first executable boundary after the raw Na-LTA NVE-continuation
trajectory becomes available. It does not discover sites. It binds the exact
trajectory bytes to the already implemented coordinate and sample contracts:

$$
\text{raw trajectory}
\rightarrow \text{C0 registration}
\rightarrow \text{E0b Na sample catalog}
\rightarrow \text{E8a dossier}.
$$

The output remains blocked at the missing-required-evidence gate until the real
E1--E7 analyses are executed. Historical topology or plotting summaries are not
promoted into current source-bound evidence.

# Inputs

`prepare_na_lta_300k_source_bootstrap()` accepts:

The `300k` token is a legacy public function-name identifier only and has no
source-control authority.

- one normalized `AtomisticFrameCollection` with trajectory semantics;
- the path of the exact raw trajectory file;
- the declared pilot temperature, fixed to 300 K;
- an optional explicit `FrameRegistrationPolicy`; and
- optional dossier metadata and resource limits.

The collection must retain reader provenance whose `source_files` refer to the
raw path being hashed. Absolute paths must match exactly. A relative source name
may match by basename, but that weaker condition is labeled `basename_only` in
the dossier. A conflicting absolute source path fails closed.

The source must have a physical time axis, full periodicity, 168 atoms, and the
exact composition 24 Na, 24 Al, 24 Si, and 96 O.

# Raw-byte identity

The trajectory identity is the SHA-256 digest of the raw file bytes. This digest
is distinct from, and recorded alongside, the in-memory source-coordinate and
registration signatures. Every evidence record emitted by this stage uses the
raw-file digest as its E8a `source_digest`.

Changing any source byte therefore changes the pilot dataset identity even when
a parser would produce numerically equivalent coordinates. The C0 source
contract and E0b signature bind the in-memory collection separately; the reader
provenance path check prevents silently pairing those products with an unrelated
raw file.

# Registration policy

When no policy is supplied, the stage uses the physical fixed-cell C0 baseline:

- the spatial policy is `physical`;
- the translation mode is `none`;
- no structure-derived gauge is fitted; and
- the registered cell is required to remain fixed.

This boundary is intentional. S0 certifies source coordinates and force
covectors without selecting the later density/site-discovery gauge. Stage
11E8a-S1 owns the analysis-specific framework-registration policy and its cost,
stability, and sensitivity checks. A caller may still provide an explicit C0
policy when replaying a certified gauge.

The raw trajectory remains immutable. Registration stores affine products,
wrapped fractions, image shifts, transformed force covectors, exact round-trip
errors, and work-invariance diagnostics in the existing C0 contracts.

# E0b sample boundary

The stage constructs one `FrameworkAlignedIonSampleCatalog` for Na. The compact
layout is frame-major over the 24 persistent Na atom identities. Position,
force, joint, temporal, structural, and PMF-admissible masks remain distinct.

Equilibrium and stationarity are deliberately recorded as unknown at this
stage. A declared 300 K label does not by itself certify stationarity or an
equilibrium PMF.

# Evidence emitted

The bootstrap emits source-bound records for:

- `registration` — resolved after C0 validation;
- `stationarity` — partial and explicitly untested;
- `force_availability` — resolved or unavailable from the actual source;
- `unresolved_fraction` — source-channel completeness only;
- `cost` — bootstrap wall time; and
- `memory` — a deterministic deduplicated NumPy payload estimate.

Density periodization, reference-cell sensitivity, field certificates,
attractor topology, provisional cores, temporal support, force-density
agreement, and transition paths are not fabricated. Their records remain
missing, so the dossier status is `blocked_missing_required_evidence`.

# Resource semantics

`peak_memory_bytes` in the S0 report is not process RSS. It is the deduplicated
resident numerical payload of the collection, C0 registration, E0b Na catalog,
and evidence masks. The report labels this measurement explicitly. Later pilot
stages may replace it with process-level peak measurements for their own scope.

# Acceptance criteria

Focused validation requires:

1. exact 168-atom Na-LTA composition checking;
2. raw-byte SHA-256 binding, provenance-path matching, mismatch rejection, and
   byte-change sensitivity;
3. fixed-cell physical-baseline registration without a fitted translation gauge;
4. exact C0/E0b signature linkage;
5. complete Na position/force masks when forces exist;
6. force-unavailable behavior without invented force evidence;
7. explicit blocking on the still-unexecuted E1--E7 evidence; and
8. public API exports and deterministic report rendering.

# Method provenance

SHA-256 source hashing, affine coordinate registration, force-covector
transformation, and immutable provenance records are standard scientific
computing and tensor-transformation background. The exact E8a-S0 gate, evidence
mapping, raw-byte/source-coordinate dual binding, and fail-closed continuation
rules are mdstats-specific constructions.

# S1 continuation

Stage 11E8a-S0 is now consumed by the implemented Stage 11E8a-S1 operation in
`pilot_density_attractors.py`. S1 supplies an explicit all-framework
matched-reference policy to this bootstrap, so the exact raw-byte binding,
source-contract validation, selected registration, and E0b Na catalog share one
identity. S0 remains independently callable with its physical baseline and does
not itself select an analysis gauge.
