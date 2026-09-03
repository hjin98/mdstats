---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 35
status: reopened
current_authority_pointer: AUTHORITY_REVISION_35.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_14.md
reviewed_executable_commit: 557d32b84c5934096c95ba3ea1d33ed1714d165b
reviewed_executable_tree: 349a8cb9ac7cee653733f397f196d1426f6a7726
reviewed_plan_commit: 55dcb26f1dd770b98e13b92ba088f93d2da3c371
review_verdict: NO-PASS-PLAN-AMENDED
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses only:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted closed final-apply design;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_14.md` — complete current Revision-35 bounded implementation and acceptance contract;
- `AUTHORITY_REVISION_35.md` — current disposition/authority summary.

Revision 31-34 implementation-review and authority files are historical provenance. Revision 35 is snapshot-complete for all still-binding implementation/acceptance work; no current requirement depends exclusively on superseded files, Git history, prior conversation, or local tool state.

## Preserved architecture and conforming implementation

Revision 30 remains the closed accepted design: P7 owns released-state/proof/currentness semantics; exact release/root/target identities remain plan-bound and reauthenticated on live capabilities; proof remains a monotonic-shrink upper bound; same-attempt contradiction invalidates only that attempt; proof lookup remains once-per-session/read-only; the four cleanup mutation outcomes remain frozen; Python `>=3.10` and the accepted descriptor-pinned POSIX threat boundary remain unchanged.

Preserve conforming current implementation including the shared cleanup `MutationLedger`, mutation truth independent of byte credit, exact per-action reclaimed bytes, descriptor-relative/no-follow child recursion, trust-owned no-follow acquisition, complete P7 target identity, real two-attempt fixture, deterministic exact-byte evidence, resealed/damaged authority acceptance, repaired interruption failpoints, and the current storage-spec contract.

## Revision-35 bounded reopen

Current blocking implementation/acceptance work is fully specified in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_14.md`. In summary:

1. bind canonical nested-mount ownership to the actual opened destructive descriptor for both top-level roots and descendants across generic/common/P7 cleanup;
2. replace post-hoc single-file deletion inference with transition-aware unlink truth and preserve typed/current authority for individually-authorized common members;
3. transport observation, durability, recursive-descriptor, `ReleasedAttemptSession`, and cleanup-session-finalizer failures without losing primary mutation truth/cause or fabricating pre-mutation change;
4. preserve and separately prove P7 typed-partial continuation semantics versus exceptional-partial termination semantics through the real owner;
5. make `StorageExecutionResult.mutated` the explicit exception-time mutation fact and reconcile persistent mutation boundaries in cleanup, archive creation/hot reclamation/restore, deduplication and campaign-state maintenance;
6. converge the public boolean remover and traversal documentation onto the canonical consequential owners;
7. close the complete real-owner acceptance matrix and execute fresh exact-candidate affected regression/integration/static/document evidence, including newly implicated archive/restore/dedup/maintenance consumers.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus the bounded Revision-35 implementation corrections.**

**Reviewed executable tree `349a8cb9ac7cee653733f397f196d1426f6a7726`: NO-PASS / reopened under Revision 35.**
