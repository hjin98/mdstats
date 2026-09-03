---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 34
status: reopened
supersedes_revision: 33
reviewed_executable_commit: 557d32b84c5934096c95ba3ea1d33ed1714d165b
reviewed_executable_tree: 349a8cb9ac7cee653733f397f196d1426f6a7726
reviewed_branch_head: acdb3f8b2a43e5c65b4a3ca2844816cf9073b8d4
reviewed_branch_tree: 3f09a96b292ca682539f2751b2e774dc715e3a44
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_13.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 34

Revision 34 independently reviews the Revision-33 implementation now assembled on `plan/mlff-storage-io-reset-realign-p1-p7`.

The executable candidate is:

```text
commit  557d32b84c5934096c95ba3ea1d33ed1714d165b
tree    349a8cb9ac7cee653733f397f196d1426f6a7726
```

The current branch head `acdb3f8b2a43e5c65b4a3ca2844816cf9073b8d4` is a generated-PDF-only successor and does not change executable or test source.

## Current normative handoff

Implementation reads only:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md`;
3. `docs/specs/training_data/mlff_storage_management_spec.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_13.md` — complete Revision-34 bounded implementation/acceptance contract;
5. `AUTHORITY.md` as canonical navigation/status.

Revision 31-33 authority/review files are historical provenance. No current obligation requires reconstructing them.

## Preserved state

Revision 30 remains the closed accepted design. Preserve the conforming implementation already present: action-scoped `MutationLedger` ownership of mutation/bytes/dedup, zero-credit mutation truth, descriptor-relative/no-follow recursive mutation, shared trust-owned no-follow directory acquisition, complete P7 target identity, real two-attempt refusal scoping, deterministic exact byte evidence, and the other conforming items enumerated in the Revision-34 review.

## Revision-34 blocking implementation/acceptance work

The reviewed executable is **NO-PASS** for six bounded groups:

1. generic/common destructive recursion does not consume the canonical mutation-time nested-mount boundary, and P7 checks the mount locator before rather than against the actual opened child descriptor;
2. P7 and generic/common destructive recursion still have raw `DirEntry`/descriptor-close failure paths that can lose or replace structured post-mutation truth;
3. exported `remove_durably` still owns an independent `shutil.rmtree` recursion instead of adapting to the canonical typed safe removal path, while `walk_contained` still claims false destructive-traversal ownership;
4. exception-time executor settlement still treats any non-empty `completed` list as evidence of partial mutation, so an `already_absent` no-op followed by a pre-mutation failure can be falsely audited as partial;
5. several Revision-33 acceptance cases remain vacuous, helper-level, or absent at the required real-owner boundary, including guaranteed default-engine post-unlink failure, common-subtree failure cases, mutation-time mount cases, and all-path close/observation failures;
6. the prior canonical `AUTHORITY.md` contained unresolved merge-conflict markers and no complete exact-candidate behavioral acceptance record exists for executable tree `349a8cb...`; connected CI on the merge candidate supplies only documentation validation.

Precise end states, test-double boundaries, affected-surface rules, implementation sequence, and final evidence requirements are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_13.md`.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy.

## Disposition

**Accepted design:** **CLOSED / implementation-ready under Revision 30.**

**Current bounded implementation handoff:** **Revision 34 / reopened.**

**Reviewed executable tree `349a8cb9ac7cee653733f397f196d1426f6a7726`: NO-PASS.**
