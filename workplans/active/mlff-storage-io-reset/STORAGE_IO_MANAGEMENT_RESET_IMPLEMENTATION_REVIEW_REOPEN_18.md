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
scope: bounded R37 implementation correction for default-executor semantic-owner routing plus exact-candidate acceptance evidence
precedence: Revision 30, Revision 37, and refined IR17 remain the accepted design/workplan authority; this handoff supersedes IR17 only for work still open after executable candidate 6391043b and introduces no new product architecture
---

# Storage/I-O reset implementation review reopen 18 — default-executor owner-boundary closure

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

and changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`. Behavioral review therefore binds to executable tree `4055b67f...`; the PDF-only successor may inherit later behavioral evidence only after proving that executable identity remains unchanged.

Candidate `6391043b...` closes the principal IR17 implementation defects. Preserve its conforming work: plan-bound descriptor acquisition from the campaign anchor, opened-target identity checks, default single-file final identity, same-parent directory-entry durability, common owner root/container checks, final fd-relative `rmdir`, transition-exact publication/unlink behavior, exactly-once no-follow acquisition cleanup, ranked mount-refusal close, failed P7 session-acquisition ranking, typed member authority, and the existing R30-R37 mutation/byte/session semantics.

Two blocking closure families remain:

1. the exported/default `StorageExecutor.run(..., engine=None)` path can bypass semantic-owner mutation rules by sending owner-specific cleanup actions to the generic remover; and
2. the exact executable candidate has no recorded behavioral acceptance evidence satisfying IR17/R37 final closure.

Neither finding changes Revision-30/37 architecture. No Revision 38 is justified.

# IR18-1 — the default executor must not erase semantic-owner mutation authority

## Evidence and failure mechanism

`StorageExecutor.run()` is an exported consequential execution surface and accepts `engine=None`. When no engine is supplied it calls `_execute_actions()`.

The current `_execute_actions()` does the following for `ACTION_REMOVE` and `ACTION_EVICT_CACHE` after root-path authorization:

```text
authorize_path(action.path, snapshot)
  -> remove_planned_outcome(action, anchor=plan.workspace)
```

It does **not** consult the current `OwnerArtifactView`, `view.exact_authorizer`, `view.coverage`, `snapshot.authorized_members(view)`, owner `root_identity` / `path_identity`, retained members, or P7 live-session authority.

That is not equivalent to the production cleanup engine. `_cleanup_engine()` correctly distinguishes at least these materially different semantic owners:

- P7 released-attempt members use `P7_RELEASED_ATTEMPT_AUTHORIZER`, live `ReleasedAttemptSession`, authenticated proof/release/root identity, mutation-time target identity, typed proof, and same-attempt invalidation;
- common owner directories use `snapshot.authorized_members(view)` plus `remove_certified_subtree()`, preserving typed member authority, owner root/path identity, refusals, and retained/foreign descendants;
- only the residual generic case reaches `remove_planned_outcome()`.

`safe_candidates()` deliberately plans at the whole `OwnerArtifactView.path` when the owner says that artifact is reclaimable; member-level authority is applied later by the cleanup engine. Therefore root-path authorization alone is not descendant authorization. A valid cleanup plan can contain a P7 exact-authorizer action or a common container/closed-subtree action whose descendants are only partly authorized. Passing that same valid plan to the default executor currently discards those semantics and recursively removes whatever the generic walker finds under the plan-bound root.

This is a real authority bypass, not a testing preference. For a common container, a foreign or retained same-filesystem descendant that `snapshot.authorized_members()` would refuse can be unlinked by generic recursion. For P7, omission of the supplied engine bypasses the frozen live-session/proof and same-attempt invalidation owner even though the plan itself was produced from P7 authority.

The existing `engine=False` integration case does not close this claim. It drives a full cleanup plan through `StorageExecutor.run(..., engine=None)` only to inspect generic action-boundary failure accounting. It does not assert that P7/common owner semantics are retained, nor that the generic remover is unreachable for those actions. Such evidence can remain green while the semantic owner is bypassed.

## Required end state

- Omitting the optional engine may never widen or substitute the semantic owner that the plan requires.
- Before the first destructive transition, the default executor must determine whether **every** action in the plan is semantically eligible for its generic implementation. Any action requiring owner-specific mutation semantics must not reach `remove_planned_outcome()` merely because the caller omitted the specialized engine.
- At minimum, P7 `exact_authorizer` actions and common directory actions whose deletion authority depends on coverage/certified members/refusals/retained members/owner root or path identities are not generic-default actions.
- Root-path `authorize_path()` and `PlannedAction.filesystem_identity` remain necessary but are not substitutes for descendant/member/release authority.
- Prefer a fail-closed default-domain guard or one canonical semantic dispatch over duplicating the full production `_cleanup_engine()` inside `_execute_actions()`. The implementation should not create two drifting copies of P7/common routing.
- If the default engine is asked to execute a mixed plan containing any action outside its supported semantic domain, reject/refuse the unsupported execution **before any action mutates** rather than performing a convenient generic subset and leaving an accidental partial cleanup. A caller construction error must not spend part of the plan before discovering that the selected engine cannot honor the rest.
- Preserve the useful default generic leaf behavior required by R37/IR17: a genuinely generic plan-bound file/symlink action may still use the plan-bound fd-relative remover and same-parent durability path.
- Preserve production `_cleanup_engine()` behavior and every conforming P7/common path from candidate `6391043b...`.
- Do not introduce a second persistent authority, duplicate proof registry, inode registry, or new plan schema.

### Compatibility/caller census

Perform a bounded reference census of `StorageExecutor.run` and any wrapper exposing the default engine. Serena may be used when available; direct reference/source inspection is an acceptable equivalent.

If a maintained internal caller intentionally relies on `engine=None`, classify the actions it supplies and keep only behavior that is safe under the generic domain above. If evidence reveals a supported external contract that requires `engine=None` to execute owner-specific recursive cleanup, stop and reopen only this API/ownership surface rather than silently preserving an unsafe fallback.

## Mandatory acceptance

Acceptance must execute real inventory/planning, the real `StorageExecutor.run`, normal synchronization/revalidation, settlement, and durable audit. Test doubles may inject only below those owners.

1. **Common-container bypass counterfactual.** Build a real safe cleanup plan containing a reclaimable common/container action with at least one owner-authorized member and one retained/foreign/same-name unauthorized sentinel (a symlink or typed contradiction is suitable). Invoke the real executor with `engine=None`. The execution must refuse before mutation; the sentinel and authorized member both survive, and the generic recursive remover must be proven not to have run for the action.
2. **P7 exact-authorizer counterfactual.** Build a real released P7 cleanup plan and invoke the real executor with `engine=None`. It must not route a P7 action through `remove_planned_outcome()` or otherwise mutate without the P7 owner/session. The P7 scratch/proof state survives unchanged and the result/audit truthfully identifies the missing/incompatible semantic engine.
3. **Mixed-plan atomic guard.** Use a real plan containing one generic-default-eligible leaf action plus one owner-specific action. Engine-domain rejection occurs before the generic leaf is removed; no accidental partial cleanup is produced merely because the wrong engine was selected.
4. **Default generic liveness.** A plan containing only a genuinely generic single-file cleanup action still executes through `engine=None`, compares the complete plan-bound identity immediately before fd-relative unlink, persists through the same authenticated parent fd, credits exact bytes, and audits `complete`.
5. **Production routing regression.** The normal CLI/production cleanup engine still executes P7 and common actions through their existing semantic owners and generic actions through the generic remover; none of the IR17 authority/durability/close protections are weakened.
6. **Structural negative evidence.** Establish that no `engine=None` path can send an exact-authorizer/common typed-subtree action to the generic recursive remover. Validate any custom AST/Semgrep rule against a known-positive and known-negative construct before relying on zero findings.

# IR18-2 — exact-candidate functional closure is still unproven

The reviewed executable has no behavioral CI/status or other repository-accessible exact-candidate receipt. GitHub records only the successful `docs` check; the combined status has zero statuses. Source/test presence and the implementation commit message do not establish that the required suites actually executed after the last executable/test edit.

This remains blocking independently of IR18-1. After the last executable or test edit, bind all functional evidence to the exact final executable commit/tree.

## Stage-local closure for IR18

Treat IR18-1 as one coherent executable repair stage unless implementation evidence exposes a separate material owner boundary. Before final closure:

- perform semantic/conformance inspection of the default-engine domain and all maintained callers;
- run focused IR18 default-engine owner-boundary tests;
- run stage-local affected regression across executor, cleanup routing, common cleanup, P7 session/removal, generic leaf removal, settlement, and audit.

If a shared helper is changed in a way that can invalidate already-conforming IR17 acquisition/durability/close behavior, rerun those affected IR17 cases before proceeding.

## Final assembled evidence

After the **last** executable/test edit:

1. record the exact executable commit and tree and prove any later branch successor is non-executable before reusing evidence;
2. re-derive affected surface from the assembled diff plus callers/references of changed executor/routing/trust/removal helpers;
3. run focused IR18 plus all maintained R22-R37/IR17 storage and P7 namespace, release/root/target identity, opened-descriptor mount, final-rmdir, final-unlink identity, typed-common authority, transition truth, mutation/byte accounting, close/finalizer, concurrency, retry, and acceptance-liveness nodes;
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

6. include every maintained test/module discovered from the final affected-surface census that exercises `StorageExecutor.run`, cleanup routing, generic/common cleanup, P7 released-attempt removal/session, shared descriptor/trust/durability helpers, archive/catalog/journal publication, reclaim/restore, dedup, or maintenance behavior plausibly affected by the final diff;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for changed Python modules, repository-required static checks, `git diff --check`, and conflict-marker scan;
9. structurally re-establish the IR17 negative claims, including continuous anchored acquisition, opened target/owner identity checks, no unbound consequential leaf unlink, same-parent top-level durability, no direct close-before-structured-failure bypass, no double-close acquisition, transition callbacks at atomic syscalls, and every final consequential `rmdir` fd-relative/immediately identity-checked;
10. add the new IR18 negative proof: the default executor has a fail-closed semantic domain and cannot bypass `exact_authorizer` or typed/common subtree mutation authority;
11. validate the changed storage Markdown specification and its generated PDF derivative if permanent documentation changes again;
12. report commands/node selections and pass/fail/skip counts for the exact candidate. CI output, captured terminal output supplied with the implementation handoff, or an equivalent exact-candidate execution record is sufficient; do not create a new persistent evidence subsystem merely for ceremony.

Use the repository convention `conda run -n mace ...` where applicable. Full external DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Expected affected surface

Initially expect the bounded repair to touch:

- `mdstats/training_data/storage/executor.py` — default-engine domain/preflight and possibly one shared routing helper;
- `mdstats/training_data/storage/commands.py` only if factoring a canonical cleanup dispatch reduces duplicate authority; preserve production behavior;
- `tests/test_mlff_storage_reset_core.py` and/or `tests/test_mlff_storage_reset_integration.py` — real default-engine owner-boundary and structural acceptance.

`storage/inventory.py`, `storage/owners.py`, `qualification/store.py`, `storage/trust.py`, and `storage/durability.py` are regression surfaces but should not be edited unless the repair genuinely requires it. The final affected surface is re-derived from the assembled candidate and is not capped by this initial list.

# Implementation authority

## Frozen

- Revision-30/37 owner architecture and the refined IR17 capability/durability/close semantics.
- P7 released scratch is mutated only by the live P7 owner/session contract; plan/root authorization cannot substitute for proof/release/member authority.
- Common/container cleanup spends typed owner authority and retains everything the owner does not authorize.
- `PlannedAction.filesystem_identity` remains the plan's target identity and is independent of owner root/path/release/member authority.
- Wrong-engine/default-engine selection fails closed before mutation; omission of an implementation callback is never authority widening.
- No new persistent authority/control plane.
- Python `>=3.10`, existing four cleanup outcomes, accepted POSIX threat boundary, CampaignStore/P1-P7 science/currentness semantics, and archive/dedup/restore architecture remain unchanged.

## Delegated

- Exact internal representation of the default-engine eligibility/preflight predicate.
- Whether the safest low-complexity realization is a preflight guard in `StorageExecutor`, a shared semantic-dispatch helper used by both paths, or another equivalent internal factorization.
- Exact refusal/error wording for wrong-engine selection, provided no mutation occurs and durable evidence is truthful.
- Test seam and optional Serena/Semgrep/AST method for the bounded caller/structural census.

## Reopen design only on evidence

Reopen only this affected API/ownership surface if evidence proves that a supported external consumer contract requires `StorageExecutor.run(engine=None)` to execute owner-specific recursive/P7 cleanup and cannot be made safe by an internal fail-closed dispatch/guard without an incompatible public change. Ordinary internal refactoring, test inconvenience, or optional-tool absence is not a redesign trigger.

# Closure sequence

## Stage A — close the default-executor semantic-owner bypass

Perform the caller/domain census, implement the fail-closed domain or canonical dispatch, and add the common/P7/mixed-plan/generic-leaf real-owner counterfactuals. Complete semantic closure plus focused and stage-local affected regression before proceeding.

## Final assembled closure

Run IR18-2 against the exact final executable tree. A PASS requires both source/semantic closure and executed final evidence. Only then may the storage-I/O plan be marked complete and archived.

# Preserved conforming implementation

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
- shared `MutationLedger`, exact action evidence, zero-credit mutation truth, two-attempt isolation, and all other conforming Revision-30 through Revision-37 behavior.

# Final disposition

**Design/workplan:** Revision 30 + Revision 37 + refined IR17 + this bounded IR18 correction are **CLOSED / implementation-ready**.

**Implementation:** executable `6391043b3641e007017d1781678c96a2b6b0d259` / tree `4055b67f2f86954b4355023cc84c9b0134a76e85` is **NO-PASS / reopened under IR18**.
