---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.12.0
revision: 38
status: planned
current_authority_pointer: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
reviewed_current_executable_commit: 38b37f6761d30c66ec29e27abf8f2ee3a311f804
reviewed_current_executable_tree: c5918d5db992c42b144b7770d100c160f9d417f7
review_verdict: DESIGN-RESET / IMPLEMENTATION-PENDING
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses this supplied current authority set:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — original owner-driven storage architecture, engineering envelope and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md` — current snapshot-complete architecture-reduction and implementation contract;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current behavioral storage contract; implementation-topology wording that conflicts with Revision 38 is explicitly scheduled for reconciliation by Revision 38;
- current source/tests — evidence of the pre-consolidation implementation to reduce.

Revision 30-37 and implementation-review/reopen artifacts are historical provenance. They do not define the current implementation topology and are not required normative input for Revision 38.

The reviewed current executable is commit `38b37f6761d30c66ec29e27abf8f2ee3a311f804`, tree `c5918d5db992c42b144b7770d100c160f9d417f7`. Later branch changes through activation of Revision 38 are documentation/workplan/PDF-only and do not change the executable implementation reviewed by the reduction plan.

## Architecture invariant

The storage subsystem is governed by:

> **one semantic authority, one explicit operation path, one persistent-transition owner.**

For cleanup this now means concretely:

- `StorageExecutor` owns common apply authorization, storage/owner synchronization, fresh resnapshot, plan revalidation, admission, settlement and audit; it has no destructive default cleanup implementation;
- existing `StoragePlan`/`revalidate_plan` becomes the canonical action-to-owner/path/current-eligibility gate instead of a second cleanup classifier;
- there is exactly one production cleanup engine and no cleanup semantic-class/domain state machine;
- cleanup recursively mutates only owner-certified `CLOSED` trees; `CONTAINER` is not a selective recursive cleanup mode;
- there is exactly one consequential cleanup filesystem mutation kernel shared by ordinary and P7 cleanup;
- P7 retains release/proof/root/target/session authority but delegates unlink/rmdir mechanics to that kernel;
- persistent mutation truth is recorded at the actual transition and never inferred later from pathname disappearance or byte totals;
- duplicate recursion, default-engine routing, classifier/domain synchronization, mixed `members/refusals` mutation, obsolete destructive compatibility wrappers and layered cleanup finalization are deleted rather than preserved behind new facades.

Archive, restore, deduplication and CampaignStore maintenance remain specialized only where their algorithms and persistence/recovery semantics are genuinely distinct. The existing exact atomic-publication callback may remain because it is one shared mechanism that closes several genuine replace-before-fsync/readback failure windows; Revision 38 does not require replacing necessary shared machinery merely to reduce line count.

## Preservation

Revision 38 preserves the hard behavioral requirements established by the storage reset: owner-driven scientific/currentness authority, fail-closed ambiguity, immutable plan binding and fresh revalidation, storage/owner synchronization, protected external input, no-follow descriptor-relative destructive mutation, mount/identity protection, P7 released-proof/currentness semantics, truthful four-way cleanup outcomes, exact partial/zero-byte/hard-link mutation accounting, durability and post-transition truth, truthful audit degradation, and accepted archive/restore/dedup/maintenance behavior.

Python `>=3.10`, the accepted descriptor-pinned POSIX threat boundary, and the prohibition on a new persistent descriptor/inode/release/retry control plane remain unchanged.

## Revision discipline

Revision 38 is the bounded Design reconsideration required by repeated same-family failure and accumulated implementation machinery.

After implementation, an ordinary defect still governed by these frozen invariants is fixed in the surviving canonical owner/kernel under the same authority. A new site, failing test, race example or implementation mistake does **not** create another numbered storage revision. Reopen Design only when evidence shows that a frozen Revision-38 architectural decision itself is insufficient or incompatible with a required supported contract.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under the concrete Revision-38 simplicity-consolidation plan.**

**Implementation:** **PENDING.** The reviewed executable commit/tree above is the pre-consolidation implementation to reduce and is not accepted as the target architecture.
