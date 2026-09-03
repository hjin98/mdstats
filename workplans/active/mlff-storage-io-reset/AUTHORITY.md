---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 34
status: reopened
current_authority_pointer: AUTHORITY_REVISION_34.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_13.md
reviewed_executable_commit: 557d32b84c5934096c95ba3ea1d33ed1714d165b
reviewed_executable_tree: 349a8cb9ac7cee653733f397f196d1426f6a7726
reviewed_branch_head: acdb3f8b2a43e5c65b4a3ca2844816cf9073b8d4
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses only:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted closed final-apply design;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_13.md` — complete current Revision-34 bounded implementation and acceptance contract;
- `AUTHORITY_REVISION_34.md` — current disposition/authority summary.

Revision 31-33 implementation-review and authority files are historical provenance. Revision 34 is snapshot-complete for the still-binding implementation/acceptance work; no current requirement depends exclusively on superseded files, Git history, prior conversation, or local tool state.

## Preserved architecture and conforming implementation

Revision 30 remains the closed accepted design: P7 owns released-state/proof/currentness semantics; exact release/root/target identities remain plan-bound and reauthenticated on a live descriptor; proof remains a monotonic-shrink upper bound; same-attempt contradiction invalidates only that attempt capability; proof lookup remains once-per-session/read-only; the four typed mutation outcomes remain frozen; Python `>=3.10` and the accepted descriptor-pinned POSIX threat boundary remain unchanged.

Preserve the conforming implementation already present, including the action-scoped `MutationLedger`, mutation truth independent of byte credit, exact per-action reclaimed bytes, descriptor-relative/no-follow destructive recursion, shared trust-owned no-follow directory acquisition, complete P7 target identity, real two-attempt refusal scoping, deterministic exact byte evidence, and the other preserved items enumerated in the current review.

## Revision-34 bounded reopen

Current blocking work is fully specified in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_13.md`. In summary:

1. enforce canonical mutation-time nested-mount ownership on the actual opened child descriptor for generic/common/P7 destructive descent;
2. transport every post-mutation observation, fsync, and descriptor-close failure through structured action-ledger truth without fabricating pre-mutation mutation or replacing a primary failure;
3. consolidate the exported boolean remover onto the canonical typed safe removal implementation and align traversal-ownership documentation;
4. make exception-time execution status depend on explicit mutation truth, including the `already_absent`-then-pre-mutation-failure counterfactual, while reconciling every mutation-producing engine;
5. close the remaining real-owner acceptance gaps with low-level failpoints rather than semantic-owner replacement or vacuous branches;
6. execute and record the complete Revision-34 exact-candidate affected regression/integration/static/document evidence on the final executable tree.

This Revision-34 entrypoint also removes the unresolved merge-conflict markers that had corrupted the Revision-33 canonical `AUTHORITY.md` handoff.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus the bounded Revision-34 implementation corrections.**

**Reviewed executable tree `349a8cb9ac7cee653733f397f196d1426f6a7726`: NO-PASS / reopened under Revision 34.**
