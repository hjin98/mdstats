---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R38-IR20
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.14.0
status: reopened
reviewed_date: 2026-09-04
reviewed_authority_revision: 38
reviewed_candidate_executable_commit: 58854cb7b7bd7e57733807086d77c18b47f9c28e
reviewed_candidate_executable_tree: b209d26d2f1a297c14803da7b0877704f1ecbcad
reviewed_branch_head: 62e00bad5bc0373a991cf973977574a3b82a38a6
reviewed_branch_tree: 8d4b3764fabe346ee7c7a03092f76b5159623122
review_verdict: NO-PASS
scope: bounded Revision-38 closure repair for stale specification topology and exact-candidate functional acceptance evidence
precedence: STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md, STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md, docs/specs/training_data/mlff_storage_management_spec.md except the two stale cleanup-topology sentences identified here, and this IR20 handoff
---

# Storage/I-O reset implementation review reopen 20 — contract and exact-candidate closure

## Disposition

**Reviewed executable: NO-PASS.**

The candidate executable reviewed is:

```text
commit  58854cb7b7bd7e57733807086d77c18b47f9c28e
 tree    b209d26d2f1a297c14803da7b0877704f1ecbcad
```

The reviewed branch head is:

```text
commit  62e00bad5bc0373a991cf973977574a3b82a38a6
 tree    8d4b3764fabe346ee7c7a03092f76b5159623122
```

The successors after the executable candidate are closure/documentation/PDF-regeneration commits; they do not alter the executable storage implementation. Behavioral review therefore binds to executable tree `b209d26...` while contract/PDF review binds to the assembled branch head.

Revision 38's Frozen architecture remains valid. This review does **not** justify Revision 39, a wrapper, compatibility adapter, second remover, classifier, retry layer, or new authority model.

## What is conforming and must be preserved

The implementation materially satisfies Revision 38 O1-O6 and the global invariants:

- `StorageExecutor.run` is the shared synchronization/revalidation envelope and no longer owns a destructive default cleanup path.
- The cleanup classifier/domain reconciliation layer was deleted rather than hardened.
- Ordinary cleanup and released-P7 cleanup converge on one canonical destructive implementation family in `mdstats/training_data/storage/removal.py`.
- The common executor contains no hidden unlink/rmdir cleanup algorithm.
- P7 retains release/proof/generation/root/target/session semantics while delegating filesystem deletion mechanics to the canonical remover.
- Open/container ownership is not converted into selective runtime recursive authority; recursive removal consumes whole-unit certification, and independently reclaimable children are planned as independent owner-authorized actions.
- Plan-bound filesystem identity and owner/root identities are rechecked at the destructive boundary; descriptor-relative no-follow descent and mount trust remain the safety envelope.
- Mutation truth and partial reclaimed-byte accounting are local to the removal transition owner; zero-byte mutations, hard links, partial mutation, durability-after-unlink failure, and already-absence remain distinguishable.
- The implementation reduces Tier-2 complexity substantially rather than adding another mediation layer.

Do not reopen or restore deleted classifier/default-engine/P7-recursion machinery to address the blockers below.

# IR20-1 — finish O7 by deleting stale cleanup-topology claims from the specification

## Failure mechanism

Revision 38 O7 requires the durable storage specification to describe stable owner authority and safety semantics without freezing classifier/default-engine or obsolete convenience-remover topology.

Most of section 5c was correctly reconciled, but two sentences still describe machinery that no longer exists:

1. The specification says the final plan-bound target check applies to an **"ordinary default single-file removal"**. Revision 38 removed the default destructive executor route; ordinary cleanup reaches the canonical cleanup engine explicitly.
2. The specification says **"The public thin remover keeps an unbound convenience mode"**. The canonical remover now requires plan-bound identity/certification at consequential boundaries; preserving an unbound destructive convenience mode is specifically contrary to O6/O7's cleanup-surface reduction.

Because the PDF was successfully regenerated from this Markdown, the generated derivative now faithfully reproduces the stale contract. A successful docs build does not make incorrect source language acceptable.

## Required end state

- Alter or delete the two stale sentences so the specification describes only the stable contract:
  - ordinary consequential cleanup, regardless of leaf/tree shape, spends the plan's target binding immediately before destructive mutation through the canonical cleanup path;
  - no supported production cleanup route or public destructive convenience surface may bypass the required plan/owner/certification authority.
- Do **not** restore a default executor engine, unbound remover, wrapper, compatibility facade, or alternate path merely to make the stale prose true.
- Keep the rest of the reconciled section 5c architecture and safety statements intact unless a directly adjacent wording edit is needed for grammatical coherence.
- Regenerate the derived PDF from the corrected Markdown using the repository's pinned docs workflow/toolchain and verify the branch successor is documentation-only.

## Mandatory acceptance

1. Source search proves the stale phrases `ordinary default single-file removal` and `unbound convenience mode` are absent from the stable storage specification.
2. Source/spec comparison confirms section 5c states one explicit cleanup path and one destructive implementation family, with required target/owner authority at mutation time.
3. The regenerated `docs/specs/training_data/mlff_storage_management_spec.pdf` corresponds to the corrected Markdown and the docs workflow succeeds.
4. No executable storage code is added merely to satisfy documentation wording.

# IR20-2 — establish exact-candidate functional regression/integration evidence

## Failure mechanism

Revision 38 final acceptance requires focused cleanup/P7/transition tests, complete affected-surface regression/integration, repository collection/import/static/conflict/diff checks, and exact final commit/tree evidence after the last material executable/test edit.

For executable candidate `58854cb7...`, GitHub exposes no workflow runs and no commit statuses. The repository contains substantial focused tests, but source presence is not execution evidence. The current authority entrypoint says implementation is complete without recording exact commands/results that establish the required final functional acceptance.

This is an acceptance blocker, not evidence of an architectural defect. Do not solve it by adding a new testing framework or runtime wrapper.

## Required end state

Run the existing test/static machinery against the exact assembled executable candidate after the last material executable/test change and record the commands, pass/fail counts, and final commit/tree. Use the existing pytest configuration and repository tools; add only missing tests that expose a concrete uncovered Revision-38 requirement.

At minimum the acceptance run must cover:

- `tests/test_mlff_storage_reset_core.py` including the Revision-38 one-path/one-remover structural claims and the real removal/P7 behavior already present there;
- all storage tests under `tests/` that exercise executor, commands, plan/revalidation, owners/inventory, cleanup, archive, restore, dedup, maintenance, audit, and P7/qualification storage seams affected by the R38 diff;
- maintained CLI/owner/campaign regressions discovered from references to changed `storage/{executor,commands,plan,owners,removal,trust,outcome}` and `qualification/store.py` surfaces;
- import/collection and repository static/conflict checks used by the project.

The implementer must re-derive the final affected set from the exact diff/caller census rather than hard-coding only the examples above. Full production-scale DFT/GPU/HPC qualification remains explicitly out of scope.

## Mandatory behavioral evidence

The final run must include real-boundary coverage for the Revision-38 claims, including:

- ordinary leaf success, already-absent, symlink/replacement contradiction, zero-byte mutation, and durability failure after unlink;
- certified whole-tree removal, unexpected descendant/kind/symlink/special/mount contradiction, monotonic missing certified node where permitted, hard-link accounting, final directory identity safety, and partial prefix accounting;
- released-P7 file/tree cleanup through the canonical remover, release/proof/root/target mismatch, monotonic shrink, live addition/kind contradiction, spent capability, same-attempt invalidation, independent-attempt isolation, and close/finalization failure ranking;
- cross-operation transition-truth regressions for archive/restore/dedup/maintenance where shared result/transition code was affected;
- structural uniqueness proving no alternate cleanup mutation path, classifier/domain synchronization state machine, P7-owned recursive deletion algorithm, or executor-owned unlink/rmdir route has returned.

Existing tests may satisfy these obligations; do not duplicate them merely to increase count. Add a test only when the final census shows a real requirement lacks executable evidence.

## Stage-local and final closure sequence

Treat IR20-1 and IR20-2 as a bounded closure stage:

1. correct only the stale specification wording;
2. regenerate/validate the PDF derivative;
3. if no executable/test file changes are needed, keep executable identity `58854cb7...` / `b209d26...`; if any executable/test file changes are necessary, establish a new exact executable commit/tree and invalidate prior runtime evidence;
4. re-derive affected callers/tests from the exact assembled candidate;
5. run focused Revision-38 cleanup/P7/transition tests;
6. run complete affected-surface regression/integration and collection/import/static/conflict checks;
7. inspect the exact candidate structurally, using ordinary source/reference analysis and Semgrep where useful; Serena may be used when available, but no review claim depends on a tool being installed;
8. record exact commands/results and exact final executable commit/tree in the closure handoff;
9. only then mark implementation PASS/CLOSED.

## Simplification guard for any newly found defect

If a test exposes a new defect, first ask whether the defect is created by surviving Tier-2 machinery. Prefer deleting, narrowing, altering, or consolidating that machinery. A new wrapper, fallback, classifier, compatibility route, state flag, retry, or second representation is nonconforming unless it protects a specific Tier-1/Frozen capability that cannot be satisfied cleanly by simplifying the existing owner.

## Closure criterion

Pass only when both are true:

- the Markdown/PDF contract no longer describes deleted default/unbound cleanup topology; and
- exact-candidate functional/static evidence establishes Revision 38 O1-O7 and affected integration behavior after the last material edit.

Until then, **Implementation remains REOPENED / NO-PASS.**
