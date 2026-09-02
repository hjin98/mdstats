---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 24
status: reopened
current_authority_pointer: AUTHORITY_REVISION_24.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I-O reset package.

The **Revision-19 storage architecture and Revision-21 final repair design remain accepted**. Revisions 22 and 23 are bounded implementation-review reopens. Revision 24 is the final independent **repair-plan closure amendment**: it preserves those findings and closes the remaining descriptor/root-continuity and exact released-attempt-root-identity gaps in the implementation handoff. None of Revisions 22-24 reopens P1-P7 science or the owner-driven storage architecture.

The reviewed executable remains:

```text
commit 9da6525be75c328ffbbf6968cebe773e2dc8921e
tree   7ff82374cbc966795e710f21ba3737d892af57f2
```

The executable has not changed in Revisions 22-24. The later branch commits add generated documentation and workplan/design authority only.

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
17. `AUTHORITY_REVISION_23.md`;
18. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_24.md`;
19. `AUTHORITY_REVISION_24.md`.

Earlier authority revisions other than explicitly included Revision 11 are provenance. Any `current_authority_pointer: true` field inside a superseded revision artifact is historical metadata only; this `AUTHORITY.md` entrypoint controls navigation.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, reference, or release science for convenience.

## Bounded remaining implementation work

Preserve every conforming Revision-20/21 repair. Revision 22 remains binding and requires descriptor/identity-bound no-follow P7 namespace traversal, correct family-root ambiguity, one strict storage-facing attempt enumeration, corrected proxy-proof fixtures, and exact candidate-bound final evidence. Revision 23 remains binding and requires malformed-but-parseable P7 state to become explicit unresolved authority while report remains available, plus the `OwnerSynchronization.to_dict()` serializer cleanup and test cleanup.

Revision 24 completes the implementation contract in three places:

- the authenticated P7 namespace identity must be continuous from the accepted campaign parent through `qualification/g<generation>/attempts/<attempt>` into state/proof/descendant observation, with exact absence-versus-race/error semantics, canonical generation naming, bounded retries, descriptor cleanup, and the already accepted nested-mount refusal;
- a released-attempt v3 proof's **exact root identity** is generation-scoped and workspace-portable: `g<campaign_generation>/attempts/<attempt_identity>` (or an equivalent canonical tuple/digest). Basename-only proof authority is insufficient; copied cross-generation attempts remain retained;
- exact P7 root authority must survive through owner views, common inventory certification, plan revalidation, and the final cleanup/archive/dedup/reclaim mutation boundary. A descriptor-certified result may not be silently reduced to typed names plus a fresh pathname recursive walk. Final mutation must preserve/re-establish the authenticated root identity or refuse.

The exact requirements and proxy-proof acceptance are in `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_24.md` together with Revisions 22 and 23.

## Rework route

Resume at bounded **R21-E2**:

1. strict namespace acquisition + Revision-23 parser totality;
2. generation-scoped v3 released-root binding;
3. root-identity continuity through common certification and final mutation;
4. stage-local focused regression for each semantic owner;
5. **R21-E5/F** final affected-surface re-derivation and exact-candidate regression/integration evidence.

CampaignStore R21-E3 source is conforming and should remain untouched unless the final repair diff actually affects it.

The current storage specification must be reconciled to the completed generation-scoped released-root and root-continuity persistence/destructive-authority contract. Permanent architecture/user documents change only if the accepted present architecture or operator behavior actually changes.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

**Design/workplan disposition:** **CLOSED / implementation-ready under Revision 24.**

**Executable disposition:** **NO-PASS / reopened** until all Revision-22, Revision-23, and Revision-24 repairs and exact-candidate acceptance requirements are implemented and evidenced.