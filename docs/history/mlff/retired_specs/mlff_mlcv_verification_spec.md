# MLCV-VERIFY1 physical verification and locked-test specification

## Status

Implemented in `mdstats 0.20.138a0`.

## Purpose

MLCV-VERIFY1 converts MLCV-FINAL1 statistical authority into one physically verified, post-freeze-tested production model without allowing fold models or locked-test evidence to become new model selectors.

## Physical-verification authority

Only qualified FINAL1 full-development representatives are eligible. Candidates are visited in the deterministic FINAL1 order. When the MLCV final-seed fallback option is enabled (the generated default), a bounded-NVE failure may advance to the next already-qualified final seed. When disabled, only the FINAL1 best seed is tested. The TOML key is shown in the campaign template. Fold representatives are never eligible; fold models can never enter this path.

The verification policy freezes learned-model dtype, physical stability thresholds, the locked-E target ceiling, and the retained checkpoint safety-metric policy. Each physical case is content-addressed by model bytes, structure bytes, temperature, integration settings, seed, precision, and acceleration identity.

The first candidate that passes the complete configured structure × temperature matrix is frozen. Physical fallback ends permanently at that point.

## Locked test E

Locked target test `E` remains unmaterialized during training, checkpoint selection, CV aggregation, FINAL1 comparison, and physical fallback. Only after one physical passer is frozen may MLCV-VERIFY1 materialize `E` from the sealed DATA8 frame identity.

`E` is evaluated exactly as post-freeze target evidence on the byte-identical frozen FINAL1 target-head model. Replay data do not enter this gate. The locked test applies the configured target force-RMSE ceiling and retained target safety gates. Its evidence declares `evaluation_count = 1` and `fallback_permitted = false`.

A locked-E failure is campaign failure/scientific-review evidence. The code must not test another seed, checkpoint, or fold model on `E` under the same campaign identity.

## Production publication

`models/production_best.model` is atomically published only after both:

1. the candidate passes bounded physical verification; and
2. that same frozen model passes locked `E`.

The published SHA-256 must equal the frozen FINAL1 committee-model SHA-256. The qualified FINAL1 committee remains a separate active-learning artifact and is not rewritten by VERIFY1.

## Restart rules

Completed physical-case evidence is content-addressed and reusable. A completed immutable physical-verification record is not re-ranked. A completed locked-E failure is terminal for the campaign; rerunning `verify` cannot reinterpret it or invoke fallback. A completed production record must authenticate the published model bytes before reuse.

## Gate closure

MLCV-VERIFY1 closes only when tests prove that physical fallback cannot escape qualified final seeds, the first physical passer is frozen, locked E cannot authorize fallback/reselection, publication requires locked-E success, byte/dtype identity is preserved, and historical ADAPT-VERIFY1 behavior remains readable for pre-MLCV campaigns.
