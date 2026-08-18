---
title: "Stage 11E8a Na-LTA NVE-Continuation Pilot Dossier and Execution Preflight"
version: "0.20.16a0"
date: "2026-07-26"
status: "Stage 11E8a implementation complete; dossier scientifically partial"
owner: "mdstats.analysis.density.pilot_audit"
---

# Purpose and scientific boundary

Stage 11E8a is the first mandatory real-chemistry gate after the Stage 11E0-E7
contracts. Its purpose is not to add another estimator. It must execute or audit
one complete Na-LTA NVE-continuation analysis and report, without omission:

- coordinate registration and source binding;
- structural and ring mapping;
- stationarity and accepted-frame masks;
- density metric, triclinic periodization, and reference-cell sensitivity;
- numerical field and topology certificates;
- attractor lineage, provisional cores, and temporal support;
- force availability and force-density agreement;
- final segmentation, transition paths, and observed-network support;
- unresolved fractions; and
- computational cost and memory.

The package does not contain the raw 300 K trajectory in version `0.20.9a0`.
It does contain real derived topology, ring, density-benchmark, plotting, and
reference-structure artifacts. The implemented layer therefore provides a
source-bound dossier and fail-closed execution preflight. It certifies what those
artifacts support and reports `blocked_missing_trajectory` for claims that require
raw coordinates or serialized Stage 11E0b-E7 products. Legacy summaries are never
promoted to current site, force, residence, path, or network evidence.

Stage 11E8a-S0 in version `0.20.10a0` provides the complementary real-source
entry point. When the raw trajectory is supplied externally, it binds the exact
bytes to C0 registration and the E0b Na sample catalog. The dossier then advances
from `blocked_missing_trajectory` to `blocked_missing_required_evidence`; no
downstream E1--E7 evidence is inferred by that bootstrap.

Stages S1 through S4 subsequently execute the registered density/attractor pilot,
bandwidth and grid lineage, serrated primitive-ring mapping, exact full-trajectory
partition transfer, provisional temporal support, force-refinement provenance gate,
and path-readiness gate. Version `0.20.15a0` closes the implementation and
regression boundary. Every required evidence record is present, but the report is
`scientifically_partial` because saddle topology is non-authoritative, no PMF-force
sample is admissible, and no inter-attractor path is observed.

# Required evidence taxonomy

A complete dossier contains exactly one record for each required evidence ID:

```text
registration
structural_mapping
stationarity
kernel_metric_periodization
reference_cell_sensitivity
field_certificate
topology_certificate
attractor_lineage
provisional_cores
temporal_support
force_availability
force_density_agreement
transition_paths
unresolved_fraction
cost
memory
```

Every record retains a stage owner, evidence status, source digest when
available, accepted-frame fraction, unresolved fraction, numeric or categorical
metrics, artifact references, and explanatory messages.

The allowed evidence statuses are:

```text
resolved
partial
legacy_summary_only
unavailable
not_applicable
blocked
```

`legacy_summary_only` is not equivalent to `resolved`.

# Dataset identity and source binding

The pilot identity records material, mobile species, temperature, composition,
atom count, represented frame count, duration, frame semantics, trajectory
availability, trajectory digest, and registration signature. Stage 11E8a accepts
only Na-LTA with Na as the mobile species at 300 K.

When a raw trajectory is available, every source-bound evidence digest must match
its trajectory digest. A mismatch gives `blocked_source_mismatch`. When the raw
trajectory is absent, the status is `blocked_missing_trajectory` regardless of
how many legacy summaries are present.

# Overall status

The report status is assigned in the following order:

1. `blocked_missing_trajectory` when raw coordinates are absent;
2. `blocked_source_mismatch` when source-bound evidence refers to another trajectory;
3. `blocked_missing_required_evidence` when a required record is absent;
4. `complete` only when every required record is `resolved` or `not_applicable`;
5. `scientifically_partial` otherwise.

A scientifically partial report remains useful, but cannot advance the real
Na-LTA gate to Stage 11E8b.

# Scientific outcome record

The outcome record may report:

- resolved site-center count;
- supported basin count;
- observed periodic connection count;
- transition-path ensemble count;
- undersampled path-ensemble count;
- rate status; and
- global-PMF status.

Unknown quantities remain `null`. The dossier cannot infer a rate, barrier,
representative mechanism, or PMF from missing evidence.

# Bundled real-evidence preflight

`audit_bundled_na_lta_300k_legacy_evidence()` reads the bundled artifacts with
real ASE and checks the following standing facts:

- the reference structure contains 168 atoms: 24 Na, 24 Al, 24 Si, and 96 O;
- the legacy topology summary represents 2,000 frames and one framework class;
- the Na-inclusive atomic connectivity catalog contains 72 states and 71 changed boundaries;
- the primitive-ring search completed without truncation through ring size eight;
- the ring catalog contains 82 primitive rings under its declared definition;
- the density benchmark represents 1,300 frames for Na, Si, Al, and O; and
- all referenced artifact bytes and SHA-256 digests are recorded.

These facts certify real historical evidence. They do not reconstruct the current
E0b-E7 products and therefore leave the pilot blocked.

# Resource and serialization contracts

The resource policy bounds artifact, evidence-record, and metadata counts before
allocation. The report, dataset, artifacts, evidence records, resource summary,
and outcome all have deterministic SHA-256 signatures and strict JSON schemas.
Artifact references must resolve to declared artifact IDs. Tampering, duplicate
IDs, malformed fractions, invalid composition, and source mismatch fail closed.

# Acceptance tests

Focused tests require:

- one complete synthetic source-bound dossier;
- missing-trajectory blocking;
- source-mismatch blocking;
- missing-evidence blocking;
- partial evidence not promoted to complete;
- serialization replay, tamper rejection, artifact binding, and resource limits;
- real-ASE audit of the bundled Na-LTA reference and historical artifacts;
- deterministic Markdown rendering; and
- public API exports.

The real pilot itself is not accepted until the raw 300 K trajectory or complete
serialized E0b-E7 products are supplied and the dossier no longer reports a
blocking status.

# Method provenance

The dossier and exact evidence taxonomy are package-specific constructions.
File hashing, immutable provenance, and reproducible audit trails are standard
scientific-computing background. No external numerical estimator is introduced
by this stage.

# Implemented execution progression

- `0.20.10a0` / S0 binds the exact raw trajectory, a C0 registration, and E0b Na samples.
- `0.20.11a0` / S1 selects and validates the framework gauge and adds one E1 density and E2 attractor realization.
- Missing required evidence continues to be represented by absent records, not inferred placeholders.

The expected S1 status is `blocked_missing_required_evidence`, with structural mapping, reference-cell sensitivity, temporal support, force-density agreement, and transition paths still absent.


## Private common-helper ownership

Canonical JSON, SHA-256 signing, metadata freezing, array accounting, and
canonical evidence replacement are implemented by `_pilot_common.py` under
`pilot_common_spec.{md,pdf}`. This does not change any public dossier schema.
