# mdstats 0.20.170a0 patch notes

## Gate

`TRAIN2B` - executable fixed-budget training plus exact deterministic low-LR refinement and 10-of-30 continuation.

## Implemented

- Added the dedicated TRAIN2B runtime path for new-policy campaigns while preserving historical adaptive-stop execution unchanged.
- Apply the frozen `LearningRateSchedulePolicy` immediately before every optimizer update over one planned 30-epoch update horizon. Native MACE validation-driven LR scheduler mutation is bypassed and patience cannot terminate a numerically valid TRAIN2 run.
- Implement TARGET-DATA2D Stage B as a durable successful pause after 10 completed epochs on the original 30-epoch trajectory, not as an independent 10-epoch training schedule.
- Added authenticated Stage-C continuation state carrying live non-EMA model parameters, EMA shadow state, Python/NumPy/Torch CPU/CUDA RNG state, base-LR identity, raw MACE checkpoint identity, update geometry, and structure-presentation geometry. The raw MACE checkpoint remains the optimizer-state carrier and is SHA-bound by the companion record.
- Persist `train2_runtime.json`, latest-only `train2_runtime.pt`, and append-only `train2_history.jsonl` evidence with completed/planned epochs, optimizer updates, structures presented, normalized progress, LR phase, instantaneous LR, checkpoint/optimizer-state identities, and available training/validation diagnostics.
- Inject the DATA8-authenticated TRUE_DFT replay monitor as the distinct `train2_true_replay` validation stream for replay-enabled TRAIN2 jobs. It is diagnostics-only and cannot stop training, mutate LR, or receive checkpoint-ranking authority.
- Make campaign execution target-size-stage aware: Stage-A survivors run the one screening seed to 10-of-30; Stage-B finalists reopen those successful executions with `--restart_latest` and continue to 30; after size selection only the selected-size `2 x (3 CV + 1 final)` production matrix is required for completion.
- Require one fixed FP32 or FP64 precision stage for TRAIN2B v1. Retired staged `refine`/`mixed` precision schedules fail closed rather than competing for checkpoint/restart authority.
- Snapshot pre-existing model artifacts before launching a continuation child so a Stage-B artifact cannot be mistaken for newly completed Stage-C work.
- Synchronize `campaign.toml.example` with the current TRAIN2-generated policy (`policy_generation="train2"`, `checkpoint_strategy="train2_target_first"`, foundation-relative replay budget, deterministic LR controls).

## Intentionally deferred

- EVAL2 target-first checkpoint-trajectory shortlist/full evaluation, paired block-bootstrap comparison, and checkpoint selection.
- DEPLOY/PES/RELAX/DYN physical qualification and SELECT2 final production publication.

## Qualification

- 238 passed, 1 expected skip across TRAIN2A/B, TARGET-DATA2A-E, FOUNDATION-AUDIT1, DATA5/DATA6/DATA8, campaign execution/materialization, and historical MLCV runtime regressions.
- One obsolete historical MLCV migration assertion was deliberately deselected because it requires newly generated configs/examples to remain `mlcv_nested_cv`; TRAIN2A intentionally changed the new-generation default to `train2_target_first`. Historical config execution tests remain passing.
- The expected skip is the existing integration test requiring an external real LTA training root.
- Python compileall passed.
- Canonical architecture PDF regenerated from 126 to 127 pages. Final render comparison changed 15 expected TOC/roadmap/TRAIN2/EVAL2/downstream pages; inspected TRAIN2 pages 118-121 render without clipping or broken equations/glyphs.
- Older specification files that pin the package version to `0.20.140a0` remain known historical test debt and are not used as TRAIN2B qualification evidence.
