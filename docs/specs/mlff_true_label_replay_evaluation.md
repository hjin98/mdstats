# MLFF independent true-label replay evaluation specification

## Status

Implemented in mdstats 0.20.85a0.

## Problem

A replay corpus may be labelled by the frozen foundation model so it can regularize multi-head fine-tuning. Those pseudolabels encode the foundation prediction, not an independent reference. They are appropriate training targets and behavioral-drift diagnostics, but they cannot establish foundation or candidate accuracy. Checkpoint evaluation therefore needs a separate path to the original true DFT labels while preserving the exact replay geometry split used by DATA8.

## Configuration contract

`[paths].replay_train` and `[paths].replay_monitor` identify the replay split used by the training protocol. `[paths].replay_true_labels` optionally identifies an independent true-label directory.

Accepted true-label directory layouts are:

1. `true_labels/replay_train.extxyz` and `true_labels/replay_monitor.extxyz`;
2. `replay_true_train.extxyz` and `replay_true_monitor.extxyz`;
3. `true_replay_train.extxyz` and `true_replay_monitor.extxyz`; or
4. an original `mp_replay_selected.extxyz` (also accepting `replay_true_source.extxyz` or `true_labels.extxyz`) from which the configured split is reconstructed.

The default `[replay].mode = "external_pseudolabel"` is unchanged. This mode controls training labels only. `external_true_label` selects the resolved true-label train and monitor files for training.

A legacy TOML without `[paths].replay_true_labels` remains valid and preserves pseudo-label-only diagnostic evaluation.

## Split reconstruction

When an original true-label source is supplied:

- the configured replay train/monitor files define geometry and order;
- `replay_source_index` maps each split frame to the original source frame;
- exact geometry, species, periodicity, cell, and Cartesian positions are verified;
- duplicate source use, invalid indices, missing/non-finite labels, and incompatible tensor dimensions fail closed;
- source energy, forces, and optional stress replace all pseudo-label reference fields;
- pseudo-label model provenance is removed and true-label source/split hashes are recorded;
- the output is re-inspected as a `ReplayFileArtifact` with `label_mode = true_dft`;
- output geometry identities must equal the configured split identities in the same order.

Materialized files are cached under the campaign internal directory with a sidecar binding source SHA-256, split SHA-256, output SHA-256, and output artifact digest.

## Evaluation matrix

For each candidate checkpoint, evaluation stores complete metrics for:

| model | LTA target monitor | replay monitor |
|---|---:|---:|
| frozen foundation | required when `evaluate_foundation_on_target = true` | required for replay runs |
| fine-tuned candidate | required | required for replay runs |

Each dataset metric record contains configuration count, energy MAE per atom, global force-component RMSE, per-mobile-species force RMSE, stress RMSE, worst-condition force RMSE, condition-resolved force RMSE, and combined loss.

The candidate target record remains the source of checkpoint admissibility and primary ranking. True-label replay can apply the configured relative retention gate. Pseudo-label replay remains an absolute disagreement diagnostic and cannot become an accuracy gate.

## Dual lineage

The campaign run remains bound to the original DATA8 replay artifact used for training. An evaluation-only override is accepted only when it:

- carries `true_dft` provenance;
- has the same configuration count;
- has exactly the same ordered geometry identities as the DATA8 replay monitor.

The checkpoint evaluation record is separately bound to the true-label replay artifact digest and byte hash. Thus changing labels invalidates evaluation without mutating or rebuilding the training plan.

## Cache invalidation and restart

A cached checkpoint evaluation is reusable only when all of the following match:

- run-plan digest;
- checkpoint SHA-256;
- evaluation-policy digest;
- target artifact digest and SHA-256;
- actual replay-evaluation artifact digest and SHA-256;
- candidate and foundation model hashes;
- complete foundation/candidate metric matrix.

Any mismatch deletes the stale record before recomputation.

If an earlier completed evaluation pruned unselected checkpoints, a true-label refresh evaluates all still-authenticated shortlisted checkpoint bytes and adds the previously selected retained checkpoint if necessary. Missing deleted checkpoints are counted and reported. If no authenticated checkpoint remains, evaluation fails with a recovery instruction rather than manufacturing evidence.
