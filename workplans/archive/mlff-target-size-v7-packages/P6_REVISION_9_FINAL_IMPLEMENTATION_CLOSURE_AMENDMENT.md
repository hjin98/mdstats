---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R9
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
package_revision: 9
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: 950acf577de67199828e0f94389fb6d8d4c4305d
reviewed_candidate_tree: c8ddbef8b3a1a7cecde3d58d330cb57dc6d3991d
reviewed_executable_parent_commit: 0016a3d44b4e854c32762bb724d2a87c49e25cf1
reviewed_executable_parent_tree: 07459698fbd092e3773b59600f25c7f3c405fe20
amends:
  - P6_REVISION_3_BASE.md
  - P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md
  - P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md
  - P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md
  - P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md
  - P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md
precedence: this amendment overrides earlier P6 text only where explicitly stated; all other obligations remain binding
successor_p7_workplan: CODE-MLFF-TARGET-SIZE-V7-P7
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P6 revision 9 amendment — final implementation closure instructions

## 1. Purpose and review disposition

Independent Design review of the revision-8 implementation found **two remaining blocking implementation nonconformances** on candidate `950acf577de67199828e0f94389fb6d8d4c4305d`:

1. the current transitional storage implementation still authorizes or describes cleanup through retired STOR-era path/stage/capability semantics, including DATA7/DATA8/evaluate/verify/preflight concepts, even though the consequential public tiers now fail closed; and
2. the required final-production completion/restart acceptance still uses a one-seed production fixture, so it cannot prove the mandatory partial-completion state or that restart reuses completed runs and executes only missing required runs.

These findings **do not reopen P6 architecture or science**. Revision 8 already established the correct target state. Revision 9 makes the remaining implementation and acceptance consequences explicit enough that the next Implementation round cannot satisfy them with a weaker proxy.

The following revision-8 outcomes were accepted by the review and must be preserved:

- fresh current DATA5 is CV-plan-free; legacy CV-bearing DATA5 is compatibility-only;
- `[post_selection.cv]` is the sole current fold-policy owner;
- P1-P4 identities remain independent of post-selection CV policy;
- `FinalProductionCompletion` is distinct from the final-production plan and is derived from authenticated run evidence;
- lifecycle completion consumes the completion owner rather than plan existence;
- A/B/C qualification now distinguishes exact P5A6 producer -> P6, fresh final-P6 producer -> P6, and retired V5/V6 reject-before-reuse;
- P7 remains downstream and is not implemented in P6;
- the post-P7 storage reset remains a separate successor and is not to be pulled into this repair.

Any repair that regresses one of those accepted outcomes is a P6 failure even if the two new focused tests pass.

## 2. Frozen closure target

The next P6 candidate must satisfy this exact current-state model:

```text
P5 final production
    plan published
      -> zero required runs: incomplete/resumable
      -> proper subset of required runs: incomplete/resumable
      -> every required run authenticated: complete
    restart never repeats an already authenticated required run

transitional P6/P7 storage
    storage report
        -> read-only accounting
    storage cleanup --tier safe
        -> zero-capability-loss, current-owner-proven cleanup only
    storage cleanup --tier cache
        -> independently reconstructible current cache eviction only
    every ambiguous/current/in-progress P3 or P5 artifact
        -> retain

retired STOR semantics
    evaluate / verify / preflight stage predicates
    DATA7 / DATA8 lifecycle capabilities
    recompute / compact / archive-as-reclamation
    current-generation deduplicate/apply or archive create/restore
        -> not current destructive authority
        -> absent or fail-closed before mutation
```

Pathname alone is never sufficient deletion authority when a current semantic owner exists. A cache may be physically recognizable by path, but eligibility must come from a current owner/invalidation/reconstructibility contract plus campaign ownership/containment checks, not from historical stage completion or historical capability vocabulary.

## 3. R9-A — finish current-generation storage quarantine

### 3.1 Protected concern

Revision 8 correctly made consequential public storage tiers fail closed, but the current implementation still retains stale destructive policy inside the supported cleanup machinery. In particular, the reviewed candidate still contains current cleanup logic or capability reporting around:

- `evaluate`, `verify`, or `preflight` stage completion;
- `data7-cache`, `data8-fixed-cache`, `evaluation-graphs`, `evaluation-predictions`, `model-sweep`, `true-label-replay`, and historical per-run model/evaluation layouts;
- `data7_reselection`, `data8_rematerialization`, `verification_replay`, old checkpoint/protocol-freeze capability language;
- configuration fallbacks such as `remove_evaluation_graph_cache_after_evaluate`, `remove_frame_cache_after_preflight`, `remove_shared_data7_cache_after_prepare`, `remove_shared_data8_fixed_file_cache_after_prepare`, historical smoke/preflight cleanup controls, or renamed equivalents.

Leaving these concepts in a reachable `safe`/`cache` or automatic-cleanup path means the current generation can still delete bytes for reasons owned by a retired architecture. Failing closed only at `recompute`/`compact` dispatch is therefore insufficient.

### 3.2 Frozen public behavior

For current P6/P7 generation state, the canonical mutating storage surface is limited to:

```text
storage cleanup --tier safe
storage cleanup --tier cache
```

and the read-only surface is:

```text
storage report
```

The following are **not current-generation consequential features** before `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`:

```text
storage cleanup --tier recompute
storage cleanup --tier compact
storage cleanup --tier archive
storage archive create
storage archive restore
storage deduplicate --apply
```

Preferred realization: remove those choices from current parser/help. An explicit fail-closed `CampaignCliError` before mutation remains acceptable only where retaining the syntax is required by an already supported compatibility surface. Do not preserve them merely because old tests or old docs mention them.

Read-only archive verification may remain only if it cannot mutate/currentize campaign state and is clearly classified as inspection of an existing historical archive rather than current P6/P7 retention policy.

The normal current command namespace is `storage ...`. Remove obsolete hidden top-level storage aliases unless a supported current compatibility contract is independently demonstrated.

### 3.3 Required code consequences in `_campaign_cli_core.py`

#### A. Current tier and capability definitions

The current cleanup dispatcher must recognize only `safe` and `cache` as consequential P6/P7 tiers.

- `_MANUAL_RECLAMATION_TIERS`, or its replacement, must not expose `recompute`, `compact`, or `archive` as current tiers.
- Current capability reporting must not describe DATA7 reselection, DATA8 rematerialization, verification replay, old protocol freeze, selected-checkpoint-only reevaluation, or equivalent retired lifecycle concepts as current V7 storage policy.
- `_manual_reclamation_add_recompute_tier()` and `_manual_reclamation_add_compact_tier()` must not remain reachable from current cleanup dispatch or another current destructive path.
- If the old functions are retained temporarily as historical/unreferenced code, structural checks must prove no current parser/dispatcher/automatic-cleanup path can call them. Prefer deletion when no current supported consumer exists; do not add a wrapper merely to preserve dead STOR policy.

#### B. Supported `safe` / `cache` candidate selection

Supported cleanup must use a **current-owner allowlist**, not a historical pathname catalog.

For every candidate eligible to be removed, implementation must be able to state all of the following from current code authority:

1. which current component owns the artifact;
2. why the artifact is non-authoritative and independently reconstructible or otherwise zero-capability-loss;
3. what identity/invalidation rule establishes that it is a cache/scratch artifact rather than current evidence;
4. why no current/in-progress P3 or P5 owner requires it for publication, currentness, restart, or completion;
5. why containment/symlink/external-input ownership checks permit mutation.

If any item cannot be established, **retain the artifact**. P6 must not invent a future cross-owner inventory registry to solve this; that belongs to the successor storage reset.

Historical path families such as `data7-cache`, `data8-fixed-cache`, `evaluation-graphs`, `evaluation-predictions`, `model-sweep`, `true-label-replay`, historical `evaluation-capsules`, or run-local `models` are not current cleanup candidates merely because those paths exist. They may be ignored/retained until the successor storage reset unless a separate current owner explicitly proves safe cache status.

The frame mmap cache is a current performance artifact and remains retained through current consumers. Do not restore automatic `remove_frame_cache_after_prepare` or `remove_frame_cache_after_preflight` behavior. If a manual `cache` eviction path for the frame cache is retained, it must be justified by the real current frame-cache owner and must fail toward retention while a current consumer can still require it.

#### C. Automatic cleanup

`_campaign_cleanup()` and helpers reachable from current lifecycle commands must no longer make deletion decisions from retired stage/configuration semantics.

Remove current execution of or fallback to settings equivalent to:

```text
remove_evaluation_graph_cache_after_evaluate
remove_frame_cache_after_prepare
remove_frame_cache_after_preflight
remove_shared_data7_cache_after_prepare
remove_shared_data8_fixed_file_cache_after_prepare
retain_historical_smoke_diagnostics
remove_preflight_heavy_artifacts_after_success
*_after_evaluate
*_after_verify
*_after_preflight
```

Do not merely hide these keys from generated TOML while continuing to honor them destructively when an older readable config contains them. Exact P5A6 configuration compatibility may parse historical fields where required, but such fields cannot authorize current-generation deletion.

Automatic cleanup may keep genuinely current, owner-proven generic scratch/cache cleanup. It must otherwise retain ambiguous material.

#### D. P3/P5 retention boundaries

Current storage cleanup must preserve all state needed for these windows:

```text
P3 object/evidence published -> current pointer/adoption not yet committed
P5 CV object/evidence published -> current pointer not yet committed
P5 final plan published -> no required final runs complete
P5 final plan published -> only a proper subset of required final runs complete
P5 required run evidence published -> final completion projection not yet re-resolved
```

The existing P3 retention owner remains authoritative for P3. P5 protection must derive from current P5 plan/currentness/run-evidence/completion owners. Storage must not duplicate those scientific/currentness decisions.

### 3.4 Parser/help and documentation consequences

Current help and durable docs must describe the same transitional surface.

At minimum reconcile:

- current CLI parser/help;
- `docs/specs/training_data/mlff_storage_management_spec.md`;
- `docs/guides/mlff_campaign_cli_user_guide.md`;
- assembled architecture/manual sources generated from affected canonical chapters;
- directly affected storage navigation/indexes.

The current user guide must not instruct users to run `recompute`, `compact`, consequential archive create/restore, or `deduplicate --apply` against V7 state. It should lead with `storage report`, then dry-run/current-safe `safe` and `cache` cleanup.

The user-guide workspace diagram must not label `models/` as a P5 **publication**. P5 owns final-production plans and authenticated completed run/model evidence; P7 later creates the deployable `FinalProductionPublication`.

Historical STOR1-STOR5 material may remain under history/release scope. A current normative storage specification must describe only the transitional P6/P7 contract and explicitly defer consequential retention/archive/dedup/admission policy to `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

### 3.5 Required structural acceptance

Use narrowly scoped source/AST/CLI assertions over **current reachable surfaces**, not repository-wide keyword bans.

Required checks:

1. current cleanup dispatch has only `safe`/`cache` consequential tiers;
2. current parser/help does not advertise `recompute`, `compact`, archive-as-reclamation, or current-generation dedup/apply;
3. current reachable cleanup/automatic-cleanup functions do not call `_effective_stage(..., "evaluate")`, `_effective_stage(..., "verify")`, or a preflight equivalent;
4. current reachable cleanup/automatic-cleanup functions contain no destructive branch keyed by the retired configuration names listed above;
5. current `safe`/`cache` candidate construction does not use DATA7/DATA8/verification-replay/protocol-freeze capability semantics as deletion authority;
6. any retained historical STOR helper is unreachable from current parser/dispatcher/automatic cleanup;
7. current docs do not present consequential STOR operations as supported P6/P7 workflow.

Historical documentation, compatibility readers, and inactive generic archive-byte utilities may contain historical names where they are genuinely non-current. Keep exact allowlists rather than weakening the checks globally.

### 3.6 Required functional acceptance

Exercise the real current CLI/cleanup owner using bounded workspaces:

- **P3 publication window:** create real current P3 publication-before-adoption state; `safe` and `cache` cleanup cannot remove evidence needed for adoption/restart.
- **P5 plan-only window:** current final plan exists and zero required runs are complete; `safe` and `cache` cleanup cannot remove plan/object/run material needed to resume.
- **P5 partial-run window:** with at least two required production seeds and exactly one authenticated run complete, `safe` and `cache` cleanup preserve both completed evidence and all state required to execute the missing run.
- **historical-path trap:** place a campaign-owned directory using one or more retired names (`data7-cache`, `evaluation-graphs`, or equivalent) without a current owner certification; current cleanup retains it rather than deleting it because of pathname.
- **current-cache positive case:** at least one genuinely current, owner-proven reconstructible cache/scratch candidate is removed by `cache`, proving the tier is functional rather than a universal no-op. If no such candidate exists in current P6, it is acceptable for `cache` to perform no deletion and report why; do not fabricate eligibility merely to make this test non-empty.
- external configured inputs remain protected;
- symlink escape/unlink-versus-traversal protections remain correct;
- retired consequential commands are absent or fail closed before mutation with clear successor-storage guidance.

A test that directly calls a deletion helper after preselecting a path cannot establish the cleanup-owner claim. The real parser/dispatcher/current cleanup candidate-selection path must execute.

### 3.7 Anti-shortcuts

The following do **not** close R9-A:

- leaving old tier/capability constants current but throwing only at the last command handler;
- renaming DATA7/DATA8/evaluate/verify strings while preserving the same path/stage inference;
- deleting only user-guide examples while stale destructive authorization remains executable;
- adding a blanket `try/except` around retired stage lookup;
- treating all `.mdstats/*cache*` paths as reconstructible by naming convention;
- replacing current cleanup with a new cross-owner storage registry or successor-storage architecture inside P6;
- making `safe`/`cache` unconditional no-ops if a real current owner-certified cache cleanup already exists and can be retained simply.

## 4. R9-B — prove real multi-seed final-production interruption and restart

### 4.1 Protected concern

The reviewed completion code can distinguish a final-production plan from completed evidence, but the committed acceptance fixture uses only one production seed. A one-seed campaign has no observable **proper-subset** state, so it cannot establish the required restart behavior:

```text
required seeds [A, B]
A authenticated
B missing
close/reopen
-> incomplete
-> reuse A
-> execute only B
-> complete
```

The next implementation round must add this evidence through the real P5 owner path. If the test exposes a code defect, repair the owning P5 logic under the already frozen revision-8 design; do not weaken the test to fit current behavior.

### 4.2 Dedicated two-seed acceptance fixture

Add a dedicated bounded final-production configuration with **at least two required final seeds**, preferably:

```toml
[post_selection.production]
seeds = [5, 6]
```

Do not globally change the default single-seed fixture if other tests legitimately use it. The purpose is to create an acceptance fixture where a proper subset is observable.

The numerical trainer/inference dependency may remain a deterministic lightweight fake **below** the P5 semantic owner. The real components that must execute are:

- current selected-context resolution;
- P5 final-plan construction/publication;
- the real final-production required-seed loop;
- real immutable run-evidence persistence/loading;
- `resolve_current_final_production_completion()`;
- public lifecycle `status` / `advance` projection;
- close/reopen of the real campaign persistence;
- resume through the real `train-production` command/owner.

The harness may record trainer invocations by seed and may deliberately raise below the P5 owner to simulate interruption. It may **not** manually seed a successful completion record, directly write fake run evidence as the primary success path, replace the completion resolver, or reimplement the missing-run decision.

### 4.3 Mandatory case 1 — plan published, zero runs complete

Use the real `train-production` owner with a trainer seam that fails on the first requested production run **after the final plan has been durably published but before valid run evidence exists**.

After the induced interruption:

1. close every open store/handle;
2. reopen the campaign through the real persistence owner;
3. assert the final plan resolves and is current;
4. assert `resolve_current_final_production_completion()` returns incomplete/`None` rather than success;
5. assert `status` reports final production incomplete/resumable;
6. assert `advance` selects/routes to `train-production`, not terminal completion and not P7;
7. assert no required seed has authenticated run evidence.

A test that constructs a plan object directly without exercising plan persistence/reopen does not satisfy this case.

### 4.4 Mandatory case 2 — exactly one of two required runs complete

Run the real final-production loop with a deterministic harness that:

- completes seed `5` successfully through the normal P5 run-evidence persistence path;
- then raises on seed `6` before valid seed-6 run evidence is published.

After close/reopen:

1. the final plan is current;
2. seed-5 evidence authenticates against its exact `FinalProductionRunPlan`;
3. seed-6 evidence is absent;
4. completion is absent/incomplete;
5. `status` remains incomplete/resumable;
6. `advance` routes to `train-production`;
7. storage `safe`/`cache` cannot remove seed-5 evidence or state needed to execute seed 6.

Then resume through the real final-production command using a fresh recording trainer harness. The required assertion is:

```text
trainer invocations during resume == [6]
```

or the exact equivalent for the configured second seed. Seed `5` must not be trained again. After seed `6` publishes valid evidence, completion must resolve and include both required runs in deterministic plan order.

This **missing-run-only assertion is mandatory**. Merely asserting eventual completion after restart is insufficient because a broken implementation could rerun all seeds and still finish successfully.

### 4.5 Mandatory case 3 — corrupt or mismatched required evidence fails closed

Using the same two-seed campaign, create valid required run evidence through the real P5 owner, then simulate one representative persistence failure by externally corrupting or mismatching one required evidence artifact, for example:

- truncate/invalid JSON;
- alter the persisted `run_plan_digest`;
- copy otherwise valid evidence under the other required run root/identity.

On reopen/resolution:

- corrupt/mismatched evidence must **not** be treated as missing-success;
- completion must not resolve;
- the owner must fail closed with the existing actionable integrity/currentness error semantics rather than silently training around evidence whose identity is ambiguous or invalid.

Do not change the product to auto-delete corrupt evidence solely to simplify this test unless such recovery is already an accepted P5 contract.

### 4.6 Mandatory case 4 — all runs complete and stable across reopen

After both required seeds complete through normal execution:

- `FinalProductionCompletion` exists;
- its ordered run set corresponds exactly to the final plan's required seed order;
- its `content_digest` remains distinct from `plan.content_digest` and binds the ordered run-evidence identities;
- public `status` is complete for P6;
- `advance` has no P6 scientific next operation and does not re-run production;
- closing and reopening the campaign produces the same completion identity and run-evidence set.

At least one acceptance check must cross a real process boundary, not only reopen `CampaignStore` in the same Python process. A bounded subprocess invocation of the public CLI `status`/`advance` against the completed or partial workspace is sufficient; no GPU work is required.

### 4.7 Required compatibility/qualification interaction

The mandatory A/B/C qualification remains producer-distinct and completion-aware.

- Case A remains exact accepted P5A6 producer -> final P6 unchanged reopen.
- Case B remains a fresh final-P6 producer -> final P6 close/reopen/restart and must authenticate **completion**, not only the plan.
- Case C remains retired V5/V6 reject-before-reuse.

Revision 9 does not require the compatibility driver itself to use two production seeds if its independent Case-B completion claim is already valid. The dedicated R9-B test owns the stronger proper-subset/resume claim. Do not conflate these two evidence purposes.

### 4.8 Anti-shortcuts

The following do **not** close R9-B:

- changing the fixture to two seeds but executing both in one uninterrupted call only;
- directly persisting seed-5 evidence from the test instead of letting the real final-production loop persist it;
- asserting only that completion is absent before training and present afterward;
- resuming and allowing both seeds to retrain;
- mocking `resolve_current_final_production_completion()` or the required-seed selection logic;
- using a fake/in-memory persistence layer when close/reopen is the claim;
- treating corrupt evidence as simply absent and then retraining without surfacing the integrity failure.

## 5. Implementation stages and stage-local closure

Revision 9 contains two independent repair surfaces. Keep them as two coherent executable stages unless repository evidence shows they are inseparable.

### Stage R9-1 — transitional storage current-authority closure

Implement R9-A, including parser/help, current cleanup/automatic-cleanup authorization, focused storage tests, and directly affected current storage/user documentation.

Before proceeding:

- perform semantic/source closure that no retired stage/path/capability remains a current deletion authority;
- run focused storage ownership/containment/symlink/P3/P5-retention tests;
- run stage-local affected regression for current storage CLI, cleanup, campaign lifecycle consumers, and configuration compatibility paths that can reach cleanup;
- regenerate/validate directly affected generated documentation/PDFs if the repository tracks them.

### Stage R9-2 — multi-seed P5 completion/restart acceptance

Add the two-seed interruption/resume coverage and repair P5 code only if the real-owner test exposes a defect.

Before final closure:

- execute all four mandatory R9-B cases;
- run affected P5 plan/run-evidence/completion/status/advance/restart regression;
- rerun storage P5-retention tests because they now must cover the proper-subset final-production window;
- rerun the distinct A/B/C qualification driver if P5 lifecycle/completion code changes.

If R9-2 changes only tests and exposes no product-code defect, prior executable evidence whose dimensions are unchanged may be reused at stage level, but final assembled P6 acceptance below is still mandatory.

## 6. Final assembled P6 revision-9 acceptance

After all executable/documentation edits are assembled, Implementation must re-derive the affected surface and run fresh final acceptance on the same candidate.

Required final evidence:

1. revision-8 DATA5/P1-P4 CV-independence tests remain green;
2. final-production plan-versus-completion tests remain green;
3. the new two-seed plan-only, proper-subset/missing-run-only, corrupt-evidence, all-complete, and process-reopen cases pass through real P5 owners;
4. current storage structural assertions prove only `safe`/`cache` current destructive tiers and no retired lifecycle/path/capability authorization;
5. current storage functional tests cover P3 publication, P5 plan-only, P5 proper-subset completion, ownership/containment, symlink/external inputs, and consequential-command fail-closed/absence;
6. generated config/current help remain free of retired current storage policy and previously retired verification/dynamics/CV-authoring controls;
7. independent A/B/C compatibility qualification reports PASS separately for all three producer classes;
8. real parser/dispatch lifecycle remains functional through `prepare -> select-target-size -> cross-validate -> train-production`, including close/reopen/currentness;
9. current user guide/storage spec/architecture sources describe the transitional storage boundary and P5 evidence vs P7 publication correctly;
10. directly affected documentation source chains build/regenerate successfully, including tracked PDFs;
11. complete affected-surface CPU-safe regression passes; because `_campaign_cli_core.py`, P5 persistence/currentness, and public CLI are central surfaces, use the broader/full CPU-safe suite unless a smaller complete affected bound is independently demonstrated.

Long target-GPU runs, real-data M-ladder production qualification, P7 downstream physical/deployment qualification, and the post-P7 storage optimization/qualification remain outside P6 and remain deferred as already frozen.

A required test that does not execute is not a PASS. Do not skip or substitute the two-seed proper-subset case, the current storage real-dispatch path, or A/B/C qualification.

## 7. Frozen / delegated / reopen-only decisions

### Frozen

- This is implementation rework, not a redesign.
- Fresh DATA5 remains CV-plan-free and P5 remains the sole current CV owner.
- P1-P4 remain independent of `[post_selection.cv]`.
- Final-production plan is not completion.
- Completion requires authenticated evidence for every required final seed.
- Restart must reuse authenticated completed runs and execute only missing required runs.
- Current P6/P7 storage is conservative and owner-driven; retired STOR stage/path/capability semantics are not current deletion authority.
- Current consequential storage policy is limited to `safe`/`cache`; the successor storage reset owns cross-owner retention/archive/dedup/admission redesign.
- Ambiguous/current/in-progress P3/P5 state fails toward retention.
- P7 remains gated on independent P6 PASS.
- GPU/long-real-data production qualification remains deferred.

### Delegated

- exact helper/function names after stale STOR cleanup;
- whether unreachable historical STOR helpers are deleted or retained outside current dispatch, provided structural evidence proves they are non-current;
- exact current-cache allowlist representation, provided it uses existing current owners and does not create a successor-style registry;
- exact deterministic trainer harness implementation below the P5 semantic-owner seam;
- exact representative corruption mode for R9-B;
- exact current doc phrasing and historical STOR filename/location.

### Reopen Design only on evidence

Reopen only the affected surface if implementation evidence establishes one of these conditions:

1. a currently supported external compatibility contract genuinely requires a consequential STOR command to mutate current P6/P7 state before the successor storage reset;
2. no safe/cache cleanup can be expressed using existing current ownership boundaries without implementing a material portion of the successor storage architecture;
3. the P5 persistence model cannot represent or resume a proper subset of required final runs without a material persistence/authority redesign;
4. exact accepted P5A6 compatibility is broken by the storage quarantine despite current state being semantically unchanged.

If none of these evidence-backed triggers fires, do not reopen P6 design. Repair the implementation under this contract.

## 8. Revision-9 PASS definition

P6 revision 9 is eligible for independent PASS only when:

```text
all revision-8 accepted ownership/scientific repairs preserved
+ current storage destructive authority contains no retired STOR lifecycle policy
+ current safe/cache cleanup is owner-proven and fail-toward-retention
+ current docs/help match that transitional storage surface
+ >=2-seed final-production proper-subset interruption is demonstrated
+ restart executes only missing required production runs
+ corrupt/mismatched required run evidence fails closed
+ completion remains stable across close/reopen and a real process boundary
+ A/B/C compatibility remains producer-distinct and PASS
+ stage-local and final affected regression/integration closure
```

Only an independent **P6 revision-9 PASS** opens the P7 implementation gate.