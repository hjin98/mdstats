# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into seven sequential implementation packages. The frozen parent V7 workplan remains the controlling scientific and architectural authority. Package amendments constrain implementation/acceptance without reopening settled science unless material evidence requires it.

## Current sequencing state

P1-P6 remain accepted/reclosed, including the revision-11 P5 final-publication decision repair and affected P6 rebind.

The revision-13.2 executable candidate reviewed by revision 13.3 is:

- executable commit: `f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7`;
- executable tree: `56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0`;
- evidence-only documentation head: `8f6a2e353cdccfaf37fb17660e55bfbc679b501d`.

**P7 revision 13.3 is the current authority and is REOPENED / NO-PASS.** Revision 13.2 genuinely removed the explicit generic runtime veto and demonstrated successful selected KOKKOS/mliappy MACE execution plus a target-machine `RELEASE_QUALIFIED` run. Those results are retained as useful historical evidence. A remaining environment/currentness ownership defect still requires executable repair, so the real B11/B12 gates must be repeated on the next frozen candidate.

### Accepted repairs to preserve

- P5 final publication ownership; no P7 ranking, committee shrinkage or fallback;
- exact target-head publication/export/ML-IAP identity;
- R12 LAMMPS bar/pressure-sign canonical stress adapter;
- R13 component/member/geometry-scoped stress capability and fail-closed applicable-stress reducers;
- authenticated external-reference stress source representation/units/sign/order/virial/canonicalization provenance;
- immutable cumulative resource-observation lineage, locked timing, selected-device resource telemetry and reserve-plus-headroom disk safety;
- exact static/dynamics per-axis PBC and static post-build cell verification;
- public terminal/release/resource/component/reference referential integrity;
- R13.2 selected KOKKOS/mliappy child-worker execution, callback evidence, process isolation, abnormal-exit blocking and no external Python finalization;
- accepted R11 publication/currentness/reference/locked semantics.

### Current blockers

1. **R13.3-B11C — diagnostic runtime still contaminates binding/currentness.** `capture_environment_fingerprint()` still executes `probe_lammps_runtime()` through `_lammps_facts()`, and the resulting generic `lammps_version`/`lammps_mliap_available` values participate in `EnvironmentFingerprint.content_digest`. A generic diagnostic flip can therefore stale the entire P7 binding. `qualify_deployment_parity()` and `execute_lammps_request()` also still call the generic in-process probe before the selected child, so a native diagnostic failure can still prevent the semantic worker from being reached. Mandatory qualification/currentness must not execute or depend on that generic probe.
2. **R13.3-B7E — selected accelerator environment identity still reads device 0.** `_accelerator_facts(device)` queries GPU 0 even for `cuda:N`; the environment binding must identify the exact selected accelerator.
3. **R13.3-B12E — final evidence record is incomplete.** The next final closure record must retain the exact reference-bundle/protocol, full component digests, member checkpoint/deployed artifact, environment/resource/predecessor, terminal/release/resource/locked identities and post-restart current resolver identities required to audit B11/B12.

## Mandatory sequence

```text
P1 neutral scientific substrate
  -> P2 target-size statistical authorities
  -> P3 candidate execution and paired-seed screen
  -> P4 atomic runtime/persistence cutover
  -> P5 post-selection CV + fresh final production + final-publication decision
  -> P6 destructive cleanup / predecessor closure
  -> P7 qualification and locked release evidence
       -> preserve accepted R11/R12/R13/R13.2 repairs
       -> R13.3 remove generic diagnostic runtime from environment/currentness
          and selected-worker mandatory paths; fix selected CUDA-device identity
       -> focused + complete affected P7 regression/integration
       -> freeze new executable candidate
       -> rerun actual current-publication selected-KOKKOS MACE parity
       -> rerun final target-machine real-reference qualification on same candidate
       -> one-shot locked closure
       -> process-restart terminal/resource/reference graph close-reopen
       -> record complete exact closure identities
       -> independent P7 PASS
  -> CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
```

The successor storage reset remains blocked until independent P7 PASS.

## Cross-package rules

- Frozen V7 science and accepted predecessor ownership remain authoritative; P7 is read-only with respect to target-size selection, CV, production training and publication membership.
- P7 qualification has pass/reject/waiting authority only for the exact frozen product and never selects a fallback product.
- Public/current qualification views must reauthenticate the exact current binding and acceptance-critical immutable descendants.
- Generic/static/default LAMMPS probes are diagnostics only. They may not veto, reinterpret or stale selected KOKKOS/MACE product evidence, and mandatory qualification must not depend on executing them.
- Selected semantic KOKKOS/mliappy MACE execution owns runtime capability evidence; actual runtime failure remains unavailable/blocking.
- Stress applicability is training/member/geometry owned. Missing selected-runtime/reference stress cannot redefine an applicable trained channel as not applicable.
- External reference stress must authenticate source representation, units, sign, ordering, volume semantics where applicable and canonicalization provenance.
- Exact per-axis periodicity and executed cell are product geometry evidence.
- Dynamics retains the frozen reference-relaxed NVT/NVE/topology/displacement safety contract.
- One-shot locked disclosure is irreversible but crash-resumable to its exact result.
- Resource observations are release evidence, not science/selection authority, and must describe the exact selected execution scope/device.
- Functional regression/integration and final target-machine production qualification are distinct gates; neither substitutes for the other.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md`
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md`
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` plus accepted closure amendments
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` plus accepted closure amendments
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` plus accepted final-publication amendments
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` plus accepted reclosure/rebind amendments
7. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` composed with revisions 2, 10-13.2 and **current revision 13.3**

## Current P7 authority

Read P7 in this precedence order:

1. frozen parent workplan;
2. accepted/reclosed predecessor authorities;
3. `P7_REVISION_13_3_IMPLEMENTATION_REVIEW_RUNTIME_IDENTITY_REOPEN_AMENDMENT.md` and `P7_REVISION_13_AUTHORITY.md`;
4. `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md` where still binding;
5. `P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md` where still binding;
6. earlier R13/R12/R11/R10/base-P7 authorities where non-conflicting;
7. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` for the storage-neutral successor boundary.

`P7_REVISION_13_AUTHORITY.md` is the current authority pointer. `P7_REVISION_13_3_REVIEW_EVIDENCE.md` records the independent NO-PASS review of the revision-13.2 candidate. `P7_REVISION_13_2_IMPLEMENTATION_EVIDENCE.md` remains useful historical execution evidence but is not final closure evidence for the next executable candidate.

P7 remains **REOPENED / NO-PASS** until the R13.3 identity/control-flow repair, fresh affected regression, new freeze, repeated real B11/B12/locked close-reopen gates, complete exact evidence recording and independent final review all pass.
