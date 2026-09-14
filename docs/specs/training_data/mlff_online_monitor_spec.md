# MLFF common online-monitor specification

**Status:** current normative monitoring policy  
**Architecture:** restored-P5 reconciliation 2026-09-14

## 1. Scope and semantic type boundary

This specification defines deterministic campaign-common **monitoring evidence**. It does not define target-training size, replay-training membership, checkpoint score thresholds, or held-out cross-validation roles.

The current policy families are type-distinct:

```text
OnlineTargetMonitorPolicy
ReplayMonitorPolicy
ResolvedTargetSizePolicy
```

Their records SHALL remain distinct even when two cardinalities happen to share an integer value.

Online monitors never supply gradients.

## 2. Common target monitor

`OnlineTargetMonitorPolicy` owns the common target-monitor subset used by authorized development/model-selection procedures. For **restored current P5**, it is the single target checkpoint/adaptive-stop monitor `M_mon` reused by every selected size, CV fold/seed, and final-production seed/run belonging to the same current campaign/method lineage.

The current requested target-monitor cardinality is exactly:

```text
256 configurations
```

For restored P5 the realized cardinality is also exactly 256. Fewer than 256 usable eligible configurations is typed P5 infeasibility; there is no current P5 short-parent success state or shrink fallback.

The current deterministic monitor seed is:

```text
161803
```

The current default strategy identity is:

```text
balanced_condition_run_time_systematic
```

Changing requested cardinality, seed, strategy, or another policy field changes the policy identity.

### Parent role

For restored P5, the target-monitor parent is the neutral label-usable `OUTER_MONITOR` domain only. Gradient-training, held-out CV evaluation, calibration, purge-only, excluded, and locked-test roles are not eligible parents.

Historical/general references to a DATA5 common outer/development-monitor parent are compatibility descriptions; current P5 resolves the neutral parent through the current P1/neutral-substrate authority and does not reactivate a pre-target DATA5 CV owner.

### Deterministic selection

The current target-monitor constructor preserves the accepted D2 deterministic construction. At the representation level it records the governed strata/quotas, source/run/time ordering evidence, seed-derived deterministic choices, exact ordered frame/source identities, requested/realized size, policy identity, and label-domain identity required to reconstruct membership.

Every current P5 size/fold/seed/final run using the same compatible campaign monitor identity receives the exact same target-monitor membership/content identity.

### Membership before protected-relation qualification

Monitor membership construction and target/monitor protected-relation qualification are different owners and occur in this order:

1. validate the label-usable neutral `OUTER_MONITOR` parent;
2. sample the exact 256 members under accepted D2;
3. persist/authenticate the immutable monitor record; then
4. use canonical P1 protected-relation authority over the joint monitor/target universe to prove separation from every governed `T_N`.

A protected-relation conflict fails plan admission. The implementation SHALL NOT relation-prefilter the parent, delete/replace a conflicting selected member, or resample another target monitor.

The selected-only `SelectedRelationProjection` is insufficient as the sole proof of this cross-role separation because it intentionally excludes frames outside `T_selected`.

## 3. Independent true-label replay monitor

`ReplayMonitorPolicy` owns replay-monitor construction. The current default requested replay-monitor cardinality remains exactly:

```text
512 configurations
```

The default replay-monitor strategy remains:

```text
chemistry_size_systematic
```

The true-label replay monitor parent must satisfy the current true-label replay contract. Foundation pseudo labels may be used by a separately identified replay-training path when allowed, but they do not define an absolute true-label replay-validation metric.

Replay-monitor selection uses deterministic ordering across chemistry/composition, atom-count/size grouping, and source order followed by the current systematic selection rule. The materialized replay-monitor artifact is immediately re-inspected; ordered geometry identity, label identity, and true-label mode must match its selection record.

When fewer than 512 eligible true-label replay configurations exist, all eligible configurations are used and the replay-monitor fallback is explicit. This retained replay-monitor behavior does **not** imply a fallback for the restored-P5 256-frame target monitor.

Replay training and replay monitoring are different evidence roles and may not silently alias one another.

## 4. Record contracts

### `OnlineTargetMonitorRecord`

Binds at least:

- target-monitor role;
- neutral parent-domain identity/digest;
- `OnlineTargetMonitorPolicy` digest;
- requested size;
- realized size;
- exact ordered selected identities/source indices;
- per-stratum available/selected and other D2 reconstruction evidence;
- strategy and seed;
- label-domain identity; and
- label-usability evidence required by the consuming target metric.

For restored current P5, requested and realized sizes are both exactly 256 and no target-monitor fallback reason can authorize success.

Plan-level protected-relation separation evidence is a descendant of the monitor record and the governed target binding(s); it is not folded into monitor membership identity.

### `ReplayMonitorRecord`

Binds at least:

- replay-monitor role;
- replay source/label lineage;
- `ReplayMonitorPolicy` digest;
- requested and realized sizes;
- exact ordered selected identities/source indices;
- strategy/seed fields owned by the replay policy;
- true-label mode where required;
- materialized artifact digest where applicable; and
- explicit replay fallback reason where applicable.

For restored P5, the exact common target-monitor record is bound by current CV/final plans descending from `PostSelectionMethodIdentity`. Broad `TrainingProtocolIdentity` monitor fields remain applicable only to separately current non-P5 consumers/history and do not create a second P5 owner.

## 5. Leakage and independence invariants

- Monitoring configurations never contribute gradients.
- The common target monitor is development/model-control evidence, not held-out CV evidence.
- Held-out CV evaluation and locked tests cannot be promoted into online-monitor roles.
- Target-training geometries may not violate governing replay-monitor separation requirements.
- Restored-P5 target-monitor membership is selected once per compatible campaign identity and reused; it is not redrawn per epoch, selected size, fold, seed, or final run.
- Target-monitor membership is not mutated to repair protected-relation conflicts.
- The monitor seed is policy identity, not an informal hint.
- A monitor cardinality is never interpreted as `N_selected`.
- Common target-monitor labels may control checkpoint/adaptive-stop choice and representative target metrics but may not enter foundation-P5 residual-E0 fitting.

## 6. Relationship to target-size study

The target-size reducer may consume monitor evidence only under its separately accepted P3 method. The target-size study does not own restored-P5 monitor construction and cannot change common-monitor membership between P5 sizes/folds/seeds.

The target-size ladder remains an independent population; monitor sizes 256 and 512 are semantically independent of target-training size.

A P5-only monitor schema/currentness cutover SHALL NOT blanket-invalidate unchanged P3 evidence unless an actual shared P3 monitor semantic changed.

## 7. Precision and accumulation boundary

Monitor inference uses the learned-model precision/backend declared by the applicable current method/runtime identity. For broad non-P5 DATA8 consumers this may be `TrainingProtocolIdentity`; for restored P5 it is the current P5 method/runtime lineage. mdstats-owned metric accumulation remains under the current numerical-precision specification and is not weakened by model dtype.

Changing a numerically material model precision/backend creates a different applicable method/runtime identity where the current architecture declares it method-defining.

## 8. Persistence and unsupported historical records

Current monitor artifacts are accepted only when their current schema, content, parent lineage, policy digests, and consumer-specific invariants validate.

For restored P5, obsolete fold-local, final-specific, M3-derived, alternate-parent, or short target-monitor records remain historical. Compatibility aliases/deserialization cannot make them current.

A campaign whose required current monitor records cannot validate under the applicable generation requires re-preparation or typed infeasibility; it does not silently reinterpret old monitor semantics.

## 9. Acceptance requirements

Current monitor qualification covers at least:

1. deterministic target/replay membership regeneration;
2. restored-P5 exact target requested/realized size 256 with no short-parent success;
3. common target-monitor identity across every compatible current P5 size/fold/final/seed plan;
4. accepted condition/run/time or more exact D2 distribution semantics rather than first-N truncation;
5. target-monitor label usability;
6. post-sampling protected-relation failure without filtering/replacement/resampling;
7. proof that selected-only relation projection is not the sole target-vs-monitor separation authority;
8. true-label replay enforcement where required and exact replay artifact round-trip;
9. applicable method/plan identity binding;
10. corruption/staleness rejection; and
11. proof that monitor cardinalities are not consumed as target-size authority.