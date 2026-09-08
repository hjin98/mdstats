---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R37-IR18
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 37
reviewed_plan_commit: a62e922e1f4455577e1acb3e0bde4133d60f60df
reviewed_executable_commit: 6391043b3641e007017d1781678c96a2b6b0d259
reviewed_executable_tree: 4055b67f2f86954b4355023cc84c9b0134a76e85
reviewed_branch_head: e76ca9cf40bc5b52b48827cb3503d4611b19de34
reviewed_branch_tree: 5ab42b2996d58804e70871ee9dc436e34a968dea
review_verdict: NO-PASS
scope: bounded R37 implementation correction for canonical cleanup semantic-owner routing, fail-closed executor domain, action-owner binding, and exact-candidate acceptance evidence
precedence: Revision 30, Revision 37, the current storage specification, and this IR18 handoff are the current normative implementation authority; earlier IR17 remains historical provenance only
---

# Storage/I-O reset implementation review reopen 18 — canonical cleanup semantic-owner closure

## Disposition

**Reviewed executable: NO-PASS.**

The executable candidate is:

```text
commit  6391043b3641e007017d1781678c96a2b6b0d259
 tree    4055b67f2f86954b4355023cc84c9b0134a76e85
```

The branch successor is:

```text
commit  e76ca9cf40bc5b52b48827cb3503d4611b19de34
 tree    5ab42b2996d58804e70871ee9dc436e34a968dea
```

and changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`. Behavioral review therefore binds to executable tree `4055b67f...`; a later non-executable successor may inherit behavioral evidence only after proving its executable tree is unchanged.

Candidate `6391043b...` closes the principal refined-IR17 defects. Preserve its conforming work: plan-bound descriptor acquisition from the campaign anchor, opened-target identity checks, default single-file final identity, same-parent directory-entry durability, common owner root/container checks, final fd-relative `rmdir`, transition-exact publication/unlink behavior, exactly-once no-follow acquisition cleanup, ranked mount-refusal close, failed P7 session-acquisition ranking, typed member authority, and the existing R30-R37 mutation/byte/session semantics.

Two closure families remain:

1. cleanup semantic-owner routing is still structurally split so a valid owner-specific plan can reach the generic remover when the optional/default engine path is selected, and the current plan does not yet positively bind each cleanup action to the fresh owner view that actually authorizes its action kind; and
2. the exact executable candidate still lacks recorded behavioral acceptance evidence satisfying the final R37 closure contract.

Neither finding changes Revision-30/37 architecture. No Revision 38 is justified.

## Current supplied authority and snapshot completeness

The current implementation handoff is intentionally recoverable without prior chat, Git history, or superseded review files. The supplied normative set is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted final-apply design;
- `AUTHORITY_REVISION_37.md` — accepted bounded R37 authority;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract, including descriptor-capability, transition-truth, durability, close-ranking, typed-authority, and owner-driven cleanup semantics;
- this IR18 handoff — all still-open implementation and acceptance obligations after candidate `6391043b...`.

Earlier refined IR17 remains useful provenance and test-selection history, but no still-open requirement depends on loading it. The preserved invariants and final regression obligations below restate the still-binding implementation consequences needed to protect its conforming result. Test names carrying historical revision labels are evidence selectors, not hidden authority.

# IR18-1 — cleanup action semantics must have one canonical classifier and fail-closed execution domain

## Evidence and root failure mechanism

`StorageExecutor.run()` is an exported consequential execution surface and accepts `engine=None`. With no engine supplied it calls `_execute_actions()`, which currently root-authorizes each `ACTION_REMOVE` / `ACTION_EVICT_CACHE` action and then calls `remove_planned_outcome()` without consulting the semantic owner fields that production cleanup uses.

Production `_cleanup_engine()` independently performs a richer dispatch:

- P7 released-attempt actions use `P7_RELEASED_ATTEMPT_AUTHORIZER`, a live `ReleasedAttemptSession`, proof/release/root identity, typed topology, mutation-time target identity, and same-attempt invalidation;
- owner-scoped directory actions use `snapshot.authorized_members(view)` plus `remove_certified_subtree()`, preserving typed member authority, refusals, retained descendants, owner `root_identity` / `path_identity`, and action-wide mutation truth;
- maintenance actions use the campaign-state maintenance owner;
- only the residual branch reaches `remove_planned_outcome()`.

`safe_candidates()` and `cache_candidates()` plan owner artifacts at their owner-view path. Descendant/member authority is intentionally applied later by the semantic owner. Therefore path authorization plus `PlannedAction.filesystem_identity` is necessary but not sufficient authority for a directory/container or exact-authorizer action.

The defect is broader than one `engine=None` branch: cleanup semantic classification is duplicated between the default executor and production engine, and the residual generic fallback is defined by what earlier branches did *not* match. That negative/default shape is the mechanism that allowed semantic authority to disappear. Closing the family requires a positive, canonical classification that both paths consume.

## Required canonical semantic classification

Create one canonical cleanup-action semantic classifier or equivalent single owning decision. Exact enum/function names and module placement are delegated, but the semantic result is frozen. For the **fresh post-revalidation snapshot** supplied inside `StorageExecutor.run` while the storage lease and owner mutation/publication barriers remain held, every cleanup action must resolve to exactly one of these semantic classes or to `invalid/unsupported`:

1. **P7 / exact-authorizer action.** Any nonempty `view.exact_authorizer` is owner-specific. The recognized P7 authorizer routes only through the live P7 session owner. An unknown/future exact authorizer is unsupported until a specific owner implementation exists; it never falls through to generic removal.
2. **Owner-scoped subtree action.** A directory action at the exact owner-view path whose semantics depend on `coverage`, certified/retained members, owner-exclusive subtree evidence, `root_identity`, `path_identity`, or typed member authority routes only through the common owner-scoped subtree implementation. It never becomes generic because no exact authorizer matched.
3. **Generic leaf action.** The only default-executor destructive class. It is a non-directory leaf (`file` or `symlink`) whose current owner view exactly matches `action.artifact_id` and `action.path`, whose action-kind eligibility is positively established by that current owner view, and whose mutation requires no exact-authorizer, subtree/member, retained-member, or independent owner-root/path capability beyond the plan-bound target identity and existing synchronization. Unknown/special-node shapes are not generic by default.
4. **Maintenance / specialized action.** Campaign-state maintenance and any other action with its own engine is not executable by the generic default engine.
5. **Invalid / ambiguous action.** Missing owner view, mismatched `artifact_id` -> `view.path`, unsupported action kind, missing action-kind eligibility, unknown exact authorizer, unsupported directory semantic shape, or another inability to prove one of the classes above fails closed before mutation.

This is a **positive allow-domain**, not a blacklist. New fields, owner types, or authorizers do not become generic merely because the classifier has never heard of them.

### Action-kind eligibility binding

The classifier must bind the plan back to current owner semantics, not merely to a path:

- `ACTION_REMOVE` requires the fresh matching owner view to still authorize safe reclamation for that artifact under the already-revalidated owner state;
- `ACTION_EVICT_CACHE` requires the fresh matching owner view to still establish the accepted reconstructible/evictable cache semantics and the policy/action context that permits eviction;
- a cleanup `PlannedAction` whose `artifact_id` resolves to a different `view.path` is invalid even if the supplied path is physically campaign-owned, unprotected, and has a valid filesystem identity;
- root/path authorization and `PlannedAction.filesystem_identity` remain independent constraints and do not substitute for this semantic binding.

Canonical builders already produce these relationships. The new check is a fail-closed execution invariant against accidental/malformed plans and future routing drift, not a second persistent authority.

## Preflight placement and atomicity

Semantic classification is performed from the **fresh snapshot after `revalidate_plan()`** and while the existing storage lease plus owner activity/publication barriers are still held. Do not classify from the stale planning snapshot, cached path shape, or a pre-lock observation.

Before the first destructive transition, the selected engine must preflight the **entire plan** against its supported semantic classes:

- `engine=None` accepts a plan only when every consequential action is `generic leaf` and no maintenance/specialized/owner-specific/invalid action is present;
- production cleanup accepts the classes it actually implements and rejects `invalid/unsupported` before any action mutates;
- a mixed plan is never executed sequentially until an unsupported later action is discovered;
- ordinary per-action runtime refusal (for example a target changing at the final identity boundary) remains distinct from engine/domain construction failure and may retain existing settlement semantics.

For a wrong-engine or invalid-domain plan, no action is completed, `mutated=false`, `reclaimed_bytes=0`, and the executor's durable audit truthfully records a refused/nonmutating execution. The low-complexity preferred realization is a typed executor/engine-domain failure raised only after `StorageExecutor.run` has materialized/finalized that refused truth; an equivalent audited refused return is acceptable only if caller compatibility requires it and it cannot settle as `complete` or fabricate per-action owner refusals.

## Canonical ownership / complexity constraint

Do not implement one independent default-engine safety predicate and leave production `_cleanup_engine()` on a separate ad-hoc `if/elif/else` semantic definition. Both paths must consume the same canonical semantic classification or a single shared dispatch owner.

This does **not** require making the default engine capable of P7, common subtree, or maintenance work. The simplest acceptable product is:

- one canonical classifier;
- production cleanup dispatches all recognized classes to their existing specialized owners;
- the default executor preflights the whole plan and executes only the positive `generic leaf` class;
- unsupported/ambiguous classes fail closed.

No new persistent plan schema, proof registry, inode registry, or authority database is permitted.

## Caller and compatibility census

Perform a bounded reference census of:

- `StorageExecutor.run` and wrappers that expose it;
- direct construction of `StoragePlan` / `PlannedAction` used with cleanup execution;
- production cleanup callers and tests that intentionally use `engine=None`;
- the `mdstats.training_data.storage` export surface and any maintained documentation/tests that treat the optional engine behavior as supported API.

Serena may accelerate this when available; direct reference/source inspection is an acceptable equivalent. Record the discovered caller classes and disposition in the implementation handoff/output; no persistent census artifact is required.

If a maintained external/public contract genuinely requires `engine=None` to execute owner-specific recursive/P7 cleanup, stop and reopen only this API/ownership surface. Do not preserve an unsafe fallback for compatibility. If the only maintained uses are generic-leaf tests/internal callers, narrow the default domain accordingly.

## Mandatory acceptance for IR18-1

All material execution cases below use real inventory/planning or an intentionally malformed plan built from a real snapshot when malformed-plan rejection itself is the claim, the real `StorageExecutor.run`, normal synchronization/revalidation, settlement/finalization, and durable audit. Test doubles may inject only below those semantic owners. For every acceptance-critical guard/failpoint, assert the intended seam actually fired and that the result was not instead produced by stale-plan rejection or an unrelated earlier refusal.

1. **Common-container wrong-engine counterfactual.** Before planning, create a real reclaimable owner-scoped directory/container state containing at least one authorized member plus one retained/foreign/typed contradiction sentinel that production `authorized_members()` would retain. Build/revalidate the real plan successfully, then invoke `StorageExecutor.run(..., engine=None)`. Engine-domain preflight fires; no generic remover is invoked; authorized and retained members both survive; audit is refused/nonmutating/zero-byte.
2. **P7 exact-authorizer wrong-engine counterfactual.** Build a real released-P7 cleanup plan with no post-plan owner mutation. Invoke `engine=None`. Classification identifies the exact-authorizer class, `remove_planned_outcome()` and P7 mutation are not invoked, attempt scratch/proof state survives, and the audit identifies incompatible engine/domain rather than stale plan.
3. **Mixed-plan plan-wide preflight, both orders.** Use one generic-leaf action and one owner-specific/specialized action. Parameterize/order the unsupported action both before and after the generic leaf. In both orders the generic leaf survives; there is no accidental partial cleanup; audit is nonmutating refused.
4. **Maintenance mixed-plan sibling.** Use a real cleanup plan or equivalent real-snapshot plan containing a generic leaf plus a planned maintenance action. `engine=None` rejects before the leaf mutates. This closes the currently distinct sequential maintenance-refusal branch under the same plan-wide domain rule.
5. **Cache-directory sibling.** Where a real evictable cache artifact is directory-shaped or otherwise owner-scoped, `engine=None` rejects it as owner/specialized rather than recursively deleting it generically; normal production cache cleanup still works through its semantic owner. If no current maintained directory cache candidate exists, record that census result and cover the classifier with a focused non-proxy unit fixture instead of inventing a fake production owner.
6. **Action-owner binding counterfactual.** From a real fresh snapshot, deliberately construct a cleanup action whose `artifact_id` names one legitimate owner view but whose `path` is a different unprotected campaign-owned target, with a valid plan-bound filesystem identity. Both default and production cleanup execution reject the plan before mutation because `view.path != action.path`; the target sentinel survives. This test is allowed to construct the malformed action because the claim is precisely executor rejection of malformed semantic binding.
7. **Owner-eligibility counterfactual.** Deliberately construct `ACTION_REMOVE` for a matching but non-`safe_reclaimable` view, and/or `ACTION_EVICT_CACHE` for a matching view lacking current reconstructible+evictable authority. The canonical classifier returns invalid before mutation; path authorization alone cannot rescue it.
8. **Unknown exact-authorizer guard.** A focused classifier/structural test proves a nonempty unrecognized exact authorizer is never classified generic. No fake production integration claim is made for an owner that does not exist.
9. **Default generic-leaf liveness.** A real-snapshot plan containing only a genuinely generic owner-authorized regular-file (or supported symlink) cleanup action executes through `engine=None`, compares the complete plan-bound identity immediately before fd-relative unlink, persists through the same authenticated parent fd, credits exact bytes, and audits `complete`.
10. **Production routing regression.** Normal CLI/production cleanup still routes recognized P7 exact actions through the P7 session owner, owner-scoped directories through common typed-subtree removal, maintenance through its owner, and positive generic leaves through `remove_planned_outcome()`. The same canonical classifier is in the live path and every conforming IR17 acquisition/durability/close protection remains intact.
11. **Structural negative evidence.** Establish that there is no residual cleanup branch in which an unmatched/unknown action shape falls through to `remove_planned_outcome()`. Direct generic-remover calls in consequential cleanup must be dominated by the canonical `generic leaf` classification. If Semgrep/custom AST is used, validate the rule on a known-positive and known-negative construct before relying on zero findings.

# IR18-2 — exact-candidate functional closure remains mandatory

The reviewed executable has no behavioral CI/status or other repository-accessible exact-candidate receipt. Source/test presence and the implementation commit message do not establish that required suites executed after the last executable/test edit.

After the last executable or test edit, bind all functional evidence to the exact final executable commit/tree.

## Stage-local closure

Treat IR18-1 as one coherent executable stage unless implementation evidence exposes a separate material owner/API boundary. Before final closure:

- perform semantic/conformance inspection of the canonical classifier, full-plan preflight, and discovered callers;
- run focused IR18 classifier/default-engine/production-routing tests;
- run stage-local affected regression across executor, plan/revalidation if touched, cleanup routing, inventory/owner classification, common cleanup, P7 session/removal, cache eviction, maintenance, generic leaf removal, settlement, and audit;
- if a shared trust/removal/durability helper changes, rerun the specifically affected preserved R37/IR17 cases before dependent work proceeds.

## Final assembled evidence

After the **last** executable/test edit:

1. record exact final executable commit and tree and prove any later successor is non-executable before evidence reuse;
2. re-derive the affected surface from the assembled diff plus callers/references of changed executor/routing/inventory/owner/trust/removal helpers;
3. run focused IR18 plus all maintained R22-R37 storage/P7 namespace, release/root/target identity, opened-descriptor mount, final-rmdir, final-unlink identity, typed-common authority, transition truth, mutation/byte accounting, close/finalizer, concurrency, retry, and liveness nodes that protect the preserved implementation listed below;
4. run complete:

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

5. run at minimum:

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

6. include every maintained test/module discovered from the final affected-surface census that exercises `StorageExecutor.run`, `StoragePlan`/`PlannedAction` cleanup construction, cleanup routing, safe/cache candidate semantics, generic/common cleanup, P7 released-attempt removal/session, maintenance, shared descriptor/trust/durability helpers, archive/catalog/journal publication, reclaim/restore, or dedup behavior plausibly affected by the final diff;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for changed Python modules, repository-required static checks, `git diff --check`, and conflict-marker scan;
9. structurally re-establish the preserved negative claims: continuous anchored acquisition, opened target/owner identity checks, no unbound consequential leaf unlink, same-parent top-level durability, no direct close-before-structured-failure bypass, no double-close acquisition, transition callbacks at atomic syscalls, and every final consequential `rmdir` fd-relative/immediately identity-checked;
10. structurally establish the new IR18 claims: exactly one canonical cleanup semantic classification governs default and production routing; unknown/unmatched semantic shapes cannot fall through generic removal; `engine=None` has a positive generic-leaf-only domain; cleanup action/view binding is checked before mutation;
11. validate the changed storage Markdown specification and regenerate/validate its PDF derivative only if permanent product/API documentation changes; workplan-only edits do not require product-spec regeneration;
12. report commands/node selections and pass/fail/skip counts for the exact candidate. CI output, captured terminal output supplied with the implementation handoff, or equivalent exact-candidate execution output is sufficient; do not create a persistent evidence subsystem solely for this closure.

Use repository convention `conda run -n mace ...` where applicable. Full external DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Expected affected surface

Initially expect the bounded repair to touch:

- `mdstats/training_data/storage/executor.py` — default-engine full-plan preflight and generic-leaf execution domain;
- `mdstats/training_data/storage/commands.py` — production cleanup dispatch consuming the same canonical classification;
- `mdstats/training_data/storage/inventory.py` and/or `storage/owners.py` only if the canonical classification naturally belongs with current owner semantics; do not add persistent state;
- `mdstats/training_data/storage/plan.py` only if a narrow validation hook is needed; no new schema/authority registry is expected;
- `mdstats/training_data/storage/__init__.py`, maintained API docs, and callers as compatibility/regression surfaces because `StorageExecutor` is exported, though they need not change if the census shows no documented owner-specific default contract;
- `tests/test_mlff_storage_reset_core.py` and `tests/test_mlff_storage_reset_integration.py` plus any caller/API regression tests discovered by the census.

`qualification/store.py`, `storage/trust.py`, `storage/durability.py`, archive/catalog/journal, dedup, and maintenance owners are regression surfaces and should not be edited unless the canonicalization genuinely requires it. Final affected surface is re-derived from the assembled candidate and is not capped by this list.

# Implementation authority

## Frozen

- Revision-30/37 owner architecture and current storage-spec semantics remain authoritative.
- Cleanup action semantics are decided by one canonical semantic classifier/dispatch owner consumed by both default and production cleanup paths; duplicated negative-fallback classification is not an acceptable closure.
- Classification uses the fresh post-revalidation snapshot while storage/owner synchronization remains held.
- Every cleanup action is positively bound to a matching current owner view and the action-kind eligibility that owner grants; `artifact_id`, root-path authorization, and plan filesystem identity cannot camouflage a different target or unsupported action.
- P7 released scratch is mutated only by the live P7 owner/session contract; an unknown exact authorizer is never generic.
- Owner-scoped directory/container cleanup spends typed/retained/root/path authority and is never generic default work.
- The default engine supports only positively classified generic leaves; maintenance, directories, exact authorizers, unknown/special nodes, and ambiguous/malformed semantic bindings fail closed before any plan action mutates.
- Engine/domain incompatibility is plan-wide and nonmutating: no convenient subset executes before the incompatibility is discovered.
- `PlannedAction.filesystem_identity` remains the plan's target identity and is independent of owner root/path/release/member authority.
- Preserve the four cleanup outcomes for action-level product truth; wrong-engine/invalid-plan failure is an execution/domain failure and must not fabricate action mutation truth.
- No new persistent authority/control plane or plan schema solely for this repair.
- Python `>=3.10`, accepted POSIX threat boundary, CampaignStore/P1-P7 science/currentness semantics, and archive/dedup/restore architecture remain unchanged.

## Delegated

- Exact enum/type/function names and module placement for the canonical classifier.
- Whether default preflight is implemented as a dedicated validation pass, a shared dispatch preparation pass, or another equivalent single-owner mechanism, provided the whole plan is classified before mutation.
- Exact typed exception/refusal wording for domain mismatch, provided nonmutation, audited refusal, and no accidental `complete` settlement are preserved.
- Exact test seam and optional Serena/Semgrep/AST method for caller/structural census.
- Internal refactoring needed to remove duplicated routing, provided public product semantics above remain unchanged.

## Reopen design only on evidence

Reopen only the affected API/ownership surface if evidence proves that a maintained external/public consumer contract requires `StorageExecutor.run(engine=None)` to execute owner-specific recursive/P7/maintenance cleanup and cannot be safely routed through the canonical semantic owner without an incompatible contract change.

Also reopen if the current `OwnerArtifactView`/plan representation cannot positively distinguish generic-leaf authority from owner-specific mutation authority without a new persistent/public semantic field; do not guess a permissive predicate. A narrow internal derived classifier is preferred and is not a redesign.

Ordinary internal refactoring, test inconvenience, additional current caller sites, optional-tool absence, or a malformed-plan test failure is implementation work under this authority.

# Closure sequence

## Stage A — canonicalize cleanup semantic classification and preflight

Perform the caller/action-domain census; implement the shared classifier; make default and production cleanup consume it; enforce exact action-owner/eligibility binding and full-plan preflight; add the common/P7/mixed-order/maintenance/cache/malformed-binding/generic-leaf acceptance. Close semantic conformance plus focused and stage-local affected regression before proceeding.

## Final assembled closure

Run IR18-2 against the exact final executable tree. A PASS requires both source/semantic closure and executed final evidence. Only then may the storage-I/O plan be marked complete and archived.

# Preserved conforming implementation and regression obligations

Preserve candidate `6391043b...` unless a narrowly necessary local adjustment is required by IR18:

- plan-bound componentwise descriptor descent from the justified campaign anchor;
- opened target comparison across current plan identity dimensions before mutation;
- common opened authority/container owner identity checks and typed member authority;
- default single-file fd-relative final observation/unlink and same-parent fsync;
- top-level directory same-parent durability after fd-relative final `rmdir`;
- immediate final name-vs-opened-directory identity check;
- ranked recursive mount-refusal close and exactly-once no-follow acquisition cleanup;
- failed P7 session acquisition primary/secondary ranking and one-way session invalidation;
- transition-exact unlink/publication/archive/restore-journal behavior;
- shared `MutationLedger`, exact action evidence, zero-credit mutation truth, two-attempt isolation, and all other conforming Revision-30 through Revision-37 behavior represented in the current specification and maintained tests.

# Handoff closure

The corrected handoff now closes the identified plan gaps:

- unsafe/default cases are defined by a positive semantic domain rather than an open-ended blacklist;
- classification is canonical rather than duplicated between default and production cleanup;
- the classification seam is explicitly fresh/post-revalidation/under-barrier;
- semantic engine incompatibility is whole-plan and order-independent;
- cleanup actions are bound back to exact current owner path and action-kind eligibility;
- maintenance, cache-directory, unknown-authorizer, malformed binding, and mixed-order siblings are explicit acceptance classes;
- acceptance asserts the intended domain guard fired rather than accidentally passing through stale-plan rejection;
- prior IR17 is provenance only, so snapshot loss cannot remove a still-open requirement.

**Design/workplan:** Revision 30 + Revision 37 + current storage specification + this corrected IR18 handoff are **CLOSED / implementation-ready**.

**Implementation:** executable `6391043b3641e007017d1781678c96a2b6b0d259` / tree `4055b67f2f86954b4355023cc84c9b0134a76e85` remains **NO-PASS / reopened under IR18**.
