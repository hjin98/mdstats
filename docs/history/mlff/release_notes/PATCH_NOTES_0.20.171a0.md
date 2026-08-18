# mdstats 0.20.171a0 patch notes

## Gate

`EVAL2` - target-first static checkpoint-trajectory evaluation and uncertainty-aware ranking.

## Implemented

- Added immutable EVAL2 target-role, evaluation-plan, trajectory-point, detailed target-metric, checkpoint, paired-bootstrap, and run-selection records. Historical `CheckpointEvaluationRecord` / MLCV-ADAPT ranking semantics remain unchanged; the persistent prediction cache is reused only as the authenticated inference substrate.
- Freeze leakage-safe target evidence. CV runs rank on their frozen internal checkpoint-monitor units. Target-size/final-development runs use one common TARGET-DATA2A development-only complement equal to the authorized development pool minus the largest Stage-A training rung; the historical outer monitor has zero checkpoint-ranking or target-size authority.
- Reconstruct the development complement exactly from frozen CV evaluation shards, preserving requested frame order and authenticating source artifacts, target-role identity, and correlation-block IDs before cache reuse.
- Implement the target-only `3 best overall + 2 best refinement-phase` initial full-evaluation shortlist, at most five unique checkpoints. Lightweight replay cannot enter shortlist ordering.
- Reduce full target evidence into global force RMSE, per-species RMSE, species-macro RMSE, P90/P95/P99 force-error tails, applicable condition/stratum and focus/nonfocus-group RMSEs, energy/atom, composition-centered relative-energy RMSE, and stress metrics where labels exist.
- Define relative-energy error without cross-composition offsets: within each exact atomic-composition group containing at least two configurations, center signed per-atom energy errors by that group's mean and pool the centered residual RMSE. Singleton composition groups are non-applicable.
- Apply TRUE_DFT replay only as the foundation-relative hard admissibility constraint after full checkpoint evaluation. Replay has zero positive/negative ranking or tie-break credit among admissible checkpoints.
- Add deterministic bounded target-ranked rescue. The generated default `eval2_candidate_rescue_cap = 5` allows at most five additional full evaluations after the initial five, for at most ten full checkpoint evaluations per run.
- Implement practical/statistical indistinguishability: <=1 meV/A target-score difference is a deterministic practical tie; larger differences use a paired correlation-block bootstrap only when at least 10 independent blocks exist (2000 replicates, 95% percentile CI, deterministic seed from the evaluation-plan digest). A material winner requires both the raw >1 meV/A point improvement and the CI to favor the same candidate.
- Implement target-only lexicographic tie handling: worst applicable stratum RMSE -> species-macro RMSE -> P95 -> P99 -> later/lower-LR refinement maturity -> stable identity. Replay cannot re-enter this ordering.
- Correct TARGET-DATA2D Stage-B eligibility to the approved 10-of-30 policy: only numerical/operational failure removes a candidate at epoch 10. Final target qualification thresholds and replay ceilings are diagnostic-only at Stage B.
- Wire TRAIN2 `evaluate` directly to EVAL2. Stage B evaluates the exact epoch-10 endpoint and can advance the target-size funnel. Stage C evaluates the authenticated 30-epoch trajectory and freezes static checkpoint selection evidence but does not finalize target-size selection until later physical VERIFY evidence exists.

## Intentionally deferred

- DEPLOY/PES/RELAX/DYN physical qualification of EVAL2 static finalists.
- TARGET-DATA2D Stage-C physical pass/fail completion, TARGET-DATA2E production-corpus materialization from the final Stage-C winner, and SELECT2 production publication.

## Qualification

- 274 passed, 2 expected skips across EVAL2/TRAIN2, TARGET-DATA2A-E, FOUNDATION-AUDIT1, DATA5/DATA6/DATA8/DATA9, campaign CLI/performance, checkpoint materialization, historical evaluation pipelines, and TRUE_DFT replay/evaluation regressions.
- Expected skips: the campaign integration requiring an external real LTA training root and the real-MACE evaluation smoke requiring its external supplied MACE package.
- Python `compileall` passed and the public import reports `mdstats 0.20.171a0` with `mdstats.eval2-run-record.v1` exported.
- Canonical architecture PDF regenerated from 127 to 128 pages. Final full low-DPI render comparison completed successfully; EVAL2 pages 121-122 were re-rendered at 140 DPI and visually inspected with no clipping, overlap, or broken equations/glyphs.
- Older specification files that exact-pin package version `0.20.140a0` remain known historical test debt and are not used as EVAL2 qualification evidence.
