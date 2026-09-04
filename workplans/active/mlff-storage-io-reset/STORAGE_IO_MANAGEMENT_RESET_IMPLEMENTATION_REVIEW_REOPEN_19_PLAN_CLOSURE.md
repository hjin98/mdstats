---
kind: implementation-review-plan-closure
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R37-IR19
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: closed-implementation-ready
reviewed_date: 2026-09-03
reviewed_authority_revision: 37
reviewed_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
reviewed_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
review_verdict: NO-PASS
scope: plan-closure refinement for IR19 action-family totality, dispatch completeness, structural proof, and final evidence
precedence: this file is a current normative companion to STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md; where wording differs, this closure refinement governs
---

# IR19 plan-closure refinement

## Disposition

The executable candidate remains **NO-PASS** under IR19. Revision 30, Revision 37, and the current storage specification remain accepted. No Revision 38 and no IR20 are created.

The original IR19 diagnosis is sound, but a second handoff review found four places where its implementation contract could still be satisfied too narrowly. This refinement closes those plan-level gaps without changing the frozen product model.

The current bounded implementation contract is the union of:

- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md`; and
- this plan-closure refinement.

IR18 and earlier review artifacts remain historical provenance only.

# IR19-C1 — cleanup action-family authority is a plan-level total invariant

The action-family rule cannot live only inside per-action classification. An empty plan has no action to classify, and maintenance is currently recognized before leaf eligibility. Therefore a local `if policy.action != cleanup` added only to the generic-leaf branch, or only to `StorageExecutor._execute_actions`, is not sufficient closure.

## Required end state

1. **Plan-level gate before action iteration.** The canonical cleanup semantic owner must reject any plan whose resolved policy action is not `ACTION_CLEANUP` **before inspecting or dispatching individual actions**. The gate must run for an empty plan as well as a nonempty one.
2. **Shared by both cleanup execution paths.** Both `StorageExecutor.run(..., engine=None)` and production `_cleanup_engine(...)` must consume the same plan-level cleanup-family gate. Do not repair only the default engine while leaving the production cleanup engine callable on a non-cleanup plan.
3. **All semantic classes are covered.** The action-family gate precedes maintenance, exact-authorizer, owner-subtree, generic-leaf, invalid, and any future cleanup semantic class. A non-cleanup plan containing maintenance is just as out of domain as one containing `ACTION_REMOVE`.
4. **Standalone classifier consistency.** `classify_cleanup_action(...)` is exported and must not positively classify a cleanup semantic class when called with a non-cleanup policy. It may return `invalid` or raise the same typed cleanup-domain/family error, but it may not report `generic_leaf`, `maintenance`, `owner_subtree`, or `exact_authorizer` under an archive/dedup/restore/report policy. The plan-level gate remains mandatory for empty-plan totality.
5. **Genuine empty cleanup remains valid.** A genuinely empty `ACTION_CLEANUP` plan is a legitimate no-op and retains the existing successful/no-mutation settlement semantics. The repair must distinguish `empty cleanup` from `wrong-family empty plan`; it must not implement `empty means refuse`.
6. **No second authority.** The plan-level action-family decision belongs in the canonical cleanup semantic owner (for example `classify_cleanup_plan`/a shared cleanup-domain preflight) or an equivalent single mechanism that both cleanup engines must traverse. Caller-local action tests are defense in depth at most and do not establish closure.
7. **Specialized engines stay specialized.** Archive, deduplication, restore, and other specialized engines continue to use the shared `StorageExecutor` authorization shell for their own policy/action families and are not forced through cleanup classification.

## Mandatory acceptance

A. **Default-engine cross-action removal.** Under a real fresh snapshot, construct a non-cleanup policy/plan containing a real owner-authorized generic cleanup leaf and `ACTION_REMOVE`; run the real `StorageExecutor.run(..., engine=None)`. Ordinary plan/policy revalidation must succeed far enough that the intended cleanup-family guard is the refusal. No mutation, no completed action, zero reclaimed bytes, durable refused audit.

B. **Default-engine empty wrong-family plan.** A non-cleanup empty plan with `engine=None` is refused by the same cleanup-family guard. This proves the guard is plan-level rather than merely per-action.

C. **Production-cleanup wrong-family plan.** Invoke the real production cleanup engine through `StorageExecutor.run` on a deliberately malformed non-cleanup plan built from a real snapshot. Use either a generic leaf or maintenance action. It must refuse before owner dispatch or mutation. This proves the production path cannot bypass the canonical family guard.

D. **Standalone classifier wrong-family control.** A focused test calls the exported single-action classifier with otherwise-valid cleanup owner semantics but a non-cleanup policy. It must not return a positive cleanup class.

E. **Empty-cleanup liveness.** A genuine empty cleanup plan executes/settles according to the existing valid no-op cleanup semantics and is not rejected merely because there are zero actions.

F. **Generic cleanup liveness.** Preserve the existing real generic-leaf `engine=None` liveness case under an actual cleanup policy, including complete plan-bound identity, fd-relative unlink, same-parent durability, exact bytes, and audit.

G. **Specialized-engine regression.** Normal archive, dedup, restore, and production cleanup command paths continue to use their intended engines and are not rejected by the cleanup-family gate.

# IR19-C2 — supported domain and dispatch must be one coherent closed set

IR19 correctly requires an explicit positive generic branch. One further drift mode must be excluded: the preflight's `supported=(...)` set and the dispatch implementation cannot evolve as unrelated authorities. Otherwise a future class can be added to the accepted domain without adding its handler. A defensive residual raise prevents unsafe mutation, but leaving two silently divergent definitions still recreates avoidable routing debt.

## Required end state

1. **Explicit positive generic branch.** In every consequential cleanup dispatcher, `remove_planned_outcome()` is reached only from an explicit `CLASS_GENERIC_LEAF` branch or an equivalently explicit handler mapping keyed by that class. No residual `else`/fallthrough may mutate generically.
2. **Residual fails closed.** Any semantic class that reaches a dispatcher without a handler produces a typed domain/dispatch failure before destructive work. The residual branch never calls a remover.
3. **Preflight/dispatch alignment.** The semantic classes an engine claims to support and the classes for which it has handlers must be mechanically shared or explicitly checked for equality/completeness. Acceptable low-complexity forms include a handler map whose keys are also the supported domain, or a focused invariant test proving the declared supported set equals the explicit handled classes. Do not maintain two unverified lists.
4. **Default engine remains one-class.** The default cleanup engine's destructive domain is exactly `CLASS_GENERIC_LEAF`. If its loop retains a generic-only preflight, each iterated item must still be asserted/branched as generic rather than relying on the loop body itself as future fallback.
5. **Canonical classifier remains single-owned.** No P7 authorizer, coverage, member, root/path, cache, or owner-specific semantic classification is reintroduced in `commands.py` or `executor.py`.

## Mandatory acceptance

A. **Dispatch completeness invariant.** A focused test or source check establishes that each engine's accepted semantic-class set equals its explicit handler set, except any deliberately non-destructive administrative class that is separately dispositioned. A future supported class with no handler must fail this check or fail closed, never reach generic removal.

B. **Residual nonmutation.** Demonstrate by focused test or directly inspectable exhaustive source shape that an unexpected semantic class reaching either cleanup dispatcher cannot mutate.

C. **Preserved IR18 real-owner routing.** P7 exact-authorizer actions still reach the live P7 session owner; owner-subtree actions still use typed/member/root/path authority; maintenance still reaches its owner; generic leaves alone reach the generic remover.

# IR19-C3 — structural negative evidence must cover call sites, aliases, and false negatives

The earlier AST rule was too weak because function-level co-occurrence of a classifier call and a guard does not establish dominance. The replacement evidence must be bounded but actually capable of detecting the forbidden family.

## Required closure basis

1. Perform a bounded reference census for consequential cleanup routing over:
   - every production `StorageExecutor.run` call/wrapper;
   - every direct or aliased reference/call to `remove_planned_outcome` reachable from production cleanup/default execution;
   - every consumer of the canonical cleanup classifier/plan preflight in `mdstats/training_data/storage` and any repository caller discovered by references.
2. Disposition each production `StorageExecutor.run` caller by engine family. No production caller may rely on `engine=None` for owner-specific or non-cleanup work. A deliberate generic-cleanup `engine=None` caller is acceptable only if it remains inside the positive cleanup/generic-leaf domain.
3. Disposition each consequential generic-remover call. Every one must be control-flow dominated by the explicit generic class or live in a lower-level compatibility/helper context that cannot be reached as unclassified consequential cleanup. The public convenience helper itself is not forbidden; an unclassified production cleanup route to it is.
4. If an AST/Semgrep/custom rule is used, its liveness suite must include:
   - a known-bad function that performs legitimate classifier/preflight work **and also contains an undominated generic-remover call**; the rule must flag it;
   - a known-good explicit `CLASS_GENERIC_LEAF` branch with a fail-closed residual; the rule must accept it;
   - the actual production modules in scope.
5. State the rule's scan scope and limitations. Zero findings outside that defined scope are not claimed as proof of repository-wide absence.

Serena/Semgrep may accelerate the census where available; direct AST/reference/source inspection is an acceptable equivalent. No persistent census database or linter is required.

# IR19-C4 — exact-candidate evidence and snapshot closure

The final evidence requirements in IR19 remain mandatory. The following refinements close ambiguity about what must be fresh after the final executable/test edit.

1. The exact candidate is the final executable commit/tree after the action-family/dispatch code **and acceptance tests** are complete. A later docs/PDF-only successor may inherit behavioral evidence only after proving the executable tree is unchanged.
2. Stage-local closure for IR19-C1/C2 includes focused family tests plus affected regression over executor, cleanup-domain, production cleanup routing, plan/revalidation, owner inventory/classification, common cleanup, P7 session/removal, maintenance, generic leaf mutation, settlement, and audit.
3. Final assembled closure reruns the complete affected-surface regression and real-boundary integration after the last executable/test edit. At minimum retain the complete core/integration and owner-regression suites named in IR19, plus any additional maintained callers discovered by the final census.
4. Record command/node selection and pass/fail/skip counts. Source comments, commit messages, test presence, or a docs-only CI status are not behavioral execution evidence.
5. Re-run structural evidence on the exact final tree, including:
   - cleanup family gate is plan-level and precedes per-action dispatch;
   - standalone classifier does not positively classify non-cleanup policies;
   - empty non-cleanup default execution cannot settle complete;
   - default and production cleanup consume the same cleanup-family gate;
   - supported-domain and handler sets are aligned;
   - every consequential generic-remover call is explicitly generic-class dominated;
   - no residual destructive generic fallthrough remains.
6. Preserve the Revision-30/37 descriptor, durability, transition callback, close/finalizer, mutation-truth, byte-accounting, and P7-session structural claims already named in IR19.
7. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Implementation authority

## Frozen

- Revision 30, Revision 37, and the current storage specification.
- Invocation-local action authority: cleanup semantic authority is valid only inside an `ACTION_CLEANUP` execution family.
- The cleanup-family gate is plan-level, applies to empty and nonempty plans, precedes per-action class recognition, and is shared by default and production cleanup.
- The exported single-action classifier may not positively classify cleanup work under a non-cleanup policy.
- Genuine empty cleanup is a valid no-op; wrong-family empty execution is not.
- One canonical positive cleanup classifier; no duplicated owner classification.
- One coherent supported-domain/dispatch definition per cleanup engine, with explicit generic handling and fail-closed residual behavior.
- No consequential generic-remover call without explicit generic-class dominance.
- All previously frozen Revision-30/37/IR18 descriptor, durability, close-ranking, mutation truth, byte accounting, publication, P7 session, CampaignStore/P1-P7 science/currentness, Python `>=3.10`, and POSIX threat-boundary semantics remain unchanged.
- No new persistent authority/control plane.

## Delegated

- Whether the plan-level cleanup-family guard is implemented inside `classify_cleanup_plan`, a shared `require_cleanup_family(...)`, or an equivalent canonical preflight traversed by both cleanup engines.
- Whether wrong-family standalone `classify_cleanup_action` returns `invalid` or raises the typed domain error, provided it never returns a positive cleanup class.
- Whether dispatch alignment uses a handler mapping, exhaustive `if`/`elif` plus equality test, `match`, or equivalent low-complexity mechanism.
- Exact structural-analysis tool and internal error wording.

## Reopen design only on evidence

Reopen only the affected API/ownership surface if a maintained external/public consumer genuinely requires one of the following and cannot be migrated safely without an incompatible public contract:

- `StorageExecutor.run(engine=None)` executing a non-cleanup policy;
- production `_cleanup_engine` executing a non-cleanup policy;
- the exported cleanup classifier positively classifying non-cleanup policies; or
- an unclassified consequential cleanup caller directly invoking the generic remover.

Existing unsafe behavior, internal tests, convenience callers, or lack of an optional analysis tool are not redesign evidence.

# Closure sequence

## Stage A — total action-family + dispatch-family closure

Implement IR19-C1 and IR19-C2 together. Complete the bounded caller/remover census and structural liveness from IR19-C3. Run focused tests and stage-local affected regression before proceeding.

## Final assembled closure

Run IR19-C4 and the original IR19 final evidence contract on the exact final executable tree. A PASS requires both semantic/source closure and executed functional evidence. Only then may the storage-I/O workplan be closed and archived.

## Final disposition

**Design/workplan:** Revision 30 + Revision 37 + current storage specification + IR19 + this closure refinement are **CLOSED / implementation-ready**.

**Implementation:** executable `7aa938d71361d2cb2ce6e370165a9a12566669f3` / tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa` remains **NO-PASS / reopened under IR19** until the refined obligations and exact-candidate evidence close.