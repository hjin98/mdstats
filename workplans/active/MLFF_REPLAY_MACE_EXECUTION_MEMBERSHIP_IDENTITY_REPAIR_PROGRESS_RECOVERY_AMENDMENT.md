---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-PROGRESS-RECOVERY-1
parent_workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR
parent_review_amendment_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-REVIEW-REOPEN-1
protocol_version: 6.0.0
status: active
created_date: 2026-09-09
runtime_evidence_date: 2026-09-09
applies_after_candidate: 41fd1cf0643fb7f42a8423c22368b2283f9176de
highest_affected_domain: D4 presentation/supervision realization under unchanged D3 P5/TRAIN2/MACE architecture
serious_challenge: none
precedence: this amendment narrows and strengthens R2 of the binding implementation-review amendment; all non-conflicting parent and review-amendment requirements remain binding
---

# MLFF P5/TRAIN2 progress-reporting recovery amendment

## 0. Why this amendment exists

Target-host runtime evidence resolved the apparent `cross-validate` hang. The process tree showed the public campaign process, the mdstats MACE wrapper, and a live MACE `run_train` child. `strace` on the MACE child showed repeated append activity on the run's `results/*_train.txt`, and `tail -f` showed normal optimizer/evaluation records, including optimizer records at epoch 5 and a completed replay-head evaluation.

Therefore the immediate observed state was **active training**, not a blocking campaign lock and not a replay-membership scan. The user-facing defect is that the current P5 path suppresses the established live training progress surface, making healthy long-running MACE work indistinguishable from a deadlock.

This is not a new observability requirement. mdstats already had a qualified MLFF training-progress contract before the V7 lifecycle reset. Recover that contract through the current P5/TRAIN2 owner instead of inventing a new reporting dialect.

The redundant replay reparsing blocker in the parent review amendment remains independently binding; this amendment does not withdraw it.

---

## 1. Historical authority to recover

The following repository history is task authority for the presentation behavior being restored.

### 1.1 `0.20.67a0` — live MACE progress owner

`docs/history/mlff/release_notes/PATCH_NOTES_0.20.67a0.md` records the original correction from generic `still running` heartbeats to live accelerator/training progress. The accepted behavior was:

- parse MACE's append-only metrics file;
- report the current MACE phase;
- report **exact completed gradient updates and percentage**;
- use the same exact update counter across all configured production-training epochs;
- report live GPU utilization and VRAM when `nvidia-smi` is available;
- print the exact resolved device, GPU model/memory, dtype, and e3nn/cuEquivariance backend at launch;
- keep interruption ownership in the supervising mdstats process and terminate the owned MACE process group on interruption.

The motivating defect then was almost identical to the current symptom: a long-running real-MACE operation exposed only a generic heartbeat and provided no quantitative indication that useful training work was progressing.

### 1.2 `0.20.75a0` — supervision cadence versus visible cadence

`docs/history/mlff/release_notes/PATCH_NOTES_0.20.75a0.md` separates control polling from user-visible progress:

- the MACE child supervisor continues to poll frequently (historically one second) so Ctrl-C, disk-reserve stops, and child exit remain responsive;
- **visible training/scheduler updates use `[execution].training_progress_interval_seconds`, default 10 seconds**;
- a fast control poll must not become a one-line-per-second console flood.

The generated/current example configuration still carries `execution.training_progress_interval_seconds = 10.0` with exactly this stated purpose. The current P5 path does not honor it because it bypasses the historical supervised child-progress route.

### 1.3 `0.20.237a0` — canonical MLFF progress grammar

`docs/specs/training_data/mlff_progress_reporting_format_spec.md`, the 0.20.237 release notes/qualification, and `release/SOURCE_PATCH_0.20.236a0_to_0.20.237a0.patch` normalized all MLFF progress output.

When applicable, dynamic fields appear in this order:

```text
status; progress; elapsed; eta; recent/current rate; average rate; stage-specific telemetry
```

Normative presentation rules:

- fields are semicolon-delimited;
- `elapsed=HH:MM:SS`;
- known `eta=HH:MM:SS`;
- unknown/not-yet-estimable `eta=--:--:--`;
- counted work uses `progress=completed/total (percent%)`;
- rates have explicit stable units;
- phase-only events use `status=phase; phase=...`;
- stage/run prefixes identify the emitter but do not replace canonical fields;
- progress state is presentation-only and never enters scientific/execution identity.

The historical TRAIN probe qualification included the exact form:

```text
phase=epoch 1/1
progress=12/48 (25.0%); unit=gradient-update
```

and the normalized supervisor emitted a TRAIN line of the form:

```text
[TRAIN <run-id>] status=running; <probe detail>; attempt=<n>; elapsed=HH:MM:SS; eta=--:--:--
```

The exact placement of `attempt` may be normalized to current field ordering, but the semantic fields above must be preserved.

---

## 2. Current regression and owner drift

Current `post_selection_execution.MacePostSelectionTrainer.__call__()` executes the long-running MACE child with a direct blocking:

```python
subprocess.run(..., capture_output=True, text=True)
```

This has three consequences:

1. child stdout/stderr is buffered until process termination rather than surfaced live;
2. the current P5 owner does not run the historical MACE metrics-file progress probe while the child is alive;
3. the existing `training_progress_interval_seconds` control is effectively bypassed on this current public training route.

Do **not** solve this by printing raw MACE stdout/stderr, tailing the whole metrics file from scratch every ten seconds, or adding a second progress daemon. The product already established a child-supervisor/progress-probe pattern; recover or refactor that capability into the current P5/TRAIN2 execution owner.

The V7 architecture reset was allowed to remove the retired public `train` lifecycle. It was not authority to discard the useful behavior of the shared private training supervision/progress surface when the same MACE/TRAIN2 engine remained part of `cross-validate` and `train-production`.

---

## 3. Required end state

### P1 — two-level CV + TRAIN progress

The public P5 owner must expose two nested but non-duplicative levels of progress.

**CV/run-matrix level** identifies the scientific run being executed or reused:

- `N_selected`;
- run index / total required run matrix;
- optimizer seed;
- fold index / fold count for CV;
- reused/restored versus executing;
- high-level phase transition such as preparing/materializing, launching TRAIN2, training, checkpoint evaluation, outer evaluation, or completed.

Example shape, using the canonical grammar rather than prescribing exact typography:

```text
[CV N=512] status=running; progress=1/5 (20.0%); unit=run; seed=0; fold=1/5; phase=training
```

A restored completed fold must be reported as restored/reused logical work and must not be counted twice.

**TRAIN child level** reports actual work inside the live MACE child:

```text
[TRAIN <run-id>] status=running; progress=<updates>/<total-updates> (<pct>%); unit=gradient-update; phase=<MACE phase>; epoch=<current>/<horizon>; elapsed=HH:MM:SS; eta=<HH:MM:SS|--:--:-->; <optional rate/GPU telemetry>
```

Do not wait until a whole selected size returns before the next visible line.

### P2 — exact progress numerator and denominator

Recover the historical exact-update semantics.

- The numerator is accepted observed optimizer progress from MACE's append-only metrics stream, not elapsed time and not an inferred epoch fraction.
- The denominator is the exact planned TRAIN2 optimizer-update budget for this run, derived from the current runtime plan/update geometry.
- Validation/evaluation records do not count as gradient updates.
- Multiple metrics records for the same update must not double-count.
- Restart must initialize visible progress consistently with authenticated completed TRAIN2 work and then count only newly observed updates.
- Full-horizon reclosure/reuse may report completed/restored status without relaunching MACE.

If the metrics format cannot uniquely identify optimizer updates for a current supported MACE version, fail the progress estimate conservatively (for example unknown ETA/phase-only) rather than inventing percentage. This must not change training authorization or completion authority.

### P3 — cadence

Restore the established separation:

- control/cancellation/child-exit polling remains frequent and responsive;
- visible training progress obeys `[execution].training_progress_interval_seconds`;
- generated/default value remains 10 seconds unless a separate accepted configuration change explicitly changes it;
- no per-batch console spam;
- a heartbeat still emits at the visible interval while the child is alive even if no new optimizer update completed, so a slow validation phase remains visibly alive.

### P4 — phase and validation visibility

The current stakeholder trace demonstrates that validation can itself take about a minute while training is otherwise healthy. A heartbeat must therefore distinguish optimizer work from validation/evaluation rather than freezing the last optimizer percentage with no explanation.

The metrics probe should expose the current MACE phase using the established vocabulary/available metrics records, e.g. optimizer epoch activity versus evaluation/validation. Exact phase spelling is delegated, but the operator must be able to tell that a long replay-head validation is active.

### P5 — accelerator/runtime telemetry

Recover the historically useful runtime diagnostics without making them requirements for correctness:

- before launch, report the resolved MACE device, dtype, and selected e3nn/cuEquivariance backend;
- when CUDA and `nvidia-smi` telemetry are available, heartbeat may include GPU utilization and VRAM usage;
- inability to obtain telemetry must not fail training;
- telemetry is observational and must not alter scheduler/scientific identity through this repair.

Reuse existing resource/telemetry helpers where available. Do not add another GPU monitor service.

### P6 — ETA/rates use the canonical formatter

Use `mdstats.training_data.progress_timing` formatting rather than private duration strings.

- elapsed/ETA use the canonical fixed-width grammar;
- ETA is `--:--:--` until representative progress makes it supportable;
- if update rate is reported, use an explicit `gradient-update/s` (or equivalently clear stable) unit;
- recent rate precedes average rate when both are shown;
- rate/ETA are observational and may reset/recalibrate after restart; they are not scientific evidence.

### P7 — supervision and failure semantics remain one owner

Do not create a second training engine or a parallel process-management stack.

Prefer one of these minimum-complexity realizations:

1. rewire P5 `MacePostSelectionTrainer` through an existing surviving generic MACE child supervisor/progress-probe owner; or
2. if the V7 reset removed that concrete helper, recover/refactor only the narrow reusable supervision/probe behavior from history into the current shared TRAIN2/MACE execution boundary.

The same owner must retain:

- child exit-code handling;
- bounded stdout/stderr diagnostic capture for failures;
- Ctrl-C/SIGTERM propagation/owned-child cleanup;
- existing disk-reserve/cancellation behavior where applicable;
- no orphan MACE worker after parent interruption.

A new daemon, second wrapper, new persistent progress record, event database, or log-forwarding service is forbidden.

### P8 — no authority drift

Progress reporting remains presentation state only.

It must not enter or modify:

- method identity;
- replay lineage;
- CV plan/acceptance;
- MACE execution authority/evidence;
- TRAIN2 continuation identity;
- checkpoint identity;
- selected-size/currentness/publication identity;
- scheduler admission decisions solely because reporting cadence changed.

---

## 4. Structural/performance interaction with the existing R1 repair

The progress recovery and redundant-replay-parse repair should reduce work together rather than create another polling I/O hotspot.

- Do not reread a 10k-frame replay ExtXYZ on every heartbeat.
- Do not reread the complete MACE metrics file on every heartbeat; consume append-only progress incrementally or use an equivalent bounded probe.
- Do not hash/revalidate large immutable scientific artifacts merely to print progress.
- Parent expected replay membership should still come from the already-authenticated single-source replay/split authority as required by the prior amendment.
- Child actual-membership validation should still piggyback on MACE-loaded data where the final R1 realization proves exact equivalence.

The reporting repair must therefore remain O(new progress records) or similarly bounded during live training, not O(total replay corpus) per heartbeat.

---

## 5. Acceptance additions

These are binding in addition to the parent workplan and prior review amendment.

### PR1 — recovered historical probe semantics

Using a bounded synthetic/fixture MACE metrics stream, prove the current probe reports:

```text
phase=epoch 1/1
progress=12/48 (25.0%); unit=gradient-update
```

or an equivalent canonical-field ordering with exactly the same semantics.

Add a counterexample proving evaluation records do not increment gradient progress.

### PR2 — cadence separation

With a fake/real bounded child that remains alive for more than one visible interval:

- internal supervision polls remain responsive at the control cadence;
- visible progress is throttled to configured `training_progress_interval_seconds`;
- default 10-second behavior is covered;
- no one-line-per-control-poll flood occurs.

### PR3 — live real-owner proof

Drive the real current P5 `MacePostSelectionTrainer` with a bounded MACE child whose metrics file receives new optimizer and evaluation records while the child remains alive.

Required observation: at least one canonical TRAIN heartbeat reaches the public command **before child termination**. A test that only inspects the final metrics file after `subprocess.run` returns is insufficient.

### PR4 — current stakeholder phase

Represent the observed structure of the target-host run: a replay-enabled P5 child with optimizer records followed by a materially slower replay-head evaluation.

Required output while the evaluation is in flight:

- command remains visibly alive;
- current run N/seed/fold context remains available;
- phase reports evaluation/validation rather than implying optimizer work is hung;
- update numerator is not falsely advanced during evaluation.

The test may use bounded sleep/fake metrics below the real supervisor; production-scale GPU training is not required.

### PR5 — restart accounting

Create authenticated partial TRAIN2 progress, interrupt through the real supervision owner, then resume.

Prove:

- existing completed updates appear as restored progress;
- new metrics advance from that point rather than restarting the visible counter from zero or double-counting;
- run identity, checkpoint authority, and scientific outputs remain unchanged by progress reporting.

### PR6 — CV run-matrix visibility

For a bounded two-size replay-enabled frozen design, prove the public `cross-validate` path reports each required size/run context before the expensive trainer returns, and later sizes are not hidden behind a first-size-only progress implementation.

### PR7 — canonical grammar and structural absence

Use focused source/AST checks plus behavioral capture to establish:

- current P5 long-running MACE execution does not use a bare blocking `subprocess.run(..., capture_output=True)` path that prevents live supervision;
- `training_progress_interval_seconds` is consumed by the current P5/TRAIN2 progress owner;
- progress uses shared `progress_timing` formatters;
- no legacy humanized ETA dialect is introduced;
- no raw per-batch MACE stdout passthrough is used as the primary progress UI;
- no new durable progress schema/service exists.

### PR8 — final evidence

Execute the original replay-membership acceptance matrix, the prior review's R1/R3 requirements, and PR1-PR7 on one final unchanged executable candidate. Full GPU/CuEq/LAMMPS/MLIAP final-release qualification remains deferred; the bounded real-MACE loader/supervisor tests required here must still execute where their dependencies are available.

---

## 6. Updated implementation sequence

1. **R1 membership performance correction:** eliminate avoidable parent and child full replay reparsing using existing replay/split authority and actual MACE-loaded geometry.
2. **R2/P1-P8 progress recovery:** rewire/recover the established supervised MACE progress path; do not add a new reporting framework.
3. **Adversarial closure:** replay geometry mutation, mismatched continuation, pre-fix same-workspace, multi-size composition.
4. **Final execution evidence:** all affected tests/static checks on one candidate, then independent Protocol 6 review.

The progress work is deliberately after/alongside the R1 I/O correction so a heartbeat implementation cannot accidentally institutionalize repeated corpus reads.

---

## 7. Additional PASS criteria

```text
[ ] live target-host symptom is classified as active MACE training, not lock wait
[ ] current P5 MACE child is supervised rather than silently buffered to completion
[ ] visible training heartbeat defaults to 10-second cadence via training_progress_interval_seconds
[ ] exact completed/total gradient-update percentage is recovered
[ ] evaluation/validation phase is visible without falsely advancing update count
[ ] CV output identifies N, seed, fold/run progress and reuse/execution state
[ ] elapsed/ETA/progress grammar matches the existing MLFF progress specification
[ ] optional GPU/VRAM/device/backend telemetry reuses existing observational helpers
[ ] restart progress does not double-count restored work
[ ] progress reporting causes no scientific/execution identity change
[ ] no full replay-file or full metrics-file reread is performed per heartbeat
[ ] no new daemon/wrapper/state schema/progress database is introduced
[ ] final affected execution evidence passes on one unchanged candidate
```

Until these rows and the earlier review-amendment rows close, the parent repair remains **NO-PASS / REOPENED**.
