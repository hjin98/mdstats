---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R8
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
package_revision: 8
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: 2740ed6e0c638808306bcd889119bb6d240658b4
reviewed_candidate_tree: 387313916f3e8a20cb48b206a18e94255717dd7e
amends:
  - P6_REVISION_3_BASE.md
  - P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md
  - P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md
  - P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md
  - P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md
precedence: this amendment overrides earlier P6 text only where explicitly stated; all other obligations remain binding
successor_p7_workplan: CODE-MLFF-TARGET-SIZE-V7-P7
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P6 revision 8 amendment — precise blocker-repair instructions

## 1. Purpose and review disposition

Independent review of the revision-7 implementation found three remaining blockers on the reviewed candidate `2740ed6e0c638808306bcd889119bb6d240658b4`:

1. fresh current DATA5 still constructs and persists pre-selection cross-validation plans, leaving two CV owners;
2. the public current storage surface still executes and documents the retired STOR4/STOR5 `evaluate`/`verify`/DATA7-DATA8 capability model instead of a conservative transitional P6/P7 boundary;
3. the mandatory compatibility driver still labels a second reopen of a P5A6-produced workspace as `P6 -> P6` restart and therefore does not establish the required independent final-P6 producer lineage.

The implementation also introduced a useful derived `FinalProductionCompletion` resolver, but its acceptance evidence remains incomplete and its exposed `content_digest` currently aliases the final-plan digest rather than representing completion evidence.

These are **implementation nonconformances against the already accepted P6 architecture**. This amendment does not reopen target-size science, P1-P5 decision semantics, P7 design, or the post-P7 storage reset. It exists to remove implementation ambiguity and make the next repair round mechanically precise.

## 2. Frozen repair end state

The repaired P6 candidate must have exactly this ownership direction:

```text
P1 / DATA5 current write
    -> neutral evidence roles, protected relations, independence/leakage facts
    -> NO current CV folds, fold count, CV partition seed, or held-out CV plan

P4
    -> one current N_selected + exact T_selected

P5 post-selection CV
    -> consumes current T_selected + P1 protected relations
    -> constructs every configured fold inside T_selected
    -> owns fold_count, partition_seed, CV seeds, fold evidence, acceptance

P5 final production
    -> publishes a plan first
    -> becomes complete only after every required run has authenticated evidence

transitional P6/P7 storage
    -> read-only accounting + independently safe low-consequence cleanup
    -> no evaluate/verify/DATA7-DATA8 destructive authorization
    -> no current-generation recompute/compact/archive/dedup policy claim

mandatory compatibility qualification
    A. exact P5A6 producer -> final P6 reopen
    B. fresh final-P6 producer -> final P6 close/reopen/restart
    C. retired V5/V6 state -> reject-before-reuse
```

The post-P7 storage package remains the only owner of the future cross-owner retention/archive/dedup/admission design.

## 3. R8-A — remove current pre-selection CV construction from DATA5

### Concern / rationale

Revision 7 removed configurable CV fields from preparation identity, but the current `prepare` path still instantiates a fixed three-fold DATA5 policy and `build_data5_partition_bundle()` still calls `build_cross_validation_plans()` and persists `cross_validation_plans`. That preserves the wrong semantic owner even if the values are now hard-coded.

### Required end state

A **fresh current P6 preparation** must not create, persist, expose, hash into current P1 identity, or use any CV fold plan before `N_selected/T_selected` is frozen.

DATA5 remains current only for neutral/statistical responsibilities needed by later owners: partition units or equivalent independence units, outer evidence roles that are genuinely pre-selection, purge/exclusion relations, protected event/correlation relations, blinding boundaries where still current, and leakage facts that do not construct post-selection folds.

### Required code consequences

1. In `mdstats/training_data/_campaign_cli_core.py::_prepare_catalog()`:
   - remove the fixed `PartitionRoleBudgetPolicy(cross_validation_folds=3, ...)` current-authority use;
   - remove the fixed `PartitionPolicy(..., cross_validation_seed=104729)` **when that field is CV-specific**;
   - do not replace either with a different hard-coded CV count/seed;
   - current preparation must construct only the neutral DATA5/P1 policy needed for pre-selection evidence roles and protected relations.

2. In `mdstats/training_data/data5_bundle.py` and its owned policy classes:
   - fresh current DATA5 serialization must not contain `cross_validation_plans` as a current field;
   - fresh current DATA5 construction must not call `build_cross_validation_plans()`;
   - current DATA5 accessors must not expose a current `cross_validation_for_domain()` or equivalent fold authority;
   - current DATA5 policy identity must not include `cross_validation_folds`, `checkpoint_monitor_minimum_units_per_fold`, `cross_validation_seed`, or another renamed equivalent whose only purpose is post-selection CV.

3. Compatibility disposition:
   - exact accepted P5A6 DATA5 payloads that already contain legacy fold fields/plans may remain readable **only through a compatibility reader capable of preserving and authenticating their original digest**;
   - those legacy folds are inert compatibility payload, not a current P5 plan and not an input to P2/P3/P4 or current P5 planning;
   - fresh final-P6 writes must use a current CV-neutral representation/schema;
   - do not rewrite a P5A6 workspace merely to strip its historical DATA5 fields.

4. If a currently named CV field is discovered to serve a genuinely neutral P1 algorithm as well:
   - split the responsibility rather than silently retaining the CV name;
   - the retained current field must receive a neutral semantic name and owner;
   - changing `[post_selection.cv]` must not alter that neutral field or any P1-P4 identity.

5. P5 remains the sole fold constructor:
   - `build_post_selection_cv_plan()` or its current equivalent must derive folds from the authenticated `CurrentSelectedTrainingContext.selected_membership` and current `[post_selection.cv]` policy;
   - it must enforce the P1 protected-relation/purge/exclusion constraints inside exactly `T_selected`;
   - if configured `K` is infeasible for the selected set, `cross-validate` fails as a post-selection methodological/precondition outcome. It must not trigger re-selection, change N, or cause P1 to pre-reserve a different fold topology.

### Expected affected files/surfaces

At minimum inspect and reconcile:

- `mdstats/training_data/_campaign_cli_core.py`
- `mdstats/training_data/role_budget.py`
- `mdstats/training_data/partition.py`
- `mdstats/training_data/data5_bundle.py`
- `mdstats/training_data/campaign_post_selection_runtime.py`
- serializers/loaders for persisted DATA5
- all tests/specs/docs that currently call DATA5 a CV-plan owner.

Do not delete generic lower-level partition helpers solely because their names contain CV if they remain an independently supported library API. The hard requirement is that **the current campaign P1/DATA5 path neither creates nor owns post-selection folds**. Any retained generic/legacy API must be structurally outside the current P1-P5 authority chain and documented accordingly.

### Acceptance evidence

The following are required on the real current owners:

- fresh `prepare` produces a DATA5/current neutral record with no serialized current CV plan/fold count/CV partition seed;
- structural source assertion: the current campaign `prepare -> DATA5` path cannot reach `build_cross_validation_plans()`;
- mutate only `[post_selection.cv].fold_count`, `partition_seed`, or CV `seeds`: P1 preparation digest, P3 generation/head, P4 selected binding and exact `T_selected` remain current/unchanged; P5 CV/final descendants change or invalidate as appropriate;
- two different current P5 `fold_count`/`partition_seed` values produce different P5 plans over the same frozen `T_selected` while P1-P4 identities remain identical;
- fold leakage/protected-relation tests execute the real P5 planner, not a DATA5 legacy fold helper;
- authenticated P5A6 -> P6 reopen remains unchanged and does not promote its legacy DATA5 folds into current P5 authority.

### Anti-shortcut

It is **not** sufficient to set old DATA5 CV fields to zero, three, `None`, or a fixed seed while continuing to serialize/build fold plans. The current fold object itself must move to P5 ownership.

## 4. R8-B — finish final-production completion as a real owner boundary

### Concern / rationale

The new `resolve_current_final_production_completion()` correctly distinguishes missing required run evidence from a published final plan. However, P6 acceptance still authenticates only the final plan in important restart paths, and `FinalProductionCompletion.content_digest` currently aliases `plan.content_digest`, which makes the exposed identity unable to distinguish authorization from completed evidence.

### Required end state

P6 has one derived, owner-authenticated completion projection that exists only when **every required final run for the exact current plan** has valid current run evidence.

It is not a second mutable persisted authority. It is derived from the current plan plus the authoritative immutable run-evidence records.

### Required code consequences

1. Keep `resolve_current_final_production_plan()` as plan/currentness resolution only.

2. `resolve_current_final_production_completion()` must, for each `required_final_seed` in plan order:
   - rebuild/resolve the exact expected `FinalProductionRunPlan`;
   - load the corresponding immutable run evidence through the production run-evidence owner;
   - verify `run_plan_digest`, selected binding, method/policy lineage, seed/run identity, and integrity already required by the run-evidence schema;
   - return incomplete (`None`) only for genuinely missing required evidence;
   - fail closed on corrupt, mismatched, stale, duplicate/ambiguous, or semantically invalid evidence rather than treating it as missing-success.

3. Completion identity:
   - if `FinalProductionCompletion` exposes `content_digest`, it must be a digest of a completion payload, not the plan digest;
   - the payload must bind at minimum a completion schema/version, `plan.content_digest`, and the ordered required run-evidence identities/digests (and seed/run-plan identity where not already unambiguous);
   - alternatively remove the misleading completion `content_digest` property entirely if no consumer needs one. Do not expose `plan_digest == completion_digest` as two differently named semantic identities.

4. Public lifecycle:
   - `status`, `advance`, `_current_lifecycle_is_complete`, storage protection, compatibility qualification, and P7 handoff checks must consume the completion resolver where they claim final production is complete;
   - a durable stage marker may summarize completion after the owner resolves it, but stage state alone cannot satisfy completion.

5. Do not implement P7 `FinalProductionPublication` in P6. P6 completion proves required fresh training finished; P7 later freezes the deployable publication/member decision.

### Mandatory interruption/restart cases

Use a production policy with at least two required final seeds so partial completion is observable.

- **plan only:** publish current final plan, stop before first required run evidence; close/reopen -> completion absent, status WAIT/incomplete, `advance` selects `train-production`;
- **proper subset:** complete exactly one of >=2 required seeds, stop; close/reopen -> completion absent; rerun executes only missing run(s) and never repeats authenticated completed runs;
- **corrupt/mismatched evidence:** wrong `run_plan_digest`, truncated/invalid evidence, or evidence copied under another required run root cannot satisfy completion;
- **all complete:** completion exists and binds every required run in deterministic plan order; status is complete and `advance` has no P6 scientific next operation;
- **reopen:** completion identity/evidence set is stable across a separate process/store reopen.

The real P5 planner, run loop, evidence persistence, resolver, status, and advance paths must execute. Expensive MACE training/inference may remain replaced below the accepted numerical seams.

## 5. R8-C — quarantine retired STOR semantics for the current generation

### Concern / rationale

Current code still executes `_effective_stage(..., "evaluate")` and `_effective_stage(..., "verify")` inside manual reclamation, still targets `evaluation-capsules`, `model-sweep`, true-label replay and DATA7/DATA8 hot materializations, and current docs still claim the STOR1-STOR5 roadmap is complete/current. Wrapping those lookups in `try/except` only makes the stale architecture fail closed in some cases; it does not remove it from current destructive authorization.

### Frozen transitional public behavior

Until `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` is implemented after P7, a current P6/P7 workspace supports only:

```text
storage report                       read-only
storage cleanup                      conservative current-safe cleanup
storage cleanup --tier safe          zero-capability-loss owner-proven cleanup
storage cleanup --tier cache         independently reconstructible current cache eviction only
```

Consequential historical tiers/operations are **not current-generation features**:

```text
recompute
compact
archive-as-reclamation
current-generation deduplicate/apply
current-generation archive create/restore
```

For a current P3/P5 generation they must either be absent from the current parser/help or raise one clear fail-closed `CampaignCliError` explaining that consequential storage transformation is deferred to the post-P7 storage reset. Do not silently execute old STOR policy.

Read-only verification of an already existing archive may remain if it has no ability to mutate/currentize campaign state and does not claim current semantic alignment.

### Required code consequences

1. Remove current destructive authorization based on:
   - `evaluate`, `verify`, `preflight`, SELECT2 or renamed aliases;
   - DATA7/DATA8 rematerialization capability;
   - old protocol freeze / selected-checkpoint / verification replay semantics;
   - path-only assumptions such as `evaluation-capsules`, `evaluation-predictions`, `model-sweep`, `true-label-replay`, `runs/.../models`, or `paths.data` being safe because of historical stage completion.

2. In `_campaign_cli_core.py`:
   - `_manual_reclamation_add_recompute_tier()` and `_manual_reclamation_add_compact_tier()` must not remain reachable current-generation authorization paths;
   - `_MANUAL_RECLAMATION_TIERS` / `_MANUAL_CAPABILITIES` must no longer advertise DATA7 reselection, verification replay, selected production checkpoint, old protocol freeze, or equivalent historical capabilities as current V7 policy;
   - current automatic cleanup must not delete `evaluation-graphs` or another retired path family merely because the path exists; path classification cannot substitute for a current owner proof;
   - remove hidden pre-0.20.117 top-level storage aliases unless a current supported compatibility contract is demonstrated. The normal current entry remains `storage ...`.

3. Current `safe`/`cache` cleanup may retain proven generic primitives, but every candidate must be justified independently of retired lifecycle stages and must pass the campaign ownership boundary plus current P3/P5 protection.

4. P3/P5 protection:
   - target-size publication-before-adoption evidence remains protected by the existing P3 retention owner;
   - current or in-progress P5 post-selection object/run roots, including object-before-pointer and plan-before-run-completion windows, fail toward retention;
   - no current cleanup/dedup/archive path may infer disposable P3/P5 evidence from a pathname.

5. Preserve rather than redesign:
   - configured external-input/containment checks;
   - symlink unlink-versus-traversal safety;
   - P3 retention fence;
   - immutable publication helpers;
   - frame-cache mmap and current DATA4/DATA6 persistence;
   - shared SHA receipt machinery;
   - generic archive byte-authentication code if it is not reachable as stale current policy.

6. Frame cache remains retained through its current consumers. P6 must not reintroduce automatic `remove_frame_cache_after_prepare` behavior.

### Documentation disposition

- move the full historical STOR1-STOR5 design text under `docs/history/mlff/` (exact historical filename is delegated);
- keep `docs/specs/training_data/mlff_storage_management_spec.md` as the current link target, but rewrite it as the **transitional P6/P7 storage contract**: read-only accounting, conservative safe/cache cleanup, external/symlink ownership guarantees, P3/P5 fail-toward-retention, and explicit deferral of consequential retention/dedup/archive policy to the post-P7 reset;
- remove statements such as "the storage roadmap is complete" from current normative documentation;
- current user guide examples must not instruct users to run current `recompute`, `compact`, consequential `archive`, or `deduplicate --apply` on V7 state;
- the user-guide workspace diagram must not claim `models/` is the current P5 production publication. Current P5 evidence is owned by the post-selection persistence/run roots; P7 owns the later deployable publication boundary.

### Required storage acceptance

- structural scan over current production authorization code finds no `evaluate`/`verify`/DATA7-DATA8 destructive predicate;
- current parser/help/guide advertises only supported transitional behavior;
- attempts to invoke disabled consequential current-generation operations fail before candidate enumeration/deletion;
- safe/cache cleanup while P3 is in publication-before-adoption window cannot remove current/adoptable P3 evidence;
- safe/cache cleanup with a P5 final plan but incomplete required production runs cannot remove any object/run evidence needed to resume;
- external configured input and symlink escape tests remain green;
- retired STOR3 tests that manufacture an `evaluate` stage are replaced by current owner-bound safety tests, not merely skipped or deleted;
- the post-P7 storage workplan remains unchanged in scope and still owns the real storage renewal.

## 6. R8-D — make mandatory A/B/C qualification producer-distinct and completion-aware

### Concern / rationale

The current mandatory driver creates one P5A6 workspace, reopens it under P6, and sets both A and B to PASS from that same reopen. This cannot establish final-P6 self-production/restart.

### Required driver structure

The mandatory command under `qualification/p6-p5a6-compat/` must run three independent cases and print three independently computed PASS/FAIL values:

```text
A. P5A6 -> P6 authenticated current-generation compatibility
B. P6   -> P6 current-generation production/restart
C. V5/V6 -> reject-before-reuse
```

#### Case A — exact accepted P5A6 producer

Preserve the revision-5/7 authentication requirements:

- detached worktree at exact commit `1670275487d29bbcde4c59efafdef9d1f8b0ced7` and tree `17e2c5609974712bda1efd3375f09f42da830f68`;
- baseline import roots authenticated before state creation;
- real baseline P1-P5 persistence/currentness owners with bounded numerical seams only below MACE;
- final-P6 reopen in a separate process with no migration/pre-load rewrite;
- authenticate selected binding, CV acceptance, final plan, **derived final-production completion**, and unchanged authoritative content permitted by the compatibility contract.

A second read/reopen of this P5A6-produced workspace remains part of A only. It can never set B to PASS.

#### Case B — fresh final-P6 producer

Create a separate empty workspace/root, e.g. `producer-p6`, under a process importing exclusively from the final P6 repository.

The producer must drive the real current orchestration through:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
```

using bounded numerical fakes only at the already accepted trainer/inference seams. It must not seed P4/P5 state directly and must not reuse/copy the P5A6-produced workspace.

Before producer exit, record authenticated current identities sufficient to recheck:

- P3/P4 current generation/state and selected binding;
- exact selected membership;
- current method identity;
- current CV plan and accepted CV result;
- current final plan;
- current final-production completion identity plus the ordered required run-evidence identities/digests;
- public lifecycle complete state.

Then close all stores/process state. A **new final-P6 process** must reopen the same fresh P6 workspace and reauthenticate those owners from disk. It must resolve final-production completion, not only the final plan.

Finally, rerun `cross-validate` and `train-production` through the real commands with an instrumented accepted numerical seam and prove already complete authenticated runs are reused rather than retrained. Any newly executed required production run in this already-complete B workspace is a failure unless the prior evidence was intentionally corrupted by the test.

#### Case C — obsolete generation rejection

Keep a distinct V5/V6 fixture. It must prove the current reject-only owner refuses semantic reuse before retired state can influence target-size or P5 authority. No migration result can satisfy this case.

### Driver integrity rules

- statuses for A/B/C are initialized independently and set only by their own producer/reopen path;
- a failure or unavailability in B cannot be masked by A;
- mandatory qualification never skips because a workspace is absent; it creates/authenticates its required fixtures or fails;
- evidence/output paths for A and B are distinct so accidental workspace reuse is detectable;
- test helper use is allowed only when the helper drives the real production owners; a helper that preconstructs owner state is not acceptable.

## 7. R8-E — documentation/dependency ownership corrections tied to the blockers

The executable repairs above must be reflected in current durable documentation.

At minimum:

1. `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
   - DATA5 emits neutral evidence roles/protected relations, not "CV roles" or prebuilt fold plans;
   - P5 owns all fold construction after `T_selected`;
   - final production wording distinguishes plan/current run completion from P7 publication.

2. `docs/arch_manuals/mlff_training_data_dependency_graph.json`
   - remove `HELD_OUT_CV_EVALUATION` ownership by `DATA5/CV` as a pre-selection product;
   - `POST_SELECTION_CV_ACCEPTANCE` and its fold evidence must descend from `CURRENT_SELECTED_SET` plus neutral protected-relation/P1 evidence and be owned by P5;
   - remove current DATA7 fitted-selection nodes/edges that imply retired DATA7 remains a P1-P5 current owner;
   - no P7 deployment/calibration/locked owner may be represented as already implemented.

3. Current architecture/manual/user/spec sources must state the same owner chain. Generated PDFs are regenerated after semantic sources close; successful rendering alone is not semantic acceptance.

4. Current user guide workspace/layout must describe actual P5 persistence rather than `models/` as a current final publication.

## 8. Coherent implementation sequence

### R8-1 — P1/P5 ownership and completion repair

Implement R8-A and R8-B together because DATA5 neutralization and P5 completion both affect the current P1-P5 acceptance chain.

Stage-local closure:

- fresh prepare/DATA5 structural and serialization tests;
- post-selection fold construction/leakage tests on exact `T_selected`;
- CV-only invalidation tests proving P1-P4 stability;
- final-production plan-only/partial/corrupt/complete/reopen tests;
- current status/advance regression;
- affected P3/P4/P5 regression.

Do not proceed to final compatibility qualification with a hard failure in this stage.

### R8-2 — transitional storage quarantine

Implement R8-C against the accepted R8-1 candidate.

Stage-local closure:

- parser/help/current storage behavior;
- current storage structural absence checks;
- P3 publication-race retention;
- P5 plan/incomplete/completed evidence retention;
- external/symlink ownership regression;
- frame-cache lifetime test;
- affected storage/accounting regression.

### R8-3 — mandatory qualification and documentation reconciliation

Implement R8-D and R8-E after executable semantics are stable.

Stage-local closure:

- mandatory A/B/C driver with distinct producer lineages;
- fresh-P6 completion-aware self-restart;
- structural current-owner checks;
- current docs/spec/dependency graph checks;
- documentation/PDF build.

### R8-4 — final assembled P6 acceptance

Re-derive the complete affected surface from the full P6 diff through revision 8 and run fresh acceptance on one candidate:

1. all focused R8 tests above;
2. complete affected P1-P5/current public/storage-handoff regression;
3. real parser/dispatch lifecycle `prepare -> select-target-size -> cross-validate -> train-production` with close/reopen and currentness reauthentication;
4. final-production interruption/restart cases;
5. mandatory independent A/B/C qualification;
6. structural absence of current pre-target CV construction and retired storage authorization;
7. current documentation/source-map/dependency-graph checks and PDF build;
8. repository-required static/build checks;
9. broader/full CPU-safe repository suite unless the final affected surface is independently and completely bounded smaller.

A required check that skips or does not execute is not a PASS. Long target-machine GPU/real-data production qualification remains deferred and is not part of P6 functional closure.

## 9. Implementation authority

### Frozen

- P6 remains cleanup/cutover functional closure; P7 and the storage reset remain separate successors.
- Fresh current DATA5 does not construct or persist CV folds.
- P5 is the sole current owner of fold count, CV partition seed, CV optimizer seeds, fold construction and CV acceptance, all inside frozen `T_selected`.
- Legacy CV-bearing DATA5 may be read only for exact compatibility and never promoted into current P5 authority.
- Final-production plan existence is not completion; completion requires every exact required run evidence record.
- A completion identity, if exposed, is distinct from the final-plan identity.
- Current P6/P7 storage cannot execute retired evaluate/verify/DATA7-DATA8 consequential reclamation policy.
- Current consequential recompute/compact/archive/dedup policy is deferred to the post-P7 storage reset.
- P5A6->P6, P6->P6, and V5/V6 rejection are three independently produced qualification claims.
- Current docs and dependency graph must describe the same ownership as executable code.
- No GPU/long production qualification is required for P6.

### Delegated

- Exact current DATA5 schema/version name and whether compatibility decoding is implemented by a private legacy type, adapter, or version branch.
- Exact neutral names for any P1 policy fields proven not to be CV-specific.
- Exact user-facing mechanism used to disable consequential current storage operations: parser omission or fail-closed runtime rejection.
- Exact historical destination filename for the retired STOR1-STOR5 specification.
- Exact completion helper/type layout if it preserves the frozen derived-owner semantics.
- Fixture sizes and bounded numerical fake implementation below accepted MACE seams.

### Reopen only on evidence

Reopen Design only if implementation proves one of the following:

- P1 leakage/protected-relation correctness genuinely requires materializing configured post-selection folds before target selection;
- exact P5A6 compatibility cannot authenticate legacy DATA5 without making its old folds current;
- final-production completion cannot be derived safely from plan + immutable run evidence without a material new persisted authority;
- current safe/cache storage cannot be made conservative without implementing material cross-owner policy reserved for the post-P7 storage reset;
- a final-P6 workspace cannot be created/reopened through the real P1-P5 owners using bounded numerical seams.

Reopen only the affected surface and preserve unrelated accepted P6 work.

## 10. P6 revision-8 PASS definition

P6 passes only when one assembled candidate satisfies:

```text
fresh DATA5 is CV-plan-free
+ P5 alone constructs selected-only folds
+ P1-P4 are invariant to post-selection CV policy
+ final-production completion is evidence-authenticated and restart-safe
+ current storage is conservative and free of retired destructive lifecycle policy
+ exact P5A6 unchanged compatibility
+ independent fresh-P6 self-production/restart
+ V5/V6 reject-before-reuse
+ truthful current docs/config/public surface
+ affected regression/integration closure
```

Only an independent revision-8 P6 PASS may open P7 implementation.