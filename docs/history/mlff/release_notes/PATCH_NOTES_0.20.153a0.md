# mdstats 0.20.153a0 patch notes

## MLCV checkpoint mixed-buffer dtype hotfix

`MLCV-SELECT1` could reach a valid authenticated MACE checkpoint and then fail during model materialization with:

`Checkpoint model state does not carry one qualified floating dtype.`

The materializer incorrectly equated the learned-model execution dtype with uniform dtype across every floating tensor in the checkpoint `state_dict`. MACE defines model dtype from learned parameters, while a valid checkpoint/model can contain floating buffers/bookkeeping tensors in the other qualified precision. This is especially relevant to FP32 learned models that retain FP64 reference/accumulation buffers.

### Fix

- Direct checkpoint restoration no longer requires the complete floating state dictionary to be globally uniform before attempting reconstruction.
- Exact per-key shape and dtype compatibility with the completed-run architecture template remains mandatory, so no silent dtype conversion is introduced.
- The historical optional whole-model cast path remains available only when both checkpoint and template states are individually uniform and their dtypes differ.
- Legacy restart-export fallback resolves execution dtype from the checkpoint itself when it is uniform; for a qualified FP32/FP64 mixed-buffer state it uses the immutable DATA8 MACE `default_dtype` as the learned-model execution authority.
- Floating state containing unsupported precisions still fails closed.

Existing DATA8 bundles, checkpoints, hashes, monitor artifacts, and training evidence remain reusable. Rerun `mdstats-mlff-campaign evaluate`; no DATA8 regeneration or retraining is required.

### Qualification

Focused checkpoint/MLCV campaign coverage passes 116 tests with one external-LTA-root skip. The real MACE 0.3.16 checkpoint materialization suite passes all 11 tests, including exact energy/force/stress reconstruction and multihead target-head export.
