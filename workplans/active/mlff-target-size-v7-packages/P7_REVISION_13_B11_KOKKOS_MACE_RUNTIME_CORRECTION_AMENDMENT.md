---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13-B11-KOKKOS-RUNTIME
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.1
status: active
amended_date: 2026-08-31
scope: R12-B11 runtime capability/execution owner and dependent implementation ordering only
precedence: supersedes the runtime-unavailability premise and B11 implementation/acceptance wording in P7 revision 13; all non-conflicting revision-13 obligations remain binding
---

# P7 revision 13.1 — B11 KOKKOS/MACE runtime correction amendment

## 1. Reason for correction

Target-machine diagnostics invalidate the revision-13 assumption that the available LAMMPS environment is intrinsically incapable of MACE execution because a statically inspected ML-IAP Python data class lacks `forward_exchange`.

On the exact Python environment intended for mdstats qualification, the operator verified:

```text
LAMMPS Python version: 20250910
pair style mliap: available
KOKKOS package: available
KOKKOS CUDA startup with -k on g 1 -sf kk: successful
lammps.mliap.activate_mliappy(lmp): successful
LAMMPS close + process-owned KOKKOS/MPI native finalization: successful
```

Two additional observations constrain the implementation:

- importing `mliap_unified_couple` or `mliap_unified_couple_kokkos` as ordinary top-level Python modules is not a valid capability oracle for the active ML-IAP/KOKKOS runtime;
- calling `lammps.finalize()` from the externally owned Python interpreter is unsafe for this path because it also invokes LAMMPS Python finalization; the observed run reached `Py_FinalizeEx` and segfaulted. The qualification worker must not destroy its owning Python interpreter.

These diagnostics are **preflight evidence only**. They do not close R12-B11. B11 closes only when the actual frozen publication product executes through the real runtime owner.

## 2. Frozen B11 design correction

### 2.1 Semantic owner, not static introspection

The authoritative capability test for R12-B11 is the bounded real MACE product execution itself.

Static checks such as these are diagnostic/preflight only and may not own PASS/UNAVAILABLE:

- importing `mliap_unified_couple*` directly;
- `hasattr(..., "forward_exchange")` on a statically imported class;
- `has_package("KOKKOS")`;
- `has_style("pair", "mliap")`;
- successful `activate_mliappy()` alone.

Remove or demote any current `supports_mace_product_execution` / equivalent decision that declares the product path unavailable solely because a statically imported ML-IAP class lacks `forward_exchange`. In particular, a false static result may not skip the required B11 semantic execution.

For a multilayer MACE model, `forward_exchange` capability is established by the **actual ML-IAP data object presented to the real MACE callback during execution**. If that actual callback fails because the active data object lacks the required exchange contract, that is authoritative runtime-unavailable/blocking evidence.

### 2.2 Exact GPU KOKKOS startup contract

The real product worker must initialize the same LAMMPS Python/shared-library runtime used for qualification and must activate the selected KOKKOS execution mode before ML-IAP product construction/execution.

For the verified single-GPU target allocation, the required effective launch is equivalent to:

```text
-k on g 1 -sf kk
```

Do not hard-code one GPU as a universal product constant. The worker must derive the requested GPU count/device visibility from the existing authenticated resource allocation/device policy. The one-GPU target-machine qualification must resolve to the verified one-GPU KOKKOS invocation.

The worker must call:

```python
lammps.mliap.activate_mliappy(lmp)
```

on the **same live LAMMPS instance** before configuring/executing the Python-backed ML-IAP MACE model.

Failure to initialize the selected KOKKOS mode, activate mliappy, or create the actual MACE product path is typed runtime-unavailable/blocking evidence. It is not a scientific model rejection and must not alter publication membership.

### 2.3 Required real B11 execution

B11 closure must execute this exact semantic chain:

```text
CURRENT frozen P5 publication decision
 -> authenticated bytes of an actual selected publication member
 -> real mdstats mace_deployment target-head exporter
 -> real LAMMPS_MLIAP_MACE builder
 -> canonical target-head identity (including built.model.head == 1 where that remains the frozen invariant)
 -> actual KOKKOS-enabled LAMMPS Python instance
 -> activate_mliappy on that instance
 -> actual bounded LAMMPS evaluation that enters the MACE ML-IAP callback
 -> real neighbor/message-passing path, including forward_exchange where required by the model
 -> observed energy + forces + stress when the repaired claim-scoped stress contract says stress is applicable
 -> parity evaluation under the frozen tolerances/oracle
```

Construction-only evidence is insufficient. `run 0` or an equivalent bounded evaluation is acceptable only if it actually executes the real pair callback and produces the required observations.

No monkey patch, analytic ML-IAP substitute, emulated `forward_exchange`, fake model, or test-only replacement of the exporter/builder/runtime may establish B11.

### 2.4 Worker/process ownership and shutdown

Run the KOKKOS/MACE product path in a disposable qualification worker subprocess using the existing LAMMPS worker boundary where practical. Do not create a second independent deployment implementation merely for B11.

The worker owns the native runtime for its lifetime:

```text
worker starts
 -> select/activate assigned KOKKOS GPU execution mode
 -> create LAMMPS instance
 -> activate mliappy
 -> execute all worker-owned bounded product evaluations
 -> close the LAMMPS instance
 -> finalize only process-owned native KOKKOS/MPI state once at terminal worker shutdown when required by the chosen worker lifecycle
 -> worker exits
```

Frozen lifecycle rules:

1. Do **not** call `lammps.finalize()` from this externally owned Python interpreter path.
2. Do **not** call `lammps_python_finalize()` from the worker's owning Python interpreter.
3. Native KOKKOS/MPI finalization, when explicitly performed, occurs once at terminal worker shutdown after the LAMMPS instance is closed; no later KOKKOS LAMMPS instance may be created in that process.
4. A worker abnormal exit, native crash, CUDA/KOKKOS teardown failure, or missing structured result is blocking runtime evidence. The parent must not publish successful component/B11 evidence from a crashed worker.
5. Process isolation must prevent a native runtime crash from corrupting the main qualification/session process or immutable evidence store.

Exact internal cleanup mechanics are delegated if they preserve these ownership rules and demonstrate clean worker exit on the supported target runtime.

## 3. Runtime evidence identity

Reuse existing environment/runtime/resource evidence owners; do not create a competing release authority. B11 evidence must bind enough material to prove which runtime actually executed the product, including at minimum:

- current publication decision/member identity and authenticated member bytes digest;
- exported product/deployed artifact identity and canonical target head;
- LAMMPS version/runtime identity already owned by environment provenance;
- ML-IAP and KOKKOS availability diagnostics;
- effective KOKKOS launch mode/arguments relevant to execution;
- selected accelerator/resource binding;
- mliappy activation success for the executed instance;
- exact probe geometry/cell/PBC identity;
- claim-scoped stress-capability decision digest(s) where relevant;
- real E/F/stress observations and parity result;
- worker completion/exit status and bounded diagnostic provenance sufficient to distinguish a scientific mismatch from runtime unavailability/crash.

These runtime facts are evidence/currentness inputs only where the existing P7 architecture says runtime/environment identity is material. Do not broaden them into model-selection identity or a new storage subsystem.

## 4. Source implementation consequence

The B11 runtime correction is an **executable P7 repair**, not a post-freeze experiment. Therefore it must be implemented and regression-tested before the final executable candidate/tree is frozen.

Required source consequences:

1. remove/demote the static `forward_exchange` capability oracle as an owner of MACE product availability;
2. make the real LAMMPS worker able to start the authenticated selected KOKKOS GPU mode and activate mliappy on the exact live instance;
3. route real current-publication MACE product evaluation through that worker/path;
4. preserve existing exact target-head, stress, cell/PBC, resource-allocation, crash isolation, and no-fallback contracts;
5. ensure teardown does not invoke Python finalization from the external Python process;
6. surface typed runtime-unavailable/crash diagnostics without converting them into scientific rejection or PASS.

If inspection shows the existing worker already provides an equivalent lifecycle/activation owner, extend/reuse it rather than introducing another wrapper.

## 5. Mandatory focused and integration acceptance

### 5.1 Focused/runtime-owner tests

Add tests proving:

- a one-GPU authenticated allocation resolves to effective KOKKOS startup equivalent to `-k on g 1 -sf kk`;
- other supported resource allocations do not silently receive an incompatible hard-coded GPU count/device;
- `activate_mliappy()` is called on the exact LAMMPS instance before Python ML-IAP MACE execution;
- absence/failure of direct imports of `mliap_unified_couple*` cannot by itself classify the actual product path unavailable;
- a static class without `forward_exchange` cannot by itself skip B11;
- an actual MACE callback failure for missing `forward_exchange` is captured as authoritative runtime-unavailable/blocking evidence;
- the worker path contains no call to `lammps.finalize()` or `lammps_python_finalize()` in the externally owned Python lifecycle;
- normal worker shutdown is clean and returns a successful structured result/exit status;
- simulated/controlled abnormal worker termination cannot publish successful B11/component evidence and leaves the parent/store recoverable;
- existing static/dynamics exact PBC and repaired stress-conversion behavior remain unchanged.

Tests may mock below the runtime owner for failure/lifecycle branches, but such tests do not replace the real integration gate.

### 5.2 Required real-owner integration

On a supported target runtime, run an actual current frozen P5 multihead publication member through:

```text
real member bytes -> real exporter -> real LAMMPS_MLIAP_MACE -> canonical head
-> real one-GPU KOKKOS LAMMPS -> real mliappy activation -> actual evaluation
```

Acceptance requires:

- the evaluation actually enters the MACE callback and completes;
- energy/forces are observed and satisfy the frozen parity contract;
- stress is observed/compared whenever the corrected claim-scoped stress decision requires it;
- exact cell/PBC evidence is preserved under the revision-13 static/dynamics contract;
- worker exits cleanly with no KOKKOS/CUDA/Python-finalization crash;
- no static `forward_exchange` preflight skip can suppress this run on the verified capable target environment.

Ordinary CI may skip this hardware/runtime integration only when the real target runtime is genuinely absent. Such a CI skip is **unavailable**, not P7 PASS. P7 cannot close until this integration succeeds on the actual supported target-machine runtime.

## 6. Revised binding implementation order

This amendment supersedes revision-13 section 11 with the following order:

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

No executable source edit is permitted between R13-P8 freeze and accepted R13-P9/P10 evidence. Any required runtime-source correction after freeze invalidates affected evidence and requires a new candidate freeze.

## 7. B12 consequence

R12-B12 is unchanged scientifically, but it must use the **same corrected runtime owner** proven by B11. Final target-machine qualification may not use a separate ad-hoc LAMMPS launch path or a capability shortcut that was not part of the frozen executable candidate.

Thus the final target-machine run must inherit:

- selected KOKKOS resource activation;
- mliappy activation on the exact live LAMMPS instance;
- real target-head MACE product execution;
- safe worker/process lifecycle;
- corrected stress capability/provenance semantics;
- exact cell/PBC evidence;
- complete attempt-wide resource evidence and immutable terminal/release closure.

## 8. Closure correction

Revision-13 closure remains binding except that R12-B11 is now stated precisely as follows:

> The actual frozen publication member must successfully execute through the real mdstats exporter, canonical target-head `LAMMPS_MLIAP_MACE`, selected KOKKOS-enabled LAMMPS Python runtime, and actual ML-IAP/MACE callback on the supported target machine, producing required E/F/stress parity and clean worker completion. Static `forward_exchange` introspection is neither PASS nor authoritative UNAVAILABLE evidence.

The operator's successful KOKKOS/mliappy startup and clean native shutdown diagnostics establish that implementation should target this runtime path; they do **not** by themselves close B11.

All other R13 blockers, regression obligations, R12-B12 final qualification, one-shot locked semantics, and successor-storage blocking remain unchanged.
