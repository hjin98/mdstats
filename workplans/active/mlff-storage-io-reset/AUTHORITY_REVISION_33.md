---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 33
status: reopened
supersedes_revision: 32
reviewed_executable_commit: 2e01d6fa5119ba67088f7c312c44962eba902c8e
reviewed_executable_tree: fe927d28612d411303676fc04d5a9cd7164720b1
reviewed_plan_commit: 1b9b3845777c34480c1cd032c49cf9281a30049a
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_12.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
plan_review_disposition: amended-resealed
---

# Storage/I-O reset authority — Revision 33

Revision 33 is a second independent review of the **Revision-32 implementation handoff itself** against the current repository ownership, trust, API, and testing surfaces. Revision 30 remains the accepted closed final-apply design. Revision 33 does not reopen P1-P7 science/currentness, owner-driven storage architecture, R26 historical retirement, CampaignStore ownership, P5 typed proof, archive/dedup/restore/control-plane architecture, Python `>=3.10`, or the accepted POSIX threat boundary.

## Current normative handoff

Implementation reads only:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_12.md` — **complete Revision-33 bounded implementation and acceptance contract**;
5. `AUTHORITY.md` only as canonical navigation/status.

Revision 31/32 review files are historical provenance and are not required to recover any current obligation. The supplied current set is snapshot-complete.

## Plan-review findings incorporated into Revision 33

The Revision-32 direction remains correct but was not yet lossless enough for implementation. Revision 33 closes these plan-level gaps:

- makes the existing action-scoped `MutationLedger` the canonical owner of mutation truth, exact action bytes, and inode deduplication instead of permitting another parallel P7 `freed`/`seen` authority;
- requires a public-API fd-relative/no-follow tracked recursive deletion mechanism for generic/common cleanup rather than leaving an effectively unsupported `shutil` alternative for exact per-transition accounting;
- binds destructive nested-mount decisions to the existing canonical `storage.trust` policy and adds mutation-time mount acceptance, not merely symlink-race acceptance;
- closes post-mutation observation, mount-check, descriptor-open/enumeration and descriptor-close failures, including the converse no-mutation case when an empty directory fails fsync before its rmdir;
- requires a real two-independent-P7-attempt cleanup execution because the current owner inventory already represents multiple attempt authorities/actions;
- reconciles the public `remove_durably` compatibility surface with the canonical typed removal mechanism so repeated fixes do not leave two drifting recursive deletion authorities;
- restores the exact previously known affected-regression file set that Revision 32 compressed away, while still requiring final affected-surface expansion where needed;
- corrects traversal documentation ownership so `storage.trust` owns mount policy while planning/read-only and destructive descriptor walkers remain distinct mechanisms;
- records Serena/Semgrep as optional high-information structural tools without making local tool state, cloud scanning, or a protocol-version upgrade part of product authority.

## Preserved implementation state

The executable `2e01d6fa5119ba67088f7c312c44962eba902c8e` materially implements and must preserve the conforming Revision-31 repairs: exact per-action serialized reclaimed bytes, one executor-owned partial-failure recorder for default/CLI removal paths, generic/common mutation-ledger accounting, retention of unmeasurable P7 files, mandatory complete target identity, exact released authority/root binding, live P7 descriptor capability, proof-as-upper-bound semantics, same-attempt invalidation, once-per-session proof lookup, and the four typed outcomes.

It remains **NO-PASS** until the Revision-33 implementation and acceptance obligations close.

## Authority

**Accepted design:** **CLOSED / implementation-ready under Revision 30.**

**Current bounded implementation handoff:** **Revision 33 / reopened.**

**Reviewed executable:** **NO-PASS / reopened pending Revision 33.**
