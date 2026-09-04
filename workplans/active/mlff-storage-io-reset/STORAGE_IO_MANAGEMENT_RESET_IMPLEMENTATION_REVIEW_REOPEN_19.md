---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R37-IR19
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 37
reviewed_plan_commit: e3794d73b59095e07cf445061afcb262ea11092d
reviewed_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
reviewed_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
reviewed_branch_head: d035492a71652d562be7c23d0e1e77e8d5bb03c5
reviewed_branch_tree: 0b5a898308406f49cef3bc561584c12b1fc4b562
review_verdict: NO-PASS
scope: bounded R37 implementation correction for cleanup engine/action-family closure, explicit positive generic dispatch, and exact-candidate acceptance evidence
precedence: Revision 30, Revision 37, the current storage specification, and this IR19 handoff are the current normative implementation authority; IR18 and earlier review artifacts are historical provenance only
---

# Storage/I-O reset implementation review reopen 19 — action-family and positive-dispatch closure

## Disposition

**Reviewed executable: NO-PASS.**

The executable candidate is:

```text
commit  7aa938d71361d2cb2ce6e370165a9a12566669f3
 tree    5fd91f30672fb7d9a2be89d6e0fdc261619509aa
```

The branch successor is:

```text
commit  d035492a71652d562be7c23d0e1e77e8d5bb03c5
 tree    0b5a898308406f49cef3bc561584c12b1fc4b562
```

and changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`. Behavioral review therefore binds to executable tree `5fd91f30...`.

Candidate `7aa938d...` substantially implements corrected IR18. Preserve its conforming work: one canonical `cleanup_domain` classifier; fresh post-revalidation classification under the existing storage/owner barriers; action-to-current-owner path binding; current remove/evict eligibility checks; unknown exact-authorizer refusal; generic-leaf-only default domain; whole-plan domain preflight; real P7/common/maintenance/generic production routing; the already-conforming Revision-30/37 descriptor, durability, transition-truth, close-ranking, mutation-ledger, byte-accounting, and P7 session behavior.

Two blocking implementation/acceptance families remain. Neither changes the Revision-30/37 architecture, so no Revision 38 is created.

## Current supplied authority and snapshot completeness

The current implementation handoff is recoverable without prior chat, Git history, or superseded review files. The supplied normative set is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted final-apply design;
- `AUTHORITY_REVISION_37.md` — accepted bounded R37 authority;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract;
- this IR19 handoff — every still-open implementation and acceptance consequence after candidate `7aa938d...`.

IR18 remains historical provenance. Its already-satisfied semantics are represented by the current specification and the preserved implementation above; no still-open obligation depends on loading IR18.

# IR19-1 — engine selection must also bind the invocation action family

## Failure mechanism

The new classifier binds `ACTION_REMOVE` / `ACTION_EVICT_CACHE` to the current owner view, but it does not require the resolved `StoragePolicy.action` itself to be `cleanup` before returning a cleanup semantic class.

`StorageExecutor.run()` is a generic exported consequential executor. `revalidate_plan()` proves that the executor policy and the plan policy agree with each other, but it does not prove that an `ACTION_REMOVE` action belongs to that policy's action family. `build_storage_plan()` likewise accepts arbitrary `PlannedAction` sequences.

Therefore a malformed plan can be built under a non-cleanup policy (for example archive or deduplication), contain an owner-released generic `ACTION_REMOVE` leaf, pass ordinary policy/owner/filesystem revalidation, and then be accepted by `engine=None` as `CLASS_GENERIC_LEAF`. That spends cleanup deletion authority under an invocation that authorized a different storage action. An empty non-cleanup plan passed with `engine=None` can also currently pass the empty domain preflight and settle as `complete`, falsely reporting that the wrong engine executed the requested operation.

This violates the existing invocation-local/action-scoped authority contract. It is an implementation consequence of the accepted design, not a new product model.

## Required end state

- The cleanup classifier/default engine has an explicit **action-family domain**: cleanup semantic classes are valid only when the resolved/plan policy action is `ACTION_CLEANUP`.
- `engine=None` must refuse a non-cleanup policy **before any mutation**, even when the plan is empty.
- A non-cleanup plan containing `ACTION_REMOVE`, `ACTION_EVICT_CACHE`, maintenance, or another cleanup-classified action never becomes executable merely because the owner/path/target identity is otherwise valid.
- The canonical check belongs in the shared cleanup semantic owner or in an engine-level preflight that is impossible for either default or production cleanup to bypass; do not add a second unrelated policy/action predicate to one caller only.
- Existing specialized archive/dedup/restore engines remain unchanged and continue to execute their own action families through `StorageExecutor.run(..., engine=<specialized>)`.
- Preserve ordinary cleanup behavior and every conforming IR18 owner/path/action-kind check.

### Mandatory acceptance

1. **Cross-action remove counterfactual.** From a real fresh snapshot create a real owner-authorized generic cleanup leaf, but build the apply plan under a resolved non-cleanup policy and include an `ACTION_REMOVE` for that leaf. Invoke the real `StorageExecutor.run(..., engine=None)` with matching executor/plan policy and normal synchronization. Ordinary `revalidate_plan()` must be shown to get past policy-identity/action-equality checks; the cleanup action-family/domain guard then fires, the leaf survives, no action completes, and the durable audit is refused/nonmutating/zero-byte.
2. **Empty wrong-engine counterfactual.** A non-cleanup policy with an empty plan and `engine=None` is refused as an engine/action-family mismatch rather than settling `complete`.
3. **Cleanup liveness control.** The same real generic leaf under a genuine cleanup policy still executes through `engine=None` and retains the complete IR18 identity/durability/accounting behavior.
4. **Specialized-engine regression.** Normal archive, dedup, restore, and production cleanup command paths still supply and execute their specialized engines successfully; the new guard must not reject them merely because `StorageExecutor` is shared.
5. **Structural evidence.** Establish that the default cleanup engine cannot be entered successfully for a policy action other than cleanup. If a custom AST/Semgrep rule is used, validate it against a positive wrong-family example and a valid cleanup example.

# IR19-2 — eliminate residual generic fallthrough and make the structural proof real

## Failure mechanism

The semantic classifier is now canonical, but production cleanup still dispatches by handling maintenance, exact-authorizer, and owner-subtree classes and then treating the residual branch as `CLASS_GENERIC_LEAF`. Today the preceding `require_supported_domain()` call restricts the set enough that this is behaviorally equivalent, but the source still encodes the generic destructive path as negative fallthrough. Adding a future supported class without adding its dispatch branch would again route it to `remove_planned_outcome()`.

The new structural test does not actually prove dominance. Its helper marks a function safe when the function contains *some* classifier call plus *some* generic guard anywhere in its AST. It would remain green if the same function also contained an unrelated undominated call to `remove_planned_outcome()`. Its known-positive case omits the classifier entirely, so it does not exercise this false-negative shape.

That is inadequate for the exact family IR18 was created to close.

## Required end state

- Every consequential call to `remove_planned_outcome()` is reached only through an explicit positive `CLASS_GENERIC_LEAF` dispatch or an equivalently exhaustive construct whose residual/unreachable branch raises rather than mutates.
- In production cleanup, do not rely on "all other currently supported classes were already continued" as the destructive generic branch. Prefer an explicit `if item.semantic_class == CLASS_GENERIC_LEAF:` branch followed by an impossible/defensive `StorageEngineDomainError` (or equivalent) for any residual class.
- In the default engine, the plan-wide single-class preflight remains required; an explicit per-item generic assertion/branch is preferred so future domain widening cannot silently turn the loop into a fallback.
- Keep the canonical classifier single-owned. Do not reintroduce P7/coverage/owner-specific classification logic in `commands.py` or `executor.py`.

### Mandatory acceptance

1. **Structural dominance/branch proof.** Prove every cleanup-path `remove_planned_outcome()` call is syntactically/control-flow guarded by the positive generic class, or use a simpler exhaustive dispatch shape that makes this evident by inspection.
2. **Rule liveness.** If retaining the custom AST rule, add a known-bad construct that contains a legitimate classifier/preflight *and also* an undominated generic call; the rule must flag it. Keep a known-good explicit generic branch that the rule accepts. Merely testing a function with no classifier is insufficient.
3. **Impossible residual.** A focused test/inspection demonstrates that an unexpected semantic class reaching the dispatcher cannot mutate; it fails closed instead.
4. Preserve all IR18 common/P7/mixed-order/maintenance/cache/action-owner/owner-eligibility/unknown-authorizer/generic-liveness/production-routing cases.

# IR19-3 — exact-candidate functional closure remains mandatory

GitHub records only the successful `docs` check for executable candidate `7aa938d...`; the combined commit status has no behavioral statuses. The repository contains substantial new IR18 tests, but source presence is not execution evidence. Local independent execution was attempted during review but the review runtime could not resolve `github.com`, so it could not clone the candidate and cannot substitute for Implementation's required exact-tree run.

After the last executable or test edit, bind all evidence to the exact final executable commit/tree.

## Stage-local closure

Treat IR19-1 and IR19-2 as one coherent cleanup-domain closure stage unless implementation evidence exposes a separate material API boundary. Before final closure:

- complete semantic/conformance inspection of action-family binding and explicit positive dispatch;
- run the new focused cross-action/empty-plan/dispatch-rule tests;
- rerun the existing IR18 classifier/default-engine/production-routing acceptance;
- run stage-local affected regression across executor, cleanup-domain, commands, planning/revalidation, inventory/owners, common cleanup, P7 session/removal, maintenance, generic leaf removal, settlement, and audit.

## Final assembled evidence

After the **last** executable/test edit:

1. record the exact final executable commit and tree and prove any later branch successor is non-executable before reusing evidence;
2. re-derive affected surface from the assembled diff plus callers/references of changed executor/cleanup-domain/commands/plan helpers;
3. run focused IR19/IR18 plus all maintained R22-R37 storage and P7 namespace, release/root/target identity, mount, final-rmdir, final-unlink identity, typed-common authority, transition truth, mutation/byte accounting, close/finalizer, concurrency, retry, and liveness nodes affected by the final diff;
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

6. include every maintained module discovered by the final affected-surface census that exercises `StorageExecutor.run`, cleanup-domain/routing, generic/common cleanup, P7 released-attempt removal/session, maintenance, shared descriptor/trust/durability helpers, archive/catalog/journal publication, reclaim/restore, dedup, or other callers plausibly affected by the final diff;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for changed Python modules, repository-required static checks, `git diff --check`, and conflict-marker scan;
9. structurally re-establish the preserved Revision-30/37/IR18 negative claims: anchored descriptor acquisition; opened target/owner identity; no unbound consequential leaf unlink; same-parent durability; exactly-once close/finalization; transition callbacks at atomic syscalls; final fd-relative/identity-checked rmdir; one canonical cleanup classifier; no wrong-action-family default execution; and no residual generic fallthrough;
10. validate the changed storage specification and generated PDF derivative if permanent Markdown changes again;
11. report commands/node selections and pass/fail/skip counts for the exact candidate. CI output, captured terminal output supplied with the implementation handoff, or equivalent exact-candidate execution output is sufficient. Do not create a persistent evidence subsystem merely for ceremony.

Use `conda run -n mace ...` where applicable. Full external DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Expected affected surface

Initially expect:

- `mdstats/training_data/storage/cleanup_domain.py` — action-family validation;
- `mdstats/training_data/storage/executor.py` — default-engine wrong-family/empty-plan preflight and explicit generic assertion if realized there;
- `mdstats/training_data/storage/commands.py` — explicit positive production generic dispatch / defensive residual;
- `tests/test_mlff_storage_reset_core.py` and/or `tests/test_mlff_storage_reset_integration.py` — cross-action, empty-plan, structural-rule liveness, and preserved IR18 regression.

`storage/plan.py`, inventory/owners, qualification/store, trust/durability, archive/dedup/restore/maintenance are regression surfaces and should not be edited unless evidence shows the narrow repair requires it. Re-derive the final affected surface from the assembled candidate.

# Implementation authority

## Frozen

- Revision-30/37 owner architecture and the current storage specification.
- Invocation-local action authority: an archive/dedup/restore invocation cannot spend cleanup deletion authority merely because it uses the shared executor.
- One canonical cleanup semantic classifier and positive default domain.
- P7 exact-authorizer actions spend only the live P7 session owner; owner-scoped subtrees spend typed/member/root/path authority; generic leaves spend only plan-bound target identity plus existing synchronization.
- Wrong-engine/action-family/domain selection fails before mutation and is durably audited as nonmutating refusal.
- No residual destructive generic fallthrough from an unmatched semantic class.
- Existing plan-bound descriptor, same-parent durability, mutation truth, exact byte accounting, close ranking, archive/restore publication, P7 session, CampaignStore/P1-P7 science/currentness, Python `>=3.10`, and accepted POSIX threat-boundary semantics remain unchanged.
- No new persistent authority/control plane.

## Delegated

- Exact placement of the cleanup-policy action-family predicate.
- Whether exhaustive dispatch is implemented with explicit `if`/`elif`, `match`, typed handler mapping, or equivalent, provided the generic destructive branch is positively named and residual classes fail closed.
- Exact internal error wording and structural-test mechanism.

## Reopen design only on evidence

Reopen only the affected API/ownership surface if a maintained external/public consumer genuinely requires `StorageExecutor.run(engine=None)` to execute non-cleanup policies or owner-specific cleanup semantics and cannot be made safe without an incompatible public change. Internal tests, convenience callers, or the existing unsafe fallback are not such evidence.

# Closure sequence

## Stage A — action-family and explicit dispatch closure

Implement IR19-1/IR19-2 together, add the focused tests, and complete semantic plus stage-local affected regression.

## Final assembled closure

Run IR19-3 against the exact final executable tree. A PASS requires both semantic/source closure and executed final evidence. Only then may the storage-I/O workplan be marked complete and archived.

# Final disposition

**Design/workplan:** Revision 30 + Revision 37 + current storage specification + IR19 are **CLOSED / implementation-ready**.

**Implementation:** executable `7aa938d71361d2cb2ce6e370165a9a12566669f3` / tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa` is **NO-PASS / reopened under IR19**.
