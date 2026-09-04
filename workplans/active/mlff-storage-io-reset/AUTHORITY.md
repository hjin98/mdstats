---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.14.0
revision: 38
status: reopened
current_authority_pointer: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_20.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md
reviewed_candidate_executable_commit: 58854cb7b7bd7e57733807086d77c18b47f9c28e
reviewed_candidate_executable_tree: b209d26d2f1a297c14803da7b0877704f1ecbcad
reviewed_branch_head: 62e00bad5bc0373a991cf973977574a3b82a38a6
reviewed_branch_tree: 8d4b3764fabe346ee7c7a03092f76b5159623122
review_verdict: NO-PASS / IMPLEMENTATION-REOPENED
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Use this supplied authority set:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — original owner-driven storage problem, engineering envelope, and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md` — accepted Protocol-5.14 Tier-1/Frozen architecture and implementation contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_20.md` — current bounded implementation-repair and closure authority;
- `docs/specs/training_data/mlff_storage_management_spec.md` — stable storage contract except for the two explicitly identified stale cleanup-topology sentences in IR20-1, which must be corrected to match Revision 38 before closure;
- current source/tests — implementation and acceptance evidence, not authority for preserving replaceable Tier-2 machinery.

Revision 30-37 and IR1-IR19 are historical provenance. They do not reopen superseded Tier-2 mechanisms or define the current repair target.

## Global invariants and Frozen architecture

The original problem remains invariant: storage may reclaim campaign-managed bytes only when the real semantic owner positively establishes that the artifact is safely reclaimable/currently expendable, while externally supplied inputs and ambiguous/current/in-flight/unreadable/unresolved state fail closed. Consequential work uses an immutable owner-bound plan followed by synchronized fresh reauthentication/revalidation before mutation, and mutation must never silently retarget to a same-name replacement, symlink, or different mount.

Revision 38 freezes the high-level realization for this implementation cycle:

- real semantic owners remain the sole scientific/currentness/reclaimability authority;
- the common consequential executor is a non-destructive synchronization/revalidation envelope, not an alternate cleanup engine;
- there is one canonical cleanup semantic path and no default/hidden destructive route;
- ordinary and released-P7 cleanup share one canonical consequential filesystem destructive implementation family and one transition-truth model;
- recursive cleanup requires whole-unit owner authority; open/container ownership is not selective recursive destructive authority;
- P7 retains release/proof/generation/root/target authority but delegates filesystem deletion mechanics to the canonical destructive owner;
- mutation truth is captured at the state-changing transition and is not reconstructed from later pathname disappearance, reclaimed-byte totals, or compatibility fallback;
- archive/restore/dedup/maintenance remain specialized only where materially required by distinct semantics;
- no new persistent storage scientific/currentness authority or descriptor/inode/release/retry registry is introduced.

Exact functions, module layout, helper counts, session representation, callbacks, tests, and other Tier-2 mechanics remain replaceable. A repair must first delete, narrow, alter, consolidate, or replace causal Tier-2 machinery before adding a wrapper, fallback, classifier, compatibility route, state bit, retry layer, or second representation.

## 2026-09-04 implementation review disposition

**Design/workplan:** **CLOSED / Revision 38 Frozen architecture remains accepted.** No Revision 39 or architectural redesign is justified by this review.

**Implementation:** **NO-PASS / REOPENED** against executable candidate `58854cb7b7bd7e57733807086d77c18b47f9c28e`, tree `b209d26d2f1a297c14803da7b0877704f1ecbcad`; reviewed branch head `62e00bad5bc0373a991cf973977574a3b82a38a6`, tree `8d4b3764fabe346ee7c7a03092f76b5159623122`, differs from the executable candidate only by closure documentation/PDF regeneration successors.

The executable consolidation is materially aligned with Revision 38 O1-O6: the classifier/default destructive path was removed, the common executor no longer owns mutation, ordinary and P7 cleanup converge on `mdstats/training_data/storage/removal.py`, whole-unit owner authority is enforced at the destructive boundary, P7 delegates its filesystem mechanics, and transition/partial-byte truth is carried by the canonical removal owner rather than inferred later.

Two genuine closure blockers remain and are bounded by `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_20.md`:

1. **O7 source/specification reconciliation is incomplete.** The Markdown still calls the ordinary plan-bound path an "ordinary default single-file removal" and says the public thin remover retains an "unbound convenience mode". Both describe machinery Revision 38 intentionally removed. The generated PDF therefore reproduces a false contract even though its build succeeded. Repair the contract by deleting/altering the stale claims; do not restore a default or unbound destructive route in code.
2. **Exact-candidate functional acceptance is unproven.** The implementation SHA has no recorded GitHub Actions runs or commit statuses, and the closure handoff records no exact regression/integration/static execution commands or results. Source presence and static inspection are not execution evidence. Run and record the Revision-38 focused and affected-surface functional checks on the exact assembled candidate after the last material edit.

External DFT, long GPU production, and machine-specific HPC/shared-filesystem qualification remain deferred/nonblocking exactly as Revision 38 states. The reopened checks are ordinary functional regression/integration and closure verification, not production qualification.
