---
kind: consolidated-implementation-workplan
workplan_id: CODE-MLFF-REPLAY-MACE-P5-EXECUTION-RECOVERY-CONSOLIDATED
protocol_version: 6.0.0
status: reopened
created_date: 2026-09-09
last_review_date: 2026-09-10
implementation_branch: fix/mlff-replay-mace-membership-identity
reviewed_candidate_head: f87d9c2d4b355b02cf5cbd6aad6c15de2ab0fd20
reviewed_candidate_tree: 538924d8e18a8d8fd1356aebd7ab9c94ac566d57
review_verdict: no-pass
workplan_review_state: source-and-oracle-review-passed-awaiting-final-executed-acceptance
highest_affected_domain: D4 realization under unchanged accepted D3 replay/P5/TRAIN2/MACE, serial selected-size orchestration, recovery ownership, and acceleration architecture
serious_challenge: none
open_blockers: final executed affected-surface acceptance only
precedence: This file is the sole snapshot-complete implementation handoff for the current repair cycle. Earlier revisions and replay/progress/scheduler/recovery amendments remain provenance only. Accepted current D1-D4 authority outside this workplan remains binding.
---

# MLFF P5 replay/MACE execution recovery — Protocol 6 final implementation review reopen

## 0. Review disposition

Executable candidate `f87d9c2d4b355b02cf5cbd6aad6c15de2ab0fd20` is **NO-PASS / REOPENED**, but the remaining blocker is now **evidence-only**.

No Serious Challenge is active. D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE architecture remain coherent and unchanged.

Independent source review finds the R4 recovery repair conforming to the protected crash-consistency outcome and to the minimum-complexity constraint. The candidate replaces recursive destruction of live canonical checkpoint/materialization namespaces with owner-local atomic detach followed by recursive reclamation only outside those canonical namespaces. It introduces no new durable recovery authority, registry, database, journal, state machine, scheduler, compatibility layer, or alternate run identity.

The added R4 tests exercise the real public P5 recovery owner and cover:

- interruption after checkpoint namespace detachment and before materialization detachment;
- interruption during recursive reclamation of detached checkpoint scratch;
- interruption during recursive reclamation of detached materialization scratch;
- retry in the same workspace from epoch zero for only the affected stale run;
- preservation of completed sibling materialization/checkpoint evidence;
- bounded cleanup of deterministic retirement scratch;
- an existing retirement-destination collision remaining fail closed rather than being overwritten.

The branch graph is one merge commit behind `main`, but this is **not a content drift**: the main-only merge commit and the branch merge base carry the same tree identity. No missing baseline file content is introduced by that graph-only divergence.

The only remaining blocker is final D4 executable acceptance. GitHub exposes no commit status, check run, or Actions run for `f87d9c2d4b355b02cf5cbd6aad6c15de2ab0fd20`, and the independent review host cannot clone the repository because shell networking cannot resolve `github.com`. Therefore the required affected-surface regression/integration/static checks have not been independently observed as executed on the reviewed candidate. Under Protocol 6, test source is not executed evidence and an unexecuted required check cannot be promoted to PASS.

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

No remaining acceptance work may change D1/D2 method meaning.

### 1.2 Recovery/identity invariants

- current `single_source` replay uses existing canonical source/split geometry identity;
- supported `legacy_split` uses its existing historical identity domain;
- generated replay ExtXYZ remains transport, not new scientific authority;
- actual MACE-loaded membership authenticates exactly before execution evidence is accepted;
- TRAIN2 continuation remains bound to exact run/materialization/MACE execution evidence;
- persisted actual TRAIN2 architecture, not today's interpretation of an omitted historical config key, decides pre-fix architecture equivalence;
- architecture-equal authenticated historical state is reused rather than destructively normalized;
- architecture-different exact authenticated immediately-pre-fix state may be recomputed from epoch zero;
- ambiguous, corrupt, foreign, or unclassified canonical state remains fail closed;
- stale-state replacement must remain same-workspace recoverable after interruption;
- canonical checkpoint/materialization namespaces must never be recursively destroyed in place once their shape is used as restart classification authority.

### 1.3 Execution/orchestration invariants

- selected sizes remain serial at the accepted outer D3 boundary;
- within one selected size, the existing adaptive scheduler may admit independent folds/seeds or production members;
- active futures own scheduler task liveness;
- scheduler readiness is transient execution state: training phase plus bounded fresh optimizer activity under the existing activity timeout;
- scheduler controls resource admission only; progress/reporting never becomes completion authority;
- runtime failure stops new admission and cancellation reaches/reaps owned active child processes;
- completion order cannot alter canonical reduction/publication;
- completed sibling evidence remains valid under its own identity/currentness when another run fails or is recomputed;
- the existing run activity lease owns authentication, stale-state transition, rebuild, and execution serialization.

### 1.4 Acceleration/model invariants

- source/evaluation/deployment remain portable e3nn where current policy requires it;
- TRAIN2 may use configured transient CuEq/OEq realization;
- `only_cueq=false` retains portable-product semantics;
- architecture authentication remains fail closed;
- P5-frozen model-affecting values, including `avg_num_neighbors`, reach MACE exactly and are not recomputed from fold-local data.

### 1.5 Minimum-complexity constraint

Do not add a scheduler, cross-size queue, persistent queue, progress daemon, replay/checkpoint/update registry, compatibility database, migration framework, restart state machine, second MACE wrapper, second architecture authority, durable readiness state, permanent stale-run archive namespace, or another recovery protocol to close this workplan.

The current deterministic retirement scratch is delegated D4 temporary state only. It is bounded to the two run-local canonical namespaces, does not enter scientific/recovery identity, and must be absent after successful recovery.

---

## 2. Source/conformance findings — closed

### C1 — optimizer-event accounting

Append-only optimizer metrics are counted by stream position/cursor rather than JSON-content equality. Newly consumed complete `mode="opt"` rows count separately even when content is identical. Validation rows remain non-counting; partial-line and no-new-byte handling preserve exactly-once behavior.

### C2 — bounded readiness and reporting

Scheduler readiness remains training phase plus at least one newly observed optimizer completion plus bounded freshness. Validation is non-ready; stale activity revokes readiness; reporting does not become completion authority.

### C3 — replay identity routing

Current single-source replay selects canonical geometry identity once; canonical mismatch cannot fall into legacy/file reread identity. Supported legacy replay remains explicitly routed through its historical identity domain.

### C4 — scheduler liveness/topology

Task liveness comes from live future/task ownership. Selected sizes remain serial and no command-wide cross-size scheduler was introduced.

### C5 — historical architecture classification

The pre-fix classifier authenticates materialization, continuation, MACE execution evidence, and persisted actual TRAIN2 architecture before replacement. Architecture-equal state reuses immutable evidence. Architecture-different exact pre-fix state resets only that run to epoch zero. Foreign/corrupt/unclassified canonical state remains fail closed.

### C6 — real scheduler/trainer/process acceptance boundary

Bounded tests retain the real P5 scheduler, real `MacePostSelectionTrainer`, progress observer, subprocess/process-group ownership, and TRAIN2 persistence owner while substituting only bounded workload and external telemetry.

### C7 — real TRAIN2 architecture persistence boundary

A real MACE model is driven through the actual TRAIN2 persistence owner and the persisted model-architecture digest is compared with the canonical live-model descriptor.

### C8 — checkpoint-before-materialization ordering

Stale continuation retirement occurs before stale materialization retirement. This preserves the existing classifier's monotonic restart relation.

### C9 — R4 atomic detach/reclaim

Candidate `f87d9c2...` closes the prior recursive-deletion crash window:

1. deterministic run-local scratch names are reserved for `checkpoints` and `materialization` retirement;
2. top-level canonical/scratch paths are inspected no-follow and must be ordinary directories or absent;
3. an existing scratch destination while the canonical namespace is present is treated as an integrity conflict and preserved;
4. the authenticated canonical namespace is renamed to same-parent retirement scratch, making namespace detachment the atomic visible commit point;
5. the parent directory is fsynced through the repository's existing durability primitive;
6. recursive reclamation targets only detached scratch;
7. retry first reclaims residual detached scratch when the canonical namespace is absent;
8. checkpoint detachment precedes materialization detachment;
9. existing materialization/TRAIN2 owners recreate the canonical namespaces; no second persistence/recovery authority exists.

The implementation is consistent with the current recovery architecture: restart classification observes either the intact canonical namespace or its absence, not an mdstats-created partially recursively deleted canonical tree.

### C10 — R4 oracle strength

The added R4-A/R4-B/R4-C tests keep the public P5 recovery owner live and place failpoints at the low-level rename/reclaim boundaries. They establish trigger liveness, no incomplete acceptance, same-workspace retry, epoch-zero retraining of the affected stale run, sibling preservation, and bounded scratch cleanup. The destination-collision test protects the fail-closed no-overwrite condition.

### C11 — integration-baseline graph check

`main` currently points at merge commit `b0d2dd13...`; the merge base with this branch is `9abb2b899...`. Both commits have tree `344369ff4e70d65f53b0e932025edcc920700d67`, so the branch's apparent one-commit-behind state represents merge history only, not missing baseline content. No rebase/merge is required solely for this review.

No new source, documentation, scientific, numerical, architecture, ownership, or complexity blocker was found in DS-5.

---

## 3. Sole remaining blocker E2 — execute final acceptance on one unchanged candidate

Final executable acceptance is still unavailable for candidate:

```text
f87d9c2d4b355b02cf5cbd6aad6c15de2ab0fd20
```

Observed review evidence:

```text
GitHub combined commit statuses: 0
GitHub check runs: 0
GitHub Actions runs for exact head: 0
independent review-host clone/pytest: unavailable (github.com DNS resolution failure)
```

This is an **Implementation functional-closure blocker**, not a new Design defect. Do not change the now-conforming R4 source merely to create review evidence.

Execute the complete affected surface on the unchanged executable candidate. At minimum:

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
- P5 storage/run-activity lease, stale replacement, R4 interruption/retry, cancellation, and failure behavior;
- repository-configured fast Python lint/type/static checks;
- structural absence/ownership claims: no current single-source replay file-reread fallback, no bare blocking P5 training `subprocess.run`, one scheduler telemetry owner per interval, serial selected-size orchestration, no fold-local `avg_num_neighbors`, and no new durable compatibility/recovery framework.

Use project-configured Semgrep/Serena or equivalent bounded validated source/AST inspection where available and materially useful. Tool absence does not itself block; missing required behavioral execution does.

If the affected surface cannot be bounded confidently on the execution host, run the broader P5/P7/campaign/replay/storage regression.

Record enough output to bind the result to `f87d9c2d4b355b02cf5cbd6aad6c15de2ab0fd20` (or to a later code-identical executable candidate). Do not substitute test definitions, test counts, or an unsupported statement that tests passed for actual execution evidence.

---

## 4. Re-review PASS criteria

Source/conformance is closed. Final PASS now requires only evidence closure on one unchanged executable candidate:

```text
[x source] optimizer event accounting semantics conform
[x source] readiness/liveness semantics conform
[x source] selected sizes remain serial
[x source] replay identity routing remains fail closed
[x source] persisted actual TRAIN2 architecture owns historical equivalence
[x source] architecture-equal historical state is reused
[x source] architecture-stale exact historical state is retrained from epoch zero
[x source] checkpoint retirement precedes materialization retirement
[x source] canonical retirement uses atomic detach before recursive reclaim
[x source] retry handles interruption between detaches
[x source] retry handles partial detached-checkpoint reclamation
[x source] retry handles partial detached-materialization reclamation
[x source] deterministic retirement scratch is bounded/non-authoritative
[x source] existing scratch collision with canonical state fails closed
[x source] only affected run is routed to retraining; sibling state is preserved by the R4 oracle
[x source] no new recovery registry/DB/journal/state machine/second scheduler/second wrapper was introduced
[x source] no effective main-baseline content divergence exists

[ ] focused optimizer/progress and R4 recovery tests execute on final candidate
[ ] public stale-run recomputation/interruption/retry tests execute on final candidate
[ ] real scheduler/trainer promotion and cancellation/reaping tests execute
[ ] real TRAIN2 architecture-persistence test executes
[ ] pinned real MACE parser/loader replay identity tests execute
[ ] complete affected regression/integration/project static checks execute
[ ] bounded e3nn/CuEq TRAIN2/EVAL2 architecture guards remain fail closed
[ ] no newly executed affected regression fails
[ ] production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred
```

No unchecked execution row may be converted into PASS by weakening or proxying the claim.

---

## 5. Routing

Do **not** make another source repair unless executing E2 exposes a real defect.

Next action is Implementation acceptance only:

```text
run E2 on f87d9c2... (or a demonstrably code-identical executable candidate)
  -> if all required checks pass, return to Software Design for closure/archive
  -> if an affected check fails, diagnose the concrete failure under the existing authority
```

Reopen D3 only if executed evidence shows the atomic-detach/reclaim realization cannot satisfy the accepted recovery contract without materially new architecture. Nothing in the current source review supports such a redesign.

---

## 6. Deferred final-release qualification

Still deferred until the complete final release package:

- production-scale GPU throughput/capacity qualification;
- long CuEq numerical/performance qualification;
- LAMMPS/MLIAP target-machine deployment qualification;
- full stakeholder production campaign qualification.

The bounded MACE/CuEq/control-path tests above are implementation functional evidence, not production-scale qualification.
