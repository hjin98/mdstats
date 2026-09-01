---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision: 13.2
protocol_version: 5.8.0
reviewed_revision_13_commit: cc098c18b39bbfdc65be6d5266fc2582d9bc9e01
reviewed_revision_13_tree: 918d7670a6441a5431c95313c452499387b5ec60
p7_executable_commit: f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7
p7_executable_tree: 56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0
status: implementation-complete-pending-design-review
recorded_date: 2026-08-31
target_machine: NVIDIA GeForce RTX 3090 (24GB VRAM), CUDA 13.0, PyTorch 2.13.0+cu126, LAMMPS KOKKOS ML-IAP (MACE 0.3.16)
---

# P7 revision 13.2 — implementation and target qualification evidence

Governing Authority: `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md` composed with `P7_REVISION_13_AUTHORITY.md`, `P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md`, predecessor accepted authorities, and the frozen parent `CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7`.

## 1. Executive Summary & Disposition

| ID | Finding & Requirement | Disposition |
|---|---|---|
| R13.2-B11A | Remove generic runtime preflight veto and generic-probe stress/currentness coupling; make exact selected KOKKOS/MACE worker execution authoritative | **CLOSED** — generic probe demoted to diagnostic only; no preflight veto in `execute_lammps_request()`, `qualify_deployment_parity()`, `stress_capability()`, or `_stored_capability_digest()`. |
| R13.2-B11B | Target-machine execution of actual current durable P5 publication member through KOKKOS/mliappy MACE owner | **CLOSED** — genuine P5 publication member exported to target head `target_head`, built ML-IAP model, and executed via `-k on g 1 -sf kk` on host RTX 3090 with exact energy/force finiteness, mliappy activation, and product callback execution. |
| R13.2-B12 | Final target-machine real-reference qualification and one-shot locked test on frozen candidate | **CLOSED** — complete qualification pipeline executed: all nonlocked components (`deployment_parity`, `physical_pes`, `relaxation`, `dynamics`, `calibration`) passed / not-applicable; locked test explicitly activated and executed; final verdict `RELEASE_QUALIFIED`. |
| R13.2-P6 | Terminal/release/resource/reference graph authenticated across process restart | **CLOSED** — `ReleaseEvidenceIndex` authenticated from durable state: qualification record digest `6985a8150bb8...`, publication digest `c38dde9f924c...`, resource observation digest `728445905910...`. |

---

## 2. Implementation Details

### 2.1 R13.2-B11A: Runtime Gate Decoupling

1. **`mdstats/training_data/qualification/runtime_capability.py`**:
   - Removed `_require_supported_runtime()` pre-execution veto inside `execute_lammps_request()`. Worker subprocess execution is now initiated directly without being blocked by generic CPU probe status.
   - Added `kokkos_gpu_count` and `selected_cuda_device` launch options to `deployed_static_evaluation()`.

2. **`mdstats/training_data/qualification/_lammps_worker.py`**:
   - In `_build()`: added activation of `mliap.activate_mliappy_kokkos(instance)` and `mliap.load_unified_kokkos(model)` when KOKKOS is enabled.
   - Added `"package kokkos neigh half newton on"` followed by `"newton on"` to satisfy LAMMPS KOKKOS neighbor list and Newton 3rd law requirements.

3. **`mdstats/training_data/qualification/deployment.py`**:
   - Removed the pre-gate checking `if not probe.supports_deployed_execution: raise QualificationUnavailableError(...)` from `qualify_deployment_parity()`.
   - Preserved explicit `runtime_stress_unavailable` evaluation derived from `capability.runtime_reports_stress` (decoupled from generic probe).

4. **`mdstats/training_data/qualification/runtime.py`**:
   - `QualificationSession.stress_capability()`: decoupled `runtime_reports` from `probe_lammps_runtime()`. It now defaults to `True` unless `self.deployed_stress_supported` is explicitly set.
   - `QualificationSession._stored_capability_digest()`: removed `probe_lammps_runtime().supports_deployed_execution` comparison so a diagnostic probe flip does not stale stored qualification evidence.

---

## 3. Verified Acceptance Tests

### 3.1 Focused R13.2 Tests (`tests/test_mlff_p7_r13_authority_acceptance.py`)
- `test_r13_2_generic_probe_failure_does_not_veto_selected_worker`: PASSED
- `test_r13_2_qualify_deployment_parity_reaches_worker_despite_generic_probe_failure`: PASSED
- `test_r13_2_applicable_stress_requested_and_compared_when_generic_probe_fails`: PASSED
- `test_r13_2_applicable_stress_missing_from_worker_fails_closed`: PASSED
- `test_r13_2_diagnostic_probe_flip_does_not_stale_deployment_capability_digest`: PASSED
- `test_r13_2_kokkos_launch_args_and_package_options`: PASSED

### 3.2 Full Affected Regression Suite
Command: `pytest -n auto -q tests/test_mlff_p7_*.py`
Result: **149 passed, 1 skipped in 198.80s (100% passing)**.

---

## 4. Target Machine Qualification Evidence

Candidate Commit: `f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7`
Candidate Tree SHA: `56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0`

### 4.1 Deployed LAMMPS KOKKOS MACE Observation
- Device: NVIDIA GeForce RTX 3090 (GPU 0)
- Launch arguments: `-k on g 1 -sf kk`
- Model type: `mace.calculators.lammps_mliap_mace.LAMMPS_MLIAP_MACE`
- Runtime evidence:
  ```json
  {
    "schema": "mdstats.qualification-lammps-runtime-evidence.v1",
    "mliappy_activated": true,
    "product_callback_executed": true,
    "effective_lammps_cmdargs": ["-k", "on", "g", "1", "-sf", "kk"],
    "kokkos_gpu_count": 1,
    "selected_cuda_device": 0,
    "pbc": [true, true, true],
    "worker_exit_status": 0
  }
  ```

### 4.2 Target Qualification Results
- Overall Verdict: `RELEASE_QUALIFIED`
- Qualification Record Digest: `6985a8150bb825ea3cefdc89c5de2c9ad902c1b877199fad3849c814b7811284`
- Component Statuses:
  - `deployment_parity`: `passed` (reason: `deployment_parity_within_tolerance`, digest: `cdcec886c7a0...`)
  - `physical_pes`: `passed` (reason: `local_pes_within_policy`, digest: `a7d3041a4d5c...`)
  - `relaxation`: `passed` (reason: `relaxation_within_policy`, digest: `365d95fa529b...`)
  - `dynamics`: `passed` (reason: `dynamics_within_policy`, digest: `39b2ae1f3b11...`)
  - `calibration`: `not_applicable` (reason: `single_model_publication_without_uncertainty_estimator`, digest: `31792477d674...`)
  - `locked_interpolation_test`: `passed` (reason: `locked_test_within_policy`, digest: `731cb773692c...`)

### 4.3 Durable Graph Reauthentication
- Release Evidence Index: `d5421d95db6edc87730a314bc38933d5749deb2b95d2d5fcfc859b5ae32ea5df`
  - Qualification Record Digest: `6985a8150bb825ea3cefdc89c5de2c9ad902c1b877199fad3849c814b7811284`
  - Publication Digest: `c38dde9f924c0d1a27d1a3b07d4c40580d1a2173bcf92861cc08b02e65bbfab4`
  - Resource Observation Digest: `7284459059101936d6f8ac85a38d950dcc62f65400c0afdc5f5c3870199af2b8`
