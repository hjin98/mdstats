---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R31
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 30
reviewed_executable_commit: 3295bc47775f521db3518f6f1ba8419c78cd8b82
reviewed_executable_tree: 1fb6ac2cf368922adde06171216f55e50bf04811
reviewed_branch_head: 2524ecfcf37d9045a5544c310749a42ddde34407
review_verdict: NO-PASS
scope: bounded implementation and acceptance repair for exact per-action mutation evidence, all-path post-mutation failure truth, exact P7 measurement-before-delete behavior, mandatory final target identity, and missing real-owner/candidate-bound acceptance
precedence: Revision 30 remains the accepted closed final-apply design; this review reopens only the bounded implementation and acceptance surfaces stated here
---

# Storage/I-O reset implementation review reopen 10 — Revision 31

## Verdict and preserved implementation

**NO-PASS / bounded implementation reopen.**

Reviewed executable:

```text
commit  3295bc47775f521db3518f6f1ba8419c78cd8b82
tree    1fb6ac2cf368922adde06171216f55e50bf04811
```

Branch head `2524ecfcf37d9045a5544c310749a42ddde34407` changes only the generated storage-specification PDF relative to that executable commit. The unrelated working-tree `.gitignore` edit and `.serena/` state are not part of the reviewed executable and must be preserved.

Revision 30's core architecture is conforming and remains frozen: exact release/root binding, strict retained P7 descriptor capability, proof-as-upper-bound semantics, monotonic retry, same-attempt invalidation, once-per-session read-only proof lookup, the four typed outcomes, descriptor-relative P7 mutation, Python `>=3.10`, and the accepted POSIX threat boundary. Do not redesign or duplicate those mechanisms.

Five blocking groups remain.

## R31-1 — serialized action evidence drops exact partial bytes

### Finding and evidence

`MutationOutcome.removed_bytes` carries the exact substantiated amount and `record_removal()` uses it for the aggregate, but `MutationOutcome.to_dict()` omits it. Consequently each completed/refused action in the returned result and durable audit contains the planned `size_bytes`, outcome and mutation flag, but not the exact bytes that action actually removed. For example `partial_change_refused(..., removed_bytes=17).to_dict()` currently has no byte field.

This violates R30-F/G/H: exact partial bytes must remain explicit at action, execution, and audit levels. An aggregate cannot identify which action mutated or explain multiple partial actions.

### Required repair

- Serialize an explicit action-local reclaimed/removed-byte value for every recorded removal outcome. Equivalent additive field naming is delegated, but for a partial outcome it must be the exact numeric `MutationOutcome.removed_bytes`, for absence/refusal it must be zero, and for clean removal it must resolve to the exact amount credited under the existing metric rather than expose an ambiguous internal sentinel.
- Keep the existing aggregate `StorageExecutionResult.reclaimed_bytes`; require it to equal the sum of action-local credited amounts.
- Do not overload planned `size_bytes` as the partial result and do not infer actual bytes from prose.

### Acceptance

Through the real cleanup executor and durable audit, assert exact per-action and aggregate bytes for: one clean removal, already absent, no-change refusal, one partial action, and at least two actions where only one partially mutates. A counterfactual must fail if the action-local byte field is omitted or replaced by planned size.

## R31-2 — post-mutation failure truth is not closed across the common/default paths

### Finding and evidence

The new `_record_or_reraise()` boundary covers the CLI cleanup engine, but Serena reference analysis confirms that `StorageExecutor._execute_actions()` still calls `remove_durably_outcome()` directly. A `PartialMutationError` there reaches the executor's outer `BaseException` handler without `record_removal()`, so current-action mutation and bytes are lost.

The helper coverage is also incomplete:

- `remove_durably_outcome()` treats an `OSError` as partial only when the top-level path is fully absent. A recursive removal can delete a strict subset and fail while the container still exists; the function then raises a plain `OSError`. A review counterfactual removed one child, retained its sibling/container, and observed exactly this raw exception.
- `remove_certified_subtree()` calls `remove_durably()` directly on its fully certified branch, so unlink/rmtree followed by durability failure bypasses structured outcome transport. In its individually authorized branch, a later pre-unlink error after an earlier successful member likewise raises without carrying the earlier mutation.
- More generally, once an action has made its first destructive transition, any later exception must carry the accumulated action-local mutation/byte truth; checking only whether the top-level pathname disappeared is not sufficient for recursive/multi-member work.

This is implementation nonconformance with R30-G, not a redesign trigger.

### Required repair

- Establish one common action-boundary recording path for every `StorageExecutor` removal execution, including `engine=None`; no producer of `PartialMutationError` may bypass it.
- In generic recursive removal and common certified-subtree removal, track destructive transitions and exact action-local bytes as they occur. If a later unlink/rmdir/fsync/enumeration or other operation raises, convert/augment the failure to `partial_change_refused` when any earlier mutation occurred, record it at the current action boundary, then propagate the underlying failure under the existing error contract.
- A failure before the first destructive transition remains a no-mutation failure and credits zero.
- Do not infer a recursive action's mutation solely from top-level path existence. Do not credit bytes before the corresponding unlink/rmdir succeeds.
- Consolidate duplicated catch/record/rethrow mechanics when practical so the CLI and default executor cannot drift again, without introducing a new control plane or changing settled action semantics.

### Acceptance

Use the real `StorageExecutor`, settlement and durable audit for all of the following bounded counterfactuals:

1. default `engine=None`: unlink succeeds, durability fails -> current action is recorded partial with exact bytes before propagation;
2. generic directory: one child is removed, a later child/removal fails while the container survives -> partial action with exact bytes, not an unannotated exception;
3. fully certified common subtree: final removal succeeds, later durability fails -> partial action with exact bytes;
4. individually authorized common subtree: an earlier member succeeds and a later member fails before mutation -> earlier bytes/mutation survive in the partial action;
5. corresponding pre-first-mutation failures -> no fabricated mutation or bytes.

Instrumentation may replace low-level filesystem transitions only; authorization, `StorageExecutor`, action recording, settlement and audit remain real.

## R31-3 — P7 measurement failure can delete bytes and report no change

### Finding and evidence

In `_remove_certified_directory()`, failure of `DirEntry.stat(follow_symlinks=False)` sets `key=None, measured=0` and still calls `_unlink_certified_file()`. If a later contradiction stops the action, the successful unlink is absent from `freed`; when no earlier counted entry exists, the result can even be `refused_no_change` with `mutated=false` and zero bytes.

A review counterfactual used an 11-byte proof-recorded file whose stat failed, followed by an unrecorded sibling. The file was removed, but the returned outcome was `refused_no_change`, `removed_bytes=0`, `mutated=false`.

This violates R30-F/G/H and the explicit measure-before-unlink rule.

### Required repair

- A regular file whose required size/inode observation cannot be established must be retained/refused before unlink; exact accounting may not be replaced by zero.
- Once a prior entry has been removed, a later measurement/observation failure produces an exact partial outcome for that prior prefix.
- Preserve action-wide `(device,inode)` deduplication across recursion and credit only after successful unlink.

### Acceptance

Cover measurement failure on the first file and after one prior successful removal. In both cases the unmeasured file survives. The first case is no-change/zero; the second is partial with only the earlier exact bytes. Exercise the real P7 executor and durable audit for the second case.

## R31-4 — final P7 target identity is optional and incomplete at the mutation API

### Finding and evidence

`remove_released_attempt_member(..., planned_identity=None)` skips the final target identity check, and when a mapping is supplied it compares only keys that happen to be present. The function is exported and is the owner mutation boundary. A review counterfactual constructed a live session and called the function without `planned_identity`; it removed the target.

The production cleanup caller currently supplies a complete identity, but R30-B freezes the check as an invariant of every released-member mutation, not an optional caller convention. A future/internal caller or malformed plan can bypass the exact boundary while still using a valid P7 capability.

### Required repair

- Make the plan-bound target identity mandatory for every released-member mutation entry. Before any target observation or destructive syscall, reject a missing identity or one missing any current `TARGET_IDENTITY_DIMENSIONS` key.
- Compare all current dimensions (`kind`, `device`, `inode`, `size_bytes`, `mtime_ns`) no-follow relative to the retained descriptor. Preserve the structural guard that prevents later plan revalidation dimensions from outgrowing this set.
- Closed/spent capability rejection must still occur before any syscall; tests may supply the identity explicitly rather than rely on the optional default.
- Treat production data-shape absence as fail-closed. Whether programmer misuse raises before filesystem access or returns a typed no-change refusal is delegated, provided it cannot mutate or widen authority.

### Acceptance

For both file and directory targets, missing and each one-key-incomplete identity must reach no stat/open/unlink/rmdir and leave the target intact. Complete identity retains the existing replacement/staleness behavior. Include the real cleanup caller and a direct owner-boundary misuse counterfactual.

## R31-5 — required real-owner and exact-candidate acceptance remains incomplete

### Finding and evidence

The added tests are useful but do not close several explicit R30 acceptance boundaries:

- resealed valid-but-different release authority and final state/proof/topology damage still call `open_released_attempt_session()` directly rather than driving the old plan through the real cleanup executor;
- recursive partial-byte evidence still calls `_remove_certified_directory()` directly and does not prove real action settlement or durable audit;
- no real-executor case proves one successful action followed by a no-change refusal settles `partial` with exact collections and bytes;
- the unrelated-attempt invalidation case calls `_apply_released_member()` directly rather than the real cleanup executor;
- no combined real-executor case proves partial/refusal invalidates later same-attempt actions while an independent attempt remains eligible;
- the post-mutation test checks only aggregate bytes greater than zero; it does not assert the exact per-action value required by R30;
- the generic/default and common-subtree failure cases in R31-2 are untested at the required owner boundary;
- no candidate-bound record identifying the actual complete R30 command set and results for executable `3295bc4...` was supplied.

Passing direct helper tests cannot close these owner claims because those tests can remain green while executor routing, action recording, settlement, or durable audit is broken.

### Required repair and acceptance

Preserve focused helper tests, add the missing bounded real-owner counterfactuals above, and after the last executable edit record actual commands/results for the exact final executable commit/tree:

1. focused R22-R31 P7 namespace/state/proof/root/release-authority/target-identity/capability/mutation/outcome/concurrency and failure counterfactuals;
2. complete `tests/test_mlff_storage_reset_core.py`;
3. complete `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the common cleanup/result/durability path;
5. clean maintained-suite `pytest --collect-only -q`;
6. final affected-surface re-derivation followed by a fresh complete affected regression/integration pass on that exact executable tree;
7. repository static checks plus affected Markdown/PDF validation.

Record exact test node/file selection, pass/fail/skip summaries, executable commit and executable tree. A later plan/review-only successor does not invalidate functional evidence; a generated-document-only successor is reusable only after an exact compare proves no executable or test change. Any executable/test repair made for R31 invalidates the current R30 run and requires fresh final evidence.

Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy. External-DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking; do not present them as run.

## Independent review evidence

The following was freshly executed from branch head `2524ecfcf37d9045a5544c310749a42ddde34407` after proving no executable source or test differs from reviewed executable `3295bc47775f521db3518f6f1ba8419c78cd8b82`:

- `conda run -n mace pytest -q -n 16 --dist=load tests/test_mlff_storage_reset_core.py tests/test_mlff_storage_reset_integration.py` -> **327 passed**;
- `conda run -n mace pytest -q -n 16 --dist=load tests/test_mlff_target_size_p4f_storage_docs_structure.py tests/test_mlff_target_size_p6_destructive_closure.py tests/test_mlff_p7_r11_repair_acceptance.py tests/test_mlff_p7_r12_repair_acceptance.py tests/test_mlff_p7_r13_authority_acceptance.py tests/test_mlff_campaign_cli.py` -> **170 passed, 1 skipped**; the skip is the pre-existing explicitly unavailable target-machine mliappy/MACE callback qualification, not storage functional evidence;
- `conda run -n mace pytest --collect-only -q` -> **3563 tests collected**;
- changed Python modules compile successfully and `git diff --check` reports no error;
- the generated storage specification PDF is readable as a 13-page letter PDF and `pdftotext` extracts its R30 content.

The focused current tests also passed (8 selected R30 integration cases), but they do not invalidate the counterexamples below because their assertions do not cover those states. Independent review directly reproduced all of the following on the reviewed executable:

1. `partial_change_refused(..., removed_bytes=17).to_dict()` omits the byte value;
2. generic recursive removal deletes one child, retains the container/sibling, and raises a plain `OSError`;
3. P7 recursion deletes an 11-byte proof-recorded file after its stat fails, then returns `refused_no_change`, zero bytes and `mutated=false` when a later unrecorded sibling stops the action;
4. the exported released-member remover deletes a proof-recorded file when `planned_identity` is omitted.

These executable counterexamples take precedence over otherwise green regression evidence for the specific R31 claims. No external-DFT, GPU, long production, or environment-specific HPC/storage qualification was run or claimed.

## Affected surface and route

Initially affected executable surface remains bounded to:

- `mdstats/training_data/qualification/store.py`;
- `mdstats/training_data/storage/outcome.py`;
- `mdstats/training_data/storage/executor.py`;
- `mdstats/training_data/storage/commands.py`;
- `mdstats/training_data/storage/durability.py` only if the owning failure tracker belongs there;
- storage core/integration tests and affected current-owner regressions;
- current storage specification wording and generated PDF if implementation truth requires adjustment.

Treat R31-1 through R31-4 as one coherent truthful-final-apply behavior correction:

```text
mandatory complete target identity
 + exact measure-before-delete P7 recursion
 + all-path structured partial failure transport
 + one shared action-boundary recorder
 + explicit per-action byte evidence
 -> real-owner R30/R31 counterfactuals
 -> stage-local storage regression
 -> final affected-surface re-derivation
 -> exact-candidate affected regression/integration + static/docs validation
```

Reopen Design only if supported Python/POSIX interfaces cannot realize the frozen descriptor/identity boundary, or if an external public result consumer cannot accept an additive exact action-byte field without a required compatibility migration. Helper layout, exception type, and internal tracker representation remain delegated.

## Handoff closure

The current supplied set is `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` + `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` + `docs/specs/training_data/mlff_storage_management_spec.md` + this review + `AUTHORITY_REVISION_31.md`/`AUTHORITY.md` navigation. It recovers every still-binding design decision, review correction, acceptance boundary, preservation rule, and redesign trigger without Git history, prior chat, or superseded review files.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**; Revision 31 is bounded implementation and acceptance rework only.

**Executable disposition:** **NO-PASS / reopened under Revision 31.**
