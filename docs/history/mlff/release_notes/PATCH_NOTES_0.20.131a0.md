# mdstats 0.20.131a0 — MLCV-ROLE1

This release implements the first gate of the conventional cross-validation correction roadmap recorded in 0.20.130a0. It deliberately freezes **statistical authority and lineage only**. The later MLCV gates will change monitor construction, adaptive stopping semantics, run-local top-five ranking, full checkpoint selection, CV aggregation, final-model competition, and verification/export behavior.

## Implemented

- Added `mdstats.mlcv-role-catalog.v1` and typed target/replay statistical roles.
- Fold roles are derived directly from the passing DATA5 cross-validation plan: gradient training, nested checkpoint selection, untouched outer CV evaluation, and purge units remain disjoint.
- DATA5 `outer_monitor` is frozen as final model-selection validation `D`; `locked_interpolation_test` is frozen as locked post-selection test `E`.
- Role lineage is bound to the DATA5 bundle, partition policy, partition-unit catalog, outer partition, and cross-validation plan digests. Production splitting therefore remains under correlation-aware DATA5 partition-unit authority rather than frame-wise shuffling.
- Replay-gradient and replay-validation evidence are separate typed roles. Any attached authoritative replay-validation artifact must use `TRUE_DFT` labels and must be geometrically disjoint from replay-gradient training data.
- Checkpoint stop/rank/top-K APIs now accept an optional typed MLCV role guard for transition compatibility; passing an outer-CV or locked-test role fails closed. Historical ADAPT callers remain readable until the later migration gate makes role identity mandatory for the new lifecycle.
- DATA8 v4 embeds the MLCV role catalog and also writes `mlcv_role_catalog.json` beside preparation evidence. Historical DATA8 v1-v3 payloads remain readable.
- A regression sweep also exposed and fixes a pre-existing decorator-placement bug: the campaign-level evaluation command now owns the MACE/PyTorch warning-condensation scope, so setup warnings are condensed before configuration/evaluator initialization.

## Default campaign change

New `init` configurations now use three optimizer seeds rather than four:

```text
multi-head replay only
3 seeds x (3 CV folds + 1 final fit) = 12 training jobs
```

Naive/native target-only fine-tuning remains disabled by default but configurable. Existing TOML/campaign identities are never expanded, shrunk, or reinterpreted by this default change.

## Not changed yet

The completed ADAPT-MON1/STOP1/RANK1/EVAL1 behavior still controls actual monitor materialization and model selection. In particular, this release does **not** yet switch fold training to the new nested light/full monitor hierarchy. That begins at `MLCV-MON1`.
