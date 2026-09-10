---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: reopened
created_date: 2026-09-09
last_review_date: 2026-09-09
implementation_branch: fix/mlff-replay-mace-membership-identity
source_candidate_under_repair: a4d722d6de6dda59f7f1a20eb9b583e4a756f12a
review_verdict: no-pass
workplan_review_state: reconciled
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE, serial selected-size orchestration, and acceleration architecture
serious_challenge: none
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier replay-membership/review/progress/scheduler amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — consolidated final repair workplan

## 0. Disposition after workplan re-review

Executable candidate `a4d722d6de6dda59f7f1a20eb9b583e4a756f12a` remains **NO-PASS / repair required**. This workplan itself has now been re-reviewed against current SSDP 6.0.0 and current mdstats architecture/specification authority and is reconciled for the next D4 implementation pass.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, and accepted D3 P5/TRAIN2/MACE architecture remain unchanged.

One requirement from the preceding workplan revision is explicitly **retracted**: do **not** lift adaptive training admission across selected sizes. Current accepted D3 states that the selected-size dimension sits outside fold/seed/MACE execution and remains serial; each selected size uses the one effective fold/seed/MACE resource allocation before the next size proceeds. The prior command-wide cross-size scheduler requirement was an unjustified workplan expansion, not a product requirement.

The remaining repair is therefore smaller: make the existing per-size P5 scheduler behave correctly, keep replay identity-domain handling exact without redundant parsing, preserve live TRAIN supervision/reporting, and classify the pre-fix completed TRAIN2 run from actual authenticated architecture rather than from current configuration spelling.

---

## 1. Governing current architecture and problem of concern

The current post-selection chain remains:

```text
frozen ordered selected-size collection
 -> serial outer selected-size iteration
      -> one size's exact pending CV folds/seeds or production members
      -> existing adaptive TRAIN admission for those independent jobs
      -> supervised MACE/TRAIN2 execution
      -> authenticated checkpoint/EVAL2
      -> canonical per-size CV reduction or production publication
 -> campaign-level CV/status aggregation where already defined
```

For final production there is one additional precondition: the complete frozen selected-size collection is preflighted before any **new** production job is admitted. Every selected size must already hold current accepted CV ancestry under its own binding/horizon. This collection-wide barrier does not create cross-size training scheduling or transactional rollback of independently valid per-size evidence.

The core concern is exact composition at the shared per-size TRAIN execution boundary:

- target and replay membership must retain their distinct identity domains;
- single-source replay membership must not be recovered by repeated full-corpus parsing;
- TRAIN supervision/progress must reflect actual execution without becoming completion authority;
- adaptive CUDA admission must observe real current optimizer activity and resource telemetry;
- TRAIN2 continuation and EVAL2 reconstruction must authenticate the same model realization;
- pre-fix completed state must be classified before destructive replacement or retraining.

---

## 2. Frozen invariants and non-goals

### 2.1 Scientific/method invariants

Do not change:

- exact selected target membership `T_N`;
- frozen per-size CV and production horizons;
- CV folds, seeds, all-required acceptance, or target-only acceptance semantics;
- optimizer, loss, objective weighting, batching, EMA, checkpoint ranking, or evaluation conventions;
- replay training exposure versus independent TRUE_DFT replay admissibility;
- foundation scientific identity;
- multi-size identity/currentness semantics;
- final-production freshness/currentness/publication semantics.

### 2.2 Identity and lineage invariants

- target execution membership uses exact target `frame_uid`;
- canonical single-source replay uses existing replay source/split/canonical geometry identity;
- generated replay ExtXYZ views are transport, not new scientific authority;
- actual MACE-loaded membership must equal authenticated expected membership exactly;
- replay source/split/view/method lineage must not churn merely to repair transport/control logic;
- TRAIN2 continuation remains bound to exact run/materialization/MACE execution evidence;
- progress, scheduler readiness, and resource telemetry are transient execution observations and enter no scientific identity.

### 2.3 Orchestration invariants

- selected sizes remain serial at the outer current D3 boundary;
- within one selected size, independent folds/seeds or production members may be admitted concurrently by the existing scheduler;
- scheduler controls resource admission only;
- reporter describes live execution only;
- completion order never changes canonical reduction/publication order;
- no duplicate concurrent launch of one run identity;
- methodological CV rejection of one size is recorded and remaining frozen sizes are still cross-validated before campaign-level reduction;
- an execution/runtime failure stops new admission for the affected active scheduler and must not create acceptance/publication for incomplete work;
- already-authenticated evidence belonging to completed sibling runs/sizes remains valid according to its own identity/currentness and is not rolled back merely because later work fails.

### 2.4 Acceleration/model invariants

- source/evaluation/deployment representation remains portable e3nn where current policy says so;
- TRAIN2 may use configured transient CuEq/OEq execution;
- `only_cueq=false` requires the portable product representation;
- architecture authentication remains fail closed;
- model-affecting values frozen by P5, including `avg_num_neighbors`, must reach MACE exactly and must not be recomputed from fold-local data.

### 2.5 Forbidden machinery

Do not add a new scheduler, persistent queue, progress daemon, replay registry, checkpoint registry, compatibility database, migration framework, restart state machine, second MACE wrapper, cross-size scheduler, or durable recovery representation. Prefer removal, direct routing, and reuse of existing owners.

---

## 3. Accepted implementation direction from `a4d722d6...`

Preserve these directions unless executable evidence proves a concrete defect:

- canonical single-source replay can execute without target-domain `frame_uid`;
- `PostSelectionReplayResolution` carries authenticated ordered single-source replay geometry membership process-locally;
- parent expected replay membership can therefore avoid a full replay ExtXYZ scan;
- existing `canonical_replay_geometry_identity()` can be applied to loaded MACE configuration geometry;
- TRAIN progress incrementally tails MACE's append-only metrics stream;
- optimizer records advance gradient-update progress while evaluation records do not;
- `MacePostSelectionTrainer` supervises a `Popen` child instead of a blind blocking `subprocess.run(..., capture_output=True)` path;
- cancellation/process-group cleanup, bounded stdout/stderr diagnostics, disk stop, timeout, and configured visible cadence remain part of the shared trainer owner;
- current P5 executable configuration explicitly disables local `avg_num_neighbors` recomputation;
- EVAL2 reconstruction keeps the fail-closed architecture guard and distinguishes transient accelerator realization from portable representation;
- existing e3nn/CuEq conversion authority is reused instead of creating another model/checkpoint representation.

These accepted source directions still require final executed evidence after the remaining blockers are repaired.

---

## 4. Blocking repair R1 — remove scheduler lifecycle/phase conflation

### Defect

The current per-task state overloads `phase`: submission writes `phase="running"`, then child observations overwrite the same field with MACE/reporting phase such as `launching`, `training`, or `validation`. Admission later counts true-epoch work only where `phase == "running"`, so the first child heartbeat can make a genuinely active job disappear from scheduler readiness accounting.

### Required end state

Do not add another lifecycle state machine. The existing transient `active Future -> task` relation already owns scheduler task liveness.

Use:

```text
active slots        := slots represented by active futures
active job count    := len(active futures)
reported MACE phase := child observation only
```

A future leaving `active` is completed/failed independently of its last reporting phase. Keep the reporting `phase` field exclusively for actual execution phase.

### Acceptance

Through the real per-size P5 scheduler/supervisor path, prove that a live child reporting `phase=training` remains scheduler-active and that safe telemetry can actually promote concurrency above one.

---

## 5. Blocking repair R2 — define true-epoch readiness from bounded fresh optimizer activity

### Defect

The candidate reports scheduler readiness as `completed_epochs > 0`. This is false during first-epoch optimizer work and becomes sticky after one epoch, including during long validation. Neither behavior matches the existing true-epoch admission contract.

The preceding workplan revision also overcorrected by suggesting that an optimizer counter must increase on every scheduler observation. A legitimate optimizer step may span more than one telemetry interval. The repository already exposes `parallel_training_epoch_activity_timeout_seconds` as the bounded freshness control; do not replace it with an implicit one-poll timeout.

### Required end state

Use only transient facts already available from the incremental metrics observer:

- current MACE phase;
- accepted optimizer-update count;
- time of the most recent newly observed optimizer update;
- existing configured activity-freshness timeout.

For scheduler admission, one active job is true-epoch/optimizer-active only when:

1. it is currently in optimizer/training phase, not initialization or validation;
2. at least one real optimizer update has been observed for the current execution/resume; and
3. the most recently observed optimizer update is still within the configured `parallel_training_epoch_activity_timeout_seconds` freshness window.

The timestamp/counter comparison is process-local observation only; do not persist a readiness record.

Consequences:

- first-epoch optimizer work becomes eligible after the first real optimizer update;
- a normal slow step may remain eligible across multiple telemetry polls while still inside the activity timeout;
- validation/evaluation is immediately non-ready even if the last update is recent;
- no fresh optimizer progress beyond the activity timeout is non-ready;
- whenever any active job is non-ready, the existing controller's calibration window is held/reset through its normal `epoch_active_jobs < active_jobs` path;
- returning to fresh optimizer work restarts the existing fixed-duration calibration window;
- visible progress cadence must not alter admission semantics.

### Acceptance

Real-owner bounded evidence must show:

1. first-epoch optimizer updates establish readiness without waiting for epoch completion;
2. no new update on one ordinary telemetry poll does not falsely revoke readiness while still within the configured activity timeout;
3. validation phase revokes readiness immediately and cannot authorize promotion;
4. stale optimizer activity beyond the timeout revokes readiness;
5. resumed optimizer activity re-establishes calibration;
6. existing controller promotion, projection, fluctuation averaging, saturation throttling, and CPU-serial tests remain green.

---

## 6. Binding correction — preserve serial selected-size orchestration

The previous revision's command-wide cross-size scheduler requirement is withdrawn.

Current accepted D3 states:

```text
selected size N1
 -> its fold/seed or production-member scheduler/work
 -> its canonical reduction/publication
selected size N2
 -> its fold/seed or production-member scheduler/work
 -> its canonical reduction/publication
...
```

Do not flatten jobs from different selected sizes into one scheduler session and do not introduce a cross-size resource queue.

For CV:

- each size still obtains every required fold/seed verdict;
- a methodological rejection does not truncate the remaining selected-size experiment;
- campaign CV passes only when every frozen selected size is accepted.

For production:

- perform the existing collection-wide accepted-CV preflight before any new production job;
- after admission, execute/publish each selected size through its existing per-size owner in frozen order;
- if a later size fails, do not publish that incomplete size and do not mark the overall production stage complete, but do not delete or counterfeit-invalid previously authenticated per-size evidence.

No Architecture Manual mutation is required by this workplan.

---

## 7. Blocking repair R3 — one explicit replay identity domain, no cascading fallback

### Defect

The current child adapter can try canonical loaded-geometry identity, then historical geometry identity, then reread replay-file metadata and accept whichever digest matches. This can hide a broken current single-source boundary and reintroduce the full replay parse that the repair is supposed to eliminate.

### Required end state

Choose the replay identity domain once from existing authenticated replay/interface authority and execute only that domain.

For current canonical `single_source`:

```text
expected = authenticated split's canonical replay geometry identities
actual   = canonical_replay_geometry_identity(MACE-loaded configuration) for each loaded replay item
result   = exact set/membership authentication or typed failure
```

No historical-identity retry and no replay-file metadata reread are allowed for current single-source execution.

For supported `legacy_split`, use the one legacy identity domain already authorized by that artifact/interface and keep that compatibility bounded.

Prefer deriving the domain from information already present in the current replay request/artifact/resolution. If the child process genuinely needs a discriminator that is not otherwise reconstructable at its boundary, carry only the minimum discriminator through the **existing process-local MACE execution authority**. Do not create a side channel, registry, new replay identity, or gratuitous durable schema family. The discriminator itself is execution routing, not scientific lineage, and must not invalidate otherwise authentic replay source/split/view/method identity.

### Representation-equivalence requirement

Because current single-source authentication now relies on geometry reconstructed from MACE-loaded `Configuration` objects, prove that the existing canonical identity is representation-stable across the source -> MACE loader boundary. Use representative periodic and non-periodic geometries; do not invent another hash.

### Acceptance

- canonical single-source success performs zero redundant full replay membership scans in the parent and zero replay-file membership rereads after MACE's necessary load;
- canonical identity computed from source authority equals the identity reconstructed from the corresponding real MACE-loaded configuration for representative periodic and non-periodic frames;
- a geometry mutation beyond the existing identity quantization changes identity and rejects;
- canonical loaded-geometry mismatch fails before training evidence acceptance rather than entering a legacy/file fallback;
- supported legacy behavior remains explicit and green;
- partial/mixed identity domains fail typed;
- replay mutation and mismatched continuation remain fail closed;
- seed/fold count does not multiply avoidable replay membership parsing.

---

## 8. Blocking repair R4 — classify the pre-fix completed TRAIN2 run from actual architecture

### Defect

The stakeholder's completed run was produced immediately before the current explicit `compute_avg_num_neighbors=False` P5 configuration spelling. Its immutable config can therefore differ from today's expected config even when much of the run is otherwise authentic.

Current recovery reaches current-config equality too early. More importantly, current reconstruction treats a missing `compute_avg_num_neighbors` key using today's disabled-recomputation behavior; that must not be used to infer what the old run actually realized. Historical absence and current explicit `False` are not automatically semantically equivalent because pinned MACE historically defaults local recomputation on.

### Required end state

Do not migrate, rewrite, or broadly whitelist old configuration.

Recognize only the exact immediately-pre-fix internally authenticated state relevant to this defect, then classify it from **persisted actual TRAIN2 architecture authority** before current-config spelling is allowed to reject or replace it:

1. authenticate the old materialization, run plan, artifacts, TRAIN2 summary/continuation, MACE execution evidence, and checkpoint as recorded;
2. reconstruct the **current authorized training realization** from the current frozen P5 method, including the configured transient CuEq/OEq realization when applicable;
3. compare the persisted actual TRAIN2 `model_architecture_digest` with that current authorized training-realization architecture using the existing canonical architecture descriptor/digest;
4. when diagnostics are needed, compare recoverable architecture dimensions such as heads and realized `avg_num_neighbors`, but do not create another architecture authority;
5. if the actual persisted training architecture equals the current authorized training realization, treat the config difference as non-model representation/spelling and permit reuse of the authenticated TRAIN2 state through the corrected EVAL2 path;
6. if the architecture differs, preserve the old run and recompute only that affected run under current authority;
7. never normalize a missing historical control into today's value as proof of equivalence;
8. never delete/rewrite the old materialization or checkpoint before classification.

For phase-separated CuEq with `only_cueq=false`, compare like with like at the transient training-realization boundary, then project the authenticated state back through the existing qualified conversion to the portable e3nn EVAL2 provider.

### Acceptance

Through the real recovery/checkpoint/architecture owners, provide both counterfactuals:

- immediately-pre-fix config representation + persisted actual training architecture equal to current authorized realization -> reuse without rewriting scientific materialization or retraining;
- immediately-pre-fix representation + persisted actual architecture genuinely different (for example different realized `avg_num_neighbors`/head topology) -> typed preserved rejection and recomputation.

Also prove that an unrelated foreign/corrupt old config is not admitted merely because this bounded classification exists.

---

## 9. Reporter, failure propagation, and architecture parity — proof still required

The current direction is acceptable but not yet closed without executed real-owner evidence.

### 9.1 Progress denominator and restart accounting

Progress is observational and never completion authority.

Required behavior:

- optimizer records are the numerator; evaluation/validation records never increment it;
- before a durable TRAIN2 summary is available, any projected denominator must match the exact authorized MACE training-loader geometry, including target + replay combined-loader and current drop-last semantics when multihead replay is active;
- once authenticated TRAIN2 `planned_updates` exists, it supersedes launch-time projection;
- restart begins from authenticated completed updates and tails only new metrics bytes; historical metrics are not double-counted;
- if exact progress is not yet knowable, report liveness/phase with unknown ETA rather than fabricate completion percentage.

### 9.2 Failure/cancellation orchestration

Use bounded failure injection through the real per-size scheduler and real supervised trainer owner:

- one active child fails or is interrupted while another child is active and at least one task remains queued;
- scheduler stops new admission immediately;
- cancellation reaches owned active siblings and their subprocess groups are reaped;
- already-authenticated TRAIN2 continuation/checkpoint evidence remains reusable;
- no incomplete fold/size obtains acceptance and no incomplete production run is published;
- previously completed sibling evidence remains untouched.

Do not add retry/queue state to satisfy this test.

### 9.3 Architecture parity

Retain and prove:

- ordinary e3nn training-reconstruction architecture equality;
- deliberate model-architecture mutation rejection;
- two distinguishable P5 memberships/folds receive the same frozen authorized `avg_num_neighbors` rather than fold-local recomputation;
- bounded real CuEq TRAIN2 realization -> reconstruction -> authenticated state -> portable e3nn EVAL2 parity when the qualified CuEq stack is available.

If the CuEq stack required for that concrete functional bug test is unavailable on the implementation host, mark this implementation-acceptance claim unavailable/blocking. Do not substitute mock-only evidence. Full long-running production GPU qualification remains deferred.

---

## 10. Final intended control shape

```text
public cross-validate / train-production
 -> establish collection-level freeze/admission rules
 -> serial selected-size iteration (accepted D3)
      -> derive this size's exact plans, reusable evidence, pending tasks
      -> ONE existing AdaptiveTrainingConcurrency session for this size
           -> active futures own task liveness
           -> supervised MACE child per admitted task
                -> one incremental metrics probe
                -> phase + update freshness feed scheduler/reporting
           -> one GPU telemetry sample per scheduler interval reused for admission/reporting
      -> canonical per-size result ordering
      -> existing CV reduction or final-production publication
      -> existing TRAIN2/EVAL2 authentication/projection
```

Replay:

```text
single_source -> authenticated canonical split identity -> MACE-loaded canonical geometry -> exact compare/fail
legacy_split  -> explicitly authorized existing legacy identity domain -> exact compare/fail
```

No cross-size scheduler and no cascading replay identity fallback.

---

## 11. Required executable evidence

After all material executable edits, run one unchanged final candidate through the complete affected surface. At minimum include:

```text
tests/test_mlff_replay_unify1b.py
tests/test_mlff_replay_unify1c.py
tests/test_mlff_replay_unify1d.py
current replay restart/currentness tests

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
new/current real per-size P5 scheduler-supervisor integration tests
current multi-size CV/final-production/currentness/publication tests
```

Add real-owner tests for R1-R4 and section 9. Controller-only tests cannot close scheduler wiring; direct helper reconstruction cannot close public recovery/orchestration claims.

Use Semgrep when available, otherwise bounded validated AST/source checks with known-positive/known-negative cases, for structural claims that runtime tests cannot establish cheaply. Protect at minimum:

- no current single-source replay membership file-reread fallback;
- no bare blocking P5 training subprocess path;
- no duplicate GPU poller for scheduler versus reporter within one observation interval;
- no new durable scheduler/progress/replay/checkpoint compatibility machinery;
- no dataset-local recomputation of frozen P5 `avg_num_neighbors`;
- scheduler task liveness is not derived from human-readable MACE phase text;
- outer selected-size iteration remains serial unless D3 is deliberately reopened in a future task.

Run configured fast Python lint/type/static checks. Re-derive the final affected surface from the final candidate; this list is a floor, not a substitute for impact analysis.

A required test/check that does not execute is a blocker. Production-scale GPU/CuEq/LAMMPS/MLIAP runs are not required here except the tiny real CuEq functional check described above when needed for the concrete architecture bug.

---

## 12. Re-review PASS criteria

All must be true:

```text
[ ] target frame_uid exactness remains intact
[ ] canonical single-source replay executes through real P5/MACE owners without target frame_uid
[ ] parent single-source expected replay membership comes from existing split authority with no redundant full scan
[ ] child single-source membership uses the canonical loaded-geometry domain only and fails instead of entering legacy/file fallback
[ ] source-vs-MACE canonical replay identity equivalence is demonstrated on representative periodic/non-periodic frames
[ ] supported legacy replay remains explicit, bounded, and green
[ ] replay mutation / mixed domain / mismatched continuation fail closed
[ ] replay source/split/view/method lineage remains stable

[ ] P5 TRAIN uses supervised child execution for CV and final production
[ ] progress numerator/denominator/validation/restart/cadence semantics are exact and observational only
[ ] interruption/failure stops new admission, reaps owned children, preserves valid continuation, and creates no incomplete acceptance/publication

[ ] scheduler active membership comes from actual active task ownership
[ ] scheduler readiness uses current training phase plus bounded fresh optimizer activity, not completed_epochs > 0
[ ] a slow legitimate optimizer step within the configured activity timeout does not reset readiness merely because one telemetry poll saw no new record
[ ] initialization/validation/stale activity cannot authorize added jobs
[ ] safe optimizer-phase telemetry promotes 1 -> 2 through real per-size P5 wiring
[ ] VRAM/utilization projection, fluctuation averaging, saturation throttling, CPU/RAM limits remain intact
[ ] scheduler/reporting share child observations and GPU telemetry without competing control planes
[ ] selected sizes remain serial at the accepted outer D3 boundary
[ ] every frozen size still receives its required CV verdict before campaign reduction
[ ] production retains collection-wide CV preflight and per-size publication/currentness semantics

[ ] current P5 freezes avg_num_neighbors and other model-affecting architecture fields
[ ] e3nn TRAIN2/EVAL2 architecture parity passes and mutation rejects
[ ] bounded real CuEq transient-realization -> portable-provider parity passes where required/available
[ ] old pre-fix completed run is classified from persisted actual TRAIN2 architecture before current-config rejection/deletion
[ ] architecture-equal old run can reuse authentic state; architecture-different run is preserved/recomputed
[ ] unrelated foreign/corrupt historical state remains rejected

[ ] no new registry/DB/daemon/queue/state machine/second scheduler/second wrapper/cross-size scheduler is introduced
[ ] final focused + affected regression + integration + static evidence executes on one unchanged candidate
[ ] full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to final release
```

Any unchecked row remains a blocker. Do not narrow the claim or weaken an oracle to manufacture closure.

---

## 13. Genuine reopen/escalation triggers

Return to Software Design only if implementation evidence shows one of these:

1. canonical identity cannot be reconstructed exactly from real MACE-loaded single-source replay geometry without changing accepted replay authority;
2. correct true-epoch activity cannot be established from the existing metrics/phase/freshness controls without a materially new execution-state architecture;
3. exact transient accelerator realization cannot be reconstructed/authenticated through existing MACE conversion owners and would require a new persistent model/checkpoint representation;
4. the pre-fix completed run cannot be classified without changing accepted P5 scientific/model authority;
5. a newly demonstrated resource/performance requirement shows the accepted serial outer selected-size D3 topology itself is inadequate rather than merely slower than an ungoverned alternative;
6. another discovered construction difference proves accepted D3 architecture contradictory or unable to preserve D1/D2 semantics.

Absent one of these triggers, keep the work in D4 and repair/reduce the existing owners.

---

## 14. Deferred final-release qualification

Still deferred until the complete final release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS/MLIAP target-machine deployment qualification;
- full stakeholder production campaign qualification.

The tiny bounded real CuEq execution/reconstruction test required to close the concrete checkpoint-realization defect is implementation functional evidence, not production qualification.
