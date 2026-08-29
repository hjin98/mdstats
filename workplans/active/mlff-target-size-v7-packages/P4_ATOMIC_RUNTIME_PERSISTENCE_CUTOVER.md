---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: active
package_revision: 3
amended_date: 2026-08-29
entry_p3_commit: 472276ee521eb2b19177299c1c9ad660dbd6ad46
prior_p4_revision_commit: 4c55a283f49124972933ccfc8a700be0a8b8ee1e
compatibility_policy: destructive-generation-reset
entry_gate: p4-0-p3-head-recovery-repair-and-formal-p3-closure-required-before-p4-runtime-cutover
reconciliation_reason: Revision 3 preserves the frozen parent and accepted P1-P3 scientific semantics while incorporating the final implementation-handoff review. It adds one mandatory narrow P3 execution-head crash-recovery prerequisite, makes campaign authority and same-generation compare-and-set semantics explicit, freezes selected-N/T-selected as derived projections rather than independent persisted decisions, integrates promoted P3 evidence with STOR1-STOR5 lifecycle ownership, requires public CLI/documentation cutover, and expands real-owner crash/concurrency/restart acceptance so implementation cannot satisfy P4 through proxy persistence or a parallel state machine.
---

# P4 — Atomic runtime and persistence cutover

## 0. Authority, revision disposition, and implementation entry rule

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P4 does **not** reopen P1-P3 science, statistics, candidate qualification, reducer policy, TRAIN2/EVAL2 semantics, checkpoint semantics, provider ownership, seed policy, or target-size decision logic.

P4 revision 3 is the implementation handoff contract. It supersedes revision 2 only for implementation precision and newly demonstrated persistence/recovery consequences. The accepted owner chain remains:

```text
P1 neutral_substrate
  -> P2 target_size_experiment
  -> P3 target_size_execution
  -> P4 campaign orchestration/persistence cutover
```

P4 inherits the complete accepted P1/P2/P3 history through the P3A8 implementation state at `472276ee521eb2b19177299c1c9ad660dbd6ad46`.

### Mandatory entry rule

**Do not begin the production runtime cutover until Pass P4-0 is implemented, accepted, and the cumulative P3 exit is formally recorded.**

P4-0 is a narrow repair inside the existing P3 persistence/reconciliation owner. It exists because final P4 review demonstrated a real crash window in the current implementation: an immutable successor execution head can be durable while `current_head.json` still points to its predecessor. The current P3 reconciler rejects that valid successor as an orphan rather than replaying and adopting it. This defect must be closed in P3 itself; P4 must not work around it with another replay engine.

P4-0 does **not** reopen P3 scientific design. It repairs only crash recovery of already-defined P3 immutable execution-head ancestry.

All new production code, symbols, schema names, record names, keys, and persisted authority names introduced by P4 must be **version-agnostic**. `V7` remains historical workplan/generation terminology only. Semantic product names use explicit schema/generation fields rather than `v7_` or `V7` prefixes.

Full long GPU/real-production qualification remains deferred to final release. P4 requires bounded functional, regression, restart, concurrency, real-owner persistence, and CPU/reference acceptance only.

---

## 1. Required product outcome and non-negotiable authority invariants

After P4, ordinary `prepare` and `select-target-size` must expose exactly one current target-size architecture. The P1-P3 graph is the only scientific authority for target-size work; the campaign store is the only mutable current-runtime authority; restart is deterministic and authenticated; and stale or retired state cannot become current through schema translation, pointer existence, process ownership, or duplicated mutable metadata.

The implementation must preserve all of the following simultaneously:

1. **One mutable campaign authority.** The real campaign SQLite persistence owner is the sole authority for current regime, current runtime generation/attempt, mutable stage/FSM state, adopted P3 execution-head reference, and terminal target-size result visibility.
2. **One scientific execution authority.** P3 immutable content-addressed evidence, heads, batches, completions, snapshots, predictions, metrics, failures, and typed replay graph remain the scientific execution authority.
3. **`current_head.json` is not campaign authority.** The P3 `current_head.json` file is only a rebuildable execution-local recovery/index pointer to an authenticated immutable head. It may accelerate/localize reconciliation, but it may not independently authorize campaign generation, completion, selected `N`, or downstream selected data.
4. **No second mutable result manifest.** If an external terminal-result file is retained for usability, it must be either immutable/content-addressed evidence or a rebuildable non-authoritative view of SQLite + authenticated P3 state. It must not be another current-state owner.
5. **No parallel algorithmic owner.** P4 must not implement another split builder, selector, reducer, target-size scheduler, checkpoint interpreter, evaluation engine, immutable evidence graph, or restart/replay algorithm.
6. **No fallback/dual-write regime.** Current execution may not try the promoted path and fall back to the retired path; may not write old and current authoritative records; and may not reinterpret retired schemas as current.
7. **Terminal selection is derived, not editable.** `N_selected` and exact `T_selected` are authenticated projections of the terminal P2/P3 state. Persisted copies are materialized results for downstream use, never independent decision inputs.
8. **Historical P3 ownership is immutable.** A new process/generation may own new operational work, but may not rewrite the owner proof of historical P3 evidence.
9. **Same-generation writers are fenced.** Generation/attempt identity alone is insufficient. Every mutable transition must also compare the exact expected predecessor campaign-state revision in the same SQLite transaction.
10. **Storage lifecycle cannot break replay.** Promoted P3 evidence required for current or restartable target-size state is protected by existing STOR ownership/reachability rules before any cleanup may reclaim it.

Any implementation that satisfies the CLI superficially while violating one of these invariants fails P4.

---

## 2. Frozen owner graph and implementation surfaces

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
       regime + generation/attempt + state revision
       adopted authenticated P3 head
       terminal selected-data projection
```

P4 adapters may call these owners and may add persistence-facing records around them. They may not reproduce their algorithms.

### 2.2 Mandatory implementation reconnaissance before edits

Before changing product code, the implementer must inspect the actual branch and identify, in implementation notes/tests, the real owners of all of the following:

- `prepare` parser and `command_prepare` call graph;
- `select-target-size` parser and `command_select_target_size` call graph;
- the concrete CampaignStore/SQLite class or functions and transaction helpers;
- existing current campaign generation/prepare receipt/state keys;
- current target-size selection/restart keys and terminal selected-size fields;
- P3 execution-root construction and resolver creation;
- storage accounting/reclamation/archive ownership surfaces;
- user-facing CLI help and campaign guide text describing `prepare`/target-size behavior.

The expected high-impact surfaces include `_campaign_cli_core.py`, `campaign_cli.py`, the actual campaign persistence owner discovered from the code, `storage_accounting.py`, `storage_reclamation.py`, `storage_archive.py`, `target_size_experiment.py`, and `target_size_execution/coordinator.py`. This list is a starting map, not permission to ignore a discovered owner elsewhere.

The implementation must remove or redirect real production call edges, not merely add a new facade beside the old runtime.

---

## 3. Pass P4-0 — mandatory narrow P3 execution-head crash-recovery repair

### 3.1 Demonstrated defect to repair

Current P3 boundary commit semantics are effectively:

```text
persist immutable batch
 -> derive reducer post-state
 -> persist immutable heads/<head-digest>.json
 -> atomically replace current_head.json
```

A crash after the immutable successor head is durable but before `current_head.json` advances leaves:

```text
current_head.json -> H_g
heads/ contains H_g and valid child H_g+1
```

The existing reconciliation path accepts a missing current pointer, but when a stale pointer exists it treats heads outside that pointer's ancestry as orphans. A valid crash-left child can therefore be rejected.

### 3.2 Required repair owner and algorithm

Modify the existing P3 reconciliation implementation in `mdstats/training_data/target_size_execution/coordinator.py`. Do **not** add a P4 replay routine.

The repaired `reconcile_target_size_screen_root(...)` or the smallest existing helper beneath it must implement these semantics:

1. Acquire the existing screen-commit serialization when reconciliation will mutate `current_head.json`. Reuse `.screen_commit.lock` or the same canonical lock owner used by `commit_target_size_boundary_batch`; do not introduce an independently ordered second head-commit lock.
2. Load `current_head.json`, if present, through the typed P3 owner and verify that an immutable `heads/<digest>.json` record with exactly the same authenticated content exists.
3. Load every immutable head through `TargetSizeExecutionResolver`/typed deserialization. Do not trust raw JSON fields without the existing digest/schema validation path.
4. Construct head ancestry using immutable `parent_head_digest` relations.
5. If a valid current pointer exists, treat that head as the currently published base and inspect immutable descendants from that base.
6. Recover only a **unique linear successor chain**:
   - zero children: no pointer repair is needed;
   - exactly one child: replay that child's referenced batch from the exact current replayed reducer state using the same scientific batch replay/validation logic already used by P3 reconciliation; require exact pre-state, batch, parent, and derived post-state agreement, then continue to that child's children;
   - more than one child from any accepted head: fail closed as a fork/conflicting scientific history.
7. An immutable head that is neither in the accepted ancestry nor in the unique validated successor chain is an orphan/fork and must cause fail-closed reconciliation. Do not silently choose the newest file or filesystem ordering.
8. Only after the complete successor chain has passed typed loading and deterministic scientific replay may reconciliation atomically replace `current_head.json` with the validated tip.
9. If `current_head.json` is absent, retain the existing unique-tip repair concept, but require the complete ancestry and scientific replay to validate before creating the pointer.
10. Preserve the existing unreferenced-complete-batch repair behavior. A batch left durable before its head may be replayed and committed only when it is the unique exact successor of the current reducer state.
11. Never accept serialized `post_state` merely because its digest parses. Re-derive the state through the frozen P2 reducer transition and compare it with the stored head.
12. Keep create-or-verify semantics, immutable historical records, and P3 owner proofs unchanged.

### 3.3 P4-0 mandatory tests

Add or extend focused P3 tests through the **real** P3 resolver/reconciler. If no existing test file cleanly owns these cases, use a focused file such as `tests/test_mlff_target_size_p3_head_recovery.py`.

Prove at minimum:

- crash after complete batch publication but before immutable head publication;
- crash after immutable successor head publication but before `current_head.json` replacement;
- missing `current_head.json` with one valid head chain;
- stale pointer followed by two or more valid linear successor heads;
- stale pointer with one corrupted successor head;
- stale pointer with two competing children from the same parent -> reject;
- unrelated/orphan immutable head -> reject;
- duplicate exact retry remains idempotent;
- fresh-process reconciliation after repair yields byte/identity-equivalent reducer state and selected scientific outcome to uninterrupted execution;
- existing success, TRAIN2-failure, EVAL2-failure, P3A7 restart-owner, and P3A8 reconciliation acceptance continue to pass.

### 3.4 P3 formal closure prerequisite

After P4-0 passes the complete affected P3 regression surface, formally record cumulative P3 revision-7 functional/semantic closure in the package metadata/README according to repository workplan conventions. Do not mark P4 runtime-cutover passes accepted while the package chain still says P3 is active/blocked.

**Gate P4-0:** P4-A and later executable cutover work are blocked until the repair and formal P3 closure are committed.

---

## 4. Campaign current-state model and transactional compare-and-set contract

### 4.1 One mutable state record/aggregate

Implement or reconcile one version-agnostic current target-size campaign-state aggregate in the real CampaignStore/SQLite owner. Exact table/column names are delegated, but the semantic state must bind, directly or through authenticated aggregate digests/references:

- schema version;
- cutover/regime state;
- runtime generation;
- execution attempt identity where an attempt is active;
- **campaign state revision / predecessor token**;
- lifecycle/stage state;
- P1 neutral/canonical/source authority identity;
- inherited protected/split-exclusion relation authority;
- P2 experiment definition/aggregate identity including hard-support authority;
- P3 screen/window identity and durable root locator owned by the campaign;
- currently adopted immutable P3 execution-head digest and reducer-state digest, when one exists;
- terminal-result projection when terminal;
- stop/failure classification and replay-manifest/reference identity when applicable.

Do not copy the full P1-P3 immutable graph into mutable SQLite rows. Store stable identities/references and revalidate them through their owning loaders.

### 4.2 Required CAS predicate for every mutation

Every mutable target-size campaign transition must execute in one real SQLite transaction and compare all of:

```text
expected regime/schema
expected runtime generation
expected execution attempt (if applicable)
expected predecessor campaign-state revision
```

The transition may commit only if all expected values still match the current row/state. The same transaction must advance the state revision and write the new state.

A state revision may be an authenticated digest or monotonic revision token owned by CampaignStore. It must uniquely distinguish predecessor state; process ID, timestamp, or worker-local memory alone is insufficient.

Required behavior:

- writer from generation `g` cannot mutate after `g+1` has taken ownership;
- writer from the same generation but stale predecessor revision cannot mutate after another transition committed;
- an exact duplicate retry of an already-committed logical transition is recognized as idempotent success only after the stored result is verified identical;
- two divergent transitions from the same predecessor cannot both commit;
- a crashed transition owner does not permanently lock the campaign: a new process may resume by reading the exact persisted transition identity/revision and performing the next valid CAS;
- process identity does not grant authority to rewrite historical evidence.

If the existing CampaignStore lacks a suitable transaction/CAS helper, add the smallest reusable store-level primitive. Do not implement compare-then-write as separate unlocked SQL operations in CLI code.

### 4.3 Same-generation race acceptance

Use two independent SQLite connections/process-equivalent clients against the same real campaign database:

1. both read the same generation/attempt/revision;
2. both attempt different next states;
3. exactly one commits;
4. the loser receives a typed stale/conflict result and does not overwrite the winner;
5. exact duplicate transition retry is idempotent and returns/verifies the existing state.

This acceptance is mandatory; generation-only fencing does not close P4.

---

## 5. Terminal result is an authenticated projection, not an independent decision

### 5.1 Terminal-success derivation

When P3 becomes terminal with a selected target size, the current runtime must perform this order:

```text
reconcile P3 screen through TargetSizeRestartAuthority
 -> obtain exact authenticated terminal execution head/post reducer state
 -> derive terminal selection through the P2 reducer/statistical owner
 -> derive exact T_selected through the accepted P2 training-order/T_N owner
 -> build terminal campaign projection
 -> CAS-commit head digest + reducer digest + selected N + exact T_selected identity together
```

Use existing P2 public/pure owners where they exist. If a small pure projection helper is missing, add it adjacent to `target_size_experiment.py` so it exposes already-frozen P2 semantics; do not encode target-size decision logic in P4 CLI/store code.

`N_selected`, `T_selected`, stop reason, and terminal status must be internally consistent with the authenticated terminal P2/P3 state.

### 5.2 Terminal load/restart validation

A completed selection may be exposed to P5/downstream code only after the loader:

1. resolves the referenced P1/P2 authorities;
2. reconciles/resolves the referenced P3 screen/head through P3;
3. verifies the reducer-state digest referenced by campaign state;
4. re-derives terminal `N_selected` from that reducer state;
5. re-derives exact `T_selected` membership/identity from P2;
6. compares both with the persisted terminal projection.

Any mismatch is corruption/stale state and fails closed. Updating only a local digest, `N_selected`, or `T_selected` field must never make a divergent terminal record valid.

### 5.3 Terminal scientific failure versus interruption

A reducer-terminal configured-ceiling nonconvergence or other frozen scientific terminal failure must persist as a **terminal scientific outcome** bound to exact P3/P2 provenance. It must not be treated as an operational interruption eligible to resume the same scientific screen indefinitely.

Conversely, process death, temporary resource failure, or an incomplete candidate/rung that has not produced a terminal P2/P3 outcome remains operationally resumable and must not be materialized as scientific nonconvergence.

Mandatory negative tests:

- mutate only persisted selected `N` -> reject;
- mutate only exact `T_selected` identity/membership -> reject;
- mutate adopted head/reducer reference while leaving selected fields intact -> reject;
- terminal success fresh-process reload re-derives the identical projection;
- terminal scientific failure reload remains terminal and cannot masquerade as resumable interruption.

---

## 6. Cross-store visibility and recovery protocol

SQLite and filesystem evidence cannot share one physical atomic transaction. P4 therefore requires **ordered visibility, authenticated adoption, CAS mutation, and idempotent recovery**.

### 6.1 Canonical transition order

For any target-size state advancement that depends on new P3 evidence:

```text
1. P3 produces attempt-local work.
2. P3 validates all scientific parents through accepted P1/P2/P3 owners.
3. P3 publishes immutable evidence using existing create-or-verify durability.
4. P3 commits/reconciles its immutable execution-head graph.
5. P4 invokes the real P3 reconciler and receives the exact authenticated current immutable head/post-state.
6. P4 opens a real CampaignStore transaction with regime + generation + attempt + predecessor-revision CAS.
7. P4 binds the exact P3 screen/head/reducer identities and next campaign lifecycle state.
8. P4 commits SQLite.
9. Any human-readable/external view is generated only as non-authoritative derived output.
10. Cleanup/retirement may run only after the new state is reloaded and authenticated.
```

A campaign row may never reference an incomplete/unvalidated P3 artifact. File existence alone is never completion evidence.

### 6.2 Required recovery matrix

Implement and test the following exact states:

| Crash/restart state | Required behavior |
|---|---|
| crash before P3 immutable publication | resume/recompute through P3 owner; campaign state unchanged |
| complete batch durable but head absent | P3 reconciler validates unique batch and commits head |
| immutable successor head durable but P3 pointer stale | P4-0 P3 reconciler replays unique successor chain and repairs pointer |
| P3 reconciled head is ahead of SQLite | if all scientific identity + campaign generation/attempt match, CAS-adopt the exact head; do not rerun completed work |
| SQLite references missing/corrupt P3 head | hard reject/corruption; never recreate authority from SQLite summary fields |
| SQLite references older head and P3 has one unique valid successor chain | reconcile P3 then CAS-adopt successor under same current generation; fork/conflict rejects |
| SQLite commit complete but derived result/view missing | rebuild derived view from SQLite + P3; do not roll back science |
| crash during legacy->current cutover | remain transition-owned; restart exact transition via CAS; normal current runtime blocked |
| stale generation writer resumes | typed stale/conflict; no mutation |
| two same-generation writers race | predecessor-revision CAS permits one divergent successor only |

Recovery must not delete authoritative, external, or potentially adoptable current-generation evidence merely to obtain a clean directory.

---

## 7. Destructive-generation cutover and legacy-state disposition

### 7.1 Durable regime transition

Use one campaign-level durable regime/cutover marker in the real SQLite owner. Exact enum names are delegated, but semantics must distinguish at least:

```text
legacy/unconverted
transitioning-to-current
current
```

Required transition:

1. CAS `legacy -> transitioning`, allocating/binding the new current runtime generation and exact predecessor state revision.
2. Inventory retired target-size derived state before mutating it.
3. Quarantine/reject retired derived authority. Do not translate it into P1/P2/P3 objects.
4. Reconstruct current P1/P2/P3 state from source inputs and only independently reusable lower-level caches through current validators.
5. Persist current campaign references/state through CAS transitions while the regime remains `transitioning`.
6. Validate that all required current authorities are resolvable and no retired target-size record is being used as current authority.
7. CAS `transitioning -> current` from the exact expected transition revision.
8. Only after `current` is durable may ordinary production target-size runtime proceed.

A fresh process must be able to resume an interrupted `transitioning` state by persisted transition identity/revision; it must not depend on the original PID surviving.

### 7.2 No mixed per-row runtime

The cutover is campaign/runtime-wide. Do not lazily migrate target-size rows such that some datasets execute the retired selector while others execute P1-P3. While `transitioning`, target-size commands either resume the transition or fail with actionable guidance; they do not execute a mixed regime.

### 7.3 Retired-state inventory

At minimum, current target-size authority must stop consuming/reject or quarantine:

- `target_size_study.py` selector state as current authority;
- prepare-time selected-N/selector outcomes;
- `TargetDataRoleFreeze` target-size authority;
- FEAS/MVIDX/MVSEL/REPAIR/MVSTATE/MVQUAL current-runtime selection records;
- compatibility-domain/label-domain target-size maps and `domain_prefix_digests`;
- per-domain prescribed target/evaluation materialization authority;
- complement/coarse EVAL2 target-size roles;
- pre-target CV/MLCV role/catalog dependencies;
- V5/current-generation target-size receipts/migration aliases;
- old selected-N records that cannot resolve the complete P1/P2/P3 authority chain;
- incompatible resumable checkpoints/continuations;
- orphaned incomplete attempts that cannot authenticate to a current generation.

Raw source files, manifests, precise provenance parsing, and lower-level content-addressed caches may be reused only where their current owner proves recipe/identity equivalence independent of retired target-size semantics.

P4 does not destructively delete historical scientific evidence merely because its runtime is retired. P6 owns broad topology deletion. P4 may remove/quarantine only mutable current-state records necessary to make the cutover unambiguous and recoverable.

---

## 8. Current invalidation matrix and failure disposition

The current loader/caller must classify mismatches rather than silently repairing them. The implementation must encode and test this minimum matrix:

| Changed/bad authority | Disposition |
|---|---|
| malformed schema, impossible digest, changed artifact bytes, typed-content mismatch | hard corruption reject |
| P1 source/canonical/neutral identity change | invalidate target-size descendants; start/rebuild fresh current generation |
| inherited protected/split-exclusion relation change | invalidate P2/P3/terminal target-size state; fresh generation |
| P2 target-size policy, hard-support obligation, target/eval powers, fidelity, metric, practical-equivalence policy | fresh generation |
| `U_size`, `P_train/M3`, `pi_train`, `pi_eval`, qualified candidate set/order change | fresh generation |
| ordered optimizer seed set change | fresh generation |
| common preparation/training recipe/optimizer policy/evaluation-model-state policy change | fresh generation |
| materialization/export/source/checkpoint/evaluation identity change | reject stale evidence and rebuild under fresh valid generation as scientifically appropriate |
| P3 screen/window/plan/boundary identity change | stale current state; fresh generation unless exact current owner proves same experiment |
| execution owner/generation mismatch | typed stale/conflict or corruption; never transfer old owner |
| required live/EMA/raw-checkpoint state missing or incompatible | fail through P3 checkpoint owner; no state downgrade |
| current schema/regime version mismatch | reject/quarantine; explicit destructive-generation transition |
| retired target-size schema/record | reject/quarantine; never reinterpret |
| CV-only fold count/seed/settings change | target-size identity/result preserved; invalidate CV descendants only |
| production-only final horizon/adaptive settings change | target-size identity/result preserved; invalidate production descendants only |

A mismatch may not preserve a terminal selected `N` unless current P1/P2/P3 owners independently re-derive the exact same current result under the same current scientific identity. Equality of the integer `N` alone is never equivalence proof.

---

## 9. P3 checkpoint/restart semantics P4 must preserve exactly

P4 may persist references to P3 checkpoint evidence but may not reinterpret it.

For TRAIN2 boundaries:

- raw MACE checkpoint bytes remain authenticated by their bound digest;
- when EMA is enabled, raw checkpoint model parameters represent the accepted MACE checkpoint-save EMA-shadow state;
- companion `live_parameters` represent authenticated continuation/live optimization state;
- authenticated EMA shadow remains the canonical evaluation state when the frozen optimizer policy requires EMA;
- without EMA, raw checkpoint/live state follows the accepted non-EMA contract;
- evaluation-state choice is derived from the canonical optimizer-policy owner, never editable persistence metadata;
- numerical checkpoint validity does not grant execution ownership;
- restart must preserve exact raw/live/EMA distinctions through the real P3 owner;
- missing/malformed/noncanonical state fails closed and may not silently fall back to another representation.

All P3A5/P3A6/P3A7 real-owner acceptance remains regression authority for P4.

---

## 10. STOR1-STOR5 lifecycle integration for promoted P3 evidence

P3 was previously isolated scaffolding; after P4 its evidence becomes production campaign state. The existing storage subsystem must therefore understand and protect its lifetimes.

### 10.1 Reuse existing storage owners

Integrate through existing `storage_accounting.py`, `storage_reclamation.py`, `storage_archive.py`, and their real CLI/ownership helpers. Do not create a target-size-specific deletion queue or bypass STOR containment/ownership checks.

### 10.2 Artifact families to classify/account

At minimum account the promoted P3 families actually present in the implementation:

- screen/window identity;
- immutable boundary batches and execution heads;
- logical progress/current-head recovery pointers;
- cell completions;
- candidate trajectories/materializations;
- planned rungs and continuation requests;
- boundary snapshots and their raw checkpoint/companion/runtime-summary bytes;
- EVAL2 roles and exact-M evaluation artifacts;
- predictions and metric records;
- raw TRAIN2/EVAL2 failure records and failure checkpoint bytes;
- current-generation attempt-local/staging files under campaign ownership.

### 10.3 Required retention classes

Storage planning must distinguish at least:

- **current/restart-required**: protected from deletion;
- **current terminal provenance**: retained unless an existing later STOR tier explicitly proves preserved capability;
- **active attempt**: protected;
- **crash-left but still adoptable/reconcilable current-generation evidence**: protected until reconciliation classifies it;
- **historical retained immutable evidence**: retained/auditable under existing policy;
- **provably unreachable campaign-owned temporary/orphan evidence**: reclamation eligible only through existing STOR ownership + reachability + capability checks;
- **external or ownership-ambiguous path**: never deletion-authorized merely because a P3 record references it.

Do not solve disk growth by deleting unknown heads/batches/checkpoints during restart. Reconciliation first establishes reachability/authority; reclamation runs afterward through STOR.

### 10.4 Storage acceptance

Prove through real storage owners that:

- `storage report` includes the promoted target-size artifact families/bytes;
- safe cleanup during an interrupted screen preserves everything required for fresh-process reconciliation and candidate continuation;
- safe cleanup after a crash does not delete an unreferenced-but-adoptable immutable head/batch before reconciliation;
- external references, symlink escapes, and ownership-ambiguous files remain protected;
- after a safe cleanup, fresh-process P3 reconciliation and campaign restart still succeed with identical scientific state;
- no new target-size retention logic weakens STOR1-STOR5 guarantees.

---

## 11. Atomic production orchestration switch

### 11.1 `prepare`

After cutover, the real `prepare` path may construct/load the P1 neutral substrate and deterministic prerequisites/common preparation that are scientifically independent of candidate `N`, but it must not:

- select `N`;
- execute the P2 paired-screen reducer;
- train target-size candidates;
- perform target-size EVAL2 ranking;
- construct pre-target CV plans;
- create compatibility-domain/per-domain target-size authority merely for legacy code.

Any prerequisite persisted by `prepare` must be version-agnostic and authenticated to current P1/current campaign regime.

### 11.2 `select-target-size`

The real `select-target-size` path must:

1. load/revalidate current P1 authority from campaign state;
2. construct/load the exact P2 experiment through `target_size_experiment` owners;
3. construct/load P3 common preparation/execution context/screen window;
4. reconcile any existing P3 root before scheduling new work;
5. derive the active P2 matrix from the authenticated reducer state;
6. execute only the required surviving `(N, optimizer_seed)` cells through P3 candidate/TRAIN2/EVAL2 owners;
7. publish outcomes through P3 completion/batch/head owners;
8. reconcile the resulting P3 head;
9. CAS-adopt the exact P3 head/reducer identity into campaign state;
10. repeat only while the P2 reducer is nonterminal;
11. on terminal success, derive and atomically persist the terminal projection from section 5;
12. on terminal scientific failure, persist the authenticated failure terminal state;
13. return/report from the current campaign projection only after reload/revalidation.

P4 must not create a local ranking loop that bypasses the P2 reducer or a local restart loop that bypasses P3 reconciliation.

### 11.3 Retired call-edge removal

In the same coherent cutover, remove production call edges from `prepare`/`select-target-size` to retired target-size role/domain/selector authorities. `target_size_study.py` and older modules may remain physically present until P6 only if unreachable from current target-size production entrypoints and not imported as current authority.

Preserve the guard that ordinary public `train`/`evaluate` commands cannot become a second target-size screening scheduler.

Forbidden implementation patterns:

- runtime old/new feature flag;
- try-current/fallback-retired;
- dual authoritative writes;
- old-schema alias interpreted as current;
- wrapper rebuilding retired label-domain maps internally;
- P4-local selector/reducer/replay engine;
- manual selected-N override path;
- using file existence or a worker PID as current-state proof.

---

## 12. Material implementation passes and acceptance gates

Execute these passes in order. Do not combine them into one opaque edit. After each behavior-changing pass, run the listed affected regression before proceeding. Continue through the sequence unless a genuine design/repository blocker is demonstrated.

### Pass P4-0 — P3 head-pointer recovery prerequisite

Implement section 3 exactly in the existing P3 reconciler.

**Primary owner:** `target_size_execution/coordinator.py` and its existing P3 tests.

**Must not touch:** P2 reducer science, TRAIN2/EVAL2 policy, provider inference semantics.

**Gate:** complete section 3.3 tests + affected P3 suite + formal P3 closure metadata.

### Pass P4-A — CampaignStore current-state schema and CAS primitive

1. Locate the real CampaignStore/SQLite owner.
2. Add/reconcile version-agnostic target-size regime/current-state records.
3. Add one transaction-level CAS operation checking regime + generation + attempt + predecessor revision.
4. Add typed stale/conflict/corruption outcomes as appropriate to existing error conventions.
5. Add terminal projection record fields/references but do not wire the public runtime yet.

**Gate:**

- schema/serialization round-trip;
- real SQLite close/reopen;
- transaction rollback leaves predecessor unchanged;
- older generation rejection;
- same-generation stale-revision rejection;
- same-predecessor divergent-writer race admits exactly one successor;
- exact duplicate retry idempotency;
- retired schema cannot deserialize/relabel as current;
- no `v7_`/`V7` new production key/symbol.

### Pass P4-B — Regime cutover/migration owner

1. Implement durable `legacy -> transitioning -> current` semantics in CampaignStore.
2. Implement exact transition CAS/restart behavior.
3. Inventory and quarantine/reject retired target-size derived state.
4. Permit only validator-proven reusable low-level inputs/caches.
5. Add actionable fail-closed guidance for incompatible old workspaces.
6. Keep public target-size orchestration on its coherent pre-switch state until P4-D; do not expose half-wired current runtime.

**Gate:**

- fresh current-generation campaign;
- legacy campaign enters transition once;
- crash during transition resumes from exact persisted transition revision;
- second process cannot start conflicting transition;
- no row-by-row mixed old/current target-size execution;
- old selected-N/selector records never become P2/P3 authority.

### Pass P4-C — Cross-store adoption, restart, and concurrency

1. Wire P3 reconciliation result into CampaignStore CAS adoption.
2. Implement the section 6 recovery matrix.
3. Ensure SQLite adopts authenticated immutable head/reducer identities, not `current_head.json` as campaign authority.
4. Ensure stale/generation races return typed conflicts without mutating P3 history.
5. Keep optional external views non-authoritative.

**Gate:** every section 6.2 crash case, with real SQLite and real P3 resolver/reconciler. In-memory stores or fake persistence cannot close this gate.

### Pass P4-D — Atomic `prepare` / `select-target-size` production switch

1. Rewrite the real orchestration edges according to section 11.
2. Use P1/P2/P3 owners directly.
3. Remove reachable old target-size call edges in the same coherent switch.
4. Preserve shared optimized execution/materialization/inference machinery where P3 already reuses it.
5. Preserve ordinary `train`/`evaluate` scheduler guards.

**Gate:**

- bounded real parser + CampaignStore + `prepare` integration proving no N selection;
- bounded real parser + CampaignStore + `select-target-size` integration reaching P1/P2/P3 owners;
- no old selector/domain/complement/CV authority in the current call graph;
- stage-local affected CLI regression.

Expensive training/prediction may be replaced below the accepted owner boundary only after real config parsing, authority construction, provider/state validation, materialization validation, and orchestration ownership have executed.

### Pass P4-E — Terminal projection, semantic restart, and invalidation

1. Implement section 5 terminal derivation/reload validation.
2. Wire every section 8 invalidation class through the real current loader/caller.
3. Preserve P3 raw/live/EMA semantics on restart.
4. Make terminal scientific failure distinct from operational interruption.

**Gate:**

- terminal success exact rederivation;
- selected-N-only/T-selected-only/head-only tamper negatives;
- protected-relation/hard-support change invalidation;
- seed/order/fidelity/metric/training-policy invalidation;
- EMA/live malformed restart rejection through real owner;
- CV-only and production-only changes do not invalidate target-size state;
- fresh-process mid-screen continuation and terminal replay.

### Pass P4-F — STOR integration, public documentation, and structural closure

1. Integrate P3 artifact families into STOR accounting/reachability/retention.
2. Run storage acceptance from section 10.4.
3. Update public CLI/help/documentation surfaces that describe the changed lifecycle, at minimum the actually affected parts of:
   - `docs/guides/mlff_campaign_cli_user_guide.md`;
   - parser/help text owned by `_campaign_cli_core.py`/current CLI parser;
   - `campaign.toml.example` if exposed configuration semantics changed;
   - current architecture/source-map documentation when needed to keep public/current documentation truthful.
4. Make documentation state clearly that `prepare` no longer performs target-size selection/training and that `select-target-size` owns the current P2/P3 screen.
5. Run structural searches/import checks proving retired target-size owners are unreachable.

**Gate:**

- storage report/safe-cleanup tests;
- docs/help tests/lint where available;
- no current docs claim the retired prepare/select lifecycle;
- no new version-prefixed product names;
- `target_size_study.py` and retired runtime modules are not reachable from current target-size CLI authority.

### Pass P4-G — Assembled affected-surface closure

Re-derive the affected surface from the complete P4 diff rather than reusing the planned file list blindly.

Run:

- all P4-0 P3 recovery regressions;
- complete affected P1/P2/P3 regression where the integration diff can affect their callers;
- complete affected campaign persistence/CLI regression;
- restart/invalidation matrix;
- concurrency/CAS matrix;
- STOR regression for touched ownership/reclamation paths;
- structural absence/uniqueness checks;
- bounded real-owner `prepare -> select-target-size -> terminal projection reload` integration;
- broader repository suite if affected-surface inspection cannot independently prove a smaller suite sufficient.

Do not run long GPU/real-production qualification as a P4 exit requirement.

---

## 13. Mandatory real-owner acceptance matrix

P4 is not accepted by unit-testing record constructors alone. The following scenarios must pass through the production owners named here.

### Persistence/concurrency

- real CampaignStore/SQLite reopen preserves current state;
- transaction rollback cannot expose partial state;
- generation `g` writer loses after `g+1` takeover;
- two writers in same generation from the same predecessor revision: one divergent successor only;
- exact same logical retry verifies/returns identical stored state;
- cutover transition is restartable by a new process without PID ownership.

### P3 crash/replay

- missing pointer;
- stale pointer with unique successor head;
- stale pointer with multi-head linear successor chain;
- forked successor heads reject;
- unreferenced complete batch adopts only after full replay;
- success/TRAIN2-failure/EVAL2-failure fresh-process replay;
- P3A7 canonical restart-owner rejection still passes;
- current campaign adopts only the reconciled immutable head digest.

### Scientific identity/invalidation

- P1 source/canonical identity mismatch;
- protected relation mismatch;
- P2 hard-support mismatch;
- split/order/candidate-set mismatch;
- optimizer seed mismatch/reorder;
- fidelity/evaluation-power mismatch;
- common preparation/training policy mismatch;
- evaluation-model-state/EMA mismatch;
- checkpoint/artifact byte corruption;
- schema/regime mismatch;
- CV-only and production-only changes remain target-size-neutral.

### Terminal projection

- terminal reducer -> exactly one selected `N` + exact `T_selected` projection;
- persisted selected-N mismatch rejects;
- persisted T-selected mismatch rejects;
- adopted head/reducer mismatch rejects;
- configured-ceiling nonconvergence remains a terminal scientific result;
- operational interruption remains resumable.

### Runtime cutover

- real `prepare` reaches current P1 path but cannot select `N`;
- real `select-target-size` reaches P2/P3 and no retired selector;
- no pre-target CV dependency;
- no complement/coarse EVAL2 target-size role;
- public ordinary `train`/`evaluate` cannot schedule the target-size screen;
- old current-runtime records fail closed with reset/reprepare guidance.

### Storage

- P3 bytes appear in storage accounting;
- active/restart-required evidence is protected;
- adoptable crash-left evidence survives safe cleanup until reconciliation;
- external/symlink/ambiguous ownership cannot acquire deletion authority;
- fresh-process replay after safe cleanup is identical.

Mocks/fakes may replace expensive numerical work only **below** the real semantic owner boundary. They may not replace CampaignStore, P3 resolver/reconciler, P1/P2 authority construction, state/provider authentication, or the CLI parser when the acceptance claim concerns those owners.

---

## 14. Failure taxonomy and required operational behavior

Use existing project exception/result conventions where possible, but preserve these semantic classes:

1. **Corruption/tampering** — bad digest/schema/bytes/typed graph. Hard reject; do not auto-recompute over evidence while claiming continuation.
2. **Scientific incompatibility/invalidation** — valid prior state belongs to different current scientific identity. Quarantine/retire current authority and start a justified fresh generation.
3. **Stale writer/revision conflict** — valid writer lost generation or predecessor CAS. Abort that mutation with typed conflict; do not rewrite history.
4. **Operational interruption** — incomplete current work without terminal scientific outcome. Resume through P3/current CampaignStore state.
5. **Terminal scientific failure/nonconvergence** — authenticated terminal reducer/scientific outcome. Persist terminal state; do not loop as interruption.
6. **Incomplete cutover** — regime is `transitioning`. Resume exact cutover or fail with actionable transition guidance; do not run mixed runtime.
7. **Legacy incompatible workspace** — old derived target-size authority. Reject with destructive reset/reprepare guidance; do not migrate/reinterpret.

Do not collapse these classes into a generic "missing cache, recompute everything" path.

---

## 15. Performance and implementation-economy constraints

P4 is an integration/cutover package, not permission to replace proven optimized machinery.

- Reuse existing optimized DATA8/TRAIN2/EVAL2/provider/inference/materialization paths already consumed by P3.
- Reuse P3 create-or-verify publication and resolver validation.
- Reuse CampaignStore transactions rather than adding a second database.
- Reuse STOR ownership/accounting/reclamation rather than adding target-size-specific cleanup.
- Avoid rehashing/copying large immutable artifacts merely to duplicate them into SQLite.
- Store references/digests and revalidate through owners.
- Do not introduce per-domain loops or pre-target CV work retired by the parent.
- Crash recovery should reuse durable completed evidence rather than rerun expensive training/evaluation.
- No P4 performance optimization may weaken provenance, restart exactness, CAS fencing, or scientific validation.

Bounded resource/performance checks are appropriate for accidentally repeated hashing/copying or obvious serialization regressions. Long machine-specific production benchmarking remains final-release work.

---

## 16. Structural closure checks

At P4 exit, automated AST/import/search inspection plus real call-path tests must establish:

- production `prepare` and `select-target-size` depend on accepted P1/P2/P3 owners;
- no second target-size split/reducer/trainer/evaluator/restart implementation exists in P4;
- `target_size_study.py` is unreachable from current target-size production entrypoints;
- old FEAS/MVIDX/MVSEL/REPAIR/MVSTATE/MVQUAL/domain/complement/CV-coupled target-size call edges are absent from current orchestration;
- current target-size state contains no compatibility-domain map or pre-target CV plan authority;
- SQLite is the only mutable campaign-current/terminal-result authority;
- P3 `current_head.json` is not read as sufficient campaign completion/selection authority;
- no new `v7_`/`V7` product code/symbol/schema/record key was introduced;
- no old-runtime state loader can authorize a current selected target size;
- storage cleanup cannot unlink required P3 current/restart evidence.

Physical removal of all retired files remains P6 unless a specific mutable state record must be removed in P4 to prevent ambiguous current authority.

---

## 17. P4 exit criteria

P4 is complete only when all of the following are true:

1. P4-0 repaired the demonstrated P3 stale-pointer/immutable-successor crash window through the existing P3 reconciler.
2. Cumulative P3 exit is formally recorded before P4 current-runtime cutover acceptance.
3. The real campaign store has one current target-size state authority with regime, generation/attempt, and predecessor-state CAS fencing.
4. Same-generation divergent writers cannot both commit.
5. P3 immutable evidence remains the sole scientific execution/replay authority; `current_head.json` is only a rebuildable local pointer.
6. Cross-store recovery adopts validated complete evidence and rejects forks/corruption without fabricating a physical cross-store transaction.
7. `N_selected` and exact `T_selected` are re-derived authenticated projections of terminal P2/P3 state, not independent decision fields.
8. Terminal scientific failure is distinct from operational interruption.
9. Legacy target-size derived state is rejected/quarantined without reinterpretation; no mixed old/current runtime exists.
10. Current `prepare` does not select `N`; current `select-target-size` uses P2/P3 and is the sole screening entrypoint.
11. Retired selector/domain/complement/pre-target-CV target-size call edges are unreachable from current runtime.
12. P3 raw/live/EMA checkpoint semantics and historical owner proof remain intact.
13. Promoted P3 evidence participates in existing STOR accounting/retention/reclamation with restart-required evidence protected.
14. Public CLI help/user documentation describes the actual new lifecycle.
15. New production naming remains version-agnostic.
16. Complete affected regression, integration, crash, concurrency, invalidation, storage, and structural acceptance passes.
17. No long GPU/real-production qualification was required for P4 closure.

Only after these conditions pass may P5 treat selected target-size state as frozen current authority.

---

## 18. Implementer execution discipline

The implementer must use the following working discipline for this package:

1. Start from the accepted branch state and verify `entry_p3_commit` is an ancestor.
2. Perform the mandatory implementation reconnaissance from section 2.2 before editing.
3. Implement P4-0 first and stop P4 cutover work if its real P3 acceptance cannot be closed without reopening frozen science.
4. Commit/checkpoint accepted P4-0 before P4-A.
5. Implement P4-A through P4-G in order; after every material pass run its gate before proceeding.
6. When a gate fails, diagnose the violated owner/invariant. Repair the smallest owning layer; do not bypass the test with a compatibility shim or test-only alternate path.
7. Preserve accepted P1-P3 semantics unless a real implementation contradiction meeting section 19 reopen criteria is demonstrated.
8. Prefer modifying existing owners over adding new modules when an existing owner naturally owns the behavior.
9. New persistence helpers must be exercised by production callers before their tests count as acceptance.
10. Keep all expensive numerical fakes below the real owner boundary defined in section 13.
11. Re-derive the final affected test surface from the actual diff before closure.
12. Report separately at completion:
    - P4-0 P3 prerequisite repair evidence;
    - stage-local gate results;
    - final affected regression/integration results;
    - deferred long GPU/real-production qualification.

Do not stop merely because old tests encode retired architecture. Update/remove those expectations only when the frozen parent proves they are obsolete. Stop/reopen only for a genuine material blocker.

---

## 19. Frozen decisions, delegated details, and reopen conditions

### Frozen by this package/parent

- P1/P2/P3 scientific semantics and ownership boundaries;
- one current campaign mutable authority;
- P3 immutable scientific evidence/replay authority;
- P3 `current_head.json` is non-authoritative outside P3 recovery/localization;
- generation **and predecessor-revision** transactional CAS;
- selected-N/T-selected derivation from terminal authenticated state;
- one destructive-generation cutover with no mixed runtime;
- no retired-state reinterpretation;
- storage lifecycle protection for current/restart evidence;
- version-agnostic production naming;
- long GPU qualification deferred.

### Delegated implementation details

The implementer may choose, consistent with repository conventions:

- exact SQLite table/column names;
- exact semantic schema names and integer/string representation;
- whether campaign state revision is a monotonic integer, authenticated digest, or equivalent store-owned CAS token;
- exact transaction helper names;
- exact regime enum spellings;
- whether a human-readable terminal result view is stored only in SQLite or mirrored to a non-authoritative filesystem view;
- exact test filenames when extending an existing better-owned test module;
- small adapter refactors at CLI/store boundaries required to consume P1/P2/P3 owners.

Delegation does not permit weakening any invariant or acceptance case above.

### Reopen only on material evidence

Reopen design only if implementation proves one of the following:

- the real CampaignStore cannot provide transactional generation + predecessor-state CAS without a material persistence-architecture replacement;
- the P3 immutable execution graph cannot be referenced/revalidated durably from campaign state without changing frozen P3 scientific semantics;
- the P4-0 head-recovery defect cannot be repaired within existing P3 ancestry/replay semantics;
- a frozen parent requirement is internally contradictory with the accepted P1-P3 implementation;
- current STOR ownership semantics make it impossible to protect required P3 evidence without a material storage-architecture change.

Legacy tests, old workspace compatibility, convenience of reusing retired selected-N state, or desire to avoid updating public documentation are **not** reopen conditions.
