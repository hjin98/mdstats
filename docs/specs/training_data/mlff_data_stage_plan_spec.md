---
title: "MLFF Training-Data System Contract"
subtitle: "Cross-cutting current-generation invariants"
author: "mdstats project"
date: "2026-09-14"
geometry: margin=0.78in
toc: true
---

# Scope

This document is the cross-cutting current system contract for the mdstats MLFF training-data and fine-tuning workflow. The legacy filename is retained for stable references; this is **not** an implementation-stage plan.

It owns only invariants that span narrower specifications: evidence-role separation, dependency direction, identity/lineage, fitted-domain isolation, target-membership/target-size ownership, protocol/method identity, replay/monitor separation, sealed evaluation, calibration, bounded execution, and fail-closed current-generation publication.

Narrow specifications own exact module schemas, numerical constants, algorithms, storage formats, and runtime behavior. Current D1/D2 own scientific/numerical semantics; D3 architecture owns the higher-level dependency/ownership model. Workplans and historical documents are non-normative once binding semantics are promoted into current authority.

For restored post-selection P5, `mlff_post_selection_p5_spec.md` is the narrow current D4 owner. Broad DATA8-era `TrainingProtocolIdentity` contracts remain applicable only to separately current non-P5 consumers and historical provenance; they are not a second P5 authority.

# Normative principles

1. Source facts, eligibility, evidence roles, fitted preparation, target membership, target size, weighting, exposure, checkpoint selection, validation, calibration, and acquisition are distinct record/decision families.
2. A frame that supplied a gradient is not independent validation evidence for that model.
3. Held-out cross-validation evaluates a frozen method/protocol and cannot control target size, fitting, stopping, or checkpoint choice for that fold.
4. After target selection, every **current restored-P5** fold has a gradient-training partition, a held-out outer-evaluation partition, and explicit independence/purge evidence. Its target checkpoint monitor is the external campaign-common `M_mon`, not selected-fold membership. Separately current non-P5 protocol families may retain their own accepted monitor topology.
5. Restored-P5 cross-validation trains a fresh model/optimizer lineage for each held-out fold and validates the complete `PostSelectionMethodIdentity` actually used by final production. A broad `TrainingProtocolIdentity` is not a second current P5 method identity.
6. Feature fitting, E0 fitting, label-derived difficulty evidence, and target-subset inputs inspect only the applicable authorized training partition; post-selection fold-local fits never inspect that fold's held-out labels. Foundation-P5 transfer validation may inspect governed geometry/composition classes from monitor/evaluation consumers but not their labels for fitting.
7. Current DATA6/DATA7 preparation publishes fitted inputs and evidence for the common target-size owner and SHALL NOT publish target membership or target size.
8. One canonical training order `pi_train` is the sole current target-membership authority; every candidate is the exact prefix `T_N = pi_train[:N]`.
9. The one target-size reducer is the sole owner of the *automatic* target-size diagnostic, which recommends a size and freezes nothing. The operator owns the provisional choice, restricted to the configured qualified candidate set. Monitor/replay/batch/pool cardinalities are different semantic types.
10. Exact target membership, the ordered collection of provisional target sizes, and their per-size effective role training horizons are frozen together, once, at `cross-validate` admission.
11. Target-size screening uses only authorized development/model-selection evidence. Held-out CV, calibration, and locked tests are forbidden inputs.
12. Locked tests cannot affect fitting, membership, size, protocol/method choice, stopping, checkpointing, calibration-policy choice, publication membership, or acquisition and are activated only after the applicable freeze boundary.
13. Replay training, replay monitoring, target monitoring, and target training preserve separate source/role identities.
14. Replay retention and mandatory physical/deployment integrity are hard admissibility constraints unless an explicit current scientific policy states otherwise.
15. Dynamic resampling/exposure semantics require an explicit current adapter/protocol; static files alone cannot claim them.
16. Calibration is bound to predictions from the actual frozen final committee/publication and an explicit applicability domain.
17. Active-learning child generations inherit prior evidence roles unless a new evaluation lineage explicitly reassigns them.
18. Retired campaign generations are rejected and re-prepared rather than migrated into current semantics. Retired derived target-size or P5 method state is detected before semantic reuse, candidate/checkpoint continuation, or descendant publication and is quarantined rather than translated. Only independently valid lower-level evidence whose recipes do not depend on retired semantics may be reused, and each is re-validated by its current owner.
19. Execution caches, worker scheduling, out-of-core layout, and other realization choices cannot change scientific/numerical identity or authoritative decisions.
20. Publication fails closed when required current-generation identities, upstream evidence, or schema/content validation are missing/incompatible.
21. Restored P5 has one campaign-common exact 256-frame target monitor `M_mon` from neutral label-usable `OUTER_MONITOR`, reused across every selected size, CV fold/seed, and final-production seed/run.
22. Common-monitor membership is sampled first under accepted D2; canonical P1 cross-role protected-relation qualification follows. Relation conflicts or exact-support shortfall fail closed rather than filtering/replacing/resampling members.
23. Foundation P5 uses selected-head foundation-residual E0 fitting plus composition-level transfer validation and does not bind the whole P3 `TargetSizeCommonTrainingPolicy` or inert P3 configuration-weight fitting.
24. Foundation P5 uses native MACE UniversalLoss through the one method-aware MACE seam. P3 target-size screening and P5 scratch keep their separately accepted weighted methods.
25. Retired target/replay **training-head scalar** weights are absent from restored P5; checkpoint/adaptive-stop target/replay score weights remain separately owned.
26. Foundation P5 binds replay/`pt_head` first then target before shuffle for multihead replay, no implicit target duplication, accepted `drop_last=true` geometry, and the qualified single-process path. Distributed foundation P5 fails closed pending separate D2-equivalence qualification.
27. Canonical single-source replay omission resolves TRUE_DFT; explicit pseudo-label training remains opt-in and requires independent TRUE_DFT replay monitoring. Ambiguous omitted legacy split-file semantics fail closed.
28. M3 remains P3 evidence and may support a separately authorized downstream probe, but it is not restored-P5 checkpoint, final-plan, final-seed-ranking, currentness, or publication ancestry.
29. `single_best_final_seed` consumes only already-frozen admissible final representatives and already-authenticated common-monitor target metric records under accepted target-only representative-ordering semantics; it performs no second target or M3 evaluation.

# Core record ownership

| Record / policy family | Owns | Must not own |
|---|---|---|
| `TrainingDataSource` / source records | source bytes/controls/composition/label-domain lineage | frame eligibility or evidence role |
| `TrainingFrameRecord` | immutable source-bound frame facts | eligibility, partition, membership, exposure |
| `FrameEligibilityDecision` | post-label/quality eligibility | partition or target membership |
| `PartitionAssignment` | one statistical role under DATA5/P1 policy | fitted quantities or target order |
| `PartitionFeasibilityReport` | whether requested evidence roles are supportable | fabricated independent evidence |
| `PartitionIndependenceReport` | actual independence/purge/duplicate limitations | stronger independence than observed |
| DATA6/7 fitted records | authorized training-partition descriptors/transforms/E0/difficulty/objective/weights/subset inputs | held-out labels, target membership, target size |
| target-size development split | one `P_train`/`M3` split derived from neutral substrate | training order or size choice |
| canonical training order `pi_train` | one deterministic order whose prefixes are candidate subsets | evaluation populations or size choice |
| canonical evaluation ladder `pi_eval` | nested direct populations `M1 subset M2 subset M3` | training membership or size choice |
| common target-size preparation | one P3 preparation identity shared by every candidate size/optimizer seed | restored foundation-P5 method/preparation authority |
| target-size policy / reducer decision | configured candidate ladder, fidelity funnel, recommendation/no-recommendation | freezing size; P5 monitor construction; P5 CV |
| `CampaignStore` provisional proposal | ordered collection of mutable `(N, T_N identity, selection source, H_cv, H_prod)` | immutable ancestry; running screen work |
| `CampaignStore` frozen selection | selected sizes bound to exact `T_N` memberships plus role horizons | re-deciding size or accepting P5 method |
| `OnlineTargetMonitorPolicy` / common P5 monitor record | campaign-common target-monitor evidence membership | target-training size; held-out fold membership |
| `ReplayMonitorPolicy` | replay-monitor evidence set | target-training size or replay-training membership |
| `PostSelectionMethodIdentity` | complete current restored-P5 method identity | realized fold/monitor/fitted/checkpoint/evaluation descendants |
| P5 fitted-preparation record | authorized fit result plus foundation selected-head/transfer evidence where applicable | target-size ownership; inert P3 weighting authority |
| CV/final role plans | role-specific P5 plan ancestry including same common monitor | alternate method/monitor authority |
| `PostSelectionMaterialization` | current executable P5 realization identity | independent method definition |
| final publication decision | frozen P5 member set before qualification | qualification-driven model selection |
| `TrainingProtocolIdentity` | broad general/historical DATA8 protocol for separately current non-P5 consumers | restored-P5 method authority |
| `ProtocolFreezeRecord` | applicable frozen protocol/committee identities and promotion evidence | locked-test results |
| calibration records | final-committee/publication uncertainty calibration/applicability | refitting the method being calibrated |
| locked-test activation/evidence | final sealed evaluation | upstream model-control decisions |
| `CandidateAdmissibilityDecision` | pre-query safety/admissibility | DFT convergence result |
| `AcquisitionDecision` | calibrated/rank-only acquisition result | post-DFT eligibility |

Every serialized current record SHALL carry a versioned schema, deterministic content identity, explicit upstream lineage, and explicit policy/failure identities as appropriate.

# Identity and leakage contract

## Source occurrence, geometry, and labels

Source occurrence (`frame_uid` or current equivalent), geometry fingerprint, label payload digest, and combined labeled-configuration fingerprint are distinct identities.

Geometry identity excludes energy/force/stress labels. Label identity includes selected labels and label-domain identity. Leakage audits use exact occurrence overlap, exact geometry overlap, exact labeled-configuration overlap, near-duplicate evidence where required, and forbidden temporal proximity.

## Label-domain compatibility

Label-domain identity separates theory/electronic-structure identity, energy-reference identity, derivative/stress convention, numerical-quality profile, and software provenance. A current compatibility policy may accept non-semantic provenance differences but cannot silently merge incompatible theory or energy-reference domains.

One target MACE artifact family contains one compatible target label domain plus a separately identified replay lineage where replay is enabled.

# Fitted-domain isolation

Raw physical/structural/event facts may be constructed before partitioning when the owning provider is partition-independent. Any learned/fitted transform—including scaling, PCA/whitening, fitted metrics, E0 corrections, or label-derived residual difficulty—is bound to a specific authorized gradient-training domain.

Before selection, the common P3 preparation is global. After admission of the ordered frozen collection, current restored-P5 fitted domains branch over each frozen size's exact membership `T_N` while sharing external `M_mon`:

```text
P_train / common P3 target-size preparation
  -> one pi_train and ordered collection of frozen sizes {N_selected}
  -> one external campaign-common M_mon + P1 separation evidence
  -> for each frozen size N_selected, exact T_N = pi_train[:N_selected]:
       |-> post-selection fold_training_partition_k(N)
       |     -> fold-local fitted P5 preparation from gradient-training labels only
       |     -> checkpoint/adaptive stop using external common M_mon
       |     -> held_out_evaluation_fold_k(N) only after checkpoint freeze
       |-> final-training fitted P5 preparation for complete T_N
             -> fresh final production using same external M_mon
             -> publication before downstream qualification
```

For foundation P5, transfer validation additionally binds selected foundation checkpoint/head, exact residual-fit inputs/result, numerical rank/null-space evidence, and every governed target composition class. Monitor/held-out geometry/composition may participate in transfer feasibility; their labels do not enter the fit.

A reverse dependency from held-out evaluation into fitted products, target size, checkpoint selection, common-monitor membership, or final-publication ranking is prohibited.

# Target membership and target-size contract

The current target-subset construction chain is:

```text
neutral statistical substrate
  -> one P_train / M3 development split
  -> one canonical training order pi_train
  -> one canonical evaluation ladder M1 subset M2 subset M3
  -> one common target-size preparation
  -> optional paired optimizer-seed automatic diagnostic (recommends only)
  -> operator-owned provisional design (ordered collection of (N, H_cv, H_prod))
  -> cross-validate admission
  -> ordered collection of frozen entries (N_selected, T_selected = pi_train[:N_selected], and role horizons)
```

No current alternate, migration, or rescue branch exists. Retired derived target-size state is rejected before reuse rather than translated.

The configured candidate ladder, screen `(n1,n2,n3)`, and independent production-horizon policy are owned by Architecture Part V and campaign configuration; they are not duplicated here.

Candidate membership at size `N` is exact prefix `pi_train[:N]`. `cross-validate` admission freezes the ordered collection of selected sizes, each with exact `T_selected = pi_train[:N]` and effective CV/production horizons. Identity projection stays role-specific: CV depends on the frozen CV horizon and never on production horizon, and vice versa.

Because every candidate is a prefix of one order, increasing `N` only adds frames; a non-monotone qualification result over nested increasing prefixes is an invariant failure.

# Current campaign lifecycle

The public campaign lifecycle, including configuration initialization, is:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`storage` is an orthogonal artifact-management command. `status` and `advance` project the same current owners. The campaign ends at fresh final-production closure; deployment, physical-observable, calibration, and locked-test qualification remain downstream contracts and cannot feed back into target-size or method selection.

# Training-method/protocol and checkpoint contract

## Restored current P5

`PostSelectionMethodIdentity` SHALL bind only current P5 method-bearing inputs, directly or through named component-policy digests. It SHALL NOT bind the whole P3 `TargetSizeCommonTrainingPolicy` merely because that object packages P3 objective/weighting/harness state.

Current P5 descendants additionally bind exact realized ancestry where appropriate:

```text
applicable selected target size and exact TargetBinding
post-selection fold train/eval/purge identity where applicable
replay source/training/monitor identities
one exact common target-monitor record identity
plan-level P1 monitor-vs-target separation evidence
foundation residual-fit/transfer evidence where applicable
checkpoint metric and replay-retention policy
optimizer/LR/stopping/epoch policy
seed policy
precision/backend/runtime identity
```

A comparison or CV claim applies only to the current method/plan actually evaluated.

Checkpoint selection uses explicit target/focus/replay/property/integrity constraints. A candidate violating a mandatory constraint is inadmissible even if another target metric is lower. The held-out fold does not choose its checkpoint.

## Broad DATA8/general protocols

`TrainingProtocolIdentity` may still bind foundation/model/head, selected membership, replay, objective/weights, exposure, checkpoint, optimizer, seed, precision/backend, and adapter/runtime identity for separately current non-P5 consumers that explicitly use that representation. It does not authorize restored P5.

# MACE realization and exposure

Current MACE artifacts contain only supported labels/weights/masks/compact identities in interchange formats; extended provenance remains sidecar/content-addressed.

The adapter verifies current upstream behaviors on which the applicable method semantics depend: head ordering, loader realization, loss realization, checkpoint retention/control, precision/backend, and effective target/replay exposure.

Loss/exposure resolution is mode-specific:

```text
P3 target-size screening        -> accepted weighted objective + complete-batch geometry
P5 scratch                      -> separately accepted weighted method
P5 naive foundation adaptation  -> native UniversalLoss + accepted target-only foundation geometry
P5 multihead replay adaptation  -> native UniversalLoss + replay-first combined foundation geometry
```

There is no global loss-family switch that may change an unaffected method family. Intended exposure cannot substitute for realized exposure. Silent loader duplication or changed corpus order/counts fail closed unless the accepted method explicitly binds that behavior.

Foundation P5 remains on the accepted single-process path until a distributed realization is separately D2-qualified.

Runtime/package locks are owned by narrow current runtime specifications and may evolve independently only when applicable equivalence/currentness obligations are satisfied.

# Sealed evaluation, calibration, and active learning

Development, calibration, and locked evaluation artifacts remain role-separated. Locked-test configuration/path access is absent from development control flow until explicit activation after the applicable protocol/publication freeze.

Calibration numerical thresholds derive from the actual frozen final committee/publication and a dedicated authorized calibration cohort. Applicability/transfer decisions explicitly distinguish within-domain, rank-only, recalibration-required, and incompatible-domain behavior.

Active-learning labels create a new development generation. Existing role assignments are inherited by default; repartitioning previously classified evidence creates a new evaluation lineage.

# Bounded execution and persistence

Scientific policy must be realizable without duplicating product-scale state per target-size rung. The current architectural materialization remains one fitted-input authority, one canonical training order, one common P3 target-size preparation, prefix metadata for candidate rungs, and only currently authorized training artifacts. Restored P5 adds one shared common-monitor record rather than one monitor per fold/size/seed.

Persistent execution caches are reconstructible unless another current specification explicitly makes them scientific evidence. Every cache validates semantic inputs and payload integrity. Corrupt/stale state is rebuilt or fails cleanly; it never changes policy to rescue a run.

Worker count, queue ordering, chunking, file-backed versus in-memory layout, and cache path are non-semantic only under the applicable exact-equivalence contract.

# Current-generation publication and failure rules

Current products SHALL fail closed when required source/label identity, evidence roles, fitted-partition lineage, target-size decision, replay/monitor lineage, post-selection acceptance, current method/protocol identity, runtime behavior, or publication payload validation is missing/incompatible.

For restored P5, incompatible historical weighted-stress foundation trajectories, fold-local target-monitor plans, M3-dependent P5 final plans/publications, from-scratch-E0 foundation preparations, target-first replay exposure records, missing-transfer preparations, and broad DATA8 `TrainingProtocolIdentity` payloads used as P5 authorization remain historical and cannot become current through deserialization.

Unsupported historical campaign schemas are not current compatibility obligations. Current code may retain low-level readers for forensic purposes, but those readers cannot create a second product-semantic path. Independently valid lower-level evidence may be reused only through its current owner and validation rules.

# Extension rule

A new feature/provider may enrich raw or DATA7 inputs without creating another membership selector. A new selector objective, target-size population, evidence role, loss function, stopping rule, common-monitor method, P5 method owner, final-publication selection rule, or compatibility generation changes accepted semantics at its owning D1-D4 layer and requires explicit revision plus qualification. Lower-layer implementation cannot silently compensate for an upstream change.