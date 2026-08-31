---
title: "MLFF Training-Data System Contract"
subtitle: "Cross-cutting current-generation invariants"
author: "mdstats project"
date: "2026-08-21"
geometry: margin=0.78in
toc: true
---

# Scope

This document is the cross-cutting current system contract for the mdstats MLFF training-data and fine-tuning workflow. The legacy filename is retained for stable references; this is **not** an implementation-stage plan.

It owns only invariants that span narrower specifications: evidence-role separation, dependency direction, identity/lineage, fitted-domain isolation, target-membership/target-size ownership, protocol identity, replay/monitor separation, sealed evaluation, calibration, bounded execution, and fail-closed current-generation publication.

Narrow specifications own exact module schemas, numerical constants, algorithms, storage formats, and runtime behavior. Architecture owns the higher-level dependency/ownership model. Workplans and historical documents are non-normative.

# Normative principles

1. Source facts, eligibility, evidence roles, fitted preparation, target membership, target size, weighting, exposure, checkpoint selection, validation, calibration, and acquisition are distinct record/decision families.
2. A frame that supplied a gradient is not independent validation evidence for that model.
3. Held-out cross-validation evaluates a frozen protocol and cannot control target size, stopping, or checkpoint choice for that protocol.
4. After target selection, every post-selection fold has a gradient-training partition, an authorized checkpoint monitor, and a held-out evaluation fold with explicit independence/purge evidence.
5. Cross-validation trains a fresh model/optimizer lineage for each held-out fold and validates the complete `TrainingProtocolIdentity` actually used by final training.
6. Feature fitting, E0 fitting, label-derived difficulty evidence, and target-subset inputs inspect only the applicable authorized training partition; post-selection fold-local fits never inspect that fold's held-out partition.
7. Current DATA6/DATA7 preparation publishes fitted inputs and evidence for the common target-size owner and SHALL NOT publish target membership or target size.
8. One canonical training order `pi_train` is the sole current target-membership authority; every candidate is the exact prefix `T_N = pi_train[:N]`.
9. The one target-size reducer is the sole scientific target-size authority. Monitor/replay/batch/pool cardinalities are different semantic types.
10. Target membership and the selected target size are both protocol-global and are frozen together as `N_selected` and `T_selected`.
11. Target-size screening uses only authorized development/model-selection evidence. Held-out CV, calibration, and locked tests are forbidden inputs.
12. Locked tests cannot affect fitting, membership, size, protocol choice, stopping, checkpointing, calibration-policy choice, or acquisition and are activated only after protocol/committee freeze.
13. Replay training, replay monitoring, target monitoring, and target training preserve separate source/role identities.
14. Replay retention and mandatory physical/deployment integrity are hard admissibility constraints unless an explicit current scientific policy states otherwise.
15. Dynamic resampling/exposure semantics require an explicit current adapter/protocol; static files alone cannot claim them.
16. Calibration is bound to predictions from the actual frozen final committee and an explicit applicability domain.
17. Active-learning child generations inherit prior evidence roles unless a new evaluation lineage explicitly reassigns them.
18. Retired campaign generations are rejected and re-prepared rather than migrated into current semantics. Retired derived target-size state is detected before any semantic deserialization, candidate or checkpoint reuse, or descendant publication, and is quarantined rather than translated. Only raw scientific inputs and independently valid low-level content caches whose recipes do not depend on retired target-size semantics may be reused, and each is re-validated by the current owner that consumes it.
19. Execution caches, worker scheduling, out-of-core layout, and other realization choices cannot change scientific identity or authoritative decisions.
20. Publication fails closed when required current-generation identities, upstream evidence, or schema/content validation are missing/incompatible.

# Core record ownership

| Record / policy family | Owns | Must not own |
|---|---|---|
| `TrainingDataSource` / source records | source bytes/controls/composition/label-domain lineage | frame eligibility or evidence role |
| `TrainingFrameRecord` | immutable source-bound frame facts | eligibility, partition, membership, exposure |
| `FrameEligibilityDecision` | post-label/quality eligibility | partition or target membership |
| `PartitionAssignment` | one statistical role under DATA5 policy | fitted quantities or target order |
| `PartitionFeasibilityReport` | whether requested evidence roles are supportable | fabricated independent evidence |
| `PartitionIndependenceReport` | actual independence/purge/duplicate limitations | stronger independence than observed |
| DATA6/7 fitted records | authorized training-partition descriptors/transforms/E0/difficulty/objective/weights/subset inputs | held-out labels, target membership, target size |
| target-size development split | one `P_train`/`M3` split derived from the neutral substrate | training order or size choice |
| canonical training order `pi_train` | one deterministic order whose prefixes are the candidate subsets | evaluation populations or size choice |
| canonical evaluation ladder `pi_eval` | nested direct populations `M1 subset M2 subset M3` | training membership or size choice |
| common target-size preparation | one preparation identity shared by every candidate size and optimizer seed | any per-size or per-seed variation |
| target-size policy / reducer decision | configured candidate ladder, fidelity funnel, selected target size or typed failure | monitor construction or post-selection cross-validation |
| `CampaignStore` terminal projection | `N_selected` bound to the exact `T_selected` membership digest | re-deciding the size or accepting the method |
| `OnlineTargetMonitorPolicy` | common target-monitor evidence set | target-training size |
| `ReplayMonitorPolicy` | replay-monitor evidence set | target-training size or replay-training membership |
| `TrainingProtocolIdentity` | complete frozen model/data/replay/membership/size/objective/exposure/checkpoint/runtime protocol | mutable runtime observations or test results |
| `ProtocolFreezeRecord` | frozen protocol/committee identities and promotion evidence | locked-test results |
| calibration records | final-committee uncertainty calibration/applicability | refitting the protocol being calibrated |
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

One target MACE bundle contains one compatible target label domain plus a separately identified replay lineage where replay is enabled.

# Fitted-domain isolation

Raw physical/structural/event facts may be constructed before partitioning when the owning provider is partition-independent. Any learned/fitted transform—including scaling, PCA/whitening, fitted metrics, E0 corrections, or label-derived residual difficulty—is bound to a specific authorized gradient-training domain.

Before selection, the common preparation is global. After selection, a
post-selection fold `k` may have a fold-local fitted view. The allowed
directions are:

```text
P_train / common target-size preparation
  -> one pi_train and exact T_selected membership after the target-size freeze
  -> post-selection fold_training_partition_k
  -> fold-local fitted products and checkpoint choice using its authorized monitor
  -> held_out_evaluation_fold_k only after checkpoint freeze

final T_selected
  -> final-training fitted products
  -> fresh final production
```

A reverse dependency from held-out evaluation into fitted products, target size, or checkpoint selection is prohibited.

# Target membership and target-size contract

The current target-subset construction chain is:

```text
neutral statistical substrate
  -> one P_train / M3 development split
  -> one canonical training order pi_train
  -> one canonical evaluation ladder M1 subset M2 subset M3
  -> one common target-size preparation
  -> paired optimizer-seed screen over the configured candidate ladder
  -> one target-size reducer
  -> N_selected and T_selected = pi_train[:N_selected]
```

No current alternate, migration, or rescue branch exists. Retired derived
target-size state is rejected before reuse rather than translated.

The configured candidate ladder, the screen `(n1,n2,n3)`, and the independent
production-horizon policy are owned by the architecture manual's Part V and the
campaign configuration; they are not duplicated here.

Candidate membership at size `N` is the exact prefix `pi_train[:N]`. The selected
`N` and its exact membership `T_selected` are frozen together into the complete
training protocol.

Because every candidate is a prefix of one order, increasing `N` only adds
frames; a non-monotone qualification result over nested increasing prefixes is an
invariant failure.

# Current campaign lifecycle

The public campaign lifecycle, including configuration initialization, is:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`storage` is an orthogonal artifact-management command. `status` and `advance`
project the same current owners. The P6 campaign ends at fresh final-production
closure; deployment, physical-observable, calibration, and locked-test
qualification remain downstream contracts; downstream qualification cannot feed
back into target-size or method selection.

# Training-protocol and checkpoint contract

`TrainingProtocolIdentity` SHALL bind, as applicable:

```text
foundation/model/head identity
selected target size and exact global membership identity
post-selection fold partition identity where the protocol is a CV fold
replay source/training/monitor identities
common target-monitor identity
objective and configuration/property weights
exposure backend and realized balancing/duplication policy
checkpoint metric and replay-retention policy
optimizer/LR/stopping/epoch policy
seed policy
precision/backend
MACE adapter/runtime lock
```

A comparison or CV claim applies only to the protocol identity actually evaluated.

Checkpoint selection uses explicit target/focus/replay/property/integrity constraints. A candidate violating a mandatory constraint is inadmissible even if another target metric is lower.

# MACE realization and exposure

Current MACE artifacts contain only supported labels/weights/compact identities in their interchange format; extended provenance remains sidecar/content-addressed.

The adapter verifies current upstream behaviors on which protocol semantics depend: head ordering, loader realization, checkpoint retention/control, precision/backend, and effective target/replay exposure.

Intended exposure cannot substitute for realized exposure. Silent loader duplication or changed target/replay counts fail closed unless the accepted current protocol explicitly binds that behavior.

Runtime/package locks are owned by the narrow current runtime specification and may evolve independently of this cross-cutting contract.

# Sealed evaluation, calibration, and active learning

Development, calibration, and locked evaluation artifacts remain role-separated. Locked-test configuration/path access is absent from development control flow until explicit activation after protocol/committee freeze.

Calibration numerical thresholds derive from the actual frozen final committee and a dedicated authorized calibration cohort. Applicability/transfer decisions explicitly distinguish within-domain, rank-only, recalibration-required, and incompatible-domain behavior.

Active-learning labels create a new development generation. Existing role assignments are inherited by default; repartitioning previously classified evidence creates a new evaluation lineage.

# Bounded execution and persistence

Scientific policy must be realizable without duplicating product-scale state per target-size rung. The current architectural materialization is one fitted-input authority, one canonical training order, one common target-size preparation, prefix metadata for candidate rungs, and only currently authorized training artifacts.

Persistent execution caches are reconstructible unless another current specification explicitly makes them scientific evidence. Every cache validates semantic inputs and payload integrity. Corrupt/stale state is rebuilt or fails cleanly; it never changes policy to rescue a run.

Worker count, queue ordering, chunking, file-backed versus in-memory layout, and cache path are non-semantic under an exact-equivalence contract.

# Current-generation publication and failure rules

Current products SHALL fail closed when required source/label identity, evidence roles, fitted-partition lineage, target-size decision, replay/monitor lineage, post-selection acceptance, training protocol, runtime behavior, or publication payload validation is missing/incompatible.

Unsupported historical campaign schemas are not current compatibility obligations. Current code may retain low-level readers for forensic purposes, but those readers cannot create a second product-semantic path and are not normative documentation authority. The immediate fixed-fidelity predecessor is handled only by the explicit fail-closed re-authentication boundary above; it is not blanket historical compatibility.

# Extension rule

A new feature/provider may enrich raw or DATA7 inputs without creating another membership selector. A new selector objective, target-size population, evidence role, loss function, stopping rule, or compatibility generation changes scientific protocol semantics and requires explicit architecture/specification revision plus qualification.
