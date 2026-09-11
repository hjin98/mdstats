---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION-REVIEW-REOPEN-4
parent_workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION
predecessor_review_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION-REVIEW-REOPEN-3
protocol_version: 6.1.0
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
baseline_commit: f49c965a276324d585866dc1c7509600b40fe12e
semantic_candidate: 90b9e77f73e75a79b8de632220fdfed37a6707f2
highest_affected_domain: D4 implementation under coherent cycle-scoped D3 TRAIN2 resource/orchestration architecture
serious_challenge: none
precedence: This review supersedes the third-review implementation disposition only. It accepts B1-B3 as repaired, preserves all non-conflicting parent/third-review D1/D2 invariants, D3 decisions, non-goals, real-owner boundaries, and independent-D3 closeout requirements, and keeps the work open only for B4/B5 and final candidate-bound closure.
---

# P5 TRAIN2 CUDA repair — fourth implementation Review reopen

## 0. Review disposition

Candidate `90b9e77f73e75a79b8de632220fdfed37a6707f2` is **NO-PASS / REOPENED**, narrowly. The three D4 orchestration blockers from the third review are now materially repaired at the existing shared owner, and the newly discovered post-selection MACE restart seam is corrected consistently with the existing target-size restart contract. No Serious Challenge is active and no D1/D2 scientific or numerical method change is warranted.

Two blockers remain before closure:

1. the recorded target-host R5-B realization still does not establish the frozen required terminal TRAIN2 outcome; and
2. candidate `90b9e77...` introduces two permanent environment-variable concurrency override paths solely to obtain the R5-B execution cap even though the existing canonical `execution.parallel_training_jobs` configuration already expresses that execution-only policy.

The repair remains reduction-oriented. Do not add another scheduler, monitor, resource registry, retry database, OOM parser, configuration layer, or scientific fallback.

## 1. Accepted repairs from the third review

### B1 — CPU serial replacement: PASS

`_execute_post_selection_pending_runs()` now interprets `decision.memory_safe` as an admission gate only when `concurrency_plan.gpu_memory_budget_bytes is not None`. CPU plans therefore keep `admission_blocked=False`, retain `maximum_jobs=1`, and can submit replacement slots after monitor observations.

The new real-owner regression drives multiple CPU TRAIN2 slots across monitor observations, proves maximum active CPU jobs remains one, reaches EVAL2/CV acceptance, and also exercises the shared final-production caller. Preserve this behavior.

### B2 — idle transient CUDA admission: PASS

When no future is active but pending work remains under a transient memory/observability block, the scheduler now sleeps on the existing `poll_interval` rather than tight-looping. Confirmed `target_jobs < 1` still raises the existing typed zero-admission failure. This is the requested direct control-flow reduction; no new monitor/timer subsystem was introduced.

The deterministic unsafe->safe, unsafe->unsafe, and missing->missing tests exercise the real P5 scheduler owner with resource observations substituted below that owner. Preserve this behavior.

### B3 — truthful same-poll completion classification: PASS

The scheduler now drains the complete current `done` set before surfacing the first failure. Successful futures are removed from `active`, counted, and retained in `trained_slots`; failed futures are removed and counted; only genuinely still-running futures remain for cancellation/reaping. EVAL2 remains forbidden after the failed TRAIN wave.

The new mixed success/failure test forces both futures to be done before scheduler classification and verifies `completed_jobs=1`, `failed_jobs=1`, `active_jobs=0`, `queued_jobs=0`, no EVAL2/current CV acceptance, and reuse of the completed TRAIN2 summary on the next healthy invocation. Preserve this behavior.

### Newly discovered MACE restart seam: accepted D4 reconciliation

`MacePostSelectionTrainer` now appends `--restart_latest` when `request.start_epoch > 0` and supplies the already-established `MDSTATS_MACE_RESTART_EPOCH = start_epoch - 1` contract. This matches the pre-existing target-size launcher/precision-runtime restart handshake rather than inventing a second restart mechanism. The R7 guard was extended to observe the argument/environment handoff. Preserve this correction and its fail-closed downstream validation.

## 2. Blocker B4 — R5-B still lacks the required terminal TRAIN2 outcome

### Finding

The third-review contract requires one exact current-method TRAIN2 job from a clean/admissible baseline and requires that realization to reach **natural TRAIN2 completion or a genuine resource-stop/OOM terminal outcome**. An arbitrary operator interrupt is explicitly insufficient.

The new implementation record materially improves the evidence identity:

- RTX 3090 / 24 GiB target host;
- exact N=512 LTA MPA-0 FP32 context;
- frozen `batch_size=2`, CuEq, precision/replay/optimizer unchanged;
- clean 0.9 GiB pre-recovery / 1.2 GiB admission baseline;
- exactly one admitted TRAIN2 job (`active_jobs=1`, `target_jobs=1`, `ceiling=1`);
- 60-second warmup and 12/12 calibration observations;
- approximately 7.4 GiB aggregate high-water with approximately 6.3 GiB worker residency and >14 GiB headroom to the 21.6 GiB envelope;
- clean device teardown and no orphan worker.

But the record does **not** state planned TRAIN2 completion, completed epochs/updates, publication of an authenticated completed TRAIN2 summary, a terminal resource stop/OOM, or continuation/currentness verification after such a terminal outcome. "Warmup completed" and "memory returned upon exit" do not establish why the process exited. Under Protocol 6.1 evidence semantics, absence of the required terminal observation cannot be inferred into a pass.

### Required end state

Perform or recover a snapshot-complete R5-B realization for the final semantic candidate that records:

- exactly one TRAIN2 job from a clean/admissible baseline;
- unchanged frozen method identity (`batch_size=2`, CuEq, precision, replay, optimizer, membership, folds/horizon);
- natural authenticated TRAIN2 completion **or** a genuine resource-stop/OOM terminal outcome;
- aggregate high-water and available process-local allocated/reserved high-water;
- no model-scale preflight residue and no orphan worker after terminal cleanup;
- when completion is successful, the authenticated TRAIN2 summary and ordinary continuation/currentness path are usable without retraining.

If the exact isolated job completes safely, close the method/device-fit concern. If it intrinsically OOMs or violates the accepted envelope, stop D4 closure and route the method/device compatibility question to D3/D2. Do not change batch size, precision, backend, replay exposure, optimizer semantics, or model architecture as an OOM workaround.

## 3. Blocker B5 — remove the unnecessary hidden concurrency environment override surface

### Finding

Candidate `90b9e77...` adds production reads of:

- `MDSTATS_PARALLEL_TRAINING_JOBS`; and
- `MDSTATS_MAXIMUM_PARALLEL_TRAINING_JOBS`.

These are resolved directly inside `_post_selection_training_concurrency_policy()` and can override the existing `[execution] parallel_training_jobs` / `maximum_parallel_training_jobs` configuration. The implementation record says they were added to permit execution-only concurrency bounding for R5-B without modifying configuration files.

This is not an accepted product requirement. The parent/third-review contract permits an execution-only cap of one for the evidence realization; it does not require a new permanent production configuration surface. The existing canonical `execution.parallel_training_jobs=1` already supplies the required cap and is explicitly non-scientific execution policy.

Keeping the environment paths would create a second, hidden policy-resolution surface in a function that previously resolved the existing campaign configuration. It is contrary to the active-simplicity requirement and the SSDP configuration rule that meaningful execution policy be recoverable from one canonical resolution path unless an environment override is deliberately supported, documented, normalized, and justified. Promoting/documenting these new variables would add more contract than the problem requires.

### Required repair

Delete the two new environment-variable override branches from `_post_selection_training_concurrency_policy()` and restore direct resolution from the existing campaign execution configuration. Delete the corresponding environment-override-only test.

For R5-B, use the existing `execution.parallel_training_jobs=1` field through the ordinary configuration path (a target-host evidence-specific config/copy is sufficient). Do not replace the removed environment variables with a CLI flag, new config key, helper layer, or another hidden override.

### Required evidence

After removal:

- the existing positive configured job-cap admission tests remain green;
- B1-B3 real-owner regressions remain green;
- the final affected P5/campaign regression remains green;
- structural inspection confirms no candidate production path retains the two new environment-variable names;
- R5-B evidence identifies the existing configuration field as the one-job execution cap.

## 4. Evidence applicability and final regression

Implementation-supplied evidence for candidate `90b9e77...` records:

- 20/20 in `tests/test_mlff_p5_train2_zero_safe_admission.py`;
- 19/19 in `tests/test_mlff_target_size_p5_r7_guards.py`;
- 130/130 combined affected regression across training scheduler, P5 zero-safe admission, P5 replay/MACE recovery, P5 R7-R9 guards, and downstream integration;
- 29/29 P5 R10 guards;
- 8/8 P5 R11 guards.

These results are supportive implementation evidence. The remote GitHub commit currently exposes no Python CI/status realization for `90b9e77...`, and this review runtime has no Serena or Semgrep executable/backend available. The review therefore used exact-revision GitHub source/diff inspection as the concrete fallback for symbol/structural reasoning and does not represent Serena/Semgrep or Python tests as independently executed here.

Removing B5 changes executable policy resolution, so rerun the complete affected surface on the final candidate. Preserve all still-applicable D1/D2 and prior target-host observations with explicit applicability reasoning; do not treat old green D4 tests as the final assembled realization after the edit.

Also reconcile the evidence references in the third-review implementation note: the recorded B1/B2 test names should match the actual final test symbols rather than stale draft names.

## 5. Independent D3 authority gate remains open

The durable Architecture Manual resource-semantics mutation still requires a genuinely independent falsification pass by a reviewer/context that did not author the D3 proposal. This conversation participated in authoring/refining that proposal and cannot self-satisfy the independence requirement.

That independent review must challenge at least:

- zero-safe TRAIN2 admission;
- `training_gpu_memory_fraction` as live TRAIN2 memory envelope;
- bounded transient and observability-loss behavior;
- whole-wave cancellation for sustained memory-safety failure;
- TRAIN-wave failure before EVAL2;
- separation from EVAL2/inference semantics;
- preservation of CPU serial behavior;
- absence of D1/D2 method changes.

This is an authority/evidence closeout gate, not a reason to add implementation machinery.

## 6. Final PASS criteria

PASS requires one final semantic candidate satisfying all of the following:

1. B1-B3 and the restart-seam correction remain conforming.
2. B4 has a snapshot-complete exactly-one-job R5-B realization with natural authenticated TRAIN2 completion or genuine resource terminal outcome and continuation/currentness evidence as applicable.
3. B5 environment concurrency overrides and their test are removed with no replacement configuration surface.
4. Retained zero-safe, live-memory, observability, cancellation, TRAIN/EVAL phase separation, lifetime cleanup, restart, currentness, publication, and scientific/numerical identity semantics do not regress.
5. Complete affected regression/integration and repository-required checks pass on the final semantic candidate.
6. Evidence/test references and any resulting documentation are reconciled; regenerate the Architecture Manual PDF/manifest only if its Markdown source changes.
7. A genuinely independent D3 falsification pass accepts the proposed durable Architecture Manual resource semantics.
8. Only after all above close may the parent workplan and review-reopen artifacts be closed/archived.

Until then the branch remains **NO-PASS**. No Serious Challenge is active.
