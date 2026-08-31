---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 12
status: reopened
reviewed_implementation_commit: d24c16cecfd25f2dfcd83b10e0850981d5b64318
reviewed_implementation_tree: 2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e
post_implementation_documentation_head: 4f8b624acedf23c0cf15a59ba5d7994336dc9755
review_verdict: NO-PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 12 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict.

Independent review of the revision-11 repair implementation at executable commit `d24c16cecfd25f2dfcd83b10e0850981d5b64318`, tree `2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e`, is **NO-PASS**. The later commit `4f8b624acedf23c0cf15a59ba5d7994336dc9755` changes generated documentation PDFs only and does not change the executable verdict.

P7 is reopened under `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md`. Revision 12 is intentionally narrow: revision-11 B1-B6, B8, and B10 are accepted at source/design level, subject to remaining repairs not regressing them. Revision 12 does not invite their redesign.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan — controlling verdict;
2. accepted/reclosed predecessor P1-P6 authorities, including the revision-11 P5 publication-decision repair and its affected P6 rebind;
3. `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — current residual repair and closure authority;
4. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding except where revision 12 records a repaired surface as closed or gives more specific residual instructions;
5. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` — implementation-state architecture except where later revisions supersede it;
6. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base qualification science and no-fallback contract except stale predecessor assumptions already superseded;
7. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor handoff;
8. revisions 3-9 — historical predecessor-entry alignment records.

Historical implementation/review evidence is not rewritten. In particular, `P7_REVISION_11_IMPLEMENTATION_EVIDENCE.md` remains evidence for the reviewed revision-11 repair candidate; it is not revision-12 closure evidence.

## Residual blocking surfaces

P7 remains reopened until all of the following are closed on one final frozen candidate:

- **R12-B9:** correct and authenticate the LAMMPS-pressure -> canonical ASE/MACE stress boundary, including source units, pressure/stress sign, tensor ordering, and a real capability-based stress applicability decision;
- **R12-B13:** preserve exact per-axis periodic boundary conditions through deployed static/dynamics execution and safety reductions, or fail closed when unsupported;
- **R12-B7:** complete disk-safety integration and immutable measured target-machine performance/resource observations without introducing the successor storage architecture;
- **R12-B11:** execute an actual member of the frozen P5 publication through the real target-head mdstats deployment -> MACE ML-IAP -> supported LAMMPS path; development-host unavailability remains blocking, not a pass;
- **R12-B12:** run final target-machine qualification with real authenticated reference evidence, then explicit one-shot locked activation and immutable terminal close/reopen.

## Preserved repaired surfaces

Do not redesign the following unless a remaining repair produces concrete contradictory evidence:

- P5 owns the pre-qualification publication decision for both supported committee policies; P7 only consumes it;
- canonical target-head identity is part of publication/member/deployment identity and is mandatory at export/build;
- P7 current plan/verdict/release exposure reauthenticates the exact current binding;
- reference-dependent descendants bind exact authenticated bundle content;
- dynamics uses authenticated reference-relaxed starting geometries and the revision-11 diagnostic vocabulary;
- locked disclosure is permanent while incomplete activation is resumable onto the same identity;
- placeholder external-reference protocols fail closed;
- canonical analysis owners are reused through narrow adapters where their semantics apply;
- no downstream qualification result may change target size, CV acceptance, checkpoint, seed/member publication choice, or thresholds.

## Sequence consequence

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked. The post-P7 storage workplan cannot adopt a P7 baseline until revision-12 source repairs, fresh affected regression/integration, actual target-head MACE deployment execution, final target-machine real-reference qualification, one-shot locked closure, immutable terminal evidence/resource observation close-reopen, and independent final Software Design review all PASS.