---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.2
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.3
status: reopened
reviewed_implementation_commit: f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7
reviewed_implementation_tree: 56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0
post_qualification_documentation_head: 8f6a2e353cdccfaf37fb17660e55bfbc679b501d
review_verdict: NO-PASS
amended_date: 2026-08-31
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
scope: preserve accepted R13/R13.2 qualification repairs; remove remaining generic-runtime diagnostic contamination from environment/currentness and mandatory control flow; correct selected-accelerator environment identity; then re-freeze and repeat final real B11/B12 closure with complete exact evidence identities
precedence: revision 13.3 supersedes revision 13.2 only for the reviewed candidate disposition, runtime/environment identity ownership, evidence-completeness requirement, and final closure sequence; all non-conflicting frozen-parent, R13.2, R13.1, R13, R12, R11, R10, and base-P7 requirements remain binding
---

# P7 revision 13.3 — implementation review runtime/environment identity reopen amendment

## Objective and protected concerns

Independent Software Design review of the revision-13.2 candidate at executable commit
`f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7`, tree
`56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0`, remains **NO-PASS**.

Revision 13.2 genuinely removes the explicit `supports_deployed_execution` veto, decouples deployment stress applicability/reuse from that boolean, and demonstrates successful selected KOKKOS/mliappy MACE execution on the target machine. Those repairs are preserved.

One acceptance-critical ownership defect remains: the supposedly diagnostic generic/default LAMMPS probe still executes inside mandatory qualification construction/execution and still contributes claim-relevant environment identity. A generic diagnostic result can therefore change the entire P7 binding/currentness, and an in-process native failure can still prevent the selected isolated semantic worker from being reached. This directly violates the revision-13.2 requirement that diagnostic generic-probe state must not veto, reinterpret, or stale selected-runtime product evidence.

A second closely related environment-identity defect remains: selected accelerator identity is not exact for `cuda:N` because the environment fingerprint queries GPU device 0 regardless of the selected device. The target-machine run used GPU 0 and is therefore not contradicted by this defect, but the accepted P7 environment contract is not correct for supported nonzero selected devices.

The revision-13.2 target-machine evidence is retained as useful historical execution evidence. It cannot close P7 after an executable repair is required, and its committed summary also does not record all exact identities required by R13.2-P6 for final independent closure.

## Engineering envelope and preserved design

Preserve without redesign unless contradictory evidence appears:

- frozen V7 target-size/CV/production/publication science and accepted P1-P6 architecture;
- R11 publication/currentness/reference/locked owners and no downstream fallback/committee shrinkage;
- R12 LAMMPS bar -> canonical tensile-positive stress adapter and exact target-head binding;
- R13 claim/member/geometry-scoped stress capability, fail-closed missing applicable stress, and authenticated external stress source provenance;
- R13 cumulative resource-observation lineage, disk reserve plus bounded write headroom, static/dynamics exact PBC/cell evidence, and terminal/release/resource referential integrity;
- R13.2 selected child-worker mechanics: authenticated KOKKOS launch, mliappy/MACE callback execution, process isolation, structured callback evidence, abnormal-exit blocking, and no external Python finalization;
- the distinction between bounded functional regression and the mandatory final target-machine qualification gate.

No storage-successor work is pulled into this repair.

## R13.3-B11C — generic diagnostics still contaminate binding and mandatory execution

### Confirmed production path

The reviewed candidate still has all of the following:

1. `capture_environment_fingerprint()` calls `_lammps_facts()`.
2. `_lammps_facts()` calls `probe_lammps_runtime()`.
3. `probe_lammps_runtime()` starts a generic/default LAMMPS instance in the parent Python process and calls `activate_mliappy()` there.
4. `EnvironmentFingerprint.content_digest` retains `lammps_version` and `lammps_mliap_available`; therefore a generic probe result flip changes the environment digest, the P7 binding, attempt identity, and public currentness even when executable/product/selected KOKKOS runtime contract are unchanged.
5. `qualify_deployment_parity()` still calls `probe_lammps_runtime()` before member execution solely to populate diagnostic payload.
6. `execute_lammps_request()` still calls `probe_lammps_runtime()` before spawning the isolated selected worker and records its digest into worker evidence.

The explicit boolean veto is gone, but the generic probe remains acceptance-critical through identity and control flow. A Python `BaseException`, hang, or native crash in that diagnostic path can still prevent the semantic child execution; a clean but different generic probe outcome can stale otherwise valid release evidence through `EnvironmentFingerprint`.

### Required end state

1. **No generic/default runtime execution in mandatory pre-run identity.** Building a `QualificationSession` and its `EnvironmentFingerprint` must not start a generic LAMMPS instance merely to determine currentness.
2. **Stable pre-run environment identity.** Bind stable installed/runtime-selection facts that can be obtained without executing a non-selected simulation instance. At minimum, preserve Python/package/MACE/ASE/Torch/CUDA/driver/device/default-dtype identity and include a stable LAMMPS package/build identity when available without semantic execution. Do not bind a volatile generic-startup success/failure bit as `lammps_mliap_available` currentness material.
3. **Selected worker owns runtime capability evidence.** Actual ML-IAP/KOKKOS/mliappy/MACE availability, LAMMPS runtime version/build facts that require execution, callback success, selected launch arguments, and stress observation availability belong to the selected isolated worker/component evidence. They may be recorded diagnostically without becoming a pre-run generic veto.
4. **No mandatory generic probe before selected execution.** `qualify_deployment_parity()` and `execute_lammps_request()` must be able to execute with `probe_lammps_runtime()` unavailable, raising, or absent. If generic diagnostics are retained, run them only through a best-effort/isolated diagnostic owner that cannot alter binding, component input identity, verdict, or ability to reach the semantic worker.
5. **No diagnostic-probe currentness coupling.** A generic diagnostic result change alone, with unchanged executable source, installed stable runtime/package identity, selected device/resource contract, publication/product, specification, and actual selected runtime behavior, must leave `EnvironmentFingerprint.content_digest`, `QualificationInputBinding.content_digest`, and current terminal/release resolution unchanged.
6. Preserve all accepted R13.2 selected-worker failure behavior: actual selected worker/callback failure remains typed unavailable/blocking and cannot publish successful evidence.

### Acceptance evidence

Add owner-level acceptance that would fail on the reviewed candidate:

- patch `probe_lammps_runtime()` to raise if called, then prove `capture_environment_fingerprint()` / `build_qualification_session()` can still build the same binding from stable environment facts;
- under the same no-generic-probe condition, prove deployment parity reaches the selected semantic evaluator/worker and can pass when exact E/F/applicable stress are returned;
- prove two otherwise identical session builds with opposite generic diagnostic results have identical environment and qualification binding digests;
- publish a bounded terminal/release record, flip only the generic diagnostic result, rebuild current context, and prove public verdict/release resolution remains current;
- prove actual selected worker/callback failure still blocks and cannot be converted into diagnostic success;
- preserve the existing R13.2 one-GPU `-k on g 1 -sf kk`, stress request/fail-closed, callback evidence, and crash-isolation tests.

## R13.3-B7E — selected accelerator environment identity still queries device zero

### Confirmed defect

`_accelerator_facts(device)` checks whether the requested device is CUDA, but calls `torch.cuda.get_device_properties(0)` unconditionally. `EnvironmentFingerprint.content_digest` includes `accelerator_model` and `device`, so `device="cuda:1"` can be paired with GPU 0's model. The resource-observation owner correctly learned selected-device telemetry in R13, but the pre-run environment identity remains inconsistent with that accepted execution scope.

### Required end state

- Resolve the exact CUDA device index from the accepted `device`/resource selection and query that device's properties; never silently fall back to device zero for `cuda:N`.
- Validate out-of-range/invalid selected-device identities fail clearly rather than producing a mismatched fingerprint.
- Keep volatile free-memory observations out of environment identity; selected accelerator model/runtime/driver/device identity remains stable claim material.
- Keep resource-observation selected-device telemetry consistent with the environment/resource-scope identities.

### Acceptance evidence

Use a two-device fake/controlled CUDA surface where device 0 and device 1 have distinct models. Prove `capture_environment_fingerprint(device="cuda:1")` records device 1, its digest differs appropriately from `cuda:0`, and no device-0 properties are queried for the cuda:1 case. Preserve the existing R13 resource-observation selected-device test.

## R13.3-B12E — final closure evidence record is incomplete

The revision-13.2 implementation evidence records the frozen candidate, target GPU/runtime summary, qualification record digest, release-index digest, publication digest, resource-observation digest, component statuses, and only shortened component digests. It does **not** record the complete exact identity set R13.2-P6 explicitly required for independent final closure, including at least the authenticated external reference bundle digest/protocol identity, full component evidence digests, current publication member checkpoint SHA, deployed artifact SHA, environment digest, resource-scope digest, predecessor-reclosure identity, and exact close/reopen resolver result identities.

Do not create a second evidence subsystem. After the new candidate is frozen and the real gates rerun, one concise durable implementation/qualification evidence record is sufficient if it records the exact identities needed to interpret and independently audit the claim.

Required final record:

- executable commit/tree and executable source identity used by both B11 and B12;
- current P5 publication digest, exact member ID/checkpoint SHA/target head, and deployed artifact SHA;
- environment digest, resource-scope digest, predecessor-reclosure digest/tree identity, and effective selected worker launch arguments;
- exact external-reference protocol identity and immutable reference-bundle digest, plus confirmation that required stress observations carry authenticated source provenance;
- exact full component evidence digests and statuses;
- exact terminal qualification-record, release-index, cumulative resource-observation, and locked-activation/result digests;
- the post-restart current verdict/release identities showing the same graph reauthenticated;
- focused/affected regression command/result and target-machine B11/B12 execution result.

## Implementation authority

### Frozen

- Generic/default runtime diagnostics are non-authoritative and cannot alter selected product availability, scientific stress applicability, binding/currentness, or access to the semantic worker.
- Stable environment identity must identify the actually selected accelerator/runtime installation without executing a generic simulation as an identity oracle.
- Actual selected KOKKOS/mliappy MACE execution remains the runtime semantic owner.
- All R11/R12/R13/R13.2 accepted repairs listed above remain preserved.
- Final B11/B12 evidence must correspond to one executable candidate after all executable repairs.

### Delegated

- Exact representation of stable non-executing LAMMPS installation/build identity, provided it is deterministic, claim-relevant, and does not reintroduce generic runtime startup as currentness authority.
- Whether optional generic diagnostics are removed entirely from qualification or retained behind an isolated/best-effort diagnostic API.
- Formatting of the final concise evidence record.

### Reopen only on evidence

Reopen this design only if stable pre-run runtime identity cannot be established without executing the selected semantic runtime, or if the selected worker cannot expose the runtime facts required to interpret qualification evidence. In that case reopen only environment/runtime identity ownership; do not reopen accepted qualification science.

## Affected surface and task-specific acceptance

Expected affected production surface:

- `mdstats/training_data/qualification/identity.py`;
- `mdstats/training_data/qualification/runtime_capability.py`;
- `mdstats/training_data/qualification/deployment.py` where diagnostic probe payload remains mandatory;
- P7 session/currentness tests and R13.2 acceptance tests;
- possibly environment/binding tests if those owners live elsewhere.

Re-derive the final affected surface after implementation. Run focused R13.3 tests plus the complete affected `tests/test_mlff_p7_*.py` regression. Broaden only if the implementation changes shared identity/resource owners outside P7.

Production qualification is **required** after the executable repair because P7 closure claims the real selected runtime and durable final release graph.

## Implementation sequence

```text
R13.3-P1  remove generic-runtime execution/result from mandatory environment/currentness
          and selected-worker pre-control paths; fix exact selected accelerator identity
R13.3-P2  focused owner tests + complete affected P7 regression/integration
R13.3-P3  freeze a new executable candidate commit/tree
R13.3-P4  rerun actual current-publication selected-KOKKOS MACE E/F/applicable-stress parity
R13.3-P5  rerun final target-machine real-reference qualification + one-shot locked closure
          on the same candidate
R13.3-P6  close/reopen the terminal/release/resource/reference graph after process restart
          and record the complete exact evidence identities above
R13.3-P7  independent Software Design closure review
```

No executable edit is permitted between R13.3-P3 and accepted R13.3-P4/P5/P6. If the target run exposes an executable defect, repair it, rerun affected regression, and freeze a new candidate before repeating the affected real gates.

## Handoff closure

The current supplied P7 authority set plus this amendment preserves all still-binding task-specific semantics without relying on private conversation history. The new implementation has one narrow goal: make environment/currentness and mandatory control flow truly independent of the generic diagnostic probe, make selected-device identity exact, then re-establish the already-demonstrated real release gates on the resulting final candidate with complete auditable identities.

Until independent review passes that candidate, P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
