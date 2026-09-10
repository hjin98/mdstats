---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: reopened
created_date: 2026-09-09
last_review_date: 2026-09-10
implementation_branch: fix/mlff-replay-mace-membership-identity
reviewed_candidate_head: 15347f448ffab61286c0540b830d6681c3cc2e5c
reviewed_candidate_tree: 159277951c7925f755da8e544407b921bbf4a39d
review_verdict: no-pass
workplan_review_state: implementation-review-reopened-for-atomic-retirement-and-final-evidence
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE, serial selected-size orchestration, recovery ownership, and acceleration architecture
serious_challenge: none
open_blockers: interruption-safe atomic retirement of authenticated stale-run checkpoint/materialization namespaces; final executed affected-surface acceptance
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier revisions and replay/progress/scheduler amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — Protocol 6 implementation review reopen

## 0. Review disposition

Executable candidate `15347f448ffab61286c0540b830d6681c3cc2e5c` is **NO-PASS / REOPENED** after independent SSDP Protocol 6 Software Design review.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, and the accepted D3 replay/P5/TRAIN2/MACE architecture remain coherent and unchanged. The remaining defects are D4 recovery/acceptance defects plus one cycle-scoped workplan-oracle inadequacy; they do not justify a new scheduler, state machine, migration framework, registry, or compatibility authority.

The candidate is a deliberately small delta over the previous review point: it modifies only `campaign_post_selection_runtime.py` and `test_mlff_replay_mace_p5_execution_recovery.py`. It correctly repairs the previously identified **between-cleanup-steps** ordering defect by removing the stale `checkpoints/` tree before `materialization/`, and its new public-owner failure-injection test proves retry when interruption is injected **after the checkpoint `shutil.rmtree()` has completed successfully** and before materialization retirement starts.

That closes the narrow R3 counterexample but does **not** yet make the destructive transition crash-idempotent. Both cleanup operations remain direct recursive deletion of live canonical namespaces. `shutil.rmtree()` is not an atomic namespace transition. A hard process interruption while either recursive deletion is in progress can leave an incomplete canonical tree. The existing recovery classifier intentionally treats such partially durable checkpoint/materialization state as ambiguous/corrupt and fails closed. That is correct for unknown state, but it means the replacement operation can still manufacture a same-workspace dead end from a previously fully authenticated stale run.

The current test misses this because its monkeypatch calls the original checkpoint `rmtree()` to completion and raises only afterward. The protected product outcome is crash-safe same-workspace recovery, not merely safe ordering between two successful recursive deletions. The workplan's prior failure oracle was therefore too weak for its own `crash-idempotent` claim and is strengthened below.

Final executable affected-surface evidence is also unavailable for this exact candidate. GitHub exposes no status/check and no Actions run for `15347f448ffab61286c0540b830d6681c3cc2e5c`. The independent review host again cannot clone/execute the repository because shell-network DNS resolution for GitHub is unavailable. Under Protocol 6, a required D4 check that did not execute is a blocker; test source is not executed evidence.

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

No remaining repair may change D1/D2 method meaning merely to simplify recovery.

### 1.2 Recovery/identity invariants

- current `single_source` replay uses existing canonical source/split geometry identity;
- supported `legacy_split` uses its existing historical identity domain;
- generated replay ExtXYZ remains transport, not a new scientific authority;
- actual MACE-loaded membership authenticates exactly before execution evidence is accepted;
- TRAIN2 continuation remains bound to exact run/materialization/MACE execution evidence;
- persisted actual TRAIN2 architecture, not today's interpretation of a missing historical config key, decides pre-fix architecture equivalence;
- architecture-equal authenticated historical state is reused rather than destructively normalized;
- architecture-different **exact authenticated** immediately-pre-fix state may be recomputed from epoch zero;
- ambiguous, corrupt, foreign, or unclassified state remains fail closed and is never destructively treated as the narrow stale-pre-fix case;
- an interruption caused by mdstats while replacing that already-authenticated stale case must not convert it into a permanent same-workspace dead end;
- canonical recovery namespaces must not expose partially destroyed trees as if they were independently arrived-at durable state.

### 1.3 Execution/orchestration invariants

- selected sizes remain serial at the accepted outer D3 boundary;
- within one selected size, the existing adaptive scheduler may admit independent folds/seeds or production members;
- active futures own scheduler task liveness;
- scheduler readiness is transient execution state: current training phase plus bounded fresh optimizer activity under the existing activity timeout;
- scheduler controls resource admission only; progress/reporting never becomes completion authority;
- runtime failure stops new admission and cancellation reaches/reaps owned active child processes;
- completion order cannot alter canonical reduction/publication;
- completed sibling evidence remains valid under its own identity/currentness when another run fails or is recomputed;
- the run activity lease remains held across authentication, stale-state transition, rebuild, and execution ownership.

### 1.4 Acceleration/model invariants

- source/evaluation/deployment remain portable e3nn where current policy requires it;
- TRAIN2 may use configured transient CuEq/OEq realization;
- `only_cueq=false` retains portable-product semantics;
- architecture authentication remains fail closed;
- P5-frozen model-affecting values, including `avg_num_neighbors`, reach MACE exactly and are not recomputed from fold-local data.

### 1.5 Minimum-complexity constraint

Do not add a scheduler, cross-size queue, persistent queue, progress daemon, replay/checkpoint/update registry, compatibility database, migration framework, restart state machine, second MACE wrapper, second architecture authority, durable readiness database/state machine, or permanent stale-run archive namespace merely to close this repair.

Prefer a direct owner-local filesystem transition that makes the existing recovery classifier's canonical namespaces crash-consistent. A bounded temporary retirement path used only as disposable run-owned scratch is acceptable when needed to obtain an atomic same-filesystem namespace transition; it must not become a new semantic authority, compatibility record, unbounded archive, or second recovery protocol.

---

## 2. Closed source/conformance findings — preserve

### C1 — optimizer-event accounting

`_PostSelectionTrainingProgress` uses its append cursor (`metric_offset` plus partial-line remainder) as the exactly-once observation boundary. Every newly consumed complete valid `mode="opt"` row increments `optimizer_updates_since_launch` and refreshes activity even when rows have identical JSON content. Validation rows remain non-counting. Existing focused tests cover identical rows, no-new-byte refresh, partial-line completion, validation non-counting, and restart offset behavior.

### C2 — bounded optimizer readiness and reporting

The accepted readiness model remains training phase plus at least one newly observed optimizer completion plus freshness under `parallel_training_epoch_activity_timeout_seconds`. Validation is immediately non-ready; ordinary polls without a new row do not revoke readiness inside the timeout; stale activity does. Authenticated TRAIN2 `planned_updates` remains the eventual exact progress owner.

### C3 — explicit replay identity routing

Current single-source P5 selects canonical replay geometry identity once. The child reconstructs canonical identity from MACE-loaded configurations and cannot enter legacy identity or replay-file membership reread after canonical mismatch. Supported legacy replay remains explicitly routed through the historical identity domain. The pinned real MACE parser/loader boundary remains the required functional oracle.

### C4 — scheduler liveness and serial selected-size topology

Active scheduler membership is derived from live future/task ownership. Human-readable MACE phase does not own task liveness. Selected sizes remain serial; no command-wide cross-size scheduler has been introduced.

### C5 — pre-fix architecture classification and nominal replacement

The narrow immediately-pre-fix classifier authenticates materialization, continuation, MACE execution evidence, and actual persisted TRAIN2 architecture before any replacement decision. Architecture-equal state reuses immutable evidence. Architecture-different exact pre-fix state obtains an execution-local replacement decision, clears continuation reuse, and resets training to epoch zero. Foreign/corrupt/unclassified state remains outside this branch.

### C6 — real scheduler -> real trainer/process acceptance boundary exists

Bounded tests retain the real per-size P5 scheduler, real `MacePostSelectionTrainer`, real incremental progress observer, subprocess/process-group ownership, and TRAIN2 persistence owner while substituting only bounded child workload and external telemetry. They exercise promotion, active failure, cancellation/reaping, queued-work suppression, and absence of incomplete acceptance.

### C7 — real TRAIN2 architecture persistence boundary exists

A bounded test constructs a real MACE model from current materialization and drives it through the actual TRAIN2 persistence owner. Persisted JSON/PT architecture digests are compared with the canonical live-model descriptor. Synthetic digest mutation remains valid only for counterfactual classifier coverage.

### C8 — successful checkpoint-first ordering is now correct

Candidate `15347f4...` moves `shutil.rmtree(checkpoint_directory)` ahead of `shutil.rmtree(material_directory)`. The added public-owner test constructs an authenticated stale run plus a completed sibling, raises after successful checkpoint retirement, proves no incomplete acceptance, retries in the same workspace from epoch zero, and preserves sibling bytes. This closes the previous *between two completed deletions* defect. Preserve the ordering relation while repairing the non-atomic recursive-retirement problem below.

---

## 3. Blocking repair R4 — make stale-state namespace retirement crash-consistent, not only ordered

### 3.1 Defect A: direct recursive checkpoint deletion can manufacture ambiguous continuation state

Current replacement executes direct recursive deletion of the live canonical checkpoint namespace:

```text
shutil.rmtree(checkpoint_directory)
```

The checkpoint authenticator behaves deliberately conservatively:

1. absent `checkpoints/` -> no continuation;
2. a directory containing no durable entries beyond temp/lock residue -> no continuation;
3. any durable entry -> validate the complete TRAIN2 continuation;
4. failed validation -> preserve diagnostic state and fail closed.

Therefore this counterexample remains:

1. materialization and TRAIN2 continuation fully authenticate as the narrow architecture-stale pre-fix case;
2. replacement starts `shutil.rmtree(checkpoints/)`;
3. some durable checkpoint files are removed;
4. the process is killed before recursive deletion completes;
5. the next invocation sees `checkpoints/` still present with one or more durable entries;
6. full continuation authentication fails because mdstats itself partially deleted the tree;
7. fail-closed preservation now prevents the same canonical run from making progress without manual deletion.

The new test does not exercise this state because it lets `rmtree(checkpoints/)` finish before injecting the exception.

### 3.2 Defect B: direct recursive materialization deletion has the same failure class

After checkpoint removal, current replacement also executes:

```text
shutil.rmtree(material_directory)
```

Interruption during this recursive deletion can leave `materialization/` partially present. If `materialization.json` survives while an authenticated member/config/artifact has already been removed, the classifier correctly treats the remaining record/tree as corrupt/incomplete and preserves it. Thus checkpoint-first ordering alone moves, rather than eliminates, the crash window.

This is the same defect family: **destructive recursive mutation is being performed directly in the canonical recovery namespaces whose shape the next process uses to distinguish absent/incomplete/stale/corrupt state.**

### 3.3 Required end state

Make the stale replacement transition namespace-atomic from the next invocation's point of view.

Required semantic property:

```text
before transition:
  canonical historical checkpoints/materialization are fully intact and authenticate

after the atomic retirement boundary for each canonical namespace:
  that canonical path is absent (or otherwise in the already-supported unambiguously empty state)
  and any recursively reclaimed bytes are outside the classifier's canonical authority paths
```

The minimum justified realization is an owner-local **atomic detach then recursive reclaim** using existing filesystem primitives and the existing run activity lease:

1. complete the same full stale-case authentication/classification **before any mutation**;
2. while holding the existing run activity lease, atomically detach the authenticated canonical `checkpoints/` tree to one bounded run-owned temporary retirement path on the same filesystem; do not overwrite an existing unknown destination;
3. preserve the checkpoint-before-materialization ordering relation;
4. atomically detach the authenticated canonical `materialization/` tree to its bounded run-owned temporary retirement path rather than recursively deleting the live canonical tree;
5. recursive deletion/reclamation operates only on the detached temporary trees, so interruption during reclamation cannot leave partial canonical checkpoint/materialization state;
6. retry must be able to continue from every boundary: before either detach, between the two detaches, after both detaches, and during reclamation of either detached tree;
7. detached scratch is bounded, never enters scientific/recovery identity, never becomes resumable continuation, and is deterministically reclaimed by the same run owner; do not create an unbounded history of retired copies;
8. canonical new `checkpoints/` and materialization are recreated only through the existing owners, and stale retraining still begins at epoch zero;
9. completed sibling runs/sizes remain untouched.

A same-filesystem `rename`/`os.replace`-class namespace operation is the intended low-complexity mechanism. Prefer an already-established owner-local atomic/temp helper if one exists and fits exactly. Do **not** build a new recovery framework, journal, tombstone protocol, registry, compatibility database, migration record, alternate run identity, permanent quarantine/archive area, or second cleanup service.

If implementation evidence demonstrates that the repository/filesystem contract cannot provide a bounded owner-local atomic detach without materially new durable recovery authority, return to Software Design rather than layering retries around `rmtree()`.

### 3.4 Required fault-injection oracles

Keep the public P5 recovery owner live. Low-level rename/removal failure injection is acceptable; fixture-side reimplementation of recovery is not.

At minimum cover all of these on the same repair family:

**R4-A — interruption between canonical detaches**

1. construct the exact authenticated architecture-stale pre-fix run plus a completed sibling;
2. inject after canonical checkpoint detachment but before canonical materialization detachment;
3. prove no incomplete acceptance/publication;
4. rerun normally in the same workspace;
5. prove only the affected run retrains from epoch zero and reaches authenticated TRAIN2/EVAL2 evidence;
6. prove sibling bytes/currentness are unchanged.

**R4-B — interruption during detached checkpoint reclamation**

1. after canonical checkpoint detachment, force recursive reclaim of the detached checkpoint scratch to become partial and raise;
2. prove the canonical `checkpoints/` path is not a partially destroyed continuation;
3. retry normally and prove recovery succeeds without manual deletion;
4. prove temporary scratch remains bounded and is cleaned after successful recovery.

**R4-C — interruption during detached materialization reclamation**

1. after canonical materialization detachment, force its detached scratch reclamation to become partial and raise;
2. prove the canonical `materialization/` path is not a partially destroyed record tree;
3. retry normally and prove recovery succeeds without manual deletion;
4. prove temporary scratch remains bounded and is cleaned after successful recovery.

Retain controls proving:

- architecture-equal authenticated state performs no destructive retirement;
- corrupt/foreign/unclassified canonical state performs no destructive retirement;
- terminal evidence prevents re-entry;
- only the exact affected run is recomputed;
- no new durable recovery/compatibility authority appears.

The fault injection must establish trigger liveness; a green test that never crosses the intended detach/reclaim boundary does not close the claim.

---

## 4. Blocking evidence E2 — execute final acceptance on one unchanged candidate

No final executable acceptance is available for candidate `15347f448ffab61286c0540b830d6681c3cc2e5c`:

- GitHub combined statuses/checks: none;
- GitHub Actions runs for the exact head: zero;
- independent review-host clone/pytest: unavailable because shell-network DNS cannot resolve GitHub.

After R4 is implemented, execute the complete affected surface on the resulting **unchanged final executable candidate**. At minimum:

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
- P5 storage/run-activity lease, stale replacement, interruption at each R4 boundary, cancellation, and failure behavior;
- repository-configured fast Python lint/type/static checks;
- structural absence/ownership claims: no current single-source replay file-reread fallback, no bare blocking P5 training `subprocess.run`, one scheduler telemetry owner per interval, serial selected-size orchestration, no fold-local `avg_num_neighbors`, and no new durable compatibility/recovery framework.

Use Semgrep/Serena when available and materially useful. On a host without those capabilities, bounded validated AST/source/search fallback is acceptable when it establishes the same structural claim and its limitations are recorded. Optional tool absence is not itself a blocker; missing required behavioral evidence is.

If the final impact cannot be bounded confidently, run the broader P5/P7/campaign/replay/storage regression.

A required check that does not execute is a blocker. Test definitions, test counts, or an implementer's statement that tests passed are not substitutes for recorded execution evidence tied to the final candidate.

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
[x source] architecture-different exact pre-fix state has a bounded epoch-zero replacement path
[x source] checkpoint-before-materialization cleanup ordering is corrected
[x source] public-owner interruption test exists for the boundary after checkpoint retirement
[x source] real scheduler -> real MacePostSelectionTrainer -> subprocess tests exist
[x source] real TRAIN2 MACE architecture-persistence test exists

[ ] canonical checkpoint retirement cannot leave a partially destroyed canonical continuation after interruption during recursive reclamation
[ ] canonical materialization retirement cannot leave a partially destroyed canonical record tree after interruption during recursive reclamation
[ ] retry succeeds before/between/after namespace retirement boundaries without manual deletion
[ ] detached retirement scratch is bounded, non-authoritative, and cleaned deterministically
[ ] only the affected stale run is retrained; completed sibling evidence remains untouched
[ ] corrupt/foreign/ambiguous state never enters destructive retirement

[ ] focused optimizer/progress tests execute on final candidate
[ ] public stale-run recomputation + all interruption/retry tests execute on final candidate
[ ] real scheduler/trainer promotion and cancellation/reaping tests execute
[ ] real TRAIN2 architecture-persistence test executes
[ ] pinned real MACE parser/loader replay identity tests execute
[ ] complete affected regression/integration/project static checks execute
[ ] e3nn/CuEq TRAIN2/EVAL2 architecture guards remain fail closed on the available bounded functional surface
[ ] no new registry/DB/daemon/queue/state machine/second scheduler/second wrapper/cross-size scheduler is introduced
[ ] production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred
```

No unchecked row may be converted into a pass by weakening the protected claim, narrowing the failure point to a successful deletion boundary, or treating test code as executed evidence.

---

## 6. Routing

This remains implementation work under unchanged accepted D3 architecture.

- **D4 repair:** replace direct recursive destruction of live canonical stale-recovery namespaces with the minimum owner-local atomic-detach/reclaim realization that satisfies R4.
- **Cycle-plan correction:** the previous R3 failure oracle was insufficient for its `crash-idempotent` protected outcome; R4 supersedes it without changing durable D3 architecture.
- **No D1/D2 reopening:** scientific membership, training method, numerical semantics, replay meaning, and evaluation semantics remain unchanged.
- **No new recovery system:** if the repair starts to require a journal/registry/state machine/permanent archive/second authority, stop and return to Software Design for bounded reconsideration instead of accreting machinery.

After R4 source/tests close, run E2 on the final unchanged candidate and return for final independent Software Design review. Do not close or archive this plan before both source conformance and executed final acceptance are established.

---

## 7. Deferred final-release qualification

Still deferred until the complete final release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS/MLIAP target-machine deployment qualification;
- full stakeholder production campaign qualification.

The bounded MACE/CuEq/control-path tests required above are implementation functional evidence, not production-scale qualification.
