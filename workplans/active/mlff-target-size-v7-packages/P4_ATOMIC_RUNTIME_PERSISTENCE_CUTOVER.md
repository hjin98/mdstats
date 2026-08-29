---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: active
package_revision: 2
amended_date: 2026-08-29
entry_p3_commit: 472276ee521eb2b19177299c1c9ad660dbd6ad46
compatibility_policy: destructive-generation-reset
---

# P4 — Atomic runtime and persistence cutover

## 0. Authority and disposition

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P4 does **not** reopen P1-P3 science, statistics, execution semantics, checkpoint semantics, provider ownership, reducer policy, or target-size decision logic.

P4 is the one coherent **promotion and campaign-state integration** package over the accepted current-generation owner chain. It makes the P1-P3 architecture the only reachable production target-size runtime, binds its immutable evidence safely into the mutable campaign runtime, makes persistence/restart crash-recoverable and generation-fenced, and retires the old resumable target-size regime without constructing another state machine.

P4 inherits the complete accepted P1/P2/P3 history, including all cumulative P3 revision-7 amendments through the P3A7 restart-owner acceptance repair and the implementation state at `472276ee521eb2b19177299c1c9ad660dbd6ad46` (`P3A8`). Those amendments are implementation authority for P4 preservation even when their exact mechanics are not repeated here.

All new production code, symbols, schemas, record names and persisted authority names introduced by P4 must remain **version-agnostic**. `V7` remains only historical workplan/generation metadata. Persisted schemas use semantic names plus explicit schema/generation versions rather than `v7_*` product names.

---

## 1. Objective and protected concerns

Required product outcome:

> After P4, ordinary `prepare` and `select-target-size` use exactly one current target-size architecture and one mutable campaign state authority. The accepted P1-P3 scientific/evidence graph is the only scientific authority for target-size work; restart is deterministic and authenticated; crashes or concurrent stale writers cannot make partial or old-generation state appear current; and legacy derived target-size state cannot be silently reused, translated, or reinterpreted.

Protected concerns:

- P1 remains compatibility-neutral: precise provenance is evidence, not a target-size partition axis.
- P2 remains the sole statistical owner of `U_size`, inherited split-exclusion/protected relations, hard-support obligations, `P_train/M3`, `pi_train`, `pi_eval`, qualified `T_N`, `M1/M2/M3`, optimizer-seed namespace and pure reducer semantics.
- P3 remains the sole execution/evidence owner for common preparation, candidate realization, TRAIN2/EVAL2 execution, exact boundary state, exact-M evaluation, raw success/failure evidence, immutable publication, owner proof, reconciliation and restart replay.
- P4 must not create a second split builder, selector/reducer, training scheduler, checkpoint interpreter, evaluation engine, immutable evidence graph, or restart algorithm.
- One mutable campaign/orchestration authority must exist after cutover. Immutable P1-P3 artifacts are scientific evidence referenced by that authority, not a second mutable campaign FSM.
- Current target-size execution cannot fall back to or dual-write the retired target-size regime.
- A crash may leave an unreferenced valid immutable artifact, but may not leave a partially published artifact or stale campaign mutation that is accepted as current.
- Historical scientific ownership is immutable. A later process may own a new execution attempt; it may not rewrite the execution owner of already-produced historical evidence.
- Full long GPU/real-production qualification remains deferred to the established final-release phase. P4 acceptance is bounded functional/regression/integration acceptance through the real persistence/orchestration owners.

---

## 2. Engineering envelope and frozen owner graph

### 2.1 Promoted scientific/execution chain

The production dependency direction after cutover is frozen as:

```text
verified current source/config inputs
  -> P1 neutral_substrate owners
       SourceAuthority / CanonicalFrameAuthority / NeutralStatisticalBase
  -> P2 target_size_experiment statistical owners
       resolved target-size policy
       inherited split-exclusion/protected relation authority
       hard-support obligation authority
       U_size -> P_train/M3 -> pi_train/pi_eval -> qualified T_N/M_i
  -> P3 target_size_execution owners
       common preparation + execution context
       candidate/materialization/TRAIN2/EVAL2
       immutable evidence + owner proof + restart/reconciliation
  -> P4 campaign orchestration/persistence integration
       current prepare/select-target-size entrypoints
       mutable campaign generation/FSM references
       terminal selected-N/T_selected authority
```

P4 may refactor adapters at the current CLI/store boundary, but it must consume these accepted semantic owners rather than reproduce their algorithms.

### 2.2 Mutable state versus immutable evidence

P4 must preserve one explicit state split:

- **Mutable campaign state**: current orchestration generation, command/stage status, expected execution generation/attempt, references to accepted immutable artifacts, terminal selected target-size state, and operational resume bookkeeping. This is owned by the real campaign persistence layer (`CampaignStore`/SQLite unless implementation evidence requires the smallest owning-layer replacement).
- **Immutable scientific evidence**: P1/P2/P3 content-addressed authorities, materializations, boundary snapshots, prediction/evaluation evidence, completion/failure records, owner proofs and replay graph. Existing P3 create-or-verify and typed resolver/reconciliation owners remain authoritative.

Do not copy full immutable evidence into mutable rows merely for convenience. Persist stable identity/reference fields sufficient to authenticate and resolve the accepted graph. Do not let filesystem file existence become campaign completion authority.

### 2.3 Persistent identity that current campaign state must bind

The promoted current state must bind enough identity to reject stale/replayed/rehashed descendants. At minimum, directly or through one authenticated aggregate identity/reference, current target-size state must bind:

- accepted P1 source/canonical/neutral-substrate identity;
- complete inherited P1 split-exclusion/protected-relation authority;
- resolved target-size policy including hard-support obligations;
- exact `U_size`, `P_train/M3`, `pi_train`, `pi_eval`, qualified candidate-size set and derived exact `T_N`/`M_i` memberships;
- ordered optimizer-seed set;
- common preparation and target-size training/execution-context identity;
- training recipe/optimizer policy and canonical evaluation-model-state authority;
- P3 screen/plan/boundary identities and execution generation/attempt where applicable;
- exact materialization/checkpoint/evaluation artifact identities required by P3 replay;
- immutable execution-owner proof and content-addressed artifact digest/length/reference where applicable;
- terminal reducer state, selected `N`, exact `T_selected`, stop/failure reason and replay-manifest identity.

Derived digests are acceptable only when the real loaders revalidate their semantic parents. Updating local digest references without re-deriving the accepted P1-P3 parent graph must not make stale state valid.

---

## 3. Persistence, crash consistency and concurrency contract

### 3.1 Cross-store publication protocol

SQLite and filesystem publication cannot be one physical atomic transaction. P4 therefore freezes **atomic visibility plus idempotent recovery**, not a fictitious cross-device transaction.

For any campaign transition that references new P3 evidence, the required ordering is:

```text
1. produce attempt-local temporary evidence
2. validate through the owning P1/P2/P3 semantic owner
3. publish immutable evidence with P3 crash-safe create-or-verify semantics
4. fsync/finish durability according to the existing P3 publication contract
5. enter the real CampaignStore transaction under expected generation/attempt fencing
6. bind exact immutable identity/reference + new mutable stage/FSM state
7. commit SQLite transaction
8. publish/update any terminal current-result pointer/manifest only through its canonical owner
9. reconcile and retire only state proven obsolete and owned by this generation
```

A database row may not reference an incomplete/unvalidated artifact. A complete immutable artifact published before a crash may remain unreferenced; restart must detect and safely reuse/reconcile it when it is the exact expected evidence rather than recompute it merely because the DB commit did not occur.

### 3.2 Generation and stale-writer fencing

Introduce or reuse one campaign-level monotonically distinguishable **runtime generation / execution attempt authority**. Every mutable target-size mutation must validate the expected current generation/attempt in the same store transaction that performs the mutation.

Required behavior:

- a writer from generation/attempt `g` cannot mutate state after `g+1` has taken ownership;
- duplicate identical retries within the same logical mutation are idempotent;
- conflicting duplicate publication or conflicting campaign mutation fails closed;
- process death does not transfer historical scientific ownership of already-published P3 evidence;
- a new attempt receives a new operational owner/generation rather than rewriting an old attempt's owner proof.

P3 stage-local file locks/CAS remain in force. Campaign generation fencing is additional protection for mutable orchestration state and must not replace P3 immutable publication validation.

### 3.3 Crash/recovery states

P4 must explicitly handle and test at least these interruption points:

1. before immutable artifact publication;
2. after immutable artifact publication but before SQLite reference commit;
3. after SQLite commit but before terminal current-result/manifest publication;
4. after terminal publication but before obsolete-state cleanup;
5. during destructive-generation cutover/quarantine;
6. during competing restart/resume attempts;
7. during a stale writer attempting to commit after a newer generation exists.

Recovery must classify state as complete/current, reusable-unreferenced immutable evidence, incomplete attempt-local state, stale generation, incompatible scientific state, or corrupt state. File existence, process disappearance and progress counters are never sufficient completion evidence.

---

## 4. Compatibility, cutover and invalidation policy

### 4.1 One-time destructive-generation cutover

P4 performs one explicit transition from the retired current target-size generation to the promoted regime. Implement one durable cutover/schema-regime marker owned by the real campaign store or equivalent canonical persistence owner.

Startup must distinguish enough cutover state to fail safely, for example:

```text
legacy/unconverted -> transition-owned -> current
```

Exact enum/schema mechanics are delegated. The semantics are frozen:

- normal current execution may not run while the store is ambiguously half-transitioned;
- transition ownership is exclusive;
- transition is restartable/idempotent;
- no lazy per-row mode is allowed where some datasets execute the old selector while others execute the promoted selector;
- old derived target-size state is not translated into current scientific objects;
- raw scientific inputs and independently valid lower-level caches may be reused only through their current owning validators.

### 4.2 Legacy state disposition

Inventory old target-size state surfaces before changing them. Classify each as reject/quarantine, safely reusable low-level input/cache, historical evidence retained for audit, or explicitly obsolete runtime state scheduled for P6 deletion.

At minimum, current execution must reject/quarantine rather than reinterpret:

- old `target_size_study.py` selector state used as current authority;
- prepare-time selected-N/selector outcomes;
- target-size records lacking the current P1/P2/P3 semantic authority chain;
- compatibility-domain/label-domain target-size maps and domain prefix authorities;
- old FEAS/MVIDX/MVSEL/REPAIR/MVQUAL current-runtime lineage;
- complement/coarse evaluation roles retired by the parent;
- incompatible resumable checkpoint/continuation records;
- orphaned incomplete attempts that cannot be authenticated to a current generation.

Do not delete independently valid historical scientific evidence merely because its runtime is obsolete. Destructive deletion remains P6 unless P4 must remove a specific mutable current-state record to make the atomic cutover safe and recoverable.

### 4.3 Current invalidation matrix

The current restart loader/caller must fail closed or start a justified fresh generation when a material authority changes. The matrix must cover at least:

- P1 neutral/canonical/source identity;
- inherited split-exclusion/protected-relation authority;
- target-size policy or hard-support obligations;
- `U_size`, split, training/evaluation order or candidate qualification;
- target/evaluation power or fidelity schedule;
- optimizer seed set;
- common preparation, training recipe, optimizer policy or evaluation-model-state policy;
- materialization/source/export/evaluation artifact identity;
- P3 screen/plan/boundary identity;
- execution generation/owner mismatch;
- checkpoint schema/state/compatibility identity, including required live/EMA evidence;
- target-size metric/reducer policy;
- schema/generation version;
- artifact digest/byte corruption.

For each mismatch, define one of: **hard reject/corruption**, **quarantine + fresh recomputation**, or **safe fresh generation**. Silent repair that preserves an old terminal `N_selected` is forbidden.

CV-only fold/seed settings and production-only final-training horizons/settings remain excluded from target-size identity unless repository evidence shows an actually shared frozen scientific input was misclassified.

---

## 5. P3 checkpoint/restart semantics that P4 must preserve

P4 may persist references to P3 checkpoint state but may not reinterpret it.

For TRAIN2 boundaries:

- the raw MACE checkpoint bytes remain authenticated by their bound digest;
- with EMA enabled, raw checkpoint model parameters represent MACE checkpoint-save EMA-shadow state;
- companion `live_parameters` remain the authenticated continuation/live optimization state;
- authenticated EMA shadow remains the canonical evaluation state when the frozen optimizer policy requires EMA;
- without EMA, raw checkpoint/live state follows the accepted non-EMA contract;
- evaluation-model-state choice remains derived from the canonical optimizer policy owner, not editable persistence metadata;
- numerical checkpoint validity does not grant or transfer execution ownership.

Migration/restart must preserve exact live/EMA/raw-checkpoint distinctions and P3's real-owner validation. Missing, malformed, incompatible or noncanonical checkpoint state fails through the accepted typed owner; it must not silently downgrade to another state representation.

---

## 6. Implementation obligations and material stages

### Pass P4-A — freeze promoted persistence and cutover schema

Implement/reconcile the current campaign persistence generation around the owner split in sections 2-5.

Required end state:

- semantic/version-agnostic current record names and explicit schema/generation versioning;
- one mutable campaign target-size FSM authority;
- immutable P1-P3 evidence referenced rather than duplicated as mutable authority;
- current rows bind sufficient parent identity for semantic restart authentication;
- explicit cutover marker/state and generation/attempt fencing exist;
- old-generation state cannot deserialize/relabel itself as current.

Acceptance:

1. schema/serialization/digest round-trip;
2. real `CampaignStore` SQLite reopen/transaction tests;
3. current-generation compare-and-set/generation-fence tests;
4. old-generation/stale-schema negative loads;
5. structural record-key/name inspection proving no new `v7_*` production surface and no retired domain/CV/complement authority in current target-size records.

### Pass P4-B — atomic production orchestration switch

Switch ordinary production orchestration in one coherent change:

```text
real config/parser
 -> P1 neutral substrate
 -> P2 statistical experiment
 -> P3 common preparation/execution/restart owners
 -> P4 campaign state transition
 -> selected N / exact T_selected current authority
```

`prepare` may build/load the neutral substrate and common prerequisite state but must not select `N`. `select-target-size` owns entry into the accepted P2/P3 candidate-screen path and terminal selection persistence.

Remove current call edges to retired target-size role/domain authorities, public FEAS/MVIDX/MVSEL/REPAIR/MVQUAL plans, per-domain target-size materialization resolution, complement/coarse EVAL2 roles and legacy candidate/receipt keys. `target_size_study.py` may remain only as unreachable historical code scheduled for P6 deletion.

Preserve the guard that ordinary public `train`/`evaluate` commands cannot become a second screening scheduler.

Forbidden:

- old/current runtime feature flag;
- try-new/fallback-old;
- dual authoritative writes;
- wrappers that reconstruct old label-domain maps internally;
- aliases that reinterpret old schemas as current;
- a P4-local selector/reducer/execution/restart engine.

Acceptance:

1. focused orchestration/config tests;
2. structural source/import/call-edge absence checks;
3. bounded real CLI `prepare -> select-target-size` integration through the real parser, store and promoted P1/P2/P3 owners;
4. stage-local affected CLI/orchestration regression.

### Pass P4-C — cross-store crash recovery and concurrency

Implement the cross-store visibility/recovery protocol and stale-writer fencing from section 3.

Acceptance must include:

- interruption injection at every listed crash boundary;
- restart after unreferenced but complete immutable evidence;
- conflicting versus identical duplicate publication;
- two competing campaign writers for the same logical target-size transition;
- stale generation commit rejection after a newer generation takes ownership;
- restart cleanup that does not delete authoritative/external or valid immutable evidence;
- deterministic post-recovery reducer/selected-N result equivalence.

Use the real campaign store and P3 persistence/resolver/reconciliation owners. In-memory/custom persistence cannot close these claims.

### Pass P4-D — semantic restart and invalidation closure

Promote the complete P1-P3 authority graph into current restart/invalidation.

Required behavior:

- same current scientific inputs/config reproduce the same neutral/statistical/execution identities and selected data;
- every material mismatch from section 4.3 is detected through the real current loader/caller;
- P2 protected-relation and hard-support changes invalidate stale descendants;
- P3 checkpoint live/EMA/raw-state and execution-owner authentication survives current campaign reopen;
- durable P3 success, TRAIN2 failure and EVAL2 failure evidence remains resolvable/replayable through a fresh process without trusting serialized terminal outcomes as reducer input;
- CV-only and final-production-only settings remain isolated from target-size identity.

Acceptance:

1. disk-backed fresh-process restart/reopen;
2. one-change-at-a-time invalidation matrix;
3. protected-relation and hard-support mutation negatives;
4. live/EMA/checkpoint-state restart negatives and canonical positives;
5. owner/generation mismatch negatives;
6. corruption/truncation/schema mismatch negatives;
7. real-loader/caller execution rather than direct helper-only proxy tests.

### Pass P4-E — cutover/legacy structural closure

Prove after the switch:

- only the promoted current generation is reachable from ordinary target-size commands;
- only one mutable target-size campaign FSM can authorize current state;
- `target_size_study.py` and retired domain/role/resolver machinery cannot authorize a current result;
- current target-size schemas contain no label-domain maps, CV plans, complement roles or retired multi-authority lineage;
- public exports do not present retired target-size plans as current authority;
- there is no second split/reducer/trainer/evaluator/restart implementation introduced by P4;
- historical old code/evidence remains only where intentionally unreachable and scheduled for P6 disposition.

Use structural/negative evidence where runtime tests cannot establish absence/uniqueness.

### Pass P4-F — assembled package closure

Run fresh final affected-surface regression after all P4 executable edits and re-derive the affected surface from the assembled candidate.

Required real-owner integration:

```text
real config parser
 -> real CampaignStore/SQLite cutover + generation fence
 -> current prepare
 -> current select-target-size
 -> accepted P1 neutral owners
 -> accepted P2 statistical owners
 -> accepted P3 materialization/TRAIN2/EVAL2/restart owners
 -> immutable evidence publication
 -> selected N/T_selected campaign commit
 -> fresh-process restart/reopen authentication + replay
```

Expensive MACE training/prediction may use bounded scientific fixtures or fakes **below** the accepted P3 numerical-forward/training dependency boundary, but the current CLI, campaign store, cutover state machine, generation fence, P1/P2/P3 semantic validators, P3 persistence/resolver/reconciliation and current orchestration transitions under acceptance may not be mocked, reimplemented or bypassed.

Include focused and affected regression for campaign persistence, current CLI orchestration, P1/P2/P3 promoted interfaces, restart/recovery, checkpoint-state validation and legacy rejection. Run the broader repository suite if the final affected surface cannot be confidently bounded.

Production qualification: **deferred**. Do not run long production-scale GPU qualification in P4; preserve reproducible commands/conditions for the established final-release qualification phase.

---

## 7. Failure taxonomy and operator behavior

Current restart/cutover code must distinguish at least:

- **scientific/configuration incompatibility** — stale authority; reject reuse and require fresh current generation;
- **corruption/tampering/schema failure** — fail closed; do not retry as transient;
- **stale generation/owner conflict** — reject stale writer/resume attempt without mutating newer state;
- **ordinary operational interruption** — idempotently resume/reconcile from exact current durable evidence;
- **incomplete cutover** — block normal target-size execution until the transition owner resumes/completes or an explicit safe reset is performed.

Actionable diagnostics should identify the failed authority/category and safe operator action. Diagnostics must not become a second state authority.

---

## 8. Implementation authority

### Frozen

- Parent V7 scientific/architectural verdict and destructive-generation-reset policy.
- P1-P3 scientific/statistical/execution/checkpoint/restart/owner semantics, including all cumulative revision-7 repairs.
- One promoted current runtime and one mutable campaign target-size FSM after P4.
- P1-P3 immutable evidence remains the scientific authority; P4 integrates references and campaign transitions rather than duplicating it.
- Cross-store atomic visibility is achieved by validated immutable-first publication, fenced campaign commit and deterministic reconciliation/recovery.
- Generation/attempt fencing prevents stale mutable writers.
- Historical execution-owner evidence is immutable.
- No old/current feature flag, fallback, dual write or schema reinterpretation.
- New product names/schemas are version-agnostic.
- Real-owner acceptance boundaries in Passes P4-C/D/F.

### Delegated

- Exact semantic schema names, table/column layout and migration helper names.
- Exact generation token representation so long as stale-writer fencing is transactional and deterministic.
- Whether terminal current-result metadata is stored wholly in SQLite or as a small canonical filesystem manifest referenced by SQLite, provided the frozen visibility/recovery ordering and single mutable authority remain intact.
- Exact cutover marker enum and internal transaction decomposition.
- Refactoring of CLI/store adapters needed to consume P1/P2/P3 owners without changing their accepted semantics.

### Reopen only on evidence

Reopen only the affected P4 design surface if implementation evidence proves one of these assumptions false:

- the real campaign store cannot provide transactional compare-and-set/generation fencing without replacement;
- existing P3 immutable publication/resolver semantics cannot support deterministic cross-store reconciliation;
- an accepted P1/P2/P3 owner lacks information required to authenticate the current campaign reference without inventing a second authority;
- a filesystem/platform durability limitation makes the accepted immutable publication contract materially unsafe on supported deployment filesystems.

Do **not** reopen target-size science, P2 reducer policy, P3 checkpoint semantics or provider/execution architecture merely because another persistence layout is possible.

---

## 9. Exit gate

P4 is accepted only when:

> The accepted P1-P3 authority chain is the sole reachable production target-size architecture; one generation-fenced campaign state machine references the immutable authenticated scientific/evidence graph; cross-store crashes and retries recover deterministically without stale or partial state becoming current; old derived target-size state fails closed rather than being reinterpreted; and no supported runtime path can mix, fall back to, or authorize results through the retired architecture.

Before P5, commit the accepted P4 checkpoint and preserve the package-local test/review evidence needed to establish the real-owner cutover, restart and structural-absence claims. Do not begin P5 while any mixed-generation current path, unfenced mutable writer, ambiguous cutover state or unclosed P4 acceptance claim remains.
