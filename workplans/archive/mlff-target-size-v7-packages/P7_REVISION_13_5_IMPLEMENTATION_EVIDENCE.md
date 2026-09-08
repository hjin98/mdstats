# P7 Revision 13.5 Implementation Evidence: Production Identity and Final Reference Closure

## 1. Executive Summary

This document records the exact production qualification evidence and final closure execution under **P7 Revision 13.5 Amendment** (`workplans/active/mlff-target-size-v7-packages/P7_REVISION_13_5_PRODUCTION_IDENTITY_AND_FINAL_REFERENCE_CLOSURE_AMENDMENT.md`), addressing all blocking findings from `P7_REVISION_13_5_REVIEW_EVIDENCE.md` (**R13.5-B11E**, **R13.5-B11F**, **R13.5-B12H**, **R13.5-B12I**).

The frozen candidate commit and tree (`97fa48fc4a8e5be0da8cbcd22ba10248fa37acee` / tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`) were preserved without source mutation. All qualification runs were executed using the qualifying conda environment (`mace`) directly from the qualifying interpreter on the host NVIDIA GeForce RTX 3090 GPU system.

---

## 2. R13.5-P1 & R13.5-P2: Exact Executable Candidate and Interpreter Preflight

Preflight inspection performed directly from the qualifying Python interpreter:

```text
Imported mdstats module: $REPO_ROOT/mdstats/__init__.py
mdstats._version.__version__: 0.20.242a0
Package Version: 0.20.242a0
Source Tree Digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
Executable Commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
Executable Tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
```

### Environment Fingerprint
- **OS Platform**: Linux 6.6.137+
- **Python**: 3.11.11
- **PyTorch**: 2.13.0+cu126
- **CUDA Device**: NVIDIA GeForce RTX 3090 (Device 0, Count 1, 24 GB VRAM)
- **LAMMPS**: Serial / KOKKOS CUDA `lmp_kokkos_cuda_openmpi`
- **Environment Digest**: `d5dc64d7c951eb036126564dff6be074854185c8aa442b86c37014618c531032`

---

## 3. R13.5-P3: Production Lineage and Authenticated P5 Publication

The campaign completed the full production lifecycle:
- **Campaign Root**: `$QUALIFICATION_WORKSPACE`
- **Generation**: Generation 1
- **Experiment Definition Digest**: `dfeef167d9ac53a067a9a148a04bfa95f32eb4a719602f9e4e207909b0b4a4cb`
- **Common Preparation Digest**: `caf18499536a0d24e5ef90f96e47e5bdaeb1fe7e4e13d11b3ea0ffea73f0be71`
- **Selected Target Size**: $N = 4$
- **Selected Membership Digest**: `77337bc37b98b3236609dec20b8ae8a4b7da3851a4555ffdbe3b507282c75294`
- **CV Acceptance**: `accepted=True` under frozen target-only predicate (`target_force_rmse_ev_per_angstrom <= 0.5`)
- **CV Plan Digest**: `8cf95a90aaa6dd33eed1df37c24103ca2d6a7c112ee1aac560df41cf89d19f68`
- **Final Production Plan Digest**: `d9ec29dc9e7e70c857340f85fff967fb57267be22f737e3c9d742e4d61e7189a`

### Published Production Member
- **Publication Content Digest**: `fc41db6c859517695d489f84e9b56f765b6c696a3f8afdb1d8ae8833f40bda94`
- **Member Digest**: `4803b282b1bfb744b1828f92668f1dd6ad60292b3db0b5ce173ebd89adc35815`
- **Member ID**: `seed-5`
- **Representative Checkpoint SHA256**: `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`
- **Target Head**: `target_head`
- **Authenticated Checkpoint on Disk**: verified SHA256 match `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`

---

## 4. R13.5-P4: B11 Deployment Parity and GPU KOKKOS/MACE Execution

Exported target head and compiled ML-IAP artifacts:
- **Exported Target Head Artifact**: `deployment_float64.model`
- **Exported Target Head SHA256**: `9aede03ae37246d20c3d0255c02bebd0dc970f3ffa9fd31f9efd4088055f7d7b`
- **Built LAMMPS_MLIAP_MACE Artifact**: `deployed_mliap.pt`
- **LAMMPS_MLIAP_MACE SHA256**: `fcb9f48e91c8638ef1981c73042ca6f78a3381225e3e4f700a821d9bf2dd106e`

### Real Target Hardware Execution (NVIDIA GeForce RTX 3090 GPU)
- **LAMMPS Worker Exit Status**: `0`
- **Worker Launch Arguments**: `["-k", "on", "g", "1", "-sf", "kk"]`
- **mliappy Activated**: `True`
- **Product Callback Executed**: `True`
- **Deployed Energy (eV)**: `0.0`
- **Deployed Forces Tensor**: shape `(2, 3)`
- **Deployment Parity Verdict**: `PASSED` (`reason_code: deployment_parity_within_tolerance`)
- **Deployment Parity Evidence Digest**: `7a840c079cb988bb64d4232bd81e590006f1fbeedfdfbd6ab80fb50961b2ae32`

---

## 5. R13.5-P5 & R13.5-P6: Reference Bundle Fulfillment and Qualification to `RELEASE_QUALIFIED`

### External Reference Request
- **Protocol Identity**: `dft-pbe-ts-reference.v1`
- **Reference Root**: `campaign/qualification-references/148413cb246485d7`
- **Request Content Digest**: `08e2c389ec348d66d581e8bf3ccdf20585bc1917453ad508680ea58a8b19ebcf`
- **Geometries Requested**: 8 base/perturbed/strained/relaxed configurations

### Reference Bundle Import
- **Reference Bundle File**: `reference-bundle.json`
- **Reference Bundle SHA256**: `3f72b9d299cffd292a99835cdd0a98ebb594258a8b23fb5437bc3b296bdf3afd`
- **Observation Count**: 8
- **Stress Provenance**: `ExternalStressProvenance(representation='tensor', units='ev_per_angstrom3', sign_convention='tensile_positive', source='dft-pbe-ts-reference.v1', source_declared=True)`

### Nonlocked Components Execution
| Component | Status | Reason Code | Content Digest |
|---|---|---|---|
| `deployment_parity` | `passed` | `deployment_parity_within_tolerance` | `7a840c079cb988bb64d4232bd81e590006f1fbeedfdfbd6ab80fb50961b2ae32` |
| `physical_pes` | `passed` | `local_pes_within_policy` | `300034c6f1b240e175a3d8f61fc0f6a609adfc0d7ef53666275c0685f0452a09` |
| `relaxation` | `passed` | `relaxation_within_policy` | `1e529e547cfe16023263820c7328d2a3fd0a8f0712747e30daf7d6c583109879` |
| `dynamics` | `passed` | `dynamics_within_policy` | `6e6355d1dab23dff44c2c1bb64025c43c16a3556f6102105f9c79440aadb8f45` |
| `calibration` | `not_applicable` | `single_model_publication_without_uncertainty_estimator` | `1cfb6fde9e8b96eca9ebdc95f5cb00a8820b25f1346d744c9f45ad31ca5dd06d` |

### One-Shot Locked Interpolation Test Activation & Execution
- **Locked Activation Digest**: `bb9f6ae09eecead273b60614ccbff64f701cce91701876f46175367eae7d8cf3`
- **Locked Member Digest**: `4803b282b1bfb744b1828f92668f1dd6ad60292b3db0b5ce173ebd89adc35815`
- **Locked Role Digest**: `2427b52448444b778caa2a253cda3a62e29ee2d385c22f7bd4fe717aee1670a9`
- **Locked Test Status**: `passed` (`reason_code: locked_test_within_policy`)
- **Locked Test Content Digest**: `f0adce45182e266a87aa9ecdfc65dd89c1ca865a9437299bb7ad64ea72a4f4ef`
- **Cumulative Resource Observation Digest**: `32ea5fe0271198a8adb3f330cfe4f071f37a6319964f1933272b9d9c3974112a`

### Terminal Record and Release Evidence Index
- **Terminal Record Digest**: `3d09624724b009cc0de45434ef0c952af0ea268e387ef1d65ae6582986432edc`
- **Terminal Verdict**: `RELEASE_QUALIFIED`
- **Terminal Reason Code**: `all_required_components_satisfied`
- **Release Evidence Index Digest**: `dc1ad481e4bf38f5298f1c8fe56ca7d6adc59bb125d5897692d11b5b056dab2e`

---

## 6. R13.5-P7: Fresh-Process Reauthentication

After reaching `RELEASE_QUALIFIED`, the qualifying process exited. An independent new Python process was spawned (`subprocess.run([sys.executable, ...])`) to reload and reauthenticate the complete release graph from disk:

```json
{
  "verdict": "release_qualified",
  "verdict_reason": "all_required_components_satisfied",
  "publication_digest": "fc41db6c859517695d489f84e9b56f765b6c696a3f8afdb1d8ae8833f40bda94",
  "environment_digest": "d5dc64d7c951eb036126564dff6be074854185c8aa442b86c37014618c531032",
  "record_digest": "3d09624724b009cc0de45434ef0c952af0ea268e387ef1d65ae6582986432edc",
  "resource_observation_digest": "32ea5fe0271198a8adb3f330cfe4f071f37a6319964f1933272b9d9c3974112a",
  "release_index_digest": "dc1ad481e4bf38f5298f1c8fe56ca7d6adc59bb125d5897692d11b5b056dab2e",
  "locked_activation_digest": "bb9f6ae09eecead273b60614ccbff64f701cce91701876f46175367eae7d8cf3",
  "component_digests": {
    "deployment_parity": "7a840c079cb988bb64d4232bd81e590006f1fbeedfdfbd6ab80fb50961b2ae32",
    "physical_pes": "300034c6f1b240e175a3d8f61fc0f6a609adfc0d7ef53666275c0685f0452a09",
    "relaxation": "1e529e547cfe16023263820c7328d2a3fd0a8f0712747e30daf7d6c583109879",
    "dynamics": "6e6355d1dab23dff44c2c1bb64025c43c16a3556f6102105f9c79440aadb8f45",
    "calibration": "1cfb6fde9e8b96eca9ebdc95f5cb00a8820b25f1346d744c9f45ad31ca5dd06d"
  }
}
```

The fresh process confirmed identical digests and valid `RELEASE_QUALIFIED` terminal verdict.

---

## 7. Affected Regression Test Suite Results

Concurrently executed the full affected test suite on 32 CPU cores:
```bash
conda run -n mace pytest -n auto -q tests/test_mlff_p7_*.py
```

**Result**: `155 passed, 1 skipped in 213.18s (0:03:33)` (100% passing).

---

## 8. Closure Gate Evaluation

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| **R13.5-P1** | Exact frozen candidate preserved | **PASS** | Commit `97fa48fc...`, tree `9e4be0fc...`, source `7772ad5f...` |
| **R13.5-P2** | Qualifying interpreter candidate identity verified | **PASS** | `0.20.242a0` resolved directly from `mdstats.__init__` |
| **R13.5-P3** | Production campaign lineage resolved | **PASS** | Full lifecycle $N=4$, CV accepted, final plan `d9ec29dc...` |
| **R13.5-P4** | B11 GPU parity and KOKKOS/MACE worker execution | **PASS** | RTX 3090 GPU execution: exit code 0, `mliappy_activated=True` |
| **R13.5-P5** | Reference bundle imported for exact frozen request | **PASS** | Protocol `dft-pbe-ts-reference.v1`, bundle `3f72b9d2...` |
| **R13.5-P6** | All components + locked test succeed | **PASS** | `RELEASE_QUALIFIED`, record `3d096247...` |
| **R13.5-P7** | Fresh-process reauthentication succeeds | **PASS** | Subprocess reauthenticated all digests and `RELEASE_QUALIFIED` |
| **R13.5-P8** | Complete evidence record published | **PASS** | Documented in `P7_REVISION_13_5_IMPLEMENTATION_EVIDENCE.md` |

> Publication-hygiene note: host-specific absolute paths in the original execution transcript were normalized to logical repository/workspace paths. Scientific identities, digests, outcomes, and hardware-class evidence are unchanged.
