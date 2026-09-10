---
kind: implementation-workplan
workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION
protocol_version: 6.1.0
status: reopened - independent implementation review blockers
target_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
baseline_commit: d2d9051b56d83bcae18db71452c363276c118e3f
implementation_commit: cf75ac37922ec1ec60e0adab0903f2c0342a52d8
reviewed_candidate: 88e92650317687248221505b9fd7023954a8b2e4
highest_affected_domain: D3 software architecture -> D4 implementation
serious_challenge: none
trigger: target-host P5 cross-validation CUDA OOM after scheduler restoration
predecessor_context: archived MLFF P5 replay/MACE execution-recovery work
---

# MLFF P5 TRAIN2 CUDA lifetime, zero-safe admission, and phase-ownership repair

## 0. Independent implementation review disposition

Independent implementation review of candidate `88e92650317687248221505b9fd7023954a8b2e4` is **NO-PASS**. The implementation substantially closes the original lifetime, zero-safe-admission, phase-ownership, and diagnostic defects, but two executable failure-path defects and two acceptance/closeout obligations remain blocking.

No Serious Challenge is active. The accepted scientific and numerical method remains coherent, and no current evidence establishes that the exact frozen `batch_size=2` CuEq training method is intrinsically incompatible with a clean 24 GiB target device. Reopen only this bounded D3/D4 resource-execution surface unless the clean exact-method target-host gate below proves otherwise.

The blocking repair strategy deliberately reduces or alters existing control flow. Do not add a second scheduler, selective-victim allocator, out-of-memory (OOM) parser, persistent graphics-processing-unit (GPU) lease registry, recovery database, resource state machine, or scientific fallback.

### Retained implementation that must not be regressed

The following implemented corrections are accepted as directionally conforming and remain binding through rework:

1. `_post_selection_current_training_architecture()` drops temporary portable and accelerator-realized MACE models in `finally` and reuses shared accelerator-residency cleanup rather than creating a second lifetime subsystem.
2. Hard host random-access memory (RAM) and video random-access memory (VRAM) feasibility may resolve to zero jobs; the planner and submission loop no longer force a one-job floor.
3. The 24 GiB / 20.2 GiB baseline / 90% envelope / 6 GiB reservation case is represented as zero safe admission and launches no TRAIN2 work in the real P5 scheduling owner.
4. Missing utilization telemetry with a trustworthy current device-memory observation permits only conservative serial training; missing trustworthy memory observability blocks automatic admission.
5. One training scheduler future stops at the authenticated TRAIN2 summary. Post-TRAIN EVAL2 is serial and outside the TRAIN scheduler lifetime, using the existing durable TRAIN2 continuation rather than a new handoff record.
6. Scheduler reporting uses actual queued/active/completed/failed ownership rather than reconstructing pending work from a formula that can count failed submitted slots again.
7. Current documentation/history distinguishes TRAIN2 zero-safe admission from the separate EVAL2/inference serial-floor contract.

## 1. Background and terminology

The **Scientific Software Development Protocol (SSDP)** governs this workplan under Protocol 6.1. The highest materially affected domain is D3 software architecture because the former execution rule that CUDA training always starts with one job was falsified by target-host resource evidence. D4 implementation must concretize the corrected resource architecture without altering D1 scientific meaning or D2 numerical/training-method semantics.

**Video random-access memory (VRAM)** is accelerator memory visible to CUDA workloads. **Out of memory (OOM)** means an accelerator allocation cannot be satisfied. **TRAIN2** is the current authenticated MACE training execution path. **EVAL2** is the current authenticated checkpoint/model evaluation path. **CuEq** is the cuequivariance-backed transient MACE execution representation used by the configured training backend.

A **baseline** is accelerator memory already occupied before a new training job is admitted. A **zero-safe-admission state** means pending work exists but no new training job can presently fit inside the governing resource envelope. Zero safe admission is not equivalent to zero work, CUDA unavailability, or queue completion.

## 2. Target outcome and governing invariants

Repair post-selection cross-validation and final-production execution so that:

- temporary parent-process MACE/CuEq objects do not retain model-scale accelerator memory after their final consumer;
- TRAIN2 admission truthfully represents zero currently safe jobs;
- GPU memory safety is evaluated independently of optimizer-activity readiness and remains valid after adaptive promotion above one job;
- TRAIN2 concurrency cannot accidentally authorize post-TRAIN EVAL2 accelerator overlap;
- any TRAIN2 wave failure terminates that invocation's training/evaluation transition cleanly, preserving durable completed TRAIN2 state for later restart rather than beginning fresh GPU evaluation after failure;
- an intrinsically too-large scientific method fails explicitly rather than silently changing batch size, precision, backend, replay membership, optimizer semantics, or model architecture.

### Corrected D3 cycle-scoped architecture

> CUDA starts with one TRAIN2 job only when one job is currently resource-admissible. Zero safe admission is a valid execution state. Once TRAIN2 work is active, sustained aggregate VRAM occupancy at or above the configured training envelope is an execution-safety condition independent of active-job count and independent of true-epoch calibration readiness.

> A TRAIN scheduler slot owns TRAIN2 only. EVAL2 begins only after the TRAIN wave has completed successfully and released TRAIN ownership. If the TRAIN wave fails, the invocation terminates after cancellation/reaping; authenticated completed TRAIN2 summaries remain the restart boundary for a later invocation.

These are cycle-scoped D3 decisions for this repair. Durable Architecture Manual authority requires the normal independent D3 falsification/acceptance boundary before final closeout.

### D1/D2 invariants that must remain unchanged

Do not change:

- frozen selected size(s) or exact `T_selected` membership;
- cross-validation folds, purge/exclusion relationships, seeds, or horizons;
- replay training membership or independent TRUE_DFT replay-monitor membership;
- target/replay head semantics;
- loss coefficients or per-head weighting;
- optimizer family or optimizer-state semantics;
- `batch_size=2` or validation batch size;
- learning-rate schedule;
- exponential moving average (EMA), AMSGrad, weight decay, or clipping;
- model dtype/precision policy;
- configured training backend;
- checkpoint-selection or EVAL2 metric semantics;
- target-only fold acceptance;
- fresh final-production semantics.

An OOM is not authority to halve batch size, change gradient accumulation, switch CuEq to e3nn, change precision, reduce replay membership, or alter model architecture. Such evidence must be routed to the actual D2/D3 owner.

## 3. Governing runtime evidence

The target-host failure that opened this work established:

```text
device total                 24.0 GiB
configured training ceiling  21.6 GiB
pre-launch occupied          20.2 GiB
safe envelope remaining       1.4 GiB
configured job estimate       6.0 GiB
```

The historical planner nevertheless launched one job. That one TRAIN2 job later failed roughly 2,411 optimizer updates into epoch 0 inside CuEq backward while requesting another approximately 646 MiB allocation. Concurrent sibling EVAL2 was not required for this failure.

The implementation correctly repairs the original forced-one admission and temporary preflight model lifetime. The independent review found the remaining defects below.

## 4. Blocking repair R1 - sustained multi-job memory hazard must fail closed

### Finding

Current `AdaptiveTrainingConcurrency.observe()` evaluates aggregate memory safety before true-epoch readiness, but only converts sustained over-envelope occupancy into `memory_hazard=True` when `active_jobs == 1`. With two or more active TRAIN2 jobs, the code deliberately keeps all running jobs alive and relies on the later stable-calibration path to reduce only future replacement concurrency.

A regression test explicitly asserts that two running jobs may remain above the VRAM envelope without producing a memory hazard.

This is blocking. It reopens the same physical OOM class after adaptive promotion: rare high-water batches, initialization/validation transitions, or a changed external baseline can push aggregate occupancy above the configured memory envelope after multiple jobs are active. Lowering only the future replacement target cannot make the current unsafe allocation disappear before a physical OOM occurs. The later true-epoch averaging path may also be unavailable while jobs initialize or validate.

### Required end state

Use the existing memory-hazard debounce uniformly for **any positive active TRAIN2 count**:

- while occupancy is below the envelope, ordinary operation continues;
- a transient excursion above the envelope may remain a nonterminal unsafe observation during the existing bounded grace interval;
- if aggregate occupancy remains at or above the envelope through the grace interval and at least one owned TRAIN2 job is active, return a hard memory hazard regardless of whether one, two, or more jobs are active;
- the scheduler then uses the already existing cancellation event/process supervision path to stop and reap the whole current TRAIN2 wave;
- GPU-utilization saturation remains a soft concurrency/promotion signal and may still throttle future replacements without killing running jobs when memory itself remains safe.

Do **not** introduce selective victim choice, a second reservation algorithm, or a new scheduler. The simplest conforming repair is to remove the `active == 1` exception from the existing hard-memory hazard decision and preserve the existing soft utilization/replacement logic below it.

### Required evidence

Replace the test that encodes "running work must not be killed" under sustained multi-job VRAM violation with evidence that distinguishes:

1. multi-job transient over-envelope spike before grace expiry -> `memory_safe=False`, no terminal hazard yet;
2. multi-job sustained over-envelope occupancy after grace expiry -> `memory_hazard=True`;
3. real P5 scheduler owner receives that hazard, cancels/reaps active TRAIN2 work, starts no EVAL2, and publishes no CV acceptance.

Clarification: the existing requirement that "active jobs consuming capacity wait/re-evaluate rather than collapse to idle zero admission" applies to ordinary active saturation **inside the safety envelope** or to a transient memory excursion before debounce expiry. It never authorizes indefinite execution above the hard VRAM safety envelope.

## 5. Blocking repair R2 - any TRAIN2 wave failure must terminate before EVAL2

### Finding

`MacePostSelectionTrainer` reports any nonzero MACE child exit, including an actual CUDA OOM, as the existing generic `PostSelectionExecutionError`. The scheduler immediately re-raises `TrainingResourceError`, cancellation, and process-exit control exceptions, but stores other TRAIN failures in `train_failure`, completes EVAL2 for already trained slots, and only then re-raises the original failure.

Therefore a real CUDA OOM from the MACE child can still enter fresh GPU EVAL2 work because it is not typed as `TrainingResourceError`. This contradicts the workplan's failure rule and couples failure classification to an exception type that does not distinguish physical CUDA OOM.

### Required end state

Simplify the TRAIN/EVAL transition instead of adding an OOM parser or exception wrapper:

- **any exception from the TRAIN2 scheduling wave** stops new admission, signals cancellation, cancels/reaps owned active children using the current supervision path, reports failure, and re-raises before `complete_eval2_for_trained_slots()`;
- EVAL2 is entered only after the entire TRAIN2 wave completes successfully;
- authenticated TRAIN2 summaries already completed before the failure remain durable and reusable on the next invocation;
- the next invocation reclassifies/reuses those summaries through the existing continuation owner and resumes outstanding TRAIN2/EVAL2 work normally;
- no new failure-state record, retry database, OOM-message classifier, or handoff artifact is introduced.

Remove the `train_failure` "evaluate siblings then raise" branch. This is both simpler and safer than teaching the scheduler to parse MACE stderr for CUDA OOM text.

### Required evidence

Exercise the real P5 owner with at least:

1. one TRAIN2 slot reaches a durable authenticated summary, then a later TRAIN2 slot raises a representative generic training execution error; assert no EVAL2 executes in that failing invocation;
2. rerun with a healthy trainer; assert completed TRAIN2 state is reused rather than retrained and the remaining campaign can resume;
3. where concurrent TRAIN2 children exist, a failure stops admission and owned siblings are cancelled/reaped through the existing process/cancellation semantics;
4. no partial CV acceptance or final-production publication is exposed after the failed invocation.

A test may include CUDA-OOM text in the representative child failure to protect the historical symptom, but production code must not parse that text to decide whether EVAL2 is safe.

## 6. Blocking repair R3 - reconcile the new memory-hazard grace configuration surface

### Finding

The implementation reads `execution.parallel_training_memory_hazard_grace_seconds` with a default of 60 seconds, but the checked-in campaign example/current operator-facing execution configuration does not declare or explain that key. The debounce mechanism was delegated implementation detail in the workplan; public configurability was not required.

### Required end state

Prefer the lower-complexity option unless existing product authority proves operator tuning is required:

- remove the new TOML/configuration lookup and keep the bounded debounce as an implementation-local `TrainingConcurrencyPolicy` default/test parameter; or
- if operator configurability is already a genuine supported requirement, retain the key and document/validate it alongside the other training scheduler settings, including the fact that it controls only transient-memory debounce and does not weaken the envelope itself.

Do not keep an undocumented public safety-affecting configuration key merely because it makes tests convenient.

## 7. Blocking acceptance R4 - execute current evidence and the bounded target-host gate

### Current evidence status

Source inspection finds relevant new regression specifications, but the reviewed branch has no recorded Python regression/integration CI result. The only observed GitHub Actions run for the implementation candidate is documentation PDF generation. Tests present in source are not an executed evidence realization.

The new architecture-classification CUDA test uses real PyTorch CUDA allocation but substitutes the actual MACE/CuEq conversion with a bounded cyclic tensor stand-in. That is useful owner-lifetime evidence, but it cannot establish that the real third-party CuEq conversion leaves no unexpected process-global/model-scale residency.

### Required final evidence

After R1-R3, execute fresh evidence on the final candidate:

- focused `training_parallel` and P5 zero-safe/phase-ownership tests;
- P5 recovery, cancellation/process-supervision, provider-lifetime, R7-R11, multi-size/currentness, downstream integration, and every other materially affected regression re-derived from the final diff;
- repository/project-required Python checks;
- bounded target-host G0/G6 evidence through the real current MACE/CuEq path.

The bounded target-host run must record enough existing diagnostics to establish:

```text
pre-recovery/preflight occupancy
 -> post-recovery/admission occupancy
 -> one exact frozen-method TRAIN2 admission or correct zero-safe rejection
 -> observed aggregate high-water / outcome
 -> no parent-preflight model-scale residue
 -> no CUDA OOM if admitted
 -> restart/currentness remains valid
```

Process/PID attribution is diagnostic and should use existing host tooling where available; do not build a persistent profiling subsystem.

If the exact clean-baseline `batch_size=2` CuEq method still OOMs or cannot fit the supported target-device envelope, stop D4 repair and reopen D3/D2 method/device compatibility. Do not silently change batch size, precision, backend, replay exposure, optimizer accumulation, or model architecture.

Full production GPU performance qualification remains deferred to release closeout. This gate is only the bounded hardware evidence necessary to close this concrete OOM/resource-safety defect.

## 8. Retained implementation obligations and final regression matrix

After the blocking repairs, the final candidate must still prove all of the following:

1. 24 GiB GPU, 20.2 GiB baseline, 90% ceiling, 6 GiB estimate -> zero jobs and no launch.
2. Safe low baseline -> ordinary one-job startup.
3. Safe measured workload -> adaptive promotion remains possible.
4. Positive configured job cap cannot override zero-safe admission.
5. Insufficient host RAM -> zero safe training jobs rather than forced one.
6. Active jobs with no additional safe slot remain live and wait/re-evaluate while aggregate VRAM remains inside the safety envelope.
7. Transient over-envelope memory excursions are debounced; sustained over-envelope occupancy with any active-job count becomes a terminal memory hazard.
8. Idle pending queue + zero feasible jobs -> typed failure without spin.
9. Memory safety is observed before true-epoch readiness.
10. Unavailable utilization telemetry + known current memory capacity -> conservative serial/no promotion.
11. Unavailable trustworthy current memory capacity -> no automatic TRAIN launch.
12. Repeated temporary architecture classification has bounded post-cleanup residency; exception cleanup also holds.
13. Architecture digest semantics are unchanged by lifetime cleanup.
14. TRAIN scheduler future ends at authenticated TRAIN2-summary ownership.
15. EVAL2 cannot overlap sibling TRAIN2 under the repaired P5 path.
16. Completed TRAIN2 state is reused after interruption before EVAL2.
17. Any TRAIN-wave exception prevents EVAL2 in that invocation, cancels/reaps owned siblings, and preserves restartable completed TRAIN2 state.
18. Scheduler failure reporting counts queued/active/completed/failed work truthfully.
19. Cross-validation scientific identities/results are invariant to the resource-control repair.
20. Final production uses the same corrected TRAIN admission/supervision owner.

Acceptance must exercise the real planner/controller/orchestration owner. Resource probes and expensive MACE numerics may be bounded/faked below that owner when the claim is scheduler semantics. Planner-only tests cannot close end-to-end admission, failure, or restart behavior.

## 9. Documentation, authority, evidence, and impact closure

Current documentation must remain consistent with final executable behavior:

- `campaign.toml.example` and generated/default configuration comments;
- `mdstats/training_data/training_parallel.py` comments/docstrings;
- P5 execution/performance Architecture Manual material;
- README/user-facing scheduler documentation;
- `docs/history/mlff/train2_admission_evolution.md` and its index.

Preserve the distinct EVAL2/inference serial-floor contract; do not mechanically apply TRAIN2 zero-safe semantics to inference.

Because this cycle mutates durable D3 Architecture Manual resource semantics, final accepted-current D3 promotion requires an **independent falsification pass by a reviewer/context that did not author the proposed D3 change**. The present review authored the governing workplan earlier in the same context and therefore cannot satisfy that independence gate by itself. After R1-R4 close, obtain a fresh independent D3 review before marking the workplan closed/accepted-current.

Prior D1/D2 scientific evidence remains admissible because method semantics are frozen. Prior D4 evidence touching scheduler admission, memory-hazard handling, TRAIN/EVAL phase ownership, failure transition, cleanup, configuration, or restart is review-required and must be rerun/remapped on the final candidate. Preserve unaffected evidence with an explicit applicability rationale.

## 10. Reopen and Serious Challenge triggers

Remain within this workplan for:

- parent accelerator/model retention;
- zero-safe resource-floor logic;
- TRAIN scheduler phase ownership;
- live-memory safety and debounce;
- ordinary process/cancellation lifetime;
- TRAIN-wave failure transition;
- execution-only resource observability/estimation.

Reopen D3/D2 only if clean exact-method target-host evidence shows that the frozen method itself cannot safely execute on the supported device without changing scientific/numerical semantics.

Raise a Serious Challenge only if evidence shows accepted D1/D2 authority or simultaneous D3 constraints are materially contradictory, false, or impossible to concretize. No such evidence exists at this review.

## 11. Final closure criteria

PASS requires:

- R1-R3 implemented without additive substitute machinery;
- R4 fresh affected regression/integration and bounded target-host evidence complete;
- temporary P5 architecture classification leaves no model-scale accelerator residue under the real relevant path;
- zero-safe TRAIN admission remains end-to-end;
- sustained aggregate VRAM violation stops owned TRAIN2 for any active-job count before known unsafe work is allowed to continue;
- no EVAL2 begins after any failed TRAIN2 wave in the same invocation;
- successful TRAIN waves still transition to serial EVAL2 and resume correctly from authenticated TRAIN2 summaries;
- no D1/D2 method identity or numerical behavior changed;
- failure diagnostics, cancellation/reaping, restart, currentness, and publication remain truthful;
- affected documentation/history/configuration surfaces agree with implementation;
- final independent D3 falsification accepts the durable Architecture Manual mutation.

Until all of these close, the workplan remains reopened and the branch is **NO-PASS**.
