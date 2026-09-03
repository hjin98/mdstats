---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 31
status: reopened
current_authority_pointer: AUTHORITY_REVISION_31.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_10.md
reviewed_executable_commit: 3295bc47775f521db3518f6f1ba8419c78cd8b82
reviewed_executable_tree: 1fb6ac2cf368922adde06171216f55e50bf04811
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses only the following current task authorities:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete remaining final-apply repair contract;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_10.md` — bounded Revision-31 implementation and acceptance corrections;
- `AUTHORITY_REVISION_31.md` — concise disposition/authority summary.

Revision-26/28/29/30 authority and earlier implementation-review files are historical provenance. Revision 30 remains supplied because it owns the accepted final-apply design; Revision 31 is a bounded implementation-review delta over that complete contract. No current requirement depends exclusively on superseded files, Git history, or prior conversation.

## Preserved Revision-30 closure

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

## Revision-31 reopen

Independent review of executable `3295bc47775f521db3518f6f1ba8419c78cd8b82` found bounded blocking nonconformance in the still-open truthful-final-apply surface:

- per-action serialized evidence drops the exact `removed_bytes` carried by a partial outcome;
- generic/default and common certified-subtree failure paths can mutate and then bypass structured action recording;
- P7 recursion may delete an entry whose size observation failed and then report no mutation/zero bytes;
- the exported P7 member mutation entry accepts absent or incomplete planned target identity and therefore permits the required final identity check to be bypassed;
- several mandatory R30 real-executor counterfactuals and exact-candidate acceptance records remain absent.

The accepted R30 owner architecture, exact release/root binding, live descriptor capability, proof-as-upper-bound semantics, same-attempt invalidation, once-per-session proof lookup, four-outcome model, and Python/POSIX threat boundary remain closed and must be preserved.

## Disposition

**Design/workplan: CLOSED / implementation-ready under Revision 30 plus the bounded Revision-31 corrections.**

**Reviewed executable `3295bc47775f521db3518f6f1ba8419c78cd8b82`: NO-PASS / reopened for bounded implementation and acceptance repair under Revision 31.**
