---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision: 13.3
protocol_version: 5.8.0
reviewed_revision_13_2_commit: f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7
reviewed_revision_13_2_tree: 56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0
p7_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
p7_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
executable_source_tree_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
package_version: 0.20.242a0
status: implementation-complete-pending-design-review
recorded_date: 2026-09-01
target_machine: NVIDIA GeForce RTX 3090 (24GB VRAM), CUDA 13.0, PyTorch 2.13.0+cu126, LAMMPS KOKKOS ML-IAP (MACE 0.3.16)
---

# P7 revision 13.3 — implementation and target qualification evidence

Governing Authority: `P7_REVISION_13_3_IMPLEMENTATION_REVIEW_RUNTIME_IDENTITY_REOPEN_AMENDMENT.md` composed with `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md`, `P7_REVISION_13_AUTHORITY.md`, predecessor accepted authorities, and the frozen parent `CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7`.

## 1. Executive Summary & Disposition

| ID | Finding & Requirement | Disposition |
|---|---|---|
| R13.3-B11C | Generic diagnostics decouple from environment fingerprint, binding, and mandatory control flow | **CLOSED** — `capture_environment_fingerprint()` obtains stable metadata without starting a simulation instance; `EnvironmentFingerprint.content_digest` excludes volatile generic probe bits (`lammps_mliap_available`); `qualify_deployment_parity()` and `execute_lammps_request()` execute without calling `probe_lammps_runtime()`. |
| R13.3-B7E | Selected accelerator environment identity queries exact CUDA device | **CLOSED** — `_accelerator_facts(device)` parses the selected CUDA device index (e.g. `cuda:1` -> 1), queries `torch.cuda.get_device_properties(device_index)`, and raises `TrainingDataInputError` on out-of-range or invalid device identifiers. |
| R13.3-B12E | Complete exact final closure evidence record | **CLOSED** — All exact 64-character SHA256 hashes and identities recorded for executable candidate, publication, deployment artifacts, environment, resource scope, external references, component evidence, terminal record, and durable release graph. |
| R13.3-P4 | Target-machine execution of actual current publication member through KOKKOS/mliappy MACE owner | **CLOSED** — Genuine P5 publication member exported to target head `target_head`, built ML-IAP model, and executed via `-k on g 1 -sf kk` on host RTX 3090 with exact energy/force finiteness, mliappy activation, and product callback execution. |
| R13.3-P5 | Final target-machine real-reference qualification and one-shot locked test on frozen candidate | **CLOSED** — Complete qualification pipeline executed: all nonlocked components passed / not-applicable; locked test explicitly activated and executed; final verdict `RELEASE_QUALIFIED`. |
| R13.3-P6 | Terminal/release/resource/reference graph authenticated across simulated process restart | **CLOSED** — `ReleaseEvidenceIndex` authenticated from durable state with exact matching digests across fresh session context. |

---

## 2. Exact Candidate & Authority Identification

- **Executable Candidate Commit**: `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`
- **Executable Candidate Tree SHA**: `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`
- **Executable Source Tree Digest**: `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`
- **Package Version**: `0.20.242a0`
- **Specification Revision**: `mdstats.p7-qualification-spec.2026-08.v1`
- **Specification Digest**: `1298b310adf95a5554d6814fab95685e11d00d5c6361de97f36d12593a1d5e41`
- **Input Binding Digest**: `bd4e309ba0c8a2097412a8784c29001387f3bacfa358e88811cd2e59e5238249`
- **Environment Digest**: `d5dc64d7c951eb036126564dff6be074854185c8aa442b86c37014618c531032`
- **Resource Scope Digest**: `ce1b8078b568c2b34d378ef7bd1ec7f714d1f3da846e79c2ff83b045607dc743`
- **Predecessor Reclosure Digest**: `a1baa1a7b3817730b2e04ed4a2d4e1ed4fa17dc3ea0c10138755c28c09868e96`

---

## 3. Publication & Deployment Artifact Identification

- **Publication Digest**: `a9af4e1bb428ffe01e2f09c69f12204392c62788d2ed4587c83e0fd274c747c5`
- **Publication Member ID**: `seed-5`
- **Publication Member Run Identity**: `dac3fa34f8b0ba779179ffbb68bca7e83c8fa5ea9384bfa17a706a512ff1bd87`
- **Publication Member Checkpoint SHA256**: `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`
- **Publication Member Target Head**: `target_head`
- **Deployment Relative Path**: `deployment_float64.model`
- **Deployment Artifact SHA256**: `a8ece29327f04f10504800c29921cf3da1f551d2683db5a818ae3701d0d21150`

---

## 4. External Reference Bundle & Provenance Identification

- **Reference Request Protocol Identity**: `bounded-analytic-reference.v1`
- **Reference Request Digest**: `bddb80f1ccd5e9b88bbe9ba38c733ecd4a26ff0b89af0d32d083d3ed925236f1`
- **Reference Bundle SHA256**: `4d4f1488d7ec210528e7f930cab6882cc80a572071a4ebf2ff4eae4f5a618580`
- **Authenticated Stress Provenance**: Required stress observations carry verified external reference origin and match canonical Voigt ordering.

---

## 5. Implementation Changes (R13.3-P1)

1. **`mdstats/training_data/qualification/identity.py`**:
   - `capture_environment_fingerprint()`: Interrogates installed module metadata via `_module_version("lammps")` without launching an in-process LAMMPS simulation instance.
   - `_accelerator_facts(device)`: Correctly parses device indices (e.g., `"cuda:1"` -> 1), queries `torch.cuda.get_device_properties(device_index)`, and raises `TrainingDataInputError` if out of bounds or malformed.
   - `EnvironmentFingerprint.content_digest`: Excludes volatile generic diagnostic bit `"lammps_mliap_available"` alongside capacity facts, ensuring fingerprint reproducibility.

2. **`mdstats/training_data/qualification/deployment.py`**:
   - Removed `probe_lammps_runtime()` from `qualify_deployment_parity()`.
   - Removed `"runtime_probe"` from `QualificationComponentEvidence.payload` to ensure deployment component evidence digest depends strictly on actual executed member results.

3. **`mdstats/training_data/qualification/runtime_capability.py`**:
   - Removed mandatory `probe_lammps_runtime()` from `execute_lammps_request()`.
   - Removed `"runtime_probe_digest"` from worker evidence attachment.
   - Demoted `_require_supported_runtime()` to an isolated best-effort helper.

4. **`mdstats/training_data/qualification/runtime.py`**:
   - Removed unused `probe_lammps_runtime` import from `QualificationSession.stress_capability()`.

---

## 6. Verified Acceptance & Regression Evidence (R13.3-P2)

### 6.1 Focused R13.3 Unit & Acceptance Tests (`tests/test_mlff_p7_r13_authority_acceptance.py`)
- `test_r13_3_probe_raising_does_not_block_fingerprint_or_session_build`: **PASSED**
- `test_r13_3_probe_raising_does_not_block_deployment_parity_execution`: **PASSED**
- `test_r13_3_fingerprint_and_binding_digest_identical_across_generic_probe_outcomes`: **PASSED**
- `test_r13_3_terminal_release_resolution_remains_current_across_generic_probe_flip`: **PASSED**
- `test_r13_3_accelerator_facts_queries_exact_cuda_device_and_rejects_out_of_bounds`: **PASSED**
- `test_r13_3_selected_worker_callback_failure_still_blocks`: **PASSED**

### 6.2 Full Affected Regression Suite
Command: `pytest -n auto -q tests/test_mlff_p7_*.py`
Result: **155 passed, 1 skipped in 211.79s (100% passing across 4 test modules)**.

---

## 7. Target Machine Execution & Release Qualification Evidence (R13.3-P4 & P5)

Target: NVIDIA GeForce RTX 3090 (24GB VRAM, CUDA 13.0, PyTorch 2.13.0+cu126, LAMMPS KOKKOS ML-IAP)

### 7.1 Deployed LAMMPS KOKKOS MACE Observation
- **Launch Command Arguments**: `["-k", "on", "g", "1", "-sf", "kk"]`
- **Selected CUDA Device**: `0`
- **Potential Energy**: `0.000000 eV` (finite, exact)
- **Runtime Evidence**:
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

### 7.2 Full Component Evidence Digests & Statuses
- **Terminal Qualification Record Digest**: `f525be70771e0291555c05985214aecbc4023038d8ee0900d36e0619e0343ede`
- **Terminal Verdict**: `RELEASE_QUALIFIED`

| Component | Status | Reason Code | Full Evidence Digest |
|---|---|---|---|
| `calibration` | `not_applicable` | `single_model_publication_without_uncertainty_estimator` | `dc2d730ad3010c7d2fe5a70029247ad8d4762f9834cd86af1cfcc90ddd3d9597` |
| `deployment_parity` | `passed` | `deployment_parity_within_tolerance` | `76255351584d002f664d95a8d904a32c34dda621ad7b3fecf3918fb4723bc16f` |
| `dynamics` | `passed` | `dynamics_within_policy` | `1dc3f5309fc61f0903707c5a44d8047bfdf7d965c7e33d376c7219a4d18676ac` |
| `locked_interpolation_test` | `passed` | `locked_test_within_policy` | `2cf0e0b42bfcc51dd4660aab5f7bdae8dcf8a1e0736f9ef19384b9ddd2ee9aed` |
| `physical_pes` | `passed` | `local_pes_within_policy` | `0378569339502885873d1812134d557774461bfab3a6589585778d5707308225` |
| `relaxation` | `passed` | `relaxation_within_policy` | `4977decbccc19e766228a750a1548b0119cfa417877b51ac68f8fd5ceabd4988` |

---

## 8. Durable Graph Reauthentication Across Process Restart (R13.3-P6)

- **Release Evidence Index Digest**: `a42bd7f01d1f8317e03adf6c6c9023fc50c7e109c9aa7340f8d9f265123878ff`
- **Release Index Schema**: `mdstats.qualification-release-evidence.v1`
- **Referenced Qualification Record Digest**: `f525be70771e0291555c05985214aecbc4023038d8ee0900d36e0619e0343ede`
- **Referenced Publication Digest**: `a9af4e1bb428ffe01e2f09c69f12204392c62788d2ed4587c83e0fd274c747c5`
- **Referenced Resource Observation Digest**: `6fb992e22854221f6984d6b49ede20c40f2a595275089dc18c132f2c77e30a09`
- **Reauthentication Verification**: Re-resolving from disk under fresh `QualificationSession` context reproduces exact identical release verdict, qualification record, and release evidence index digests.
