---
kind: R3-canonical-D3-promotion-status
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R3
protocol_version: 6.3.0
status: PASS_PROMOTED_D4_AUTHORIZED
accepted_r3_candidate: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
independent_rereview_commit: d575feb36f80f1d8e6abe434005237b410830163
canonical_d3_promotion_commit: 3789e11ed9d652aff29cd61dc3158556f27e4644
d4_authorized: true
---

# R3 canonical D3 promotion status

## Verdict

**PASS / PROMOTED.** The independently passed repaired R3 architecture has been reconciled into current canonical D3. The promotion is internally consistent and no stale competing current target-order ownership was found in the canonical MLFF D3 chapter set.

D4 implementation is now authorized under the accepted R1 D1/D2 method, closed R2 provenance map, and promoted current D3 architecture.

## Canonical promotion

The promotion added the dedicated detailed owner:

- `docs/arch_manuals/mlff_training_data/45_target_training_order.md`

and reconciled the affected canonical owners:

- `docs/arch_manuals/mlff_training_data_architecture.md`;
- `docs/arch_manuals/mlff_training_data/00_front_matter.md`;
- `docs/arch_manuals/mlff_training_data/README.md`;
- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md`;
- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- `docs/arch_manuals/mlff_training_data_dependency_graph.json`.

The promotion is a direct canonical reconciliation, not a permanent amendment overlay.

## Consistency / stale-owner check

The promoted current D3 has one coherent target-order story:

```text
exact P_train
 -> sole TargetCoverageReference
 -> one canonical membership-obligation authority
 -> one shared exact FEAS1/NEIGHBOR1 construction
      -> FEAS1 support/capacity
      -> authenticated NEIGHBOR1
           -> MVIDX adoption/inversion
                -> MVSEL2
                -> configured REPAIR2
                -> exact repaired-prefix reconstruction
                -> complete TargetTrainingOrder
 -> independent MVQUAL from primitive definitions
 -> current P2 projection
 -> unchanged P3/CV/replay/production
```

Checks closed:

1. DATA6/DATA7 may supply raw/provider/lineage inputs but no longer own a competing fitted selector metric/reference.
2. `TargetCoverageReference` is the sole selector-specific fitted numerical product on exact current `P_train`.
3. the normal path contains one shared exact neighborhood construction rather than separate FEAS/MVIDX geometry owners;
4. the canonical obligation authority is explicit and shared; MVIDX is representation, not semantic definition;
5. MVQUAL remains independent membership qualification and has no target-size outcome ranking authority;
6. pre-adoption MVSTATE/history/checkpoint state is subordinate authenticated `prepare`/prepared-storage build state and cannot establish CampaignStore currentness;
7. the execution chapter no longer claims a neutral substrate directly supplies both `pi_train` and `pi_eval`; the restored target order has its own accepted chain while `pi_eval/M1/M2/M3` remain under existing owners;
8. P3/CV/replay/production/qualification retain no reverse control edge into target-order membership;
9. old `candidate_independent_priority.v1` order products are stale/reconstructible at cutover rather than semantically migrated;
10. no selector-specific currentness database, migration router, alternate suffix selector, or GC owner was introduced.

The companion dependency graph was advanced to schema version 5 and expresses the same ownership/dependency direction.

## D4 authorization boundary

D4 may now implement the accepted architecture using the sequence and acceptance obligations in:

- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF_REPAIRED.md`;
- canonical D3 `docs/arch_manuals/mlff_training_data/45_target_training_order.md`;
- the accepted scoped D1/D2 target-order method papers;
- the closed R2 dependency/provenance map;
- composed workplan Revisions 5-8.

D4 remains free to choose exact class/module names, schema field names, checkpoint layout and local helper structure while preserving the accepted ownership/identity/restart/resource relations.

The first product mutation must not partially activate the restored selector. Policy/schema/currentness cutover becomes current only when the restored path is complete enough to satisfy the accepted publication/currentness contract. Old/new selector routers and hidden UID fallback are forbidden.

Final production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.
