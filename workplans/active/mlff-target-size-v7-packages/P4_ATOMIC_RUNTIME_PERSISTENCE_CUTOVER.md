---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: active
package_revision: 4
amended_date: 2026-08-29
entry_p3_baseline_commit: 472276ee521eb2b19177299c1c9ad660dbd6ad46
entry_p3_closure_commit: 9d195807cff0bb8042f447ac33ceb0586ed708ac
p3a9_contract_commit: cf0cfedbfadc700acde72f5a25e4fc9d0c22f7fd
prior_p4_revision_commit: 878604128e9695a8040ff46b20f15216c4e038f4
compatibility_policy: destructive-generation-reset
entry_gate: cumulative-p3-revision-7-through-p3a9-accepted-at-9d195807cff0bb8042f447ac33ceb0586ed708ac
reconciliation_reason: Revision 4 preserves the frozen parent and all accepted P1-P3 scientific semantics while closing the final P4 implementation-handoff gaps. The stale-current-head successor repair is moved out of P4 into the cumulative revision-7 P3A9 closure contract so P4 no longer depends on work inside its own blocked predecessor. P4 now freezes one canonical CampaignStore generation authority, deterministic logical-transition identity for idempotent CAS retries, explicit cross-subsystem lock/transaction ordering, and a STOR retention fence protecting active/restartable P3 execution roots and reconciliation-frontier evidence even before SQLite adoption. No scientific, statistical, TRAIN2/EVAL2, checkpoint, provider, seed, reducer, or target-size decision semantics are changed.
---

# P4 — Atomic runtime and persistence cutover

## 0. Authority, revision disposition, and entry gate

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P4 does **not** reopen P1-P3 science, statistics, candidate qualification, reducer policy, TRAIN2/EVAL2 semantics, checkpoint semantics, provider ownership, seed policy, or target-size decision logic.

P4 revision 4 is the implementation handoff contract for the production runtime/persistence cutover. It supersedes revision 3 only for implementation sequencing and persistence/concurrency precision. The accepted dependency direction remains:

```text
P1 neutral_substrate
  -> P2 target_size_experiment
  -> P3 target_size_execution
  -> P4 campaign orchestration/persistence cutover
```

### 0.1 Mandatory predecessor closure

P4 is **blocked** until cumulative P3 revision 7, including `P3_P3A9_HEAD_POINTER_RECONCILIATION_REPAIR_INSTRUCTIONS.md`, has both semantic/conformance closure and functional closure and that accepted closure commit is recorded in the package chain.

P3A9 owns the demonstrated stale-`current_head.json` / durable-successor-head crash-recovery defect. P4 must not implement that repair, duplicate it, or work around it with a second replay engine.

When P3A9 closes:

1. record the accepted cumulative P3 closure commit in package metadata/README;
2. update this package's entry metadata to bind that exact accepted P3 commit;
3. change P4 from `blocked` to `active`;
4. only then begin P4-A executable work.

The P3A8 baseline `472276ee521eb2b19177299c1c9ad660dbd6ad46` is historical entry evidence, **not** sufficient by itself to authorize P4 execution.

### 0.2 Naming and qualification boundary

All new production code, symbols, schema names, record names, keys, and persisted authority names introduced by P4 must be **version-agnostic**. `V7` remains historical workplan/generation terminology only.

Full long GPU/real-production qualification remains deferred to final release. P4 requires bounded functional, regression, restart, concurrency, real-owner persistence, storage, CPU/reference, and assembled integration acceptance only.

---

## 1. Required product outcome and authority invariants

After P4, ordinary `prepare` and `select-target-size` expose exactly one current target-size architecture. The P1-P3 graph is the only scientific authority for target-size work; the campaign store is the only mutable current-runtime authority; restart is deterministic and authenticated; stale or retired state cannot become current through schema translation, file existence, pointer state, process ownership, or duplicated mutable metadata.

The implementation must preserve all of the following simultaneously:

1. **One mutable campaign authority.** The real CampaignStore/SQLite owner is the sole authority for current regime, canonical target-size generation, current subordinate attempt, mutable lifecycle/FSM state, adopted P3 execution-head reference, and terminal-result visibility.
2. **One canonical generation authority.** P4 must reuse/evolve the existing campaign/prepare target-size generation authority discovered in the real CampaignStore. It may not introduce a second independently advancing `target_size_runtime_generation` or equivalent counter. Any new persisted generation field created during schema cutover becomes the single canonical generation authority and replaces, rather than runs beside, the retired authority.
3. **Attempts are subordinate.** Attempt identity is scoped beneath one canonical generation. It cannot outlive, supersede, or independently authorize mutation after that generation is replaced.
4. **One scientific execution authority.** P3 immutable content-addressed evidence, heads, batches, completions, snapshots, predictions, metrics, failures, and typed replay graph remain the scientific execution authority.
5. **`current_head.json` is not campaign authority.** It is only a rebuildable P3-local recovery/index pointer to an authenticated immutable head. It may localize reconciliation but cannot independently authorize campaign generation, completion, selected `N`, or downstream selected data.
6. **No second mutable result manifest.** Any filesystem result view is immutable/content-addressed evidence or a rebuildable non-authoritative projection of SQLite plus authenticated P3 state.
7. **No parallel algorithmic owner.** P4 must not implement another split builder, selector, reducer, target-size scheduler, checkpoint interpreter, evaluation engine, immutable evidence graph, or restart/replay algorithm.
8. **No fallback/dual-write regime.** Current execution may not try the promoted path and fall back to the retired path, write both old and current authoritative state, or reinterpret retired schemas as current.
9. **Terminal selection is derived, not editable.** `N_selected` and exact `T_selected` are authenticated projections of terminal P2/P3 state. Persisted copies are downstream materializations, not independent decision inputs.
10. **Historical P3 ownership is immutable.** A new process/generation may own new operational work but cannot rewrite historical P3 owner proof.
11. **Same-generation writers are fenced.** Generation/attempt identity alone is insufficient. Every mutable campaign transition also compares the exact expected predecessor campaign-state revision in the same SQLite transaction.
12. **Storage lifecycle cannot break replay.** Active/restartable P3 execution roots and still-undecided reconciliation-frontier evidence are protected before SQLite adoption and remain protected until reconciliation classifies them.
13. **Cross-layer locking is acyclic.** P3 mutation/reconciliation, CampaignStore mutation, and STOR destructive actions must follow the frozen ordering in section 6.3; no implementation may hold one layer's mutation lock/transaction while waiting on a later layer in reverse order.

Any implementation that satisfies the CLI superficially while violating one of these invariants fails P4.

---

## 2. Frozen owner graph and implementation reconnaissance

### 2.1 Scientific/execution dependency direction

The only accepted production dependency direction after cutover is:

```text
verified source/config inputs
  -> mdstats.training_data.neutral_substrate                 # P1
       SourceAuthority / CanonicalFrameAuthority / NeutralStatisticalBase
  -> mdstats.training_data.target_size_experiment            # P2
       policy / protected relations / hard support
       U_size -> P_train/M3 -> pi_train/pi_eval -> T_N/M_i
       pure reducer and terminal statistical state
  -> mdstats.training_data.target_size_execution             # P3
       common preparation / candidate realization
       TRAIN2/EVAL2 / immutable evidence
       typed resolver / execution heads / reconciliation
  -> campaign CLI + real SQLite campaign persistence         # P4
       regime + canonical generation + subordinate attempt
       predecessor revision / adopted authenticated P3 head
       terminal selected-data projection
```

P4 adapters may call these owners and add persistence-facing records around them. They may not reproduce their algorithms.

### 2.2 Mandatory implementation reconnaissance before edits

Before product edits, identify the real owners of:

- `prepare` parser and `command_prepare` call graph;
- `select-target-size` parser and `command_select_target_size` call graph;
- concrete CampaignStore/SQLite class/functions and transaction helpers;
- the pre-existing campaign/prepare target-size generation authority and all consumers of it;
- current target-size selection/restart keys and terminal selected-size fields;
- P3 execution-root construction and typed resolver/reconciler creation;
- P3 locking used for boundary/head publication and reconciliation;
- storage accounting/reclamation/archive ownership and destructive-operation entrypoints;
- user-facing CLI help and campaign guide text describing `prepare`/target-size behavior.

Expected high-impact surfaces include `_campaign_cli_core.py`, `campaign_cli.py`, the actual CampaignStore owner, `storage_accounting.py`, `storage_reclamation.py`, `storage_archive.py`, `target_size_experiment.py`, and P3 public resolver/reconciliation entrypoints. This is a starting map, not a scope cap.

The implementation must redirect/remove real production call edges, not add a new facade beside the old runtime.

---

## 3. P4 entry assertions inherited from closed P3

P4 does not own P3A9 implementation. Before P4-A, verify against the accepted P3 closure commit that:

- the real P3 reconciler recovers a unique authenticated linear successor chain when `current_head.json` is stale;
- complete-batch-without-head recovery remains deterministic and fail-closed;
- forks, unrelated orphan heads, corrupt successors, and tampered reducer ancestry reject;
- fresh-process reconciliation is identity-equivalent to uninterrupted execution;
- P3 success, TRAIN2-failure, EVAL2-failure, P3A7 restart-owner, and P3A8 owner-level acceptance remain passing;
- `current_head.json` remains a P3-local rebuildable pointer rather than campaign authority.

If any of these assertions is not established by the accepted P3 closure, P4 remains blocked and work routes back to P3 rather than implementing a P4 workaround.

---

## 4. Campaign current-state model and transactional CAS contract

### 4.1 One mutable state aggregate

Implement/reconcile one version-agnostic current target-size campaign-state aggregate in the real CampaignStore/SQLite owner. Exact table/column names are delegated, but the semantic state must bind, directly or through authenticated references:

- schema version;
- cutover/regime state;
- **canonical campaign target-size generation**;
- subordinate execution attempt identity where active;
- campaign state revision / predecessor token;
- lifecycle/stage state;
- P1 neutral/canonical/source authority identity;
- inherited protected/split-exclusion relation authority;
- P2 experiment definition/aggregate identity including hard-support authority;
- P3 screen/window identity and campaign-owned durable root locator;
- currently adopted immutable P3 execution-head digest and reducer-state digest, when present;
- terminal-result projection when terminal;
- stop/failure classification and replay/reference identity where applicable.

Do not copy the full P1-P3 immutable graph into mutable SQLite rows. Store stable identities/references and revalidate through owning loaders.

#### Canonical generation rule

Repository reconnaissance must identify the existing campaign/prepare target-size generation authority before schema design. P4 then either:

- evolves that exact authority in place, or
- atomically replaces it during the destructive cutover with one new canonical generation field while making the retired field unreachable/non-authoritative in the same cutover.

A design in which an old campaign generation and a new target-size runtime generation can advance independently is forbidden.

### 4.2 CAS predicate for every mutation

Every mutable target-size campaign transition executes in one real SQLite transaction and compares:

```text
expected regime/schema
expected canonical generation
expected subordinate attempt (if applicable)
expected predecessor campaign-state revision
```

The same transaction advances the state revision and writes the successor state.

A state revision may be an authenticated digest, monotonic token, or equivalent CampaignStore-owned CAS value. PID, wall-clock time, worker-local memory, or file modification time is insufficient.

Required behavior:

- generation `g` writer cannot mutate after `g+1` owns the campaign;
- same-generation writer with stale predecessor revision cannot mutate after another transition commits;
- two divergent transitions from one predecessor cannot both commit;
- crashed process does not permanently own the campaign; a fresh process resumes from persisted generation/attempt/revision;
- process identity never authorizes historical rewrite.

### 4.3 Deterministic logical-transition identity and idempotency

An already-committed transition may be treated as an idempotent duplicate only when its **logical transition identity** is exactly equal. That identity must deterministically bind at least:

```text
operation/transition kind
expected predecessor campaign-state revision
canonical generation
subordinate attempt identity, when applicable
canonical authoritative successor payload/reference set
```

The implementation may encode this as an explicit transition-intent digest, deterministic successor-state digest, or equivalent CampaignStore-owned representation.

PID, timestamp, retry count, or equality of only selected result fields is not transition identity.

On duplicate retry, load and verify the stored successor is exactly the one implied by the same logical transition identity before returning idempotent success. A conflicting successor from the same predecessor is a typed stale/conflict outcome, not a duplicate.

### 4.4 Same-generation race acceptance

Use two independent SQLite connections/process-equivalent clients against the same real campaign DB:

1. both read the same generation/attempt/revision;
2. both attempt different next states;
3. exactly one commits;
4. loser receives typed stale/conflict and cannot overwrite winner;
5. exact duplicate logical transition retry verifies/returns the existing identical state;
6. near-duplicate with one changed authoritative reference is rejected as conflict, not accepted as idempotent.

If CampaignStore lacks the primitive, add the smallest reusable store-level transaction/CAS helper. Do not implement compare-then-write as unlocked CLI operations.

---

## 5. Terminal result is an authenticated projection

### 5.1 Terminal-success derivation

When P3 becomes terminal with a selected target size:

```text
reconcile P3 through TargetSizeRestartAuthority
 -> obtain exact authenticated terminal execution head/post-reducer state
 -> derive terminal selection through P2 reducer/statistical owner
 -> derive exact T_selected through P2 training-order/T_N owner
 -> build terminal campaign projection
 -> CAS-commit adopted head + reducer digest + selected N + exact T_selected identity together
```

Use existing P2 owners. If a small pure projection helper is missing, add it adjacent to `target_size_experiment.py`; do not encode target-size decision logic in P4 CLI/store code.

`N_selected`, `T_selected`, stop reason, and terminal status must be internally consistent with authenticated terminal P2/P3 state.

### 5.2 Terminal load/restart validation

A completed selection may be exposed downstream only after the loader:

1. resolves referenced P1/P2 authorities;
2. reconciles/resolves referenced P3 screen/head through P3;
3. verifies reducer-state digest referenced by campaign state;
4. re-derives `N_selected` from terminal reducer state;
5. re-derives exact `T_selected` membership/identity from P2;
6. compares both with persisted terminal projection.

Any mismatch fails closed. Updating only a digest, selected integer, or selected-data field cannot make divergent state valid.

### 5.3 Terminal scientific failure versus interruption

Reducer-terminal configured-ceiling nonconvergence or another frozen scientific terminal failure persists as a terminal scientific outcome bound to exact P2/P3 provenance. It is not an operational interruption eligible for indefinite same-screen resume.

Process death, transient resource failure, or an incomplete rung without terminal P2/P3 outcome remains operationally resumable and cannot be materialized as scientific nonconvergence.

Mandatory negatives:

- mutate only persisted selected `N` -> reject;
- mutate only exact `T_selected` identity/membership -> reject;
- mutate adopted head/reducer reference while selected fields remain -> reject;
- terminal success fresh-process reload re-derives identical projection;
- terminal scientific failure reload stays terminal and cannot masquerade as interruption.

---

## 6. Cross-store visibility, recovery, and lock ordering

SQLite and filesystem evidence cannot share one physical atomic transaction. P4 therefore uses immutable-first publication, authenticated reconciliation, bounded CAS adoption, and deterministic recovery.

### 6.1 Canonical transition order

For target-size advancement that depends on new P3 evidence:

```text
1. P3 produces attempt-local work.
2. P3 validates scientific parents through accepted P1/P2/P3 owners.
3. P3 publishes immutable evidence with existing create-or-verify durability.
4. P3 commits/reconciles its immutable execution-head graph.
5. P3 releases its head/screen mutation lock.
6. P4 receives the exact authenticated reconciled immutable head/post-state.
7. P4 opens a short real CampaignStore transaction with regime + generation + attempt + predecessor CAS.
8. P4 binds exact P3 screen/head/reducer identities and next lifecycle state.
9. P4 commits and releases SQLite.
10. Human-readable/external views are generated only as non-authoritative projections.
11. Reconciliation classifies leftover filesystem evidence.
12. STOR destructive cleanup/retirement may run only under section 10 retention rules.
```

A campaign row may never reference incomplete/unvalidated P3 evidence. File existence alone is never completion evidence.

### 6.2 Required recovery matrix

| Crash/restart state | Required behavior |
|---|---|
| crash before P3 immutable publication | resume/recompute through P3; campaign state unchanged |
| complete batch durable but head absent | closed P3 reconciler validates unique batch and commits head |
| immutable successor head durable but P3 pointer stale | closed P3/P3A9 reconciler replays unique successor chain and repairs pointer |
| P3 reconciled head ahead of SQLite | if scientific identity + campaign generation/attempt match, CAS-adopt exact head; do not rerun completed work |
| SQLite references missing/corrupt P3 head | hard corruption reject; never recreate authority from SQLite summary |
| SQLite references older head and P3 has one unique valid successor chain | reconcile P3 then CAS-adopt successor under same current generation; fork/conflict rejects |
| SQLite commit complete but derived result/view missing | rebuild view from SQLite + P3; do not roll back science |
| crash during legacy->current cutover | remain transition-owned; restart exact transition via CAS; current runtime blocked |
| stale generation writer resumes | typed stale/conflict; no mutation |
| two same-generation writers race | predecessor CAS permits one divergent successor only |
| cleanup races P3-publication -> SQLite-adoption window | section 10 retention fence preserves all still-adoptable/reconcilable evidence |

### 6.3 Frozen cross-subsystem lock/transaction ordering

There are three mutation domains:

```text
P3 filesystem execution/reconciliation
CampaignStore SQLite state mutation
STOR destructive mutation
```

Their ordering is frozen:

```text
P3 reconcile/commit
  -> release P3 mutation lock
CampaignStore bounded CAS transaction
  -> commit/release SQLite
STOR destructive classification/reclamation
```

Hard constraints:

- never hold a CampaignStore SQLite write transaction while acquiring a P3 screen/head mutation lock;
- never perform P3 reconciliation, large artifact hashing, model/provider reconstruction, or slow filesystem traversal inside the SQLite write transaction;
- never hold a STOR destructive-operation lock/lease while waiting for CampaignStore or P3 mutation authority in reverse order;
- STOR may perform non-destructive accounting/inspection as repository conventions allow, but destructive authorization occurs only after campaign/P3 state needed for reachability classification is stable and the retention fence has been evaluated;
- no process-liveness lock may substitute for durable generation/revision fencing.

If actual repository lock ownership makes this ordering impossible without a material architecture replacement, stop and reopen only the affected persistence/concurrency surface.

---

## 7. Destructive-generation cutover and legacy-state disposition

### 7.1 Durable regime transition

Use one campaign-level durable regime marker in the real SQLite owner with semantics equivalent to:

```text
legacy/unconverted
transitioning-to-current
current
```

Required transition:

1. CAS `legacy -> transitioning`, allocating/binding the new **canonical** target-size generation and exact predecessor revision.
2. Inventory retired target-size derived state before mutation.
3. Quarantine/reject retired derived authority; do not translate it into P1/P2/P3 objects.
4. Reconstruct current P1/P2/P3 state from source inputs and only independently reusable lower-level caches through current validators.
5. Persist current campaign references/state through CAS while regime remains `transitioning`.
6. Validate all current authorities and prove retired target-size records are not current authority.
7. CAS `transitioning -> current` from exact expected transition revision.
8. Only after `current` is durable may ordinary production target-size runtime proceed.

A fresh process resumes interrupted `transitioning` state from persisted transition identity/revision; original PID survival is irrelevant.

### 7.2 No mixed runtime

Cutover is campaign/runtime-wide. Do not lazily migrate rows such that some datasets execute retired selection while others execute P1-P3. While `transitioning`, target-size commands resume transition or fail with actionable guidance.

### 7.3 Retired-state inventory

At minimum stop consuming/reject/quarantine as current authority:

- `target_size_study.py` selector state;
- prepare-time selected-N/selector outcomes;
- `TargetDataRoleFreeze` target-size authority;
- FEAS/MVIDX/MVSEL/REPAIR/MVSTATE/MVQUAL current-runtime selection records;
- compatibility/label-domain target-size maps and `domain_prefix_digests`;
- per-domain prescribed target/evaluation materialization authority;
- complement/coarse EVAL2 target-size roles;
- pre-target CV/MLCV role/catalog dependencies;
- retired target-size prepare receipts/migration aliases;
- old selected-N records lacking the full current P1/P2/P3 authority chain;
- incompatible resumable checkpoints/continuations;
- orphaned incomplete attempts unable to authenticate to current generation.

Raw source files, manifests, provenance parsing, and lower-level content-addressed caches may be reused only where the current owner proves recipe/identity equivalence independent of retired target-size semantics.

P4 does not broadly delete historical scientific evidence. P6 owns broad topology deletion. P4 removes/quarantines only mutable current-state records necessary for unambiguous cutover and safe recovery.

---

## 8. Current invalidation matrix and failure disposition

The current loader/caller classifies mismatches rather than silently repairing them.

| Changed/bad authority | Disposition |
|---|---|
| malformed schema/digest, changed artifact bytes, typed-content mismatch | hard corruption reject |
| P1 source/canonical/neutral identity change | invalidate descendants; fresh current generation |
| protected/split-exclusion relation change | invalidate P2/P3/terminal target-size state; fresh generation |
| P2 target-size policy, hard support, target/eval powers, fidelity, metric, practical-equivalence policy | fresh generation |
| `U_size`, `P_train/M3`, `pi_train`, `pi_eval`, qualified candidate set/order change | fresh generation |
| ordered optimizer seed set change | fresh generation |
| common preparation/training recipe/optimizer/evaluation-state policy change | fresh generation |
| materialization/export/source/checkpoint/evaluation identity change | reject stale evidence and rebuild under fresh valid generation as scientifically appropriate |
| P3 screen/window/plan/boundary identity change | stale current state; fresh generation unless exact owner proves same experiment |
| execution owner/generation mismatch | typed stale/conflict or corruption; never transfer old owner |
| required live/EMA/raw checkpoint state missing/incompatible | fail through P3 checkpoint owner; no downgrade |
| current schema/regime mismatch | reject/quarantine; explicit destructive transition |
| retired target-size schema/record | reject/quarantine; never reinterpret |
| CV-only fold count/seed/settings change | preserve target-size identity/result; invalidate CV descendants only |
| production-only horizon/adaptive settings change | preserve target-size identity/result; invalidate production descendants only |

Equality of selected integer `N` alone never proves equivalence after invalidation.

---

## 9. P3 checkpoint/restart semantics P4 preserves exactly

P4 may persist references to P3 checkpoint evidence but cannot reinterpret it.

For TRAIN2 boundaries:

- raw MACE checkpoint bytes remain authenticated by bound digest;
- with EMA enabled, raw checkpoint model parameters represent accepted MACE checkpoint-save EMA-shadow state;
- companion `live_parameters` represent authenticated continuation/live optimization state;
- authenticated EMA shadow is canonical evaluation state when frozen optimizer policy requires EMA;
- without EMA, raw checkpoint/live state follows accepted non-EMA contract;
- evaluation-state choice derives from canonical optimizer-policy owner, never editable persistence metadata;
- numerical checkpoint validity does not grant execution ownership;
- restart preserves exact raw/live/EMA distinctions through real P3 owner;
- missing/malformed/noncanonical state fails closed without representation fallback.

P3A5/P3A6/P3A7 and later cumulative P3 restart acceptance remain regression authority.

---

## 10. STOR1-STOR5 lifecycle integration and retention fence

P3 evidence becomes production campaign state after P4. Existing storage accounting/reclamation/archive machinery must understand and protect its lifecycle.

### 10.1 Reuse existing storage owners

Integrate through existing `storage_accounting.py`, `storage_reclamation.py`, `storage_archive.py`, and real CLI/ownership helpers. Do not create a target-size-specific deleter/queue or bypass STOR containment/ownership checks.

### 10.2 Artifact families to classify/account

At minimum account the promoted P3 families actually present:

- screen/window identity;
- immutable boundary batches and execution heads;
- logical progress/current-head recovery pointers;
- cell completions;
- candidate trajectories/materializations;
- planned rungs and continuation requests;
- boundary snapshots plus raw checkpoint/companion/runtime-summary bytes;
- EVAL2 roles and exact-M evaluation artifacts;
- predictions and metric records;
- raw TRAIN2/EVAL2 failure records and failure checkpoint bytes;
- current-generation attempt-local/staging files under campaign ownership.

### 10.3 Active/restartable execution-root retention fence

While a target-size campaign generation is `transitioning`, active, operationally interrupted/restartable, or awaiting authenticated adoption of newly published P3 state, the campaign-owned **P3 execution root** is a STOR protected root.

Protection cannot depend solely on the P3 head already adopted by SQLite. Before SQLite adoption, the following remain protected when they belong to the current generation/attempt and have not yet been rejected by reconciliation:

- the authenticated current P3 ancestry;
- immutable batches/heads/completions and their required evidence that can still be part of a unique valid successor chain;
- complete boundary batches that P3 can still reconcile into a head;
- checkpoint/materialization/evaluation/failure ancestry required to validate such heads/batches;
- attempt-local publication/staging material that the existing P3 owner still classifies as resumable/recoverable rather than disposable.

This set is the **reconciliation frontier**. It is protected until the real P3 reconciler plus current campaign generation/attempt classification decides whether each item is adopted/reachable, retained historical evidence, corrupt/conflicting, or provably unreachable campaign-owned residue.

Consequences:

- absence of an SQLite reference is **not** by itself proof that a current-generation P3 artifact is orphaned;
- safe cleanup must not race ahead of reconciliation and delete a valid successor merely because the adoption CAS has not yet committed;
- reconciliation runs before reclamation classification for ambiguous current-generation P3 evidence;
- after classification and authenticated campaign adoption/reload, existing STOR ownership + reachability + capability rules decide retention/reclamation;
- external, symlink-escaped, or ownership-ambiguous paths never gain deletion authority from a P3 reference.

Use the smallest integration with existing STOR reachability/protection mechanisms. Do not make the whole target-size workspace permanently non-reclaimable; protection is tied to current/restartable generation state and unresolved reconciliation capability.

### 10.4 Retention classes

Storage planning distinguishes at least:

- current/restart-required — protected;
- current terminal provenance — retained unless an existing later STOR tier proves preserved capability;
- active attempt — protected;
- unresolved reconciliation-frontier evidence — protected;
- historical retained immutable evidence — auditable under existing policy;
- provably unreachable campaign-owned temporary/orphan evidence — reclamation eligible only through existing STOR ownership/reachability/capability checks;
- external/ownership-ambiguous path — never deletion-authorized merely because referenced.

### 10.5 Storage acceptance, including concurrent race

Prove through real storage owners that:

- `storage report` includes promoted target-size artifact families/bytes;
- safe cleanup during interrupted screen preserves fresh-process reconciliation and candidate continuation;
- safe cleanup after crash preserves an unreferenced-but-adoptable immutable head/batch before reconciliation;
- **cleanup racing the P3 publication -> reconciliation -> SQLite adoption window cannot unlink any head, batch, completion, checkpoint/materialization/evaluation/failure ancestry, or other evidence the current generation can still legitimately adopt**;
- once reconciliation classifies evidence as provably unreachable and campaign state is reloaded/authenticated, existing STOR safe cleanup can reclaim eligible campaign-owned residue;
- external references, symlink escapes, and ambiguous ownership remain protected;
- fresh-process replay after safe cleanup yields identical scientific state;
- no target-size retention logic weakens STOR1-STOR5 guarantees.

The race acceptance must exercise real STOR destructive authorization and real P3/campaign state; a test-local "do not delete" flag that production cleanup does not consume is insufficient.

---

## 11. Atomic production orchestration switch

### 11.1 `prepare`

After cutover, real `prepare` may construct/load P1 neutral substrate and deterministic prerequisites/common preparation independent of candidate `N`, but it must not:

- select `N`;
- execute P2 paired-screen reducer;
- train target-size candidates;
- perform target-size EVAL2 ranking;
- construct pre-target CV plans;
- create compatibility-domain/per-domain target-size authority merely for legacy code.

Any prerequisite persisted by `prepare` is version-agnostic and authenticated to current P1/current campaign regime.

### 11.2 `select-target-size`

Real `select-target-size` must:

1. load/revalidate current P1 authority from campaign state;
2. construct/load exact P2 experiment through `target_size_experiment` owners;
3. construct/load P3 common preparation/execution context/screen window;
4. reconcile existing P3 root before new scheduling;
5. derive active P2 matrix from authenticated reducer state;
6. execute only required surviving `(N, optimizer_seed)` cells through P3 candidate/TRAIN2/EVAL2 owners;
7. publish through P3 completion/batch/head owners;
8. reconcile resulting P3 head;
9. CAS-adopt exact P3 head/reducer identity into campaign state;
10. repeat only while P2 reducer is nonterminal;
11. on terminal success derive/atomically persist terminal projection from section 5;
12. on terminal scientific failure persist authenticated terminal failure state;
13. report only after current campaign projection reload/revalidation.

No P4-local ranking or restart loop may bypass P2 reducer/P3 reconciliation.

### 11.3 Retired call-edge removal

In the same coherent cutover, remove production call edges from `prepare`/`select-target-size` to retired role/domain/selector authorities. `target_size_study.py` and old modules may remain physically until P6 only if unreachable from current target-size production entrypoints and not imported as current authority.

Preserve the guard that public ordinary `train`/`evaluate` cannot become a second target-size screening scheduler.

Forbidden:

- runtime old/new feature flag;
- try-current/fallback-retired;
- dual authoritative writes;
- old-schema alias interpreted as current;
- wrapper rebuilding retired label-domain maps internally;
- P4-local selector/reducer/replay engine;
- manual selected-N override;
- file existence/PID as current-state proof.

---

## 12. Material implementation passes and gates

Execute in order after the P3A9 entry gate has closed. Each behavior-changing pass requires semantic/conformance closure plus focused and affected regression before dependent work.

### Pass P4-A — CampaignStore state, canonical generation, CAS, transition identity

1. Locate real CampaignStore and existing generation owner.
2. Add/reconcile version-agnostic target-size regime/current-state records.
3. Consolidate to one canonical target-size generation authority; retire any parallel current authority in the eventual cutover design.
4. Add one transaction-level CAS checking regime + generation + attempt + predecessor revision.
5. Add deterministic logical-transition identity/idempotent retry verification.
6. Add typed stale/conflict/corruption outcomes per existing conventions.
7. Add terminal projection fields/references without public runtime wiring yet.

**Gate:**

- schema/serialization roundtrip;
- real SQLite close/reopen;
- rollback leaves predecessor unchanged;
- older-generation rejection;
- same-generation stale-revision rejection;
- divergent same-predecessor race admits exactly one successor;
- exact logical duplicate retry idempotent;
- near-duplicate changed-reference retry conflicts;
- structural proof there is one canonical target-size generation authority;
- retired schema cannot deserialize/relabel as current;
- no `v7_`/`V7` new production key/symbol.

### Pass P4-B — Regime cutover owner

1. Implement durable `legacy -> transitioning -> current` semantics in CampaignStore.
2. Allocate/bind canonical generation through exact CAS transition.
3. Inventory/quarantine/reject retired derived target-size state.
4. Permit only validator-proven reusable lower-level inputs/caches.
5. Add actionable fail-closed guidance for incompatible old workspaces.
6. Keep public target-size orchestration coherently pre-switch until P4-D; no half-wired runtime.

**Gate:** fresh current campaign; legacy enters transition once; crash resumes exact transition; competing transition rejected; no row-wise mixed execution; old selected-N/selector records never become current P2/P3 authority.

### Pass P4-C — Cross-store adoption, retention fence, restart, concurrency

1. Wire P3 reconciled head into CampaignStore CAS adoption.
2. Implement section 6 recovery matrix and section 6.3 ordering.
3. Implement the section 10.3 active/restartable execution-root retention fence before any safe cleanup can encounter promoted P3 evidence.
4. Ensure SQLite adopts immutable head/reducer identities, not `current_head.json` as authority.
5. Ensure stale/generation races return typed conflicts without P3-history mutation.
6. Keep external result views non-authoritative.

**Gate:** every section 6.2 crash case with real SQLite and real P3 resolver/reconciler, plus concurrent cleanup race proving the retention fence. In-memory stores/fake persistence/fake STOR destructive authorization cannot close this gate.

### Pass P4-D — Atomic `prepare` / `select-target-size` production switch

1. Rewrite real orchestration edges per section 11.
2. Use P1/P2/P3 owners directly.
3. Remove reachable old target-size call edges in the same coherent switch.
4. Preserve shared optimized execution/materialization/inference machinery P3 already reuses.
5. Preserve ordinary `train`/`evaluate` scheduler guards.
6. Ensure the cutover leaves only the canonical generation/current-state authority reachable.

**Gate:** bounded real parser + CampaignStore + `prepare` integration proving no N selection; bounded real parser + CampaignStore + `select-target-size` reaching P1/P2/P3; no old selector/domain/complement/CV authority in current call graph; one current generation authority; stage-local affected CLI regression.

Expensive training/prediction may be replaced below the accepted owner boundary only after real config parsing, authority construction, provider/state validation, materialization validation, and orchestration ownership execute.

### Pass P4-E — Terminal projection, semantic restart, invalidation

1. Implement terminal derivation/reload validation.
2. Wire section 8 invalidation classes through real current loader/caller.
3. Preserve raw/live/EMA restart semantics.
4. Distinguish terminal scientific failure from operational interruption.

**Gate:** terminal success rederivation; selected-N/T-selected/head tamper negatives; protected/hard-support change invalidation; seed/order/fidelity/metric/training-policy invalidation; EMA/live malformed restart rejection through real owner; CV-only/production-only changes target-size-neutral; fresh-process mid-screen continuation and terminal replay.

### Pass P4-F — Full STOR integration, docs, structural closure

1. Complete P3 artifact-family accounting/reachability/retention in existing STOR owners.
2. Run section 10.5 storage acceptance including concurrent cleanup/adoption race.
3. Update affected public CLI/help/docs, at minimum the actually affected parts of:
   - `docs/guides/mlff_campaign_cli_user_guide.md`;
   - parser/help text owned by current campaign CLI;
   - `campaign.toml.example` if exposed config semantics changed;
   - current architecture/source-map docs where needed for truthfulness.
4. State clearly that `prepare` no longer performs target-size selection/training and `select-target-size` owns current P2/P3 screening.
5. Run structural searches/import checks proving retired target-size owners unreachable and only one mutable current authority/generation remains.

**Gate:** storage report/safe-cleanup/race tests; docs/help tests/lint where available; no current docs claim retired lifecycle; no version-prefixed product names; old selector/runtime modules unreachable from current CLI authority.

### Pass P4-G — Assembled affected-surface closure

Re-derive affected surface from complete P4 diff. Run:

- all accepted P3A9 recovery regressions if P4 changes can plausibly affect their callers/roots;
- complete affected P1/P2/P3 regression where integration diff affects callers;
- complete affected campaign persistence/CLI regression;
- restart/invalidation matrix;
- concurrency/CAS/transition-identity matrix;
- STOR regression for touched ownership/reclamation paths, including concurrent publication/adoption cleanup race;
- structural absence/uniqueness checks;
- bounded real-owner `prepare -> select-target-size -> terminal projection reload` integration;
- broader repository suite if affected-surface inspection cannot independently bound a smaller set.

Do not run long GPU/real-production qualification as P4 exit requirement.

---

## 13. Mandatory real-owner acceptance

P4 is not accepted by record-constructor unit tests alone.

### Persistence/concurrency

- real CampaignStore/SQLite reopen preserves current state;
- transaction rollback cannot expose partial state;
- exactly one canonical target-size generation owner is reachable;
- generation `g` writer loses after `g+1` takeover;
- two same-generation writers from same predecessor admit one divergent successor;
- exact logical retry verifies/returns identical state;
- near-duplicate is conflict;
- cutover restart does not depend on PID;
- no SQLite write transaction nests P3 reconciliation or STOR destructive work.

### P3 crash/replay/adoption

- accepted P3A9 unique-successor recovery remains valid;
- missing pointer, stale pointer, linear successors, fork rejection, and complete-batch recovery remain through real P3 owner;
- success/TRAIN2-failure/EVAL2-failure fresh-process replay;
- campaign adopts only reconciled immutable head digest;
- SQLite-behind-P3 crash state adopts without rerunning completed science.

### Scientific identity/invalidation

- P1 source/canonical mismatch;
- protected relation mismatch;
- P2 hard-support mismatch;
- split/order/candidate-set mismatch;
- optimizer-seed mismatch/reorder;
- fidelity/evaluation-power mismatch;
- common preparation/training policy mismatch;
- evaluation-state/EMA mismatch;
- checkpoint/artifact corruption;
- schema/regime mismatch;
- CV-only/production-only changes remain target-size-neutral.

### Terminal projection

- terminal reducer -> exactly one selected `N` + exact `T_selected` projection;
- selected-N mismatch rejects;
- T-selected mismatch rejects;
- adopted head/reducer mismatch rejects;
- configured-ceiling nonconvergence remains terminal scientific result;
- operational interruption remains resumable.

### Runtime cutover

- real `prepare` reaches current P1 path but cannot select `N`;
- real `select-target-size` reaches P2/P3 and no retired selector;
- no pre-target CV dependency;
- no complement/coarse target-size EVAL2 role;
- ordinary `train`/`evaluate` cannot schedule screen;
- old current-runtime records fail closed with reset/reprepare guidance.

### Storage

- P3 bytes appear in storage accounting;
- active/restart-required execution root is protected independent of adopted SQLite head;
- reconciliation-frontier evidence survives safe cleanup;
- cleanup racing publication/reconciliation/adoption cannot delete legitimately adoptable evidence;
- provably unreachable owned residue becomes reclaimable after classification;
- external/symlink/ambiguous ownership cannot acquire deletion authority;
- fresh-process replay after safe cleanup is identical.

Mocks/fakes may replace expensive numerical work only **below** the real semantic-owner boundary. They may not replace CampaignStore, P3 resolver/reconciler, P1/P2 authority construction, state/provider authentication, STOR destructive authorization when storage safety is claimed, or the CLI parser when those owners are under acceptance.

---

## 14. Failure taxonomy

Preserve these semantic classes:

1. **Corruption/tampering** — bad digest/schema/bytes/typed graph. Hard reject; no auto-recompute while claiming continuation.
2. **Scientific incompatibility/invalidation** — valid prior state belongs to different scientific identity. Quarantine/retire authority and start justified fresh generation.
3. **Stale writer/revision conflict** — writer lost generation/predecessor CAS. Abort mutation; do not rewrite history.
4. **Operational interruption** — incomplete current work without terminal scientific outcome. Resume through P3/current CampaignStore state.
5. **Terminal scientific failure/nonconvergence** — authenticated terminal reducer/scientific outcome. Persist terminal; do not loop as interruption.
6. **Incomplete cutover** — regime is transitioning. Resume exact cutover or fail with actionable guidance; no mixed runtime.
7. **Legacy incompatible workspace** — old derived target-size authority. Reject with destructive reset/reprepare guidance; no migration/reinterpretation.

Do not collapse these into generic "missing cache, recompute everything" behavior.

---

## 15. Performance and implementation-economy constraints

P4 is integration/cutover, not permission to replace proven optimized machinery.

- reuse optimized DATA8/TRAIN2/EVAL2/provider/inference/materialization paths already consumed by P3;
- reuse P3 create-or-verify publication and resolver validation;
- reuse CampaignStore rather than adding another DB;
- reuse STOR ownership/accounting/reclamation rather than target-size-specific cleanup;
- avoid rehashing/copying large immutable artifacts into SQLite;
- store references/digests and revalidate through owners;
- do not introduce per-domain loops or pre-target CV work retired by parent;
- recovery reuses durable completed evidence rather than rerunning expensive training/evaluation;
- keep SQLite CAS transactions short and free of slow P3/STOR I/O;
- retention fence must not permanently pin proven unreachable historical residue;
- no performance optimization weakens provenance, restart exactness, CAS fencing, storage safety, or scientific validation.

Bounded checks for repeated hashing/copying, serialization, lock contention, and cleanup/recovery regressions are appropriate. Long machine-specific production benchmarking remains final-release work.

---

## 16. Structural closure checks

At P4 exit, AST/import/search inspection plus real call-path tests establish:

- production `prepare` and `select-target-size` depend on accepted P1/P2/P3 owners;
- no second target-size split/reducer/trainer/evaluator/restart implementation in P4;
- `target_size_study.py` unreachable from current target-size production entrypoints;
- retired FEAS/MVIDX/MVSEL/REPAIR/MVSTATE/MVQUAL/domain/complement/CV-coupled call edges absent from current orchestration;
- current target-size state has no compatibility-domain map/pre-target CV plan authority;
- exactly one canonical mutable target-size generation/current-state authority exists in CampaignStore;
- P3 `current_head.json` is not sufficient campaign completion/selection authority;
- no new `v7_`/`V7` product code/symbol/schema/record key;
- no old-runtime loader can authorize current selected target size;
- safe cleanup cannot unlink active/restart-required/reconciliation-frontier P3 evidence;
- no reverse nested lock/transaction path violates section 6.3.

Physical removal of all retired files remains P6 unless a mutable state record must be removed in P4 to prevent ambiguous current authority.

---

## 17. P4 exit criteria

P4 is complete only when:

1. cumulative P3 revision 7 through P3A9 was accepted and formally recorded **before P4 execution began**;
2. real CampaignStore has one current target-size state authority and one canonical generation with subordinate attempts + predecessor CAS fencing;
3. deterministic logical-transition identity makes exact duplicate retry safe and divergent same-predecessor transitions exclusive;
4. P3 immutable evidence remains sole scientific execution/replay authority; `current_head.json` remains rebuildable local pointer;
5. cross-store recovery adopts validated complete evidence and rejects forks/corruption without fake physical transaction;
6. cross-subsystem lock ordering is acyclic and SQLite mutation remains bounded;
7. `N_selected` and exact `T_selected` are re-derived terminal projections, not independent decisions;
8. terminal scientific failure differs from operational interruption;
9. legacy derived state is rejected/quarantined without reinterpretation; no mixed runtime;
10. current `prepare` does not select `N`; current `select-target-size` uses P2/P3 as sole screening entrypoint;
11. retired selector/domain/complement/pre-target-CV call edges are unreachable;
12. raw/live/EMA semantics and historical owner proof remain intact;
13. promoted P3 evidence participates in STOR accounting/retention/reclamation;
14. active/restartable execution-root + reconciliation-frontier retention prevents cleanup/adoption races without unbounded permanent retention;
15. public CLI help/docs describe actual lifecycle;
16. production naming remains version-agnostic;
17. complete affected regression, integration, crash, concurrency, invalidation, storage, race, and structural acceptance passes;
18. no long GPU/real-production qualification was required for P4 closure.

Only then may P5 treat selected target-size state as frozen current authority.

---

## 18. Implementer execution discipline

1. Verify P4 metadata is active and binds the accepted cumulative P3-through-P3A9 closure commit. If not, do not start P4 executable work.
2. Perform section 2.2 reconnaissance before editing.
3. Verify section 3 inherited P3 entry assertions; if false, route to P3 repair rather than work around them.
4. Implement P4-A through P4-G in order; close each material pass semantically and functionally before dependent work.
5. When a gate fails, repair the smallest owning layer; do not bypass with compatibility shim, second authority, or test-only alternate path.
6. Preserve P1-P3 semantics unless a section 19 redesign trigger is genuinely demonstrated.
7. Prefer existing owners over new modules when ownership fits.
8. New persistence/storage helpers must be exercised by production callers before their tests count as acceptance.
9. Keep expensive numerical fakes below real-owner boundary in section 13.
10. Re-derive final affected surface from actual assembled diff.
11. Report separately: stage-local gates; final affected regression/integration; deferred long GPU/real-production qualification.

Old tests that encode retired architecture may be updated/removed only where frozen parent proves expectation obsolete. Stop/reopen only for a genuine material blocker.

---

## 19. Implementation authority

### Frozen

- frozen parent and all accepted P1/P2/P3 scientific semantics/ownership;
- P3A9 belongs to P3 closure and must be accepted before P4 starts;
- one current CampaignStore mutable authority and one canonical target-size generation;
- attempts subordinate to canonical generation;
- P3 immutable scientific evidence/replay authority;
- `current_head.json` non-authoritative outside P3 recovery/localization;
- generation + predecessor-revision transactional CAS;
- deterministic logical-transition identity for duplicate retry;
- terminal N/T derivation from authenticated state;
- one destructive-generation cutover with no mixed runtime;
- no retired-state reinterpretation;
- P3 -> CampaignStore -> STOR mutation ordering from section 6.3;
- active/restartable execution-root and reconciliation-frontier storage protection;
- version-agnostic production naming;
- long GPU qualification deferred.

### Delegated

The implementer may choose, consistent with repository conventions:

- exact SQLite table/column/schema names;
- monotonic integer vs authenticated digest vs equivalent CampaignStore-owned state revision;
- explicit transition-intent digest vs equivalent deterministic successor identity;
- exact transaction helper names;
- exact regime enum spellings;
- exact representation by which the existing generation authority is evolved/replaced during cutover, provided only one canonical authority remains;
- exact STOR protected-root/reachability representation, provided production cleanup consumes it and section 10 semantics hold;
- whether human-readable terminal result view is SQLite-only or mirrored non-authoritatively;
- exact test filenames;
- small CLI/store adapter refactors needed to consume P1/P2/P3 owners.

Delegation cannot weaken frozen invariants or acceptance.

### Reopen only on material evidence

Reopen only if implementation proves one of:

- real CampaignStore cannot provide transactional canonical-generation + predecessor-state CAS without material persistence replacement;
- existing campaign generation ownership cannot be consolidated to one canonical authority without material cross-campaign redesign;
- P3 immutable graph cannot be durably referenced/revalidated from campaign state without changing frozen P3 science;
- accepted P3A9 closure is insufficient for the cross-store recovery states P4 must adopt;
- existing lock ownership makes the frozen acyclic P3 -> CampaignStore -> STOR ordering impossible without material architecture change;
- current STOR ownership/reachability model cannot protect unresolved current-generation P3 reconciliation-frontier evidence without material storage-architecture change;
- a frozen parent requirement is internally contradictory with accepted P1-P3 implementation.

Legacy tests, old workspace compatibility, convenience of reusing retired selected-N state, desire for a second generation counter, or desire to avoid public documentation updates are not reopen conditions.

---

## 20. Handoff closure

This revision preserves every material protected concern from the parent and P4 revision 3 while eliminating the circular predecessor gate and closing the final persistence/concurrency escape hatches:

```text
parent scientific reset + accepted P1/P2/P3 semantics
+ P3A9 crash-recovery closure before P4
+ one canonical campaign generation/current authority
+ predecessor CAS + deterministic transition identity
+ immutable-first P3 publication / bounded SQLite adoption
+ acyclic P3 -> CampaignStore -> STOR mutation ordering
+ pre-adoption execution-root/reconciliation-frontier retention
+ derived terminal N/T projection
+ destructive no-fallback runtime cutover
+ real-owner regression/integration/storage-race acceptance
-> lossless P4 implementation contract
```

No known material requirement, protected concern, frozen decision, persistence/recovery consequence, storage-lifecycle consequence, or required acceptance boundary remains intentionally delegated to implementation interpretation.
