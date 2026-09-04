---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.14.0
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

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — original owner-driven storage product problem, engineering envelope, and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md` — current Protocol-5.14 snapshot-complete architecture-reduction and implementation contract;
- `docs/specs/training_data/mlff_storage_management_spec.md` — stable behavioral storage contract, except that section 5c's classifier/default-engine implementation topology is superseded immediately by Revision 38 and must be reconciled before final implementation closure;
- current source/tests — evidence of the pre-consolidation Tier-2 implementation to reduce, not authority for preserving it.

Revision 30-37 and implementation-review/reopen artifacts are historical provenance. They do not define the current target realization and are not required normative input for Revision 38.

The reviewed current executable is commit `38b37f6761d30c66ec29e27abf8f2ee3a311f804`, tree `c5918d5db992c42b144b7770d100c160f9d417f7`. Later changes through this plan review are workplan/documentation-only and do not change that executable baseline.

## Protocol adoption

Revision 38 explicitly adopts backward-compatible Protocol **5.14.0**. The current handoff has been reconciled to the 5.14 three-tier authority model:

- Tier 1A: intrinsic product/problem invariants;
- Tier 1B: only deliberately Frozen high-level storage architecture;
- Tier 2: replaceable implementation machinery, including functions, modules, helpers, callbacks, session representations, prior patches, tests, and implementation-created invariants unless separately justified and promoted.

Affected-surface expansion does not create product requirements. Existing dependencies/tests do not promote Tier-2 machinery into Frozen authority.

## Frozen storage architecture

The storage subsystem is governed by these high-level decisions for this cycle:

- real semantic owners remain the sole authority for scientific/currentness/reclaimability facts;
- consequential work uses an immutable owner-bound plan and a synchronized fresh authority check before mutation;
- there is one common non-destructive consequential execution envelope and one canonical production cleanup semantic path, with no hidden alternate destructive cleanup route;
- ordinary and P7 cleanup share one canonical consequential filesystem destructive implementation family and one transition-truth model;
- recursive cleanup requires whole-unit owner authority; an open/container root is not recursive destructive authority, and selectively reclaimable children are authorized as independent destructive units before mutation;
- P7 retains its release/proof/generation/root/target semantics but does not own a second generic filesystem deletion algorithm;
- mutation truth is established at the state-changing transition and is never inferred later from pathname disappearance, reclaimed-byte totals, or compatibility fallback;
- archive/restore/dedup/maintenance remain specialized only where their transformation/recovery semantics materially require it;
- no new persistent storage scientific/currentness authority or descriptor/inode/release/retry registry is introduced.

Exact module/function names, callable counts/signatures, location of the current-owner gate, session-cache representation, callback identity, helper layout, and test organization are delegated Tier-2 realization. Revision 38 does not freeze them merely because the current implementation or acceptance harness names them.

## Active simplicity rule

A defect created only by surviving Tier-2 machinery is a Tier-2 problem. Before adding a durable wrapper, fallback, classifier, compatibility path, state bit, retry, session layer, or second representation, implementation must first challenge whether deleting, narrowing, altering, consolidating, refactoring, or replacing the causal machinery makes the problem disappear.

Net-new machinery is justified only when it protects an identified Tier-1/Frozen requirement that the simplified existing realization cannot satisfy cleanly, or when one canonical mechanism replaces broader existing complexity and lowers total system complexity.

## Preservation

Revision 38 preserves the hard product requirements established by the storage reset: owner-driven scientific/currentness authority, fail-closed ambiguity, protected external input, plan/apply freshness, storage/owner synchronization, safe no-follow/mount-aware destructive behavior within the supported POSIX boundary, P7 released-proof semantics, truthful absent/refused/removed/partial outcomes, exact zero-byte/hard-link/partial accounting, durability/recovery, truthful audit degradation, archive/restore/dedup/maintenance behavior, resource admission, Python >=3.10, and bounded reporting/audit behavior.

## Revision discipline

Revision 38 is the bounded Design reconsideration triggered by repeated same-family failure and accumulated implementation machinery.

After implementation, an ordinary defect still governed by the Frozen architecture is repaired by reducing/altering the surviving Tier-2 owner under the same authority. A new failure site, failing test, current helper dependency, or additional affected caller does not create another numbered storage revision.

Reopen Design only when evidence shows that a Frozen high-level decision itself cannot satisfy a required product contract or the accepted engineering envelope.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Protocol 5.14.0 Revision 38.**

**Implementation:** **PENDING.** The reviewed executable commit/tree above is the pre-consolidation Tier-2 realization to reduce and is not accepted as the target architecture.
