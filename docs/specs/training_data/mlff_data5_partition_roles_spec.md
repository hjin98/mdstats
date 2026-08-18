---
title: "MLFF-DATA5: Partition Feasibility, Evidence Roles, and Leakage Control"
author: "mdstats development"
date: "2026-07-28"
status: "implementation specification"
---

## Implemented public records

The implementation exposes `PartitionUnitCatalog`, `PartitionFeasibilityReport`,
`PartitionIndependenceReport`, `OuterPartition`, `CrossValidationFold`,
`CrossValidationPlan`, `BlindingBoundaryCatalog`, and `LeakageAuditReport`.
The held-out evaluation units never control early stopping or checkpoint choice.


# 1. Purpose

MLFF-DATA5 converts the eligible, full-resolution DATA3/DATA4 evidence into
statistically explicit roles without fitting a model or selecting a reduced
training set. It owns:

- autocorrelation-aware complete-frame units;
- role-budget feasibility;
- outer development, monitor, calibration, and locked-test domains;
- machine-readable independence grades;
- independent cross-validation evaluation folds;
- nested checkpoint-monitor roles;
- label-derived-feature blinding boundaries;
- exact-identity, event-window, temporal-purge, and fold leakage audits.

It does **not** fit feature transforms, compute foundation-model residuals,
select training frames, estimate numerical atomic reference energies, or write
MACE artifacts.

# 2. Statistical rationale

Adjacent MD frames are correlated observations. Random frame splitting can put
nearly identical structures on both sides of an evaluation boundary and
therefore understate generalization error. DATA5 uses complete contiguous
blocks whose length is derived from integrated autocorrelation estimates and
places purge regions between incompatible statistical roles. This follows the
logic of blocking analysis and hv-block cross-validation for dependent data
[1-3].

For an observable x(t), the effective sample count is approximated as

$$
N_{\mathrm{eff}} \approx \frac{N}{2\tau_{\mathrm{int}}},
$$

where $\tau_{\mathrm{int}}$ is measured in stored frames. The estimate is a
sampling diagnostic, not proof that slow structural states have decorrelated.
DATA5 therefore records both numerical block evidence and a categorical
independence grade.

# 3. Evidence hierarchy

DATA5 preserves five separate concepts:

1. `FrameEligibilityDecision`: whether the DFT-labeled frame may be used.
2. `PartitionUnit`: one indivisible, autocorrelation-aware frame block.
3. `OuterRoleAssignment`: the unit's outer statistical role.
4. `CrossValidationFold`: a held-out evaluation role and a distinct nested
   checkpoint-monitor role inside the development domain.
5. `LeakageAuditReport`: verification that no identity, event burst, purge, or
   role boundary has been violated.

A frame may have exactly one outer role. A development frame may additionally
appear in exactly one cross-validation evaluation fold, in fold training for
other independent jobs, or in a fold-local checkpoint monitor. These are job-
specific roles, not mutations of the immutable outer assignment.

# 4. Public data contracts

## 4.1 Partition policy

`PartitionPolicy` binds:

- the DATA1 complete-frame block policy;
- the DATA4 `PartitionRoleBudgetPolicy`;
- accepted eligibility states;
- observable names used for autocorrelation;
- event-window block merging;
- outer-role assignment order;
- hierarchical condition axes;
- cross-validation fold count;
- temporal purge radius in units;
- checkpoint-monitor support per fold;
- whether an unavailable calibration cohort may be deferred.

All ordering and tie breaking is deterministic. Content digests, not digital
signatures, bind every policy and record.

## 4.2 Condition key

`PartitionConditionKey` is a hierarchical stratum descriptor containing:

- label-domain ID;
- reduced chemical formula;
- target-temperature label;
- strain class;
- regime label;
- optional user-provided condition labels.

The key describes only combinations that exist. DATA5 never constructs an
impossible full Cartesian product of composition, temperature, strain, and
regime.

## 4.3 Partition unit

`PartitionUnit` contains:

- deterministic unit ID;
- source run and frame interval;
- ordered frame UIDs;
- label domain and condition key;
- block-plan digest;
- event IDs and whether the unit contains protected event frames;
- maximum autocorrelation time and effective-sample estimate;
- source replica/reference metadata;
- independence grade and evidence codes.

Protected windows from one DATA4 event must belong to one unit. Event-aware
merging happens before role assignment.

## 4.4 Independence grades

`IndependenceGrade` is ordered from strongest to weakest:

- `independent_replica`;
- `independent_structural_realization`;
- `independent_thermodynamic_run`;
- `purged_temporal_block`;
- `slow_state_not_decorrelated`;
- `insufficient_independence`.

The grade is evidence metadata. It does not alter labels or model loss.

## 4.5 Feasibility report

`PartitionFeasibilityReport` is produced before assignments. It reports, per
label domain and condition key:

- eligible frames and partition units;
- requested role support;
- available independent replicas and runs;
- available temporal units after event merging;
- expected losses to purge regions;
- feasible cross-validation fold count;
- calibration support or deferral;
- missing condition coverage;
- overall outcome and reason codes.

Possible outcomes include:

- `fully_supported`;
- `supported_with_temporal_blocks_only`;
- `calibration_deferred`;
- `reduced_cross_validation_folds`;
- `insufficient_for_locked_test`;
- `insufficient_for_requested_roles`.

A failed feasibility report must not silently produce a nominally complete
partition.

## 4.6 Outer roles

`OuterRole` is one of:

- `development`;
- `outer_monitor`;
- `uncertainty_calibration`;
- `locked_interpolation_test`;
- `purged`;
- `excluded`.

The locked test is sealed. It cannot be used for feature fitting, selection,
hyperparameter decisions, checkpoint selection, uncertainty calibration, or
active-learning threshold choice.

## 4.7 Cross-validation folds

Each `CrossValidationFold` contains disjoint unit IDs for:

- fold training;
- nested checkpoint monitor;
- held-out evaluation;
- fold purge.

A fresh downstream model must be trained for every fold. The held-out
evaluation units never control early stopping or checkpoint choice. The nested
checkpoint monitor is selected only from that fold's training-eligible domain.

## 4.8 Blinding boundary

`BlindingBoundaryCatalog` declares permitted operations by outer role:

| Outer role | Geometry/raw features | Label-derived selection features | Checkpoint metrics | Calibration | Final evaluation |
|---|---:|---:|---:|---:|---:|
| development | yes | yes, training-domain only | no | no | no |
| outer monitor | yes | no | yes | no | no |
| uncertainty calibration | yes | no | no | yes | no |
| locked interpolation test | sealed until protocol freeze | no | no | no | post-freeze only |
| purged/excluded | provenance only | no | no | no | no |

DATA5 emits boundaries; DATA6-DATA10 enforce operation-specific access.

## 4.9 Leakage audit

`LeakageAuditReport` verifies:

- one outer role per frame and unit;
- no exact geometry or labeled configuration duplicated across incompatible
  outer roles;
- no DATA4 protected event window split across roles;
- temporal purge separation within each run;
- no locked or calibration unit in any cross-validation training/monitor role;
- fold training, monitor, evaluation, and purge disjointness;
- every development unit appears in exactly one held-out evaluation fold;
- all records bind the same source, frame, and DATA4 feature catalogs.

Errors fail the gate. Warnings record weak independence or incomplete condition
coverage without rewriting the data.

# 5. High-level algorithm

For each label domain:

1. Read eligible DATA3 frames and DATA4 raw/LTA/event catalogs.
2. Build dense per-run observables from available finite raw features.
3. Construct DATA1 complete-frame blocks without crossing source gaps.
4. Merge adjacent blocks when one protected DATA4 event window crosses their
   boundary.
5. Attach condition keys, event evidence, replica/run metadata, effective
   sample estimates, and independence grades.
6. Evaluate the role budget and resolve the feasible fold count.
7. Deterministically assign outer monitor, calibration, and locked-test units
   within each existing condition group; place neighboring same-run units into
   purge where required; assign the remainder to development.
8. Build independent cross-validation evaluation folds over development units.
9. For each fold, purge same-run neighbors of evaluation units, then carve a
   deterministic nested checkpoint monitor from the remaining fold-training
   domain and purge its neighbors.
10. Emit blinding boundaries and run the complete leakage audit.

# 6. Deterministic outer assignment

Within each condition group, units are ordered by run ID and source interval.
Outer-role anchors are selected by stable, evenly spaced positions rather than
random frame draws. When a requested role cannot be supported in every
condition, DATA5 records the uncovered conditions and uses deterministic global
minimum support only if the policy permits degradation.

Role priority during conflict resolution is:

1. locked interpolation test;
2. uncertainty calibration;
3. outer monitor;
4. purge;
5. development.

No unit may be silently reassigned after the partition digest is emitted.

# 7. Event and slow-state handling

DATA4 event detection is full resolution and precedes DATA5 blocking. DATA5
merges units so that each protected event window remains indivisible. A stable
cation-site state over the complete available run is not interpreted as an
independent sample. When only one run supports a condition and no slow-state
transition is observed, temporal blocks receive
`slow_state_not_decorrelated` rather than an independence claim.

# 8. Serialization and provenance

All public records are frozen dataclasses with canonical JSON serialization,
SHA-256 content digests, replay verification, and tamper rejection. The DATA5
bundle binds:

- source catalog digest;
- frame catalog digest;
- DATA4 feature bundle digest;
- partition and role-budget policy digests;
- partition-unit catalog;
- feasibility reports;
- outer assignments;
- independence report;
- cross-validation plan;
- blinding catalog;
- leakage audit.

# 9. Failure semantics

DATA5 fails closed when:

- no eligible frames remain;
- a label domain cannot support development plus required evidence roles;
- an event window cannot be kept in one unit;
- duplicate geometry crosses a locked boundary;
- temporal purge or fold disjointness is violated;
- a held-out evaluation unit enters checkpoint monitoring or training;
- a locked-test unit is exposed to a development operation;
- source/frame/feature lineage digests disagree.

Calibration may be deferred only when the role-budget policy explicitly allows
it. External challenge tests are declared but not fabricated from insufficient
source evidence.

# 10. Focused acceptance tests

The DATA5 gate requires tests for:

- deterministic block and role replay;
- event-window block merging;
- full and degraded feasibility outcomes;
- calibration deferral;
- temporal-only independence grading;
- replica-supported independence grading;
- locked-test sealing;
- cross-validation fold and checkpoint-monitor disjointness;
- geometry-duplicate leakage rejection;
- protected-event leakage rejection;
- purge-neighbor enforcement;
- serialization and tamper rejection;
- real ASE 3.29.0 VASP-to-DATA5 integration;
- DATA0-DATA4 regression preservation.

# References

[1] H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of
Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989).
DOI: 10.1063/1.457480.

[2] J. Racine, "Consistent Cross-Validatory Model-Selection for Dependent
Data: hv-Block Cross-Validation," *Journal of Econometrics* **99**, 39-61
(2000). DOI: 10.1016/S0304-4076(00)00030-0.

[3] D. R. Roberts, V. Bahn, S. Ciuti, et al., "Cross-Validation Strategies for
Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,"
*Ecography* **40**, 913-929 (2017). DOI: 10.1111/ecog.02881.

[4] J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, "How to Validate
Machine-Learned Interatomic Potentials," *Journal of Chemical Physics* **158**,
121501 (2023). DOI: 10.1063/5.0139611.

# 11. Implementation environment

Focused VASP-path tests use the user-supplied **ASE 3.29.0** source archive.
ASE remains an external dependency and is not bundled with mdstats.

The DATA4 ordering requirement remains normative: **Event detection before thinning**
ensures protected event windows exist before DATA5 constructs statistical units.
