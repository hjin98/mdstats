---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 23
status: reopened
current_authority_pointer: AUTHORITY_REVISION_23.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I/O reset package.

The **Revision-19 storage architecture and Revision-21 final repair design remain accepted**. Revisions 22 and 23 are bounded implementation-review reopens of the Revision-21 implementation; neither reopens P1-P7 science or the owner-driven storage architecture.

The reviewed executable remains:

```text
commit 9da6525be75c328ffbbf6968cebe773e2dc8921e
tree   7ff82374cbc966795e710f21ba3737d892af57f2
```

Branch head `071387cb21c1a046f4ffa7b641bcdd3ad2da1699` is a generated-document-only successor and does not change the functional review target. Revision-22 design commit `d4305fa975ddcde6106fe39a3335ffee9c15aef5` adds workplan artifacts only and likewise does not change executable behavior.

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
15. `AUTHORITY_REVISION_22.md`;
16. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_6.md` (Revision 23);
17. `AUTHORITY_REVISION_23.md`.

Earlier authority revisions other than explicitly included Revision 11 are provenance. Any `current_authority_pointer: true` field inside a superseded revision artifact is historical metadata only; this `AUTHORITY.md` entrypoint controls navigation.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, reference, or release science for convenience.

## Bounded remaining implementation work

Preserve the conforming Revision-20/21 implementation. Revision 22 remains fully binding and requires:

- descriptor/identity-bound no-follow P7 namespace traversal at the actual open/enumeration boundary, including correct absent-versus-ambiguous qualification-family handling and concurrent ancestor-swap closure;
- storage-facing attempt enumeration/reporting derived from the same strict namespace authority, with no parallel followable `Path.is_dir()/iterdir()` traversal of the state-bearing hierarchy;
- corrected proxy-proof fixtures: truly self-digest-valid wrong-root state, released-attempt special node, deterministic proof of both actual reopen/cleanup lock orderings, family-root substitution/unreadability, and concurrent ancestor-swap cases;
- exact final executable commit/tree regression and integration evidence after final affected-surface re-derivation.

Revision 23 additionally requires:

- structurally malformed but parseable attempt-state records to become explicit unresolved authority instead of escaping `KeyError`/`TypeError`, while observational `storage report` remains available and consequential authority remains workspace-wide fail-closed;
- removal of the duplicate `OwnerSynchronization.to_dict()` so diagnostics actually serialize `attempt_roots`;
- removal of the dead `or True` externalization-test escape if that test file is touched.

Exact instructions are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_5.md` and `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_6.md`.

Resume at bounded **R21-E2**, then complete corrected counterfactuals and **R21-E5/F**. CampaignStore R21-E3 source is conforming and should remain untouched unless the repair actually affects it.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

**Design/workplan disposition:** accepted design remains closed; Revision 23 is the current bounded implementation-review authority.

**Executable disposition:** **NO-PASS / reopened under Revision 23** until all Revision-22/23 repair and exact-candidate acceptance requirements are closed.