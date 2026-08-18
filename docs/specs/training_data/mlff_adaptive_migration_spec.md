# MLFF ADAPT-MIGRATE1 migration and compatibility closure specification

Status: implemented in `mdstats 0.20.128a0`.

## Purpose

ADAPT-MIGRATE1 closes the post-0.20.120 adaptive campaign revision without changing the
scientific policies established by ADAPT-PREC1 through ADAPT-VERIFY1. Its responsibility is to
make the new lifecycle authoritative, restart-safe, storage-safe, and compatible with historical
campaign evidence.

The gate does **not** delete or reinterpret historical EVAL-MF, staged-precision, committee, or
protocol-freeze evidence. It adds an explicit schema-neutral authority layer so generic lifecycle
code no longer guesses a scientific freeze type from a database key.

## Final adaptive production contract

New campaigns use the completed adaptive chain:

```text
binary model precision (single|double)
        -> fixed common 256 target / 512 true-replay monitors
        -> adaptive STOP1 training
        -> one RANK1 champion per run
        -> EVAL1 top-5 full evaluation with next-5 rescue
        -> VERIFY1 score-ordered bounded verification fallback
        -> one verified deployment model + frozen authority
```

The resolved defaults remain:

```toml
[training]
max_num_epochs = 30
online_target_monitor_configurations = 256
online_replay_monitor_configurations = 512
target_stop_fraction = 0.80
replay_stop_multiplier = 1.20

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030

[evaluation]
target_score_weight = 1.0
replay_score_weight = 1.0
finalist_count = 5
finalist_rescue_batch_size = 5
checkpoint_strategy = "adaptive_topk"
```

The replay ceiling remains derived from the target threshold and score weights unless a separately
versioned future policy explicitly changes that contract.

## Schema-neutral protocol-freeze authority

`ProtocolFreezeAuthorityRecord` is the generic lifecycle/storage authority adapter. It contains:

- authority kind: `historical_committee` or `adaptive_deployment`;
- campaign and production-qualification lineage;
- the original scientific freeze schema and digest;
- protected production-model SHA-256 identities;
- source freeze timestamp; and
- for adaptive deployment only, the learned-model inference dtype plus invariant FP64 scientific
  analysis dtype.

The adapter never replaces the original scientific freeze record. Historical
`ProtocolFreezeRecord` and adaptive `AdaptiveProtocolFreezeRecord` remain the authoritative
scientific evidence for their respective campaign generations.

Historical committee freezes predate the binary precision contract, so migration must not invent a
model dtype for them.

## 0.20.127 adaptive alias reconciliation

`0.20.127a0` stored the adaptive scientific freeze itself under both
`adaptive_protocol_freeze` and the generic `protocol_freeze` key. On the first verified adaptive
reconciliation under `>=0.20.128a0`, mdstats:

1. authenticates the complete EVAL1 -> VERIFY1 -> deployment -> adaptive-freeze lineage;
2. preserves `adaptive_protocol_freeze` unchanged;
3. replaces only the generic `protocol_freeze` alias with a
   `ProtocolFreezeAuthorityRecord` derived from that freeze;
4. preserves all historical evaluator/committee records; and
5. writes one immutable `AdaptiveMigrationRecord` plus `results/adaptive-migration.json`.

The operation is idempotent. A second reconciliation must reproduce the same migration identity.
A historical committee freeze and adaptive freeze claiming generic authority in the same campaign
is an ambiguity and fails closed.

## AdaptiveMigrationRecord

The migration closure record binds:

- campaign plan digest;
- authoritative ADAPT-EVAL1 digest;
- ADAPT-VERIFY1 digest;
- deployment-model digest;
- adaptive scientific-freeze digest;
- generic freeze-authority digest;
- learned-model inference dtype;
- invariant `float64` scientific-analysis dtype;
- preserved historical evaluator evidence keys; and
- the migration version.

The source adaptive freeze timestamp is reused as the closure timestamp so migration identity is
stable across exact restart/reconciliation.

## Evaluation migration boundary

Algorithm migration is determined from immutable campaign/run protocol identity, not from an
editable TOML string.

- A campaign whose run protocols contain ADAPT-STOP1 policy identity must use
  `checkpoint_strategy = "adaptive_topk"`.
- A historical/pre-adaptive campaign may continue to use its historical
  `bounded|exhaustive|multi_fidelity` evaluator.
- A historical campaign cannot be switched to `adaptive_topk` without preparing a new scientific
  campaign identity.
- An adaptive campaign cannot regain historical EVAL-MF authority by editing its TOML.

Once an adaptive deployment protocol is frozen, later `evaluate` invocations only authenticate and
reuse the frozen EVAL1 record. They do not create a second evaluation history under the same
campaign identity.

## Restart and stale-evidence rules

The migration layer preserves the restart guarantees of each implemented adaptive gate:

- STOP1 reuses fixed monitor membership and authenticated stop history;
- RANK1 is regenerated only from STOP1 + frozen checkpoint-catalog evidence;
- EVAL1 reuses authenticated completed full predictions and finalist decisions;
- VERIFY1 reuses authenticated completed bounded-NVE cases;
- a verified/frozen adaptive campaign reconciles its migration authority without rerunning model
  inference, training, or verification.

Missing, mismatched, or partially rewritten lineage fails closed. A stale authority adapter cannot
unlock storage or change selection.

## Historical readability

Historical evidence remains readable but cannot control a new adaptive campaign. This includes:

- EVAL-MF policy/round/evaluation records;
- bounded/exhaustive evaluator records;
- historical committee and committee-member records;
- historical `ProtocolFreezeRecord`;
- `single`, `double`, and retired `refine` precision-profile records; and
- staged-precision/restart evidence created by the campaign that originally owned it.

New `refine` production execution remains prohibited by ADAPT-PREC1.

## Storage contract

STOR1-STOR5 ownership/deletion boundaries are unchanged.

Consequential storage operations no longer treat mere presence of a `protocol_freeze` key as
authority. The payload must parse as a recognized historical/adaptive freeze or the new generic
authority record and must pass its digest/schema validation.

`storage report` remains read-only. It reads migration/freeze summary through a read-only SQLite
connection and reports:

- protocol-freeze authority kind/source; and
- preserved historical evaluator evidence keys.

Migration does not broaden cleanup authority. Retired EVAL-MF prediction shards, staged-precision
state, and other historical artifacts remain governed only by their existing STOR lifecycle and
capability-loss rules.

## Qualification requirements

The final adaptive revision is qualified only when the combined suite demonstrates:

1. binary `single|double` learned-model dtype propagation;
2. the frozen 256-target / 512-true-replay monitor identities and statistical-rationale evidence;
3. target-success, replay-exhaustion, max-epoch, and no-admissible STOP1 outcomes;
4. 1:1, 2:1, and 1:2 weight-derived replay ceilings;
5. run champions occurring before the final stopping epoch;
6. top-five full evaluation and next-five rescue;
7. exact restart/reuse during adaptive training and full finalist evaluation;
8. score-ordered VERIFY1 fallback and byte-identical publication of the first passing model;
9. historical EVAL-MF/refine/freeze readability without adaptive authority leakage;
10. schema-aware storage/report safety; and
11. idempotent 0.20.127 adaptive-freeze alias migration with no historical evidence deletion.

The release qualification record is
`release/mlff_adapt_migrate1_lifecycle_qualification.json`.
