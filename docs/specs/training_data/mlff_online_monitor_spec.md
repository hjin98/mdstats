# MLFF ADAPT-MON1 fixed common online monitor specification

Status: implemented in mdstats 0.20.123a0

## 1. Scope

ADAPT-MON1 replaces variable fold-local checkpoint-monitor inputs in newly prepared MLFF
campaigns with two immutable, campaign-common online validation artifacts. It changes monitor
construction and lineage only. It does **not** implement adaptive stopping, lightweight finalist
ranking, or retirement of EVAL-MF; those remain later gates.

The online monitors are model-selection evidence only and must never supply gradients.

## 2. Canonical policy

`OnlineMonitorPolicy` uses schema `mdstats.online-monitor-policy.v1` and defaults to:

- target budget: **256 configurations**;
- replay budget: **512 configurations**;
- deterministic monitor seed: **161803**;
- target strategy: `balanced_condition_run_time_systematic`;
- replay strategy: `chemistry_size_systematic`.

Changing any policy field changes the policy digest and therefore the materialization/protocol
identity.

## 3. Common target monitor

The target parent domain is DATA5 `outer_monitor` evidence only. Fold-local training,
fold-local validation, and locked/held-out test roles are not eligible parents.

The selector:

1. groups eligible units by declared condition and run identity;
2. distributes the requested budget as evenly as possible across those strata;
3. orders frames by source trajectory/time within each stratum;
4. uses a deterministic random-start systematic sample to spread selections across time; and
5. records exact ordered configuration identities, source-frame indices, stratum counts,
   requested/realized size, seed, strategy, parent digest, and true-label domain.

Every fold, seed, training method, and final-development job prepared under the same label domain
receives the **same target monitor membership and artifact content digest**. This is required so
online errors are directly comparable across competing runs.

If fewer than 256 eligible configurations exist, all eligible configurations are used and the
fallback is explicitly recorded.

## 4. Independent true-label replay monitor

The replay parent must be a `ReplayFileArtifact` with `ReplayLabelMode.TRUE_DFT`. Foundation
pseudo labels may remain replay **training** data, but they cannot define the absolute online
replay validation metric.

Replay selection uses a stable ordering over exact composition/chemistry, atom count/size bin,
and source order followed by deterministic systematic sampling. The selected 512-frame default
subset is materialized at:

`shared/replay/online_true_replay_monitor.xyz`

The materialized artifact is immediately re-inspected. Geometry identity, ordered membership,
label identity, and true-label mode must match the parent selection exactly or preparation fails.
If fewer than 512 true-label configurations exist, all available configurations are used and the
fallback is recorded.

For multi-head replay jobs:

- MACE `pt_train_file` remains the configured replay training artifact; and
- MACE `pt_valid_file` is the fixed true-label online replay monitor.

Thus validation evidence is independent of the gradient-label mode.

## 5. Identity contracts

`OnlineMonitorRecord` uses schema `mdstats.online-monitor-record.v1`. A record binds:

- role (`target` or `replay`);
- parent-domain digest;
- policy digest;
- requested and realized sizes;
- exact ordered selected identities;
- source indices;
- per-stratum available/selected counts;
- strategy and seed;
- label mode and parent role; and
- explicit fallback reason codes.

New DATA8 preparation uses `mdstats.data8-preparation-bundle.v2`. New production materialization
uses `mdstats.production-materialization-plan.v4`. New training protocol identities use
`mdstats.training-protocol-identity.v4` when online-monitor evidence is present. The protocol
binds the policy digest, target-record digest, replay-record digest, and materialized replay-valid
artifact digest as one quartet.

Historical DATA8/production-plan/protocol schemas remain readable. Low-level callers that do not
request ADAPT-MON1 retain legacy construction semantics for compatibility, while new campaign CLI
preparation always binds the new monitor policy and requires independent true replay labels.

## 6. Leakage and role invariants

- Online monitor configurations never contribute gradients.
- Target monitor selection is restricted to the common DATA5 outer-monitor domain.
- Locked/sealed test evidence cannot be promoted into the online monitor role.
- Target-training geometries may not overlap the true-label replay online monitor by exact
  geometry identity.
- Monitor membership is selected once and reused; it is not redrawn per epoch, fold, or seed.
- The monitor seed is identity, not an informal reproducibility hint.

## 7. Precision boundary

ADAPT-PREC1 remains authoritative. `single` jobs evaluate these monitors with the FP32 learned
model; `double` jobs use the FP64 learned model. mdstats-owned SSE/RMSE/statistical accumulation
remains hard-coded FP64 under either model precision.

## 8. Current runtime boundary

ADAPT-MON1 itself freezes the common validation artifacts. Beginning in 0.20.124a0, ADAPT-STOP1
consumes their already-paid force-RMSE rows at every evaluated epoch and can terminate training at
the target-success, replay-exhaustion, or hard-epoch boundary without additional monitor
inference. ADAPT-EVAL1 has not yet retired the existing mixed-fidelity evaluation stage.

## 9. Acceptance tests

The gate requires regression coverage for:

1. deterministic target and replay membership regeneration;
2. exact 256/512 defaults and explicit small-parent fallbacks;
3. common target membership across every fold/final job;
4. target condition/run/time coverage rather than first-N selection;
5. TRUE_DFT replay enforcement and exact label/geometry round-trip;
6. no target-training/replay-monitor geometry overlap;
7. MACE `pt_valid_file` separation from replay training data;
8. protocol/digest serialization and corruption rejection; and
9. historical schema readability.
