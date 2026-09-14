---
title: "MLFF-DATA5: Partition Feasibility, Evidence Roles, and Leakage Control"
author: "mdstats development"
date: "2026-09-13"
status: "current specification with V7 neutral-substrate clarification"
---

# 0. Current-generation scope clarification

This specification predates the V7 target-size reset and therefore documents two things that must now be distinguished explicitly:

1. the still-valid DATA5 statistical concepts and public record family (`PartitionUnitCatalog`, feasibility/independence/outer-role/blinding/leakage records and the legacy/general `CrossValidationPlan` API); and
2. the **current target-size/P5 authority path**, which no longer uses DATA5 label-domain partitioning or DATA5 preselection cross-validation as target-size scientific authority.

The current target-size path is:

```text
canonical frame/source authority
  -> compatibility-neutral NeutralStatisticalBase
       (correlation units, outer roles, independence/leakage evidence; no CV)
  -> canonical P1 split-exclusion relations
  -> P2 P_train/M3 split and pi_train/pi_eval
  -> target-size diagnostic
  -> operator freeze
  -> P5 post-selection folds inside each exact frozen T_N
```

The neutral condition key contains reduced formula, temperature condition,
strain class, regime, and optional user labels; it does **not** contain the
retired `label_domain_id` target-size partition axis. The neutral substrate
constructs no pre-target-size CV plan.

This clarification does **not** retire source-label compatibility. DATA2/DATA3
source authority still distinguishes theory/electronic-structure, energy
reference, derivative/stress convention, numerical quality, and related label
compatibility. A target training bundle still requires compatible target labels.
What is retired is the use of compatibility/label-domain grouping to create
multiple target-size selectors, per-domain candidate ladders, or pre-target-size
CV authorities.

Accordingly, the DATA5 `CrossValidationPlan` described below is not the current
P5 post-selection CV plan and cannot select, freeze, accept, or change a target
size. The current P5 fold owner operates only after target-size admission and
only inside exact frozen `T_N` membership.

## Implemented public records

The repository still exposes `PartitionUnitCatalog`, `PartitionFeasibilityReport`,
`PartitionIndependenceReport`, `OuterPartition`, `CrossValidationFold`,
`CrossValidationPlan`, `BlindingBoundaryCatalog`, and `LeakageAuditReport` from
the earlier DATA5 record family. The held-out evaluation units in that record
family never control early stopping or checkpoint choice.

The current target-size neutral counterparts are owned under
`mdstats.training_data.neutral_substrate` (`NeutralUnitCatalog`,
`NeutralFeasibilityReport`, `NeutralOuterPartition`, `NeutralIndependenceReport`,
`NeutralLeakageReport`, and `NeutralStatisticalBase`). They intentionally contain
no compatibility-domain or CV authority.

# 1. Purpose

The DATA5 statistical layer converts eligible, full-resolution DATA3/DATA4
evidence into statistically explicit roles without fitting a model or selecting
a reduced target-training set. Across the legacy/general and current neutral
record families, the retained responsibilities are:

- autocorrelation-aware complete-frame units;
- role-budget feasibility;
- outer development, monitor, calibration, and locked-test roles;
- machine-readable independence grades;
- label-derived-feature blinding boundaries;
- exact-identity, event-window, temporal-purge, and leakage audits; and
- protected statistical evidence consumed by later current owners.

The older DATA5 record family also exposes preselection `CrossValidationPlan`
records and nested checkpoint-monitor roles. Those records remain documented for
the API/evidence they represent, but they are **not** current target-size or P5
post-selection-CV authority after the V7 cutover.

DATA5 does **not** fit feature transforms, compute foundation-model residuals,
select target-training membership, choose target size, estimate the current P3
common atomic-reference fit, or write MACE artifacts.

# 2. Statistical rationale

Adjacent MD frames are correlated observations. Random frame splitting can put
nearly identical structures on both sides of an evaluation boundary and
therefore understate generalization error. Complete contiguous blocks whose
length is derived from integrated autocorrelation estimates, together with
protected event merging and temporal purge, reduce that leakage risk.

For an observable `x(t)`, with integrated autocorrelation time expressed in
stored-frame units, the effective sample count is approximated as

$$
N_{\mathrm{eff}}\approx\min\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

The estimate is a sampling diagnostic, not proof that slow structural states
have decorrelated. The statistical substrate therefore records both numerical
block evidence and a categorical independence grade.

# 3. Evidence hierarchy

The statistical layer preserves separate concepts:

1. frame eligibility — whether a labeled frame may be used;
2. a partition/correlation unit — one indivisible autocorrelation-aware frame block;
3. an outer role assignment — the unit's role relative to development, monitor,
   calibration, locked evaluation, purge, or exclusion;
4. independence/limitation evidence — how strongly that role separation is supported;
5. protected split relations — correlation units, exact duplicates, protected
   event windows, and accepted condition-scoped lineage relations; and
6. leakage evidence — whether incompatible roles violate identity, event, purge,
   or protected-relation constraints.

The legacy/general DATA5 family additionally defines `CrossValidationFold` as a
job-specific held-out/monitor/training/purge assignment over development units.
That concept is not a mutation of the outer role. In the current target-size
campaign, the authoritative post-selection fold is reconstructed later by P5
inside exact frozen `T_N` and must not be confused with this preselection record.

# 4. Public data contracts

## 4.1 Partition policy

The legacy/general `PartitionPolicy` binds:

- the DATA1 complete-frame block policy;
- role-budget policy;
- accepted eligibility states;
- observables used for autocorrelation;
- event-window block merging;
- outer-role assignment order;
- hierarchical condition axes;
- legacy/general cross-validation fold count;
- temporal purge radius in units;
- legacy/general checkpoint-monitor support per fold; and
- whether an unavailable calibration cohort may be deferred.

The current `NeutralPartitionPolicy` retains the correlation, role-budget,
condition-coverage, purge, event-merging, and outer-role semantics needed by the
current target-size substrate, but deliberately owns no CV plan.

All authoritative ordering/tie behavior is deterministic and content-bound.
Content digests are deterministic content identities, not digital signatures.

## 4.2 Condition key

The legacy/general `PartitionConditionKey` contains:

- label-domain ID;
- reduced chemical formula;
- target-temperature label;
- strain class;
- regime label; and
- optional user-provided condition labels.

The current target-size `NeutralPartitionConditionKey` removes `label_domain_id`
and contains:

- reduced chemical formula;
- temperature condition;
- strain class;
- regime; and
- optional user labels.

Both represent only physically existing/applicable combinations. Neither layer
constructs an impossible full Cartesian product of condition labels.

## 4.3 Partition unit

A statistical unit contains or binds:

- deterministic unit identity;
- source run and frame interval;
- ordered frame UIDs;
- condition identity;
- block-plan identity;
- protected event IDs/evidence;
- maximum autocorrelation time and effective-sample estimate;
- source replica/structural-realization/reference metadata where available; and
- independence grade and evidence codes.

The legacy/general record may also carry label-domain metadata. The current
neutral target-size unit does not use that metadata as a partition axis.

Protected windows from one event remain indivisible. Event-aware merging occurs
before incompatible role assignment.

## 4.4 Independence grades

`IndependenceGrade` is ordered from stronger to weaker evidence:

- `independent_replica`;
- `independent_structural_realization`;
- `independent_thermodynamic_run`;
- `purged_temporal_block`;
- `slow_state_not_decorrelated`;
- `insufficient_independence`.

The grade is evidence metadata. It does not alter target labels or model loss.

## 4.5 Feasibility report

Feasibility is evaluated before role assignment. The report records, over the
applicable current condition grouping:

- eligible frames and statistical units;
- requested role support;
- available replicas/runs/temporal units;
- expected purge losses;
- calibration support or deferral;
- missing condition coverage; and
- overall outcome and reason codes.

The legacy/general record may additionally report a feasible preselection CV
fold count. That field does not determine current P5 fold topology.

Current neutral outcomes include:

- `fully_supported`;
- `supported_with_temporal_blocks_only`;
- `calibration_deferred`;
- `insufficient_for_locked_test`;
- `insufficient_for_requested_roles`.

Older DATA5 records may additionally contain `reduced_cross_validation_folds`.
That historical/general outcome is not a current target-size/P5 target-selection
mechanism.

A failed feasibility report must never silently produce a nominally complete
partition.

## 4.6 Outer roles

`OuterRole` includes:

- `development`;
- `outer_monitor`;
- `uncertainty_calibration`;
- `locked_interpolation_test`;
- `purged`;
- `excluded`.

The locked test is sealed. It cannot influence feature fitting, target
membership, target size, protocol choice, checkpoint selection, uncertainty-
calibration-policy design, or active-learning threshold choice.

The current target-size population is projected from the neutral DEVELOPMENT
role. The later `M3` target-size reserve is a further development/model-selection
split and is not the neutral outer locked/calibration evidence.

## 4.7 Cross-validation records

The legacy/general `CrossValidationFold` contains disjoint unit IDs for:

- fold training;
- nested checkpoint monitor;
- held-out evaluation; and
- fold purge.

The held-out units never control checkpoint choice. A fresh downstream model is
required for each such fold when that record family is used.

For the **current target-size campaign**, this section is descriptive only of the
older/general API. The authoritative post-selection CV owner runs after
`cross-validate` freezes the ordered selected collection and derives fold roles
inside each exact frozen `T_N`. No DATA5 `CrossValidationPlan`, label-domain fold
map, or preselection fold result may choose or accept a current target size.

## 4.8 Blinding boundary

The legacy/general `BlindingBoundaryCatalog` expresses the same scientific
separation retained by current architecture:

| Evidence role | Geometry/raw features | Label-derived selection features | Checkpoint metrics | Calibration | Final evaluation |
|---|---:|---:|---:|---:|---:|
| development | yes | authorized training-domain only | role-dependent | no | no |
| monitor/model control | yes | no held-out leakage | yes | no | no |
| uncertainty calibration | yes | no | no | yes | no |
| locked interpolation test | sealed until activation | no | no | no | post-freeze only |
| purged/excluded | provenance only | no | no | no | no |

Later DATA6/P2/P3/P5/P7 owners enforce operation-specific access. A historical
catalog object is not itself a current target-size selector.

## 4.9 Leakage and split-exclusion evidence

Leakage checks preserve at least:

- one outer role per unit/frame occurrence;
- no incompatible exact occurrence/geometry/labeled-configuration overlap;
- no protected event window split across incompatible roles;
- required temporal purge within a run;
- no locked/calibration evidence in development fitting or post-selection
  training/monitor roles; and
- consistent parent source/frame/feature identities.

For current target-size `P_train/M3` construction, the canonical P1
`NeutralSplitExclusionEvidence` supplies the complete protected relation family:
correlation units, exact geometry duplicates, protected event windows,
condition-scoped replica lineage, and condition-scoped structural-realization
lineage. Downstream P2 must consume this one authority rather than re-derive a
partial relation set.

Errors fail the gate. Warnings record weak independence or incomplete support
without rewriting the evidence.

# 5. High-level algorithms

## 5.1 Legacy/general DATA5 record family

The historical/general DATA5 API operates, per its declared compatibility
partition where applicable, by:

1. reading eligible DATA3 frames and DATA4 raw/event evidence;
2. building finite per-run observables;
3. constructing complete-frame correlation blocks without crossing gaps;
4. merging adjacent blocks crossed by protected event windows;
5. attaching condition/event/replica/run/effective-sample/independence evidence;
6. evaluating role-budget feasibility;
7. deterministically assigning outer roles and purge;
8. optionally constructing its legacy/general CV evaluation folds;
9. carving nested checkpoint monitors only from the corresponding training-
   eligible domain and applying purge; and
10. emitting blinding/leakage evidence.

These steps continue to describe the public older record family, but step 8/9
must not be interpreted as current P5 CV or target-size authority.

## 5.2 Current neutral target-size substrate

The current V7 target-size substrate instead performs:

1. canonical source/frame/eligibility projection into a compatibility-neutral
   frame authority;
2. candidate-independent neutral feature/event projection;
3. complete-frame block construction and protected-event merging;
4. construction of `NeutralPartitionConditionKey` without label-domain axis;
5. role-budget feasibility, deterministic neutral outer-role allocation,
   independence evidence, and leakage audit;
6. construction of canonical P1 split-exclusion relation evidence; and
7. publication of one `NeutralStatisticalBase` containing **no pre-target CV**.

P2 then owns the exact `P_train/M3` split and canonical target/evaluation orders;
P5 owns CV only after target-size admission.

# 6. Deterministic outer assignment

Within each current condition group, units are ordered by run identity and
source interval. Outer-role anchors are selected by stable positions rather than
random frame draws. If requested condition-level coverage cannot be supported,
the feasibility/partition policy may permit a deterministic global fallback;
otherwise the request fails.

Current conflict priority is:

1. locked interpolation test;
2. uncertainty calibration;
3. outer monitor;
4. purge;
5. development.

No unit may be silently reassigned after the partition identity is emitted.

# 7. Event and slow-state handling

DATA4 event detection is full resolution and precedes statistical blocking and
ordinary thinning. Units are merged so that each protected event window remains
indivisible. A stable cation/site/phase state over the complete available run is
not interpreted as an independent sample merely because the run can be divided
into multiple blocks.

When only weak temporal evidence supports a condition, the independence grade
records that limitation (`slow_state_not_decorrelated`, temporal-block-only
support, or insufficient independence) rather than promoting it to replica-level
independence.

# 8. Serialization and provenance

Both legacy/general and current neutral public records use canonical,
content-bound serialization and explicit parent lineage. The relevant evidence
binds source/frame/feature identities, partition/block policy, unit catalogs,
feasibility, outer role assignment, independence, and leakage state.

The legacy/general DATA5 bundle may also contain its `CrossValidationPlan` and
`BlindingBoundaryCatalog`. Those objects are not parents of the current P2/P5
target-size/CV graph.

# 9. Failure semantics

The statistical layer fails closed when, as applicable:

- no eligible frames remain;
- requested development/evidence roles are unsupported;
- an event window cannot be preserved as one protected relation;
- duplicate/protected relations cross an incompatible boundary;
- temporal purge or role disjointness is violated;
- a locked/calibration unit is exposed to a forbidden development operation;
- source/frame/feature lineage disagrees; or
- a downstream owner attempts to reinterpret legacy DATA5 label-domain/CV state
  as current target-size/P5 authority.

Calibration may be deferred only when the active role-budget policy explicitly
allows it. External/challenge evidence is not fabricated from insufficient
source support.

# 10. Focused acceptance expectations

The shared DATA5/neutral statistical semantics require evidence for:

- deterministic block and outer-role replay;
- event-window block merging;
- full and degraded feasibility outcomes;
- calibration deferral;
- temporal-only and stronger independence grading;
- locked-test sealing;
- exact geometry/protected-event leakage rejection;
- purge-neighbor enforcement;
- serialization/tamper rejection; and
- source-to-statistical-substrate integration.

Current V7 target-size conformance additionally requires:

- neutral condition keys and P1 target-size authorities contain no
  compatibility-domain or pre-target CV fan-out;
- P2 consumes the canonical neutral split-exclusion relation authority;
- current target-size execution cannot depend on DATA5/label-domain/CV state;
- post-selection folds are derived only after freeze inside exact `T_N`; and
- retired preselection CV/label-domain target-size descendants cannot authorize
  current execution.

The older DATA5-focused tests for its public `CrossValidationPlan` remain useful
API/regression evidence but do not establish current P5 authority.

# 11. References

1. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
2. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
3. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
4. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
5. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.

# 12. Implementation environment

Focused VASP-path tests historically used ASE 3.29.0 source fixtures. ASE
remains an external dependency and is not bundled with mdstats.

The DATA4 ordering requirement remains normative for the statistical substrate:
**event detection before thinning** ensures protected event windows exist before
statistical role allocation.
