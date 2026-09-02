---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 22
status: reopened
current_authority_pointer: AUTHORITY_REVISION_22.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I/O reset package.

The **Revision-19 storage architecture and Revision-21 final repair design remain accepted**. Revision 22 is an implementation-review reopen of the Revision-21 implementation, not a scientific or storage-architecture redesign.

The reviewed executable is:

```text
commit 9da6525be75c328ffbbf6968cebe773e2dc8921e
tree   7ff82374cbc966795e710f21ba3737d892af57f2
```

Current branch head `071387cb21c1a046f4ffa7b641bcdd3ad2da1699` changes generated documentation only and does not alter the functional review target.

## Current supplied contract

Read these artifacts together:

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
15. `AUTHORITY_REVISION_22.md`.

Earlier authority revisions other than explicitly included Revision 11 are provenance. Any `current_authority_pointer: true` field inside a superseded revision artifact is historical metadata only; this `AUTHORITY.md` entrypoint controls navigation.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, reference, or release science for convenience.

## Bounded remaining implementation work

Preserve the conforming Revision-20/21 implementation. Reopen only:

- the P7 storage-facing namespace walk: a present wrong-kind/unreadable qualification family root must become explicit unresolved authority, and generation/`attempts`/attempt descent must be identity-bearing/no-follow at the actual traversal/open boundary rather than `lstat` followed by a new path-based `scandir`/open;
- storage-facing attempt enumeration/reporting must derive from the same strict namespace result instead of independently following `Path.is_dir()/iterdir()` through the P7 attempt hierarchy;
- acceptance fixtures must truly isolate the required failure modes: self-digest-valid wrong-root state, released-attempt special node, actual deterministic owner-first and storage-first lock orderings, family-root substitution, and concurrent ancestor swap;
- exact final executable commit/tree regression and integration evidence required by Revision 21 E5/F must be supplied after the repair and final affected-surface re-derivation.

The exact repair and test instructions are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_5.md`.

Resume at bounded **R21-E2**, then complete corrected counterfactuals and **R21-E5/F**. CampaignStore R21-E3 source is conforming and should remain untouched unless the repair actually affects it.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

**Design/workplan disposition:** Revision-21 design remains closed and accepted; Revision 22 supplies bounded implementation-review rework instructions.

**Executable disposition:** **NO-PASS / reopened under Revision 22** until the P7 namespace race/root-classification defect, acceptance counterfactuals, and candidate-bound functional evidence are closed.
