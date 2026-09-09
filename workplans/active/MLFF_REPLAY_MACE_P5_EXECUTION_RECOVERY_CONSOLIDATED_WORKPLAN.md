---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: active
created_date: 2026-09-09
implementation_branch: fix/mlff-replay-mace-membership-identity
source_candidate_under_repair: 41fd1cf0643fb7f42a8423c22368b2283f9176de
consolidation_base_commit: 405fa486363bacf87b806d38a76edc7de409e129
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE and acceleration architecture
serious_challenge: none
supersedes_for_implementation:
  - CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR
  - CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-REVIEW-REOPEN-1
  - CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-PROGRESS-RECOVERY-1
  - CODE-MLFF-REPLAY-MACE-MEMBERSHIP-SCHEDULER-ARCHITECTURE-RECOVERY-1
precedence: This file is the single snapshot-complete implementation handoff for the current repair cycle. The superseded files remain historical/provenance evidence only and do not need to be consulted to implement this workplan. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — consolidated implementation workplan

## 0. Purpose and disposition

This file consolidates the current replay-membership, replay-I/O, live TRAIN reporting, adaptive GPU scheduling, and TRAIN2/EVAL2 architecture-realization repairs into **one implementation stage**.

An implementation agent should be able to execute this entire repair from this file without mentally composing the prior parent workplan and three amendments. The older files remain useful provenance for why individual requirements were introduced, but they are not separate implementation entrypoints after this consolidation.

The current executable candidate is **NO-PASS / repair required**. No Serious Challenge is active. The accepted scientific and high-level architecture remain unchanged:

- target-size and post-selection scientific methodology remain frozen;
- target and replay membership remain different semantic identity domains;
- P5 remains the owner of CV/final-production orchestration and currentness;
- TRAIN2 remains the training/restart authority;
- EVAL2 remains the checkpoint evaluation path;
- MACE remains the neural-network/loss/optimizer execution dependency;
- the acceleration policy remains the existing source/evaluation versus training-backend authority;
- full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package.

This cycle is a coherent D4 execution repair. It should be implemented and reviewed **in one go**, with one final executable candidate and one final affected-surface evidence set.

---

## 1. Core problem of concern

The current P5 execution path has four coupled defects/regressions around one shared TRAIN execution boundary.

### 1.1 Replay membership identity composition

Canonical single-source replay is valid without target-domain `frame_uid`. Its generated replay views carry replay-specific geometry/source/split identity. The earlier candidate incorrectly assumed every replay frame had target `frame_uid`, causing:

```text
TrainingDataInputError: MACE execution frame identity requires non-empty UID values.
```

Candidate `41fd1cf...` repairs the identity-domain direction correctly: target continues to use target `frame_uid`; single-source replay may use canonical replay geometry identity; mixed replay identity domains fail closed. Preserve that semantic correction.

### 1.2 Replay membership is now authenticated with redundant full-corpus parsing

The repaired candidate establishes expected replay membership in the parent P5 path by reparsing the complete replay ExtXYZ, then reparses the same file again in the child wrapper after MACE already loaded the data. These scans occur inside the CV seed/fold run matrix and scale with every replay-enabled run.

This must be reduced to the existing authoritative source/split membership on the parent side and the already-loaded MACE geometry on the child side. Do not add a cache/registry merely to hide redundant parsing.

### 1.3 Long-running TRAIN execution lost historical supervision/reporting

The current `MacePostSelectionTrainer` uses a blocking child invocation and hides healthy long-running MACE activity. Target-host evidence proved the process was actively training while the public command appeared frozen after the design banner.

Recover the established supervised MACE progress contract for both current P5 public consumers:

```text
cross-validate
train-production
```

This is recovery of a historical shared execution capability, not a new public lifecycle or new reporting framework.

### 1.4 Adaptive GPU training scheduling survived but lost its consumers

`training_parallel.py` still contains the historical adaptive GPU scheduler and tests, including `TrainingConcurrencyPolicy`, `build_training_concurrency_plan()`, `AdaptiveTrainingConcurrency`, NVML/`nvidia-smi` telemetry, and GPU-utilization/VRAM/CPU/RAM admission logic.

The V7 P5 path no longer constructs or consumes it. Current CV/final-production TRAIN jobs therefore execute serially despite the scheduler machinery, configuration controls, and regression tests surviving.

Restore the existing scheduler to both CV and final production. Do not create a second scheduler.

### 1.5 Completed TRAIN2 checkpoint can fail EVAL2 architecture authentication

A long real CV run completed training and then failed with:

```text
TrainingDataInputError:
Candidate MACE configuration reconstructs a different execution architecture
from the authenticated TRAIN2 model.
```

The fail-closed architecture check is correct and must remain. The repair must make the actual TRAIN2 execution realization and independent reconstruction comparable under the already accepted acceleration/model architecture.

Two concrete drift vectors require closure:

1. phase-separated CuEq training can persist/authenticate the transient CuEq live model while EVAL2 reconstructs the portable e3nn representation;
2. P5 may allow MACE to recompute model-affecting `avg_num_neighbors` from fold-local training data while independent reconstruction uses the frozen architecture value.

The implementation must perform a complete construction census rather than patch only the first observed mismatch.

---

## 2. Frozen invariants and non-goals

### 2.1 Scientific and numerical invariants

Do not change:

- exact selected target membership `T_N`;
- frozen per-size CV and production horizons;
- CV fold construction, acceptance predicates, or all-required aggregation;
- optimizer/loss/weighting/batching semantics except to realize already-frozen values exactly;
- replay training exposure versus independent TRUE_DFT replay admissibility;
- replay label semantics;
- foundation scientific identity;
- checkpoint ranking/evaluation conventions;
- multi-size experiment semantics;
- final-production freshness/currentness/publication semantics.

### 2.2 Identity and lineage invariants

- target execution membership remains exact target `frame_uid` membership;
- canonical single-source replay membership comes from existing replay geometry/source/split authority;
- generated replay ExtXYZ views are reconstructable transport, not new scientific authority;
- no replay identity is derived from pathname, arbitrary sequence number, or a new registry;
- replay source/split/view/method/replay-lineage identities must not churn merely to satisfy transport bookkeeping;
- actual MACE-loaded membership remains authenticated exactly before evidence is accepted;
- TRAIN2 continuation remains bound to exact MACE execution evidence;
- progress and scheduler state are observational/execution-control state only and enter no scientific identity.

### 2.3 Acceleration/model invariants

Preserve the accepted phase-separated acceleration semantics:

```text
source / evaluation / deployment representation -> portable e3nn
TRAIN2 execution backend                        -> configured training backend
only_cueq=false                                 -> portable e3nn checkpoint/product required
```

CuEq/OEq may be a transient execution realization without becoming a second scientific model identity.

Do not silently switch a configured training backend to e3nn to make architecture comparison pass.

### 2.4 Explicit non-goals / forbidden machinery

Do not introduce:

- a new replay-ID namespace or replay registry;
- a compatibility database or migration database;
- a second MACE wrapper or second training engine;
- a new scheduler database or persistent job queue;
- a second progress daemon/service or durable progress schema;
- a new checkpoint registry or alternate persistent checkpoint hierarchy;
- a new restart state machine;
- broad user/source replay-file rewriting;
- a cache whose only purpose is masking avoidable reparsing;
- weakened architecture or membership authentication;
- count-only replay membership checks;
- per-frame fallback between mixed identity domains;
- raw MACE stdout passthrough as the primary progress UI.

Prefer reduction, rewiring, and reuse of existing owners.

---

## 3. Repair family A — replay execution-membership realization without redundant reparsing

### A1 — preserve role-aware identity domains

The accepted semantic direction from `41fd1cf...` remains binding:

```text
target role -> exact target frame_uid membership
replay role -> exact existing replay geometry membership
```

A replay file/run with partial or conflicting identity metadata fails typed. Do not select an identity source independently per frame.

Supported legacy split replay remains bounded by its existing current authority. Do not break authentic legacy continuation merely because canonical single-source replay is repaired.

### A2 — parent expected replay membership comes from existing authority

For canonical single-source replay, parent P5 launch authority must not reread the complete generated replay training ExtXYZ merely to recover expected membership.

Use already-authenticated replay source/split information already carried through the existing P5 replay resolution, including the canonical train geometry membership/set digest where available.

Required result:

```text
single-source replay resolution
 -> authenticated source/split membership already known
 -> expected MACE replay membership digest
```

with **zero additional full replay ExtXYZ membership scans** in the parent authority path.

Do not add a memoization/cache layer instead of deleting the redundant scan.

### A3 — child actual replay membership piggybacks on MACE-loaded data

The child wrapper must still prove that the actual replay configurations MACE loaded equal the authenticated expected membership, but should not reopen the complete replay ExtXYZ solely to recover identity metadata after MACE already parsed it.

Preferred realization:

- derive the existing canonical replay geometry identity from geometry retained by MACE's loaded `Configuration` objects (`atomic_numbers`, `positions`, `cell`, `pbc`, and any other fields the existing canonical replay geometry owner requires);
- prove exact equivalence with the existing replay geometry identity function;
- compare loaded-membership digest with the expected authenticated split membership;
- keep the existing MACE execution-evidence record family.

Do not invent another geometry hash.

If pinned MACE cannot establish exact loaded replay membership without a second full reread or an accepted authority change, stop and route to Software Design rather than hiding the cost.

### A4 — same-workspace compatibility

The stakeholder's prepared workspace and pre-fix generated replay views must remain usable if they are otherwise authentic.

Installing the repair and rerunning must not require:

- `prepare` solely for this defect;
- deletion of `.mdstats/replay-unified`;
- rewriting the external replay source;
- rewriting valid generated replay views solely to inject target `frame_uid`;
- changing source/split/view/method/replay-lineage identity.

### A5 — performance oracle

Acceptance must include structural/call-count evidence, not only tiny fixtures or wall time:

- parent single-source authority performs zero redundant full replay membership scans when split authority is available;
- child validation performs no extra full replay-file parse beyond MACE's necessary data load if the loaded-geometry realization is used;
- seed/fold count does not multiply avoidable replay membership parsing.

A representative 10k-class bounded benchmark may supplement this, but is not the primary oracle.

---

## 4. Repair family B — one supervised TRAIN execution owner and live progress reporter

### B1 — replace the blocking blind execution path

Current P5 long-running MACE execution must no longer rely on a bare blocking `subprocess.run(..., capture_output=True)` path that prevents live supervision.

Reuse/refactor the historical generic MACE child supervision/progress behavior into the current shared P5/TRAIN2 boundary. The public V7 `train` lifecycle does not return; only the reusable private execution capability returns.

The same owner must handle:

- child launch and exit code;
- bounded stdout/stderr diagnostic capture;
- frequent control polling;
- Ctrl-C/SIGTERM propagation;
- owned-child process-group cleanup;
- existing disk/resource/cancellation behavior where applicable;
- live metrics probing;
- no orphan MACE process after interruption.

### B2 — exact TRAIN progress semantics

The live TRAIN reporter uses MACE's append-only metrics stream and the current TRAIN2 runtime plan.

Numerator:
- accepted observed optimizer/gradient-update progress;
- evaluation/validation records do not increment it;
- duplicate records for one update do not double-count.

Denominator:
- exact planned TRAIN2 optimizer-update budget derived from current update geometry and horizon.

Restart:
- authenticated completed work is shown as restored progress;
- new metrics continue from that point;
- visible counter does not restart from zero or double-count.

If current supported MACE output cannot uniquely establish an exact update count at some phase, report conservative phase/liveness with unknown ETA rather than invent a percentage. Reporting uncertainty never changes completion authority.

### B3 — nested P5 and TRAIN visibility

Both current public operations must expose outer run context and inner child progress.

For CV, outer context includes:

```text
N_selected
run index / total required run matrix
seed
fold / total folds
restored/reused versus executing
phase
```

For final production, outer context includes:

```text
N_selected
member/seed identity
member index / total required production jobs
restored/reused versus executing where legitimate
phase
```

Inner TRAIN heartbeat includes when available:

```text
progress=<updates>/<total> (<pct>%)
unit=gradient-update
phase=<optimizer/evaluation/...>
epoch=<current>/<horizon>
elapsed=HH:MM:SS
eta=<HH:MM:SS|--:--:-->
rate(s)
GPU/VRAM telemetry
```

A long validation phase must remain visibly alive without falsely increasing optimizer progress.

### B4 — canonical cadence and formatting

Use existing `progress_timing` formatters and the established MLFF grammar:

```text
status; progress; elapsed; eta; recent/current rate; average rate; stage telemetry
```

- semicolon-delimited;
- `elapsed=HH:MM:SS`;
- unknown ETA `--:--:--`;
- counted work `completed/total (percent%)`;
- explicit rate units.

Visible cadence consumes `[execution].training_progress_interval_seconds`, default 10 seconds. Control polling may remain much faster. Do not print on every control poll or every batch.

### B5 — both CV and final production use it

The recovered reporter/supervisor is not CV-specific. `cross-validate` and `train-production` must launch through the same shared owner.

---

## 5. Repair family C — restore the existing adaptive GPU scheduler to CV and final production

### C1 — reuse the surviving scheduler owner

Use existing:

- `TrainingConcurrencyPolicy`;
- `build_training_concurrency_plan()`;
- `AdaptiveTrainingConcurrency`;
- `query_gpu_telemetry()`/existing telemetry implementation;
- existing generated/configured execution controls.

Do not create `PostSelectionSchedulerV2`, another queue, or another resource controller.

### C2 — one current P5 training admission surface

Both current public operations schedule their independent required TRAIN jobs through the same admission owner:

```text
cross-validate
 -> exact pending (N, seed, fold) jobs
 -> existing adaptive TRAIN scheduler

train-production
 -> exact pending (N, member/seed) jobs
 -> same scheduler
```

The scheduler controls resource admission only. It owns no scientific selection, fold membership, replay membership, horizon, ranking, CV acceptance, or publication decision.

### C3 — deterministic science despite concurrent completion

Before scheduling, construct the required run identities from existing frozen authority.

Concurrency may change wall-clock completion order only.

- no duplicate concurrent launch of one run identity;
- restored valid runs count once and are not relaunched to fill capacity;
- CV reduction consumes evidence in canonical plan order and still requires every required run;
- final-production publication consumes canonical frozen member order/policy and waits for all required members;
- completion order is never ranking or acceptance authority.

### C4 — preserve adaptive CUDA semantics

Auto CUDA mode retains historical behavior:

1. start one real job;
2. require genuine optimizer/epoch activity, not initialization/validation idleness;
3. observe the configured telemetry window;
4. project aggregate VRAM and GPU utilization for one additional job;
5. admit one additional job only if projected VRAM and GPU utilization are within configured ceilings and CPU/RAM permit it;
6. repeat incrementally to the measured/configured cap;
7. sustained saturation throttles future replacements/admission using the existing controller semantics.

A positive `parallel_training_jobs` remains a cap, not permission to ignore resource safety. CPU remains serial unless existing accepted policy says otherwise.

### C5 — reporter and scheduler share observations

The supervisor/progress owner supplies the scheduler with per-child:

- liveness;
- true optimizer/epoch activity;
- completed updates;
- phase.

GPU telemetry should be sampled once per scheduler/control interval and reused for scheduler decisions and visible scheduler reporting when practical. Do not create duplicate NVML pollers for the same interval/sample.

Presentation cadence must not change admission decisions.

### C6 — scheduler visibility and failure semantics

Recover `[TRAIN scheduler]` status using the same canonical grammar. Report when applicable:

```text
progress completed/total jobs
elapsed / eta
active jobs
true_epoch active/active
admission target / cap
queued/pending
last decision/reason
GPU utilization
VRAM use/budget
```

On hard child failure/interruption/resource stop:

- stop admitting new work;
- terminate/reap owned children according to existing graceful-stop semantics;
- preserve already-authenticated restart evidence;
- do not publish partial CV acceptance or partial final production;
- derive pending work again from current P5 authority on rerun rather than persisting a second queue authority.

---

## 6. Repair family D — TRAIN2/EVAL2 architecture parity without weakening authentication

### D1 — keep the fail-closed architecture guard

`authenticate_train2_checkpoint_provider()` must continue to independently establish that the candidate configuration reconstructs the same executable model architecture that TRAIN2 authenticated before checkpoint state is applied.

Do not suppress, bypass, or relax the comparison merely because the run is expensive.

### D2 — complete construction census first

Before finalizing a patch, compare actual TRAIN2 model construction and independent reconstruction across every architecture dimension represented by the canonical MACE execution-architecture descriptor, at minimum:

- portable e3nn versus transient CuEq/OEq realization;
- exact model class/modules before/after accelerator conversion;
- P5 head set and order (`pt_head`, `target_head`, ordinary `Default` where legal);
- foundation-head selection/removal;
- `r_max` and foundation-inherited values;
- atomic-number table/order;
- `avg_num_neighbors` and recomputation behavior;
- interaction/product/readout/correlation structure;
- dtype;
- architecture-derived buffers.

Use a bounded real P5 configuration and record field-level/digest-level comparison. Do not patch the first differing field and stop.

### D3 — distinguish transient training realization from portable representation

For ordinary e3nn training, existing direct architecture reconstruction should remain the simple path.

For phase-separated CuEq with `only_cueq=false`, the intended semantic flow is:

```text
authenticated P5 candidate configuration
 -> reconstruct canonical portable e3nn model
 -> apply configured TRAIN2 execution realization
 -> compare exact training-realization architecture with TRAIN2 summary
 -> apply authenticated raw/EMA checkpoint state
 -> project back through existing qualified conversion to portable e3nn
 -> verify portable architecture still equals the canonical P5 configuration
 -> expose EVAL2 provider
```

Preferred minimum-complexity realization reuses pinned MACE's existing e3nn->CuEq and CuEq->e3nn conversion owners transiently during checkpoint authentication. No second persistent model identity or checkpoint file is required.

If exact TRAIN2 realization cannot be reconstructed safely through existing conversion authority, return to Software Design before adding persistent representation machinery.

### D4 — freeze model-affecting P5 normalization

Any model-affecting quantity already owned by `context.method_policies.mace_architecture` must reach MACE exactly and must not be silently recomputed from fold/final membership.

For `avg_num_neighbors`:

- parser/head configuration must carry the frozen resolved value;
- dataset-local recomputation must be disabled at the correct existing translator/HeadConfig boundary;
- target and replay heads must resolve consistently with the actual foundation/method architecture;
- do not hide conflicts with a runtime `max()` or similar heuristic merely because pinned MACE contains one.

If foundation fine-tuning legitimately requires an inherited value, reconcile it in the existing canonical method-policy/architecture resolver **before method identity is frozen**.

Do not add another normalization record.

### D5 — classify the stakeholder's existing completed run before deletion

After D2-D4 are implemented, reauthenticate the existing failed workspace.

Case 1 — representation-only mismatch:

```text
TRAIN2 used the authorized transient CuEq realization
portable e3nn scientific architecture is otherwise the same
checkpoint/state round-trip authenticates exactly
```

Then reuse the existing authenticated TRAIN2 checkpoint and proceed to EVAL2. No retraining is scientifically necessary.

Case 2 — genuine model drift:

```text
fold-local avg_num_neighbors differs
head topology differs
foundation-derived architecture differs
or another model-affecting field differs from frozen P5 method
```

Then fail typed, preserve the evidence, and recompute that affected run under the corrected current method. Do not migrate/bless it merely to save compute.

Never delete the old checkpoint before classification completes.

### D6 — diagnostics

On architecture mismatch, provide bounded diagnostics identifying the compared realizations/digests and major/first differing architecture dimensions. Do not dump learned parameter values or huge state dictionaries.

Diagnostics are evidence only, not a new authority.

---

## 7. One integrated execution/control shape

The repairs should compose through one existing execution boundary:

```text
P5 CV / final-production owner
 -> derive exact required/pending run tasks from frozen authority
 -> existing adaptive training-concurrency controller
      -> launch supervised MACE children
           -> one live metrics/progress probe per child
           -> TRAIN2 raw checkpoint + runtime summary
      -> shared GPU telemetry drives admission + scheduler/reporting telemetry
 -> canonical TRAIN2 checkpoint authentication
      -> exact configured training realization
      -> portable provider projection when required
 -> EVAL2
 -> canonical CV reduction or final-production publication
```

Role separation remains strict:

- scheduler decides resource admission, not scientific ranking;
- reporter describes execution, not completion authority;
- architecture checker authenticates model realization, not scheduling;
- replay membership owner authenticates membership, not progress;
- completion order does not alter scientific ordering.

---

## 8. Implementation sequence — execute as one coherent stage

### Stage 1 — replay membership/I/O reduction

1. preserve role-aware target/replay membership semantics from the accepted candidate;
2. route single-source expected membership from existing replay/split authority;
3. derive actual replay membership from MACE-loaded geometry if exact equivalence is proven;
4. remove redundant full replay reparsing;
5. preserve same-workspace/restart identity.

### Stage 2 — shared supervised TRAIN owner

1. replace P5 blocking blind child execution with the recovered/refactored existing supervision pattern;
2. recover exact-update metrics probing, phase visibility, cadence, interruption ownership, and canonical formatting;
3. route both CV and final production through it.

### Stage 3 — adaptive scheduler rewiring

1. construct existing training concurrency policy/plan at current P5 orchestration scope;
2. schedule exact CV and production tasks through `AdaptiveTrainingConcurrency`;
3. share child true-epoch state and GPU telemetry with the reporter;
4. preserve deterministic canonical reduction/publication order.

### Stage 4 — architecture-realization closure

1. perform full construction census;
2. repair transient acceleration-realization comparison using existing conversion authority;
3. freeze `avg_num_neighbors` and any other discovered model-affecting configured values at the correct owner;
4. classify/reuse-or-reject existing failed workspace without broad deletion.

### Stage 5 — integrated falsification and final evidence

Run all focused, adversarial, assembled, regression, and static evidence below on one unchanged executable candidate. Then perform independent Protocol 6 implementation review.

Stages 1-4 are one implementation handoff and should normally be completed before independent review. Do not request a separate design/review cycle after each substage unless a stated reopen trigger fires.

---

## 9. Acceptance matrix

### E1 — original replay identity failure remains closed

Through the real P5 request/trainer owner and real dependency-facing loader owner:

- canonical single-source replay without `frame_uid` is accepted using existing replay geometry identity;
- target membership still requires exact target `frame_uid`;
- actual loaded replay membership equals authenticated expected membership;
- mixed/partial identity domains fail typed;
- no replay source/view rewriting occurs merely to add target UID metadata.

### E2 — no redundant replay parsing

Structural/call-count or equivalent owner-level evidence proves:

- parent single-source expected-membership construction performs zero full replay-file membership scans when authenticated split membership exists;
- child validation does not perform a second complete replay ExtXYZ parse solely for membership after MACE loaded the same data;
- seed/fold count does not multiply avoidable replay membership scans.

### E3 — same-workspace / lineage stability

Using pre-fix prepared replay views/workspace:

- no manual deletion/reprepare;
- replay source SHA/content digest unchanged;
- split manifest digest unchanged;
- generated train/monitor view bytes/digests unchanged unless independently corrupt;
- method/replay-lineage identity unchanged for the replay membership repair itself;
- execution proceeds beyond the former identity failure.

### E4 — replay mutation and continuation counterfactuals

- mutate/substitute one replay geometry after expected authority is established -> reject before training evidence acceptance;
- mismatched persisted replay membership evidence -> reject before partial/full continuation, EVAL2, or publication;
- supported current legacy replay continuation remains reusable when authentic;
- target `frame_uid` mutation still rejects independently.

### E5 — live TRAIN reporter

Through real current `MacePostSelectionTrainer` supervision with bounded child work:

- at least one TRAIN heartbeat is emitted before child termination;
- exact optimizer progress/denominator semantics are demonstrated;
- evaluation records do not increment gradient progress;
- a long validation phase reports validation/evaluation liveness;
- configured visible cadence is respected while control polling remains responsive;
- canonical progress formatter/grammar is used;
- interruption reaps owned child and preserves legitimate restart evidence.

### E6 — reporter restart accounting

Create authenticated partial TRAIN2 work, interrupt through the real supervision owner, resume, and prove:

- completed work appears as restored progress;
- new progress continues from the authenticated point;
- no double counting or restart-from-zero presentation;
- reporting changes no scientific/checkpoint identity.

### E7 — scheduler unit authority remains green

Retain and run the existing `tests/test_mlff_training_parallel_scheduler.py` or current equivalent, covering:

- one-job auto startup;
- true-epoch gate;
- VRAM/utilization projection;
- incremental promotion;
- saturation throttling;
- fluctuation averaging;
- CPU-serial behavior.

### E8 — CV scheduler real-owner composition

For a bounded design with enough independent runs:

- real current P5 builds every run identity/materialization/request;
- scheduler starts one CUDA job;
- bounded child/telemetry below the real supervisor demonstrates true optimizer activity;
- safe utilization promotes another job;
- projected saturation prevents further promotion;
- each required run executes/restores exactly once;
- completion order may differ but CV reduction uses canonical plan order;
- restored runs are not relaunched merely to fill capacity.

Do not monkeypatch the scheduler decision itself or P5 run-plan/currentness owners.

### E9 — final-production scheduler/reporter composition

For bounded multi-size and/or multi-member production:

- the same scheduler and supervisor owner is used;
- production freshness/run identities remain exact;
- all required members complete before publication;
- completion order does not alter publication semantics;
- live TRAIN/member context is visible before trainer completion.

### E10 — shared observation

Prove one live child metrics stream supplies both:

- reporter progress/phase; and
- scheduler true-epoch activity.

Prove one GPU telemetry observation can feed scheduler admission and scheduler/reporting telemetry without duplicate polling being required for the same sample interval.

### E11 — architecture parity: e3nn

For ordinary e3nn training:

- independently reconstructed candidate architecture equals authenticated TRAIN2 model architecture;
- valid checkpoint/provider authentication still succeeds;
- deliberate architecture mutation remains rejected.

### E12 — architecture parity: bounded CuEq realization

Where the qualified CuEq stack is available, run a tiny bounded reproduction through the real owners:

```text
P5 config
 -> real MACE TRAIN2 CuEq realization
 -> runtime summary/raw checkpoint
 -> independent portable reconstruction
 -> same qualified e3nn->CuEq realization
 -> architecture digest equality
 -> authenticated state application
 -> qualified CuEq->e3nn projection
 -> portable architecture equality
 -> EVAL2 provider
```

This is a functional bug reproduction/repair test, not production-scale GPU qualification.

If CuEq dependencies are unavailable on the implementation host, the required current architecture/unit/integration evidence must still run where possible and the bounded CuEq owner check remains an explicit unresolved blocker for final implementation acceptance rather than being silently replaced by a mock-only pass.

### E13 — frozen model-affecting normalization

Use at least two P5 memberships/folds with distinguishable geometry statistics and prove:

- the MACE training path receives the one frozen authorized `avg_num_neighbors` value;
- dataset-local recomputation is disabled;
- independent reconstruction observes the same value;
- fold membership alone cannot change model architecture;
- changing the frozen authorized architecture value changes the appropriate method/currentness identity and does not reuse stale evidence.

### E14 — existing stakeholder workspace classification

Exercise an old/completed failed run fixture or the stakeholder workspace when available:

- representation-only authorized CuEq/e3nn mismatch reauthenticates and proceeds without retraining;
- genuine model-affecting mismatch rejects typed and is preserved for recomputation;
- no broad deletion occurs before classification.

### E15 — multi-size composition

Use a bounded frozen two-size replay-enabled design with different role horizons where practical and prove:

- every requested size enters CV;
- every required size/fold/seed job participates in scheduler/reporting;
- no first-size-only behavior;
- final production likewise handles every frozen size/member required by current authority.

### E16 — structural family closure

Use Semgrep when available; otherwise validated AST/source checks with known-positive/known-negative cases. Reject at minimum:

- replay `frame_uid` as the sole source for canonical single-source membership;
- replay source/view mutation solely to inject target UIDs;
- full replay-file reparsing in parent authority when split membership is already available;
- second replay-file parse after MACE load solely for identity where loaded-geometry realization is implemented;
- bare blocking P5 `subprocess.run(... capture_output=True)` that hides live supervision;
- duplicate GPU telemetry pollers introduced for scheduler versus reporter;
- new persistent scheduler/progress/replay/checkpoint authority machinery;
- architecture-authentication bypass;
- dataset-local recomputation of frozen model-affecting P5 normalization.

### E17 — final affected regression/integration/static evidence

At minimum include the existing focused surfaces named by the superseded workplans, including as applicable:

```text
tests/test_mlff_replay_unify1b.py
tests/test_mlff_replay_unify1c.py
tests/test_mlff_replay_unify1d.py
current replay-unify restart/currentness tests

tests/test_mlff_target_size_p5_r7_guards.py
tests/test_mlff_target_size_p5_r8_guards.py
tests/test_mlff_target_size_p5_r9_guards.py
tests/test_mlff_target_size_p5_r10_guards.py
tests/test_mlff_target_size_p5_r11_guards.py

tests/test_mlff_downstream_integration_closure.py
tests/test_mlff_mace_executable_config.py
tests/test_mlff_mace_execution_semantics.py
tests/test_mlff_mace_execution_semantics_assembled.py

tests/test_mlff_train2a_policy.py
tests/test_mlff_train2b_runtime.py
relevant TRAIN2 continuation/checkpoint-state tests

tests/test_mlff_training_parallel_scheduler.py
current campaign multi-size/post-selection integration/currentness tests
current final-production/publication tests
```

Re-derive the exact final affected surface from the candidate rather than treating this list as exhaustive.

Also run the repository's configured fast Python lint/type/static checks and any changed storage/run-lease checks if execution cleanup/ownership surfaces move.

Test source without execution is not evidence.

---

## 10. One-pass PASS criteria

The consolidated implementation is ready for independent review only when all are true:

```text
[ ] canonical single-source replay without frame_uid executes through real P5/MACE membership owners
[ ] target frame_uid exactness remains intact
[ ] single-source expected replay membership comes from existing replay/split authority
[ ] actual MACE-loaded replay membership is authenticated exactly
[ ] no avoidable replay membership parse is multiplied by seed/fold count
[ ] pre-fix prepared workspace remains usable without lineage churn/reset/deletion
[ ] replay geometry mutation and mismatched continuation fail closed
[ ] current supported legacy replay semantics remain intact
[ ] both cross-validate and train-production use the recovered supervised TRAIN owner
[ ] live TRAIN progress is visible before child completion
[ ] progress numerator/denominator/restart accounting are exact and non-authoritative
[ ] canonical progress grammar/cadence is used
[ ] both cross-validate and train-production use the existing adaptive GPU scheduler
[ ] scheduler starts conservatively and admits additional work only from true-epoch + safe resource projections
[ ] scheduler/reporting share live child state and GPU telemetry where practical
[ ] completion order cannot alter CV reduction or publication semantics
[ ] architecture guard remains fail closed
[ ] full TRAIN2-vs-reconstruction construction census is complete
[ ] e3nn TRAIN2/EVAL2 architecture parity is proven
[ ] bounded CuEq training-realization -> portable-provider parity is proven where required/available
[ ] frozen avg_num_neighbors and other model-affecting configured values are realized exactly
[ ] existing failed workspace is classified before deletion/retraining
[ ] no new replay/progress/scheduler/checkpoint registry, migration DB, state machine, daemon, or wrapper
[ ] final focused + affected regression + integration + static evidence executes on one unchanged executable candidate
[ ] full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package
```

Any unchecked row is a blocker. Do not manufacture closure by narrowing the claim.

---

## 11. Reopen triggers

Return to Software Design only if implementation evidence demonstrates one of the following:

1. exact actual replay membership cannot be authenticated without changing accepted replay transport/scientific authority or retaining unavoidable repeated full-corpus parsing;
2. safe adaptive scheduling requires a persistent queue/authority not already justified by current architecture;
3. exact TRAIN2 transient acceleration realization cannot be reconstructed/authenticated with existing acceleration/conversion owners and would require a new persistent checkpoint/model representation;
4. foundation/P5 model construction reveals a genuine contradiction in accepted D3 architecture rather than a D4 realization drift;
5. a scheduler/reporter integration requirement would materially change scientific ordering, CV acceptance, final-production freshness, or currentness semantics.

Absent one of these triggers, keep the work in D4 and finish the consolidated stage before requesting another design cycle.

---

## 12. Deferred final-release qualification

Do not expand this workplan into long target-machine qualification.

Deferred until the final complete release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS / MLIAP deployment qualification;
- final production campaign qualification on the stakeholder machine.

A **tiny bounded real CuEq functional test** is allowed and required where needed to close the concrete architecture-realization bug. It is not a performance/release claim.
