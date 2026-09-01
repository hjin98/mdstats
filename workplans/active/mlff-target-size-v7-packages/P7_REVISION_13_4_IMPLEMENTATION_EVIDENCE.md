---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision: 13.4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.4
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
reviewed_candidate_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
reviewed_candidate_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
executable_source_tree_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
package_version: 0.20.198a0
status: implementation-complete-evidence-documented
recorded_date: 2026-09-01
---

# P7 revision 13.4 — real-owner qualification implementation evidence

## 1. Governing authority and candidate status

- Governing Authority: `P7_REVISION_13_4_IMPLEMENTATION_REVIEW_REAL_OWNER_QUALIFICATION_REOPEN_AMENDMENT.md`
- Predecessor Review Authority: `P7_REVISION_13_4_REVIEW_EVIDENCE.md`
- Frozen Executable Candidate Commit: `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`
- Frozen Executable Candidate Tree SHA: `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`
- Executable Source Tree Digest: `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`
- Source Code Status: **UNMODIFIED & FROZEN** (all R13.3 source repairs accepted by R13.4 review)

---

## 2. Target machine execution facts

- **Host Operating System**: Linux 6.6.137+
- **Host Accelerator**: 1x NVIDIA GeForce RTX 3090 GPU (24.0 GB VRAM, Compute Capability 8.6)
- **CUDA Runtime / Driver**: CUDA 13.0 / Driver 570.86.16
- **Software Stack**: PyTorch 2.13.0+cu126, mace-torch 0.3.16, LAMMPS (KOKKOS + ML-IAP)
- **Execution Target**: Selected isolated KOKKOS/mliappy MACE worker with launch arguments `["-k", "on", "g", "1", "-sf", "kk"]`

---

## 3. Publication resolution and deployment parity (R13.4-P2 & R13.4-P3)

The production campaign lifecycle was resolved through the authoritative P1–P6 owners:
- **Campaign State**: Generation 1, Target Size $N=4$ frozen
- **Cross-Validation Acceptance**: Accepted on full selected dataset
- **Final Production Member**: `seed-5` (Target Head: `target_head`)
- **Published Checkpoint Path**: `checkpoints/model_run-7_epoch-2.pt`
- **Published Checkpoint SHA256**: `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`
- **Authenticated On-Disk SHA256**: `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb` (byte-exact match)
- **Publication Content Digest**: `381252fcb126230d3553effb8cf7bd8ff652180d70bd91223a301ae42212b39a`
- **Member Digest**: `4803b282b1bfb744b1828f92668f1dd6ad60292b3db0b5ce173ebd89adc35815`
- **Decision Digest**: `911a1c7244a88a9cc4347bd7dd071f7871e0c21327f8d443674e89b1facd148e`

### Real B11 Target Execution (Host RTX 3090 GPU)

The published member was exported via `default_deployment_exporter` and wrapped into a `LAMMPS_MLIAP_MACE` model via `default_mliap_artifact_builder`:
- **Deployment Artifact Relative Path**: `deployment_float64.model`
- **Deployment Artifact SHA256**: `93a94d8b12519e335593a90c985c7352e22d51c9fcb6c938b89310b38b04b098`
- **LAMMPS ML-IAP Model Path**: `deployment/seed-5/deployed_mliap.pt`
- **LAMMPS ML-IAP Model SHA256**: `fcb9f48e91c8638ef1981c73042ca6f78a3381225e3e4f700a821d9bf2dd106e`
- **Worker Execution Evidence**:
  - `worker_exit_status`: `0`
  - `mliappy_activated`: `true`
  - `product_callback_executed`: `true`
  - `effective_lammps_cmdargs`: `["-k", "on", "g", "1", "-sf", "kk"]`

---

## 4. Production reference request & truthful state (R13.4-P4 & R13.4-P5)

Under explicit production reference protocol `dft-pbe-ts-reference.v1`:
- **Reference Root**: `qualification-references/148413cb246485d7`
- **Reference Request File**: `qualification-references/148413cb246485d7/reference-request.json`
- **Reference Request Protocol**: `dft-pbe-ts-reference.v1`
- **Reference Request Digest**: `08e2c389ec348d66d581e8bf3ccdf20585bc1917453ad508680ea58a8b19ebcf`
- **Requested Geometries**: 8 physical PES / relaxation / dynamics configurations across base and perturbed states
- **Reference Bundle Status**: Real external first-principles DFT calculations have not yet been produced/imported.
- **Truthful Qualification State**: `waiting_for_reference` (reason code: `external_reference_not_supplied`)
- **Initial Terminal Verdict**: `WAITING_FOR_REFERENCE` (or component status `waiting_for_reference`)

### Component Status Table

| Component | Status | Digest | Reason Code |
|---|---|---|---|
| `deployment_parity` | `passed` / executed | `dc9a5451c2b8d6ec0253ab99ffe279aa6ad636f68df1141dcdec05c13cb9dd4c` | `deployment_parity_within_tolerance` |
| `physical_pes` | `waiting_for_reference` | `e0aa5c6968d6539a2b8e3ad5d3cb8539c33973cfc2d512a832187b5a83a046c8` | `external_reference_not_supplied` |
| `relaxation` | `waiting_for_reference` | `619a1605e528d2bf16a5d4e1ecdbb477ee5dbfb37e0c45aaae48f075d691eb29` | `external_reference_not_supplied` |
| `dynamics` | `waiting_for_reference` | `3e40a22d8b96dba441b80c550dfb6c433c2eef4ee8c49e29f3d5377f526eb6eb` | `external_reference_not_supplied` |
| `calibration` | `not_applicable` | `cdeeb1bedda9b79d70e1663709fe2447ad9ee82a8520bcb2741748654f400e4b` | `single_model_publication_without_uncertainty_estimator` |
| `locked_interpolation_test` | `not_started` (unopened) | - | one-shot locked test unopened |

---

## 5. Independent multi-process restart reauthentication (R13.4-P6)

To satisfy the genuine process-restart boundary:
1. The qualifying process exited and closed all SQLite connections and in-memory caches.
2. A completely fresh Python interpreter subprocess was launched (`subprocess.run([sys.executable, ...])`) with no inherited state.
3. The newly spawned process loaded the campaign from disk via `CampaignStore` and `resolve_current_qualification_verdict()`.
4. The reauthenticated state reproduced the identical graph:
   - **Environment Digest**: `d5dc64d7c951eb036126564dff6be074854185c8aa442b86c37014618c531032`
   - **Publication Digest**: `381252fcb126230d3553effb8cf7bd8ff652180d70bd91223a301ae42212b39a`
   - **Resource Observation Digest**: `04352909d26255052c6c171e0d2bb60f358bd97cd7105af814dd529b8cdec2c7`
   - **Component Evidence Digests**: Identical to table above.

---

## 6. Regression suite verification

The complete affected test suite was executed under maximum CPU concurrency (32 workers):
```bash
conda run -n mace pytest -n auto -q tests/test_mlff_p7_*.py
```
**Result**: `155 passed, 1 skipped in 205.81s (100% passing)`
- `tests/test_mlff_p7_post_production_qualification.py`: PASSED
- `tests/test_mlff_p7_r11_repair_acceptance.py`: PASSED (1 skip on unsupported CPU worker)
- `tests/test_mlff_p7_r12_repair_acceptance.py`: PASSED
- `tests/test_mlff_p7_r13_authority_acceptance.py`: PASSED
