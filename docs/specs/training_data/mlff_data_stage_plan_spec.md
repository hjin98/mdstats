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

It owns only invariants that span narrower specifications: evidence-role separation, dependency direction, identity/lineage, fitted-domain isolation, target-membership/target-size ownership, current P5 method ownership, replay/monitor separation, sealed evaluation, bounded execution, and fail-closed current-generation publication.

Narrow specifications own exact module schemas, numerical constants, algorithms, storage formats, and runtime behavior. D3 architecture owns the higher-level ownership graph. Workplans and historical documents are non-normative once their binding semantics are promoted into current D1-D4 authority.

# Normative principles

1. Source facts, eligibility, evidence roles, fitted preparation, target membership, target size, weighting, exposure, checkpoint selection, validation, and qualification are distinct record/decision families.
2. A frame that supplied a gradient is not independent validation evidence for that model.
3. Held-out cross-validation evaluates a frozen P5 method and cannot control target size, fitting, stopping, or checkpoint choice for that fold.
4. After target selection, every current post-selection fold has a gradient-training partition, a held-out outer-evaluation partition, and accepted purge/exclusion evidence. The target checkpoint monitor is external campaign-common evidence, not fold membership.
5. Cross-validation trains a fresh model/optimizer lineage for each held-out fold and validates the current `PostSelectionMethodIdentity` actually used by final production.
6. Current P5 has one method authority: `PostSelectionMethodIdentity`. Broad DATA8-era `TrainingProtocolIdentity` records do not authorize restored P5.
7. Feature fitting, E0 fitting, and other label-derived fitted products inspect only their authorized training partition. Foundation-P5 transfer checks may inspect governed geometry/composition classes from monitor/evaluation consumers but not their labels for fitting.
8. Current DATA6/DATA7 preparation publishes fitted inputs/evidence for upstream selection/P3 owners and SHALL NOT publish target membership or target size.
9. One canonical training order `pi_train` is the sole current target-membership authority; every candidate is exact prefix `T_N = pi_train[:N]`.
10. The target-size reducer recommends only. The operator owns provisional choice, and `cross-validate` admission freezes exact selected memberships and role horizons.
11. Target-size screening uses only authorized development/model-selection evidence. Held-out CV and locked evidence are forbidden inputs.
12. Replay training, replay monitoring, target monitoring, and target training preserve separate source/role identities.
13. Current P5 target checkpoint control uses one immutable campaign-common exact 256-frame monitor `M_mon` from neutral `OUTER_MONITOR`, reused across every selected size, CV fold/seed, and final-production seed/run.
14. Monitor sampling precedes protected-relation qualification. Relation conflict or insufficient exact support fails closed; monitor members are not filtered, replaced, or resampled into a different method.
15. Every current CV and final-production plan binds the same common-monitor record digest and current cross-role P1 separation evidence.
16. Foundation P5 uses selected-head foundation-residual E0 fitting and composition-level transfer validation. Historical/from-scratch foundation preparation is not current.
17. Foundation P5 does not bind the whole P3 `TargetSizeCommonTrainingPolicy` or nontrivial P3 configuration-weight fitting.
18. Foundation P5 realizes native MACE UniversalLoss with accepted fixed parameters through the one MACE adapter; P3 and P5 scratch retain separately accepted weighted methods.
19. Retired target/replay training-head scalar weights are absent from current P5. Checkpoint/adaptive-stop target/replay score weights remain separate owners.
20. Foundation P5 exposure binds replay/`pt_head` first then target before shuffle, no implicit target duplication, `drop_last=true`, and the qualified single-process path. Distributed foundation P5 fails closed pending separate equivalence acceptance.
21. Canonical single-source replay omission resolves TRUE_DFT; explicit pseudo replay remains opt-in and requires independent TRUE_DFT replay monitoring. Ambiguous omitted legacy split-file semantics fail closed.
22. Final production is fresh and uses the same common monitor as accepted CV.
23. M3 is not P5 checkpoint, final-seed ranking, plan, currentness, or publication ancestry. M3 remains P3 evidence and may feed separately authorized downstream probes only through the P3 owner.
24. `single_best_final_seed` selects only among already-frozen admissible representatives using already-authenticated common-monitor target records and accepted target-only ordering semantics. It performs no second target or M3 evaluation.
25. Locked tests cannot affect fitting, membership, size, method choice, stopping, checkpointing, publication membership, calibration-policy choice, or acquisition.
26. Retired campaign generations are rejected/quarantined rather than migrated into current semantics. Independently valid upstream evidence may be reused only through its current owner.
27. Execution caches, worker scheduling, storage layout, and other realization choices cannot change scientific/numerical identity.
28. Publication fails closed when required current identities, upstream evidence, or content validation are missing/incompatible.

# Core record ownership

| Record / policy family | Owns | Must not own |
|---|---|---|
| `TrainingDataSource` / source records | source bytes/controls/composition/label-domain lineage | frame eligibility or evidence role |
| `TrainingFrameRecord` | immutable source-bound frame facts | eligibility, partition, membership, exposure |
| `FrameEligibilityDecision` | post-label/quality eligibility | partition or target membership |
| neutral DATA5/P1 role/relation records | statistical roles and protected relations | fitted quantities or target order |
| DATA6/7 fitted records | authorized descriptors/transforms/difficulty/foundation evidence | held-out labels, target membership, target size |
| target-size development split | one `P_train`/M3 split | training order or size choice |
| canonical `pi_train` | one deterministic training order | evaluation populations or size choice |
| common P3 preparation | P3 training preparation shared as accepted | P5 foundation method authority |
| target-size reducer decision | recommendation or typed no-recommendation | freezing size; P5 monitor/CV |
| `CampaignStore` frozen selection | selected sizes and exact `T_N` identities + role horizons | re-deciding size or accepting P5 |
| common P5 target-monitor record | exact `M_mon` membership and lineage | target-training size; held-out CV membership |
| `PostSelectionMethodIdentity` | current P5 method identity | realized fold/monitor/fitted/checkpoint results |
| P5 fitted preparation | authorized fit result + foundation transfer evidence | target-size ownership; inert P3 weighting authority |
| CV/final role plans | role-specific descendant lineage | alternate method or monitor construction |
| `PostSelectionMaterialization` | executable P5 realization identity | independent scientific method definition |
| final publication decision | frozen P5 member set before qualification | downstream qualification-driven selection |
| `TrainingProtocolIdentity` | separately current non-P5 general/historical DATA8 identity where still consumed | restored P5 authority |
| qualification records | downstream release evidence for frozen publication | P5 target/method/checkpoint/member selection |

Every serialized current record SHALL carry a versioned schema, deterministic content identity, explicit upstream lineage, and explicit policy/failure identities as appropriate.

# Fitted-domain isolation

Before target selection, fitted products are owned by their authorized upstream domains. After admission of a frozen selected size, current P5 branches as:

```text
TargetBinding
  + common M_mon record
  + current P1 separation evidence
  + PostSelectionMethodIdentity
  -> CV fold k:
       gradient-training membership
         -> fold fitted preparation
         -> checkpoint/adaptive stop on external M_mon
         -> held-out evaluation after checkpoint freeze
  -> final production:
       complete T_selected fitted preparation
         -> fresh production
         -> representative metric on same external M_mon
         -> publication decision
```

No reverse dependency from held-out evaluation or downstream qualification into fitting, checkpoint selection, target size, or method identity is permitted.

# Current P5 monitor contract

Current `OnlineTargetMonitorPolicy` for P5 is exact, not best-effort:

```text
parent role        OUTER_MONITOR
requested size     256
realized size      256
seed               161803
shortfall          infeasible/fail closed
```

The exact deterministic construction is owned by D2 and the narrow monitor specification. Membership is selected once, then canonical P1 cross-role separation is checked against every governed `T_N`. A selected-only relation projection is insufficient as sole proof.

# Current P5 protocol and MACE realization

`PostSelectionMethodIdentity` binds the current P5 method. Foundation modes resolve native MACE UniversalLoss with accepted fixed objective; scratch and P3 keep their own methods. Foundation P5 uses no active general configuration-weight layer and no target/replay training-head scalar balancing.

The one MACE adapter verifies method-specific head ordering, loader realization, loss resolution, checkpoint retention/control, precision/backend, and effective exposure. Intended exposure cannot substitute for realized evidence.

# Final publication contract

Current final publication reauthenticates target binding, accepted CV, current P5 method, production plan, common-monitor lineage, fitted preparation, run representative, and required metric records.

`all_qualified_final_seeds` publishes all required admissible representatives. `single_best_final_seed` reuses accepted target-only representative-ordering semantics over frozen common-monitor metric records and never reruns target/M3 evaluation.

Downstream qualification consumes the publication and cannot alter membership.

# Bounded execution and persistence

Scientific policy must be realizable without duplicating product-scale state per target-size rung. Persistent execution caches are reconstructible unless another current specification explicitly makes them evidence. Corrupt/stale state is rebuilt or fails cleanly; policy is not changed to rescue a run.

Worker count, queue ordering, chunking, and storage layout are non-semantic only under the accepted equivalence contract. Current foundation P5 specifically remains single-process until distributed equivalence is accepted.

# Current-generation publication and failure rules

Current products SHALL fail closed when required source/label identity, evidence roles, fitted lineage, target binding, common-monitor lineage/separation, replay lineage, P5 method identity, foundation transfer evidence, runtime realization, or publication payload validation is missing/incompatible.

Historical readers cannot create a second product-semantic path. Old stress/fold-local/M3-P5/from-scratch-foundation/missing-transfer/target-first P5 records remain historical even if readable.

# Extension rule

A new feature/provider may enrich upstream evidence without creating another membership selector, P5 method owner, target monitor, E0 solver, or publication selector. A change to accepted scientific meaning routes to D1; a change to numerical method/equivalence routes to D2; ownership/topology changes route to D3; local schema/concretization changes under the accepted graph remain D4.