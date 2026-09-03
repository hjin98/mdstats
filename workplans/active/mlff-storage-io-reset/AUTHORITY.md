---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 30
status: closed-implementation-ready
current_authority_pointer: AUTHORITY_REVISION_30.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 6423a3f33a36c09ca1b89f5740f42c402b1993d2
reviewed_executable_tree: a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses only the following current task authorities:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete remaining final-apply repair contract;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `AUTHORITY_REVISION_30.md` — concise disposition/authority summary.

Revision-26/28/29 repair, authority, and implementation-review files are historical provenance. No still-binding Revision-30 implementation requirement depends exclusively on reading those superseded files, Git history, or prior conversation.

## Revision-30 closure

Revision 30 preserves the accepted owner-driven storage architecture and consolidates all final-apply requirements, including:

- exact released-state/proof authority bound into the immutable plan and reauthenticated on the live P7 descriptor;
- retained descriptor continuity through state/proof/topology certification and fd-relative mutation;
- no-follow final comparison of the plan-bound target identity immediately before each P7 member mutation;
- permanently unspendable closed session objects even if fd numbers are reused;
- proof-as-upper-bound monotonic shrink and safe interrupted retry;
- same-attempt capability invalidation after mutation-time contradiction;
- once-per-session non-widenable typed proof lookup;
- structured removed / already-absent / no-change-refused / partial-change-refused outcomes;
- action-boundary preservation of mutation truth when a later fsync/durability/destructive step raises;
- exact nested partial-byte propagation under the existing storage accounting metric;
- real-executor / real-synchronization / real-P7-owner acceptance and exact-candidate regression/integration evidence.

The accepted Python `>=3.10` floor, descriptor-pinned POSIX threat boundary, bounded reporting, R26 historical test/tool retirement, CampaignStore, P5 proof, archive/dedup/restore/control-plane architecture, and P1-P7 scientific/currentness semantics remain frozen.

External-DFT, long GPU, and environment-specific HPC/shared-storage production qualification remain deferred and nonblocking. Whole-repository behavioral pytest is required only if final affected-surface analysis cannot remain bounded or independent repository policy requires it.

## Disposition

**Design/workplan: CLOSED / implementation-ready under Revision 30.**

**Reviewed executable `6423a3f33a36c09ca1b89f5740f42c402b1993d2`: NO-PASS / bounded implementation repair remains required.**
