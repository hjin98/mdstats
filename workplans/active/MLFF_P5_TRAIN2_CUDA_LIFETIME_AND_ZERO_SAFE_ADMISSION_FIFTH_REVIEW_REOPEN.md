---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION-REVIEW-REOPEN-5
parent_workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION
predecessor_review_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION-REVIEW-REOPEN-4
protocol_version: 6.1.0
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: d8373470bc9fa8c4d6a445fd62e6156e44e9158c
highest_affected_domain: D4 evidence/closeout under coherent cycle-scoped D3 TRAIN2 resource architecture
serious_challenge: none
precedence: This review supersedes only the fourth-review implementation disposition. It accepts B5 and the retained B1-B3/restart repairs, preserves every non-conflicting parent/third/fourth-review invariant and D3 decision, and keeps the work open only for terminal R5-B evidence plus the already-required independent D3 authority falsification gate.
---

# P5 TRAIN2 CUDA repair — fifth implementation Review reopen

## 0. Review disposition

Candidate `d8373470bc9fa8c4d6a445fd62e6156e44e9158c` is **NO-PASS / REOPENED**, but no further scheduler/configuration implementation defect was found in this review.

The fourth-review B5 configuration-surface defect is closed: `_post_selection_training_concurrency_policy()` again resolves `parallel_training_jobs`, `minimum_parallel_training_jobs`, and `maximum_parallel_training_jobs` directly from the canonical campaign execution configuration, and the temporary `MDSTATS_PARALLEL_TRAINING_JOBS` / `MDSTATS_MAXIMUM_PARALLEL_TRAINING_JOBS` production paths and their dedicated test are deleted.

The previously accepted B1-B3 orchestration repairs and the post-selection MACE restart seam remain conforming in the reviewed delta. The implementation-supplied final affected matrix reports 166/166 passing tests after the B5 deletion. No GitHub Python CI/status realization exists for this commit, so those results remain implementation-supplied evidence rather than an independently executed review result.

One task-specific evidence blocker remains: the new R5-B record still does not reach the frozen terminal TRAIN2 outcome. The independent D3 Architecture Manual falsification gate also remains open and cannot be self-satisfied by this review context.

No Serious Challenge is active. Do not change D1/D2 scientific or numerical method semantics.

## 1. Accepted B5 closure

Preserve the current direct configuration resolution. Do not reintroduce an environment, CLI, helper, or second configuration surface merely to cap evidence concurrency. The existing `[execution] parallel_training_jobs = 1` setting is sufficient for the target-host single-job realization.

The reviewed semantic delta from the fourth-review commit is reduction-oriented: the two environment-variable branches and their test are removed. This is consistent with the parent architecture and Protocol 6.1 configuration/simplicity doctrine.

## 2. Remaining blocker B4 — R5-B is still partial progress, not terminal TRAIN2 evidence

### Finding

The fourth-review contract requires the exact single-job target-host realization to reach **natural authenticated TRAIN2 completion or a genuine resource terminal outcome**. The current record identifies a frozen CV horizon of 20 epochs but records only:

- natural completion of epoch 0 at 5,185 updates;
- natural completion of epoch 1 at 10,370 cumulative updates;
- authenticated per-epoch checkpoint/runtime artifacts;
- flat approximately 6.29 GiB worker VRAM residency and approximately 7.16 GiB aggregate high-water;
- clean teardown and no orphan workers.

This is strong evidence that the original epoch-0 OOM was not intrinsic to an isolated current-method job and that the job can execute well beyond the historical 2,411-update failure point. It does **not** establish a terminal TRAIN2 summary for the frozen plan. An authenticated epoch checkpoint is durable partial/restart state; it is not the authenticated completed TRAIN2 summary that ends TRAIN scheduler ownership.

The record also does not identify a genuine memory-safety/OOM/observability terminal failure. Therefore the explicit fourth-review terminal-outcome condition remains unsatisfied.

### Required repair/evidence

Do not change product code solely for this blocker and do not restart the characterization from scratch merely for ceremony. Reuse the already-authenticated epoch-1 checkpoint through the repaired ordinary MACE continuation seam, preserving the exact same frozen runtime/method identity and canonical one-job execution cap.

Continue the same exact R5-B TRAIN2 job until its own accepted terminal condition under the frozen runtime plan:

- normally the planned CV TRAIN2 horizon, unless an already-authorized method terminal condition legitimately ends it earlier;
- or a genuine resource-safety/OOM/observability terminal failure.

For successful completion, record at minimum:

1. the resumed source checkpoint/runtime-summary identity and unchanged frozen runtime-plan / optimizer-policy identity;
2. canonical `execution.parallel_training_jobs = 1` admission and a clean/admissible baseline for the resumed execution;
3. the final authenticated TRAIN2 summary showing terminal completed epochs/updates for the governing runtime plan, not merely another per-epoch checkpoint;
4. aggregate VRAM high-water over the resumed/remaining phases and process-local high-water where already available;
5. no model-scale parent/preflight residue and no orphan accelerator worker after terminal cleanup;
6. ordinary continuation/currentness evidence proving a later invocation recognizes the completed TRAIN2 summary and does not retrain that slot before proceeding to EVAL2.

If the remaining epochs expose intrinsic over-envelope behavior or OOM, stop D4 closure and route method/device compatibility to D3/D2 exactly as the parent workplan requires. Do not alter batch size, precision, CuEq/backend, replay exposure, optimizer semantics, membership, folds, horizons, or model architecture as a workaround.

## 3. Retained implementation and regression obligations

No new executable repair is requested. Preserve:

- zero-safe RAM/VRAM admission with no one-job floor;
- current aggregate-memory admission and live safety semantics;
- bounded transient/missing-observation behavior;
- CPU serial replacement across monitor observations;
- truthful complete-done-batch accounting before failure propagation;
- TRAIN scheduler ownership ending at authenticated TRAIN2 summary;
- fail-before-EVAL2 whole-wave semantics;
- explicit provider/model cleanup boundaries;
- the repaired `--restart_latest` plus `MDSTATS_MACE_RESTART_EPOCH = start_epoch - 1` continuation handshake;
- canonical campaign configuration as the only concurrency policy surface;
- unchanged D1/D2 scientific/numerical identity.

Because no further product-code change is required for B4, the implementation-supplied 166/166 affected regression on `d837347...` remains applicable unless another executable edit is made. If product code changes again, rerun the complete affected surface on the new semantic candidate before closure.

## 4. Independent D3 authority gate remains open

The durable Architecture Manual resource-semantics proposal still requires a genuinely independent reviewer/context that did not author or refine that proposal. This review context participated in that work and therefore cannot satisfy the independence requirement.

The independent falsification pass must challenge at least zero-safe admission, `training_gpu_memory_fraction` as the live TRAIN2 envelope, transient/missing-observation semantics, whole-wave cancellation, fail-before-EVAL2 phase separation, CPU serial preservation, and absence of D1/D2 method changes.

No new D4 machinery is required for this gate.

## 5. Final PASS criteria

PASS requires all of the following on the final semantic candidate/evidence state:

1. B1-B3, B5, and the restart-seam correction remain conforming.
2. R5-B reaches a genuine terminal TRAIN2 outcome under the exact single-job frozen method and records the terminal authenticated summary or genuine resource failure.
3. Successful R5-B completion is reusable/current without retraining before EVAL2.
4. No D1/D2 scientific/numerical method meaning changes.
5. No later executable mutation invalidates the current affected-regression evidence; otherwise rerun the complete affected surface.
6. The independent D3 falsification pass accepts the proposed durable Architecture Manual resource semantics.
7. Only after the above close may the parent and review-reopen artifacts be closed/archived.

Until then the overall workplan remains **NO-PASS**. No Serious Challenge is active.
