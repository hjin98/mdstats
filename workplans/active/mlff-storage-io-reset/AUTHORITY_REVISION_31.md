---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 31
status: reopened
supersedes_revision: 30
reviewed_executable_commit: 3295bc47775f521db3518f6f1ba8419c78cd8b82
reviewed_executable_tree: 1fb6ac2cf368922adde06171216f55e50bf04811
reviewed_branch_head: 2524ecfcf37d9045a5544c310749a42ddde34407
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
implementation_review: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_10.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 31

Revision 31 is a bounded independent implementation-review reopen of the Revision-30 final-apply implementation. Revision 30 remains the accepted closed design. No P1-P7 science/currentness, owner-driven storage architecture, R26 historical test/tool retirement, CampaignStore ownership, P5 typed proof, archive/dedup/restore/control-plane design, or descriptor-pinned POSIX threat boundary is reopened.

## Current normative handoff

Implementation reads:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` for the broader frozen owner-driven storage architecture and non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` for the complete accepted final-apply design and preservation boundary;
3. `docs/specs/training_data/mlff_storage_management_spec.md` for the current storage product contract;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_10.md` for the bounded corrections required by this review;
5. `AUTHORITY.md` only as canonical navigation/status.

This supplied set is snapshot-complete for current work. Revision 31 adds no requirement that depends exclusively on Git history, prior conversation, or superseded review files.

## Review disposition

Executable `3295bc47775f521db3518f6f1ba8419c78cd8b82` materially implements and must preserve:

- exact released-authority derivation and plan binding;
- strict released-attempt session acquisition and one retained descriptor through final P7 mutation;
- descriptor-relative target re-observation in the production cleanup caller;
- one-way close checking before descriptor syscalls;
- proof-as-upper-bound monotonic shrink and interrupted retry;
- same-attempt capability invalidation after ordinary mutation-boundary refusal/partial outcome;
- once-per-session read-only typed proof lookup;
- four typed mutation outcomes and partial-failure transport for the covered P7 durability case;
- exact recursive byte propagation for normally observed entries, including action-local hard-link deduplication;
- aligned current specification text and generated PDF successor.

It is nevertheless **NO-PASS** because mutation truth and final target authority are still bypassable on concrete supported paths, per-action audit evidence is incomplete, and mandatory real-owner/candidate-bound acceptance remains incomplete. The precise findings and repair contract are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_10.md`.

## Authority

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus bounded Revision-31 implementation corrections.**

**Reviewed executable:** **NO-PASS / reopened under Revision 31.**
