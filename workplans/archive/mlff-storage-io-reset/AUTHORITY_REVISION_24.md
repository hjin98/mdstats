---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 24
status: reopened
amended_date: 2026-09-02
current_authority_pointer: true
supersedes_authority_revision: 23
reviewed_authority_revision: 23
reviewed_plan_head: f16c26da1209f72d754367bf530d1dfdd1579cad
repair_plan_closure_commit: 87b9d2d28df952a2c418b76242af1cf84580ee11
reviewed_executable_commit: 9da6525be75c328ffbbf6968cebe773e2dc8921e
reviewed_executable_tree: 7ff82374cbc966795e710f21ba3737d892af57f2
review_verdict: NO-PASS
design_disposition: closed implementation-ready
precedence: Revision 21 remains the accepted final repair design. Revisions 22 and 23 remain binding in full except where Revision 24 makes their descriptor/root-identity and acceptance instructions more precise. Revision 24 closes the remaining plan-level gaps without reopening parent architecture or P1-P7 science. AUTHORITY.md is the sole canonical navigation entrypoint.
---

# Storage/I-O reset package authority — Revision 24 final repair-plan closure

## Disposition

The repair **design/workplan is CLOSED / implementation-ready** after an additional independent Software Design challenge.

The executable at commit `9da6525be75c328ffbbf6968cebe773e2dc8921e` / tree `7ff82374cbc966795e710f21ba3737d892af57f2` remains **NO-PASS / reopened**. No executable behavior changed in Revisions 22-24.

Revision 22 correctly reopened the P7 namespace TOCTOU/root-classification and acceptance-evidence defects. Revision 23 correctly added malformed-state parser totality/report availability and the synchronization diagnostic correction. Revision 24 preserves those requirements and closes two remaining handoff gaps:

1. descriptor/root authority must remain continuous after P7 state authentication through exact certification and the common storage mutation path; and
2. R19's "exact attempt root identity" is defined as a generation-scoped, workspace-portable released-root identity rather than the attempt basename alone.

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
17. `AUTHORITY_REVISION_23.md`;
18. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_24.md`;
19. this authority pointer.

`AUTHORITY.md` is the sole canonical navigation entrypoint. Earlier `current_authority_pointer` fields are historical metadata only.

## Revision-24 closure requirements

### 1. Continuous strict P7 namespace identity

The storage-facing P7 namespace walk begins from an already accepted campaign parent identity and descends continuously through literal `qualification`, canonical `g<generation>`, literal `attempts`, and the exact attempt directory with descriptor/openat-style no-follow primitives on the supported POSIX/Linux target.

A discovered entry is not re-authorized by reconstructing its pathname. State/proof reads and exact released-attempt descendant observation are relative to the authenticated attempt identity. The walk retains the existing nested-mount ownership boundary: a descriptor-safe descent does not make a nested mount campaign-owned.

Absence is distinguished from ambiguity/race. An entry enumerated and then lost/replaced before authoritative open is unresolved namespace change, not ordinary absence. Wrong-kind, symlink, permission/stale/I/O ambiguity, noncanonical reserved generation names, and exhausted bounded race retries fail closed while observational reporting remains available.

Revision-23 malformed-state totality is semantic and remains mandatory if parsing is refactored away from the current path-taking helper.

### 2. Generation-scoped released-attempt root identity

For v3 destructive authority, the exact released-attempt root is the canonical locator relative to the qualification family:

```text
g<campaign_generation>/attempts/<attempt_identity>
```

or an equivalent canonical tuple/digest carrying the same information.

The P7 owner publishes this binding from its authoritative `PostSelectionBinding.campaign_generation` plus canonical attempt identity. The strict storage reader independently recomputes it from the authenticated generation/attempt namespace. Existing state/proof digest, binding, publication, released-state, and attempt checks remain required.

A whole released attempt copied under another generation therefore grants no authority there. The incomplete basename-only development v3 form is diagnostic/retained unless a separately authoritative metadata-only migration can reuse fully authenticated old state/proof without scanning current scratch. The scientific qualification attempt-identity formula does not change.

### 3. Root authority survives to mutation

An exact P7 certification may not be reduced to `certified_nodes` plus a newly resolved generic pathname walk before a consequential action. The common inventory/executor path either consumes the root-bound exact result or freshly reacquires it under the established owner seams immediately before mutation.

The plan's root filesystem identity and the freshly descriptor-observed root identity agree before action. Final recursive removal must preserve or re-establish the authenticated top-level root identity; `shutil.rmtree.avoids_symlink_attacks` alone is not proof that a separately authenticated root name was not replaced before entry. If the supported platform cannot preserve the proof, retain/refuse rather than weaken the authority boundary.

Symlink/special/unexpected nodes and nested mounts continue to reduce authority. The advisory P7 attempt lock serializes supported owner writes; it is not treated as a security proof that arbitrary namespace replacement cannot occur.

## Implementation route

Resume at **R21-E2** in this order:

1. Revision-22 namespace repair + Revision-23 parser totality + Revision-24 continuous acquisition/error classification;
2. generation-scoped v3 released-root proof binding;
3. common inventory/executor/final-mutation continuity;
4. stage-local focused regression after each semantic owner repair;
5. R21-E5/F final affected-surface re-derivation and exact-candidate functional acceptance.

Do not reopen conforming CampaignStore R21-E3 source unless the completed diff actually touches it. Do not introduce a persistent inode/path authority ledger.

The precise source/test/compatibility requirements and proxy-proof cases are in `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_24.md`; Revisions 22 and 23 remain fully binding.

## Required final acceptance additions

Besides every Revision-22/23 test and final regression requirement, the exact final candidate must prove:

- canonical-generation spelling and enumerate-then-replace namespace races;
- EACCES/ESTALE-style namespace ambiguity with report availability and global fail-closed retention;
- released P7 scratch nested-mount refusal;
- full released attempt copied cross-generation is rejected by generation-scoped root binding;
- basename-only incomplete proof grants no authority;
- after under-lock exact certification, a symlink swap **and a same-shaped plain-directory/inode swap** before the final common mutation seam cannot transfer authority to the replacement tree;
- structural absence of any P7 released-attempt consumer that converts exact root-bound certification back into path-only recursive authority.

Reconcile `docs/specs/training_data/mlff_storage_management_spec.md` to the completed persisted-proof/root-continuity contract. Permanent architecture/user documentation changes only if the final accepted implementation materially changes those surfaces.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not blockers.

## Final design disposition

A snapshot-loss, trust-boundary, concurrency, compatibility, destructive-consumer, and proxy-proof challenge found no further plan-level gap after Revision 24.

**Design/workplan:** **CLOSED / implementation-ready.**

**Executable:** **NO-PASS / reopened** until Revisions 22, 23, and 24 are implemented and exact-candidate evidence passes.