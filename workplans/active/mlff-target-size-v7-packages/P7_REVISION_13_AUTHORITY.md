---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13.3
status: reopened
reviewed_implementation_commit: f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7
reviewed_implementation_tree: 56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0
post_qualification_documentation_head: 8f6a2e353cdccfaf37fb17660e55bfbc679b501d
review_verdict: NO-PASS
current_amendment: P7_REVISION_13_3_IMPLEMENTATION_REVIEW_RUNTIME_IDENTITY_REOPEN_AMENDMENT.md
current_review_evidence: P7_REVISION_13_3_REVIEW_EVIDENCE.md
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13.3 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict.

Independent Software Design review of the revision-13.2 executable candidate
`f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7`, tree
`56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0`, is **NO-PASS**. The later head
`8f6a2e353cdccfaf37fb17660e55bfbc679b501d` is evidence-only and does not change importable mdstats source.

Revision 13.2 genuinely removed the explicit generic-runtime veto and demonstrated that the selected KOKKOS/mliappy MACE path can execute on the target machine. Revision 13.3 does not reopen qualification science or the accepted R11-R13 repairs. It corrects one remaining ownership/currentness defect in runtime/environment identity, one selected-device identity defect, and the final evidence-recording gap.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan;
2. accepted/reclosed predecessor P1-P6 authorities;
3. `P7_REVISION_13_3_IMPLEMENTATION_REVIEW_RUNTIME_IDENTITY_REOPEN_AMENDMENT.md` — current residual source/evidence/closure authority;
4. `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md` — binding where revision 13.3 preserves rather than supersedes it;
5. `P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md` — selected semantic runtime/lifecycle authority;
6. `P7_REVISION_13_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` and later R12/R11/R10/base-P7 authorities where still non-conflicting;
7. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor boundary.

Historical implementation/review records remain evidence only. `P7_REVISION_13_2_IMPLEMENTATION_EVIDENCE.md` is useful target-machine execution evidence for the reviewed candidate, but it cannot close the next executable candidate after revision-13.3 source repair.

## Accepted surfaces — preserve

Do not redesign these absent contradictory evidence:

- P5 owns the exact final publication/member decision; P7 never ranks/shrinks/falls back among members.
- Canonical target-head identity is mandatory through publication, export, ML-IAP construction and runtime execution.
- LAMMPS `units metal` pressure is adapted from bar/positive-compression to canonical tensile-positive stress only by the fixed source adapter.
- Stress capability is exact per component/member/claim/geometry; applicable trained stress cannot pass when selected-runtime/reference evidence is missing; external reference stress authenticates raw representation, units, sign, ordering, virial-volume semantics where applicable, and canonicalization provenance.
- Static/dynamics execution preserves exact three-axis PBC and static post-build cell observation.
- Resource evidence is immutable, cumulative across resume, selected-device aware, locked-timing aware, and enforces reserve plus bounded write headroom.
- Public terminal/release exposure authenticates the release-index -> terminal-record -> component/resource/reference graph.
- Selected KOKKOS/mliappy MACE child-worker execution, process isolation, structured callback evidence, abnormal-exit blocking, and no externally owned Python finalization remain the runtime semantic owner.
- One-shot locked disclosure/restart semantics and all accepted R11/R12 currentness/reference repairs remain binding.

## Current blockers

### R13.3-B11C — generic diagnostic runtime still contaminates binding/currentness

The candidate still builds `EnvironmentFingerprint` through `_lammps_facts() -> probe_lammps_runtime()`. That probe starts a generic/default LAMMPS instance in the parent process, while `EnvironmentFingerprint.content_digest` includes its `lammps_version` and `lammps_mliap_available` results. Therefore a generic diagnostic outcome can change the full P7 binding/currentness even when executable/product/selected KOKKOS runtime contract are unchanged.

The same generic probe is still called before member execution in `qualify_deployment_parity()` and before the isolated child in `execute_lammps_request()`. It no longer has an explicit boolean veto, but a `BaseException`, hang or native crash in the diagnostic path can still prevent the semantic worker from being reached.

Required end state: mandatory session construction/currentness and selected product execution must not execute or depend on a generic/default simulation probe. Stable pre-run environment identity must come from non-executing installed/runtime-selection facts; actual ML-IAP/KOKKOS/mliappy/runtime-version facts that require execution belong to selected isolated worker evidence. A diagnostic-probe flip alone must not alter environment/binding digests or public currentness.

### R13.3-B7E — selected accelerator environment identity still queries GPU 0

`_accelerator_facts(device)` queries `torch.cuda.get_device_properties(0)` regardless of a selected `cuda:N`. The environment binding can therefore pair `device="cuda:1"` with GPU 0's model. Query the exact selected device and fail clearly on invalid/out-of-range selections. Preserve volatile-memory exclusion and the already-correct resource-observation selected-device telemetry.

### R13.3-B12E — final closure evidence identities are incomplete

The revision-13.2 target evidence records useful full terminal/release/publication/resource digests but omits the complete exact identity chain required by R13.2-P6: reference-bundle digest/protocol identity, full component digests, exact member checkpoint SHA, deployed artifact SHA, environment/resource-scope/predecessor identities, and exact post-restart current resolver identities.

After the executable repair, rerun B11/B12 on the new frozen candidate and record one concise exact closure record containing those identities plus the affected-regression and target-run results.

## Binding implementation sequence

```text
R13.3-P1  remove generic/default runtime execution/result from mandatory environment/currentness
          and selected-worker pre-control paths; fix exact selected CUDA-device identity
R13.3-P2  focused owner tests + complete affected tests/test_mlff_p7_*.py regression/integration
R13.3-P3  freeze a new executable candidate commit/tree
R13.3-P4  rerun actual current-publication selected-KOKKOS MACE E/F/applicable-stress parity
R13.3-P5  rerun final target-machine real-reference qualification + one-shot locked closure
          on the same candidate
R13.3-P6  close/reopen the complete graph after process restart and record exact evidence identities
R13.3-P7  independent Software Design closure review
```

No executable edit is permitted between R13.3-P3 and accepted P4/P5/P6 evidence. A source defect found by target execution requires repair, fresh affected regression, a new freeze, and repetition of the affected real gates.

## Closure gate

P7 may receive PASS only when one final executable candidate satisfies all of the following:

1. mandatory environment/currentness and selected-runtime execution are independent of generic/default diagnostic probe outcomes and failures;
2. selected accelerator identity is exact for the accepted CUDA device;
3. accepted R11/R12/R13/R13.2 surfaces remain green under fresh affected regression/integration;
4. exact current durable P5 publication member execution succeeds through the selected KOKKOS/mliappy MACE owner with E/F/applicable-stress parity and clean worker completion;
5. final target-machine real-reference qualification succeeds on the same candidate;
6. one-shot locked activation/result and process-restart close/reopen succeed;
7. the exact terminal/release/resource/reference/component/publication/product/environment identities are durably recorded and reauthenticate current;
8. independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
