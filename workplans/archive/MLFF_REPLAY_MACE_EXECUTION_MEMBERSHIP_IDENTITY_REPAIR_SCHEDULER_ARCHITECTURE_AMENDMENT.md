---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-SCHEDULER-ARCHITECTURE-RECOVERY-1
parent_workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR
parent_review_amendment_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-REVIEW-REOPEN-1
progress_amendment_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-PROGRESS-RECOVERY-1
protocol_version: 6.0.0
status: active
created_date: 2026-09-09
runtime_evidence_date: 2026-09-09
highest_affected_domain: D4 execution realization under unchanged D3 P5/TRAIN2/MACE and acceleration architecture
serious_challenge: none
precedence: this amendment extends the active repair with scheduler recovery and checkpoint-architecture parity; all non-conflicting parent/review/progress requirements remain binding
---

# P5 adaptive TRAIN scheduling + TRAIN2/EVAL2 architecture-parity amendment

## 0. Trigger and verdict

A target-host `cross-validate` run supplied two further pieces of execution evidence.

First, the long silent interval was proven to be live MACE work, and repository history showed that both the live TRAIN reporter and adaptive GPU-utilization scheduler had existed before the V7 public-lifecycle cutover. The reporter recovery is already frozen by the progress amendment. This amendment adds the sibling scheduler recovery and requires both facilities to serve the current P5 public consumers: `cross-validate` and `train-production`.

Second, after a long real training run completed, P5 failed before candidate evaluation with:

```text
TrainingDataInputError: Candidate MACE configuration reconstructs a different execution architecture from the authenticated TRAIN2 model.
```

That exception comes from the correct fail-closed TRAIN2/EVAL2 checkpoint-authentication boundary. Do not weaken or remove it. The repair must make training realization, checkpoint state, and reconstruction agree under the already accepted acceleration/model architecture.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, target-size/CV science, replay science, and accepted D3 P5 architecture remain unchanged. This is a bounded D4 execution-control and architecture-realization repair.

---

## 1. Historical scheduler authority to recover

### 1.1 Surviving canonical implementation

`mdstats.training_data.training_parallel` still contains the qualified scheduler machinery:

- `TrainingConcurrencyPolicy`;
- `build_training_concurrency_plan()`;
- `AdaptiveTrainingConcurrency`;
- persistent NVML telemetry with `nvidia-smi` fallback;
- CPU/RAM/VRAM/GPU-utilization admission bounds.

Current policy behavior includes:

```text
auto CUDA scheduling starts with one real training job
 -> require true optimizer/epoch activity
 -> observe a fixed telemetry window
 -> project aggregate VRAM and GPU utilization
 -> add at most one job when both remain below their ceilings
 -> repeat up to the resource/configured cap
```

Default/current generated controls remain approximately:

```text
parallel_training_jobs = 0              # adaptive auto
minimum_parallel_training_jobs = 1
maximum_parallel_training_jobs = 4
training_gpu_memory_fraction = 0.90
training_gpu_utilization_fraction = 0.90
estimated_training_vram_mib_per_job = 6144
estimated_training_ram_mib_per_job = 8192
parallel_training_epoch_stabilization_seconds = 60
parallel_training_epoch_stability_samples = 12
parallel_training_monitor_interval_seconds = 10
training_progress_interval_seconds = 10
```

The surviving scheduler regression suite already proves one-job startup, true-epoch gating, utilization/VRAM projection, incremental promotion, saturation throttling, fluctuation averaging, and CPU-serial behavior.

### 1.2 V7 wiring regression

Current campaign orchestration still imports the training scheduler types but the current V7/P5 execution path no longer constructs a training concurrency plan or `AdaptiveTrainingConcurrency`. `execute_post_selection_cross_validation()` and final-production orchestration invoke `MacePostSelectionTrainer` serially instead.

Therefore the scheduler was not superseded scientifically; its **consumer wiring was lost** while its implementation, configuration, and tests survived.

Do not create a second scheduler. Restore the existing owner into the current P5 orchestration.

---

## 2. Scheduler requirements for both P5 public paths

### S1 — one shared P5 training admission owner

Both current public commands must consume the same scheduler realization:

```text
cross-validate
 -> required (N_selected, CV seed, fold) training jobs
 -> existing adaptive TRAIN scheduler

train-production
 -> required (N_selected, production seed/member) training jobs
 -> same existing adaptive TRAIN scheduler
```

The scheduler controls **resource admission only**. It owns no CV membership, target/replay membership, horizon, seed policy, checkpoint selection, acceptance, production membership, or publication decision.

Prefer rewiring/refactoring the former generic TRAIN scheduling/supervision capability into the existing P5 owner boundary. Do not add `PostSelectionSchedulerV2`, another persistent queue, another scheduler database, or another process wrapper merely because the public command names changed.

### S2 — deterministic scientific reduction despite concurrent completion

Concurrency may change wall-clock completion order only.

- Every required run identity is constructed from existing frozen P5 authority before scheduling.
- Completion order never becomes CV or production ordering authority.
- CV reduction consumes evidence in the canonical plan order and still requires every required run.
- Final-production publication consumes the existing frozen member order/committee policy.
- A restored completed run counts once and is never relaunched solely to fill scheduler capacity.
- No concurrent duplicate of one run identity may launch.

### S3 — adaptive CUDA admission semantics

On CUDA auto mode, preserve the surviving historical policy:

1. start with one job;
2. do not infer capacity from initialization/graph-build/validation idleness;
3. require each active job to demonstrate true optimizer/epoch activity through the same live progress owner used by the reporter;
4. collect the configured fixed-duration telemetry window;
5. project aggregate VRAM and GPU utilization for one additional job;
6. admit one additional job only when both projected quantities remain strictly within their configured budgets and host CPU/RAM limits permit it;
7. repeat until the measured/configured cap;
8. when sustained post-add saturation is observed, throttle future replacement/admission according to the existing controller semantics.

A positive `parallel_training_jobs` remains a maximum cap, not permission to bypass resource admission. CPU remains serial unless a separately accepted policy already says otherwise.

### S4 — scheduler and reporter share live observations

The progress amendment recovers the supervised child metrics probe. The scheduler should consume the same per-child state for:

- child liveness;
- true optimizer/epoch activity;
- completed gradient updates;
- current phase.

GPU telemetry should likewise be sampled once per scheduler/control interval and reused for scheduler decisions and user-visible telemetry where practical. Do not create one NVML poller for scheduling and a second independent poller for reporting when the same sample can serve both.

The presentation cadence and scheduler-control cadence may differ; reporting must not change admission decisions.

### S5 — failure, interruption, and resource-stop behavior

Reuse the historical owned-child supervision semantics:

- stop admitting new work after a hard failure/interruption/resource stop;
- terminate/reap owned children according to the existing graceful-stop policy;
- preserve already-authenticated restart evidence;
- do not leave orphan GPU workers;
- rederive pending work from current P5 authority on rerun rather than persisting a second queue authority.

Existing P5 hard-failure semantics remain fail-fast at the public operation. In-flight cancellation mechanics are D4-delegated but may not publish partial CV acceptance or partial final production.

### S6 — scheduler visibility

Recover the historical `[TRAIN scheduler]` presentation using the canonical progress grammar. A heartbeat should expose, when applicable:

```text
status
progress completed/total
elapsed
eta
active jobs
true_epoch active/active
admission target/cap
queued/pending
last admission decision/reason
GPU utilization
VRAM use/budget
```

CV and final production must also retain their outer N/seed/fold/member context from the progress amendment.

---

## 3. Architecture-mismatch diagnosis and governing invariant

### 3.1 Keep the current fail-closed check

`authenticate_train2_checkpoint_provider()` independently reconstructs a MACE model from the authenticated candidate/P5 configuration and compares its canonical execution-architecture digest with `Train2RuntimeSummary.model_architecture_digest` before applying checkpoint state. This is an important defense against loading a syntactically valid state dictionary into a different model topology.

The new target-host exception is evidence that the two model-construction paths differ. The check is the messenger, not the bug.

### 3.2 High-confidence phase-separated CuEq drift

The current acceleration architecture supports:

```text
source / evaluation / deployment representation = portable e3nn
TRAIN2 execution backend                        = configured training backend (commonly CuEq)
only_cueq = false                               = portable e3nn checkpoints/products remain required
```

Pinned MACE 0.3.16 constructs an e3nn model and, when `enable_cueq=True` and `only_cueq=False`, converts that live model to CuEq **before optimizer/training execution**. It converts a copy back to e3nn only when producing its portable saved model.

TRAIN2 currently computes `model_architecture_digest` from the **live model object** it is training. Therefore, under phase-separated CuEq training, the summary naturally authenticates the transient CuEq model structure. `build_mace_model_from_configuration()` reconstructs the portable e3nn configuration and does not apply the training-backend conversion before the comparison. Comparing those two representations as if they were the same architecture can produce exactly the observed exception.

This is a representation/realization mismatch under an already accepted acceleration policy, not authority to disable the architecture guard or silently switch training to e3nn.

### 3.3 Independent model-affecting P5 drift to census: average neighbors

Pinned MACE also resolves `args.avg_num_neighbors = get_avg_num_neighbors(...)` immediately before `configure_model()`. Unless at least one head supplies an explicit non-recomputed value, MACE computes it from the actual training loader. The value is model-affecting and is included in mdstats's canonical execution-architecture descriptor.

The current P5 `_post_selection_mace_config()` does not itself emit `compute_avg_num_neighbors=False`. Current P5 reconstruction, however, sets `args.avg_num_neighbors` from the frozen `mace_architecture`. This creates a second possible source of the same exception and, more importantly, could make one fold train a different model normalization from another.

The earlier P3 architecture repair already established the governing principle: model-affecting normalization owned by frozen/common method authority must not be silently recomputed from candidate-local training membership.

### 3.4 Required construction census before final patch

Before changing the guard, compare actual TRAIN2 construction with independent reconstruction for every field represented by `mace_model_execution_architecture_digest`, emphasizing:

- portable e3nn versus transient CuEq/OEq realization;
- exact model class/modules after accelerator conversion;
- P5 head set and order (`pt_head`, `target_head`, ordinary `Default` where legal);
- foundation-head selection/removal;
- `r_max` and other architecture values inherited/mutated by foundation fine tuning;
- atomic-number table/order;
- `avg_num_neighbors` and `compute_avg_num_neighbors` behavior;
- interaction/product/readout/correlation structure;
- dtype;
- architecture-derived buffers.

Use one bounded real P5 configuration and record a field-level/digest-level comparison. Do not patch the first differing field and stop without proving the complete owner relation.

---

## 4. Required architecture repair

### A1 — distinguish transient training realization from portable evaluation representation using existing acceleration authority

Do **not** invent a second scientific model identity. The existing acceleration policy already states which backend is a transient training realization and whether the output must remain portable.

Required semantic flow:

```text
authenticated P5 candidate configuration
 -> reconstruct canonical portable e3nn model
 -> apply the configured TRAIN2 execution realization when needed
 -> authenticate raw TRAIN2 checkpoint against that exact training realization
 -> apply authenticated checkpoint/EMA state
 -> project back to the authorized portable e3nn representation when policy requires it
 -> EVAL2 provider
```

For ordinary e3nn training, this reduces to the existing direct path.

For `training_backend=cueq`, `only_cueq=false`, a preferred minimum-complexity realization is to reuse pinned MACE's existing e3nn<->CuEq conversion owners transiently at checkpoint authentication:

1. reconstruct the portable e3nn model from the existing authenticated P5 configuration;
2. convert that model through the same qualified e3nn->CuEq realization used for training;
3. compare the existing summary `model_architecture_digest` against this reconstructed **training realization**;
4. only after the digest agrees, load the authenticated raw TRAIN2/EMA state into that realization;
5. convert the authenticated state back through the existing CuEq->e3nn owner for EVAL2;
6. prove that the resulting portable model has the same canonical portable architecture as the original P5 configuration before exposing the provider.

This preserves the existing raw TRAIN2 checkpoint/restart representation and does not require a second checkpoint file, migration database, alternate checkpoint registry, or weakened digest.

If the existing MACE conversion cannot reproduce the exact TRAIN2 raw-checkpoint realization safely, return to Software Design before introducing new persistent checkpoint representation.

### A2 — prevent runtime recomputation of frozen P5 model normalization

Any model-affecting quantity already owned by `context.method_policies.mace_architecture` must be realized exactly by MACE rather than recomputed from fold/final membership.

For `avg_num_neighbors`, ensure the parser/head configuration reaching pinned MACE explicitly carries the frozen resolved value and disables dataset-local recomputation at the correct existing translator/HeadConfig boundary. Multihead target and replay heads must resolve to one executable value consistent with the actual foundation/method architecture.

Do not hide a conflict by choosing `max()` or another runtime heuristic merely because pinned MACE does so. If foundation-backed fine tuning requires an inherited value, reconcile that fact in the existing canonical method-policy/architecture resolver before method identity is frozen.

Do not add a second normalization record.

### A3 — existing failed workspace classification

After implementing A1/A2, reauthenticate the stakeholder's already-trained run without manual deletion.

- If the run's only difference is portable e3nn versus transient authorized CuEq realization and the round-trip proves exact architecture/state compatibility, reuse the existing authenticated TRAIN2 checkpoint and proceed to EVAL2.
- If the run actually used a model-affecting value different from the frozen P5 method (for example a fold-local recomputed `avg_num_neighbors`), fail typed and preserve the evidence. Recompute that affected run under corrected current method authority; do not bless/migrate it merely to save training time.
- Never delete a valid old checkpoint before this classification is complete.

### A4 — diagnostic quality

When architecture authentication fails, preserve the concise user error but make bounded diagnostics available that identify the first/major differing architecture dimensions or the two compared digests/realizations. Do not dump learned parameter values or enormous state dictionaries.

This is diagnostic evidence only and must not become another authority.

---

## 5. Reporter + scheduler + architecture integration

These repairs must compose through one current training owner rather than three parallel systems.

Recommended control shape:

```text
P5 CV/final owner
 -> derive exact pending run tasks from frozen authority
 -> existing adaptive training-concurrency controller
      -> launch supervised MACE children
           -> one live metrics/progress probe per child
           -> TRAIN2 raw checkpoint + runtime summary
      -> shared GPU telemetry drives admission and reporting
 -> canonical checkpoint-authentication/portable-provider path
 -> EVAL2 / CV reduction / publication
```

The scheduler never reads scientific metrics to decide which model is better. The reporter never determines completion authority. The architecture checker never decides scheduling. They share execution observations where useful but retain their existing semantic roles.

---

## 6. Acceptance gates

### T1 — existing scheduler unit authority remains green

Retain `tests/test_mlff_training_parallel_scheduler.py` and its one-job startup, true-epoch gating, VRAM/utilization projection, promotion, saturation, fluctuation, and CPU-serial oracles.

### T2 — current P5 CV scheduler real-owner composition

Using a bounded frozen design with enough folds/runs to permit concurrency:

- real current P5 builds every run identity/materialization/request;
- scheduler starts one CUDA job;
- fake/bounded live children below the real supervisor emit true optimizer activity and controlled GPU samples;
- low safe utilization promotes one additional job;
- projected saturation prevents further promotion;
- every required run completes exactly once;
- CV reduction occurs in canonical plan order regardless of completion order;
- a restored run is reported/completed without relaunch.

Do not monkeypatch the scheduler decision itself or P5 run-plan/currentness owners.

### T3 — current final-production scheduler composition

For a bounded multi-size and/or multi-member final-production plan:

- the same scheduler/supervisor owner is used;
- resource admission behaves identically to CV;
- final-production freshness and exact member/run identities remain intact;
- publication waits for all required final members and is independent of completion order.

### T4 — reporter/scheduler shared observation

Prove one live child metrics stream supplies both:

- canonical `[TRAIN <run>]` update/phase reporting; and
- scheduler true-epoch activity.

Prove GPU telemetry can be reused for `[TRAIN scheduler]` reporting and admission without duplicate polling being required for correctness.

### T5 — e3nn architecture parity

Run a bounded real P5 TRAIN2/evaluation path with e3nn training and prove:

- actual live TRAIN2 architecture digest equals independent reconstructed training realization;
- raw/EMA state authenticates;
- EVAL2 provider exposes the portable model;
- mutating an architecture field still fails closed.

### T6 — phase-separated CuEq parity

Where the qualified CuEq stack is available, use a tiny bounded P5 run, not a production qualification workload:

- `enable_cueq=True`, `only_cueq=False` reaches real MACE conversion;
- TRAIN2 summary authenticates the live CuEq realization;
- independent provider authentication reconstructs the same transient realization from immutable P5 config and existing acceleration policy;
- checkpoint/EMA state loads only after the training-realization digest agrees;
- provider conversion back to e3nn succeeds;
- portable e3nn architecture agrees with the candidate configuration;
- target/replay predictions are finite;
- changing the acceleration policy or an actual model field fails closed.

This is a bounded functional regression for the observed defect, not FINAL-GPU1 performance/qualification evidence. If this environment cannot execute CuEq, record that limitation and use the stakeholder same-workspace rerun as the target-host closure evidence; do not claim accelerator qualification.

### T7 — average-neighbor/foundation construction parity

For scratch, naive foundation fine tuning, and multihead replay as supported:

- parser-resolved `avg_num_neighbors` equals the frozen P5 method architecture;
- changing fold membership does not silently change it;
- foundation/head mutations are reflected through existing method/currentness owners;
- no dataset-local normalization enters P5 model identity after freeze.

### T8 — existing failed-workspace recovery

Against the same stakeholder workspace or a faithful equivalent:

- if failure is only authorized CuEq/e3nn realization mismatch, rerun proceeds from authenticated existing TRAIN2 evidence into provider/EVAL2 without retraining;
- if a genuine model-affecting runtime drift is demonstrated, affected evidence remains preserved and is rejected/recomputed rather than silently accepted.

### T9 — adversarial architecture guard

Keep counterexamples proving that a true change to r_max, heads/order, species table, interaction structure, dtype, avg-neighbor authority, or acceleration realization cannot pass checkpoint authentication.

### T10 — assembled final evidence

After the executable repair, run on one unchanged candidate:

- parent replay-membership suites;
- no-redundant-replay-parse oracles;
- progress PR1-PR8;
- training scheduler unit and P5 CV/final composition tests;
- TRAIN2 checkpoint/restart/EMA architecture suites;
- P5 executable-config and MACE execution-semantics suites;
- multi-size lifecycle and final-production/currentness/publication suites;
- affected P7 provider/qualification regressions because they consume the same published P5 checkpoints;
- configured Python static/AST checks.

Full long-running GPU/CuEq/LAMMPS/MLIAP release qualification remains deferred.

---

## 7. Explicit non-goals / forbidden fixes

Do not:

- implement a new adaptive scheduler when `training_parallel` already owns it;
- create separate scheduler implementations for CV and final production;
- create separate progress probes/reporters for CV versus final production;
- use raw MACE stdout spam as the reporter;
- schedule based on validation loss, CV metric, or scientific score;
- make completion order scientific order;
- remove or weaken `model_architecture_digest` authentication;
- classify CuEq and e3nn as interchangeable without the existing acceleration/conversion authority;
- disable CuEq or force e3nn solely to avoid the error;
- bless a fold-local recomputed normalization as the frozen method;
- add a second checkpoint registry, model-identity hierarchy, compatibility database, migration state, progress database, daemon, or wrapper;
- delete the stakeholder checkpoint before determining whether it is authorized transient realization or genuine method drift.

Prefer rewiring the surviving scheduler/reporter/conversion owners and removing duplicated or dead execution paths.

---

## 8. Updated implementation order

1. Complete the R1 replay-membership I/O reduction already required by the prior review amendment.
2. Recover the shared supervised MACE child/reporting owner from the progress amendment.
3. Rewire the existing adaptive `training_parallel` scheduler around that same child owner for both CV and final production.
4. Perform the complete TRAIN2-versus-reconstruction architecture census.
5. Repair transient acceleration realization and any genuine model-field drift at the smallest existing owners; preserve the fail-closed guard.
6. Reauthenticate the existing failed workspace before deciding whether retraining is scientifically required.
7. Run T1-T10 and return for independent Protocol 6 review.

---

## 9. Re-review PASS checklist

```text
[ ] existing training_parallel scheduler, not a replacement, controls P5 CUDA admission
[ ] cross-validate uses it for required fold/seed training jobs
[ ] train-production uses the same scheduler for required final jobs
[ ] CUDA starts with one real job and promotes only after true-epoch telemetry plus safe projected VRAM/utilization
[ ] CPU behavior remains bounded/serial per existing policy
[ ] scheduler and reporter share child activity and GPU telemetry where practical
[ ] completion order has no scientific/reduction/publication authority
[ ] historical 10-second live TRAIN reporting and canonical progress grammar are restored in both public paths
[ ] architecture mismatch guard remains fail-closed
[ ] actual TRAIN2 architecture and independently reconstructed training realization match for e3nn
[ ] phase-separated CuEq raw checkpoint is authenticated against reconstructed CuEq realization before any state load
[ ] only_cueq=false provider is projected back to portable e3nn and portable architecture matches frozen P5 configuration
[ ] avg_num_neighbors and every other model-affecting runtime field are frozen/realized consistently, not fold-local recomputed
[ ] authorized old CuEq realization can resume into EVAL2 without unnecessary retraining
[ ] genuinely nonconforming old run is rejected/preserved, not migrated/blessed
[ ] replay membership semantics and no-redundant-full-parse requirements remain closed
[ ] final affected regression/integration/static evidence executes on one candidate
[ ] no new scheduler/reporter daemon/checkpoint registry/compatibility DB/state machine/identity hierarchy
[ ] no full GPU/LAMMPS qualification claim is made
```

Until these rows close, keep the replay/MACE membership repair active and **NO-PASS / REOPENED**.
