# MLFF common online-monitor specification

**Status:** current normative monitoring policy  
**Architecture:** revision 105

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

`OnlineTargetMonitorPolicy` owns the common target-monitor subset used by authorized development/model-selection procedures, including target-size screening and current checkpoint/stopping control when those consumers explicitly bind this monitor.

The current default requested target-monitor cardinality is exactly:

```text
256 configurations
```

The current deterministic monitor seed is:

```text
161803
```

The current default strategy is:

```text
balanced_condition_run_time_systematic
```

Changing the requested cardinality, seed, strategy, or other policy field changes the policy identity.

### Parent role

The target-monitor parent is the DATA5 common outer-monitor/development-monitor domain only. Gradient-training, held-out CV evaluation, calibration, purge-only, excluded, and locked-test roles are not eligible parents.

### Deterministic selection

The current target-monitor constructor:

1. groups eligible monitor units by declared condition and source/run identity;
2. allocates the requested budget as evenly as possible across eligible strata under the current deterministic apportionment rule;
3. orders configurations by source trajectory/time within each stratum;
4. uses the policy seed for deterministic random-start systematic sampling;
5. emits exact ordered configuration identities, source indices, stratum available/selected counts, requested/realized size, policy identity, and label-domain identity.

Every fold, seed, training mode, and final-development job using the same compatible campaign monitor identity receives the same target-monitor membership/content identity.

When fewer than 256 eligible configurations exist, all eligible configurations are used and the short-parent fallback is explicit in the record. The realized monitor size remains a monitor property and does not become a target-training size.

## 3. Independent true-label replay monitor

`ReplayMonitorPolicy` owns replay-monitor construction. The current default requested replay-monitor cardinality is exactly:

```text
512 configurations
```

The default replay-monitor strategy is:

```text
chemistry_size_systematic
```

The true-label replay monitor parent must satisfy the current true-label replay contract. Foundation pseudo labels may be used by a separately identified replay-training path when allowed, but they do not define an absolute true-label replay-validation metric.

Replay-monitor selection uses deterministic ordering across chemistry/composition, atom-count/size grouping, and source order followed by the current systematic selection rule. The materialized replay-monitor artifact is immediately re-inspected; ordered geometry identity, label identity, and true-label mode must match its selection record.

When fewer than 512 eligible true-label replay configurations exist, all are used and the fallback is explicit.

Replay training and replay monitoring are different evidence roles and may not silently alias one another.

## 4. Record contracts

### `OnlineTargetMonitorRecord`

Binds at least:

- target-monitor role;
- parent-domain digest;
- `OnlineTargetMonitorPolicy` digest;
- requested and realized sizes;
- exact ordered selected identities/source indices;
- per-stratum available/selected counts;
- strategy and seed;
- label-domain identity;
- explicit fallback reason where applicable.

### `ReplayMonitorRecord`

Binds at least:

- replay-monitor role;
- replay source/label lineage;
- `ReplayMonitorPolicy` digest;
- requested and realized sizes;
- exact ordered selected identities/source indices;
- strategy/seed fields owned by the replay policy;
- true-label mode where required;
- materialized artifact digest where applicable;
- explicit fallback reason where applicable.

`TrainingProtocolIdentity` binds the exact monitor record/policy identities it uses. It does not infer them from filenames.

## 5. Leakage and independence invariants

- Monitoring configurations never contribute gradients.
- The common target monitor is development/model-selection evidence, not held-out CV evidence.
- Held-out CV evaluation and locked tests cannot be promoted into online-monitor roles.
- Target-training geometries may not overlap true-label replay-monitor evidence where the current replay contract forbids such overlap.
- Membership is selected once per compatible campaign identity and reused; it is not redrawn per epoch, fold, seed, or target-size candidate.
- The monitor seed is policy identity, not an informal hint.
- A monitor cardinality is never interpreted as `N_selected`.

## 6. Relationship to target-size study

The target-size reducer may consume the common target and replay monitors as authorized development/model-selection evidence.

The target-size study does not own their construction and cannot change their membership between size candidates. Every size candidate/seed sees the same monitor identities so comparison is paired with respect to evaluation evidence.

The target-size ladder remains the fixed population owned by `mlff_target_subset_size_study_spec.md`; monitor sizes 256 and 512 are semantically independent.

## 7. Precision and accumulation boundary

Monitor inference uses the learned model precision/backend declared by `TrainingProtocolIdentity`. mdstats-owned metric accumulation remains under the current numerical-precision specification and is not weakened by model dtype.

Changing model precision/backend creates a different training/runtime protocol identity where the current architecture declares it protocol-defining.

## 8. Persistence and unsupported historical records

Current monitor artifacts are accepted only when their current schema, content, parent lineage, and policy digests validate.

Obsolete monitor/campaign schemas do not gain current meaning through compatibility aliases. A campaign whose monitor records cannot validate under the current generation requires re-preparation.

## 9. Acceptance requirements

Current monitor qualification covers at least:

1. deterministic target/replay membership regeneration;
2. exact requested defaults and explicit short-parent fallback;
3. common target-monitor identity across compatible fold/final/seed jobs;
4. condition/run/time distribution rather than first-N truncation;
5. true-label replay enforcement where required and exact artifact round-trip;
6. forbidden-role/geometry-overlap checks;
7. protocol identity binding;
8. corruption/staleness rejection;
9. proof that monitor cardinalities are not consumed as target-size authority.
