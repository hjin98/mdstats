---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 30
status: closed-implementation-ready
supersedes_revision: 29
reviewed_executable_commit: 6423a3f33a36c09ca1b89f5740f42c402b1993d2
reviewed_executable_tree: a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
current_workplan: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-bounded-repair
---

# Storage/I-O reset authority — Revision 30

Revision 30 is the final Design -> Implementation closure for the remaining storage final-apply repair. It consolidates the still-binding Revision-28 and Revision-29 semantics and closes the additional gaps found during final plan review. Earlier Revision-26/28/29 repair/review documents are historical provenance, not required normative inputs for implementation.

## Current normative handoff

Implementation reads:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` for the broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` for the complete remaining final-apply repair contract;
- `docs/specs/training_data/mlff_storage_management_spec.md` for the current storage product contract;
- `AUTHORITY.md` only as canonical navigation/status.

## Frozen final-apply contract

The final repair must preserve and satisfy all of the following:

1. exact released P7 authority is derived from authenticated state/proof identity, bound into the immutable plan, and rederived on the final live descriptor;
2. final P7 certification and mutation share one retained no-follow descriptor capability under the established storage/P5/P7 synchronization;
3. immediately before each released-member mutation, the real P7 owner compares the plan-bound target identity by no-follow descriptor-relative observation; at minimum preserve the current stale-check dimensions `kind/device/inode/size_bytes/mtime_ns`;
4. a closed session is permanently unspendable before any filesystem syscall, even if its integer fd is later reused;
5. released proof topology is an upper bound: recorded absence is monotonic and resumable, while live additions/kind changes/symlinks/special nodes/mounts/substituted roots/release drift/target drift reduce authority;
6. a mutation-time refusal or partial contradiction invalidates later same-attempt destructive actions for that execution; successful removal/already-absence may continue, and independent attempts may continue;
7. the proof-node lookup is derived once per ephemeral session and cannot be mutated to widen authority;
8. cleanup outcomes remain structured as removed / already absent / no-change refusal / partial mutation followed by refusal or failure;
9. post-mutation exceptions must cross the current action boundary carrying structured mutation truth and measured bytes before propagation reaches the executor's outer interruption handler;
10. partial/nested reclaimed-byte accounting uses the existing storage metric, propagates successful nested removals exactly, and does not silently overcount hard links where the planner metric deduplicates inode identity;
11. ordinary reporting remains bounded, Python `>=3.10` remains supported, no new persistent authority/control-plane registry is introduced, and the accepted R26 POSIX threat boundary remains unchanged.

## Acceptance authority

Material acceptance uses the real `StorageExecutor`, existing owner synchronization, real P7 authority/session path, real settlement, and durable audit. Deterministic hooks may only sit below these semantic owners.

The Revision-30 plan contains the complete focused counterfactual set and candidate-bound final acceptance. After the final executable edit, acceptance must bind actual commands/results to the exact executable commit/tree and include full storage core/integration, affected current-owner regressions, clean collection, final affected-surface re-derivation plus fresh affected regression/integration, and static/current-doc validation. Whole-repository behavioral pytest remains conditional on unbounded impact or independent repository policy. External-DFT, long GPU, and environment-specific HPC/shared-storage production qualification remain deferred and nonblocking.

## Disposition

**Design/workplan: CLOSED / implementation-ready under Revision 30.**

**Reviewed executable: NO-PASS / bounded implementation repair remains required.**
