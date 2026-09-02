---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 23
status: reopened
amended_date: 2026-09-02
current_authority_pointer: true
supersedes_authority_revision: 22
reviewed_authority_revision: 22
reviewed_executable_commit: 9da6525be75c328ffbbf6968cebe773e2dc8921e
reviewed_executable_tree: 7ff82374cbc966795e710f21ba3737d892af57f2
reviewed_branch_head: 071387cb21c1a046f4ffa7b641bcdd3ad2da1699
review_verdict: NO-PASS
precedence: Revision 21 remains the accepted final repair design. Revision 22 remains binding in full. Revision 23 adds the remaining malformed-state error-totality/report-availability requirement and corrects the synchronization-diagnostic closure claim; no parent architecture or P1-P7 science is reopened. AUTHORITY.md is the sole canonical navigation entrypoint.
---

# Storage/I-O reset package authority — Revision 23 implementation review closure amendment

## Disposition

The implementation at executable commit
`9da6525be75c328ffbbf6968cebe773e2dc8921e` / tree
`7ff82374cbc966795e710f21ba3737d892af57f2` remains **NO-PASS / reopened**.

The generated-document successor `071387cb21c1a046f4ffa7b641bcdd3ad2da1699` does not alter the executable review target. Revision-22 design commit `d4305fa975ddcde6106fe39a3335ffee9c15aef5` correctly reopens the main P7 namespace/TOCTOU and acceptance-evidence defects. This Revision-23 amendment adds one source-level strict-reader closure defect omitted from Revision 22 and corrects one non-blocking factual closure note.

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
12. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md` (Revision 20);
13. `AUTHORITY_REVISION_21.md`;
14. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_5.md` (Revision 22);
15. `AUTHORITY_REVISION_22.md`;
16. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_6.md` (Revision 23);
17. this authority pointer.

`AUTHORITY.md` is the sole canonical navigation entrypoint. Earlier `current_authority_pointer` fields are historical metadata only.

## Bounded remaining work

Preserve every conforming Revision-20/21 repair and every Revision-22 requirement. Reopen only the already bounded R21-E2/E5/F surfaces plus the following Revision-23 additions:

1. make the strict P7 attempt-state owner total over structurally malformed but parseable JSON state records so `KeyError`/`TypeError`-class record-shape corruption becomes explicit unresolved authority and does not make observational `storage report` unavailable;
2. prove those malformed-state cases propagate through owner integrity and workspace-wide retention ambiguity while reporting stays usable and consequential storage remains fail-closed;
3. remove the duplicate `OwnerSynchronization.to_dict()` so the single diagnostic serializer actually contains `attempt_roots` as Revision 22 intended;
4. remove the dead `or True` externalization-test escape if that affected test file is touched;
5. complete all Revision-22 proxy-proof repairs and exact final executable candidate evidence.

The precise repair and acceptance instructions are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_6.md`.

## Preservation boundary

No target-size, P2/P3/P4/P5/P7 scientific/currentness/publication/qualification semantics are reopened. Do not redesign the owner-driven storage architecture, P5/P7 typed proof representation, CampaignStore writer architecture, archive/dedup/restore/audit/control-plane architecture, or established synchronization ordering.

The source repair remains local to P7 storage-facing namespace/state authentication and the affected synchronization diagnostic serializer/tests.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

**Design/workplan disposition:** accepted design remains closed; Revision 23 supplies the final bounded implementation-review amendment.

**Executable disposition:** **NO-PASS / reopened under Revision 23** until Revision 22 + Revision 23 source repairs, proxy-proof counterfactuals, and exact-candidate functional evidence are complete.