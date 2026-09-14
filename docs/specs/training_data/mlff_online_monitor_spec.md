# MLFF common online-monitor specification

**Status:** current normative monitoring policy  
**Restored P5 scope:** exact campaign-common target monitor plus independent replay monitor

## 1. Scope and semantic type boundary

This specification defines deterministic campaign-common **monitoring evidence**. It does not define target-training size, replay-training membership, checkpoint score thresholds, or held-out cross-validation roles.

The current policy families are type-distinct:

```text
OnlineTargetMonitorPolicy
ReplayMonitorPolicy
ResolvedTargetSizePolicy
```

Their records SHALL remain distinct even when two cardinalities share an integer value. Online monitors never supply gradients.

## 2. Common target monitor

`OnlineTargetMonitorPolicy` owns the current campaign-common target checkpoint monitor used by restored P5. The exact monitor record is constructed once and reused across every selected target size, CV fold, CV seed, and final-production seed/run belonging to the same current campaign/method lineage.

The current P5 values are:

```text
requested cardinality = 256
realized cardinality  = 256
seed                  = 161803
parent role           = OUTER_MONITOR
```

Fewer than 256 usable eligible parent configurations is typed P5 infeasibility. There is no current P5 short-parent success state and no shrink-to-fit fallback.

The exact deterministic stratification, quota, marker, ordering, and systematic-selection semantics are D2 authority. The record SHALL preserve enough evidence to reconstruct the exact ordered membership.

### Parent role and label usability

The target-monitor parent is the neutral authorized label-usable `OUTER_MONITOR` domain. Gradient-training, held-out CV evaluation, calibration, purge-only, excluded, and locked-test roles are not eligible parents.

The monitor constructor validates label-domain compatibility and target metric label usability before a current record is admitted.

### Membership before relation qualification

Monitor membership and target/monitor protected-relation separation are distinct responsibilities.

The required order is:

1. select exact 256 membership from the label-usable neutral parent under the accepted D2 monitor algorithm;
2. persist/authenticate the common monitor record; then
3. use canonical P1 protected-relation authority over the joint monitor/target universe to prove separation from every governed `T_N`.

A relation conflict causes failure. The constructor/planner SHALL NOT relation-prefilter the parent, delete/replace a conflicting selected member, or resample another monitor.

`SelectedRelationProjection` alone is insufficient to prove this cross-role separation because it intentionally excludes frames outside `T_selected`.

## 3. `OnlineTargetMonitorRecord`

The current record binds at least:

```text
target-monitor role
neutral parent identity/digest
OnlineTargetMonitorPolicy digest
requested size = 256
realized size = 256
exact ordered selected identities/source indices
accepted D2 stratum/quota/order evidence
strategy/seed identity
label-domain identity
label-usability evidence
exact membership/content digest
```

A current CV/final plan additionally binds the plan-level protected-relation separation evidence; that separation evidence is not folded into monitor membership identity because it depends on the governed selected target set(s).

Every current sibling CV/final plan SHALL bind the same common-monitor record digest.

## 4. Independent true-label replay monitor

`ReplayMonitorPolicy` owns replay-monitor construction. The current default requested replay-monitor cardinality is:

```text
512 configurations
```

Replay monitoring is independent of the common target monitor and of replay-training membership.

Foundation pseudo-label replay is explicit opt-in. When used for training, an independent TRUE_DFT replay monitor is required for retention evidence.

Replay train and replay monitor configurations remain geometry/role separated under their governing contract. Current replay-monitor fallback behavior, where separately accepted, does not imply any fallback for the P5 target monitor.

## 5. P5 owner binding

Current restored P5 binds target monitor identity through `PostSelectionMethodIdentity` descendants and the CV/final plans described in `mlff_post_selection_p5_spec.md`.

Broad historical/general `TrainingProtocolIdentity` monitor fields do not create a second current P5 owner. Historical monitor records may remain readable but cannot authorize current P5 if they encode fold-local target monitors, different parents, short-parent target success, or other superseded semantics.

## 6. Leakage and independence invariants

- Monitoring configurations never contribute gradients.
- The common target monitor is development/model-control evidence, not held-out CV evidence.
- Held-out CV evaluation and locked tests cannot be promoted into monitor roles.
- Exact common-monitor membership is reused; it is not redrawn per size, fold, seed, epoch, or final run.
- Protected-relation qualification occurs after exact membership construction and cannot mutate membership.
- The monitor seed/policy is identity, not an informal hint.
- Monitor cardinality is never interpreted as `N_selected`.
- Common-monitor labels may control checkpoints/adaptive stop and contribute representative target metrics, but they do not enter P5 residual-E0 fitting.

## 7. Relationship to target-size study

P3 target-size screening may have separately accepted development-monitor consumption, but it does not own current restored-P5 monitor construction and cannot turn monitor cardinality into target size.

A P5-only monitor-generation/currentness cutover SHALL NOT blanket-invalidate unchanged P3 evidence unless the actual P3 monitor semantics it consumes changed.

## 8. Precision and accumulation boundary

Monitor inference uses the learned model precision/backend bound by the applicable current method/runtime identity. mdstats-owned metric accumulation remains under its numerical-precision authority.

Changing a numerically material precision/backend field changes the relevant method/runtime identity where required by current contracts.

## 9. Persistence and unsupported historical records

Current target-monitor artifacts are accepted only when their current schema, exact content, neutral parent lineage, policy digest, label usability, and exact-256 requirement validate.

Obsolete fold-local, alternate-parent, M3-derived, short-target-monitor, or otherwise incompatible target-monitor records remain historical. Compatibility deserialization cannot make them current.

## 10. Acceptance requirements

Current monitor qualification covers at least:

1. deterministic exact target membership regeneration;
2. exact target requested/realized size 256 with no short-parent success;
3. common target-monitor identity across all current sibling CV/final plans;
4. accepted D2 stratum/quota/time-selection behavior;
5. label-domain/metric-label usability;
6. post-sampling protected-relation failure without resampling;
7. proof that selected-only relation projection is not the sole cross-role authority;
8. independent TRUE_DFT replay-monitor enforcement where required;
9. current P5 plan/identity binding;
10. corruption/staleness rejection; and
11. proof that monitor cardinalities are not consumed as target-size authority.