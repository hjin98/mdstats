---
kind: implementation-workplan
workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION
protocol_version: 6.1.0
status: reopened-ready-for-implementation
plan_review_state: second-pass-design-closure-complete
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
baseline_commit: d2d9051b56d83bcae18db71452c363276c118e3f
implementation_commit: cf75ac37922ec1ec60e0adab0903f2c0342a52d8
reviewed_candidate: 88e92650317687248221505b9fd7023954a8b2e4
highest_affected_domain: D3 software architecture -> D4 implementation
serious_challenge: none
trigger: target-host P5 cross-validation CUDA OOM after scheduler restoration
predecessor_context: archived MLFF P5 replay/MACE execution-recovery work
precedence: This workplan supersedes only the P5 TRAIN2 resource-admission, live-memory-safety, TRAIN-wave failure-transition, and TRAIN2/EVAL2 phase-ownership behavior identified below. All non-conflicting frozen P5 scientific, numerical, identity, restart, replay, publication, and execution authority remains binding.
---

# MLFF P5 TRAIN2 CUDA lifetime, zero-safe admission, and phase-ownership repair

## 0. Second-pass design closure disposition

The second independent workplan review is complete. The **workplan itself is PASS / frozen for the next implementation round**, while the currently reviewed implementation candidate `88e92650317687248221505b9fd7023954a8b2e4` remains **NO-PASS** until the bounded repairs and evidence below are complete.

No Serious Challenge is active. The accepted D1 scientific formulation and D2 numerical/training method remain coherent, and no current evidence establishes that the exact frozen `batch_size=2` CuEq training method is intrinsically incompatible with a clean 24 GiB target device.

This revision is snapshot-complete for the open repair. It deliberately closes ambiguity found in the first reopen without adding a second scheduler, resource database, out-of-memory (OOM) parser, graphics-processing-unit (GPU) lease registry, retry state machine, selective-victim allocator, model representation, or scientific fallback.

### Retained implementation that must not regress

The following existing corrections are accepted as directionally conforming and remain binding through rework:

1. `_post_selection_current_training_architecture()` drops temporary portable and accelerator-realized MACE models in `finally` and reuses shared accelerator-residency cleanup rather than creating a second lifetime subsystem.
2. Hard host random-access memory (RAM) and video random-access memory (VRAM) feasibility may resolve to zero jobs; the planner and submission loop no longer force a one-job floor.
3. The 24 GiB / 20.2 GiB baseline / 90% envelope / 6 GiB reservation case is represented as zero safe admission and launches no TRAIN2 work in the real P5 scheduling owner.
4. Missing utilization telemetry with a trustworthy current device-memory observation permits only conservative serial training; missing trustworthy current memory observability blocks initial automatic admission.
5. One training scheduler future stops at the authenticated TRAIN2 summary. Post-TRAIN EVAL2 is serial and outside TRAIN scheduler lifetime, using the existing durable TRAIN2 continuation rather than a new handoff record.
6. Scheduler reporting uses actual queued/active/completed/failed ownership rather than reconstructing pending work from a formula that can count submitted failed slots again.
7. Current documentation/history already distinguishes TRAIN2 zero-safe admission from the separate EVAL2/inference serial-floor contract.

## 1. Background and terminology

The **Scientific Software Development Protocol (SSDP)** governs this workplan under Protocol 6.1. The highest materially affected domain is D3 software architecture because target-host evidence falsified the former architectural assumption that a usable CUDA device always admits at least one TRAIN2 job. D4 implementation must concretize the corrected resource architecture without altering D1 scientific meaning or D2 numerical/training-method semantics.

**Video random-access memory (VRAM)** is accelerator memory visible to CUDA workloads. **Out of memory (OOM)** means an accelerator allocation cannot be satisfied. **TRAIN2** is the current authenticated MACE training execution path. **EVAL2** is the current authenticated checkpoint/model evaluation path. **CuEq** is the cuequivariance-backed transient MACE execution representation used by the configured training backend.

A **baseline** is aggregate accelerator memory already occupied before a proposed TRAIN2 admission. It can include the current mdstats parent, owned children, unrelated external processes, and runtime/context occupancy. A **zero-safe-admission state** means pending TRAIN2 work exists but no new training job can presently fit inside the governing resource envelope. Zero safe admission is not queue completion, CUDA unavailability, or zero currently running work.

The **TRAIN2 VRAM envelope** in this workplan is the configured training resource envelope derived from `training_gpu_memory_fraction`. For this repair it is both the admission ceiling and the live aggregate TRAIN2 safety envelope. This is intentionally distinct from the EVAL2/inference controller's separate accepted serial-floor/calibration semantics.

## 2. Governing authority, precedence, and protected invariants

### 2.1 Historical authority and narrow supersession

The archived P5 scheduler restoration authority remains binding except where new target-host evidence requires the following narrow correction.

The older scheduler rule allowed **stable post-add saturation** to lower future replacement concurrency without killing already-running work. That rule remains valid for GPU-utilization saturation and for ordinary resource saturation while aggregate VRAM remains inside the TRAIN2 safety envelope. It is **superseded for sustained TRAIN2 VRAM-envelope violation**: once live aggregate VRAM is observably outside the governed safety envelope for more than the bounded transient-observation allowance defined below, continuing the whole wave is no longer an admissible interpretation of "throttle future replacements."

The older P5 fail-fast public-operation rule remains binding: a hard TRAIN2 failure stops new admission and the current public operation fails. The phase-separation repair makes that rule explicit at the TRAIN2 -> EVAL2 boundary: a failed TRAIN wave never begins fresh EVAL2 work in the same invocation.

This is a cycle-scoped D3 correction until independently accepted into durable Architecture Manual authority. Branch-local Architecture Manual edits are therefore proposed candidate authority until the independent D3 falsification gate in Section 9 passes.

### 2.2 D1/D2 invariants that must remain unchanged

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

An OOM is not authority to halve batch size, add gradient accumulation, switch CuEq to e3nn, change precision, reduce replay membership, change optimizer exposure, or alter model architecture. Evidence requiring such a change must be routed to the actual D2/D3 owner.

### 2.3 Explicit non-goals

Do not:

- raise the 90% training VRAM fraction merely to make the failing case fit;
- hard-code the observed 19-20 GiB as a universal per-job reservation;
- repeatedly call `torch.cuda.empty_cache()` during ordinary training as a compensating loop;
- add a second scheduler, persistent resource lease/queue registry, retry state, or failure database;
- parse CUDA-OOM stderr in production merely to decide whether EVAL2 is allowed;
- delete valid restart/checkpoint evidence to obtain a clean run;
- globally serialize unrelated inference paths;
- change target-size, replay, CV, checkpoint-selection, or final-production science.

## 3. Governing runtime evidence and affected defect family

The target-host failure that opened this work established:

```text
device total                 24.0 GiB
configured TRAIN2 envelope   21.6 GiB
pre-launch occupied          20.2 GiB
safe envelope remaining       1.4 GiB
configured job estimate       6.0 GiB
```

The historical planner nevertheless launched one TRAIN2 job. That job later failed roughly 2,411 optimizer updates into epoch 0 inside CuEq backward while requesting another approximately 646 MiB allocation. Concurrent sibling EVAL2 was not required for this specific failure.

The current implementation already repairs the original forced-one admission and closes the obvious temporary preflight-model lifetime. Independent review found three still-open execution/control issues:

1. sustained live VRAM violation becomes terminal only when exactly one TRAIN2 job is active;
2. a generic TRAIN2 child failure can still be followed by EVAL2 for previously trained siblings before the original failure is raised;
3. live GPU-memory observability loss after admission has no bounded fail-closed rule and can erase an already observed unsafe-memory condition.

The current implementation also introduced an undocumented operator-facing `parallel_training_memory_hazard_grace_seconds` lookup even though public configurability was not required.

These are one bounded resource/orchestration family. Repair the shared owners directly rather than layering another control mechanism around them.

## 4. Cycle-scoped D3 decisions and delegated D4 space

### 4.1 Cycle-scoped D3 decisions

1. **Zero-safe admission is real.** Pending TRAIN2 work may resolve to zero currently admissible jobs.
2. **The existing configured TRAIN2 memory fraction is the relevant safety envelope.** Current aggregate GPU occupancy counts regardless of process ownership. No separate public "hard memory" threshold is introduced in this repair.
3. **Promotion and safety are distinct.** True optimizer/epoch activity gates scalable-demand estimation and promotion above one job; it never gates recognition of unsafe or unobservable memory state.
4. **One unsafe observation immediately blocks further admission.** A single trustworthy sample at or above the TRAIN2 VRAM envelope marks current memory state unsafe and must prevent any new TRAIN2 admission/promotion.
5. **Transient observation tolerance is bounded by the normal control loop.** One isolated unsafe observation may be rechecked to avoid terminating on a transient measurement. If the next normal trustworthy control observation is still at or above the envelope while any owned TRAIN2 job remains active, the wave is a hard memory hazard and must be cancelled/reaped. Equivalent D4 mechanics are allowed, but the implementation may not knowingly continue sustained over-envelope execution across multiple normal control intervals.
6. **Runtime observability cannot disappear indefinitely.** While TRAIN2 work is active, an unavailable memory sample authorizes no promotion/admission. One isolated missed sample may be tolerated only when the immediately preceding trustworthy sample was safe. A second consecutive normal control sample without trustworthy memory observation, or loss of observability immediately after an already-unsafe sample, is a terminal resource-observability failure for the current TRAIN wave.
7. **GPU utilization remains soft.** Utilization saturation alone may throttle future replacements and does not kill current work.
8. **TRAIN scheduler ownership ends at authenticated TRAIN2 summary.** EVAL2 is outside the TRAIN scheduler lifetime and remains serial/non-overlapping under this repair.
9. **A failed TRAIN wave terminates the invocation before EVAL2.** Any exception escaping the TRAIN scheduling wave cancels/reaps owned active TRAIN2 work and is re-raised before post-TRAIN EVAL2 begins. Completed authenticated TRAIN2 summaries remain restartable durable state for a later invocation.
10. **Resource repair cannot mutate scientific method identity.** If the exact clean single-job method is not compatible with the supported target device, route the incompatibility upstream rather than applying an implicit scientific fallback.

### 4.2 Delegated D4 concretization

The following remain replaceable implementation details provided the decisions above hold:

- whether bounded unsafe/missing-observation state is represented by timestamps, counters, or a small existing-controller field;
- helper factoring inside `training_parallel.py` and `campaign_post_selection_runtime.py`;
- exact internal exception subclass names within the existing training-resource error family;
- test fixture mechanics below the real scheduler/trainer owner;
- the exact cleanup ordering needed to make the real MACE/CuEq temporary-model lifetime satisfy its postcondition;
- wording/layout of diagnostics provided the required states remain distinguishable.

Do not create a new scheduler, monitor daemon, lease manager, state machine, or persistence record to express these transient states.

### 4.3 Active simplification

The preferred repair reduces existing control flow:

- remove the `active_jobs == 1` special case from the hard-memory-hazard semantics;
- remove the `train_failure -> run EVAL2 -> re-raise` continuation path;
- remove the new TOML lookup for memory-hazard grace;
- reuse the existing scheduler sample, cancellation event, process-group supervision, authenticated TRAIN2 summary, and provider cleanup boundaries.

## 5. Implementation obligations

### R1 - make live memory safety uniform after adaptive promotion

#### Concern

The current controller can terminate a sustained over-envelope one-job run but deliberately keeps two or more over-envelope TRAIN2 jobs alive until they finish naturally. Future-replacement throttling cannot reclaim the memory of already-running jobs and can therefore reproduce the physical OOM family after adaptive promotion.

#### Required end state

- Evaluate aggregate VRAM safety on every trustworthy scheduler sample regardless of child phase or active-job count.
- At the first over-envelope observation, admit/promote no additional TRAIN2 work.
- Permit at most the bounded transient recheck described in Section 4.1.
- If the next normal trustworthy control observation remains over-envelope with owned TRAIN2 work active, return a hard memory hazard and route through existing cancellation/reaping.
- Preserve the existing soft GPU-utilization replacement throttle whenever memory itself remains safe.
- Do not select a victim job or attempt an in-place concurrency decrement by killing one arbitrary member. The current TRAIN wave is the failure/cancellation unit.

#### Acceptance boundary

The real owners are `AdaptiveTrainingConcurrency` plus `_execute_post_selection_pending_runs()` and the existing child-cancellation path. Unit controller tests may prove state transitions; end-to-end hazard closure must exercise the real P5 scheduler owner. Resource telemetry may be deterministically substituted below that owner. A planner-only test cannot close cancellation/EVAL/publication semantics.

#### Required evidence

At minimum establish:

1. multi-job transient one-sample over-envelope observation -> unsafe, no new admission, no terminal hazard yet;
2. next trustworthy sample returns safe -> unsafe state clears and current work may continue;
3. multi-job over-envelope state persists into the next normal trustworthy sample -> terminal memory hazard;
4. real P5 scheduler receives the hazard, stops admission, cancels/reaps owned TRAIN2 work, starts no EVAL2, and publishes no CV acceptance/final-production result.

### R2 - make runtime telemetry loss fail closed without a second monitor

#### Concern

Initial automatic admission already requires trustworthy current memory information, but after TRAIN2 begins the current controller clears unsafe-memory history when `query_gpu_telemetry()` returns no sample. Repeated telemetry loss can therefore leave active accelerator work without the live safety observation that the corrected architecture assumes.

#### Required end state

Using the same scheduler/control loop:

- a missing current GPU-memory observation while TRAIN2 is active immediately blocks promotion/new admission;
- if the last trustworthy sample was already unsafe, the missing next normal sample is terminal because safety recovery cannot be established;
- if the last trustworthy sample was safe, one isolated missing sample may be tolerated, but persistent loss through the next normal control sample terminates the TRAIN wave with the existing typed resource/observability failure path;
- a later invocation may retry normally after observability is restored;
- do not create a second telemetry thread/process or persist transient observability state.

If the production telemetry implementation has an already-existing equivalent memory-only fallback that remains trustworthy during active work, it may satisfy the observation instead of being treated as missing; do not invent a new fallback solely for this repair.

#### Required evidence

Cover safe -> one missing -> safe recovery, safe -> missing -> missing terminal failure, unsafe -> missing immediate terminal failure, and real-owner propagation to cancellation/no-EVAL/no-publication.

### R3 - any TRAIN2 wave failure must terminate before EVAL2

#### Concern

`MacePostSelectionTrainer` converts any nonzero child exit, including physical CUDA OOM, into the existing generic `PostSelectionExecutionError`. The scheduler currently re-raises resource/control exceptions immediately but stores other TRAIN failures, runs EVAL2 for previously completed TRAIN2 slots, and only then raises the original failure.

#### Required end state

- Any exception escaping the TRAIN scheduling wave stops new admission.
- Signal cancellation and cancel/reap all owned active children through the existing supervision path.
- Report the failed TRAIN wave truthfully.
- Re-raise before `complete_eval2_for_trained_slots()` or equivalent post-TRAIN evaluation is entered.
- Preserve already authenticated completed TRAIN2 summaries and materializations as restartable durable state.
- On the next healthy invocation, existing continuation/currentness logic reuses those completed summaries and resumes outstanding TRAIN2/EVAL2 work.
- Do not add an OOM stderr parser, OOM-specific persistence, retry database, or alternate handoff record.

#### Acceptance boundary

For scheduler-transition semantics, bounded trainer failures below the real P5 scheduler are valid. For the historical child-process failure path, at least one deterministic acceptance must retain the real `MacePostSelectionTrainer` / wrapper-subprocess / cancellation-process-group owner while substituting only a bounded child workload. A harness that raises before the production trainer/process boundary cannot by itself close child-OOM/failure cleanup semantics.

#### Required evidence

At minimum establish:

1. one slot reaches an authenticated TRAIN2 summary, then a later slot fails generically -> no EVAL2 in that invocation;
2. rerun with healthy execution -> completed TRAIN2 state is reused rather than retrained;
3. concurrent TRAIN2 failure -> no new admission and active owned siblings are cancelled/reaped before the scheduler returns/raises;
4. deterministic real-trainer nonzero child exit, optionally containing representative CUDA-OOM text -> same no-EVAL/cancellation/reaping outcome without production stderr classification;
5. no partial CV acceptance or final-production publication after the failed invocation;
6. final-production caller exhibits the same failure-before-EVAL behavior through the shared owner.

### R4 - remove the accidental public memory-hazard-grace configuration surface

The implementation introduced `execution.parallel_training_memory_hazard_grace_seconds`, but operator tuning was not part of the accepted requirement and the key is absent from the checked-in operator-facing example.

Required end state:

- remove the `_cfg(... "parallel_training_memory_hazard_grace_seconds" ...)` lookup from the production configuration path;
- do not add the key to `campaign.toml.example` or generated public configuration;
- express the bounded transient-observation behavior through existing scheduler cadence/controller-local implementation;
- an internal test/policy field may remain only if it materially simplifies deterministic testing and does not become resolved operator configuration or scientific identity;
- if later evidence establishes a real operator requirement for tunable debounce, reopen the configuration contract deliberately rather than keeping an undocumented latent key.

This is a reduction, not a request for a replacement knob.

### R5 - complete baseline attribution and clean exact-method target-host characterization

The hardware evidence has two distinct targets and neither may substitute for the other.

#### R5-A - attribute the pre-admission baseline

On the target host, without deleting valid restart evidence, capture:

1. aggregate GPU occupancy immediately before P5 recovery/currentness preflight;
2. whether `_post_selection_current_training_architecture()` or equivalent temporary training-realization classification executes;
3. aggregate occupancy immediately after that preflight and at authoritative TRAIN admission;
4. process/PID attribution where ordinary host tooling exposes it.

Classify material baseline occupancy as current mdstats parent, owned child/orphan, unrelated external process, mixed, or unknown. Aggregate occupancy remains authoritative for admission even when attribution is unknown.

If an owned orphan/stale child is discovered, reopen only the existing child-process lifetime/cancellation surface needed to reap it. Never terminate an unrelated external process.

A real MACE/CuEq temporary architecture-classification call must return to its expected bounded allocator/context baseline; the cyclic-tensor unit stand-in is supporting evidence, not a substitute for this target-host realization.

#### R5-B - characterize one exact current-method TRAIN2 job from a clean/admissible baseline

After R1-R4 and after parent-preflight residue is closed, run one exact frozen-method TRAIN2 job for the affected N=512 CV context on the target 24 GiB-class device with the configured `batch_size=2`, CuEq backend, precision, replay/method identity, and ordinary checkpoint/restart semantics unchanged.

A high-baseline zero-safe rejection proves admission behavior but **does not satisfy this clean single-job characterization**. The single-job gate requires an actually clean/admissible baseline. If unrelated occupancy prevents obtaining one, record this gate unavailable/blocking rather than calling zero-safe rejection proof of intrinsic method fit.

Record at minimum:

- clean pre-admission aggregate baseline;
- configured TRAIN2 envelope and per-job bootstrap reservation;
- aggregate VRAM high-water and outcome across the run;
- whether any model-scale parent/preflight residency remains;
- TRAIN2 completion/OOM/resource-stop outcome;
- restart/currentness behavior after the run.

If the job approaches the envelope, stops for memory safety, or physically OOMs, collect the cheapest available discriminating diagnostics before changing method, preferably through existing runtime/framework/host facilities rather than new persistent instrumentation:

- process-local PyTorch allocated/reserved high-water where available;
- active training phase at high water/failure;
- high-demand/failing batch identity;
- atom count and graph/edge footprint for the high-demand batch where available;
- target versus replay source/head role when relevant;
- materially relevant non-PyTorch/external device occupancy.

Because the historical failure occurred well into epoch 0, initialization or a handful of early batches is not sufficient evidence of single-job feasibility.

If the exact isolated job still OOMs or persistently requires more than the accepted target-device safety envelope, stop this D4 repair and route a D3/D2 method/device-compatibility reconsideration. Do not silently mutate batch size, precision, backend, accumulation, replay exposure, or architecture.

Full production GPU performance qualification remains deferred to release closeout. R5 is only the bounded target-host evidence needed for this concrete resource-safety defect.

## 6. Evidence specifications, real owners, and allowed doubles

| Governed proposition | Real semantic owner / boundary | Allowed bounded doubles | Insufficient proxy |
| --- | --- | --- | --- |
| zero-safe initial TRAIN2 admission | `build_training_concurrency_plan()` -> controller -> real P5 submission loop | deterministic resource/GPU observations and bounded trainer workload | planner-only arithmetic for end-to-end no-launch claim |
| sustained live-memory / observability failure stops the TRAIN wave | `AdaptiveTrainingConcurrency` + `_execute_post_selection_pending_runs()` + existing cancellation path | deterministic telemetry below scheduler; bounded trainer workload | controller unit test alone for cancellation/EVAL/publication |
| child failure cancels/reaps and prevents EVAL2 | P5 scheduler plus `MacePostSelectionTrainer`/owned child-process boundary for process-cleanup claim | bounded wrapper/child workload, controlled nonzero exit | harness exception before real child-process owner for process-reaping claim |
| temporary architecture realization leaves no model-scale residue | `_post_selection_current_training_architecture()` + actual current MACE/CuEq realization/cleanup on target host | bounded model/config/data size while retaining real conversion path | cyclic tensor only for real CuEq lifetime claim |
| scientific/numerical identity is unchanged | current P5 plan/method/continuation/publication owners | existing bounded MACE numerics below identity owners | comparing only user-visible text/log output |

Every new evidence execution against a changed candidate is a new evidence realization. Prior D1/D2 evidence remains admissible because method semantics are frozen. Prior D4 results touching scheduler admission, hazard handling, telemetry loss, failure transition, phase ownership, cleanup, configuration, cancellation, or restart are review-required and must be rerun/remapped on the final candidate.

## 7. Final affected regression and integration matrix

After R1-R5, the final candidate must establish all of the following on fresh applicable evidence:

1. 24 GiB GPU, 20.2 GiB baseline, 90% envelope, 6 GiB estimate -> zero jobs and no launch.
2. Safe low baseline -> ordinary one-job startup.
3. Safe measured workload -> adaptive promotion remains possible.
4. Positive configured job cap cannot override zero-safe admission.
5. Insufficient host RAM -> zero safe training jobs rather than forced one.
6. Active jobs with no additional safe slot remain live and wait/re-evaluate while aggregate VRAM remains inside the safety envelope.
7. One isolated over-envelope observation blocks admission and can recover if the next trustworthy sample is safe.
8. Persistent over-envelope occupancy through the next normal trustworthy sample with any positive active-job count -> terminal memory hazard.
9. Safe -> one missing memory observation -> safe recovery remains possible without promotion during the missing interval.
10. Persistent runtime memory-observability loss, or observability loss immediately after an unsafe sample -> terminal resource failure and cancellation.
11. Idle pending queue + zero feasible jobs -> typed failure without spin.
12. Memory safety is observed independently of true-epoch readiness.
13. Unavailable utilization telemetry + known current memory capacity -> conservative serial/no promotion.
14. Unavailable trustworthy initial memory capacity -> no automatic TRAIN launch.
15. Repeated temporary architecture classification has bounded post-cleanup residency; exception cleanup also holds.
16. Architecture digest semantics are unchanged by lifetime cleanup.
17. TRAIN scheduler future ends at authenticated TRAIN2-summary ownership.
18. EVAL2 cannot overlap sibling TRAIN2 under the repaired P5 path.
19. Completed TRAIN2 state is reused after interruption before EVAL2.
20. Any TRAIN-wave exception prevents EVAL2 in that invocation, cancels/reaps owned siblings, and preserves restartable completed TRAIN2 state.
21. Deterministic real `MacePostSelectionTrainer` nonzero-child failure follows the same cancellation/no-EVAL path.
22. Scheduler failure reporting counts queued/active/completed/failed work truthfully.
23. Cross-validation scientific identities/results are invariant to the resource-control repair.
24. Final production uses the same corrected TRAIN admission/supervision/failure owner.
25. No partial CV acceptance or final-production publication survives a failed TRAIN wave.

Retain and rerun the materially affected current suites, including training scheduler tests, P5 replay/MACE recovery and cancellation/process tests, TRAIN2 continuation/architecture tests, provider-lifetime tests, P5 R7-R11 guards, multi-size/currentness/publication tests, downstream integration, and repository-configured fast Python checks. Re-derive the final affected surface from the assembled diff; if it cannot be bounded confidently, run the broader P5/P7/campaign/replay/storage regression rather than guessing non-impact.

Acceptance must exercise the real semantic owner named in Section 6. Resource probes and expensive MACE numerics may be bounded/faked only below or outside the owner under acceptance.

## 8. Stage order and evidence reuse

Use the following dependency order to avoid compensating for an earlier defect with later machinery:

1. **R1-R2:** correct live memory/observability supervision in the existing controller and scheduler.
2. **R3:** remove the failed-wave-to-EVAL continuation and close process/cancellation semantics.
3. **R4:** remove the accidental public debounce configuration lookup.
4. Run focused controller/scheduler/failure-transition tests and stage-local affected regression.
5. Run deterministic real-owner child-process failure/cancellation evidence.
6. **R5-A:** target-host preflight/baseline attribution and real MACE/CuEq lifetime check.
7. **R5-B:** clean exact-method single-TRAIN2 target-host characterization.
8. Reconcile documentation/history/current proposed D3 text to the final executable behavior.
9. Run complete final affected regression/integration and project-required checks on the unchanged semantic candidate.
10. Obtain the independent D3 falsification/acceptance described in Section 9.
11. Close/archive only after all impact items are resolved.

Still-valid prior scientific evidence may be reused with an explicit applicability rationale. Do not reuse old scheduler/resource evidence as current confirmation after the owners above change; rerun the relevant specifications against the final candidate.

## 9. Documentation, authority, dependency, and history closure

Current/proposed documentation must agree with final executable semantics:

- `campaign.toml.example` and generated/default configuration comments;
- `mdstats/training_data/training_parallel.py` comments/docstrings;
- P5 execution/performance Architecture Manual material;
- README/user-facing scheduler documentation;
- `docs/history/mlff/train2_admission_evolution.md` and its history index;
- generated Architecture Manual PDF/manifest where the repository requires regeneration.

Required semantic reconciliation:

- remove any implication that TRAIN2 must launch one CUDA job when one is infeasible;
- state that `training_gpu_memory_fraction` is the TRAIN2 admission/live safety envelope for this architecture, not merely a promotion preference;
- state that GPU-utilization saturation remains soft replacement throttling while persistent TRAIN2 VRAM-envelope violation is terminal;
- preserve the distinct EVAL2/inference controller contract; do not mechanically apply TRAIN2 zero-safe/live-hazard semantics to inference;
- record the new fail-wave-before-EVAL rule and why authenticated TRAIN2 summaries, rather than same-invocation sibling EVAL2, are the restart/progress-preservation boundary;
- remove/document no operator-facing `parallel_training_memory_hazard_grace_seconds` key because this plan deliberately removes that public surface.

Because this cycle changes durable D3 resource semantics, branch-local Architecture Manual edits remain **proposed** until an independent falsification pass by a reviewer/context that did not author the D3 proposal accepts them. That reviewer must reconstruct the relevant historical scheduler authority and specifically challenge:

1. zero-safe admission;
2. the use of the existing `training_gpu_memory_fraction` as the TRAIN2 live safety envelope;
3. the bounded transient/missing-observation behavior;
4. whole-TRAIN-wave cancellation on sustained memory-safety failure;
5. TRAIN-wave failure terminating before EVAL2;
6. continued separation from EVAL2/inference serial-floor semantics;
7. absence of D1/D2 method changes.

If that independent review does not accept the durable D3 mutation, do not merge the proposed Architecture Manual semantics as accepted-current and do not close this workplan.

## 10. Reopen, Serious Challenge, and simplification triggers

Remain within this workplan for:

- parent accelerator/model retention;
- zero-safe resource-floor logic;
- TRAIN scheduler phase ownership;
- live-memory safety/debounce and runtime observability loss;
- ordinary process/cancellation lifetime;
- TRAIN-wave failure transition;
- execution-only resource observability/estimation;
- documentation/configuration reconciliation required by these changes.

Reopen the smallest existing process-supervision surface if target-host attribution proves an owned orphan/stale child is contributing baseline VRAM.

Reopen D3/D2 method/device compatibility only if the clean exact-method R5-B realization shows that the frozen method itself cannot safely execute on the supported device without changing scientific/numerical semantics.

Raise a Serious Challenge only if evidence shows accepted D1/D2 authority or simultaneous D3 constraints are materially contradictory, false, ambiguous enough to admit materially incompatible semantics, or impossible to concretize. No such evidence exists at this workplan review.

If implementation attempts to solve these blockers by adding a scheduler, persistent resource authority, OOM parser, retry database, new public safety knob, scientific fallback, or other compensating machinery, stop and re-derive against the simpler existing controller/scheduler/cancellation/continuation owners before accepting it.

## 11. Final impact closure and PASS criteria

PASS requires all of the following on one final semantic candidate with no later material executable mutation:

- R1-R4 implemented by reduction/alteration of existing owners;
- R5-A and R5-B target-host evidence complete or an explicit upstream reopen triggered by R5-B failure;
- temporary P5 architecture classification leaves no model-scale accelerator residue on the real MACE/CuEq path;
- zero-safe TRAIN admission remains end-to-end;
- one unsafe sample blocks admission and persistent over-envelope VRAM becomes terminal for any positive active-job count;
- runtime memory-observability loss cannot silently permit indefinite active TRAIN2 execution;
- no EVAL2 begins after any failed TRAIN2 wave in the same invocation;
- successful TRAIN waves still transition to serial EVAL2 and resume correctly from authenticated TRAIN2 summaries;
- owned children are reaped before failed scheduler return and no orphan GPU workers remain;
- no D1/D2 method identity or numerical behavior changed;
- failure diagnostics, scheduler counts, cancellation, restart, currentness, and publication remain truthful;
- complete affected regression/integration and repository-required checks pass on the final candidate;
- affected evidence applicability is reconciled;
- affected documentation/history/configuration/generated artifacts agree with implementation;
- independent D3 falsification accepts the proposed durable Architecture Manual mutation;
- workplan/archive closeout occurs only after the accepted semantics are represented by current canonical authority.

A production run that happens to survive because more VRAM was free is not closure. A high-baseline zero-safe rejection is necessary admission evidence but does not replace clean single-job characterization. A planner-only unit test cannot close scheduler cancellation/restart/publication. A cyclic CUDA tensor fixture cannot replace the real MACE/CuEq lifetime gate. An old green test run cannot close a changed candidate.

Until all of these conditions close, the implementation remains **NO-PASS** even though this second-pass workplan design review is complete.