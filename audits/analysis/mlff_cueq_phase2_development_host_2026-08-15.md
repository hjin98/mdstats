---
title: "MLFF CUEQ-PHASE2 Development-Host Qualification"
subtitle: "Control-plane qualification with accelerator execution deferred to FINAL-GPU1"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
---

# Result

**Release:** mdstats 0.20.190a0  
**Architecture:** revision 57 / dependency graph schema 39  
**Gate:** CUEQ-PHASE2  
**Control-plane result:** PASS  
**Positive GPU qualification:** DEFERRED to FINAL-GPU1

The development host is CPU-only. It has the reconstructed MACE 0.3.16 / e3nn 0.4.4 reference environment but no CuEq core, CuEq Torch frontend, CuEq CUDA-ops layer, or CUDA device. The negative CUEQ-DEP1 record is therefore expected and fail-closed.

# Frozen scientific and execution identities

The phase-2 policy preserves the original six-head MACE-MH-1 checkpoint with the exact `omat_pbe` head as the scientific source. The candidate execution path is the previously EXTRACT1-qualified single-head artifact plus pure CuEq.

| Identity | Digest prefix |
|---|---|
| Original MACE-MH-1 checkpoint | `ec00a2705854622f` |
| Original source-potential identity | `06bf87891d6addeb` |
| EXTRACT1 selected-head checkpoint | `7b6f3cce6d208616` |
| EXTRACT1 qualification | `0f49db0ff9da291f` |
| Supplied MPA-0-medium checkpoint | `75428afe3a1d7d80` |

Full frozen values (each value is the concatenation of its two 32-hex-digit lines):

- **MH-1:** `ec00a2705854622fbbd898ccfb770107`  
  `2fcd674709102d009fb919c1b8cc5dde`
- **Source-potential:** `06bf87891d6addebd3ea300fa23fd640`  
  `1f0b74897f5676394e99507d03c8fc59`
- **EXTRACT1 checkpoint:** `7b6f3cce6d2086164082f1cb5739098`  
  `de2db990d6a49f0d60e66a3a0f1ae545e`
- **EXTRACT1 qualification:** `0f49db0ff9da291fbb4d70430c711895`  
  `52a531d0239d92c06d0ca4024b05e365`
- **MPA-0-medium:** `75428afe3a1d7d8062e19bcaabd5c433`  
  `623cabf308242ec9fb493e38604fb638`

# Control-plane acceptance

The implementation passes the current-gate and adjacent regression slice. It verifies:

- immutable original scientific source identity;
- exact EXTRACT1 selected-head realization identity;
- deterministic stratified development corpus and locked-test anti-tuning guard;
- reuse of the existing MACE acceleration-parity authority for energy, force, stress/virial, and descriptors;
- foundation-difficulty and frozen-reference-transform PCA/FPS parity states;
- exact DATA6 and DATA7 selection fingerprints;
- explicit candidate execution-realization content addressing;
- pseudolabel/E0 value parity plus dual scientific/execution lineage when pseudolabel execution is requested;
- independent PHASE1 and PHASE2 FINAL-GPU1 states;
- negative-runtime fail-closed behavior with no backend fallback; and
- serialization/tamper detection plus direct source-tree CLI execution.

The focused CUEQ/FINAL-GPU/PERF-adjacent suite passes 35 tests. A separate Stage-11 documentation synchronization slice passes 20 tests. The repository also contains archival specification tests intentionally pinned to historical package releases and earlier dependency-graph schemas; those are not rewritten or counted as current-gate qualification evidence.

# Deferred accelerator state

The development CUEQ-DEP1 runtime has digest:

`0e59a5c702db7e981cae4d8d451d0b2896e1a0b2c139ed0f4498a5869a2ab497`

and fails only the expected accelerator requirements:

- `cueq-core_import`;
- `cueq-torch_import`;
- `cueq-ops_import`;
- `torch_cuda_available`; and
- `cuda_device_inventory`.

The CUEQ-PHASE2 deferred record has digest:

`d43d3bb04feb52d8ac339065ec7a1e5f279e448f9aafbae4bce9e189f863bd65`

with blockers:

- `CUEQ_DEP1_RUNTIME_FREEZE`; and
- `development_path_assessment_missing`.

This is the intended pre-final state. It cannot authorize selected-head CuEq source execution, DATA6, source evaluation, or pseudolabel generation.

# FINAL-GPU1 handoff

FINAL-GPU1 preflight is `mdstats.mlff-final-gpu1.preflight.2026-08.v4`. It verifies both supplied foundation model hashes and embeds the independent PHASE1 and PHASE2 deferred records. The final workstation run must produce one positive release-matched CUEQ-DEP1 runtime and at least one passing deterministic PHASE2 development-corpus assessment before selected-head source/DATA6 execution can be authorized.

Direct CuEq execution of the original six-head checkpoint and any generated-default change remain outside PHASE2 authority even after a positive result.
