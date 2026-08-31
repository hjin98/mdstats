---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13
status: reopened
reviewed_implementation_commit: 89c6d9bf5c21236436342043e5afca194b3da4e7
reviewed_implementation_tree: 7d6ebd9ecf6423de0a6dc01448b932a760eda383
post_implementation_documentation_head: d10c643349a646b361357fc3a09372b4fb3306c6
review_verdict: NO-PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict.

Independent review of the revision-12 repair implementation at executable commit `89c6d9bf5c21236436342043e5afca194b3da4e7`, tree `7d6ebd9ecf6423de0a6dc01448b932a760eda383`, is **NO-PASS**. The later branch head `d10c643349a646b361357fc3a09372b4fb3306c6` is generated-documentation-only and does not alter the executable verdict.

Revision 13 is narrow. Revision 12 genuinely fixed the LAMMPS bar/GPa conversion, pressure/stress sign, named source adapter, main per-axis deployed PBC execution, and introduced a sound resource-observation concept. Revision 13 retains those repairs while reopening the remaining stress capability/provenance semantics, attempt-wide resource evidence and disk safety, static PBC observation completeness, release-evidence referential integrity, and the still-blocking real-runtime/final target-machine gates.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan — controlling verdict;
2. accepted/reclosed predecessor P1-P6 authorities, including the revision-11 P5 publication-decision repair and affected P6 rebind;
3. `P7_REVISION_13_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — current residual repair and closure authority;
4. `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where revision 13 does not preserve/clarify/supersede it;
5. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where later revisions do not supersede it;
6. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` — implementation-state architecture except where later revisions supersede it;
7. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base qualification science and no-fallback contract except stale predecessor assumptions already superseded;
8. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor handoff;
9. revisions 3-9 — historical predecessor-entry alignment records.

Historical implementation/review evidence is preserved. `P7_REVISION_12_IMPLEMENTATION_EVIDENCE.md` is evidence for the reviewed revision-12 candidate; it is not revision-13 closure evidence.

## Residual blocking surfaces

P7 remains reopened until all of the following close on one final frozen candidate:

- **R13-B9A:** stress capability must be exact per component/member/geometry claim, not a singleton derived from publication member 0 and deployment policy;
- **R13-B9B:** applicable trained stress may not pass when deployment/reference stress evidence is unavailable, and external-reference stress source units/sign/order/canonicalization must be authenticated;
- **R13-B7:** resource evidence must cover the complete resumable attempt, include locked timing and stable scope material/selected device, and preserve disk reserve with required incremental headroom;
- **R13-B13:** static deployed observations must preserve and verify the exact executed PBC/cell, not only the request;
- **R13-B14:** public terminal/release resolution must authenticate the resource observation and release-index -> terminal-record graph;
- **R12-B11:** an actual frozen P5 publication member must execute through the real target-head mdstats deployment -> MACE ML-IAP -> supported LAMMPS path;
- **R12-B12:** final target-machine qualification with real authenticated reference evidence, then explicit one-shot locked activation and immutable terminal close/reopen, must run.

## Preserved repaired surfaces

Do not redesign unless a residual repair produces concrete contradictory evidence:

- P5 owns both supported pre-qualification publication policies; P7 does not rank members;
- target-head identity remains mandatory through publication/export/ML-IAP construction;
- LAMMPS thermo pressure remains converted only by the fixed bar/compression source adapter to canonical tensile-positive eV/A^3 stress;
- deployed requests and dynamics execution retain exact three-axis PBC and axis-selective minimum-image behavior;
- public P7 binding currentness, reference-bundle descendant identity, reference-relaxed dynamics, one-shot locked disclosure/restart, explicit reference protocol, canonical analysis ownership, and no downstream fallback remain binding;
- resource measurements remain observational release evidence and cannot change science;
- the successor storage architecture must not be pulled into P7.

## Sequence consequence

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked. The post-P7 storage workplan may adopt a P7 baseline only after revision-13 source repair, fresh affected regression/integration, real current-publication MACE target-head execution, final target-machine real-reference qualification, one-shot locked closure, full terminal/resource/reference evidence graph close-reopen, and independent Software Design PASS.
