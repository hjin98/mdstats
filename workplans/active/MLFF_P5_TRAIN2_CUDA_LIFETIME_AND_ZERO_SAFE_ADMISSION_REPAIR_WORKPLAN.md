---
kind: implementation-workplan
workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION
protocol_version: 6.1.0
status: ready-for-implementation
target_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
baseline_commit: d2d9051b56d83bcae18db71452c363276c118e3f
highest_affected_domain: D3 software architecture -> D4 implementation
serious_challenge: none
trigger: target-host P5 cross-validation CUDA OOM after scheduler restoration
predecessor_context: archived MLFF P5 replay/MACE execution-recovery work
---

# MLFF P5 TRAIN2 CUDA lifetime, zero-safe admission, and phase-ownership repair

## Background and terminology

The **Scientific Software Development Protocol (SSDP)** governs this workplan under Protocol 6.1. The highest materially affected domain is D3 software architecture because the current accepted execution rule that CUDA training always starts with one job is disproven by target-host resource evidence. The D4 implementation must concretize the corrected resource architecture without altering D1 scientific meaning or D2 numerical/training-method semantics.

**Video random-access memory (VRAM)** is accelerator memory visible to CUDA workloads. **Out of memory (OOM)** means an accelerator allocation cannot be satisfied. **TRAIN2** is the current authenticated MACE training execution path. **EVAL2** is the current authenticated checkpoint/model evaluation path. **CuEq** is the cuequivariance-backed transient MACE execution representation used by the configured training backend.

A **baseline** is accelerator memory already occupied before a new training job is admitted. It may belong to the current mdstats process, an owned child, an unrelated process, or the accelerator/runtime itself. A **zero-safe-admission state** means pending work exists but no new training job can presently fit inside the governing resource envelope. Zero safe admission is not equivalent to zero work, CUDA unavailability, or queue completion.

## 1. Target outcome, governing authority, and non-goals

### Stakeholder/product outcome

Repair post-selection cross-validation and final-production execution so that:

1. temporary parent-process MACE/CuEq objects do not retain accelerator memory after their final consumer;
2. the training scheduler can truthfully represent zero currently safe training jobs;
3. CUDA memory safety is evaluated independently of optimizer-activity readiness;
4. TRAIN2 concurrency does not accidentally authorize overlapping post-TRAIN EVAL2 accelerator ownership;
5. an intrinsically too-large scientific training method fails explicitly rather than silently changing batch size, precision, backend, replay membership, or another scientific parameter.

### Accepted D3 architecture being reconsidered narrowly

The current execution architecture states that CUDA training begins with one job and adapts upward. Target-host evidence establishes a counterexample: current aggregate occupancy can leave insufficient safe headroom for even the first configured training job. The cycle-scoped corrected architecture is therefore:

> CUDA starts with one TRAIN2 job only when one job is currently resource-admissible. Zero safe admission is a valid execution state.

This workplan does not silently promote every implementation mechanism below that statement into durable D3 authority. Durable Architecture Manual updates require the normal independent D3 falsification/acceptance path.

### Applicable D1/D2 invariants preserved

The repair must not change:

- any frozen selected size or exact `T_selected` membership;
- cross-validation folds, purge/exclusion relationships, seeds, or horizons;
- replay training membership or independent TRUE_DFT replay-monitor membership;
- target/replay head semantics;
- loss coefficients or per-head weighting;
- optimizer family or optimizer-state semantics;
- `batch_size=2` or validation batch size;
- learning-rate schedule;
- exponential moving average (EMA);
- AMSGrad, weight decay, or clipping;
- model dtype/precision policy;
- configured training backend;
- checkpoint-selection or EVAL2 metric semantics;
- target-only fold acceptance;
- fresh final-production semantics.

An OOM is not authority to halve batch size, change gradient accumulation, switch CuEq to e3nn, change precision, reduce replay membership, or alter model architecture. Any such change must be routed to its real D2/D3 owner.

### Explicit non-goals

Do not:

- increase the 90% training VRAM fraction merely to hide the defect;
- hard-code the observed ~19-20 GiB as a new per-job estimate from the contaminated run;
- globally call `torch.cuda.empty_cache()` repeatedly during ordinary training;
- introduce a second scheduler, resource database, persistent GPU lease registry, recovery state machine, or model representation;
- delete valid checkpoints merely to avoid the historical-classification path;
- globally serialize unrelated inference paths;
- redesign target-size selection, CV science, replay science, or final-production authorization.

## 2. Governing runtime evidence and diagnosis

### E1 - the failing run had one active training job

The supplied target-host run reports five CV training runs, `target_jobs=1`, `ceiling=1`, and one active job throughout the failure. The OOM occurs before any fold completes, so concurrent sibling EVAL2 execution is not required to explain this specific failure.

### E2 - the GPU was already near the configured envelope before TRAIN2 launch

Before the first training future was submitted, scheduler telemetry reported approximately:

```text
device total                 24.0 GiB
configured training ceiling  21.6 GiB
pre-launch occupied          20.2 GiB
safe envelope remaining       1.4 GiB
configured job estimate       6.0 GiB
```

The existing planner nevertheless produced `initial=1, ceiling=1`.

### E3 - the current planner manufactures a one-job floor

Current `build_training_concurrency_plan()` computes a GPU process limit, then applies a minimum of one even when the resource calculation produces zero. It later forces final maximum concurrency to at least one. The P5 submission loop independently floors the controller target to one. A zero-safe resource state therefore cannot propagate to execution.

### E4 - memory safety is currently subordinated to optimizer-readiness calibration

The target-host run exceeded the configured 21.6 GiB memory envelope during initialization/validation, before true optimizer activity, yet scheduler decisions remained focused on waiting for true-epoch compute and averaging true-epoch telemetry. True optimizer activity is a valid prerequisite for estimating scalable training demand and promoting concurrency above one. It is not a prerequisite for recognizing a hard memory hazard.

### E5 - actual failure is TRAIN2 CuEq backward

The supplied failure occurs after approximately 2,411 optimizer updates in epoch 0 at `loss.backward()`, inside `cuequivariance.uniform_1d` backward, when CUDA requests another roughly 646 MiB allocation. The configured training batch size is two. Because the failure occurs well into the shuffled epoch, initialization or a handful of early batches cannot prove worst-case batch/graph feasibility.

### E6 - P5 recovery/preflight can itself realize a CUDA training model

Before authoritative training admission, P5 recovery logic can call `_post_selection_current_training_architecture()`. That helper builds a portable MACE model, realizes the configured CuEq/OEq training model on the configured device, computes an architecture digest, and returns without an explicit accelerator-retirement boundary. This is a likely source of parent-process baseline contamination and is independently inconsistent with explicit accelerator lifetime ownership even if target-host attribution later shows the 20.2 GiB baseline had multiple owners.

### E7 - cross-fold phase ownership remains a latent sibling defect

The adaptive training scheduler currently submits `execute_post_selection_run()` as a future. That future spans materialization, TRAIN2, checkpoint authentication, candidate EVAL2, replay/foundation EVAL2, outer evaluation, and publication. Therefore, when concurrency exceeds one on a clean GPU, a completed fold may enter EVAL2 while another TRAIN2 child remains active. This did not cause the supplied OOM, but it is inconsistent with a scheduler whose resource model is specifically a training-job model and should be closed in the same shared-owner repair.

## 3. Cycle-scoped D3 decisions and delegated D4 concretization

### Cycle-scoped decisions

1. TRAIN2 admission may resolve to zero currently safe jobs.
2. A configured minimum training concurrency is subordinate to current resource feasibility.
3. Positive `parallel_training_jobs` is a maximum cap, never permission to bypass admission.
4. Current aggregate GPU occupancy counts regardless of process ownership.
5. GPU memory safety is evaluated independently of true-epoch/optimizer calibration readiness.
6. TRAIN2 adaptive concurrency owns TRAIN2 lifecycle only; post-TRAIN EVAL2 must not inherit a TRAIN scheduler slot merely because the outer fold future remains live.
7. Actual scientific method changes are forbidden as an implicit OOM fallback.

### Delegated D4 concretization

Implementation may choose equivalent local mechanisms for:

- exact helper boundaries used to retire temporary architecture models;
- internal representation of zero-safe plans;
- controller decision/status record details;
- bounded debounce of transient VRAM spikes;
- exact factoring of the TRAIN2-only orchestration boundary;
- test factoring and deterministic resource fixtures.

Do not freeze replaceable helper names or local data structures unless required by an existing supported contract.

### Active simplification

Prefer rewiring and narrowing current machinery:

- remove hard `max(1, ...)` resource floors where they counterfeit feasibility;
- narrow the training scheduler future from whole-fold lifetime to the existing TRAIN2 completion boundary;
- reuse existing provider/model cleanup semantics instead of adding another lifetime subsystem;
- reuse authenticated TRAIN2 summary/continuation as the post-training durable boundary instead of inventing a handoff record.

## 4. Implementation obligations and gates

### G0 - bind the observed failure and attribute the pre-launch baseline

Before semantic repair, establish the execution ordering on the current target-host path.

Capture, without deleting valid restart evidence:

1. GPU occupancy immediately before P5 recovery preflight;
2. GPU occupancy immediately after recovery preflight;
3. GPU occupancy at authoritative TRAIN admission;
4. whether `_post_selection_current_training_architecture()` ran;
5. process/PID attribution where available.

Classify the baseline as current mdstats parent, owned orphan/stale mdstats child, unrelated external process, mixed, or unknown.

Process attribution is diagnostic. Aggregate occupancy remains authoritative for admission.

If an owned orphan is found, reopen only the existing process-lifetime/cancellation surface needed to fix it. Never kill or commandeer an unrelated process.

### G1 - close temporary architecture-realization lifetime

Repair `_post_selection_current_training_architecture()` at its natural ownership boundary.

Required end state:

- temporary portable and CuEq/OEq models are exception-safely retired immediately after the digest is computed;
- no model-scale accelerator allocation remains owned by that helper;
- reuse the existing synchronization/garbage-collection/unused-cache-release semantics already established for MACE provider retirement where applicable;
- do not create a provider merely to obtain cleanup;
- do not create a persistent architecture cache as a workaround.

Preferred concretization is direct deterministic lifetime cleanup, such as `try/finally`, around the temporary realization. A different isolation mechanism requires evidence that direct retirement is insufficient for the third-party conversion path.

Acceptance:

- repeated architecture-classification calls do not monotonically increase GPU residency;
- post-call occupancy returns to the pre-call allocator/context baseline within a bounded justified CUDA-context tolerance;
- cleanup occurs on conversion/digest exception paths;
- the resulting architecture digest remains semantically identical.

### G2 - make zero-safe TRAIN admission representable

Repair `TrainingConcurrencyPlan`, planner, controller, and P5 submission semantics so nonempty work may legitimately produce zero admissible jobs.

Remove semantic one-job floors from hard RAM/VRAM feasibility.

Interpret `minimum_parallel_training_jobs=1` as:

> once at least one job is resource-feasible, automatic operation does not voluntarily target less than one.

It must not mean:

> launch one regardless of resource feasibility.

Close the same hard-memory floor for host RAM where the current planner would otherwise manufacture one feasible process from zero memory capacity. Do not broaden this into unrelated CPU worker redesign.

### G3 - define trustworthy initial GPU admission

For CUDA TRAIN admission, use existing authorities in this order:

1. current aggregate GPU memory telemetry when available;
2. existing `SystemResourceSnapshot` current free/total GPU memory as a memory-only fallback;
3. if no trustworthy current memory observation exists, block automatic TRAIN admission with a typed resource-observability error.

Device availability and telemetry availability are separate facts.

If utilization telemetry is unavailable but current memory capacity is known, one memory-safe serial job may execute, but no parallel promotion is authorized until required utilization evidence exists.

For one proposed job:

```text
current baseline
+ conservative configured/observed job reservation
<= configured training VRAM envelope
```

must hold before launch.

The observed 20.2 GiB baseline plus 6 GiB configured job estimate under a 21.6 GiB ceiling must resolve to zero admissible jobs.

Do not change the 90% default to make this case pass.

### G4 - decouple memory safety from true-epoch readiness

Preserve true optimizer/epoch activity as the prerequisite for estimating scalable utilization and promoting concurrency above one.

Evaluate memory safety on every trustworthy sample regardless of child phase.

The controller/supervisor must distinguish:

- promotion readiness;
- memory safety;
- child liveness.

Initialization or validation above the configured memory safety envelope must not be reported merely as waiting for true epoch compute.

A sustained or unequivocal unsafe memory condition during initial calibration must stop the owned execution through existing child termination/failure semantics instead of knowingly continuing toward CUDA OOM. Exact debounce mechanics are delegated, but the supplied case, which remains above the envelope for minutes, must not survive until the eventual allocation failure.

GPU utilization remains an expansion signal, not a memory kill criterion.

### G5 - separate TRAIN scheduler lifetime from EVAL2 lifetime

Correct `_execute_post_selection_pending_runs()` so one training scheduler slot corresponds to TRAIN2 ownership rather than the complete fold lifecycle.

Preferred minimum-complexity realization:

1. factor/reuse the existing run path through authenticated TRAIN2-summary completion;
2. schedule only that training-completion portion concurrently;
3. retain the already durable TRAIN2 summary/materialization;
4. after TRAIN scheduling releases accelerator ownership, invoke the existing run path to complete EVAL2;
5. existing fully-completed continuation logic skips redundant training.

No new persistent handoff record is permitted; the authenticated TRAIN2 summary is already the durable boundary.

Post-training EVAL2 should remain serial/non-overlapping by default under this repair. Future EVAL throughput optimization belongs to the existing inference-admission owner, not a second P5 scheduler.

Acceptance:

- a fold entering EVAL2 cannot overlap an independently admitted TRAIN2 child;
- sibling EVAL providers cannot coexist merely because multiple TRAIN futures completed;
- scheduler VRAM calibration samples describe TRAIN2 rather than mixed TRAIN/EVAL phases;
- completion order cannot alter canonical CV reduction;
- completed TRAIN2 work survives interruption before EVAL2.

### G6 - characterize clean-baseline single-job demand before changing method

After G1-G5, run one exact current-method CUDA TRAIN2 job from a clean/admissible baseline.

Do not use the contaminated 20.2 GiB observation to redefine the per-job estimate.

Observe, where economical and without altering scientific execution:

- post-cleanup baseline;
- aggregate peak/high-water VRAM;
- process-local PyTorch allocated/reserved high-water;
- materially relevant non-PyTorch/device occupancy;
- active training phase;
- high-water/failing batch identity;
- atom count and graph/edge footprint of high-demand batches;
- target versus replay head/source role when relevant.

Because the supplied OOM occurs well into epoch 0, do not infer safety solely from initialization or a handful of early batches.

If the exact isolated job fits safely, measured incremental demand may update execution-only admission evidence. It does not enter scientific identity.

If the isolated exact job still OOMs or persistently requires more than the supported safety envelope, stop D4 repair and invoke the D2/D3 method/device compatibility reopen rule in Section 8.

### G7 - failure, cancellation, and restart behavior

For resource-admission failure or actual OOM:

- stop admitting new work immediately;
- cancel/reap owned children through existing process-group semantics;
- do not retry the same profile by silently mutating batch/backend/precision;
- preserve authenticated completed sibling and continuation evidence;
- derive pending work on rerun from existing P5 authority;
- publish no partial CV acceptance or final-production publication.

An idle queue with pending work and zero feasible slots must fail explicitly rather than busy-loop.

### G8 - diagnostics and progress truthfulness

Scheduler diagnostics must distinguish:

- baseline occupancy;
- configured VRAM envelope;
- available headroom;
- per-job configured/observed reservation;
- zero-safe admission;
- waiting because active work consumes capacity;
- unavailable utilization telemetry;
- unavailable memory observability;
- actual CUDA OOM;
- resource stop before OOM.

Fix the observed failure-report inconsistency where, after the first run fails and is removed from `active`, `pending_jobs` is reported as five again. Report queued, active, completed, and failed counts from actual scheduler ownership rather than a derived formula that can count an already-submitted failed slot as pending.

Diagnostics are not scientific or completion authority.

### G9 - focused and affected acceptance

At minimum add/update evidence for:

1. 24 GiB GPU, 20.2 GiB baseline, 90% ceiling, 6 GiB estimate -> zero jobs and no launch;
2. safe low baseline -> ordinary one-job startup;
3. safe measured workload -> adaptive promotion remains possible;
4. positive configured job cap cannot override zero-safe admission;
5. insufficient host RAM -> zero safe training jobs rather than forced one;
6. active jobs consuming capacity -> wait/re-evaluate rather than terminal idle-zero failure;
7. idle pending queue + zero feasible jobs -> typed failure without spin;
8. GPU memory hazard is detected before true-epoch readiness;
9. unavailable utilization telemetry + known memory capacity -> conservative serial/no promotion;
10. unavailable trustworthy memory capacity -> no automatic TRAIN launch;
11. repeated temporary CuEq architecture reconstruction has bounded post-cleanup residency;
12. cleanup executes on exception;
13. architecture digest semantics are unchanged by lifetime cleanup;
14. TRAIN scheduler future ends at TRAIN2-summary ownership;
15. EVAL2 cannot overlap sibling TRAIN2 under the repaired P5 path;
16. completed TRAIN2 state is reused after interruption before EVAL2;
17. actual child OOM cancels/reaps owned siblings and preserves restartable state;
18. scheduler failure reporting counts failed/queued work truthfully;
19. CV scientific identities/results are invariant to the resource-control repair;
20. final-production uses the same corrected TRAIN admission owner.

Retain applicable current scheduler, replay, TRAIN2 architecture, P5 R7-R11, multi-size, currentness, recovery, cancellation, provider-lifetime, and downstream integration suites.

Acceptance must exercise the real planner/controller/orchestration owner. Resource probes and expensive MACE execution may be bounded/faked below the owner where the claim is scheduler semantics. A planner-only unit test cannot close end-to-end admission or recovery behavior.

### G10 - documentation and semantic-evolution closure

Update current documentation that states or implies `CUDA always starts with one job` to the corrected invariant:

> CUDA starts with one training job only when one job is currently resource-admissible; zero safe admission is a valid execution state.

Inspect/update as applicable:

- `campaign.toml.example`;
- `mdstats/training_data/training_parallel.py` comments/docstrings;
- P5 execution/performance Architecture Manual material;
- user-facing scheduler documentation;
- generated/default configuration comments.

Preserve the distinct EVAL2/inference serial-floor contract. Do not mechanically apply TRAIN2 zero-safe semantics to inference, whose accepted calibration rules have a different owner and history.

Record concise semantic-evolution rationale explaining that target-host evidence invalidated the former unconditional one-TRAIN-job floor.

## 5. Evidence specifications, realizations, and dependencies

### Evidence target versus execution dependency

The main governed propositions are:

- unsafe initial VRAM state cannot force-launch TRAIN2;
- temporary architecture classification releases its accelerator resources;
- TRAIN scheduler resource observations describe TRAIN2 ownership only;
- failure/cancellation/restart remains correct;
- scientific identities and numerical method remain unchanged.

Execution dependencies include PyTorch, MACE 0.3.16, cuequivariance/CuEq, CUDA/NVML or equivalent resource probes, target-host GPU capacity, and the current P5 continuation/recovery machinery. They are evidence dependencies, not new scientific authority.

### Evidence applicability

Prior D1/D2 scientific evidence remains admissible because this workplan forbids method changes.

Prior D4 tests touching training scheduler admission, resource floors, scheduler lifetime, architecture-realization cleanup, failure counts, and TRAIN/EVAL overlap are review-required and must be rerun/remapped against the assembled candidate.

Provider-lifetime evidence unrelated to the newly temporary architecture-realization owner may remain reusable where inspection proves the claim is unaffected, but final assembled affected regression remains fresh.

The supplied OOM trace is admissible evidence against the former unconditional one-job D3 rule for the observed 24 GiB environment. It is not proof of the clean isolated per-job VRAM requirement because the pre-launch baseline was already heavily occupied.

## 6. Expected affected surface

Primary production surface:

- `mdstats/training_data/campaign_post_selection_runtime.py`
- `mdstats/training_data/training_parallel.py`

Likely supporting surface:

- `mdstats/training_data/model_features.py` only if existing accelerator-retirement semantics need factoring/reuse;
- configuration/default comments in `_campaign_cli_core.py` and `campaign.toml.example`;
- P5 execution/performance architecture and user documentation.

Expected tests include:

- `tests/test_mlff_training_parallel_scheduler.py`;
- current P5 replay/MACE execution-recovery tests;
- P5 R7-R11 guards;
- TRAIN2 execution/continuation tests;
- multi-size CV/final-production tests;
- provider-lifetime and downstream integration tests.

This list is provisional. Re-derive the complete affected surface from the final assembled candidate before closure.

## 7. Stage dependency order and evidence reuse

Execute in this dependency order unless implementation evidence proves an equivalent simpler ordering:

1. G0 baseline attribution and current-path binding;
2. G1 temporary-model lifetime cleanup;
3. G2-G4 zero-safe planning/admission and phase-independent memory safety;
4. G5 TRAIN/EVAL ownership narrowing;
5. G6 clean-baseline exact-method characterization;
6. G7-G8 failure/restart/diagnostic closure;
7. G9 final affected regression/integration;
8. G10 documentation/history/impact closure.

Do not optimize MACE internals before removing parent-side contamination and correcting admission ownership. Otherwise an intrinsic-memory investigation can merely compensate for a scheduler/lifetime defect.

Full production GPU performance qualification remains deferred to release closeout. This workplan requires only bounded target-host GPU evidence necessary to close this concrete OOM/resource-safety defect.

## 8. Reopen, Serious Challenge, and simplification triggers

### D4/D3 resource-concretization work that stays within this plan

Remain within this plan for:

- parent allocator/model retention;
- resource-floor logic;
- scheduler phase ownership;
- missing live-memory guard;
- ordinary process/cancellation lifetime;
- execution-only workload estimation.

### D3/D2 method/device compatibility reopen

Stop implementation and return to Design if, after parent cleanup and correct isolated admission, the exact frozen training method itself cannot safely execute on the target device.

Examples:

- exact `batch_size=2` current method still OOMs on a clean 24 GiB target device;
- exact CuEq backward representation intrinsically exceeds available VRAM for admissible batches;
- fixing the problem requires batch semantics, precision, optimizer accumulation, replay exposure, model architecture, or numerically consequential backend changes.

Do not bless such a change as a memory optimization.

### External-baseline case

If G0 proves the original 20.2 GiB belongs entirely to an unrelated process, the zero-safe admission repair remains required. No mdstats cleanup code may terminate the unrelated owner.

### Owned-orphan case

If G0 proves baseline occupancy belongs to an mdstats child that should already have been reaped, reopen the smallest existing process-supervision/lifetime surface and close that defect before final acceptance.

### Serious Challenge condition

No Serious Challenge is currently active. Raise one only if evidence shows accepted D1/D2 authority or simultaneous D3 constraints are materially contradictory, false, or impossible to concretize. Do not convert an ordinary resource implementation defect into upstream challenge merely because it manifests as OOM.

## 9. Impact closure and final acceptance

PASS requires all of the following:

- temporary P5 architecture classification leaves no model-scale accelerator residue;
- zero-safe TRAIN admission is representable end to end;
- the observed 20.2 GiB-baseline case launches zero jobs under the same 90%/6 GiB policy;
- safe low-baseline operation still launches and can adapt upward;
- memory safety no longer waits for true-epoch readiness;
- TRAIN2 and EVAL2 accelerator ownership cannot accidentally overlap through one fold future;
- no scientific/method identity changes occurred;
- restart/currentness behavior remains exact;
- failure diagnostics and scheduler counts are truthful;
- complete affected regression/integration passes on the assembled candidate;
- affected documentation and semantic-evolution history agree with the corrected architecture.

The bounded target-host CUDA acceptance must finally demonstrate either:

```text
clean baseline
 -> one admitted exact TRAIN2 job
 -> bounded VRAM
 -> no parent-preflight residue
 -> no OOM
 -> normal checkpoint/restart behavior
```

or a clean typed resource rejection before unsafe work is launched.

A run that survives only because the GPU happens to have more free memory is not closure.

Before closing the workplan, account for every materially affected descendant, evidence specification/realization, documentation/current dependency record, cleanup action, and history update. Preserve unaffected prior evidence only with an explicit applicability rationale; stale passing evidence cannot close the current candidate.
