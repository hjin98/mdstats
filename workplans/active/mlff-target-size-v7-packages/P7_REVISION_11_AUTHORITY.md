---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 11
status: reopened
reviewed_implementation_commit: afe4d690f1f7c084ac33077ecdcb24d67cd14802
reviewed_implementation_tree: ab4c1d32e44585615ba0501fb44d5666afe82190
review_verdict: NO-PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 11 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict. Revision 11 does not weaken or replace any frozen parent requirement.

Independent implementation review of P7 revision 10 at executable commit `afe4d690f1f7c084ac33077ecdcb24d67cd14802`, tree `ab4c1d32e44585615ba0501fb44d5666afe82190`, is **NO-PASS**. P7 is reopened for the blocking repairs specified in `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md`.

Documentation/PDF-only commit `f86b2de68072394dd189d21c46b8b0d4987a1a7c` does not alter the reviewed executable behavior; it closes the previously reported stale-PDF item only.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan — controlling verdict;
2. accepted P1-P6 authorities, subject to revision-11's mandatory P5 publication-owner repair and subsequent P6 reclosure/rebind;
3. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — current defect-specific repair and closure authority;
4. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` — implementation-state architecture, except where revision 11 explicitly reopens/corrects it;
5. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base qualification science and no-fallback contract, except prior stale predecessor assumptions already superseded by revision 10/11;
6. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral handoff, preserving P6 cache/safe-cleanup ownership and keeping the successor storage reset post-P7;
7. revisions 3-9 — historical predecessor-entry alignment records.

`P7_IMPLEMENTATION_EVIDENCE.md` remains historical implementation evidence for the reviewed revision-10 candidate. It is not closure evidence for revision 11 and must not be edited to imply that the reviewed candidate passed.

## Blocking surfaces reopened by revision 11

Revision 11 requires closure of all of the following before P7 can be re-reviewed:

- predecessor-owned publication decision for both `all_qualified_final_seeds` and `single_best_final_seed`, followed by affected P5/P6 reclosure;
- canonical P5 target-head binding through actual MACE deployment/ML-IAP/LAMMPS execution;
- exact P7 binding/currentness validation for plan, terminal record, and release evidence;
- reference-bundle content identity and correct descendant invalidation;
- dynamics on authenticated reference-relaxed bases with complete NVT/NVE/topology/displacement/bond/angle diagnostics;
- crash-resumable one-shot locked activation;
- accepted resource admission/stage scope and race-safe deployed-artifact reuse;
- explicit non-placeholder production reference protocol;
- stress/deformation parity and response when scientifically applicable;
- reconciliation of qualification topology/geometry algorithms with canonical `mdstats.analysis` owners;
- truthful real-owner MACE deployment acceptance rather than analytic-runtime proxy evidence;
- final target-machine, real-reference qualification on one frozen repaired candidate.

## Sequence consequence

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked. P7 cannot be closed, and the successor storage workplan cannot take a post-P7 implementation baseline, until revision-11 repairs, fresh regression/integration, final target-machine qualification, one-shot locked closure, immutable terminal evidence close/reopen, and independent final review all PASS.

The required repair sequence and acceptance matrix are defined in `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` and are binding.