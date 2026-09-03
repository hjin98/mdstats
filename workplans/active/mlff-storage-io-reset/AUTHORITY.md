---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 36
status: reopened
current_authority_pointer: AUTHORITY_REVISION_36.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_15.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 84a2df7779884fa3c0590588366bd139dd6241de
reviewed_executable_tree: 9e57b388a5826ea900edb674decc605605b51fe2
reviewed_branch_head: db0d603edf2e129c9f7a90e79c47ee5fcc11e25a
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted closed final-apply design and protected trust/outcome semantics;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_15.md` — complete current Revision-36 bounded implementation and acceptance contract;
- `AUTHORITY_REVISION_36.md` — current disposition/authority summary.

Revision 31-35 implementation-review and authority files are historical provenance. Revision 36 is snapshot-complete for all still-open implementation/acceptance work; no current repair requirement depends exclusively on superseded review files, Git history, prior conversation, or optional tool state.

## Preserved architecture and conforming implementation

Revision 30 remains the closed accepted design: P7 owns released-state/proof/currentness semantics; exact release/root/target identities remain plan-bound and reauthenticated on live capabilities; proof remains a monotonic-shrink upper bound; same-attempt contradiction invalidates only that attempt; proof lookup remains once-per-session/read-only; the four cleanup mutation outcomes remain frozen; Python `>=3.10` and the accepted descriptor-pinned POSIX threat boundary remain unchanged.

Preserve conforming implementation including the shared cleanup `MutationLedger`, mutation truth independent of byte credit, exact per-action reclaimed bytes, explicit executor mutation-based exceptional terminality, descriptor-relative/no-follow child recursion, trust-owned opened-descriptor mount helper, typed common-member handoff, complete P7 target identity, real two-attempt isolation, restore/dedup/maintenance immediate mutation marks, the thin public `remove_durably` wrapper, truthful traversal documentation, and the current storage-specification direction.

## Revision-36 bounded reopen

Current blocking implementation/acceptance work is fully specified in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_15.md`. In summary:

1. make unlink and archive publication mutation truth transition-exact; remove post-hoc pathname disappearance inference and signature-incompatible fallback paths that can fabricate mutation;
2. retain opened parent/child descriptor authority through each final fd-relative `rmdir`, with an immediate final no-follow identity comparison, and apply opened-descriptor mount trust throughout individually-authorized common-member descent;
3. require explicit typed common-member authority; a bare path may not default to regular-file deletion permission;
4. make P7/generic/common descriptor and `ReleasedAttemptSession` closure leak-free and terminality-safe, preserving primary mutation failures while surfacing close-only failures;
5. replace helper/manual-result acceptance with the required real planner/owner/`StorageExecutor`/audit counterfactuals and strengthen patch/failpoint liveness beyond `hasattr`;
6. run and record fresh exact-candidate affected regression/integration/static/document evidence after the final executable edit.

Serena/Semgrep remain optional evidence helpers under the bound protocol. They may improve source understanding when available but are not authority and their absence is nonblocking.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on an unbounded final affected surface or independent repository policy.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus the bounded Revision-36 implementation corrections.**

**Reviewed executable commit `84a2df7779884fa3c0590588366bd139dd6241de`, tree `9e57b388a5826ea900edb674decc605605b51fe2`: NO-PASS / reopened under Revision 36.**
