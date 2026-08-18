# mdstats 0.20.68a0 naïve/replay campaign identity fix

## Reported failure

Production `train` stopped while constructing the DATA9B campaign plan with:

```text
mdstats.training_data._common.TrainingDataInputError:
Training campaign run IDs must be unique.
```

The default comparison campaign contains two training modes (`naive_fine_tuning`
and `multihead_replay`) and two seeds. Each DATA8 variant contains one final job
and three fold jobs.

## Root cause

The campaign CLI correctly passed `require_replay=False` for a nominal naïve
variant, but `build_production_materialization_plan` retained the resolved replay
plan. DATA8 determines its `TrainingMode` from the bound replay plan, so the
nominal naïve job was emitted as `multihead_replay`. For each selection size and
seed, the naïve and replay bundles therefore generated the same four logical IDs:

```text
multihead_replay-n<size>-seed<seed>-fold-00
multihead_replay-n<size>-seed<seed>-fold-01
multihead_replay-n<size>-seed<seed>-fold-02
multihead_replay-n<size>-seed<seed>-final
```

The uniqueness gate was correct; the upstream DATA8 mode identity was wrong.

## Correction

- `require_replay=False` now replaces the incoming replay corpus with an explicit
  `ReplayPreparationPlan(mode=ReplayMode.NONE)` before the immutable production
  materialization plan is constructed.
- Corrected DATA8 jobs infer `TrainingMode.NAIVE_FINE_TUNING`, omit replay files
  and replay-head bindings, and retain their target-only protocol identity.
- Runtime DATA8 restoration checks that the variant label agrees with every job's
  mode, selection size, and optimizer seed.
- The successful one-epoch preflight record is bound to the exact sorted DATA8
  variant/bundle matrix; changing or repairing DATA8 automatically makes preflight
  stale until it is rerun.
- Duplicate campaign run-ID errors now identify the colliding run IDs and DATA8
  bundle prefixes.

## Migration

After installation, run ordinary `prepare` once. Do not use
`prepare --rebuild-catalog`.

The changed naïve production-plan digest creates a corrected DATA8 generation.
Existing DATA3-DATA7 records, shared DATA7 archives, normalized frame cache, and
the completed foundation descriptor/prediction sweep remain reusable. Replay
variants are unchanged and are verified/reused.

Then rerun `preflight` because the authorized preflight record was produced from
the old four-variant DATA8 matrix, followed by `train --dry-run` and `train`.

## Regression coverage

- replay-backed input plus `require_replay=False` yields an explicit replay-free
  production plan;
- materialized jobs are all `naive_fine_tuning` and have no replay-plan digest;
- stale naïve labels pointing at replay protocols fail with a migration message;
- two-mode campaign planning retains globally unique fold/final run IDs;
- promoted DATA8 runtime-root, preflight, and restart tests remain passing.
