# mdstats 0.20.154a0 patch notes

## MLCV-AGG1 target-only outer-fold evaluation

This maintenance release fixes a control-flow contradiction in conventional CV aggregation for multi-head replay runs.

`MLCV-SELECT1` already evaluates each retained checkpoint on the authoritative full target-selection domain and full TRUE_DFT replay domain and freezes the representative checkpoint plus replay metrics. `MLCV-AGG1` must then evaluate that frozen representative only on the sealed outer target fold. Its aggregation contract explicitly requires `replay_monitor_artifact_digest is None` and `replay_configuration_count == 0`, because replay is reused from SELECT1.

The generic checkpoint-preparation routine previously saw the run plan's training replay lineage and automatically required an evaluation replay monitor and foundation model even for AGG1. This caused:

```text
TrainingDataInputError: Replay evaluation requires an evaluation monitor and foundation baseline model.
```

### Fix

- Add explicit `allow_target_only_evaluation` runtime authorization to checkpoint preparation.
- Authorization is valid only with an explicit target-monitor override (the AGG1 sealed outer fold).
- Replay monitor/path/index inputs are rejected when target-only authorization is active.
- AGG1 opts into this authorization.
- Target-only evaluation records carry the audit note `evaluation_scope:authorized_target_only`.
- All ordinary replay-aware calls continue to require replay monitor + foundation baseline exactly as before.

### Compatibility

No retraining, DATA8 rebuild, SELECT1 rerun, or checkpoint conversion is required. Existing SELECT1 representative and full-replay evidence remain authoritative. Re-running `mdstats-mlff-campaign evaluate` resumes at AGG1 and computes only the missing outer-fold target evaluations.
