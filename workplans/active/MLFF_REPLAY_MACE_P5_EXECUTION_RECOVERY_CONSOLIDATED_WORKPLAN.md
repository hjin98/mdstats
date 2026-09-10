---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: reopened
created_date: 2026-09-09
last_review_date: 2026-09-10
implementation_branch: fix/mlff-replay-mace-membership-identity
reviewed_candidate_head: 577908bf117d033357e2bfb1847e5ed16047d288
reviewed_candidate_tree: 07ae2d5930289d99330d5a4d3abb429ad3fb28d5
review_verdict: no-pass
workplan_review_state: implementation-review-reconciled-reopen
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE, serial selected-size orchestration, and acceleration architecture
serious_challenge: none
open_blockers: append-only optimizer-event accounting; bounded recomputation of authenticated architecture-stale pre-fix run; real scheduler-to-trainer/process evidence; final executed affected-surface evidence
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier revisions and replay/progress/scheduler amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — Protocol 6 implementation review reopen

## 0. Review disposition

Executable candidate `577908bf117d033357e2bfb1847e5ed16047d288` is **NO-PASS / REOPENED** after independent SSDP Protocol 6 Software Design review.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE architecture remain coherent and unchanged. The candidate closes the previous source-level defects in scheduler liveness/readiness, explicit current replay identity routing, and pre-fix architecture classification. Those corrections are accepted and must be preserved.

The remaining work is a narrow D4 closure:

1. remove an incorrect content-based deduplication rule from the append-only MACE optimizer metrics observer;
2. make an exactly authenticated, immediately-pre-fix run whose actual model architecture is noncurrent transition to bounded replacement/recomputation instead of failing forever on every retry;
3. strengthen acceptance at the real scheduler -> `MacePostSelectionTrainer` -> owned subprocess boundary and at the real TRAIN2 architecture-persistence boundary;
4. execute the complete affected regression/integration/static surface on one unchanged final candidate.

Do not reopen D3 or add another compatibility/control framework to solve these local realization defects.

---

## 1. Governing invariants

### 1.1 Scientific and method invariants

Do not change:

- exact selected target membership `T_N` and target `frame_uid` identity;
- frozen per-size CV and production horizons;
- fold construction, seeds, all-required CV acceptance, and target-only acceptance semantics;
- optimizer, loss, objective weighting, batching, EMA, checkpoint ranking, or evaluation conventions;
- replay training exposure versus independent TRUE_DFT replay admissibility;
- foundation scientific identity;
- multi-size experiment/currentness semantics;
- final-production freshness/currentness/publication semantics.

### 1.2 Identity/recovery invariants

- current `single_source` replay uses existing replay source/split/canonical geometry identity;
- supported `legacy_split` replay uses its existing historical identity domain;
- generated replay ExtXYZ is transport, not scientific authority;
- actual MACE-loaded membership must authenticate exactly before training evidence is accepted;
- replay source/split/view/method lineage must not churn to repair execution transport;
- TRAIN2 continuation remains bound to exact run/materialization/MACE execution evidence;
- persisted actual TRAIN2 architecture, not present-day interpretation of a missing historical config field, decides pre-fix architecture equivalence;
- ambiguous/corrupt/foreign state remains preserved and fail closed.

### 1.3 Execution/control invariants

- selected sizes remain serial at the accepted outer D3 boundary;
- within one selected size, the existing adaptive scheduler may admit independent folds/seeds or production members;
- scheduler task liveness comes from active task ownership, not human-readable MACE phase text;
- scheduler controls resource admission only;
- reporter/progress is observational only;
- true optimizer activity requires current training phase plus bounded freshness under the existing activity-timeout policy;
- completion order cannot alter canonical reduction/publication order;
- runtime failure stops new admission and cancels/reaps owned active children;
- completed sibling evidence remains valid according to its own identity/currentness and is never rolled back merely because another run fails.

### 1.4 Acceleration/model invariants

- source/evaluation/deployment remain portable e3nn where current policy requires it;
- TRAIN2 may use the configured transient CuEq/OEq realization;
- `only_cueq=false` retains portable-product semantics;
- model architecture authentication remains fail closed;
- model-affecting fields frozen by P5, including `avg_num_neighbors`, reach MACE exactly and are not recomputed from fold-local data.

### 1.5 Minimum-complexity rule

Do not add a scheduler, cross-size queue, persistent queue, progress daemon, update registry, replay/checkpoint registry, compatibility database, migration framework, restart state machine, second MACE wrapper, second architecture authority, or durable progress/recovery representation. Prefer deletion, direct routing, and existing run-owned recovery mechanisms.

---

## 2. Closed source repairs — preserve

### C1 — scheduler liveness

Candidate `577908bf...` derives active scheduler membership from the actual `Future -> task` mapping. Submission/completion no longer overload child-reported `phase` with scheduler lifecycle tokens, and readiness counting considers only active tasks.

This closes the prior lifecycle/phase conflation at source level.

### C2 — bounded optimizer readiness

`_PostSelectionTrainingProgress` now tracks current execution phase, newly observed optimizer progress, the monotonic time of the latest accepted optimizer row, and the existing configured `parallel_training_epoch_activity_timeout_seconds`.

The resulting readiness semantics are correct in shape:

- first-epoch optimizer work can become ready after its first real optimizer completion;
- validation is immediately non-ready;
- a slow legitimate optimizer step may remain ready across multiple polls while within the configured timeout;
- stale optimizer activity becomes non-ready;
- visible reporting cadence does not own scheduler admission.

Preserve this behavior, subject only to R1 below: every genuine newly appended optimizer record must refresh the activity observation.

### C3 — serial selected-size architecture

The candidate preserves the accepted outer serial selected-size topology. Do not flatten different selected sizes into one scheduler session.

### C4 — explicit current replay identity routing

Current P5 `single_source` now transports authenticated canonical replay geometry identities process-locally and selects the `canonical_geometry` execution domain. The child reconstructs canonical identity from MACE-loaded replay configurations and fails on mismatch; current P5 cannot retry historical identity or reread replay-file membership after a canonical mismatch. Supported legacy replay selects the historical domain.

The existing test suite already contains a bounded real `mace.cli.run_train.run` path that uses the pinned MACE parser and loader construction before substituting only the expensive `tools.train` call. Its single-source replay case authenticates canonical identities from the real loaded collection. The candidate additionally supplies explicit-domain and no-file-reread negative tests. Therefore no new identity algorithm or additional loader abstraction is required; final execution of these tests remains part of E2.

### C5 — pre-fix architecture comparison direction

Continuation authentication no longer silently projects an absent historical `compute_avg_num_neighbors` field through today's default before classification. For the exact immediately-pre-fix representation, current code compares persisted actual TRAIN2 `model_architecture_digest` with the current authorized training realization reconstructed through existing MACE/CuEq owners.

Architecture-equal state may be reused without rewriting the old materialization. Foreign/corrupt state remains fail closed. Preserve this bounded classifier.

---

## 3. Blocking repair R1 — count append-only optimizer events by stream position, not JSON content

### 3.1 Defect

`_PostSelectionTrainingProgress._read_metrics()` already owns an append-only cursor through `metric_offset` plus `metric_remainder`. Every complete JSON line consumed beyond that cursor is therefore a new metrics event exactly once.

The candidate nevertheless hashes each `mode="opt"` record and suppresses it when its complete JSON content equals the preceding optimizer record. Content equality is not event identity.

Pinned MACE 0.3.16 `MetricsLogger.log()` opens the results file in append mode and writes one JSON line for each call. `train_one_epoch()` calls that logger after each optimizer step. Two genuine optimizer steps may therefore produce byte-identical serialized metrics. Suppressing the second row undercounts gradient updates and fails to refresh `last_optimizer_update_monotonic`; an actively training job can later be declared stale.

### 3.2 Required repair

Use the existing append cursor as the sole exactly-once observation mechanism:

- delete `_last_optimizer_record_digest` and the content-digest suppression branch;
- every newly consumed, complete, valid JSON row with `mode == "opt"` increments `optimizer_updates_since_launch` exactly once and refreshes the activity timestamp;
- `mode == "eval"` remains non-counting and changes readiness to validation/non-ready;
- an incomplete trailing line remains buffered and counts only after it becomes complete;
- refreshing with no new bytes changes neither update count nor activity timestamp;
- restart continues to initialize its numerator from authenticated TRAIN2 state and its byte cursor at the pre-existing metrics boundary;
- do not add an optimizer-update ID, persisted event ledger, dedup registry, file rescan, or schema.

### 3.3 Required focused oracle

Against the real `_PostSelectionTrainingProgress` parser:

1. append two byte-identical valid `mode="opt"` lines in one read: count both;
2. append the same pair across separate reads: count both and advance activity on the second;
3. refresh with no new bytes: count neither again;
4. split one JSON line across two reads: count exactly once after its newline arrives;
5. append `mode="eval"`: update phase/readiness but not optimizer count;
6. construct restart with historical metrics already present: historical bytes are ignored and only later appended optimizer rows count.

The identical-row oracle should fail on `577908bf...` and pass after the direct deletion above.

---

## 4. Blocking repair R2 — make authenticated architecture-stale pre-fix state recomputable

### 4.1 Defect

Candidate `577908bf...` correctly refuses to reuse an immediately-pre-fix run whose authenticated actual TRAIN2 architecture differs from current authority. It then raises `PostSelectionExecutionError` while leaving the same run root unchanged.

A normal retry re-enters the same classifier, sees the same proven-noncurrent state, and raises again. The stated end state — preserve/classify the old run, then recompute only that affected run under current authority — is therefore not operationally reachable.

### 4.2 Required repair

Do not create a compatibility database, migration layer, second run identity, generic quarantine service, or new recovery state machine.

Once, and only once, the existing classifier has established all of the following:

- the materialization/continuation is internally authentic;
- it is the narrowly recognized immediately-pre-fix representation;
- its persisted actual architecture is valid and genuinely different from the current authorized training realization;
- the run activity lease is held and no live sibling owner can race the transition;

use the minimum existing run-owned scratch/recovery mechanism to retire or replace only that proven-stale derived run state and execute the same canonical run identity afresh under current authority.

Preservation means **classification before destruction** and fail-closed treatment of ambiguous/corrupt/foreign evidence. It does not require scientifically noncurrent derived scratch to block the canonical run forever. If an already-existing bounded backup/diagnostic mechanism is required by repository policy, reuse it; do not invent a permanent archive namespace for this case.

Required behavior:

- architecture equal -> reuse immutable completed state;
- exact immediately-pre-fix + architecture different -> bounded replacement/recompute of only that run;
- ambiguous/corrupt/foreign -> preserve and fail typed; no auto-delete;
- no sibling run/size state is touched;
- no incomplete acceptance/publication is produced during replacement.

### 4.3 Required oracle

Through the public P5 recovery path:

1. classify an architecture-different immediately-pre-fix completed run before any removal;
2. rerun/recovery replaces and retrains only that run;
3. replacement publishes current authenticated TRAIN2/EVAL2 evidence;
4. sibling completed evidence remains byte-identical/current;
5. corrupt/foreign controls remain preserved and refuse destructive replacement.

Synthetic architecture mutation may be used for branch/counterfactual coverage, but it is not by itself proof that the real TRAIN2 producer supplies the decisive architecture fact; E1 covers that owner boundary.

---

## 5. Blocking evidence E1 — close real owner boundaries

### 5.1 Real scheduler -> real trainer -> owned process

The new promotion/failure tests keep the real per-size scheduler live but replace `MacePostSelectionTrainer` with `_PromotionTrainer`, which manually invokes `request.progress_observer`. They therefore do not prove that the production trainer actually forwards live metrics observations to the scheduler. The failure double also waits directly on the cancellation event, so it does not prove the real trainer terminates/reaps its owned subprocess group.

Add bounded integration through:

```text
real per-size P5 scheduler
 -> real MacePostSelectionTrainer
      -> tiny deterministic wrapper subprocess below the trainer
```

The child wrapper may replace expensive MACE training and synthetic GPU telemetry may be supplied at the external telemetry boundary. Do not replace `MacePostSelectionTrainer`, `_PostSelectionTrainingProgress`, or `progress_observer` wiring under acceptance.

Prove:

- a trainer-owned child appends optimizer metrics and the real trainer forwards the observation into the real scheduler;
- safe telemetry can cause actual scheduler promotion/admission of a second run;
- when one active child fails while another is active and a third remains queued, new admission stops;
- the real trainer receives cancellation and terminates/reaps the active sibling subprocess group;
- the queued third run never launches;
- no incomplete CV acceptance or production publication is created;
- already-valid continuation/checkpoint evidence remains intact.

This is bounded control-path evidence, not production GPU qualification.

### 5.2 Real TRAIN2 architecture persistence

The pre-fix classifier tests currently inject `model_architecture_digest` into serialized fixture state. That is suitable for deterministic classifier branch coverage, but the decisive production fact must also be established independently through the real architecture-producing owner.

At least one bounded test must execute:

```text
real pinned MACE model construction / training realization
 -> real TRAIN2 durable persistence owner
 -> persisted summary + companion model_architecture_digest
 -> existing canonical architecture descriptor
```

and prove the persisted digest equals the live model's canonical architecture digest without rewriting the summary/companion after publication.

This test need not reproduce a long stakeholder run. Its purpose is to close the producer boundary that the classifier consumes. If an applicable historical TRAIN2 format truly lacks architecture identity, do not backfill or guess it; classify from already-authenticated checkpoint/model state through existing architecture owners if exact, otherwise fail typed.

Keep the current equal/different synthetic counterfactuals as classifier tests, but do not present their injected digest as evidence that the production TRAIN2 owner generated that fact.

---

## 6. Blocking evidence E2 — final executable acceptance

GitHub exposes no check-runs/status evidence for executable candidate `577908bf117d033357e2bfb1847e5ed16047d288`, and this review environment cannot execute the repository locally. Source inspection cannot substitute for Protocol 6 implementation acceptance.

After R1/R2 and E1 are implemented, run one unchanged final executable candidate through the complete affected surface. At minimum:

```text
pytest -q \
  tests/test_mlff_replay_mace_p5_execution_recovery.py \
  tests/test_mlff_training_parallel_scheduler.py \
  tests/test_mlff_replay_unify1b.py \
  tests/test_mlff_replay_unify1c.py \
  tests/test_mlff_replay_unify1d.py \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r8_guards.py \
  tests/test_mlff_target_size_p5_r9_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_p5_r11_guards.py \
  tests/test_mlff_downstream_integration_closure.py \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_mace_execution_semantics.py \
  tests/test_mlff_mace_execution_semantics_assembled.py \
  tests/test_mlff_train2a_policy.py \
  tests/test_mlff_train2b_runtime.py
```

Also execute applicable affected subsets for:

- TRAIN2 continuation/checkpoint-state/content authentication and real architecture persistence;
- replay restart/currentness and supported legacy compatibility;
- multi-size CV/final-production/currentness/publication;
- P5 storage/run-activity lease, recovery, and cancellation/failure behavior;
- configured fast Python lint/type/static checks;
- structural checks for current single-source no-reread routing, no bare blocking P5 `subprocess.run` path, one telemetry owner per scheduler interval, serial outer selected-size orchestration, no fold-local `avg_num_neighbors`, and absence of new durable compatibility/control machinery.

Use Semgrep when available; otherwise bounded validated AST/source checks are acceptable for structural absence claims. If final impact cannot be bounded confidently, run the broader P5/P7/campaign/replay/storage regression.

The existing real pinned-MACE parser/loader single-source test must execute as part of this closure; no additional loader abstraction is required unless it actually fails.

The bounded real CuEq TRAIN2 -> authenticated reconstruction -> portable e3nn EVAL2 functional test remains required where the relevant qualified CuEq stack is available/needed for the concrete architecture-parity claim. Long production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package.

A required check that does not execute is a blocker.

---

## 7. Re-review PASS criteria

All must be true on one unchanged final executable candidate:

```text
[x source] active scheduler membership comes from active task ownership
[x source] readiness uses current training phase + bounded fresh optimizer activity
[x source] selected sizes remain serial
[x source] current single-source P5 selects canonical identity once and cannot enter legacy/file fallback on mismatch
[x source] supported legacy replay remains explicit in its historical identity domain
[x source] pre-fix architecture comparison uses persisted actual TRAIN2 architecture, not today's missing-key default

[ ] every newly consumed complete MACE opt row counts exactly once regardless of content equality
[ ] no-new-byte refresh / partial-line buffering / restart offset do not double-count
[ ] validation rows do not increment optimizer progress and revoke optimizer readiness

[ ] architecture-different exact immediately-pre-fix state can replace/recompute only that run
[ ] architecture-equal exact immediately-pre-fix state reuses authentic state
[ ] corrupt/foreign/ambiguous state remains preserved and fail closed

[ ] real pinned MACE parser/loader canonical replay identity test executes successfully
[ ] canonical mismatch executes with zero post-load replay membership reread
[ ] real TRAIN2 persistence produces the architecture digest consumed by recovery

[ ] real per-size scheduler -> real MacePostSelectionTrainer metrics wiring can drive promotion
[ ] active-run failure stops new admission and real trainer-owned sibling process is cancelled/reaped
[ ] queued work is not admitted after failure
[ ] no incomplete acceptance/publication is created and completed sibling evidence is preserved

[ ] e3nn/CuEq TRAIN2/EVAL2 architecture guards remain fail closed
[ ] current P5 freezes avg_num_neighbors and other model-affecting architecture fields
[ ] no new registry/DB/daemon/queue/state machine/second scheduler/second wrapper/cross-size scheduler is introduced
[ ] complete focused + affected regression + integration + configured static evidence executes successfully
[ ] full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred
```

Any unchecked row remains a blocker. Do not narrow the claim, weaken an oracle, or rewrite authority to manufacture closure.

---

## 8. Routing and genuine escalation triggers

This remains a D4 repair. Implement R1 by deleting the incorrect content-dedup behavior; implement R2 by reusing existing run-owned replacement/recovery mechanics after exact classification; strengthen the real-owner tests in E1; then execute E2.

Return to Software Design only if new evidence shows that:

1. canonical replay identity cannot be reconstructed from the real pinned MACE-loaded geometry without changing accepted replay authority;
2. exact optimizer activity cannot be represented using the existing append-only metrics stream/phase/activity-timeout contract;
3. safe bounded replacement of a proven architecture-stale immediately-pre-fix run cannot be expressed using existing run ownership/recovery rules;
4. correct failure propagation requires a materially new scheduling/process-ownership architecture;
5. transient accelerator architecture cannot be reconstructed through existing conversion owners;
6. accepted serial selected-size D3 topology is independently shown inadequate under a governing product/resource requirement; or
7. accepted D3 becomes contradictory or incapable of preserving D1/D2 semantics.

Absent those triggers, keep the repair local and subtractive.

---

## 9. Deferred final-release qualification

Still deferred until the complete final release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS/MLIAP target-machine deployment qualification;
- full stakeholder production campaign qualification.
