---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.2
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.2
status: reopened
reviewed_implementation_commit: cc098c18b39bbfdc65be6d5266fc2582d9bc9e01
reviewed_implementation_tree: 918d7670a6441a5431c95313c452499387b5ec60
review_verdict: NO-PASS
amended_date: 2026-08-31
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
scope: P7A3 implementation review; preserve accepted R13 source repairs, remove the remaining generic runtime preflight veto, then execute the mandatory real B11/B12 release gates
precedence: revision 13.2 supersedes revision 13.1 only for the reviewed P7A3 disposition, residual B11 implementation defect, acceptance tests, and closure sequence; all non-conflicting frozen-parent, R13.1, R13, R12, R11, R10, and base-P7 requirements remain binding
---

# P7 revision 13.2 — P7A3 implementation review runtime-gate reopen amendment

## 1. Verdict and scope

Independent Software Design review of P7A3 at executable commit
`cc098c18b39bbfdc65be6d5266fc2582d9bc9e01`, tree
`918d7670a6441a5431c95313c452499387b5ec60`, is **NO-PASS**.

The implementation materially closes most of revision 13. The remaining source defect is narrow but directly violates the revision-13.1 B11 authority: a generic, non-selected LAMMPS preflight can still veto or reinterpret deployment execution before the exact selected KOKKOS/MACE worker is attempted. The mandatory real current-publication B11 execution and final B12 target-machine qualification also remain unexecuted for this candidate.

This amendment does not reopen target-size science, CV, production training, publication membership, calibration science, locked-test science, or the accepted P1-P6 predecessor architecture.

## 2. Accepted P7A3 repairs to preserve

The following revision-13 surfaces are accepted as source-closed by this review and MUST NOT be redesigned absent contradictory implementation evidence:

### 2.1 R13-B9A / R13-B9B — stress ownership and external provenance

P7A3 now provides:

- component/member/claim/geometry-scoped immutable stress capability decisions;
- per-geometry periodic/model/reference availability rather than one session-wide decision;
- component-local stress policy and explicit committee-member ownership;
- capability-set identity in deployment/physical component inputs before completed-evidence reuse;
- fail-closed deployment and physical reducers for an applicable trained stress channel whose deployed/reference observation is unavailable;
- exact required-stress geometry identities in the physical reference request;
- authenticated external stress source representation, units, sign, ordering, virial-volume semantics where applicable, raw source value, canonicalization owner, and replayed canonical tensor.

Preserve these owners. Revision 13.2 changes only how deployment **runtime availability** is established; it does not make scientific stress applicability depend on a generic runtime probe.

### 2.2 R13-B7 — resource evidence and disk safety

P7A3 now provides an immutable resumable resource-observation predecessor chain, cumulative attempt timing/samples, explicit locked-test timing, stable resource-scope material, selected-device accelerator telemetry, and reserve-plus-bounded-headroom admission. Public currentness traverses and authenticates the predecessor chain. Preserve this implementation.

### 2.3 R13-B13 — static PBC/cell observation

The real worker now returns post-build cell and exact three-axis PBC, and the static adapter validates both against the authenticated requested geometry. Preserve the existing exact static/dynamics per-axis boundary behavior.

### 2.4 R13-B14 — terminal/release referential integrity

Public terminal/release resolution now dereferences and authenticates resource observations and the release-index -> single terminal-record authority, including binding/attempt/resource/predecessor/locked/component agreement. Preserve this closure.

### 2.5 Accepted B11 worker mechanics

The selected worker implementation itself is directionally correct and must be reused:

- KOKKOS arguments are carried into the real child LAMMPS instance;
- `activate_mliappy()` runs on that exact live instance before Python ML-IAP MACE execution;
- the real unified MACE artifact is loaded and `run 0`/the dynamics run enters the pair callback;
- structured runtime evidence is returned only after successful callback execution;
- worker failure/native abnormal termination cannot publish successful product evidence;
- `instance.close()` owns instance shutdown; the worker does not call `lammps.finalize()` or `lammps_python_finalize()` from the externally owned Python lifecycle.

## 3. Residual blockers

| ID | Blocking finding | Consequence |
|---|---|---|
| R13.2-B11A | generic non-KOKKOS LAMMPS preflight still owns a veto and deployment-stress runtime fact before the selected semantic KOKKOS/MACE worker executes | repair source and focused acceptance before candidate freeze |
| R13.2-B11B | no accepted execution of the exact current durable P5 publication member through the final selected KOKKOS/MACE deployment-parity owner | execute on the supported target runtime after a new freeze |
| R13.2-B12 | no accepted final target-machine real-reference qualification + one-shot locked terminal close/reopen for the same frozen candidate | execute only after B11A/B11B close |

Any one independently blocks P7 PASS.

## 4. R13.2-B11A — remove the generic preflight as semantic authority

### 4.1 Confirmed source drift

P7A3 correctly demotes the static `forward_exchange` diagnostic, but a broader generic preflight remains authoritative:

1. `probe_lammps_runtime()` creates a separate LAMMPS instance without the selected qualification KOKKOS launch contract and observes generic ML-IAP/mliappy startup.
2. `_require_supported_runtime()` converts that generic result into an execution gate.
3. `execute_lammps_request()` invokes `_require_supported_runtime()` **before** starting the exact selected worker.
4. `qualify_deployment_parity()` independently gates the component on `probe.supports_deployed_execution` before member product execution.
5. `QualificationSession.stress_capability()` and `_stored_capability_digest()` use the same generic probe result as the deployment stress-runtime fact and component-reuse discriminator.

Therefore a generic CPU/default LAMMPS startup or mliappy failure can prevent the exact `-k on g N -sf kk` product worker from running. It can also mark deployment stress unavailable before the selected worker has been asked to report stress. This contradicts revision 13.1, which makes the **actual selected product execution** the B11 semantic owner.

### 4.2 Required end state

Implement the following without creating a second deployment runtime:

1. **Generic probe is diagnostic only.** `probe_lammps_runtime()` may remain for environment reporting, troubleshooting, version/module observations, and optional early user diagnostics. Its success/failure may not itself establish product PASS/UNAVAILABLE and may not suppress the selected worker.
2. **No generic veto in `execute_lammps_request()`.** For a production product request, the parent must attempt the exact selected child worker using the authenticated resource/runtime launch contract. If Python LAMMPS, ML-IAP, KOKKOS, mliappy, the MACE callback, or the selected device is genuinely unavailable, the child execution itself fails and the parent records typed runtime-unavailable/crash evidence.
3. **No component pre-gate.** `qualify_deployment_parity()` must not reject/abort solely because generic `probe.supports_deployed_execution` is false. It may retain the generic probe in diagnostic payload, but member evaluation must reach the selected semantic worker.
4. **Scientific stress applicability remains runtime-independent.** Training objective + exact member model capability + exact geometry periodicity own applicability. A generic runtime probe cannot turn an applicable trained stress channel into `not_applicable` or prevent the stress request.
5. **Selected semantic execution owns stress evidence availability.** When stress is scientifically applicable, request stress from the real selected worker. Missing/invalid stress from that execution is unavailable/blocking or rejection under the frozen component contract; it never becomes a pass because the generic probe predicted no stress.
6. **Reuse/currentness must not depend on a non-authoritative generic startup result.** Deployment component identity may bind the already accepted executable/environment/resource/adapter contract and exact claim-scoped scientific capability. A flip in a diagnostic generic probe alone must not reinterpret or stale evidence. A changed executable, environment/resource binding, product artifact, selected runtime contract, or actual semantic observation remains material through existing owners.
7. Preserve the selected KOKKOS/mliappy worker, subprocess isolation, target-head validation, static PBC/cell verification, stress source conversion, resource owners, and no-fallback semantics already accepted above.

### 4.3 Mandatory focused acceptance

Add owner-level tests that would fail on P7A3:

- force `probe_lammps_runtime()` / its generic startup to report unavailable while a controlled selected semantic worker succeeds; prove `execute_lammps_request()` still starts the worker and accepts the structured callback result;
- under the same generic-failure condition, prove `qualify_deployment_parity()` reaches member evaluation instead of raising before the worker;
- applicable trained stress + generic probe failure + selected worker returns correct stress -> stress is requested and compared and may pass;
- applicable trained stress + selected worker omits stress -> component cannot pass;
- actual selected MACE callback failure (including missing `forward_exchange`) remains typed unavailable/blocking and cannot publish successful component evidence;
- a diagnostic generic-probe result flip, with unchanged executable/environment/resource/product/selected-runtime contract, does not by itself change the deployment component-input identity or suppress reuse;
- one-GPU authenticated target allocation still resolves to effective `-k on g 1 -sf kk`; CPU-only and other supported allocations remain correctly derived rather than hard-coded;
- preserved R13 stress-provenance, resource, PBC, release-integrity, R12 pressure-sign, and R11 publication/currentness tests remain green.

## 5. R13.2-B11B — execute the actual current publication through the final owner

The existing bounded/runtime acceptance code is not sufficient to close B11 merely by constructing or executing a synthetic fixture member. After B11A is repaired and a new executable candidate is frozen, B11 must use the exact **current durable P5 publication decision/member bytes** consumed by P7.

Required semantic chain:

```text
current authenticated P5 publication decision
 -> exact selected publication member checkpoint bytes + SHA
 -> real mdstats target-head deployment exporter
 -> real LAMMPS_MLIAP_MACE canonical target-head artifact
 -> exact selected qualification resource scope
 -> KOKKOS-enabled LAMMPS child (one-GPU target => effective -k on g 1 -sf kk)
 -> activate_mliappy on that exact instance
 -> actual MACE pair callback/message passing
 -> observed E/F and applicable stress + exact cell/PBC
 -> frozen deployment-parity comparison
 -> clean structured worker completion
```

Acceptance requires all of the following:

- the durable P7 session resolves the current P5/P6 identities; do not manufacture a separate publication solely for B11 closure;
- artifact SHA, member checkpoint SHA, target head, executable/environment/resource identities and effective launch arguments are retained in immutable evidence;
- energy and forces satisfy the frozen deployment-parity tolerances against the in-framework exact member;
- every scientifically applicable stress observation is requested and satisfies the repaired stress contract;
- the worker returns exact executed PBC/cell and clean exit status;
- no generic preflight can skip or replace this execution;
- a runtime failure is unavailable/blocking, not scientific fallback or committee shrinkage.

A CI/hardware skip may remain truthful test behavior on machines without the target runtime, but it is **not P7 PASS evidence**.

## 6. R13.2-B12 — final target-machine real-reference and locked release gate

After B11B succeeds on the frozen candidate, run the complete final qualification on the target machine using that same executable/runtime owner. Required closure evidence is:

- exact frozen repaired executable commit/tree used for B11B;
- exact current P5 publication/member bytes and current predecessor reclosure;
- explicit real external-reference protocol and immutable authenticated reference bundle, including raw/source-declared stress provenance for every required stress geometry;
- successful required nonlocked deployment, physical, relaxation, dynamics, and calibration components under the frozen specification;
- selected KOKKOS/mliappy MACE runtime used by deployment/dynamics, not a separate ad-hoc target script;
- complete cumulative attempt resource observation including target-machine CPU/GPU/disk/timing facts;
- explicit one-shot locked activation only after nonlocked success;
- successful locked result and terminal `ProductionQualificationRecord`;
- `ReleaseEvidenceIndex` that authenticates that terminal record and all component/resource/reference descendants;
- process close/reopen followed by successful current verdict/release resolution from durable state;
- exact terminal/index/resource/reference/component digests recorded with the final executable commit/tree.

No executable edit is permitted between candidate freeze and accepted B11B/B12 evidence. If the real run exposes another source defect: fix it, rerun affected regression/integration, freeze a new candidate, and repeat the affected real gates.

## 7. Revised binding implementation order

Revision 13.2 supersedes the residual sequence after review of P7A3:

```text
R13.2-P1  remove/demote generic runtime preflight veto and generic-probe stress/currentness coupling
R13.2-P2  run fresh focused + complete affected R11/R12/R13 regression/integration
R13.2-P3  freeze a new executable candidate commit/tree
R13.2-P4  run actual current-publication selected-KOKKOS MACE E/F/applicable-stress parity
R13.2-P5  run final target-machine real-reference qualification + one-shot locked closure on the same candidate
R13.2-P6  close/reopen the immutable terminal/release/resource/reference graph and record exact evidence identities
R13.2-P7  independent Software Design closure review
```

## 8. Closure gate

P7 may receive PASS only when one final executable candidate satisfies all of these:

1. R13.2-B11A is source- and test-closed; no generic preflight owns selected product availability or stress applicability/evidence.
2. Accepted P7A3 R13-B9A/B9B/B7/B13/B14 repairs remain intact under fresh affected regression/integration.
3. Actual current durable P5 publication member execution succeeds through the selected KOKKOS/mliappy MACE owner with E/F/applicable-stress parity and clean worker completion.
4. Final target-machine real-reference qualification succeeds on the same frozen candidate.
5. One-shot locked activation/result succeeds and remains crash/reopen safe.
6. Terminal record, release index, cumulative resource observations, component evidence, publication/product identities and external-reference descendants all reauthenticate current after process restart.
7. Independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
