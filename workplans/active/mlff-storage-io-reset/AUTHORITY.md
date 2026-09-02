---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 21
status: reopened
current_authority_pointer: AUTHORITY_REVISION_21.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I/O reset package.

The **Revision-19 storage architecture remains final-closure reviewed and accepted**. Revision 20 correctly reopened the executable implementation for bounded CampaignStore/P7/evidence defects. Revision 21 closes the remaining plan-level gaps found by a second independent design challenge and is now the implementation handoff authority.

The reviewed executable remains:

```text
commit 869ae1b6e9211faa1873d47e7850050cd85b5ff7
tree   a5e6c8868bdec9e88a877e6ca84aa6ef6d609286
```

No executable behavior is changed by Revision 21 itself.

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
13. `AUTHORITY_REVISION_21.md`.

Earlier authority revisions other than explicitly included Revision 11 are provenance. Any `current_authority_pointer: true` field inside a superseded revision artifact is historical metadata only; this `AUTHORITY.md` entrypoint controls navigation.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, reference, or release science for convenience.

## Bounded remaining implementation work

Preserve all conforming R12-R19 source work and all Revision-20 requirements. The remaining repair is limited to:

- CampaignStore observational purity: put the writability guard before all `replace_records_atomically()` externalization/lock/SQLite side effects and prove it with a real externalization case;
- P7 strict attempt-state authority: enumerate actual attempt namespaces no-follow, require a persisted exact current-state digest, and enforce the three-way identity invariant `attempt_root.name == state.attempt_identity == canonical_attempt_identity(state.binding_digest)`;
- consolidate one root-bound strict P7 state result as the sole storage-facing source of liveness/release authority for census, owner views, proof certification, retention, reporting, and touched-attempt classification;
- reject symlink/special/wrong-kind substitutions not only at the state/attempt root but also at authority-bearing generation and `attempts` namespace ancestors;
- when any P7 attempt state is unresolved, keep the mandatory global owner-graph planning blocker and independently make the P7 retention fence deny destructive authorization across the campaign-managed workspace until exact state is repaired;
- repeated terminal release must validate/reuse the retained v3 proof and validate proof/state binding/publication fields;
- add the Revision-20/21 real-owner counterfactuals, including both lock-ordering races, namespace-symlink cases, canonical-identity mismatch, workspace-wide retention-fence bypass test, and special nodes;
- supply exact final executable commit/tree functional regression and integration evidence after final affected-surface re-derivation.

Resume at bounded R21-E2/R21-E3, achieve stage-local semantic plus functional closure, then complete R21-E5/F final acceptance.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

**Design/workplan disposition:** closed and implementation-ready under Revision 21.

**Executable disposition:** NO-PASS / reopened until the bounded repair and candidate-bound acceptance evidence are complete.
