---
title: "MLFF-DATA9A3: Production LTA Corpus Qualification"
version: "0.20.40a0"
status: "implemented"
---

# MLFF-DATA9A3: production LTA corpus qualification

## Scope

DATA9A3 qualifies the actual bulk-LTA target corpus before DATA9B. Uploaded
filenames are opaque provenance labels. Composition, ensemble, thermostat
schedule, reference cells, finite strain, and trajectory conditions are owned
by VASP controls and ionic arrays.

The production workflow binds immutable normalization, source-catalog, DATA3,
DATA4, and DATA5 artifacts. Interrupted XML streams may retain only completely
closed `<calculation>` records; original, normalized, and discarded-suffix
hashes remain separate evidence.

## DATA5 production contract

DATA5 builds condition-bounded autocorrelation blocks, preserves protected event
windows, assigns outer roles, constructs independent nested cross-validation
folds and monitor sets, records independence grades, defines blinding
boundaries, and runs a fail-closed leakage audit. Frame-to-strain lookup is an
indexed mapping keyed by frame UID; a linear scan per frame is prohibited.

A role-feasibility report is usable unless it is
`insufficient_for_locked_test` or `insufficient_for_requested_roles`. Usable but
non-full outcomes remain explicit warnings. Slow-state independence grades of
`slow_state_not_decorrelated` or `insufficient_independence` also remain explicit
warnings and cannot be silently promoted.

## Large-artifact realization

A serialized DATA3--DATA5 artifact is validated by its `from_dict` constructor.
The validated serialized digest may then be passed to the production gate so
that gate construction does not repeatedly canonicalize tens of thousands of
frame records. Supplying a verified digest without the corresponding artifact
is invalid.

## Qualified result

The supplied corpus contains:

- 27 fixed-cell Langevin NVT trajectories;
- 37,632 complete 168-atom frames;
- seven compositions;
- thermostat targets 300, 600, 700, and 800 K;
- 29,332 unstrained, 2,700 hydrostatic, 2,800 orthorhombic/mixed, and 2,800 shear frames;
- 1,391 protected events;
- 97 DATA5 partition units across 25 conditions;
- three cross-validation folds;
- no exact geometry or labeled duplicate groups;
- a passing leakage audit.

The feasibility outcome is `supported_with_temporal_blocks_only`. Independence
evidence comprises 14 independent thermodynamic-run units, 79 purged temporal
blocks, and four insufficient-independence units. The target corpus therefore
passes with warnings.

## DATA9A/DATA9B boundary

The full DATA9A gate remains `conditionally_ready`. DATA9B must not begin until
all of the following are materialized and bound:

1. the LTA ring/site catalog and site-coverage features;
2. checkpoint-bound production DATA6 foundation descriptors/predictions;
3. foundation-residual DATA7 E0 fits and selection ladders;
4. executable production DATA8 MACE jobs;
5. the exact production replay corpus, when replay training is selected.

A missing artifact is a blocker, not a reason to infer or fabricate data.

The machine-readable blocker codes are:
`lta_site_coverage_not_materialized`,
`foundation_features_not_materialized`,
`foundation_residual_e0_not_materialized`,
`data8_artifacts_not_materialized`, and
`production_replay_corpus_not_bound`.
