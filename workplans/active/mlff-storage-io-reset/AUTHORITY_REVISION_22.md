---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 22
status: reopened
amended_date: 2026-09-02
current_authority_pointer: true
reviewed_authority_revision: 21
reviewed_executable_commit: 9da6525be75c328ffbbf6968cebe773e2dc8921e
reviewed_executable_tree: 7ff82374cbc966795e710f21ba3737d892af57f2
reviewed_branch_head: 071387cb21c1a046f4ffa7b641bcdd3ad2da1699
review_verdict: NO-PASS
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers. Revision 21 remains the accepted design; the current supplied implementation contract is the Revision-21 supplied contract plus STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_5.md and this authority pointer. Revision 22 reopens only bounded implementation and acceptance closure.
---

# Storage/I-O reset package authority — Revision 22 implementation review

## Disposition

The implementation at executable commit
`9da6525be75c328ffbbf6968cebe773e2dc8921e` / tree
`7ff82374cbc966795e710f21ba3737d892af57f2` is **NO-PASS / reopened**.

Branch head `071387cb21c1a046f4ffa7b641bcdd3ad2da1699` is a generated-document-only successor and does not change the executable review target.

Revision 21 remains the final accepted repair design. Most Revision-20/21 repairs are conforming and must be preserved. The remaining implementation is bounded to:

1. close the P7 no-follow namespace hierarchy at the actual traversal syscall/descriptor boundary, including correct fail-closed treatment of a substituted/unreadable qualification family root;
2. eliminate the parallel followable attempt-directory traversal in storage-facing P7 views/reporting and derive attempt enumeration from the same strict namespace authority;
3. correct the remaining proxy-proof tests: truly self-digest-valid wrong-root state, released-attempt special node, deterministic proof of both actual reopen/cleanup lock orderings, and family-root/concurrent ancestor-substitution cases;
4. supply exact final executable commit/tree regression and integration evidence required by Revision 21 E5/F.

The complete findings and repair instructions are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_5.md`.

## Current supplied implementation contract

Implementation must read these artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md`;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md`;
7. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md`;
8. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md`;
9. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md`;
10. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_18.md`;
11. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_19.md`;
12. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md`;
13. `AUTHORITY_REVISION_21.md`;
14. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_5.md`;
15. this authority pointer.

`AUTHORITY.md` is the sole canonical navigation entrypoint. Earlier `current_authority_pointer` fields are historical metadata only unless explicitly routed by `AUTHORITY.md`.

## Frozen preservation boundary

Do not reopen or redesign:

- target-size V7 science, P2 statistics, P3/P4 currentness, P5 CV/final production, P7 qualification/calibration/locked/release science;
- the owner-driven storage architecture;
- typed/no-follow P5/P7 proof representation and common inventory/executor authority;
- P7 v3 proof publication/lifecycle, canonical binding-derived identity, persisted state digest, workspace-wide ambiguity fence, or established attempt-lock order;
- CampaignStore RLock/flock writer architecture, constructor census, observational early guard, writer-lock ownership;
- archive/dedup/restore/audit/storage-control-plane architecture.

The remaining source repair is local to P7 storage-facing namespace authentication/traversal and its consumers.

## Rework route

Resume from **R21-E2** for the P7 namespace/authentication defect, then complete corrected focused counterfactuals and **R21-E5/F** final candidate-bound functional acceptance.

CampaignStore R21-E3 source is accepted and does not need reimplementation unless a later diff actually changes it.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not blockers.

**Disposition:** implementation **NO-PASS / reopened under Revision 22**. Revision-21 design remains accepted and implementation-ready after the precise bounded repair in reopen 5.
