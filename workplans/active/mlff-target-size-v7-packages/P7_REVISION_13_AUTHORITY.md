---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13.1
status: reopened
reviewed_implementation_commit: 89c6d9bf5c21236436342043e5afca194b3da4e7
reviewed_implementation_tree: 7d6ebd9ecf6423de0a6dc01448b932a760eda383
post_implementation_documentation_head: d10c643349a646b361357fc3a09372b4fb3306c6
review_verdict: NO-PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13.1 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict.

Independent review of the revision-12 repair implementation at executable commit `89c6d9bf5c21236436342043e5afca194b3da4e7`, tree `7d6ebd9ecf6423de0a6dc01448b932a760eda383`, remains **NO-PASS**. The later branch head `d10c643349a646b361357fc3a09372b4fb3306c6` is generated-documentation-only and does not alter that executable verdict.

Revision 13.1 does not reopen the frozen science. It corrects the R12-B11 runtime premise after target-machine diagnostics demonstrated that the intended LAMMPS Python runtime is LAMMPS 10Sep2025 with ML-IAP and KOKKOS available, can start its CUDA KOKKOS backend with effective arguments equivalent to `-k on g 1 -sf kk`, can activate `lammps.mliap.activate_mliappy()` successfully, and can close the LAMMPS instance plus process-owned KOKKOS/MPI native state cleanly. Therefore static `forward_exchange` class introspection is not authoritative runtime-unavailability evidence. Actual frozen-product execution is the semantic owner of B11 capability.

The same diagnostics also showed that `lammps.finalize()` is not an acceptable shutdown owner for this externally owned Python path because it invokes Python finalization; the observed diagnostic reached `Py_FinalizeEx` and segfaulted. The repaired worker must not finalize its owning Python interpreter.

These operator diagnostics refine the implementation contract only. They do **not** close B11; real current-publication MACE execution remains mandatory.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan — controlling verdict;
2. accepted/reclosed predecessor P1-P6 authorities, including the revision-11 P5 publication-decision repair and affected P6 rebind;
3. `P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md` — current B11 runtime owner, lifecycle, acceptance, and revised implementation-order authority;
4. `P7_REVISION_13_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — current residual repair and closure authority where revision 13.1 does not supersede it;
5. `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where revisions 13/13.1 do not preserve/clarify/supersede it;
6. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where later revisions do not supersede it;
7. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` — implementation-state architecture except where later revisions supersede it;
8. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base qualification science and no-fallback contract except stale predecessor assumptions already superseded;
9. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor handoff;
10. revisions 3-9 — historical predecessor-entry alignment records.

Historical implementation/review evidence is preserved. `P7_REVISION_12_IMPLEMENTATION_EVIDENCE.md` is evidence for the reviewed revision-12 candidate; it is not revision-13.1 closure evidence. The target-machine KOKKOS/mliappy startup diagnostics recorded in revision 13.1 are implementation-direction evidence, not B11 product-execution closure evidence.

## Residual blocking surfaces

P7 remains reopened until all of the following close on one final frozen candidate:

- **R13-B9A:** stress capability must be exact per component/member/geometry claim, not a singleton derived from publication member 0 and deployment policy;
- **R13-B9B:** applicable trained stress may not pass when deployment/reference stress evidence is unavailable, and external-reference stress source units/sign/order/canonicalization must be authenticated;
- **R13-B7:** resource evidence must cover the complete resumable attempt, include locked timing and stable scope material/selected device, and preserve disk reserve with required incremental headroom;
- **R13-B13:** static deployed observations must preserve and verify the exact executed PBC/cell, not only the request;
- **R13-B14:** public terminal/release resolution must authenticate the resource observation and release-index -> terminal-record graph;
- **R12-B11 / R13.1 runtime correction:** the static `forward_exchange` availability oracle must be removed/demoted; an actual frozen P5 publication member must execute through the real target-head mdstats exporter -> `LAMMPS_MLIAP_MACE` -> selected KOKKOS-enabled LAMMPS Python runtime -> mliappy -> actual MACE callback, producing required E/F/stress parity and clean worker completion;
- **R12-B12:** final target-machine qualification with real authenticated reference evidence, then explicit one-shot locked activation and immutable terminal close/reopen, must run through the same corrected runtime owner.

## B11 implementation authority

`P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md` is binding. In particular:

- static direct imports or `hasattr(..., "forward_exchange")` checks may be diagnostics but cannot own PASS/UNAVAILABLE for the product path;
- the actual ML-IAP data object presented to the executing MACE callback is the relevant `forward_exchange` owner;
- the worker must activate the selected KOKKOS resource mode; the verified one-GPU target resolves to effective launch arguments equivalent to `-k on g 1 -sf kk`;
- `activate_mliappy()` must run on the exact live LAMMPS instance before Python-backed ML-IAP MACE execution;
- use the existing LAMMPS worker/process boundary where practical and isolate native crashes from the main qualification/store process;
- do not call `lammps.finalize()` or `lammps_python_finalize()` from the externally owned Python lifecycle;
- abnormal worker exit/native crash is blocking runtime evidence and cannot publish successful component/B11 evidence;
- actual current-publication product execution, not construction-only evidence, closes B11.

## Revised binding implementation sequence

The B11 runtime repair is executable source work and must be completed **before** candidate freeze:

```text
R13-P1   claim-scoped/member-scoped stress capability + fail-closed reducer semantics
R13-P2   authenticated external-reference stress import/provenance + stress-required request coverage
R13-P3   attempt-wide resource-observation lineage + selected-device/scope material + bounded disk headroom
R13-P4   static deployed PBC/cell observation and parity verification
R13-P5   terminal/release/resource referential-integrity currentness closure
R13-P6   B11 KOKKOS/MACE runtime-owner correction: semantic capability, selected GPU activation, mliappy activation, process lifecycle/crash isolation
R13-P7   fresh focused + affected regression/integration, including preserved R11/R12 surfaces and B11 worker-owner tests
R13-P8   freeze new executable candidate/tree
R13-P9   actual current-publication MACE target-head execution on the supported target runtime using the frozen candidate
R13-P10  final target-machine real-reference qualification + explicit one-shot locked closure using the same corrected runtime owner
R13-P11  independent Software Design closure review
```

No executable edit is permitted between R13-P8 freeze and accepted R13-P9/P10 evidence. If real B11 execution exposes a source defect, repair it, rerun affected acceptance, and freeze a new candidate before qualification continues.

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

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked. The post-P7 storage workplan may adopt a P7 baseline only after revision-13.1 source repair, fresh affected regression/integration, real current-publication MACE target-head execution through the corrected KOKKOS/mliappy runtime owner, final target-machine real-reference qualification, one-shot locked closure, full terminal/resource/reference evidence graph close-reopen, and independent Software Design PASS.
