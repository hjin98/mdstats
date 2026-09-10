---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: reopened
created_date: 2026-09-09
last_review_date: 2026-09-10
implementation_branch: fix/mlff-replay-mace-membership-identity
source_candidate_under_review: 577908bf117d033357e2bfb1847e5ed16047d288
source_candidate_tree: 07ae2d5930289d99330d5a4d3abb429ad3fb28d5
review_verdict: no-pass
workplan_review_state: reopened-after-implementation-review
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE, serial selected-size orchestration, and acceleration architecture
serious_challenge: none
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier replay-membership/review/progress/scheduler amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — Protocol 6 implementation review reopen

## 0. Review disposition

Executable candidate `577908bf117d033357e2bfb1847e5ed16047d288` is **NO-PASS / REOPENED** after an independent SSDP 6 Software Design review.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE architecture remain coherent and unchanged. The candidate substantially improves the D4 realization and closes the two scheduler-source defects from the previous review. Remaining blockers are narrower:

1. canonical single-source replay routing is source-correct, but the representation-equivalence test does not exercise MACE's real dataset loader and therefore cannot close the real-owner boundary;
2. pre-fix TRAIN2 recovery is not yet proved by authentic historical execution evidence: the new tests create a fake completed run with no architecture digest and then rewrite the TRAIN2 summary/companion to inject the desired digest;
3. when an authentic pre-fix architecture is different, current code preserves it and raises on every retry, so the required "preserve and recompute only this run" end state is not operationally reachable;
4. final affected regression/integration/static evidence is absent for this exact candidate: GitHub has no check-runs/statuses, and the review environment cannot execute the repository locally.

Do not reopen already-closed scheduler design or introduce another compatibility/recovery framework. Repair only the remaining owner/evidence boundaries below.

---

## 1. Governing architecture and invariants

The accepted post-selection topology remains:

```text
frozen ordered selected-size collection
 -> serial outer selected-size iteration
      -> exact pending CV folds/seeds or production members for one size
      -> ONE existing adaptive TRAIN admission session for that size
      -> supervised MACE/TRAIN2 execution
      -> authenticated checkpoint/EVAL2
      -> canonical per-size CV reduction or production publication
 -> campaign-level aggregation/currentness
```

Final production retains the collection-wide accepted-CV preflight before **any new production job**. That barrier does not create cross-size training scheduling or transactional rollback of independently valid completed evidence.

Preserve all of the following:

- exact selected target membership `T_N` and target `frame_uid` identity;
- frozen per-size CV/production horizons, folds, seeds, all-required acceptance, optimizer/loss/objective/batching/EMA/checkpoint semantics;
- replay training exposure distinct from independent TRUE_DFT replay admissibility;
- canonical single-source replay source/split/canonical-geometry identity and bounded legacy replay identity;
- generated replay ExtXYZ as transport, never a new scientific identity;
- exact MACE-loaded membership authentication before training evidence is accepted;
- TRAIN2 continuation bound to exact run/materialization/MACE execution evidence;
- source/evaluation/deployment portable e3nn where current policy requires it, with configured transient CuEq/OEq TRAIN2 realization allowed;
- `only_cueq=false` portable-product semantics;
- frozen model-affecting fields including `avg_num_neighbors`, with no fold-local recomputation;
- selected sizes serial at the accepted outer D3 boundary;
- completion order unable to change canonical reduction/publication;
- scheduler/resource/progress observations excluded from scientific identity;
- completed sibling evidence preserved according to its own identity/currentness after another run fails.

Forbidden repair machinery remains: no new scheduler, cross-size queue, persistent queue, progress daemon, replay/checkpoint registry, compatibility database, migration framework, restart state machine, second MACE wrapper, second architecture authority, or durable recovery representation. Prefer direct routing, bounded replacement of proven stale run-owned state, and reuse of existing owners.

---

## 2. Closed source repairs — preserve, do not reopen without contrary evidence

### C1 — scheduler task liveness

Candidate `577908bf...` closes the prior lifecycle/phase conflation at source level:

- active scheduler membership is derived from the active-future mapping;
- submission/completion no longer overwrite human-readable MACE `phase` with scheduler lifecycle tokens;
- readiness counting iterates only currently active tasks.

Preserve this realization. Final executed regression remains required.

### C2 — bounded true-epoch/optimizer readiness

Candidate `577908bf...` closes the prior sticky `completed_epochs > 0` defect at source level. Scheduler readiness is now process-local and requires:

1. current execution phase is training;
2. at least one real optimizer update has been observed for this execution/resume;
3. the most recent optimizer update is within the existing configured `parallel_training_epoch_activity_timeout_seconds` window.

Validation is immediately non-ready; first-epoch optimizer work can become ready; a slow legitimate optimizer step remains ready across ordinary telemetry polls while inside the timeout; stale activity becomes non-ready. Do not persist this readiness state.

Preserve the existing 60-second calibration semantics, resource projection, fluctuation averaging, saturation throttling, CPU/RAM bounds, and one shared telemetry sample per scheduler observation interval.

### C3 — serial selected-size architecture

Candidate `577908bf...` does not reintroduce the previously retracted cross-size scheduler. Preserve the accepted serial outer selected-size topology.

### C4 — current single-source replay routing

The production routing direction is now correct:

- current `single_source` transports authenticated canonical replay geometry identities process-locally;
- MACE launch authority carries the minimum `canonical_geometry` discriminator;
- the child reconstructs only canonical identities from loaded replay configurations and fails on mismatch;
- current single-source no longer retries historical identity or rereads replay ExtXYZ membership after a canonical mismatch;
- legacy replay remains explicitly routed through its legacy identity domain.

The optional discriminator remains execution routing, not replay lineage or a new scientific identity. Preserve that distinction.

---

## 3. Blocking repair R1 — close canonical replay identity across the **real MACE loader**

### Defect

The new representation-equivalence test imports `mace.data.Configuration` but manually constructs the object from ASE arrays. That bypasses the production transformation under acceptance: MACE's real ExtXYZ/dataset loader.

The separate no-file-fallback test likewise inserts caller-constructed `Atoms` objects into a fake `collections.train`. These tests establish routing logic, but not the required source -> actual MACE-loaded representation equivalence.

A manually constructed object can remain green even if MACE's production loader changes or normalizes cell/PBC/position representation in a way that changes canonical replay identity. Under Protocol 6 proxy-proof acceptance, that cannot close the owner claim.

### Required repair/evidence

Do **not** change the canonical identity algorithm merely to satisfy the test. Keep the source routing unless the real-loader test falsifies it.

Add a bounded CPU test that uses the pinned supported MACE loader used by production, on tiny materialized ExtXYZ inputs:

```text
source ASE/replay authority
 -> current mdstats replay materialization/export
 -> real pinned MACE ExtXYZ/dataset loader
 -> returned real MACE Configuration collection
 -> canonical_replay_geometry_identity(...)
 -> exact comparison with authenticated source identity
```

Cover at least:

- one non-periodic geometry;
- one periodic geometry with nontrivial cell/PBC;
- one geometry perturbation beyond the existing identity quantization that must change identity and reject.

The test must exercise MACE's actual loader function/path, not instantiate `Configuration` directly and not reimplement the loader in the fixture. A bounded double may remain below MACE only for unrelated expensive training.

Also retain the current negative test proving that a canonical loaded-geometry mismatch performs zero replay membership file rereads and cannot enter legacy fallback.

### Acceptance

R1 closes only when source identity and real-MACE-loaded identity are equal for the representative cases and the mismatch path remains fail closed without reread fallback.

---

## 4. Blocking repair R2 — authenticate pre-fix TRAIN2 architecture without rewriting historical evidence

### Defect in the acceptance oracle

The new pre-fix tests do not establish the required recovery claim.

`_pre_fix_foundation_workspace()` uses an external/fake trainer. The resulting toy TRAIN2 summary explicitly has no `model_architecture_digest`. The tests then call `_set_persisted_architecture(...)`, which rewrites:

- `train2_runtime.json`;
- every epoch summary;
- `train2_runtime.pt`;

to inject either the current architecture digest or an arbitrary different digest before exercising recovery.

That manufactures the decisive historical fact rather than observing it from the real TRAIN2/MACE persistence owner. It could pass while an actual pre-fix MACE run persisted a different architecture, lacked the required authentic evidence, or reconstructed differently. Recomputing content digests after altering the fixture does not make the mutated history independent evidence.

### Required end state

The recovery classifier may continue using an authentic persisted `model_architecture_digest` when one was actually produced by the pre-fix TRAIN2/MACE owner. Do not mutate historical summaries/companions to create it.

Build bounded historical counterfactuals through the real architecture-producing boundary:

```text
immediately-pre-fix P5 config spelling
 -> real pinned MACE model construction
 -> real TRAIN2 runtime persistence/checkpoint owner
 -> immutable historical summary/companion/checkpoint
 -> current recovery classifier
```

The pre-fix difference under test is limited to the absent explicit `compute_avg_num_neighbors=False` representation (plus already-authorized locator/transient-backend representation differences). Every other protected config/run/materialization/continuation fact must authenticate normally.

If the authentic pre-fix TRAIN2 format for the applicable real run contains `model_architecture_digest`, compare it directly with the current authorized training realization through the existing canonical architecture descriptor.

If a genuinely applicable historical format does **not** contain that digest, do not invent or backfill it. Instead derive the old run's actual architecture from already-authenticated historical checkpoint/model state through the existing MACE checkpoint/reconstruction + canonical architecture descriptor owner, if that is sufficient and exact. If exact classification is impossible from authentic preserved evidence, fail typed and surface that limitation; do not guess today's missing-key semantics.

In all cases:

- absence of the old control must never be normalized into today's `False` as proof;
- current authorized architecture is reconstructed through existing e3nn/CuEq realization owners;
- comparison is like-with-like at the transient TRAIN2 realization boundary when CuEq/OEq applies;
- historical materialization/checkpoint bytes are not rewritten merely to gain compatibility;
- unrelated foreign/corrupt historical state remains rejected.

### Required counterfactuals

1. authentic pre-fix representation + actual persisted/reconstructed training architecture equal to current authorized realization -> reuse completed TRAIN2 state, reach corrected EVAL2, no retraining of that run, no historical-byte rewrite;
2. authentic pre-fix representation + actual architecture different -> fail the old state closed as noncurrent and proceed through the bounded replacement behavior in R3 below;
3. foreign/corrupt old config/state -> reject and preserve; the narrow pre-fix classifier must not become a general compatibility bypass.

Delete `_set_persisted_architecture(...)` or restrict any mutation helper to a clearly synthetic low-level serialization test that is **not** claimed as R2 real-owner acceptance.

---

## 5. Blocking repair R3 — make architecture-different pre-fix state actually recomputable

### Defect

Candidate `577908bf...` correctly refuses to reuse a pre-fix run whose authentic training architecture differs from current authority, but it only raises `PostSelectionExecutionError` while leaving the same run root in place.

A retry re-enters the same classifier, observes the same preserved foreign architecture, and raises again. There is no current P5 command-owned transition from this classified stale run to a fresh current run. Therefore the frozen requirement:

```text
preserve the old run and recompute only that affected run under current authority
```

is not realized. The error text says recomputation is required, but the control flow does not make recomputation reachable.

### Required end state

Do not solve this with a compatibility database, migration framework, second run identity, generic quarantine service, or new recovery state machine.

After **complete authentication and exact classification** proves that the state is the narrowly recognized immediately-pre-fix representation and that its actual model architecture is genuinely noncurrent, use the minimum existing run-owned recovery mechanism needed to make the current run executable.

The preferred shape is a bounded one-time replacement of **only that proven stale run-owned materialization/checkpoint state**, using existing ownership/activity-lease and safe-removal rules. Preservation means the classifier must not destroy ambiguous, corrupt, foreign, or unclassified evidence before the conclusion is established; it does not require retaining scientifically noncurrent derived scratch forever if existing project policy permits deterministic replacement after classification.

If project authority requires retaining the classified old bytes for diagnostics, reuse an already-existing bounded diagnostic/backup mechanism. Do not invent a permanent backup namespace merely for this case. If no existing permitted replacement/preservation mechanism can satisfy both requirements, return to Software Design with the concrete conflict rather than adding machinery.

Required behavior:

- equal architecture -> reuse immutable state;
- different architecture, but exact immediately-pre-fix state fully authenticated -> replace/recompute **only that run** under current authority;
- ambiguous/corrupt/foreign state -> preserve and fail typed; never auto-delete;
- no sibling run/size evidence is touched;
- replacement cannot race another live owner: use the existing run activity lease and recheck classification before deletion/rebuild;
- no incomplete acceptance/publication is produced during replacement.

### Acceptance

Through the public P5 recovery path, create an authentic architecture-different pre-fix run, rerun the command, and prove:

1. old state is classified before any removal;
2. only the affected run is replaced/retrained;
3. the replacement produces current authenticated TRAIN2/EVAL2 evidence;
4. sibling completed evidence remains byte-identical/current;
5. a corrupt/foreign control case remains preserved and refuses destructive replacement.

---

## 6. Accepted source direction still requiring executed proof

Do not redesign these pieces absent failing evidence:

- supervised `Popen` TRAIN execution with process-group cancellation, timeout/disk stop, bounded diagnostics;
- incremental metrics tailing;
- optimizer records alone advance gradient-update progress;
- launch-time progress denominator follows the actual target+replay combined loader/drop-last semantics until authenticated TRAIN2 `planned_updates` supersedes it;
- restart begins from authenticated completed updates and tails only new metrics bytes;
- one active child failure stops new scheduler admission, signals owned siblings, waits/reaps them, preserves valid continuation, and creates no incomplete acceptance/publication;
- e3nn TRAIN2/EVAL2 architecture equality and architecture-mutation rejection;
- two distinct folds/memberships receive the same frozen authorized `avg_num_neighbors`;
- bounded real CuEq TRAIN2 realization -> authenticated reconstruction/state -> portable e3nn EVAL2 parity when the qualified CuEq stack required by this concrete bug is available.

The new scheduler composition/failure tests are directionally valid because they keep the real P5 scheduler/control owner live and substitute expensive training/telemetry below that owner. They do not constitute GPU qualification.

---

## 7. Required final executable evidence — E1

After R1-R3, run all acceptance evidence on one unchanged executable candidate. At minimum:

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
tests/test_mlff_replay_mace_p5_execution_recovery.py
current real per-size P5 scheduler/supervisor integration tests
current multi-size CV/final-production/currentness/publication tests
```

Re-derive the affected surface from the final diff; this list is a floor, not a ceiling.

Run repository-configured fast Python lint/type/static checks. For structural absence claims use Semgrep when available. If unavailable, use bounded AST/source checks validated against known-positive and known-negative examples and record scan scope/limitations. At minimum establish:

- current single-source replay cannot fall back to replay-file membership reread after canonical mismatch;
- no bare blocking P5 training subprocess path was reintroduced;
- scheduler and reporter do not create duplicate GPU polling/control planes;
- no dataset-local recomputation of frozen P5 `avg_num_neighbors`;
- scheduler task liveness does not derive from human-readable MACE phase;
- outer selected-size iteration remains serial;
- R3 does not introduce a generic historical-state deletion path.

A required check that does not execute remains a blocker. GitHub currently reports zero check-runs/statuses for `577908bf...`, so source inspection alone cannot close E1.

Production-scale GPU throughput, long CuEq performance/numerical qualification, LAMMPS/MLIAP deployment, and full stakeholder production campaign qualification remain deferred to the final release package. A tiny real MACE/CuEq functional boundary test is not production qualification.

---

## 8. Re-review PASS criteria

All must be true:

```text
[x source] scheduler active membership comes from active task ownership
[x source] scheduler readiness uses current training phase + bounded fresh optimizer activity
[x source] slow legitimate optimizer work inside timeout stays ready across ordinary polls
[x source] validation/stale activity cannot authorize added jobs
[x source] selected sizes remain serial
[x source] current single-source replay selects canonical identity domain once and does not retry legacy/file membership on mismatch

[ ] canonical source identity == identity from the REAL pinned MACE loader for representative periodic/non-periodic frames
[ ] canonical mismatch fails with zero post-load replay membership reread
[ ] legacy replay remains explicit/bounded and current replay lineage remains stable

[ ] pre-fix equal-architecture reuse is demonstrated from authentic real TRAIN2/MACE architecture evidence without rewriting historical authority
[ ] pre-fix different architecture is demonstrated from authentic evidence
[ ] different architecture can actually replace/recompute only the affected run through the public P5 path
[ ] ambiguous/corrupt/foreign historical state remains preserved and rejected
[ ] historical missing control is never normalized to today's value as proof

[ ] progress denominator/numerator/restart/validation semantics pass real-owner evidence
[ ] scheduler failure stops admission, reaps owned children, preserves valid continuation, and creates no incomplete publication
[ ] e3nn architecture parity and mutation rejection pass
[ ] frozen avg_num_neighbors reaches distinct folds unchanged
[ ] bounded real CuEq transient-realization -> portable-provider parity passes when required/available

[ ] no new registry/DB/daemon/queue/state machine/second scheduler/second wrapper/compatibility authority is introduced
[ ] final focused + affected regression + integration + static evidence executes on one unchanged candidate
[ ] full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred
```

Any unchecked row remains blocking. Do not weaken or substitute the real owner to manufacture closure.

---

## 9. Genuine escalation triggers

Return to Software Design only if implementation evidence shows one of these:

1. canonical replay identity cannot survive the real pinned MACE loader without changing accepted replay authority;
2. authentic pre-fix state cannot be classified from persisted/checkpoint evidence without guessing historical semantics;
3. preserving ambiguous evidence while replacing a fully classified noncurrent run is impossible under current P5 ownership/storage contracts without new durable recovery architecture;
4. exact transient accelerator realization cannot be reconstructed/authenticated through existing MACE conversion owners and would require a new persistent model/checkpoint representation;
5. a demonstrated requirement shows the accepted serial outer selected-size D3 topology itself is inadequate;
6. another concrete contradiction shows accepted D3 cannot preserve D1/D2 semantics.

Otherwise keep the repair in D4 and alter/reduce existing owners only.

---

## 10. Review environment and evidence status

This review used the current remote SSDP 6 Software Design skill and GitHub source at candidate `577908bf...`.

- Serena-class semantic navigation was considered, but Serena is unavailable in the review host.
- Semgrep-class structural review was considered, but Semgrep is unavailable in the review host.
- the review host cannot clone/execute the repository because outbound GitHub DNS resolution is unavailable;
- GitHub exposes no check-runs or commit statuses for the reviewed candidate.

Those tool limitations do not relax the acceptance claims; they are the reason E1 remains open.