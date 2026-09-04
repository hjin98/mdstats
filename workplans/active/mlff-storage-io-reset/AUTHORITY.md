---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.12.0
revision: 38
status: planned
current_authority_pointer: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
baseline_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
baseline_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
review_verdict: DESIGN-RESET / IMPLEMENTATION-PENDING
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses this supplied current authority set:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader owner-driven storage architecture and product non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md` — current snapshot-complete storage architecture and implementation contract;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product behavior/contract, to be reconciled where implementation-topology wording conflicts with Revision 38;
- current source/tests — repository evidence of the implementation state to simplify.

Revision 30-37 and IR review/reopen files are historical provenance. They do not define the current implementation topology and are not required normative input for implementation of Revision 38.

## Architecture invariant

The storage subsystem is now governed by the simplicity invariant:

> **one semantic authority, one explicit operation path, one persistent-transition owner.**

For cleanup specifically:

- `StorageExecutor` is an authorization/transaction/audit shell, not a destructive cleanup engine;
- there is exactly one production cleanup engine;
- there is exactly one consequential cleanup filesystem mutation kernel;
- cleanup mutation is either an exact leaf or an owner-certified closed tree;
- P7 owns release/proof/root/target authority and delegates deletion mechanics to the shared kernel;
- persistent mutation truth is recorded at the actual state-changing transition and is never inferred later from pathname disappearance or byte totals;
- superseded wrappers, fallbacks, duplicate recursion, classifier/domain synchronization machinery, and layered finalization logic are deleted rather than preserved behind new facades.

Archive, restore, deduplication, and CampaignStore maintenance remain specialized only where their algorithms and persistence/recovery semantics are genuinely distinct.

## Preservation

Revision 38 preserves the hard behavioral requirements established by the storage reset: owner-driven scientific/currentness authority, fail-closed ambiguity, immutable plan binding and fresh revalidation, storage/owner synchronization, protected external input, no-follow descriptor-relative destructive mutation, mount/identity protection, P7 released-proof/currentness semantics, truthful four-way cleanup outcomes, exact partial/zero-byte/hard-link mutation accounting, durability and post-transition truth, truthful audit degradation, and accepted archive/restore/dedup/maintenance behavior.

Python `>=3.10`, the accepted descriptor-pinned POSIX threat boundary, and the prohibition on a new persistent descriptor/inode/release/retry control plane remain unchanged.

## Revision discipline

This Revision 38 consolidation is the bounded Design reconsideration triggered by repeated same-family failures and accumulated machinery.

After implementation, ordinary defects that remain governed by the frozen invariant are fixed in the canonical owner/kernel under the same architecture. Concrete new failure sites, tests, or implementation mistakes do **not** create new numbered storage authority revisions. A future normative revision is warranted only by evidence that a frozen Revision-38 architectural decision is itself insufficient or incompatible with a required supported contract.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 38 simplicity consolidation.**

**Implementation:** **PENDING.** The current executable baseline remains evidence of the pre-consolidation implementation and is not accepted as the target architecture.
