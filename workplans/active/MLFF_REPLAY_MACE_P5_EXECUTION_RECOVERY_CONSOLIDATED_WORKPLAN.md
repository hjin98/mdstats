---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: reopened
created_date: 2026-09-09
last_review_date: 2026-09-10
implementation_branch: fix/mlff-replay-mace-membership-identity
reviewed_candidate_head: dadb83e680032a30fe55b42baf77bf13538f94a7
reviewed_candidate_tree: bb89fc4f8fc331bd988594a0e2aaea63bfdb10ae
review_verdict: no-pass
workplan_review_state: implementation-review-reopened-for-idempotent-replacement-and-final-evidence
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE, serial selected-size orchestration, recovery ownership, and acceleration architecture
serious_challenge: none
open_blockers: crash-idempotent ordering of authenticated stale-run replacement; final executed affected-surface acceptance
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier revisions and replay/progress/scheduler amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — Protocol 6 implementation review reopen

## 0. Review disposition

Executable candidate `dadb83e680032a30fe55b42baf77bf13538f94a7` is **NO-PASS / REOPENED** after independent SSDP Protocol 6 Software Design review.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE architecture remain coherent and unchanged.

Candidate `dadb83e...` closes the substantive source defects from the preceding review:

- append-only optimizer metrics are now counted by stream position rather than JSON-content equality;
- an exactly authenticated immediately-pre-fix continuation whose actual architecture is stale can now enter bounded replacement/retraining instead of raising forever;
- bounded tests now retain the real per-size scheduler, real `MacePostSelectionTrainer`, real incremental progress observer, owned subprocess/process-group termination path, and real TRAIN2 persistence owner while substituting only bounded child workload and synthetic telemetry;
- a real MACE model is driven through the actual TRAIN2 persistence owner and its persisted architecture digest is compared with the canonical live-model descriptor.

One newly exposed D4 recovery defect remains: the replacement path currently removes `materialization/` **before** `checkpoints/`. Interruption after the first successful removal leaves a durable authenticated continuation with no materialization. The next normal retry intentionally treats exactly that shape as ambiguous and refuses rebuild, recreating a permanent same-workspace dead end. The transition must be made monotonic/idempotent using existing ownership and cleanup semantics, without another recovery framework.

Final executable affected-surface evidence is also still unavailable for this exact candidate: GitHub exposes no status/check or Actions run for `dadb83e...`, and the independent review host could not clone/execute the repository because shell-network DNS access to GitHub is unavailable. Missing execution remains a functional-acceptance blocker, not a design revision.

---

## 1. Governing product and Frozen architecture

### 1.1 Product/scientific invariants

Preserve:

- exact selected target membership `T_N` and target `frame_uid` identity;
- frozen per-size CV and production horizons;
- fold construction, seeds, all-required CV acceptance, target-only acceptance semantics, optimizer/loss/objective/batching/EMA/checkpoint selection and EVAL2 conventions;
- replay training exposure distinct from independent TRUE_DFT replay admissibility;
- foundation scientific identity and path-free method identity;
- replay source/split/view/method lineage;
- multi-size experiment/currentness semantics and final-production freshness/publication rules.

### 1.2 Recovery/identity invariants

- current `single_source` replay uses existing canonical source/split geometry identity;
- supported `legacy_split` uses its existing historical identity domain;
- generated replay ExtXYZ remains transport, not a new scientific authority;
- actual MACE-loaded membership must authenticate exactly before its execution evidence is accepted;
- TRAIN2 continuation remains bound to exact run/materialization/MACE execution evidence;
- persisted actual TRAIN2 architecture, not today's interpretation of a missing historical config key, decides pre-fix architecture equivalence;
- ambiguous, corrupt, foreign, or unclassified state remains fail closed and is never destructively treated as the narrow stale-pre-fix case.

### 1.3 Execution/orchestration invariants

- selected sizes remain serial at the accepted outer D3 boundary;
- within one selected size, the existing adaptive scheduler may admit independent folds/seeds or production members;
- active futures own scheduler task liveness;
- scheduler readiness is transient execution state: current training phase + bounded fresh optimizer activity under the existing activity timeout;
- scheduler controls resource admission only; progress/reporting never becomes completion authority;
- runtime failure stops new admission and cancellation reaches/reaps owned active child processes;
- completion order cannot alter canonical reduction/publication;
- completed sibling evidence remains valid under its own identity/currentness when another run fails or is recomputed.

### 1.4 Acceleration/model invariants

- source/evaluation/deployment remain portable e3nn where current policy requires it;
- TRAIN2 may use configured transient CuEq/OEq realization;
- `only_cueq=false` retains portable-product semantics;
- architecture authentication remains fail closed;
- P5-frozen model-affecting values, including `avg_num_neighbors`, reach MACE exactly and are not recomputed from fold-local data.

### 1.5 Minimum-complexity constraint

Do not add a scheduler, cross-size queue, persistent queue, progress daemon, replay/checkpoint/update registry, compatibility database, migration framework, restart state machine, second MACE wrapper, second architecture authority, durable readiness state, or permanent stale-run archive namespace merely to close this repair.

Prefer ordering/reduction inside the existing run-owned cleanup and recovery path.

---

## 2. Closed source/conformance findings — preserve

### C1 — optimizer-event accounting

`_PostSelectionTrainingProgress` now uses its append cursor (`metric_offset` + partial-line remainder) as the exactly-once observation boundary. Every newly consumed complete valid `mode="opt"` row increments `optimizer_updates_since_launch` and refreshes activity, even when two rows have identical JSON content. Validation rows remain non-counting.

Focused tests now cover identical optimizer rows in one read and separate reads, no-new-byte refresh, partial-line completion, validation non-counting, and restart offset behavior.

### C2 — bounded optimizer readiness and reporting

The previously accepted readiness model remains intact: training phase + at least one newly observed optimizer completion + freshness under `parallel_training_epoch_activity_timeout_seconds`. Validation is immediately non-ready; ordinary polls without a new row do not revoke readiness inside the timeout; stale activity does.

The candidate also avoids publishing a fabricated zero progress denominator when a launch-time full-batch projection is not meaningful; authenticated TRAIN2 `planned_updates` remains the eventual exact owner.

### C3 — explicit replay identity routing

Current single-source P5 selects canonical replay geometry identity once. The child reconstructs canonical identity from MACE-loaded configurations and cannot enter legacy identity or replay-file membership reread after canonical mismatch. Supported legacy replay remains explicitly routed through the historical identity domain.

The existing pinned `mace.cli.run_train.run` parser/loader test remains the real MACE-loader boundary oracle. No new replay identity algorithm or loader abstraction is authorized absent failing execution evidence.

### C4 — scheduler liveness and serial selected-size topology

Active scheduler membership is derived from the live future/task relation. Human-readable MACE phase no longer owns task liveness. Selected sizes remain serial; no command-wide cross-size scheduler has been introduced.

### C5 — pre-fix architecture classification and nominal replacement

The narrow immediately-pre-fix classifier continues to authenticate materialization, continuation, MACE execution evidence, and actual persisted TRAIN2 architecture before any replacement decision.

Candidate `dadb83e...` now returns an execution-local `replace_stale_continuation` decision only when that exact authenticated pre-fix state has a valid actual architecture different from the current authorized training realization. Equal architecture reuses immutable state; foreign/corrupt states remain outside this branch.

The setup then clears continuation reuse and resets training to epoch zero, while the execution path removes only the affected run's derived materialization/checkpoint state. This closes the previous "raise forever" defect in nominal uninterrupted execution.

### C6 — real scheduler -> real trainer/process acceptance boundary exists

New bounded tests keep the real per-size P5 scheduler and real `MacePostSelectionTrainer` live. A tiny executable child below the trainer appends optimizer metrics; synthetic GPU telemetry is injected only at the external telemetry boundary. The tests exercise promotion, active failure, cancellation, SIGINT/SIGTERM/SIGKILL process-group ownership, queued-work suppression, and absence of incomplete acceptance.

This is the correct proxy-proof boundary. Do not replace these owners with another test trainer for final acceptance.

### C7 — real TRAIN2 architecture persistence boundary exists

The fixture can now construct a real MACE model from the current materialization and drive it through the actual `_Train2Runtime.persist_epoch()` owner. The new test checks that `train2_runtime.json` and `train2_runtime.pt` publish the same `model_architecture_digest` and that it equals the canonical descriptor reconstructed from the materialization.

Synthetic digest mutation remains permissible only for classifier branch/counterfactual coverage; it is no longer the sole producer-boundary evidence.

---

## 3. Blocking repair R3 — make authenticated stale-run replacement interruption-idempotent

### 3.1 Defect

For the narrow architecture-stale pre-fix case, `_classify_post_selection_materialization()` returns both:

```text
rebuild_materialization = True
replace_stale_continuation = True
```

`_execute_post_selection_run_locked()` currently performs:

```text
shutil.rmtree(material_directory)
shutil.rmtree(checkpoint_directory)
```

in that order.

This ordering is not restart-safe.

Counterfactual:

1. the old materialization and TRAIN2 continuation fully authenticate;
2. actual persisted architecture is proven stale;
3. the owner removes `materialization/` successfully;
4. the process is interrupted before `checkpoints/` is removed;
5. the next invocation authenticates the still-durable TRAIN2 continuation;
6. `_classify_post_selection_materialization()` sees `materialization/` absent + durable continuation and deliberately raises the preservation error instead of rebuilding.

The same canonical run is now blocked indefinitely without manual deletion. That contradicts the protected same-workspace recovery outcome and the workplan's bounded recomputation requirement.

This is an ordering/idempotency defect in delegated D4 cleanup, not evidence for a new recovery state machine.

### 3.2 Required end state

Make the destructive transition monotonic under the existing classifier/rebuild semantics.

The minimum justified realization is to retire the proven-stale continuation/checkpoint state **before** removing the old materialization. Then, if execution is interrupted between the two successful removals, the next invocation sees a historical materialization with no durable continuation; the already-existing classifier can treat that exact authenticated pre-fix materialization as disposable/rebuildable and continue normally.

Equivalent existing-owner ordering is acceptable if it establishes the same property. Do not introduce a tombstone, persistent replacement flag, migration record, compatibility database, new run identity, permanent backup namespace, or second recovery authority.

Preserve:

- complete authentication/classification before the first destructive action;
- the run activity lease across classification and cleanup;
- architecture-equal reuse with no cleanup;
- ambiguous/corrupt/foreign preservation with no cleanup;
- sibling run/size evidence untouched;
- no incomplete acceptance/publication during replacement.

### 3.3 Required failure-injection oracle

Through the real public P5 recovery owner:

1. construct the narrow authenticated architecture-stale pre-fix run plus one completed sibling;
2. inject a bounded interruption **after stale checkpoint/continuation retirement succeeds but before old materialization retirement/rebuild completes**;
3. prove the interrupted invocation publishes no incomplete acceptance;
4. rerun normally in the same workspace;
5. prove only the affected run is retrained from epoch zero under current authority and reaches authenticated TRAIN2/EVAL2 evidence;
6. prove the completed sibling is byte-identical/current;
7. retain controls showing architecture-equal state is reused and corrupt/foreign/unclassified state never reaches destructive cleanup.

The failpoint must keep the production recovery owner live. Patching the low-level removal call to raise at the intended boundary is acceptable; reimplementing recovery in the fixture is not.

---

## 4. Blocking evidence E2 — execute final acceptance on one unchanged candidate

The source/test shape for the previously missing real-owner claims is now adequate, but no execution evidence is available for `dadb83e680032a30fe55b42baf77bf13538f94a7`:

- GitHub combined statuses: none;
- GitHub Actions runs for the exact head: zero;
- the independent review host cannot clone the repository through shell networking, so it cannot substitute a local rerun.

After R3 is implemented, execute the complete affected surface on the final unchanged executable candidate. At minimum:

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

Also execute affected subsets for:

- TRAIN2 continuation/checkpoint content authentication and architecture persistence;
- replay restart/currentness and supported legacy compatibility;
- multi-size CV/final-production/currentness/publication;
- P5 storage/run-activity lease, interrupted replacement, cancellation, and failure behavior;
- repository-configured fast Python lint/type/static checks;
- structural absence/ownership claims: no current single-source replay file-reread fallback, no bare blocking P5 training `subprocess.run`, one scheduler telemetry owner per interval, serial selected-size orchestration, no fold-local `avg_num_neighbors`, and no new durable compatibility/recovery framework.

Use Semgrep if available. On hosts without Semgrep/Serena, bounded validated AST/source/search fallback is acceptable when it establishes the same structural claim and its limitations are recorded. Tool absence is not itself a product blocker.

If final impact cannot be bounded confidently, run the broader P5/P7/campaign/replay/storage regression.

A required check that does not execute is a blocker.

---

## 5. Re-review PASS criteria

All must be true on one unchanged final executable candidate:

```text
[x source] append-only identical optimizer rows count as distinct events
[x source] no-new-byte / partial-line / restart-offset semantics do not double-count
[x source] validation rows remain non-counting and non-ready
[x source] scheduler liveness comes from active task ownership
[x source] readiness uses training phase + bounded fresh optimizer activity
[x source] selected sizes remain serial
[x source] current single-source replay selects canonical identity once and cannot enter legacy/file fallback on mismatch
[x source] pre-fix architecture comparison uses persisted actual TRAIN2 architecture
[x source] architecture-equal exact pre-fix state reuses immutable state
[x source] architecture-different exact pre-fix state has a bounded same-run replacement path in uninterrupted execution
[x source] real scheduler -> real MacePostSelectionTrainer -> subprocess tests exist
[x source] real TRAIN2 MACE architecture-persistence test exists

[ ] stale-run replacement ordering remains recoverable after interruption between cleanup steps
[ ] only the affected stale run is retrained; completed sibling evidence remains untouched
[ ] corrupt/foreign/ambiguous state never enters destructive replacement

[ ] focused optimizer/progress tests execute
[ ] public stale-run recomputation + interruption/retry tests execute
[ ] real scheduler/trainer promotion and cancellation/reaping tests execute
[ ] real TRAIN2 architecture-persistence test executes
[ ] pinned real MACE parser/loader replay identity tests execute
[ ] complete affected regression/integration/project static checks execute
[ ] e3nn/CuEq TRAIN2/EVAL2 architecture guards remain fail closed on the available bounded functional surface
[ ] no new registry/DB/daemon/queue/state machine/second scheduler/second wrapper/cross-size scheduler is introduced
[ ] production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred
```

No unchecked row may be converted into a pass by weakening the claim or by treating test code as executed evidence.

---

## 6. Routing

This remains D4 implementation work. The required source repair is an ordering/idempotency correction inside existing run-owned recovery, not a redesign.

Return to Software Design only if implementation evidence shows that safe restart after the replacement interruption cannot be expressed using existing run ownership/classification/cleanup semantics without materially new durable state, or another genuine Frozen-architecture contradiction appears.

Otherwise implement R3, run E2 on the resulting unchanged candidate, and return for final independent review.

---

## 7. Deferred final-release qualification

Still deferred until the complete final release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS/MLIAP target-machine deployment qualification;
- full stakeholder production campaign qualification.

The bounded MACE/CuEq/control-path tests required above are implementation functional evidence, not production-scale qualification.
