---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 11
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
parent_plan_revisions: [9, 10]
reviewed_assembled_candidate: c76a53476596137aa34ec47bb68b7d1ab4bfe706
integration_audit_commit: 7a0cb21aaa368ac45b41af98e5df9d8e512e4c9d
highest_affected_domain: D4
challenge_state: D4_REPAIR_IMPLEMENTATION_READY
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# MLFF `pi_train` MVSEL2-chain restoration — Revision 11 implementation-ready D4 repair contract

## 0. Composition, authority, and implementation entry point

Revision 11 composes Revisions 9 and 10 and turns their six blocking findings into an implementation-ready repair contract. It does not reopen accepted D1, D2, or D3 authority.

Implementation SHALL start from this file on branch `design/mlff-pi-train-fps-diversity-restoration` at the current branch head. The implementer SHALL first read, in order:

1. `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_CURRENT.md`;
2. this Revision 11;
3. Revision 9 and Revision 10 for review provenance;
4. `docs/methods/mlff_target_training_order_scientific_method.md`;
5. `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`;
6. `docs/arch_manuals/mlff_training_data/45_target_training_order.md`;
7. the affected current general method/architecture/specification documents named below;
8. `PROJECT-ENGINEERING-MEMORY.md` entries applicable to single-authority ownership, fail-closed corruption, remove-first repair, qualification realism, and generalized lower-level fixes.

The repair is D4-only unless implementation evidence proves an actual upstream contradiction. A difficulty implementing the frozen contract is not permission to weaken or reinterpret it.

## 1. Frozen invariants

The implementation SHALL preserve all of the following:

- one exact `P_train` and one complete deterministic `pi_train`;
- exact nested `T_N = pi_train[:N]`;
- one sole fitted `TargetCoverageReference`;
- one canonical hard-obligation authority;
- one shared normal-path FEAS1/NEIGHBOR1 geometry construction;
- MVIDX as representation, not semantic ownership;
- one MVSEL2/REPAIR2 order owner with the same exact MVSEL2 continuation through all of `P_train`;
- independent MVQUAL configured-prefix admissibility;
- `prepare` as the sole live-input/build/publication orchestrator;
- prepared-generation + `CampaignStore` as the sole completed-generation currentness/adoption owner;
- pre-adoption MVSTATE/checkpoint state as subordinate reconstructible build state only;
- no target-size/P3/CV/replay/production feedback into target-order membership;
- production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.

Forbidden repair shapes include a fallback selector, old/new selector router, UID/scalar suffix, compatibility mode, second currentness database, checkpoint registry, new GC owner, semantic migration layer, duplicate advisory-lock implementation, or a special-case repair path that bypasses the existing objective.

## 2. Required repair order

Perform the repair in this dependency order so later tests exercise the final ownership/persistence topology:

1. **R11-A — consolidate the existing persistence/fencing primitive at a shared lower layer**;
2. **R11-B — make target-order completed-artifact publication immutable fail-closed**;
3. **R11-C — single-flight same-build `prepare` checkpoint mutation**;
4. **R11-D — enforce the frozen D2 universal structural-family catalog**;
5. **R11-E — remove the REPAIR2 semantic shortcut and invalidate buggy persisted build identities**;
6. **R11-F — reconcile current general D1/D2 and static documentation assertions**;
7. **R11-G — run focused real-owner and affected regression/closure validation**;
8. **R11-H — record representative current-scale complete-path performance/resource evidence**.

Do not reorder R11-B/R11-C after the concurrency tests: the tests must run against the final publication/fencing behavior, not a temporary topology.

## 3. R11-A — one shared persistence/fencing primitive

### 3.1 Problem

`mdstats/training_data/target_size_execution/persistence.py` already owns the repository's `fcntl.flock`-based advisory lock and durable directory-entry fsync logic, but importing that P3 target-size-execution module from P2 target-order preparation would invert the architecture. Copying the lock implementation would create duplicate infrastructure.

### 3.2 Required code change

Relocate, do not copy, the generic filesystem primitives to one lower shared training-data persistence module:

- `_lock_file_path`;
- `_FileLock`;
- `artifact_publication_lock`;
- `fsync_parent_directory`.

Preferred destination: `mdstats/training_data/persistence.py`, because these are training-data-wide filesystem primitives and have no target-size/P3 semantics.

Then:

- change `mdstats/training_data/target_size_execution/persistence.py` to import those primitives from the shared module;
- change target-order publication/preparation to import the same shared primitive directly;
- update all repository-internal imports in the same change so there is one implementation, not a compatibility re-export stack;
- leave target-size-specific typed/bytes publication functions in `target_size_execution/persistence.py` unless they are themselves truly generic and moving them reduces code without creating an import cycle.

No new lock protocol, lock database, lease table, or owner-specific duplicate lock class is permitted.

### 3.3 Validation

Existing target-size publication/concurrency tests must remain green. Add only the target-order-specific concurrency tests required below; do not create a second generic locking test framework if existing persistence tests already exercise the primitive.

## 4. R11-B — immutable target-order publication must fail closed

### 4.1 Owning code

Primary owner:

- `mdstats/training_data/target_order/artifact_store.py::publish_artifact_directory`

Callers include completed reference, geometry/NEIGHBOR1, MVIDX, MVSTATE checkpoint, and build publication. Completed reference/geometry/MVIDX/build destinations may become protected by a prepared generation and therefore may not be deleted in place by ordinary `prepare`.

### 4.2 Required code change

Rewrite `publish_artifact_directory` to strict create-or-verify semantics using the shared `artifact_publication_lock(destination)`:

1. build the complete attempt-owned temporary directory exactly as today;
2. fsync files/manifests as today;
3. acquire the destination advisory lock;
4. under the lock, if `destination` exists:
   - read and authenticate its manifest/schema;
   - require the existing `content_digest` to equal the attempt result;
   - call `verify_existing` and require it to pass;
   - on success, delete only the attempt temporary directory and return the existing object;
   - on any corruption, schema mismatch, content conflict, or verification failure, raise `TargetOrderArtifactStoreError` and leave the existing destination byte-for-byte untouched;
5. if `destination` is absent, atomically rename the completed temporary directory into place;
6. call shared `fsync_parent_directory(destination)` after successful publication;
7. remove the current retry branch that executes `shutil.rmtree(destination, ignore_errors=True)`.

There must be no normal `prepare` path that repairs a corrupt completed content-addressed destination by overwriting the same path. If the object is unreachable, the existing storage/cleanup owner may retire it under its own reachability rules; `prepare` does not acquire that ownership merely because it discovered corruption.

MVSTATE checkpoints remain reconstructible pre-adoption state. They may be discarded only under the same-build fence specified in R11-C; do not generalize completed-artifact deletion from checkpoint behavior.

### 4.3 Required falsification

In `tests/test_mlff_target_order_real_owner.py` or the existing target-order persistence test owner, add a focused test that:

- publishes a real target-order artifact;
- corrupts an authenticated member/manifest at the completed destination;
- attempts same-identity publication/reuse;
- proves the operation fails closed;
- proves the original corrupt destination was not deleted/replaced;
- proves no partially published alternative destination becomes current.

Also retain the existing ENOSPC/write-failure test proving attempt-owned partial output is cleaned without publishing a destination.

## 5. R11-C — same-build `prepare` must be single-flight

### 5.1 Owning code

Primary owner:

- `mdstats/training_data/target_order/preparation.py::prepare_target_training_order`

Subordinate checkpoint mutation owners:

- `mdstats/training_data/target_order/state.py::write_selection_checkpoint`;
- `restore_latest_checkpoint`;
- `prune_checkpoints`.

Current checkpoint roots are deterministic scientific identities:

- `root/checkpoints/<pure_identity>`;
- `root/checkpoints/<suffix_identity>`.

They are safe only if exactly one active builder mutates a given prospective build at a time.

### 5.2 Required code change

Implement a per-`build_identity` single-flight fence without changing scientific identity:

1. preserve the current cheap unlocked fast-path: if `build_directory` exists and `_read_build` authenticates it, return it;
2. on a cache miss, acquire the shared advisory lock for the prospective `build_directory` (or an adjacent deterministic lock path derived from that exact build destination);
3. **after acquiring the lock**, re-check `build_directory` with `_read_build`; if another attempt completed it while this attempt waited, return the authenticated completed build without creating selector scratch/checkpoints;
4. only the lock holder may create attempt scratch and enter `_build` for that `build_identity`;
5. hold the fence through pure-checkpoint restore/write/prune, REPAIR2, suffix-checkpoint restore/write/prune, final build publication, and build-owned checkpoint cleanup;
6. release the fence only after the completed build has been published or the attempt has failed and its own scratch has been removed.

Do **not** add attempt identity to scientific `selection_identity`, because restart identity is scientific/build identity and worker/attempt identity is execution-only. Do **not** create per-attempt checkpoint stores that then require merging/adoption. Serialization of identical-build mutation is simpler and preserves the accepted D3 topology.

`restore_latest_checkpoint` and `prune_checkpoints` may retain reconstructible-state deletion, but their shared-root destructive use from `prepare` must occur only while the same-build fence is held. Update docstrings/comments to state that ownership contract rather than adding an internal second lock.

Different `build_identity` values must remain concurrently executable; this is not a campaign-wide writer lock.

### 5.3 Required falsification

Add `@pytest.mark.real_target_order` coverage using the existing real-owner fixture:

- launch two simultaneous calls for the exact same prospective build identity;
- force overlap around selector/checkpoint publication with a deterministic test synchronization point, not sleeps as the correctness oracle;
- prove exactly one attempt performs mutable selector/checkpoint construction while the waiter rechecks and reuses the completed build;
- prove neither attempt deletes/prunes another active attempt's state;
- prove both callers return the same completed build/order/content identities;
- repeat with an interruption of the first lock holder before completion and prove the second holder resumes/reconstructs safely after lock release;
- prove different build identities are not unnecessarily serialized if the existing test harness can observe that without timing-sensitive assertions.

## 6. R11-D — enforce the frozen universal structural-family catalog

### 6.1 Frozen numerical authority

Scoped D2 requires the universal structural semantic families:

```text
pair_distance
radial_environment
coordination
connectivity
chemical_environment
local_density
angular_environment
orientational_order
```

The general phase/geometry provider may control how universal structural evidence is produced, but it may not silently reduce this frozen target-order family catalog unless D1/D2 explicitly defines an applicability exemption. No such phase-specific exemption exists in the accepted scoped D1/D2 baseline.

### 6.2 Owning code

- `mdstats/training_data/campaign_target_size_runtime.py::_build_current_target_training_order`;
- `mdstats/training_data/target_order/coverage_reference.py::_structural_families`;
- `build_target_coverage_reference`.

### 6.3 Required code change

At the target-order structural-input boundary:

1. continue deriving the current phase/geometry structural policy where material contracts exist so accepted local-structure/aggregation/provider semantics remain available;
2. before building the target-order structural catalog, replace only `enabled_feature_families` with `TargetCoveragePolicy().required_structural_feature_families` (or the single exported frozen constant used by that policy);
3. keep `materialize_atomic_environments=False` as the current target-order execution choice;
4. do not invent phase-specific exceptions or silently enable unrelated profile/foundation providers.

At `TargetCoverageReference` construction:

1. after `_structural_families` has projected exact `P_train`, compute the represented structural semantic-family set;
2. compare it to `policy.required_structural_feature_families`;
3. if any required semantic family has no valid retained reference family, fail preparation with `TrainingDataInputError` naming the missing semantic families;
4. do not weaken `minimum_family_elements`, thresholds, extent requirements, or synthesize dummy/constant dimensions to make the check pass.

A specific group/family projection with fewer than the D2 minimum reference elements remains invalid/inapplicable under the existing `_build_family` rule; the new completeness check prevents all valid instances of a required semantic family from disappearing silently.

Because the target-order structural policy digest participates in `structural_input_identity`, forcing the frozen family set naturally invalidates builds produced under a narrowed provider policy. Do not add a second migration/version router for this change.

### 6.4 Required falsification

Add real-owner tests that:

- construct a material/phase plan whose general provider policy would omit at least one frozen target-order family (the current molecular/gas orientational-order case is an appropriate real contract witness if fixture construction is practical);
- prove the target-order structural input still requests the complete frozen family set;
- prove a catalog genuinely unable to produce one required semantic family fails closed with the family named;
- prove a complete catalog still builds the exact reference and preserves current identities under worker variation.

## 7. R11-E — restore exact D2 REPAIR2 frontier semantics

### 7.1 Owning code

- `mdstats/training_data/target_order/repair.py::_Frontier`;
- `_build_frontier`;
- `build_repair_plan` / `_best_proposal` call site;
- `REPAIR2_VERSION` / `TargetMultiViewRepairPolicy.authority_version`.

### 7.2 Required code change

Delete the historical shortcut rather than compensating for it:

1. remove `_Frontier.proposal_possible`;
2. remove:

```python
possible = hard_pending or max(totals[c] for c in candidates) > tolerance
```

and its historical-shortcut comment;
3. return the frontier after the existing hard-gain, bottleneck-gain, and total-gain filters;
4. whenever a removal shortlist/frontier exists, invoke the existing `_best_proposal` path unconditionally;
5. retain the existing hypothetical balance, representative-gain-after-removal, diversity, UID, coverage-non-regression, and `strictly_better(J_before, J_after)` gates exactly;
6. do not add a zero-coverage special path, compatibility flag, or alternate objective.

### 7.3 Persisted-identity invalidation

The current buggy implementation serializes:

```text
REPAIR2_VERSION = mdstats.target-order.repair2.configured-shell.v1
```

and `target_order_build_identity()` includes `TargetMultiViewRepairPolicy().to_dict()` through `target_order_method_identity()`.

Bump the REPAIR2 authority/cache version to a new value (for example `mdstats.target-order.repair2.configured-shell.v2`) in the same repair commit while keeping the frozen numerical constants unchanged. This is a D4 compatibility invalidation for products generated by the defective v1 concretization; it is **not** a D2 semantic revision. The bump ensures `prepare` cannot reuse a pre-fix build whose repaired prefix may differ from the corrected D2 result.

Do not accept/read the old REPAIR2 policy as current merely to preserve cache reuse. Old completed generations remain historical under their own immutable ancestry; fresh current preparation rebuilds under v2.

### 7.4 Required falsification

Extend `tests/test_mlff_target_order_real_owner.py` with focused real-owner fixtures:

- hard deficit is zero;
- every available replacement has total new coverage within the accepted zero tolerance;
- removal is unique-mass/hard-safe and family coverage is unchanged;
- one replacement strictly improves `U_rep` and therefore must swap;
- a control with no strict `J` improvement performs no swap;
- worker/completion-order variation yields the identical repair trace;
- if straightforward with the same fixture, add a balance-only strict improvement witness, but do not invent new authority solely to create it.

Also assert that the new method/build identity differs from the old REPAIR2-v1 identity.

## 8. R11-F — reconcile current documentation and static assertions

### 8.1 General D1 contradiction

`docs/methods/mlff_scientific_method.md` currently retains target-order prose stating that configured-prefix qualification is only label usability plus explicitly declared hard-support obligations and that coverage measures do not become qualification gates. That text is superseded by the accepted scoped target-order D1.

Replace only the superseded target-order construction/qualification prose with a concise delegation to:

- `docs/methods/mlff_target_training_order_scientific_method.md`.

Preserve the general paper's unaffected `U_size -> P_train + M3`, `pi_eval/M1/M2/M3`, P3 training/evaluation/reducer, CV, replay, production, and downstream method authority. Do not duplicate the scoped MVSEL2 method back into the general paper.

### 8.2 General D2 contradiction

`docs/methods/mlff_numerical_algorithmic_method.md` currently retains:

- §6.1 condition-balanced priority ordering as the target-training order construction; and
- §7 hard-support-only prefix qualification.

For `TargetTrainingOrder/pi_train`, replace those superseded parts with a concise delegation to:

- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

Keep the condition-balanced rule only where it remains current for `pi_eval`/unaffected consumers, with wording that cannot be read as the current `pi_train` algorithm.

### 8.3 Architecture/spec/help/static closure

Rerun the exact CLI/spec/help/documentation closure batch recorded in the D4 handoff. Capture the eight previously failing node IDs and assertion mismatches. For each failure:

- if the assertion encodes retired schema/topology/provenance, update or remove that stale assertion at its real documentation/test owner;
- if the failure reveals a current-source contradiction, repair the current source rather than weakening the test;
- no `xfail`, `skip`, warning filter, baseline whitelist, or compatibility text that presents retired behavior as current;
- regenerate generated PDF siblings only after the Markdown/current source is correct.

The closure batch must finish with zero unresolved affected failures.

## 9. R11-G — validation matrix and evidence boundary

### 9.1 Owner-level target-order evidence

All claims about the real target-order chain must use `@pytest.mark.real_target_order` tests or direct real-owner execution. The repository's ordinary `test_mlff_*` harness substitutes `_build_current_target_training_order` unless marked real-owner; those tests remain useful downstream compatibility evidence but cannot prove MVSEL2/REPAIR2/NEIGHBOR/MVQUAL behavior.

At minimum run and record:

- the complete `tests/test_mlff_target_order_real_owner.py` suite after adding R11 tests;
- focused artifact-store/persistence tests affected by R11-A/B;
- current target-size prepared-generation/currentness/storage tests;
- manual `select-target-size N` proof that selector modules/checkpoints/MVIDX are not loaded or rebuilt downstream;
- automatic diagnostic routing against the same compact prepared P2 definition;
- CV/post-selection frozen-prefix lineage checks;
- package/install/native exact-equivalence tests already required by Revision 9/10 where native execution remains retained;
- the exact static/documentation closure batch with zero unresolved failures.

Do not count monkeypatched downstream suites as selector correctness evidence.

### 9.2 Falsification conditions

The repair remains NO-PASS if any of these are observed:

- zero-new-coverage late-objective repair still cannot occur;
- pre-fix REPAIR2-v1 completed target-order products can be reused as current after the fix;
- an accepted required structural semantic family can silently disappear;
- two same-build `prepare` attempts can concurrently mutate/prune/delete the same checkpoint root;
- a corrupt/conflicting completed target-order destination is deleted or overwritten by ordinary `prepare`;
- manual/automatic downstream selection reconstructs target-order science;
- worker/native/restart variation changes order, repair trace, MVQUAL, or public identity;
- static current documentation continues to describe condition-round-robin/hard-support-only `pi_train` as current.

## 10. R11-H — representative current-scale complete-path qualification

Revision 9's performance blocker remains open until real evidence is recorded. Do not create a new benchmark framework. Use the smallest existing current campaign/data substrate that is demonstrably representative of the accepted target-order workload, and record its exact configuration/input identities.

For a fresh real-owner `prepare` and authenticated reuse/reload, record:

- `|P_train|` and configured candidate sizes;
- family, witness, obligation, and NEIGHBOR edge counts;
- TargetCoverageReference wall time and peak RSS;
- shared FEAS1/NEIGHBOR1 wall/RSS/I/O and proof that normal preparation constructs exact geometry once;
- MVIDX adoption/inversion wall/RSS/scratch/final bytes;
- configured-prefix MVSEL/REPAIR wall time and evaluated sparse edges;
- Phase-A -> Phase-B transition and lazy refresh/certification behavior;
- native preflight probe widths/timings and chosen effective width under the accepted `1.05` speedup / `0.05` economical-tolerance policy;
- post-final-repair state-reconstruction cost;
- suffix rank count/wall/edges through complete `|P_train|` where `|P_train| > N_max`;
- complete-order wall/RSS/I/O;
- checkpoint write/read/recovery cost, including interruption/resume beyond `N_max` where applicable;
- peak mapped file descriptors and final/scratch disk footprint;
- immutable publication, fresh-process reload, and downstream no-scientific-rebuild behavior.

Compare fresh vs resumed and serial/reference vs selected optimized/native execution wherever the accepted D3 gate requires equivalence. The final order, configured repaired prefixes, repair trace, MVQUAL, and public scientific identities must be invariant.

If the representative run reveals a material performance defect, first prove the accepted optimized lazy/native/OOC path is actually active. Repair by simplifying/rewiring that path. Do not weaken D1/D2, lower coverage/support requirements, truncate the order, append a fallback suffix, or add an alternate selector.

Production-scale GPU qualification remains deferred and is not part of this target-order CPU/current-scale closure.

## 11. Required implementation evidence record

Update the existing D4 implementation handoff/evidence record, or add one bounded Revision-11 D4 repair evidence record under this workplan family, with:

- implementation commit SHA(s);
- exact changed-file list;
- mapping R11-A through R11-H -> code/tests/evidence;
- test commands and exact pass/fail counts;
- the eight reconciled static failure IDs and their dispositions;
- representative current-scale fixture/configuration identity and metrics;
- explicit statement of whether native execution remained useful/active under the accepted preflight policy;
- explicit statement that no fallback selector/router/currentness/GC/migration owner was added;
- any newly exposed upstream contradiction as a Protocol challenge rather than an implementation workaround.

The evidence record is evidence, not new method/architecture authority.

## 12. Completion / re-review gate

Implementation is ready for independent assembled-candidate re-review only when all of the following are true:

1. R11-A leaves exactly one generic advisory-lock implementation at a lower shared layer.
2. R11-B never deletes/replaces a corrupt/conflicting completed target-order destination during ordinary publication.
3. R11-C proves same-build concurrent preparation is single-flight and crash/restart safe without campaign-wide serialization.
4. R11-D proves every frozen D2-required structural semantic family is requested and missing required families fail closed.
5. R11-E deletes `proposal_possible`, exercises later-objective zero-new-coverage repair, and invalidates REPAIR2-v1 build reuse.
6. R11-F removes contradictory current general D1/D2 target-order claims and the affected static/docs batch is fully green.
7. Existing real-owner exactness, shared-geometry, independent-MVQUAL, post-repair reconstruction, complete-suffix, OOC/FD, package/native, prepared-generation/currentness, manual-selection, automatic-screen, and downstream lineage tests remain green.
8. R11-H representative current-scale complete-path evidence is recorded and satisfies the accepted D3/Revision-8 resource/performance contract, or any failure is routed to the owning layer before re-review.
9. No new fallback selector, alternate suffix, second currentness/checkpoint system, duplicate lock implementation, migration layer, or cleanup authority exists.

Until all nine conditions hold, the workplan remains **ACTIVE / D4 NO-PASS** and must not be closed or archived.
