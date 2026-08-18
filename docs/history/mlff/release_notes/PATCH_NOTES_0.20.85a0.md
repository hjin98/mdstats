# mdstats 0.20.85a0 — independent true-label replay evaluation

## Purpose

Replay pseudolabels remain useful for multi-head regularization, but they are not independent accuracy references. This release separates the replay corpus used by training from the replay labels used by checkpoint evaluation.

## Configuration

`campaign.toml` now accepts:

```toml
[paths]
replay_train = "/path/to/replay_train.extxyz"
replay_monitor = "/path/to/replay_monitor.extxyz"
replay_true_labels = "/path/to/LTA_replay"

[replay]
mode = "external_pseudolabel"
```

The default training mode remains `external_pseudolabel`. The new directory may contain either already split true-label train/monitor files or the original `mp_replay_selected.extxyz`. For the latter layout, mdstats reconstructs the exact split using `replay_source_index`, verifies geometry and ordering, and caches authenticated true-label ExtXYZ files.

Change `[replay].mode` to `external_true_label` only when training itself should use true labels.

## Evaluation behavior

- Candidate and foundation models are evaluated on the DFT-labeled LTA target monitor.
- Replay runs evaluate both models on the independent true-label replay monitor when configured.
- Full per-dataset metrics are stored for the foundation/candidate × target/replay matrix.
- Training lineage remains bound to the original DATA8 replay artifact; the evaluation record is separately bound to the actual true-label artifact and its SHA-256.
- Pseudo-label-only campaigns remain backward compatible and retain diagnostic disagreement semantics.

## Restart and stale records

Adding or changing `replay_true_labels`, changing the foundation model, or changing the evaluation policy invalidates cached checkpoint evaluations automatically. Stale records are deleted and recomputed.

Completed campaigns may already have pruned unselected optimizer checkpoints. In that case mdstats refreshes every still-authenticated shortlisted checkpoint and always includes the previously selected retained checkpoint. The result records the reduced refresh scope; deleted checkpoint bytes are never implied to have been re-evaluated.

No DATA preparation, replay pseudolabel generation, or model retraining is required when the retained checkpoint bytes and true replay source are available.
