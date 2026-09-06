---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-REPLAY-ACCELERATION-REALIZATION-DRIFT-BUGFIX
protocol_version: 5.15.0
status: active
parent_workplan_id: CODE-MLFF-TARGET-SIZE-PARTIAL-BOUNDARY-RESUME-BUGFIX
---

# MLFF target-size replay acceleration-realization drift bug-fix workplan

## 0. Protocol binding and inherited authority

### 0.1 Current protocol binding

This is a newly authored repair workplan and is governed by the current remote software-development protocol, **5.15.0**.

The older V7/P3/P4 target-size authorities and the parent partial-boundary-resume workplan retain the protocol versions they explicitly declare. Their still-binding product/scientific requirements and Frozen high-level architecture remain inherited authority for this repair. Binding this new workplan to 5.15.0 does **not** silently reinterpret or upgrade those older workplans.

Accordingly:

```text
explicit user/task requirements
 -> still-binding target-size product/scientific contracts and Frozen parent architecture
 -> this repair workplan under Protocol 5.15.0
 -> delegated implementation-local realization
```

Protocol 5.15.0 governs the generic Design -> Implementation methodology, active-simplicity discipline, language engineering profile, relation-first tool routing, stage-local/final regression, real-owner integration, proxy-proof acceptance, and final affected-surface re-derivation for this repair.

### 0.2 Protocol 5.15 reconciliation for this repair

The affected executable surface is Python. Implementation must therefore follow the current Python engineering profile while preserving the shared scientific, persistence/restart, orchestration, and testing owners. In particular:

- prefer one clear Python-native replay/policy owner over wrapper hierarchies, parallel policy objects, or duplicated field plumbing;
- treat the existing current-vs-historical policy ambiguity as a Tier-2 simplification target before adding durable machinery;
- do not introduce a native/C++ boundary, custom kernel, new accelerator backend, or extra runtime layer for this correctness repair;
- use relation-first repository tooling when it materially improves the claim: semantic symbol/caller/reference questions should use Serena when available/current/supported; structural absence/duplicate-path claims may use Semgrep when appropriate; broad combinatorial Python state invariants may use Hypothesis when materially useful; unavailable tooling never weakens the engineering claim;
- keep acceptance proxy-proof: bounded trainer/evaluator doubles are allowed below the production restart/orchestration owner, but tests must execute the real trajectory replay, recovery/reconciliation/continuation, batch/head, and CampaignStore transition paths whose behavior is under acceptance;
- after each material executable stage, run focused checks plus stage-local affected regression; after all executable edits, re-derive the affected surface and run complete affected regression plus assembled real-owner integration;
- production-scale GPU qualification remains separate and deferred; Protocol 5.15 does not convert implementation regression into full target-machine qualification.

### 0.3 Snapshot-complete relationship to older target-size authority

This workplan carries the repair-specific product invariants, Frozen decisions, non-goals, acceptance boundaries, and redesign triggers needed for implementation. It intentionally relies on the supplied repository's older V7/P3/P4 authorities only for their still-binding target-size scientific architecture and governed contracts; their historical Tier-2 realization is not automatically preserved.

If a 5.15 generic methodology rule appears to conflict with an explicitly Frozen target-size scientific decision from the parent authority, the scientific/Frozen decision remains the product constraint and the implementation method must adapt around it. If evidence shows that Frozen decision itself is invalid, reopen only that bounded Design surface rather than silently reinterpreting it through the newer protocol.

---

## 1. Objective / problem invariants / non-goals

### 1.1 Observed production failure

A restarted `select-target-size` invocation reaches the newly implemented authenticated partial-boundary recovery path and fails before any missing cell is scheduled:

```text
Target-size selection - controlled configurable fidelity
--------------------------------------------------------
Epoch is a controlled variable during this operation: only the exact configured screen boundary checkpoints contribute to ranking.
...
execute_current_select_target_size
  -> recover_authenticated_boundary_progress
  -> authenticate_boundary_cell_completion_record
  -> _validate_replayed_candidate_lineage
  -> validate_target_size_candidate_trajectory

TrainingDataInputError: Trajectory realization is stale for the current exact T_N;
loader/update geometry or precision realization differs.
```

This failure occurs while authenticating an already published target-size cell. It is not evidence by itself that the persisted `T_N`, loader geometry, update geometry, or precision realization actually changed.

### 1.2 Root cause

The current target-size identity model intentionally separates:

1. a **seed-neutral screen execution context**, and
2. **candidate-specific execution realization** stored in each trajectory.

The seed-neutral optimizer-policy digest explicitly excludes:

```text
seed
acceleration_realization_digest
resolved_acceleration_kernel_mode
```

because seed and acceleration realization are candidate/execution-specific rather than global screen identity.

A persisted `TargetSizeCandidateTrajectory` independently binds its historical candidate realization, including:

```text
exact T_N-derived counts
batch/update geometry
precision schedule/default dtype
acceleration_realization_digest
optimizer seed
full-n3 budget
```

On restart, however, `TargetSizeRestartAuthority.optimizer_policy_for_seed()` currently reconstructs the replay optimizer policy by taking the **current** seed-neutral optimizer template and replacing only the seed. The current template is rebuilt by `build_screen_context()` from the current campaign configuration and the currently stored/qualified training acceleration realization.

`validate_target_size_candidate_trajectory()` then derives a new expected candidate realization from that current optimizer policy and requires the entire realization digest to equal the historical trajectory realization digest.

The checks immediately preceding that comparison already require:

- the same experiment definition;
- the same execution context;
- the same common preparation;
- the same screen schedule;
- the exact accepted `T_N` membership;
- the same seed-neutral optimizer-policy identity;
- the authorized optimizer seed;
- the accepted evaluation-model-state convention.

Therefore a current-versus-historical mismatch in `acceleration_realization_digest` can survive all those checks while still changing the whole realization digest. The replay path then reports a generic stale `T_N`/loader/update/precision error even though the historical cell may be perfectly valid and internally authenticated.

The defect is thus a **historical replay semantic error**: the validator substitutes a mutable current acceleration realization into the identity of already accepted historical candidate evidence.

### 1.3 Original product problem

Target-size screening is a durable scientific workflow. Once a logical `(screen window, N, optimizer seed, boundary)` cell is validly published, restart/reconciliation must be able to authenticate and reuse that exact historical evidence from its own durable ancestry.

A later invocation may run under a different currently qualified acceleration realization. That later execution environment must not retroactively rewrite the historical identity of an already accepted trajectory.

At the same time, restart must continue to reject genuine stale or forged evidence: a historical trajectory whose exact `T_N`, training/update geometry, precision policy, schedule, seed, materialization, checkpoint/provider, prediction, metric/failure, or other accepted parentage is inconsistent with its durable identity must still fail closed.

### 1.4 Tier-1 product invariants

The repair must preserve all of the following:

- P2 remains the sole authority for target-size population, exact `T_N`, seeds, boundary schedule, evaluation memberships, reducer transitions, ranking, survivor decisions, and selected size.
- P3 remains the durable execution/restart authority for trajectories, materializations, TRAIN2 snapshots/failures, EVAL2 evidence, per-cell completion/progress, complete batches, and heads.
- A persisted trajectory is immutable historical evidence. Replay authenticates what was actually accepted; it does not silently substitute a later execution realization.
- Acceleration realization remains bound provenance when it can affect execution semantics.
- The current acceleration realization governs **new work** admitted under the current invocation; it is not automatically historical authority for already published cells.
- The seed-neutral optimizer-policy identity remains seed/acceleration-neutral as designed unless new evidence proves that high-level identity split scientifically invalid.
- Exact `T_N`, loader/update geometry, batch semantics, precision realization, full screen budget, seed, and scientific policy drift remain hard restart failures.
- Durable materialization/config/checkpoint/provider/prediction/metric/failure ancestry remains fully authenticated.
- Partial-boundary recovery continues to execute only genuinely missing active cells.
- Existing immutable logical-cell progress conflict detection remains unchanged: exact retry is idempotent; different evidence for the same logical cell is a hard conflict.
- Complete-boundary reducer advancement remains atomic and exact-order.
- Existing later-rung continuation semantics remain unchanged.
- Existing valid current-screen evidence should remain reusable without destructive cleanup, re-prepare, or forced retraining.
- Production-scale GPU qualification remains separate from implementation acceptance.

### 1.5 Non-goals

This repair must not:

- change the configured fidelity boundaries;
- change candidate sizes, evaluation sizes, seed population, ranking, practical-equivalence rules, or survivor policy;
- weaken exact `T_N` membership validation;
- make loader/update/batch geometry drift replayable;
- make precision/default-dtype drift replayable;
- make a forged acceleration digest acceptable;
- remove acceleration provenance merely to make restart pass;
- declare every acceleration realization scientifically interchangeable without evidence;
- promote the latest/current acceleration realization into a global screen identity merely to avoid historical replay logic;
- invalidate all previously accepted screen evidence whenever doctor/runtime acceleration qualification changes;
- bypass `authenticate_boundary_cell_completion_record()` from partial-boundary recovery;
- create a recovery-only weak validator;
- make file presence or self-consistent JSON sufficient evidence;
- delete progress/completions to force recomputation;
- overwrite immutable progress;
- swallow the immutable conflict error after re-executing an already completed cell;
- introduce a second restart database or alternate trajectory authority;
- introduce a persistence schema migration unless implementation evidence proves the existing durable evidence is insufficient to authenticate the historical execution realization.

---

## 2. Repository diagnosis and ownership

### 2.1 Current new-work path is conceptually correct

For a first-boundary missing cell, production currently builds a candidate trajectory from the current screen context and a current per-seed optimizer policy. That trajectory binds the candidate-specific realization actually authorized for that execution.

This remains the correct direction for **new work**.

### 2.2 Current historical replay path is defective

The shared replay path currently performs, conceptually:

```text
load historical trajectory
 -> derive optimizer policy from current restart template + historical seed
 -> derive expected candidate realization from current optimizer policy
 -> require historical realization == current-derived realization
```

This is too strong because the restart template intentionally excludes the per-realization acceleration fields from its seed-neutral identity.

The resulting contradiction is:

```text
execution context says acceleration realization is not global screen identity
but
trajectory replay demands old acceleration realization == current acceleration realization
```

That converts a deliberately candidate-local historical provenance field into an accidental mutable-current restart requirement.

### 2.3 The repair belongs at the canonical replay seam

The failure surfaces through partial-boundary recovery, but the same `_validate_replayed_candidate_lineage()` path is also consumed by:

- committed completion/head reconciliation;
- scientific root replay;
- later-boundary candidate continuation/resume.

Therefore this is not a `recover_authenticated_boundary_progress()` special case.

The repair must establish correct historical trajectory replay semantics once and reuse them from every replay/restart consumer.

### 2.4 Existing durable evidence should be preferred

Current P3 artifacts already preserve substantial historical execution provenance:

- trajectory candidate realization;
- materialized MACE configuration and hashes;
- materialization metadata;
- TRAIN2 snapshot/runtime metadata and checkpoint bytes;
- authenticated provider state;
- prediction execution provenance;
- EVAL2 artifacts and metrics/failures.

Implementation must first use these existing historical parents as the replay authority for already published work.

Do not add a new persisted “historical optimizer policy” object unless concrete inspection proves that an execution-semantic field required for replay cannot be reconstructed or authenticated from existing accepted parents.

---

## 3. Frozen high-level architecture and engineering envelope

### 3.1 Frozen: seed-neutral global context plus candidate-specific trajectory realization

The existing P3 architecture deliberately separates the study-wide seed-neutral context from candidate-varying `N`/seed execution realization.

For this repair, keep that split Frozen.

The global context remains the authority for stable screen-wide scientific/training policy. The trajectory remains the authority for candidate-specific realized execution facts.

A current execution realization does not retroactively redefine an already persisted trajectory.

### 3.2 Frozen: historical evidence is authenticated from historical parents

Restart/reconciliation must evaluate persisted evidence against:

1. still-current global P1/P2/P3 authority that is supposed to remain common across the screen; and
2. the persisted candidate-specific realization and scientific parent graph that actually produced the accepted cell.

This is the same durable-replay principle already used for materialization, snapshots, prediction evidence, and metrics.

### 3.3 Frozen: current realization controls newly executed work

When an active cell has no accepted current-boundary progress and must execute now, its new trajectory/materialization must bind the currently authorized acceleration realization and current candidate execution realization.

Historical replay semantics must not become permission for new work to silently use stale execution realization.

### 3.4 Frozen: true candidate realization drift remains fail-closed

The fix must preserve rejection of changes that alter the historical candidate's accepted scientific/execution identity, including at minimum:

- different `T_N` or candidate-membership digest;
- different target/replay/harness counts;
- different batch size or validation batch semantics where identity-bound;
- different updates/structures per epoch;
- different full-n3 update/presentation budget;
- different default dtype or precision schedule;
- different optimizer seed;
- different configured full-screen epoch horizon;
- forged/tampered historical acceleration realization;
- inconsistent materialization/config/checkpoint/provider execution ancestry.

### 3.5 Frozen: one deep replay owner

`authenticate_boundary_cell_completion_record()` or an equivalent consolidated owner remains the single accepted completion replay boundary.

The trajectory fix may refactor lower-level policy/realization helpers, but must not create separate weak and strong replay modes for recovery versus reconciliation.

### 3.6 Frozen: no production qualification in this implementation cycle

Functional acceptance must use bounded deterministic fixtures and real production owners above expensive TRAIN2/EVAL2 execution seams.

Long, data-heavy GPU production qualification remains deferred to the final complete release/user-machine qualification phase.

---

## 4. Implementation obligations and delegated solution space

### Obligation A — define correct historical trajectory replay semantics

#### Concern / rationale

The replay validator currently conflates two different questions:

```text
Is this historical trajectory internally authentic and compatible with the still-current screen authority?
```

and

```text
Would a newly created candidate today receive byte-identical execution-realization metadata?
```

Only the first question is valid for already published evidence.

#### Required end state

The canonical trajectory replay path must authenticate a historical trajectory without replacing its bound acceleration realization with the latest current acceleration realization.

It must still prove that every realization field that is determined by still-current P1/P2/global training authority is correct.

Conceptually, historical replay should distinguish:

```text
stable/current-required candidate consequences
    exact T_N membership
    counts
    batch/update geometry
    precision policy
    full-n3 schedule
    seed-neutral training policy
    authorized seed

historical candidate execution provenance
    acceleration realization actually bound to this trajectory
    any other intentionally candidate-local execution realization
```

The exact factoring is delegated.

#### Required simplification

Prefer one trajectory-aware replay derivation/validator rather than adding conditionals independently in:

- partial progress recovery;
- root reconciliation;
- continuation resolution;
- EVAL2 replay.

If the current `optimizer_policy_for_seed()` name/contract is ambiguous between “policy for new work” and “policy for historical replay,” implementation may refactor it into clearer internal ownership. Do not preserve an ambiguous helper merely because tests currently depend on it.

#### Anti-shortcut

A fix that simply omits `acceleration_realization_digest` from all validation is insufficient.

Historical acceleration provenance must continue to authenticate against the durable execution evidence that claims to have used it.

### Obligation B — derive replay policy from one seed-neutral template plus historical candidate provenance

#### Concern / rationale

P3's accepted identity model says the seed-neutral optimizer template excludes seed and per-realization acceleration fields, while each trajectory binds candidate-specific realization.

Replay needs those two pieces recombined correctly.

#### Required end state

For already persisted trajectory evidence, the accepted replay optimizer/execution policy must be derived from:

```text
accepted seed-neutral optimizer template
+ authorized historical optimizer seed
+ historical candidate-local execution realization required for replay
```

rather than:

```text
accepted seed-neutral optimizer template
+ current acceleration realization
+ historical seed
```

The result must be sufficient for all downstream validators that genuinely need optimizer policy, including materialization/config validation, snapshot/provider authentication, EVAL2 execution-policy validation, and batch-width validation.

#### Existing-evidence-first rule

Before adding persistence, determine whether all historical acceleration execution facts needed by downstream replay already exist in:

- `TargetSizeCandidateTrajectory.realization`;
- durable MACE config;
- materialization record;
- TRAIN2 runtime/snapshot/provider metadata;
- prediction evidence.

If yes, reuse them.

If a required historical field such as an exact resolved acceleration kernel mode is not recoverable from any currently persisted accepted parent, do **not** guess it from the current runtime. Stop and reopen the bounded persistence-design surface described in Section 8.

### Obligation C — preserve new-work/current-realization authorization

#### Concern / rationale

Historical replay compatibility must not turn into stale execution for work that has not yet happened.

#### Required end state

For a missing cell executed by the current invocation:

- construct its optimizer policy from the current accepted configuration/runtime realization;
- construct a new trajectory from that policy;
- bind the current acceleration realization in the new trajectory;
- materialize/train/evaluate against that trajectory;
- publish the exact resulting historical evidence.

After publication, that trajectory becomes immutable historical evidence and future replay must authenticate it as such.

This permits one incomplete boundary to contain valid cells produced under different qualified acceleration realizations **only if** the existing P3 scientific identity/equivalence model permits those realizations to coexist under the same seed-neutral context and all each-cell provenance authenticates.

If implementation evidence shows that differing acceleration realizations change governed numerical semantics beyond accepted equivalence, that is a design-reopen condition, not a reason to silently force old evidence to current realization.

### Obligation D — preserve genuine stale-realization detection

#### Required end state

The existing `validate_target_size_candidate_trajectory()` stale checks must remain materially equivalent for genuine invalidity.

At minimum, replay must reject a historical trajectory when any of the following is wrong relative to accepted authority or its own historical provenance:

- target size or exact ordered `T_N` membership;
- membership digest;
- seed-neutral training-policy digest;
- unauthorized optimizer seed;
- batch size;
- validation batch semantics if identity-relevant;
- target/replay/harness counts;
- structures/update geometry;
- planned update/presentation totals;
- `max_num_epochs`/full screen horizon;
- default dtype;
- precision schedule digest;
- evaluation-model-state convention;
- historical acceleration provenance is malformed, forged, or contradicted by durable materialization/provider evidence.

Do not replace the current all-fields digest comparison with a hand-written subset that accidentally omits identity-bearing fields. Prefer a canonical derivation or structured comparison whose ownership is explicit and tested.

### Obligation E — apply the corrected replay semantics to every real restart consumer

The corrected historical trajectory replay must be exercised through all affected production owners:

1. **current-boundary partial-progress recovery**
   - valid historical cells are authenticated and reused;
   - only missing cells execute.

2. **committed-head/root reconciliation**
   - previously committed cells/heads remain scientifically replayable after current acceleration realization changes;
   - replay reconstructs the same reducer state/head.

3. **later-boundary continuation resolution**
   - a survivor's previous-rung trajectory/materialization/snapshot remains authentic after current acceleration realization changes;
   - continuation resolves the correct historical predecessor;
   - the existing continuation authority remains the only continuation mechanism.

No consumer-specific bypass is acceptable.

### Obligation F — keep downstream materialization/provider/EVAL2 authentication strong

#### Concern / rationale

Acceleration realization is execution provenance and can affect numerical/backend behavior. Merely accepting an old trajectory digest is not enough.

#### Required end state

After trajectory replay accepts the historical candidate realization, existing deep validators must continue to verify as applicable:

- materialized target/harness bytes and sidecars;
- MACE config bytes/digest;
- config device/default dtype and other governed execution fields;
- snapshot/checkpoint/runtime summary hashes;
- authenticated checkpoint provider;
- live/EMA state;
- provider runtime architecture/backend policy;
- prediction execution provenance;
- exact-M evaluation artifact;
- EVAL2 metric or raw failure evidence;
- reconstructed P2 outcome.

If historical acceleration provenance is contradicted by those accepted parents, fail closed.

Do not turn the repair into “trust trajectory JSON and skip provider replay.”

### Obligation G — preserve partial-boundary restart and immutable publication behavior

The previous repair remains binding.

For an interrupted boundary:

```text
reconcile committed P3 history
 -> derive exact active P2 matrix
 -> authenticate existing current-boundary progress
 -> recover valid historical cells
 -> execute only missing cells under current authorization
 -> assemble exact P2 order
 -> commit one batch/head
 -> adopt through CampaignStore CAS
```

The immutable publication rule remains:

```text
same logical cell + exact same progress -> idempotent success
same logical cell + different progress  -> hard conflict
```

The new repair must prevent false stale rejection of valid recovered evidence; it must not weaken the conflict owner.

### Obligation H — compatibility and existing durable state

#### Required end state

Existing valid target-size artifacts produced under the current schemas must remain reusable in place when their historical provenance authenticates.

Expected default:

- no schema bump;
- no migration;
- no deletion of the target-size execution root;
- no forced `prepare` rerun;
- no forced retraining of already accepted cells;
- no rewriting of trajectory/completion/progress objects merely to canonicalize them to current acceleration realization.

If an existing artifact independently fails scientific authentication, report the actual violated historical parent/identity instead of replacing it with current execution evidence.

---

## 5. Implementation authority

### 5.1 Frozen

Frozen for this repair:

- P2 scientific target-size policy and reducer ownership.
- P3 durable execution/restart ownership.
- Seed-neutral global execution context plus candidate-specific trajectory realization split.
- Acceleration realization remains candidate/execution provenance rather than silently becoming a global screen identity.
- Historical replay uses the historical candidate realization for already accepted evidence.
- New work uses the current authorized acceleration realization.
- Exact `T_N`, loader/update geometry, precision, seed, schedule, materialization, snapshot/provider, prediction, metric/failure validation remain fail-closed.
- One canonical deep completion replay owner.
- One immutable progress result per logical cell.
- Exact complete-boundary commit and CampaignStore adoption ordering.
- Existing later-rung continuation authority.
- No production-scale GPU qualification during implementation acceptance.

### 5.2 Delegated

Implementation may choose or refactor:

- helper/function names;
- whether trajectory replay validation is split into stable-policy and historical-provenance derivations;
- whether `TargetSizeRestartAuthority.optimizer_policy_for_seed()` is renamed, narrowed, or supplemented by a trajectory-aware internal method;
- exact immutable dataclass used transiently to represent replay policy;
- fieldwise versus canonical-object comparison implementation;
- diagnostic error wording, provided it identifies the actual conflicting dimension more precisely than the current generic stale message;
- local test fixtures and bounded acceleration realization records;
- internal factoring between candidate/coordinator/context modules.

These are Tier-2 choices. Prefer consolidation and deletion of ambiguous duplicate logic over another wrapper layer.

### 5.3 Reopen only on evidence

Reopen Software Design only if implementation evidence proves one of these:

1. Existing durable trajectory/materialization/snapshot/provider/prediction records do not retain enough historical acceleration execution identity to authenticate a previously accepted cell without consulting mutable current runtime state.
2. Different acceleration realizations that currently share one seed-neutral execution context can produce scientifically non-equivalent governed observables, so mixing their accepted cells in one screen violates target-size comparability.
3. A per-candidate historical acceleration realization cannot be reconciled with the Frozen P3 one-trajectory-per-`(N, seed)` model.
4. Correct replay requires changing the P2 experiment definition, reducer semantics, or screen-window identity.
5. Correct replay requires changing the persistence schema of authoritative existing artifacts rather than reusing their current information.

If any trigger fires, reopen only that bounded surface. Do not silently make acceleration realization global, silently discard old cells, or weaken scientific validation.

---

## 6. Required focused regression

### 6.1 Candidate replay realization matrix

Extend the real P3-B candidate replay tests with a fixture that creates a trajectory under historical acceleration realization **A** and then replays under a current template carrying acceleration realization **B**, with all seed-neutral scientific/training fields unchanged.

Required assertions:

1. `A -> A`: replay succeeds.
2. `A -> B`: historical trajectory replay succeeds **only because A remains the bound historical candidate realization and its durable provenance authenticates**.
3. Different batch size: rejects.
4. Different `valid_batch_size` when it affects accepted execution identity: rejects.
5. Different default dtype: rejects.
6. Different precision schedule: rejects.
7. Different full-n3 epoch horizon/schedule: rejects.
8. Different exact `T_N` or membership digest: rejects.
9. Unauthorized seed: rejects.
10. Tampered trajectory acceleration digest: rejects through historical provenance validation.
11. Historical materialization/config/provider evidence that contradicts the trajectory acceleration provenance: rejects.

Do not make this test pass by patching `validate_target_size_candidate_trajectory()` or by removing acceleration fields from the fixture.

### 6.2 Error-specificity regression

When rejection is caused by a true loader/update/precision mismatch, the diagnostic should still identify that class.

When rejection is caused by contradictory historical acceleration provenance, diagnostics should identify historical acceleration/provenance inconsistency rather than claiming `T_N` changed.

Exact wording is delegated; error classification must remain actionable.

### 6.3 Preserve existing P3-B stale tests

The current stale-realization test proving changed batch geometry is rejected remains valid and must continue to pass.

The existing precision/tamper cases must remain or be strengthened, not weakened to accommodate the new restart behavior.

---

## 7. Required real-owner integration and affected regression

### 7.1 Primary production reproducer — partial boundary across acceleration turnover

Create a bounded test through the real production path:

```text
command_select_target_size
 -> execute_current_select_target_size
 -> build_screen_context
 -> reconcile P3 root
 -> recover_authenticated_boundary_progress
 -> authenticate_boundary_cell_completion_record
 -> shared trajectory replay owner
 -> execute only missing cells
 -> P3 batch/head
 -> CampaignStore adoption
```

Scenario:

1. prepare one bounded campaign fixture;
2. invocation A uses acceleration realization A;
3. allow one or more active-boundary cells to publish successfully;
4. simulate an ordinary interruption before the full boundary matrix commits;
5. change only the currently qualified/stored training acceleration realization to B while preserving the same accepted seed-neutral scientific/training policy and screen identity;
6. start a fresh invocation;
7. already published A cells must authenticate and must **not** reach TRAIN2/EVAL2 again;
8. missing cells execute exactly once under B/current authorization;
9. exact P2 matrix order is reconstructed;
10. one batch/head is committed and adopted;
11. no immutable progress conflict occurs.

The trainer/evaluator may be bounded/faked **below** the production runtime/restart semantic owner. Do not bypass the real campaign runtime, P3 recovery, trajectory replay, batch/head, or CampaignStore transition.

### 7.2 Committed-head fresh-process reconciliation

Commit a complete boundary under acceleration realization A, exit, change current realization to B, and reconcile in a fresh process/invocation.

Assert:

- the same immutable head authenticates;
- the same post-reducer state is reproduced;
- no historical trajectory is rewritten;
- no new TRAIN2/EVAL2 work occurs merely to reconcile;
- provider/materialization/EVAL2 parent validation remains live.

This closes the fact that `_validate_replayed_candidate_lineage()` is shared by more than partial progress recovery.

### 7.3 Later-boundary continuation after acceleration turnover

After committing an earlier boundary under A:

1. advance to a later active boundary;
2. change current realization to B;
3. resolve a surviving `(N, seed)` through the real `resolve_target_size_candidate_for_resume()` owner;
4. authenticate the historical trajectory/materialization/predecessor snapshot created under A;
5. construct the continuation workspace from the exact predecessor;
6. continue only the required missing later-rung work according to the accepted realization semantics.

The test must prove no competing continuation mechanism is introduced.

### 7.4 Tamper negatives at the assembled replay boundary

Representative negative cases should include:

- forged historical acceleration digest in trajectory;
- materialization config inconsistent with historical trajectory execution provenance;
- checkpoint/provider runtime evidence inconsistent with the accepted historical execution policy;
- prediction execution provenance inconsistent with authenticated provider;
- changed exact candidate membership;
- changed precision/batch geometry.

Each must fail before the cell is counted as reusable completion evidence.

### 7.5 Affected regression set

At minimum run, when touched/available:

- `tests/test_mlff_target_size_execution_p3b.py`;
- `tests/test_mlff_target_size_execution_p3e.py`;
- `tests/test_mlff_target_size_execution_p3f.py`;
- `tests/test_mlff_target_size_partial_boundary_resume.py`;
- P3 head/root reconciliation tests;
- later-rung resume/continuation tests;
- `tests/test_mlff_target_size_p4d_runtime_cutover.py`;
- target-size terminal/restart campaign tests;
- CLI `select-target-size` integration tests;
- acceleration/doctor/runtime realization tests if policy reconstruction is touched;
- materialization/config/provider/prediction replay tests if their contracts are touched.

After implementation, re-derive the final affected surface from the assembled diff. If the impact cannot be bounded confidently, run the broader target-size/campaign regression suite.

### 7.6 Production qualification

Production-scale GPU qualification is **deferred**.

Implementation acceptance requires bounded semantic and functional evidence only. The user's real campaign rerun after the fix is useful external confirmation, but it does not replace focused, affected-regression, and real-owner integration tests.

---

## 8. Implementation sequence and simplification/redesign triggers

### Stage A — canonical historical trajectory replay semantics

Implement the minimum shared candidate/restart refactor that distinguishes stable current-required policy from historical candidate-local acceleration realization.

Close with:

- focused P3-B replay matrix;
- true stale geometry/precision negatives;
- historical acceleration tamper negatives;
- stage-local affected candidate/context/coordinator regression;
- a Python-native simplicity check confirming the change consolidated current/historical replay meaning rather than adding parallel wrapper/state machinery.

Do not proceed with runtime-specific patches while the canonical replay owner remains semantically wrong.

### Stage B — all restart consumers and real-owner integration

Exercise the corrected shared replay path through:

- partial current-boundary recovery;
- committed-head/root reconciliation;
- later-rung continuation resolution.

Close with the fresh-process/bounded campaign integration scenarios above and affected P3/P4 regression. The integration evidence must execute the real production semantic owners; doubles may remain only below the expensive TRAIN2/EVAL2 boundary.

### Stage C — final assembled closure

After all executable edits:

1. reconcile implementation against this workplan and the still-binding parent partial-boundary-resume workplan;
2. confirm no recovery-specific weak validation path or duplicate historical policy authority was introduced;
3. confirm no schema/migration/destructive cleanup was added without redesign evidence;
4. confirm the assembled realization remains Python-native and no new language/runtime/accelerator layer was introduced without product need;
5. re-derive final affected surface from the assembled candidate, including callers/consumers of every refactored shared replay/policy owner;
6. run complete affected regression plus bounded real-owner integration on the assembled candidate;
7. confirm immutable conflict, exact P2 order, current-new-work behavior, and historical replay semantics remain intact;
8. use structural/semantic tooling where material to prove absence of a duplicate replay/policy path; tool absence does not waive the underlying uniqueness/simplicity claim.

### Active simplification trigger

If implementation starts accumulating separate “current policy,” “restart policy,” “recovery policy,” and “continuation policy” wrappers containing duplicated field reconstruction, stop and consolidate around one canonical seed-neutral template plus trajectory-aware historical realization owner.

This bug occurs because current and historical meanings are already being conflated. The repair should reduce that ambiguity, not institutionalize it with more parallel helpers.

Protocol 5.15 makes this an active Tier-2 simplification requirement: repeated wrappers, duplicated reconstruction, or synchronized representations around the same replay identity are not acceptable merely because they can be made to pass tests.

### Genuine redesign trigger

Stop implementation and reopen bounded Design if evidence shows historical acceleration execution semantics cannot be authenticated from existing durable parents or that acceleration turnover breaks scientific comparability under one screen context.

Do not resolve either case by guessing current values, deleting old evidence, or silently broadening/narrowing identity.

---

## 9. Explicit forbidden repairs

The following do not satisfy this workplan:

- skip `validate_target_size_candidate_trajectory()` only during partial recovery;
- catch the stale-realization exception and treat the cell as valid;
- compare only `T_N` and seed and ignore the rest of realization;
- remove `acceleration_realization_digest` from persisted trajectory identity;
- overwrite the trajectory's acceleration digest with the current one;
- regenerate/rewrite old trajectories before replay;
- delete progress/completions and retrain;
- force the current acceleration realization into the global execution-context digest without an explicit design reopen;
- declare acceleration realization execution-only without validating its scientific/provider consequences;
- accept old acceleration metadata without cross-checking materialization/checkpoint/provider/prediction evidence;
- create a recovery-only alternate optimizer-policy constructor;
- create parallel current/restart/recovery/continuation policy wrappers instead of consolidating the canonical owner;
- weaken immutable progress conflict detection;
- make current runtime state the authority for historical checkpoint/provider identity;
- change P2 ranking or fidelity policy to route around the restart failure;
- require the user to restart the whole target-size campaign from scratch as the normal fix;
- weaken or proxy around the real production restart/reconciliation owner merely to make bounded tests pass.

---

## 10. Design verdict

**Current implementation: NO-PASS for restart correctness.**

The previous partial-boundary scheduler repair correctly exposed already-published cells to deep authentication, but the shared trajectory replay owner incorrectly re-derives historical candidate realization using the mutable current acceleration realization. That rejects potentially valid durable evidence before recovery can reuse it.

**This workplan: PASS / implementation-ready under Protocol 5.15.0.**

The defect is bounded to historical candidate execution-realization replay under the existing P3 architecture. No target-size scientific-policy redesign, persistence migration, new restart architecture, or weakening of lineage validation is currently justified. Protocol 5.15 strengthens how the repair is implemented and accepted—especially active simplicity, Python-native realization, relation-first tool use, stage-local/final affected regression, and proxy-proof real-owner integration—without altering the inherited target-size scientific architecture.
