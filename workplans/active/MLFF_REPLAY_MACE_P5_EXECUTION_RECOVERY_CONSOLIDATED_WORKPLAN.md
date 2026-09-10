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
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE and acceleration architecture
serious_challenge: none
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier replay-membership/review/progress/scheduler amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — consolidated workplan, Protocol 6 review reopen

## 0. Review disposition

**NO-PASS / REOPENED** after independent Software Design review of executable candidate
`a4d722d6de6dda59f7f1a20eb9b583e4a756f12a`.

The candidate closes several important parts of the prior failure family and those corrections should be preserved. However, the adaptive scheduler is not behaviorally functional as assembled, its scope remains per-size rather than command-wide, the replay child path still contains an ambiguity/fallback route capable of reintroducing the prohibited full replay reread, and the stakeholder's pre-fix completed workspace cannot be classified under the newly frozen `compute_avg_num_neighbors=False` realization. Required real-owner/executed acceptance is also absent for these surfaces.

No Serious Challenge is active. Do **not** reopen D1 scientific formulation, D2 numerical method, or the accepted D3 P5/TRAIN2/MACE architecture. The remaining work is a bounded D4 owner-consolidation repair.

This review deliberately does **not** reopen accepted mainline storage/run-completion topology machinery or existing accelerator-conversion synchronization merely because those surfaces are present in the candidate tree. They pre-exist this implementation candidate and are outside the causal repair unless the next implementation produces direct evidence otherwise.

---

## 1. Core problem of concern and global invariants

The product outcome remains one current P5 execution path in which replay membership, TRAIN supervision/progress, adaptive resource admission, TRAIN2 continuation, and EVAL2 reconstruction compose without duplicated authority or hidden expensive work.

Preserve all of the following:

1. **Scientific invariants**
   - exact selected target membership `T_N`;
   - frozen per-size CV and production horizons;
   - CV fold construction and all-required acceptance;
   - optimizer/loss/weighting/batching semantics;
   - replay training exposure versus independent TRUE_DFT replay admissibility;
   - foundation scientific identity;
   - checkpoint ranking/evaluation conventions;
   - multi-size experiment semantics and collection-wide production admission.

2. **Identity/lineage invariants**
   - target execution membership uses exact target `frame_uid`;
   - canonical single-source replay uses existing replay geometry/source/split authority;
   - generated replay ExtXYZ is transport, not a new scientific identity;
   - actual MACE-loaded membership is authenticated exactly;
   - replay source/split/view/method lineage does not churn merely to satisfy adapter bookkeeping;
   - TRAIN2 continuation remains bound to exact MACE execution evidence.

3. **Execution/control invariants**
   - scheduler controls resource admission only;
   - reporter describes live execution only;
   - neither becomes scientific/completion authority;
   - concurrency may change wall-clock completion order only;
   - CV reduction and final publication remain in canonical frozen order;
   - no duplicate concurrent launch of one run identity;
   - hard failure/interruption stops new admission and reaps owned children.

4. **Acceleration/model invariants**
   - source/evaluation/deployment remain portable e3nn where current policy says so;
   - TRAIN2 may use the configured transient CuEq/OEq realization;
   - `only_cueq=false` remains a portable-product policy;
   - architecture authentication remains fail closed;
   - model-affecting values already frozen by P5, including `avg_num_neighbors`, must be realized exactly and not recomputed from fold-local data.

5. **Minimum-complexity rule**
   - do not add a new scheduler, queue DB, progress daemon, replay registry, checkpoint registry, compatibility DB, state machine, second wrapper, or persistent recovery representation;
   - repair by removing conflated state, lifting the existing scheduler to the correct owner, and using explicit existing identity domains rather than fallback chains.

---

## 2. Accepted parts of `a4d722d6...` — preserve unless repair evidence proves otherwise

The following implementation directions are accepted and should not be backed out merely to fix the blockers below:

- canonical single-source replay can reach P5 without target-domain `frame_uid`;
- `PostSelectionReplayResolution` carries the already-authoritative ordered replay geometry membership process-locally;
- parent expected replay membership can therefore be constructed without a full replay ExtXYZ scan;
- `canonical_replay_geometry_identity()` can operate on MACE-loaded configuration geometry while preserving the existing replay identity definition;
- TRAIN progress uses incremental append-only metrics consumption rather than rereading the full metrics file;
- optimizer records advance gradient-update progress while evaluation records do not;
- P5 training uses supervised `Popen` rather than the old blocking `subprocess.run(..., capture_output=True)` path;
- cancellation, process-group cleanup, bounded stdout/stderr capture, disk stop, and configured visible progress cadence are directionally restored;
- `compute_avg_num_neighbors=False` is now explicit in current P5 executable configuration;
- independent checkpoint reconstruction distinguishes transient training realization from portable evaluation representation and keeps the architecture guard;
- current e3nn/CuEq conversion authority should continue to be reused rather than inventing another model/checkpoint representation.

These accepted pieces still require final executed regression/integration evidence after the blockers are repaired.

---

## 3. Blocking repair R1 — eliminate scheduler lifecycle/training-phase state conflation

### 3.1 Defect

The current scheduler stores one dictionary per slot with a key named `phase`. Submission writes:

```text
phase = running
```

but the shared child progress observer then updates the same key with MACE/reporting phase values such as:

```text
launching
training
validation
```

Scheduler admission later counts true-epoch jobs only for states whose `phase == "running"`. Consequently the first live child observation removes that slot from the scheduler's active-epoch count. The existing `AdaptiveTrainingConcurrency` then observes `0/N` true-epoch jobs and cannot perform its intended 1 -> 2 -> ... promotion.

This is a direct behavioral failure of the restored scheduler, not a presentation issue.

### 3.2 Required end state

Do not add another lifecycle enum/state machine. The scheduler already owns the authoritative transient relation:

```text
active Future -> pending task
```

Use that relation to identify active slots. Keep the per-child `phase` field exclusively for actual TRAIN/MACE phase reporting.

Conceptually:

```text
active_slots := slots named by current active futures
scheduler_active_jobs := len(active_slots)
scheduler_epoch_active_jobs := fresh optimizer-active observations among active_slots
```

A future leaving `active` is completed/failed regardless of the last MACE phase value. Do not duplicate that fact into another synchronized lifecycle field unless a demonstrable need remains after simplification.

### 3.3 Acceptance

A real-owner bounded scheduler composition test must prove that a child can report `phase=training` and still count as active for admission, and that safe telemetry can actually promote target concurrency above one.

---

## 4. Blocking repair R2 — scheduler readiness must mean **fresh current optimizer activity**, not a sticky completed-epoch flag

### 4.1 Defect

The recovered progress observer currently exports:

```text
true_epoch = completed_epochs > 0
```

This does not match the historical scheduler contract.

It is false during the entire first epoch even while optimizer updates are streaming, so calibration is delayed unnecessarily. Once one epoch completes it becomes permanently true, including during long validation/evaluation phases. If used for admission, low utilization during validation can therefore be averaged as though the GPU were executing steady optimizer work.

Historical authority requires admission calibration only when **every active job is producing fresh optimizer updates**. Initialization, graph construction, and validation idleness must not authorize extra jobs.

### 4.2 Required end state

Reuse the already-recovered live metrics probe. At each scheduler observation interval, derive optimizer activity from fresh progress since the prior scheduler observation (for example, an increase in the existing completed-update/optimizer-update counter) together with the current TRAIN phase. This state is transient scheduler observation only and must not be persisted.

Required behavior:

- optimizer updates during the first epoch can establish readiness;
- no new optimizer progress during validation/evaluation makes that active job non-ready for admission calibration;
- when any active job leaves current optimizer compute, the existing controller's calibration window is held/reset through its normal `epoch_active_jobs < active_jobs` semantics;
- returning to fresh optimizer compute starts/restarts the existing fixed-duration calibration window;
- reporting cadence must not change admission semantics.

Do not introduce an independently maintained `ready`, `true_epoch`, or GPU-stage state machine if the existing metric counter/phase plus active-future relation are sufficient.

### 4.3 Acceptance

Through the real P5 supervisor -> scheduler observation path:

1. first-epoch fresh optimizer records establish active optimizer work;
2. a long evaluation interval does not count as active optimizer work and cannot promote concurrency;
3. resumed optimizer activity can re-establish calibration;
4. existing `AdaptiveTrainingConcurrency` promotion and saturation-throttle unit tests remain green.

---

## 5. Blocking repair R3 — lift one scheduler session to the command-wide multi-size P5 owner

### 5.1 Defect

The consolidated contract requires the exact pending job set to enter one P5 training admission surface:

```text
cross-validate  -> pending (N, seed, fold) jobs
train-production -> pending (N, member/seed) jobs
```

The implementation instead creates a new scheduler inside `execute_post_selection_cross_validation(context)` / `execute_final_production(context)` for one selected size at a time, while the public command retains a serial outer loop over `contexts`.

The source even states that the outer size iteration is deliberately serial and that the size dimension adds no scheduler. That contradicts the consolidated C2/E15 contract and prevents independent jobs from different selected sizes from sharing otherwise available GPU capacity.

### 5.2 Required end state

Move/lift the **existing** scheduler admission session to the public command scope that already owns the frozen selected-size collection. Do not create a second or multi-size-specific scheduler class.

Preferred decomposition:

```text
per-size P5 owner:
    derive/validate plan
    classify reusable evidence
    produce exact pending run tasks + canonical slot metadata

public command owner:
    combine pending context-bearing tasks across all frozen sizes
    execute them through one existing adaptive scheduler/supervisor session

per-size P5 owner:
    reassemble results by canonical run-plan slot
    reduce CV or publish final production using existing deterministic owners
```

The exact helper names are delegated. The important constraints are:

- all plans/run identities/currentness decisions remain owned by their existing per-size P5 authorities;
- scheduler only admits already-authorized independent tasks;
- completion order is never reduction/publication order;
- a methodological CV rejection still follows the current collection-wide reduction semantics;
- production still performs the existing collection-wide CV admission barrier before **any** new production work;
- hard child failure remains command-level fail-fast with no partial acceptance/publication.

### 5.3 Acceptance

Use at least two selected sizes with different horizons and enough independent jobs to demonstrate:

- one scheduler controller/session observes jobs from both sizes;
- safe resource conditions can fill capacity with jobs from different sizes;
- every required run executes/restores exactly once;
- per-size CV reductions and production publications remain canonical regardless of completion order;
- no first-size-only or per-size capacity reset remains.

---

## 6. Blocking repair R4 — remove cascading replay identity fallback from the current single-source child path

### 6.1 Defect

The child membership adapter currently tries, in order:

1. canonical replay geometry identity from MACE-loaded configuration;
2. historical replay geometry identity from the same loaded configuration;
3. replay metadata recovered by rereading the training file.

It chooses whichever digest happens to match the launch authority. This is exactly the fallback-chain shape the consolidated plan forbids. In particular, if canonical single-source loaded-geometry reconstruction is wrong or drifts, the code can silently reopen the full replay ExtXYZ and still pass, reintroducing the performance regression rather than exposing the broken composed boundary.

A comment saying current single-source P5 never reaches the file scan is not an enforced invariant.

### 6.2 Required end state

Select the replay membership domain **once from existing authenticated interface/artifact authority before child validation** and execute exactly that domain.

For canonical `single_source`:

```text
expected membership = existing split/canonical replay geometry identities
actual membership   = canonical geometry identities reconstructed from MACE-loaded collection
mismatch             = typed failure
```

No historical-identity retry and no replay-file metadata reread are permitted for that interface.

For currently supported legacy replay, use the one identity domain already authorized for that legacy artifact/interface. If a small discriminator must cross the existing MACE execution-authority boundary, add it as an explicit field to that existing authority/evidence contract rather than creating a new side channel or registry. It is an execution-domain discriminator, not a new scientific identity.

Do not choose an identity domain independently per frame and do not use a cascading try-until-match policy.

### 6.3 Acceptance

- canonical single-source loaded-geometry mismatch fails before training evidence is accepted and performs **zero** replay ExtXYZ rereads for membership;
- canonical success performs zero redundant parent/child membership scans beyond MACE's necessary data load;
- legacy supported behavior remains explicit and green;
- partial/mixed identity domains fail typed;
- replay geometry mutation and mismatched continuation remain fail closed.

---

## 7. Blocking repair R5 — classify the stakeholder's pre-fix completed workspace before applying the new config spelling

### 7.1 Defect

The stakeholder's long completed run was created by the immediately preceding P5 realization, whose immutable config did not include the new explicit `compute_avg_num_neighbors=False` field. Candidate `a4d722d6...` now requires that field in current executable/reconstruction projection.

Current materialization recovery still recognizes only the earlier retired `foundation_model` locator compatibility. A completed pre-fix config missing `compute_avg_num_neighbors=False` therefore becomes foreign to the current expected config. With durable continuation, execution-evidence reauthentication also projects the old config through the new translator, which rejects local average-neighbor recomputation before the code can answer the workplan's required question:

```text
Was the completed model only represented differently,
or did it actually train with a model-affecting avg_num_neighbors different from the frozen P5 method?
```

That is a failure to implement the required D5/E14 classification boundary.

### 7.2 Required end state

Do **not** add a general old-config compatibility/migration rule and do not rewrite the old materialization.

Before applying current-config equality as authorization, recognize only the exact immediately-pre-fix internally authenticated P5 representation relevant to this defect and classify the **realized model architecture**:

1. authenticate the existing materialization bytes, artifacts, run plan, TRAIN2 continuation/evidence, and raw checkpoint exactly as recorded;
2. identify that the only config-representation difference under consideration is the absent explicit `compute_avg_num_neighbors=False` control (plus any already-authorized transient CuEq/e3nn representation distinction);
3. reproduce/inspect the actual pre-fix training realization under its real parser/construction semantics sufficiently to compare its authenticated `model_architecture_digest` and the realized `avg_num_neighbors`/other model-affecting dimensions against the frozen current P5 architecture;
4. if the realized architecture is exactly the authorized frozen architecture and the only remaining difference is representation/spelling, reuse the authenticated TRAIN2 state and proceed through the corrected EVAL2 realization without retraining;
5. if the old run actually realized a different neighbor normalization/head/topology/other model-affecting architecture, fail typed, preserve it, and recompute only that affected run under current authority;
6. never delete/rewrite the old materialization/checkpoint before classification.

One-time bounded work required to authenticate an old completed run is acceptable; do not create a migration framework or durable compatibility registry.

### 7.3 Acceptance

Provide two counterfactual fixtures through the real recovery/checkpoint owner:

- old config representation + realized architecture equal to frozen architecture -> reauthenticate/reuse without rewriting old scientific materialization or retraining;
- old config representation + realized `avg_num_neighbors` (or another model field) genuinely different -> typed preserved rejection and recomputation required.

---

## 8. Accepted architecture parity and reporter work that still needs proof

The current direction for TRAIN2/EVAL2 architecture parity is acceptable in source: reconstruct portable e3nn, realize the configured transient training backend, compare against TRAIN2 architecture authority, apply authenticated state, and restore the portable provider when policy requires it. Likewise current P5 config explicitly freezes `compute_avg_num_neighbors=False`.

Do not redesign these pieces absent failing evidence. Close them with the missing real-owner tests:

- ordinary e3nn reconstruction/checkpoint parity;
- deliberate architecture mutation rejection;
- tiny bounded real CuEq TRAIN2 -> reconstruction -> authenticated state -> portable e3nn EVAL2 parity where the qualified CuEq stack is available;
- two distinguishable fold memberships proving `avg_num_neighbors` remains the one frozen method value;
- live reporter heartbeat before child exit;
- evaluation records do not increment update progress;
- long validation remains visibly alive;
- restart progress resumes from authenticated completed work without double counting;
- interruption reaps owned child and leaves valid restart evidence.

If the CuEq stack is unavailable on the implementation host, the required bounded real CuEq owner test remains an explicit implementation-acceptance blocker; do not replace it with mock-only evidence. This is functional bug closure, not production-scale GPU qualification.

---

## 9. Required implementation shape — simplify, do not layer

The final control shape should be:

```text
public P5 CV / final-production collection owner
 -> derive exact per-size plans + reusable evidence + pending authorized tasks
 -> ONE existing AdaptiveTrainingConcurrency session for the command
      -> existing supervised MACE trainer per admitted task
           -> one incremental MACE metrics probe
           -> fresh optimizer activity supplied to scheduler
           -> progress/phase supplied to reporter
      -> one GPU telemetry sample per scheduler interval reused for admission/reporting
 -> group completed evidence back by context + canonical slot
 -> existing per-size CV reduction / production publication
 -> existing TRAIN2 checkpoint authentication + EVAL2 provider projection
```

For replay membership:

```text
single_source
 -> parent expected identity from authenticated split authority
 -> child actual identity from MACE-loaded canonical geometry
 -> exact compare or fail

legacy_split
 -> explicitly authorized existing legacy identity domain
 -> exact compare or fail
```

There must be no try-canonical/try-historical/then-reread fallback for current single-source execution.

---

## 10. Test and evidence requirements

The final unchanged executable candidate must run the complete affected surface. At minimum include:

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
new/current real P5 scheduler-supervisor integration tests
current multi-size CV/final-production/currentness/publication tests
```

Add explicit owner-level tests for R1-R5. In particular, controller unit tests alone cannot close P5 scheduler wiring.

Structural closure should use Semgrep when available; otherwise use a bounded validated AST/source fallback with known-positive/known-negative examples. Establish at minimum:

- no current single-source replay fallback to full replay-file membership reread;
- no bare blocking P5 training subprocess path;
- no duplicate GPU polling for scheduler and reporter at one observation interval;
- no new durable scheduler/progress/replay/checkpoint authority machinery;
- no dataset-local recomputation of frozen P5 `avg_num_neighbors`;
- no scheduler lifecycle decision derived from the reporter's human-readable phase token.

Run configured fast Python lint/type/static checks and re-derive the final affected surface after repair.

GitHub currently carries no check-run/status evidence for candidate `a4d722d6...`; source review therefore cannot substitute for the required executed final evidence.

---

## 11. Re-review PASS criteria

All rows must be true:

```text
[ ] canonical single-source replay without frame_uid reaches real P5/MACE owners
[ ] target frame_uid exactness remains intact
[ ] parent expected replay membership uses existing split authority with no redundant full scan
[ ] child single-source membership uses canonical loaded geometry only; mismatch fails instead of fallback reread
[ ] supported legacy replay identity remains explicit and bounded
[ ] replay mutation and mismatched continuation fail closed
[ ] same prepared replay source/split/view lineage remains stable

[ ] P5 TRAIN uses live supervised child execution in CV and production
[ ] progress uses incremental metrics, correct gradient-update accounting, validation phase, cadence, restart accounting
[ ] interruption/failure reaps owned children and preserves valid continuation

[ ] scheduler active membership comes from actual active task ownership, not overloaded TRAIN phase text
[ ] scheduler readiness uses fresh current optimizer progress, not completed_epochs > 0 or another sticky flag
[ ] validation/initialization idleness cannot authorize added GPU jobs
[ ] safe optimizer-phase telemetry can actually promote 1 -> 2 through the real P5 wiring
[ ] saturation throttling remains effective
[ ] one scheduler session covers pending jobs from all frozen selected sizes for each public command
[ ] completion order cannot alter CV reduction or production publication
[ ] reporter and scheduler share child observations/GPU telemetry without competing control planes

[ ] current P5 freezes avg_num_neighbors and other model-affecting architecture fields
[ ] e3nn TRAIN2/EVAL2 architecture parity passes
[ ] bounded real CuEq transient-realization -> portable-provider parity passes where required
[ ] architecture guard remains fail closed
[ ] old stakeholder pre-fix completed run is classified by actual realized architecture before current-config rejection/deletion
[ ] representation-only old run can reuse authentic TRAIN2 state; genuinely different model realization is preserved/recomputed

[ ] no new registry/DB/daemon/queue/state machine/second scheduler/second wrapper is introduced
[ ] final focused + affected regression + integration + static evidence executes on one unchanged candidate
[ ] full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package
```

Any unchecked row remains a blocker. Do not manufacture closure by narrowing the claim.

---

## 12. Reopen/escalation triggers

Return to Software Design only if implementation evidence shows one of the following:

1. canonical loaded MACE geometry cannot reproduce current single-source replay identity without changing accepted replay authority;
2. one command-wide adaptive admission surface cannot safely schedule independent per-size jobs without changing scientific ordering/currentness semantics;
3. exact transient accelerator realization cannot be reconstructed/authenticated through existing MACE conversion authority and would require a new persistent model/checkpoint representation;
4. the old completed workspace cannot be classified without changing accepted P5 scientific/model authority;
5. a discovered construction difference proves accepted D3 architecture itself contradictory rather than D4 realization drift.

Absent one of these triggers, keep the work in D4 and repair the existing owners rather than adding machinery.

---

## 13. Deferred qualification

Still deferred until the complete final release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS / MLIAP target-machine deployment qualification;
- full stakeholder production campaign qualification.

A tiny bounded real CuEq execution/reconstruction test required to close the concrete D4 checkpoint-realization defect is **not** deferred release qualification.
