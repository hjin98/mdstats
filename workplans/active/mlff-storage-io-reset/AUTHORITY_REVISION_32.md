---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 32
status: reopened
supersedes_revision: 31
reviewed_executable_commit: 2e01d6fa5119ba67088f7c312c44962eba902c8e
reviewed_executable_tree: fe927d28612d411303676fc04d5a9cd7164720b1
reviewed_branch_head: 159c986bdf6273c0e7a44f833df30d4f3d10f852
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
implementation_review: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 32

Revision 32 is a bounded independent implementation-review reopen of the Revision-31 implementation. Revision 30 remains the accepted closed design. No P1-P7 science/currentness, owner-driven storage architecture, R26 historical test/tool retirement, CampaignStore ownership, P5 typed proof, archive/dedup/restore/control-plane design, or accepted descriptor-pinned POSIX threat boundary is reopened.

## Current normative handoff

Implementation reads:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` for the broader frozen owner-driven storage architecture and non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` for the complete accepted final-apply design and preservation boundary;
3. `docs/specs/training_data/mlff_storage_management_spec.md` for the current storage product contract;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md` for the bounded Revision-32 corrections required by this review;
5. `AUTHORITY.md` only as canonical navigation/status.

This supplied set is snapshot-complete for current work. Revision 32 incorporates the still-binding Revision-31 acceptance obligations; no current requirement depends exclusively on superseded review files, Git history, prior conversation, or local tool state.

## Review disposition

Executable `2e01d6fa5119ba67088f7c312c44962eba902c8e` materially fixes and must preserve:

- explicit per-action credited/reclaimed byte evidence and aggregate summation from those action values;
- one executor-owned action recorder for structured post-mutation failure transport across CLI and default cleanup paths;
- exact generic/common recursive byte tracking for ordinary positive-byte partial cases;
- P7 measure-before-delete refusal when a regular file cannot be measured;
- mandatory complete plan-bound target identity at the exported P7 mutation boundary;
- the previously conforming Revision-30 release/root binding, retained capability, proof-as-upper-bound, same-attempt invalidation, and once-per-session proof lookup mechanisms.

It is nevertheless **NO-PASS** because:

- P7 recursion still conflates positive reclaimed bytes with mutation truth, so zero-byte/empty-directory destructive transitions can be misreported as no change after a later refusal/failure;
- the new generic/common recursive pathname walker no longer inherits `shutil.rmtree`'s symlink-attack-resistant fd-based descent even though it still checks `shutil.rmtree.avoids_symlink_attacks`, creating a new deletion-safety regression;
- several Revision-31 acceptance claims remain proxy/helper evidence instead of real `StorageExecutor.run` + settlement + durable-audit evidence;
- the required independent-P7-attempt scoping case and exact deterministic post-mutation byte equality remain unclosed;
- exact-candidate final behavioral regression/integration/static evidence for the executable commit/tree is not supplied.

The precise findings and repair contract are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md`.

## Authority

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus bounded Revision-32 implementation corrections.**

**Reviewed executable:** **NO-PASS / reopened under Revision 32.**
