---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R37-IR17
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 37
reviewed_plan_commit: ecf9feecefaac2612d36db8f656d7fec2d7a81b6
reviewed_executable_commit: 9db97f72a6ba033aa4b092edb0ece39db56f5b23
reviewed_executable_tree: a09dabfe5eb7279adb9398a98f9349c9713962a8
reviewed_branch_head: bd4b78e59f0b500ac130597943adab5e07fcad4b
reviewed_branch_tree: 683fcc2324780a6f9b3dba4aab98f949090529e4
review_verdict: NO-PASS
scope: bounded R37 implementation correction for continuous authenticated root acquisition, close-ranking completeness, real-owner acceptance, and exact-candidate evidence
precedence: Revision 30 and Revision 37 remain the accepted design/workplan authority; this file is snapshot-complete for the still-open implementation/review work after candidate 9db97f72 and does not create new product semantics
---

# Storage/I-O reset implementation review reopen 17 — R37 candidate review

## Disposition

**Reviewed executable: NO-PASS.**

The executable candidate is:

```text
commit  9db97f72a6ba033aa4b092edb0ece39db56f5b23
 tree    a09dabfe5eb7279adb9398a98f9349c9713962a8
```

The branch successor is:

```text
commit  bd4b78e59f0b500ac130597943adab5e07fcad4b
 tree    683fcc2324780a6f9b3dba4aab98f949090529e4
```

and changes only the generated storage-specification PDF. Behavioral findings therefore bind to executable tree `a09dabfe...`.

The candidate closes substantial Revision-37 work: unlink/publication transition callbacks now occur at the actual syscall transition, archive blob/manifest/catalog phases and restore-journal phases are wired through those callbacks, the final directory-removal helper compares the name against the still-open directory descriptor, typed common-member authority is present, P7 session invalidation is one-way, and the core/integration suites contain materially stronger counterfactuals.

Three blocking families remain. They are violations of requirements already explicit in R37-2, R37-3, R37-4, and R37-5. **No new authority revision or product redesign is justified.** Repair the bounded implementation below and preserve all conforming R37 work.

## Review method and evidence boundary

The review reconciled the exact candidate against:

- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md`;
- `AUTHORITY_REVISION_37.md`;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_16.md`;
- `docs/specs/training_data/mlff_storage_management_spec.md`;
- the changed storage/P7 owners and the core/integration acceptance source.

The review runtime did not expose a usable Serena/Semgrep repository runtime. They remain optional Protocol-5.10 evidence helpers, so their absence is not a product blocker. Direct source/reference and structural-pattern inspection was used instead. A focused Semgrep/Serena census may be added when available, but it may not replace the real-owner tests below.

GitHub records only the successful documentation-PDF workflow for executable commit `9db97f72...`; no behavioral CI/status or committed exact-candidate test receipt records the mandatory affected regression/integration pass. The implementation commit message is not execution evidence.

# IR17-1 — destructive root acquisition still drops authenticated identity before traversal

R37 correctly repaired the **final** `rmdir` boundary, but two destructive acquisition paths still begin from a pathname check followed by a fresh absolute/multi-component open. The opened descriptor is not proved to be the exact object the action/owner authorized.

## IR17-1A — generic / fully-certified recursive cleanup can acquire a replacement root

Current generic flow is effectively:

```text
remove_durably_outcome(path)
  -> path.lstat()
  -> _remove_tree_tracked(path)
       -> open_directory_nofollow(str(path.parent))
       -> open_directory_nofollow(path.name, dir_fd=parent_fd)
       -> verify_opened_directory_trust(parent_fd, root_fd, path)
       -> recurse / final identity check / fd-relative rmdir
```

`verify_opened_directory_trust()` proves mount/device trust for the object that was opened. It does **not** prove that the opened root is the object observed by the plan/revalidation or by the earlier `lstat`. A same-device plain-directory replacement between the earlier observation and the authority-bearing open can therefore become the object traversed and removed. The final pre-`rmdir` comparison only protects replacements **after** that new descriptor was accepted; it cannot repair an already-transferred authority at acquisition.

The fully-certified common path reaches the same recursive implementation and inherits this gap.

### Required end state

- The consequential executor must hand the recursive owner the plan-bound target identity (`PlannedAction.filesystem_identity`) or an engineering-equivalent exact bound identity. Do not make the executor fall back to an unbound destructive call when that identity exists.
- Acquire the action root from a descriptor whose ancestry is itself authenticated. A fresh absolute/multi-component `open_directory_nofollow(str(path.parent))` is not sufficient authority because `O_NOFOLLOW` protects only the final component of that open and the opened parent is not compared to a bound identity.
- Use a componentwise no-follow descent from an accepted campaign/owner anchor, a retained authenticated parent capability, or an engineering-equivalent mechanism that proves the actual opened ancestry rather than a prior pathname observation.
- Compare the actual opened target descriptor's kind/device/inode with the plan-bound target identity **before enumeration or mutation**. A mismatch/disappearance is a no-change refusal; it never transfers authority to the replacement.
- Retain that authenticated parent/target capability through the existing final identity check and fd-relative `rmdir`.
- The thin public compatibility remover may keep a non-plan-bound convenience mode only if it cannot be reached by consequential `StorageExecutor` execution; do not weaken the executor path for compatibility.

### Mandatory acceptance

Through real inventory/planning, cleanup engine, `StorageExecutor.run`, settlement, and durable audit:

1. build a real generic recursive action, let ordinary plan revalidation succeed, then replace its top-level directory with a same-name/same-device plain directory immediately before authority-bearing acquisition; the replacement sentinel survives and the action is refused/nonmutating;
2. repeat with a replacement of an ancestor used by the acquisition path; no descendant of the replacement is traversed or mutated;
3. run the fully-certified common equivalent;
4. assert the injected acquisition seam fired and that the refusal came from comparison of the **opened** descriptor to the bound identity, not from a pre-open pathname check;
5. preserve the existing post-open/pre-`rmdir` replacement counterfactual so both sides of the capability lifetime are covered.

## IR17-1B — individually-authorized common cleanup still has check-then-reopen authority

`remove_certified_subtree()` currently `lstat`s the authority root/container and compares those pathname observations with `authority_identity` / `root_identity`. When refusals require individually-authorized descent, `_remove_authorized_members()` then performs a later:

```text
open_directory_nofollow(str(path.parent))
open_directory_nofollow(path.name, dir_fd=anchor_fd)
verify_opened_directory_trust(anchor_fd, container_fd, path)
```

The reopened `anchor_fd` and `container_fd` are not compared against `authority_identity` and `root_identity`. A same-device replacement after the precheck but before these opens can therefore inherit the earlier authorization. This is the exact check-to-use gap R37-2B required the descriptor handoff to close.

### Required end state

- Pathname `lstat` may remain an early refusal optimization, but it may not be the mutation-time authority.
- Acquire the authority root through authenticated descriptor-relative ancestry and compare the **opened** authority-root descriptor to `authority_identity` before opening the common container.
- Open the container relative to that authenticated descriptor and compare the **opened** container descriptor to `root_identity` before any member descent.
- Apply canonical opened-descriptor mount trust to those actual descriptors and to every intermediate directory, preserving the existing typed-member rule.
- Keep the action-wide `MutationLedger` across earlier successful members and a later acquisition/identity contradiction.

### Mandatory acceptance

Through real cleanup planning/execution/audit, inject a replacement specifically between the precheck and the authority-bearing open for both the authority root and the container. Use same-kind, same-device plain directories with authorized-looking member names. The replacement and sentinels must survive; any earlier genuine prefix mutation must remain exactly attributed.

# IR17-2 — close/finalization handling still has bypasses and a double-close shape

R37 established the correct close-ranking doctrine, but not every changed path uses it.

## IR17-2A — recursive mount refusal closes outside the canonical ranking path

In `storage/executor.py::_remove_tree_contents()`, after a child directory is opened and `verify_opened_directory_trust()` refuses it, the implementation directly executes:

```text
os.close(child_handle)
raise ledger.failure(MountBoundaryError(...), ...)
```

The close occurs **before** the structured mount-refusal failure is constructed. If that close itself fails, raw `OSError` escapes first. After an earlier sibling/prefix mutation, the current action's `MutationLedger` can therefore fail to cross the action boundary, allowing the executor to audit a no-mutation interruption even though this action already changed the namespace.

### Required end state

- Construct the intended structured mount-refusal failure/outcome first.
- Close the child through `_close_descriptor()` (or the one canonical equivalent) with that primary already active.
- Preserve the mount/authority failure as primary; record/log close failure only as secondary evidence.
- If there was an earlier action-local mutation, the primary must carry the exact `MutationLedger` partial state to `record_or_reraise()`.
- Remove direct close-before-outcome branches from every generic/common/P7 destructive path after a capability has entered an action ledger.

### Mandatory acceptance

Use a real cleanup action with an earlier certified sibling removed first, followed by a child refused as a mount. Inject failure of the refused child's close. Assert through `StorageExecutor.run` and audit:

- the earlier prefix is recorded as partial mutation with exact bytes;
- the mount/authority refusal remains the primary product cause;
- the close failure is secondary evidence;
- no external/mounted sentinel is touched.

Also run the no-prefix control: no fabricated mutation or byte credit.

## IR17-2B — `open_directory_nofollow()` can attempt to close the same descriptor twice

The shared trust primitive currently has the shape:

```text
if opened fd is not a directory:
    os.close(handle)
    raise NamespaceAmbiguity(...)
except OSError:
    os.close(handle)
    raise NamespaceAmbiguity(...)
```

If the first close raises `OSError`, control enters the `except OSError` and attempts `os.close(handle)` again. A failed close is an ambiguous kernel/resource event; retrying the same integer can close a descriptor the kernel has already released/reused and directly violates R37's exactly-once capability finalization rule.

### Required end state

- Refactor the helper to have one explicit descriptor-ownership state and at most one kernel close for every descriptor it acquires unless ownership is deliberately transferred to the caller.
- A failed `fstat` or wrong-kind observation is the primary namespace/authentication failure. Attempt cleanup exactly once; a cleanup-close failure may be attached/logged as secondary evidence but may not trigger a second close or replace the primary classification.
- Once a valid directory descriptor is returned, ownership is transferred and the helper performs no close.
- Because this primitive is shared by generic/common/P7 paths, re-run the destructive acceptance after the repair rather than treating it as a local unit-only change.

### Mandatory acceptance

Instrument `os.close` and prove a wrong-kind/fstat-failure acquisition attempts closure exactly once even when that close itself raises. Prove the primary namespace/authentication failure remains visible and no recycled descriptor can be closed by a second attempt.

## IR17-2C — close-family census before reseal

Perform a bounded structural census of `storage/executor.py`, `storage/trust.py`, `qualification/store.py`, and `storage/commands.py` for raw `os.close` in consequential acquisition/destructive/session-finalization paths.

- Raw closes in purely observational readers need not be rewritten merely for stylistic uniformity.
- Any close that can occur after an action-local mutation, while a structured refusal/failure is already active, or while spending a mutation capability must use the R37 primary/secondary policy.
- In particular, verify session-acquisition cleanup does not replace an active owner/authentication failure with a close failure and that no path can close the same descriptor twice.

If Serena/Semgrep is available to the implementer, use it for this bounded family census; direct AST/reference inspection is an acceptable equivalent. Tool absence does not waive the resulting claim.

# IR17-3 — acceptance is still incomplete at the semantic owner boundary

The candidate adds many useful R37 tests, but several of the new generic/common close and mount tests still use the helper `_drive_removal()`. That helper constructs `StorageExecutionResult` by hand and invokes `record_or_reraise()` directly. It does not execute real inventory/planning, `StorageExecutor.run`, synchronization/revalidation, settlement/finalization, or durable audit.

That is useful unit evidence, but R37-4 explicitly requires real planner/owner/executor/audit acceptance for the material cleanup claims. A helper-level green test is especially insufficient here because the source defects above live at the handoff between earlier plan/path identity and the later opened capability.

### Required acceptance repair

Keep the helper tests if useful, but add/convert owner-boundary tests for every material R37 cleanup claim, including:

- generic and fully-certified root acquisition/replacement;
- individually-authorized authority-root/container replacement between precheck and open;
- mount-refusal close failure after a mutated prefix and its no-prefix control;
- generic/common close-only post-mutation and pre-mutation cases;
- final post-open/pre-`rmdir` substitution;
- resolver unavailable and same-device mount cases;
- typed-member absence/replacement cases.

For each, real production planning/authorization and `StorageExecutor.run`/audit remain in the path. Inject only the lowest filesystem/trust/close timing seam needed to create the counterfactual, and assert that seam fired.

The real-owner archive publication/restore-journal and P7 integration tests added by the candidate are preserved; do not regress them while repairing cleanup.

# IR17-4 — exact-candidate behavioral evidence is absent

The exact executable candidate has no recorded behavioral CI/status; GitHub records only the documentation-PDF workflow. Revision 37 requires fresh executed functional evidence bound to the final executable tree. Source inspection and test source are not substitutes for running the tests.

After the **last executable or test edit**:

1. record the final executable commit and tree;
2. re-derive the affected surface, including all callers of changed descriptor/trust/removal helpers;
3. run focused IR17 plus all R22-R37 storage/P7 publication, namespace, mount, final-rmdir, mutation-truth, close/finalizer, concurrency, retry, and liveness nodes;
4. run complete:

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

5. run the previously required owner regressions:

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

6. include every maintained module/node discovered from the final candidate that exercises changed durability, catalog/journal publication, archive/reclaim/restore, dedup/maintenance, generic/common cleanup, or P7 released-attempt removal/session;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for every changed Python module, repository-required static checks, `git diff --check`, and conflict-marker scan;
9. structurally prove at minimum:
   - no consequential absolute/multi-component destructive anchor is treated as authenticated merely because its final component was opened no-follow;
   - actual opened generic/common roots are compared with the bound identity before traversal;
   - no direct close-before-structured-outcome remains in destructive paths;
   - no descriptor acquired by `open_directory_nofollow` can be closed twice;
   - no post-failure pathname disappearance inference or signature-incompatible unlink fallback has returned;
   - publication/journal transition callbacks remain at the atomic replace;
   - every final consequential `rmdir` remains fd-relative and immediately identity-checked;
10. validate the affected storage specification and regenerate/validate its PDF derivative if permanent Markdown changes;
11. record command/node selection and pass/fail/skip counts for the exact final executable tree. A later docs/workplan/PDF-only successor may reuse evidence only after proving its executable tree is unchanged.

Use the repository environment convention, e.g. `conda run -n mace ...`, where applicable. Full external DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Implementation sequence

## Stage A — authenticate the capability at acquisition, not before it

Repair IR17-1 across generic, fully-certified common, and individually-authorized common paths. Add the pre-acquisition replacement counterfactuals before continuing.

## Stage B — make close ranking complete

Repair IR17-2A/B, perform the bounded close-family census, and run close/mount primary-vs-secondary tests.

## Stage C — replace proxy acceptance with owner acceptance

Add/convert the IR17-3 cleanup cases so planning, synchronization, executor settlement, and audit are real.

## Final assembled closure

Run IR17-4 on the exact final executable tree. Only after the source blockers and exact-candidate evidence are both closed may the implementation be passed and the storage-I/O workplan archived.

# Preserved conforming R37 implementation

Preserve unless a narrowly necessary local change is required by the blockers above:

- transition-exact `durable_unlink` callback semantics and removal of mutation-fabricating fallbacks/post-hoc disappearance inference;
- transition-exact `durable_publish_bytes/json` callback at atomic replace;
- monotonic archive blob/manifest/catalog publication phases;
- restore nonterminal/terminal journal mutation phases and destination transition truth;
- hot-reclaim exact unlink transition truth;
- final no-follow name-vs-opened-descriptor comparison before fd-relative directory `rmdir`;
- nested descriptor-relative no-follow recursion and canonical opened-descriptor mount policy;
- explicit typed common-member authority;
- one-way `ReleasedAttemptSession` invalidation and the conforming P7 action/finalizer ranking paths;
- shared `MutationLedger`, exact action byte accounting, zero-credit mutation truth, complete P7 target identity, two-attempt isolation, and all other conforming Revision-30 through Revision-37 behavior;
- reconciled storage specification direction.

# Redesign disposition

No Revision-37 redesign trigger is presently met. The failures above are implementation and acceptance nonconformance under already-delegated semantics. Do not reopen P1-P7 science/currentness, CampaignStore ownership, archive/dedup/restore product architecture, cleanup outcome semantics, Python `>=3.10`, or the accepted POSIX threat boundary.

**Design/workplan:** Revision 30 + Revision 37 remain **CLOSED / implementation-ready**.

**Implementation:** executable `9db97f72a6ba033aa4b092edb0ece39db56f5b23` / tree `a09dabfe5eb7279adb9398a98f9349c9713962a8` is **NO-PASS / reopened for bounded R37 correction under this review handoff**.
