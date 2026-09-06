---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-PARTIAL-BOUNDARY-RESUME-BUGFIX
protocol_version: 5.8.0
status: active
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
---

# MLFF target-size partial-boundary resume bug-fix workplan

## 1. Objective / problem invariants / non-goals

### 1.1 Observed failure

A production `select-target-size` restart enters Boundary 1 and executes an active `(N, optimizer_seed)` cell through TRAIN2 and EVAL2. Publication then fails with:

`TrainingDataInputError: Conflicting immutable progress record already exists for this logical cell.`

The observed run completed training, checkpoint promotion, model evaluation, and metric generation for `(N=128, seed=1)` before discovering that durable progress for the same logical cell already existed.

The failure is therefore not caused by MACE training, EVAL2 calculation, P2 ranking, target-size policy, or the immutable publication guard. It is caused by the production screen scheduler failing to consume existing authenticated partial-boundary progress before deciding what work remains.

### 1.2 Original product problem

`select-target-size` is a durable, restartable scientific screen. An interrupted screen may have completed some `(N, seed)` cells without having completed the exact active boundary matrix or committed a reducer transition.

On restart, the product must:

1. recover and authenticate previously completed cells belonging to the exact current screen and boundary;
2. leave P2 at the unchanged pre-boundary reducer state until the complete exact matrix exists;
3. execute only genuinely missing active cells;
4. combine recovered and newly completed cells in exact P2-required order;
5. commit the boundary exactly once;
6. never overwrite or silently reinterpret conflicting scientific evidence.

A restart must not discard valid expensive completed work merely because the boundary was not yet complete.

### 1.3 Tier-1 product invariants

The repair must preserve:

- P2 remains the sole ranking, survivor, practical-equivalence, and selected-size authority.
- The active boundary and exact active `(N, optimizer_seed)` matrix come only from authenticated P2 reducer state.
- Partial completion never advances the reducer.
- Exactly one complete ordered matrix is supplied to the P2 reducer.
- One logical `(screen window, boundary, N, optimizer seed)` cell has at most one accepted immutable progress result.
- Identical retry is idempotent.
- A genuinely different second result for the same logical cell remains a hard conflict.
- Previously persisted scientific evidence is reused only after authentication against current accepted P1/P2/P3 authority.
- Missing, stale, foreign, corrupt, tampered, or inconsistent durable progress fails closed when it purports to be accepted progress.
- Ordinary missing work remains executable work rather than corruption.
- Existing exact `n1 -> n2 -> n3` continuation semantics remain unchanged.
- Existing MACE/TRAIN2/EVAL2 scientific behavior, fidelity boundaries, seed set, target memberships, evaluation memberships, metric definition, and ranking semantics remain unchanged.
- No production-scale GPU qualification is introduced into implementation acceptance.

### 1.4 Non-goals

This repair must not:

- change target-size scientific policy;
- change fidelity epochs;
- change candidate or evaluation memberships;
- change seed aggregation or ranking;
- change MACE architecture or training mathematics;
- change the immutable progress key;
- allow multiple accepted progress records for one logical cell;
- delete existing progress merely to permit recomputation;
- overwrite conflicting progress;
- downgrade a conflict to a warning;
- introduce a second restart database, completion registry, resume manifest, or parallel scientific authority;
- force regeneration of valid current-screen partial results;
- introduce a persistence schema migration unless implementation evidence proves the present schemas cannot represent the required recovery semantics.

---

# 2. Diagnosis and ownership

## 2.1 Correct existing behavior: immutable logical-cell publication

The existing progress slot is keyed by:

- screen-window digest;
- boundary epoch;
- target size;
- optimizer seed.

Publication verifies any existing record before writing a new completion/progress pair.

If an existing progress record has the same content identity, exact retry is idempotent. If it has a different identity, publication rejects the new result.

**This behavior is correct and must remain.**

The error message in the reported run is therefore functioning as an integrity guard.

## 2.2 Defective behavior: production scheduler ignores partial progress

Current production orchestration effectively performs:

```text
reconcile committed screen head
 -> derive active boundary and keys
 -> for every active key:
      execute candidate cell
 -> build complete batch
 -> commit
```

When there is no committed head for the current boundary, the reducer correctly remains at its pre-boundary state. However, durable per-cell progress from that partially executed boundary is not incorporated into scheduling.

Consequently:

```text
interrupted run
 -> cell A successfully published
 -> boundary incomplete
 -> no new reducer head

restart
 -> P2 still says whole boundary is active
 -> runtime executes cell A again
 -> new scientific execution reaches publication
 -> immutable progress slot already contains prior A
 -> conflict
```

The scheduler is therefore confusing:

```text
active according to P2
```

with:

```text
not yet durably completed at the execution layer
```

Those are not equivalent during an incomplete boundary.

## 2.3 Existing recovery machinery that should be reused

The implementation already contains the needed building blocks:

- deterministic per-cell progress paths;
- typed progress loading;
- immutable completion records;
- exact completion-record references;
- content-addressed parent artifacts;
- complete-boundary collection/building;
- scientific replay validation;
- `_reverify_published_parent_graph()` or equivalent current owner;
- committed-head reconciliation;
- previous-rung candidate continuation resolution.

The repair is therefore principally an **orchestration/recovery integration correction**, not a new persistence architecture.

---

# 3. Frozen high-level architecture and engineering envelope

The following high-level decisions remain Frozen for this implementation cycle.

## 3.1 P2 scientific ownership remains unchanged

P2 owns:

- active candidate sizes;
- optimizer-seed population/order;
- active boundary;
- evaluation rung;
- exact matrix shape/order;
- reducer transition;
- survivor/ranking decisions;
- terminal selected-size state.

P3/P4 must not create an alternate concept of scientific completion.

## 3.2 P3 remains the durable execution/restart owner

The existing P3 execution root remains the owner of:

- per-cell progress;
- immutable completion records;
- candidate and materialization evidence;
- TRAIN2 boundary/snapshot evidence;
- EVAL2 evidence;
- complete boundary batches;
- execution heads and replay ancestry.

Campaign runtime consumes those owners; it does not duplicate their state in a second resume mechanism.

## 3.3 Immutable cell progress remains immutable

The one-progress-slot-per-logical-cell design remains Frozen.

A restart must adapt scheduling around already accepted immutable progress; it must not mutate durable truth to make scheduling easier.

## 3.4 Complete-boundary reducer commit remains atomic

Recovered partial progress has no independent reducer authority.

Only:

```text
exact authenticated active matrix
 -> complete boundary batch
 -> P2 transition
 -> durable P3 head
 -> CampaignStore adoption
```

may advance scientific state.

## 3.5 Recovery is authentication followed by reuse

A durable progress record is accepted for reuse only after the current real scientific persistence/replay owners authenticate it.

Simple file existence, JSON parsing, or internal digest self-consistency is insufficient.

## 3.6 No persistence-format redesign without evidence

Existing records already bind:

- logical screen/boundary/cell identity;
- completion identity;
- trajectory identity;
- outcome;
- complete scientific parent references.

The expected repair should therefore require no schema bump and no artifact migration.

If implementation proves that an existing persisted record lacks information genuinely necessary for authentication, stop and reopen only that persistence-design surface.

---

# 4. Implementation obligations and delegated solution space

## Obligation A — establish one authenticated partial-progress recovery owner

### Concern

Current low-level collection can find persisted completion records, but production reuse requires proof that those records still descend from the exact accepted scientific parent graph.

### Required end state

There must be one canonical code path that, for an active boundary, can recover accepted completed cells and authenticate each one through the real P3 owners before returning it as reusable execution progress.

For each recovered cell, verify at minimum:

- current screen-window identity;
- exact boundary epoch;
- exact `(N, optimizer_seed)` identity;
- membership in the currently active P2 matrix;
- exact progress deterministic key;
- progress-to-completion digest binding;
- exact completion window/boundary/N/seed/outcome linkage;
- trajectory and current experiment/context/common-preparation lineage;
- candidate membership/materialization;
- planned-rung ancestry;
- predecessor continuation when applicable;
- TRAIN2 boundary/snapshot evidence where applicable;
- EVAL2 role/evaluation artifact/prediction/metric evidence for success;
- raw authenticated failure evidence and translation for supported numerical failures;
- reconstructed outcome digest.

Existing scientific replay machinery must be reused or factored into this canonical owner.

### Required simplification

Do not create separate:

```text
weak progress collector
+
trusted progress collector
+
runtime-only verifier
+
restart-only verifier
```

with duplicated semantics.

Prefer to strengthen/consolidate the existing collection/replay seam so that any production path claiming a cell is reusable passes through the same scientific validation owner.

The exact helper/function name is delegated.

### Malformed-state behavior

Fail closed for:

- duplicate incompatible progress for one logical cell;
- progress for the wrong screen;
- wrong boundary;
- foreign seed;
- non-active N;
- extra current-boundary cell outside the exact P2 active key set;
- wrong completion reference;
- missing mandatory completion;
- corrupted/tampered scientific parent;
- outcome that cannot be reconstructed from its accepted parents.

Absence of a progress record for an active key is not an error. It means that cell remains to be executed.

---

## Obligation B — schedule only missing active cells

### Concern

The real production runtime currently schedules every P2-active key even when some current-boundary keys are already durably complete.

### Required end state

For every nonterminal boundary, production orchestration must derive:

```text
active_keys = exact P2-required ordered matrix
recovered = authenticated durable completions for current boundary
missing_keys = active_keys - recovered_keys
```

Only `missing_keys` may enter `_execute_candidate_cell()` or its equivalent real candidate/TRAIN2/EVAL2 execution path.

Recovered cells must not:

- retrain;
- rematerialize unnecessarily;
- rerun EVAL2;
- republish a new completion;
- consume another optimizer attempt;
- receive a new scientific result.

### Ordering

Final completion records supplied to `build_complete_boundary_batch()` must follow the exact P2 `active_keys` order regardless of which cells were recovered and which were newly executed.

Do not rely on filesystem enumeration order or completion time.

A suitable conceptual realization is:

```text
completion_by_key = authenticated recovered completions

for key in active_keys:
    if key not in completion_by_key:
        completion_by_key[key] = execute(key)

ordered_completions = tuple(
    completion_by_key[key] for key in active_keys
)
```

This is guidance, not a frozen implementation prescription.

### Partial first invocation

If an ordinary execution failure occurs after several cells publish successfully:

- reducer remains unchanged;
- published cells remain durable;
- invocation fails normally;
- subsequent invocation re-authenticates those cells;
- only missing cells execute.

---

## Obligation C — preserve true conflict detection

### Concern

The observed exception may tempt an implementation to weaken the publisher instead of fixing scheduling.

### Required end state

`record_candidate_boundary_outcome()` or its equivalent owner must retain the semantic distinction:

```text
same logical cell + same exact progress
    -> idempotent success

same logical cell + different progress
    -> hard conflict
```

### Forbidden repairs

Do not:

- unlink the old progress record;
- overwrite it;
- rename it aside automatically;
- pick the newer result;
- pick the older result without validation;
- compare only N/seed/epoch;
- make the error recoverable by silently throwing away one scientific execution;
- recompute until a result happens to match;
- use mutable “latest result” semantics.

The correct repair prevents already-completed valid cells from being re-executed in the first place.

---

## Obligation D — preserve current-boundary and previous-rung semantics separately

### Concern

There are two distinct forms of restart:

1. current boundary has some cells already completed;
2. a survivor is entering a later boundary and needs its prior authenticated TRAIN2 snapshot.

The code already has later-rung continuation resolution.

### Required end state

Do not create a competing continuation system.

For a missing cell at boundary `n2` or `n3`:

- current-boundary durable progress determines whether the cell itself needs execution;
- if execution is needed, existing previous-boundary resume/continuation authority supplies the exact predecessor state.

For a cell already complete at the current boundary, no continuation workspace or training invocation is needed.

---

## Obligation E — preserve campaign/P3 authority ordering

The real current production sequence must remain:

```text
load current campaign generation
 -> reconstruct/revalidate P1/P2/P3 authority
 -> reconcile committed P3 execution history
 -> derive active P2 boundary
 -> authenticate current-boundary partial progress
 -> execute missing cells only
 -> assemble exact ordered complete matrix
 -> build/commit P3 boundary batch/head
 -> reconcile
 -> CAS-adopt head into CampaignStore
 -> continue if nonterminal
```

Do not introduce P4-local ranking, selection, or alternate restart authority.

---

# 5. Implementation authority

## 5.1 Frozen

Frozen for this repair:

- P2 is sole scientific reducer/selection authority.
- P3 is the execution evidence/restart owner.
- CampaignStore remains the current-generation/adoption authority.
- Current boundary reducer state does not advance on partial progress.
- Existing valid partial progress is reusable after authentication.
- Exact active matrix and order derive from P2.
- Logical-cell progress remains immutable.
- Genuine same-cell conflicting evidence remains a hard error.
- Existing TRAIN2/EVAL2 scientific semantics remain unchanged.
- Long GPU/full-production qualification remains deferred.

## 5.2 Delegated

Implementation may choose or refactor:

- helper names;
- whether the existing collection function is strengthened or replaced;
- exact dictionary/index representation of recovered cells;
- internal factoring of `_reverify_published_parent_graph()`;
- diagnostic/progress wording;
- whether authenticated recovery is invoked directly after reconciliation or factored into a common coordinator operation;
- local type annotations/data structures.

These choices must not create a second authority or duplicate scientific replay logic.

## 5.3 Reopen only on evidence

Reopen Design only if implementation evidence establishes one of the following:

1. Existing persisted partial-completion schemas cannot authenticate the scientific parent graph required for reuse.
2. The one-logical-cell immutable-progress architecture is incompatible with a genuine product concurrency requirement.
3. The P2 active-matrix model cannot distinguish durable completion from required scientific work without changing P2 semantics.
4. Reusing a valid completion would scientifically differ from executing the same accepted logical cell, demonstrating that an execution input affecting scientific identity is missing from the current cell/window/trajectory identities.
5. The existing P3 replay owner cannot be reused/consolidated without changing frozen scientific ownership.

Do not reopen merely because a local helper API is inconvenient.

---

# 6. Persistence compatibility

## 6.1 Existing current-screen partial progress

Valid existing partial progress must be readable and reusable in place.

No user deletion of the current target-size execution root should be required for this bug.

## 6.2 No migration by default

The intended repair changes runtime recovery/scheduling behavior, not persisted scientific meaning.

Therefore:

- no schema bump by default;
- no rewrite of old valid progress;
- no rehashing of valid scientific objects;
- no regenerated replacement completion merely to canonicalize state.

## 6.3 Genuine corrupt state

If an existing progress record fails current deep authentication, fail with an actionable integrity/lineage error.

Do not silently replace it with a newly computed result.

Corruption recovery, if later desired, is a separate explicitly designed operation.

---

# 7. Required focused regression

## 7.1 Authenticated progress recovery

Create focused tests covering:

### Valid current-boundary progress

Persist one valid completion/progress pair and recover it.

Assert:

- exact key recovered;
- exact completion digest retained;
- full parent replay succeeds;
- no new scientific artifact is created merely by recovery.

### Missing active progress

Leave an active key absent.

Assert it is reported/treated as missing work rather than corruption.

### Foreign or malformed progress

Reject at least:

- foreign window;
- wrong boundary;
- foreign seed;
- inactive target size;
- mismatched deterministic progress filename;
- wrong completion reference;
- wrong outcome digest;
- duplicate/conflicting logical cell if representable through corrupted filesystem state.

### Deep-parent tamper

Starting from a top-level progress/completion pair that remains internally self-consistent, remove or alter representative deep parents, such as:

- trajectory;
- materialization/configuration;
- planned rung;
- boundary snapshot/checkpoint evidence;
- evaluation artifact;
- prediction evidence;
- metric record;
- raw numerical-failure parent.

The authenticated recovery path must fail before the runtime treats that cell as complete.

Test representative parent classes sufficient to prove the common replay owner is live; do not create one redundant test per field when existing replay tests already cover the remainder.

---

# 8. Preserve publication idempotency/conflict regression

Retain or strengthen existing tests proving:

1. exact same completion/progress retry is idempotent;
2. a different outcome/completion for the same logical cell is rejected;
3. the repair does not weaken immutable publication merely to make restart pass.

This is a mandatory anti-regression boundary.

---

# 9. Real production-runtime bug reproducer

This is the primary acceptance test for the reported defect.

Use the real current:

```text
command_select_target_size
 -> execute_current_select_target_size
 -> P3 reconciliation/recovery
 -> candidate execution
 -> P3 completion/batch/head
 -> CampaignStore adoption
```

with a bounded fixture.

Expensive MACE computation may be replaced or reduced only below the real orchestration/state/restart owners.

## Scenario

1. Construct a valid current campaign and target-size screen.
2. Persist valid completion/progress for one or more cells of the active boundary.
3. Do not persist a complete boundary batch/head.
4. Start a fresh `select-target-size` invocation.
5. Instrument the bounded trainer/evaluator so that invocation for an already completed key is detectable and considered test failure.
6. Permit execution for missing active keys.
7. Finish the boundary.

## Required assertions

- existing cells are recovered;
- trainer/EVAL2 are not invoked for recovered current-boundary cells;
- every missing key executes exactly once;
- no immutable-progress conflict occurs;
- recovered and new records are assembled in exact P2 size-major/seed-minor order;
- exactly one complete batch is produced;
- exactly one reducer transition is committed;
- CampaignStore adopts the correct head/reducer state;
- no duplicate completion/progress is created for recovered cells.

A lower-level collector test does not substitute for this production-owner test.

---

# 10. Fresh-process ordinary-failure restart regression

Exercise the real campaign runtime across two invocations.

## First invocation

- execute several active cells;
- introduce one ordinary operational failure after some valid progress has published;
- allow invocation to fail.

Assert:

- completed cells remain durable;
- no complete boundary batch/head exists;
- P2 reducer state remains exactly pre-boundary;
- no scientific failure is fabricated from the ordinary operational error.

## Second fresh invocation

Reopen through real CampaignStore/P3 runtime.

Assert:

- previously completed cells authenticate and are reused;
- only missing cells execute;
- no completed cell retrains;
- completed exact matrix produces one reducer transition;
- final result matches uninterrupted execution under the same deterministic fixture.

---

# 11. Later-boundary partial-restart regression

After successfully committing the first boundary:

1. enter the next boundary;
2. complete only some surviving cells;
3. interrupt;
4. start a fresh invocation.

Assert:

- current-boundary completed cells are reused;
- missing cells use the existing authenticated previous-rung continuation path;
- no current-boundary completed cell resumes TRAIN2 again;
- eliminated candidates receive no work;
- exact boundary matrix and reducer transition remain correct.

This test protects the interaction between partial-current-boundary recovery and existing `n1 -> n2 -> n3` continuation.

---

# 12. Current-root integrity negatives

The production scheduler must fail before new scientific work is admitted if supposedly reusable progress is inconsistent with current authority.

Required representative negatives:

- current-boundary progress references an inactive `(N, seed)`;
- progress belongs to a different screen window;
- progress completion exists but a mandatory scientific parent is missing/tampered;
- completion trajectory no longer validates against current definition/context/common preparation;
- previous-rung continuation ancestry is inconsistent for a later boundary.

Do not simply ignore extraneous/foreign current-screen progress and proceed: unexplained contradictory durable scientific evidence must remain fail-closed.

---

# 13. Affected-surface regression

At minimum re-run the affected tests for:

- P3-E coordinator, progress, completion, batch, exactly-once commit and restart;
- P3-F assembled target-size execution/restart;
- P3 parent-graph/replay authentication tests affected by any verifier refactor;
- candidate continuation/resume tests;
- P3 head-pointer reconciliation tests if reconciliation changes;
- P4 current campaign target-size runtime;
- CampaignStore/P3 cross-store adoption;
- target-size current-state/restart/terminal projection tests plausibly touched by runtime sequencing;
- current campaign CLI/parser `select-target-size` tests;
- immutable persistence/publication tests whose owner was modified.

Re-derive the final affected surface after implementation. If the changed owner/call graph cannot be bounded confidently, run the broader available target-size/campaign regression suite.

A green low-level P3-E test alone is insufficient because the demonstrated defect resides in the production campaign caller.

---

# 14. Structural and simplicity checks

Before closure inspect the final implementation for:

- exactly one production current target-size orchestration path;
- no second durable partial-progress registry;
- no second scientific replay implementation;
- no mutable replacement for immutable progress;
- no retry wrapper that merely hides the conflict;
- no automatic progress deletion;
- no P4-local ranking/reducer logic;
- no fresh current-boundary execution of cells already authenticated complete;
- no weakened lineage/digest validation.

If implementation begins accumulating special cases around progress publication rather than making scheduling consume the existing durable owner correctly, stop and simplify before continuing.

---

# 15. Implementation sequence

## Stage A — canonical authenticated partial-progress recovery

1. Reconcile/refactor the existing progress/completion collection path with the existing deep P3 scientific replay owner.
2. Make reusable completion recovery validate exact current authority and active-cell identity.
3. Preserve true publication conflicts.
4. Add focused recovery/tamper/conflict tests.
5. Run stage-local affected P3 persistence/restart regression.

**Stage gate:** valid partial progress can be authenticated and recovered; malformed/stale/tampered progress fails closed; immutable conflict behavior is unchanged.

## Stage B — production scheduling integration

1. Integrate authenticated recovery into the real current `execute_current_select_target_size()` boundary loop.
2. Execute only missing active keys.
3. Assemble recovered + new completions in exact P2 order.
4. Preserve existing batch/head/adoption sequencing.
5. Add real-owner interrupted-run/fresh-restart and later-boundary regressions.
6. Run stage-local affected campaign/P3/P4 regression.

**Stage gate:** the reported failure scenario completes without re-executing already accepted cells and without weakening publication.

## Stage C — assembled closure

1. Reconcile the final implementation against this workplan and the frozen V7/P3/P4 authorities.
2. Re-derive the final affected surface.
3. Run complete affected regression.
4. Run real-owner bounded integration.
5. Run structural/simplicity checks.
6. Attribute any demonstrably unrelated pre-existing failures rather than hiding them.

---

# 16. Production qualification

Full production-scale, long real-data GPU qualification is **deferred**.

The bug is a functional restart/orchestration defect and must be closed with bounded regression and real-owner integration.

A rerun of the user's actual partially completed campaign after implementation is useful external confirmation, but it does not replace the required automated restart regression.

---

# 17. Acceptance criteria

The implementation passes only when all of the following are true:

1. A valid partially completed active boundary survives a process restart.
2. Existing completed cells are scientifically authenticated.
3. Authenticated completed cells are not retrained or re-evaluated.
4. Only missing active cells execute.
5. Exact P2 matrix ordering is preserved.
6. Partial progress does not advance the reducer.
7. The complete boundary advances the reducer exactly once.
8. Exact retry remains idempotent.
9. Different same-cell evidence remains a hard immutable conflict.
10. Tampered/stale/foreign partial progress fails closed before being reused.
11. Existing valid persisted partial progress requires no rewrite or migration.
12. No duplicate resume authority or scientific replay machinery is introduced.
13. Fresh-process production-runtime regression reproduces and closes the reported failure mode.
14. Later-boundary continuation remains correct.
15. Complete affected regression and bounded integration pass.

---

# 18. Explicit non-solutions

The following do **not** satisfy this workplan:

- deleting the user's current progress directory;
- asking the user to rerun the entire screen from scratch;
- ignoring existing progress;
- rerunning completed cells and swallowing publication conflict;
- overwriting immutable progress;
- changing progress from immutable to mutable;
- accepting the newest/oldest conflicting result by policy;
- weakening digest/lineage validation;
- making `record_candidate_boundary_outcome()` return the old record when a newly computed conflicting record arrives;
- adding a second SQLite/file resume table;
- considering file existence sufficient evidence that a cell is complete;
- testing only `collect_boundary_cell_completion_records()` while bypassing the production campaign runtime.

---

# 19. Design verdict

**Current implementation: NO-PASS.**

The production target-size runtime violates the already-frozen partial-boundary recovery semantics and can repeat expensive accepted scientific work before colliding with the correct immutable-progress guard.

**This workplan: PASS / implementation-ready.**

The repair does not require a scientific redesign, target-size policy change, persistence schema change, or new recovery architecture. It should consolidate and consume the existing P3 durable progress/replay machinery correctly at the production scheduling boundary.
