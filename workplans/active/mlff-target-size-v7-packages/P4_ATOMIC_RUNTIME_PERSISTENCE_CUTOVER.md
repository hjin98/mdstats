---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: implemented
package_revision: 7
amended_date: 2026-08-29
reopened_from_revision6_candidate: 142026700e2b1ba2f7597d5f236f66eb32f8ee29
revision6_baseline: P4_REVISION6_IMPLEMENTED_BASELINE.md
revision6_evidence: P4_REVISION6_IMPLEMENTATION_PROGRESS.md
revision5_baseline: P4_REVISION5_IMPLEMENTED_BASELINE.md
revision5_evidence: P4_REVISION5_IMPLEMENTATION_PROGRESS.md
revision4_baseline: P4_REVISION4_IMPLEMENTED_BASELINE.md
revision4_evidence: P4_REVISION4_IMPLEMENTATION_PROGRESS.md
entry_p3_closure_commit: 9d195807cff0bb8042f447ac33ceb0586ed708ac
compatibility_policy: destructive-generation-reset
implementation_closure: Complete revision-7 reclosure: P4-C3 production-STOR-owner first-publication race with control artifact deletion, P4-E3 exposure-time current-terminal authority sealing and stale snapshot view/report protection, and P4-G3 assembled regression/integration closed cleanly with 168 passed tests
reconciliation_reason: Revision 7 preserves the frozen parent, accepted P1-P3 semantics, the revision-6 canonical execution-root owner, and the revision-6 canonical current-terminal loader/full validation chain. Independent review found two remaining acceptance/consumer gaps: the revision-6 first-publication race still constructs CampaignOwnershipBoundary plus the retention fence directly in the child instead of traversing the production STOR ownership/removal path, and a legitimately validated terminal result can remain reusable for rendering/reporting after CampaignStore advances to a newer generation. Revision 7 repairs only those semantic-owner/currentness gaps. No target-size science, reducer, TRAIN2/EVAL2, checkpoint, provider, seed, path layout, persistence schema, or P5 scientific semantics are reopened.
---

# P4 revision 7 — production STOR owner and exposure-time currentness closure

## 0. Authority, preserved state, and scope

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. Cumulative P3 revision 7 through P3A9 remains accepted at `9d195807cff0bb8042f447ac33ceb0586ed708ac` and is not reopened.

`P4_REVISION6_IMPLEMENTED_BASELINE.md` preserves the exact revision-6 implementation package reviewed at `142026700e2b1ba2f7597d5f236f66eb32f8ee29`; `P4_REVISION6_IMPLEMENTATION_PROGRESS.md` preserves its evidence record. Revision-4 and revision-5 baselines/evidence remain preserved adjacent.

Revision 7 is a narrow implementation-repair overlay. It reopens only:

1. **P4-C3 — first-publication retention acceptance through the actual production STOR ownership/removal path**;
2. **P4-E3 — exposure-time CampaignStore currentness for every public/current terminal result view, write, report, and downstream current-result consumer**;
3. **P4-G3 — fresh assembled closure after C3/E3**.

The following revision-6 product work is **preserved and must not be redesigned merely to satisfy this review**:

- the single dependency-leaf canonical execution-root owner in `campaign_target_size_paths.py` and its reuse by runtime/retention;
- deterministic pre-`OPEN_ATTEMPT` root derivation and persisted locator semantics;
- `load_validated_target_size_terminal_result(...)` always loading the current CampaignStore revision first and treating `expected_revision` only as an assertion token;
- the full P1/P2/common-preparation/P3-context/head/reducer/terminal-projection validation chain;
- P4-A/P4-B state/CAS/destructive-cutover semantics;
- accepted P1-P3 science, reducer, checkpoint, replay, provider, and seed semantics;
- nonterminal target-size screen behavior except for affected regression.

P5 remains blocked until revision 7 receives both semantic/conformance and functional closure. The workplan remains bound to Protocol 5.8.0; do not silently reinterpret it under a later protocol version.

---

## 1. Independent-review findings being repaired

### 1.1 P4-C3 finding — the race test proves a hand-built fence, not production STOR

Revision 6 correctly drives real `prepare -> select-target-size`, wraps the real P3 initializer, calls that initializer exactly once, and targets the actual root argument observed from production runtime while CampaignStore is still `AUTHORITIES_BOUND` with no persisted execution root.

The cleanup child, however, constructs `CampaignOwnershipBoundary(...)` itself, injects `build_target_size_retention_fence(...)` itself, calls `destructive_authorization(...)` directly, and unlinks authorized files directly. That is below/beside the production STOR semantic owner. The test can remain green if production `_campaign_ownership_boundary(...)` stops installing the retention fence or if the real cleanup/removal helper bypasses that boundary.

The revision-6 helper also includes the root directory in its target list but only deletes `path.is_file()` targets, so it does not establish that production STOR would refuse destructive removal of the root directory itself.

This is an **acceptance-boundary nonconformance**, not a defect in the revision-6 canonical root constructor.

### 1.2 P4-E3 finding — a validated snapshot can outlive its currentness

Revision 6 correctly makes the canonical terminal loader establish currentness from CampaignStore before it returns a `ValidatedTargetSizeTerminalResult`.

Currentness is temporal, however. A result legitimately validated while terminal generation `g1` is current can be retained in memory. If scientific identity then changes and real `prepare` advances CampaignStore to `g2`, the retained `g1` validated object still matches its retained `g1` revision. The current terminal view builder can therefore render `g1_revision + g1_validated`, and `_report_terminal_state(g1_validated)` can report stale `g1`, without consulting CampaignStore again.

The missing invariant is therefore:

> A validated terminal object proves the snapshot that was current when validation ran; it is not perpetual authority that the same generation is still current when a public/current result is exposed.

This is a **current-result consumer/exposure defect**, not a reason to duplicate or weaken the revision-6 terminal loader.

---

## 2. Frozen revision-7 end state

### 2.1 Production STOR owns destructive authorization and removal

For the first-publication race, the semantic owner under acceptance is the complete production path:

```text
real select-target-size
  -> real build_screen_context
  -> canonical execution-root owner
  -> real initialize_target_size_screen publication
  -> independent process
       -> production config/path loading
       -> real CampaignStore
       -> production _campaign_ownership_boundary(...)
       -> production destructive cleanup/removal helper
```

The exact existing production function names may be reconciled if repository code has renamed them, but the semantic boundary may not be replaced by constructing `CampaignOwnershipBoundary`, a retention fence, or deletion logic in the test.

The production cleanup path must reject destructive removal of:

- the **actual observed execution-root directory** passed by runtime to the real P3 initializer; and
- representative freshly published P3 files under that root;

while the same cleanup path remains capable of deleting a deliberately prepared, unrelated, campaign-owned reclaimable control artifact. This control proves the test is not passing because cleanup was globally disabled or the boundary protects everything.

### 2.2 A current terminal result must re-establish currentness at exposure time

`ValidatedTargetSizeTerminalResult` remains a useful validated snapshot/transport object. It is **not** independently sufficient authority for a public operation whose semantic claim is “the current target-size result.”

Every public/current terminal exposure must establish CampaignStore currentness in that invocation immediately before exposing terminal authority. This applies to:

- terminal result-view generation/publication used as the current result file;
- CLI terminal stdout/reporting;
- repeated terminal `select-target-size` reload;
- initial terminal completion before its first terminal view/report publication;
- later P5-facing current-target-size consumption.

The preferred architecture is one public/current exposure owner or a small set of public entrypoints sharing one currentness owner:

```text
current terminal exposure(cfg, paths, store, optional expected token/snapshot)
  -> load_validated_target_size_terminal_result(...)
       -> reload actual current CampaignStore revision
       -> full existing P1/P2/common/P3/head/reducer/projection validation
  -> pure render/format from the returned currently validated result
  -> atomic file publication and/or stdout/downstream return
```

A pure renderer/formatter may accept a validated snapshot internally, but if it does not itself consult CampaignStore it must not be the public/current authority boundary. It may be private or explicitly historical/non-current. Public/current consumers must route through exposure-time validation.

### 2.3 No new authority or persistence topology

Revision 7 must not introduce:

- a second execution-root formula, pending-root manifest, mutable root registry, or new generation counter;
- a second terminal loader, reducer, replay engine, identity implementation, or compatibility fallback;
- a new persistence schema merely to track freshness of in-memory terminal snapshots;
- trust in dataclass construction/type identity as a security/currentness primitive;
- a broad new lock solely to hide the stale-object defect unless repository evidence demonstrates a real concurrency invariant that cannot be satisfied by the existing CampaignStore ownership/CAS model.

Currentness is established by consulting the existing authoritative CampaignStore and full canonical loader, not by synchronizing another copy of current state.

---

## 3. Stage P4-C3 — production STOR owner first-publication acceptance

### 3.1 Implementation obligations

1. Preserve `campaign_target_size_paths.py` as the single canonical root-construction owner and preserve runtime/retention imports from it.
2. Replace the revision-6 mandatory race child’s hand-built cleanup path with the actual production STOR ownership-boundary constructor and production destructive cleanup/removal helper.
3. The child must load the real campaign configuration/path objects by the same production configuration machinery used by STOR, then open the real CampaignStore at the configured state DB.
4. The child must call the existing production ownership-boundary assembly (currently expected to be `_campaign_ownership_boundary(cfg, paths, store)` or the exact owning successor in current code). The test may not manually inject `build_target_size_retention_fence(...)` into `CampaignOwnershipBoundary(...)`.
5. The child must invoke destructive attempts through the production cleanup/removal helper consumed by normal STOR cleanup. It may observe the report/result, but it may not replace production removal with direct `destructive_authorization`, `Path.unlink`, `Path.rmdir`, or `shutil.rmtree` logic.
6. Exercise both the actual observed root **directory** and representative freshly published P3 files. A directory target must genuinely reach the same production removal decision path; merely adding it to a list that only handles files is insufficient.
7. Add one unrelated, campaign-owned, demonstrably reclaimable control artifact outside the protected target-size evidence graph and submit it through the same production cleanup call. It must be removed/authorized while the observed target-size root/evidence are denied/skipped and remain intact.
8. Preserve existing containment, symlink-escape, external-path, reconciliation-frontier, publication-window, and lock-order behavior. Do not broaden the retention fence to make the acceptance test pass.

### 3.2 Mandatory proxy-proof race

The acceptance test must execute this sequence without substituting either semantic owner:

```text
real prepare
  -> CampaignStore current generation is AUTHORITIES_BOUND
     attempt=None, execution_root=None, adopted_head=None
  -> start real select-target-size through real parser/function path
  -> production build_screen_context derives root through canonical root owner
  -> synchronization wrapper calls real initialize_target_size_screen exactly once
  -> after real initializer returns, capture its actual root argument and published files
  -> wrapper blocks before OPEN_ATTEMPT can persist execution_root/attempt
  -> verify CampaignStore still AUTHORITIES_BOUND with no attempt/root/adopted head
  -> spawn independent process
       -> load real cfg/paths
       -> open real CampaignStore
       -> call production STOR ownership-boundary constructor
       -> call production cleanup/removal helper on:
            A. actual observed root directory
            B. representative first-publication files under it
            C. unrelated reclaimable campaign-owned control artifact
       -> A/B are denied/skipped and survive
       -> C is allowed/removed
  -> release wrapper
  -> real select-target-size resumes with bounded numerical seams
  -> execution reaches OPEN_ATTEMPT/reconciliation and preferably bounded terminal completion
```

### 3.3 Forbidden substitutions for the mandatory C3 claim

The mandatory C3 acceptance **must not**:

- instantiate `CampaignOwnershipBoundary(...)` directly in the spawned cleanup child;
- call `build_target_size_retention_fence(...)` directly in that child;
- call `destructive_authorization(...)` directly as the acceptance deletion decision;
- use direct filesystem deletion as a replacement for the production cleanup/removal helper;
- manually construct `.mdstats/target-size/g<N>` or otherwise calculate the target root separately from the observed runtime initializer argument;
- patch the canonical root constructor to return a test-selected path;
- replace the real P3 initializer rather than wrapping/calling it exactly once.

Direct fence/boundary tests may remain as focused unit coverage, but they do not close P4-C3.

Allowed test doubles remain bounded expensive trainer/inference seams below the already accepted P3/runtime owner.

### 3.4 C3 stage-local acceptance

At minimum rerun after the final C3 executable edit:

- `tests/test_mlff_target_size_p4c_cross_store_adoption.py`;
- affected P4-D runtime-cutover tests;
- affected P4-F STOR/storage/structural tests;
- storage accounting/reclamation/cleanup tests plausibly intersecting the production removal helper;
- canonical root uniqueness checks;
- existing external/symlink/reclaimable-residue negatives.

P4-C3 closes only if source inspection confirms the mandatory race traverses the production STOR owner and the test would fail if production boundary assembly omitted the target-size retention fence or production removal bypassed the boundary.

---

## 4. Stage P4-E3 — exposure-time current-terminal authority

### 4.1 Implementation obligations

1. Preserve `load_validated_target_size_terminal_result(...)` as the single canonical current-terminal loader and preserve its full revision-6 validation chain.
2. Treat any caller-supplied revision or prior `ValidatedTargetSizeTerminalResult` only as an expected/stale assertion token where useful; neither may substitute for reloading the current CampaignStore revision at a public/current exposure.
3. Introduce or refactor the **public/current terminal exposure owner** so it has access to `cfg`, `paths`, and `store` (or equivalent authoritative context), invokes the canonical loader in the same exposure call, and only then renders/writes/reports/returns the current terminal result.
4. Route both terminal branches of `select-target-size` through this exposure-time currentness owner:
   - repeated invocation when CampaignStore is already terminal;
   - initial terminal completion immediately after terminal projection commit.
5. Route the current terminal result-file writer through the same currentness contract. A stale validated snapshot alone must not be sufficient to create or overwrite the current `target-size-state.json` terminal view.
6. Route current CLI terminal reporting through the same currentness contract. A stale validated snapshot alone must not print selected N or terminal-scientific-failure output as current.
7. Define the P5-facing current-result API in the same way: when P5 later consumes selected N/T, it must invoke the canonical current exposure/load path rather than trusting a retained terminal snapshot or result-view file.
8. Keep nonterminal diagnostic view behavior compatible. Raw nonterminal revisions may still be rendered as non-authoritative progress views where current-terminal authority is not claimed.
9. If `build_target_size_result_view(...)`, `write_target_size_result_view(...)`, or `_report_terminal_state(...)` remain pure snapshot-formatting helpers, make their authority explicit through API visibility/naming/caller routing: they must not themselves be the public/current result boundary. No production current consumer may call them from a stale snapshot without first re-establishing currentness in the same invocation.
10. Do not duplicate P1/P2/P3 terminal validation to avoid a loader call. If optimization is justified, factor shared validation behind the canonical current loader/exposure owner while still reloading/confirming the current CampaignStore revision first.

### 4.2 Mandatory stale-snapshot acceptance — exact missing case

Use real CampaignStore transitions and retain a genuinely valid result, not a fabricated dataclass:

```text
real terminal generation g1
  -> call canonical loader while g1 is current
  -> retain g1_revision and legitimate g1_validated
  -> keep g1 immutable P3 evidence intact
  -> change a target-size scientific identity
  -> real prepare
  -> CampaignStore advances/binds nonterminal g2
```

From that exact state, prove all of the following.

#### A. Stale current-view/write exposure fails before publication

Invoke the public/current terminal view/write exposure while supplying `g1_revision`, `g1_validated`, or another supported expected token if that API permits one. It must reload current CampaignStore state and reject stale `g1` before publishing a terminal result.

Prove output atomicity against stale authority:

- either remove the current terminal result-view file before the stale attempt and assert it is not created; or
- record its exact pre-attempt content/digest and assert a stale attempt does not overwrite/change it.

A helper-only assertion that `g2_revision + g1_validated` mismatches is insufficient. The mandatory case is a self-consistent historical pair: **`g1_revision + legitimate g1_validated` after g2 is current**.

#### B. Stale current-report exposure fails before stdout

From the same `g1 -> g2` state, invoke the public/current terminal reporting/exposure route with the retained legitimate `g1_validated` if the API accepts it. It must reject after consulting current CampaignStore and must not print stale terminal authority.

Capture stdout and assert absence of stale terminal messages, including selected-N / “already selected and frozen” / “scientifically terminal” output.

A unit test that only passes a raw `TargetSizeTerminalProjection` to a type-checking formatter is useful focused coverage but does not close E3.

#### C. Unchanged current terminal still works with zero numerical work

For an unchanged terminal current generation, the public/current exposure route must:

- reload and authenticate current authority;
- render/write/report the same terminal projection;
- perform zero new TRAIN2/EVAL2/trainer/inference work;
- tolerate stale/missing rebuildable `current_head.json` exactly as accepted by P3A9/revision 6 while requiring immutable adopted evidence.

#### D. Existing corruption/invalidation matrix remains mandatory

Retain fresh affected regression for:

- missing immutable adopted head;
- corrupt immutable head/reducer evidence;
- tampered CampaignStore terminal state;
- changed optimizer seeds/training order;
- changed fidelity boundaries;
- target/evaluation policy or metric/practical-equivalence changes;
- neutral partition/protected-relation/hard-support changes;
- common preparation/training/execution-context changes;
- target-size-neutral CV-only/production-only changes remaining neutral and not advancing/retraining target-size screening;
- terminal scientific-failure reload and corruption negatives;
- stale/missing rebuildable `current_head.json`.

### 4.3 Structural/currentness acceptance

Inspect the assembled code to prove:

- exactly one canonical current terminal loader remains;
- current terminal view-file publication and CLI reporting route through exposure-time CampaignStore validation;
- no public/current terminal API treats `ValidatedTargetSizeTerminalResult` or raw `TargetSizeCampaignRevision` alone as perpetual current authority;
- no second currentness cache, mutable freshness flag, parallel generation registry, or result-file authority has been introduced;
- current terminal result files remain derived/non-authoritative and can be rebuilt only from currently authenticated CampaignStore + P3 authority.

### 4.4 E3 stage-local regression

At minimum rerun after final E3 executable edits:

- `tests/test_mlff_target_size_p4e_terminal_and_invalidation.py` including the exact stale-snapshot view/write/report cases above;
- affected P4-D `select-target-size` runtime tests;
- affected P4-F result-view/storage/structural tests;
- P3A9 resolver/reconciliation tests if current terminal exposure still resolves/reconciles adopted P3 evidence;
- any direct current-result consumer tests added for the P5-facing API seam.

---

## 5. Stage P4-G3 — assembled reclosure

P4-G3 is blocked until both P4-C3 and P4-E3 achieve semantic/conformance and functional closure.

After all C3/E3 executable edits are assembled, re-derive the affected surface and run fresh final regression. At minimum include the P4-A through P4-G affected suites and P3A9 where terminal resolver/reconciliation is intersected. Run the broader/full repository suite only if the final affected surface cannot be bounded confidently.

Mandatory assembled integration must include a bounded real-owner sequence equivalent to:

```text
real prepare
  -> bounded real select-target-size reaches terminal
  -> fresh-process/current terminal reload validates with zero retraining
  -> real production STOR cleanup executes without deleting current target-size authority
  -> second current terminal reload validates and returns identical N/T/reason
```

Also include assembled negatives for:

- missing/corrupt immutable terminal P3 evidence;
- changed target-size scientific identity requiring `prepare`/fresh generation;
- retained legitimate old-generation validated snapshot after a fresh generation becomes current;
- the first-publication STOR race through real production ownership/removal.

Structural/absence checks on the final candidate must confirm:

- one canonical execution-root construction owner;
- one canonical current-terminal loader/currentness validation core;
- no public/current stale-snapshot terminal exposure bypass;
- no duplicate root/generation/current-state authority;
- no V7/version-prefixed production code naming introduced by this repair.

Only after fresh P4-G3 closure may P4 metadata return to `status: implemented`/formal reclosure and P5 become eligible to begin.

Full long GPU/real-production qualification remains deferred to final release. Revision 7 requires bounded functional, persistence, concurrency, and real-owner acceptance only.

---

## 6. Implementation authority

### Frozen

- Parent scientific/architectural decisions and P1-P3 accepted semantics.
- Protocol binding at 5.8.0.
- Revision-6 single canonical execution-root owner and deterministic root layout ownership.
- Revision-6 canonical current-terminal loader and complete authority-validation chain.
- CampaignStore as sole current generation/revision authority.
- Production STOR boundary/removal path as the semantic owner for destructive first-publication acceptance.
- Exposure-time CampaignStore validation before any operation claims a terminal result is current.
- P5 remains blocked until formal P4 revision-7 reclosure.

### Delegated

- Exact module/function name for the current terminal exposure facade.
- Whether pure render/report helpers become private, explicitly historical/non-current, or accept authoritative context themselves, provided no public/current stale-snapshot route remains.
- Whether `expected_revision`/validated snapshot assertion tokens are retained for intra-command race detection; they remain assertions only.
- Synchronization details of the deterministic first-publication test, provided the real runtime initializer and real production STOR owner execute.
- Bounded fixture/data choices and numerical fakes below the accepted semantic-owner boundaries.

### Reopen only on evidence

Reopen design only if implementation evidence demonstrates one of the following:

- no reusable production STOR boundary/removal owner exists, such that satisfying C3 would require defining a materially new cleanup architecture;
- the existing CampaignStore/CAS ownership model cannot provide exposure-time currentness without a demonstrable race requiring a new concurrency contract;
- a preserved revision-6 root or terminal-loader design is shown materially incorrect rather than merely inconvenient to test.

If any trigger fires, reopen only the affected surface and preserve all unrelated accepted evidence. Do not broaden into P1-P3 science or P5 design by convenience.

---

## 7. Handoff closure

The revision-7 implementation contract is complete only if the implementer can recover the following without replaying this review:

```text
C3 protected concern:
  first-publication bytes survive the actual production STOR deletion path,
  not merely a hand-built equivalent boundary.

C3 required proof:
  real runtime root/P3 publication + independent process + production STOR boundary/removal,
  protected directory/files survive, reclaimable control is deleted.

E3 protected concern:
  “validated when g1 was current” does not mean “g1 is still current now.”

E3 required proof:
  retain legitimate g1 validated snapshot -> real prepare advances to g2 ->
  public/current view/write/report cannot expose g1 and produces no stale file/stdout.

Preserved design:
  one root owner + one canonical terminal loader + full P1/P2/P3 validation +
  CampaignStore current-generation authority + all accepted P1-P3 science.

Final closure:
  C3 + E3 stage-local regression -> fresh assembled G3 regression/integration ->
  formal P4 reclosure -> only then P5.
```

No proxy test, helper-only success, green regression suite, or metadata status may substitute for those semantic-owner outcomes.