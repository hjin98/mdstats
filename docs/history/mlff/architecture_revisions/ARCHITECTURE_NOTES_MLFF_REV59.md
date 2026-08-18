---
title: "mdstats MLFF Architecture Revision 59"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 59 - FINAL-GPU1 release handoff

**Release:** `mdstats 0.20.192a0`  
**Dependency-graph schema:** 41  
**Gate:** FINAL-GPU1 handoff implementation  
**Accelerator result on development host:** intentionally not claimed

Revision 59 converts FINAL-GPU1 from a readiness-only preflight into a content-addressed final-release handoff and reduction authority. The change closes the CPU/control-plane implementation boundary while preserving the project rule that positive CUDA/CuEquivariance qualification occurs once, on the final workstation package.

## Acceptance matrix

FINAL-GPU1 now records 15 matrix items in three classes. Seven **must-pass** release blockers cover the CUEQ-DEP1 runtime freeze, complete authoritative e3nn baseline, SIZE-FIDELITY1, PERF-P2R, VRAM1/PERF-P4, CUEQ-PHASE1, and PERF-CERT1. Six **measure-only** entries retain the legacy direct-CuEq/PERF-P5 observations without allowing a negative obsolete optimization to veto the phase-separated design. CUEQ-PHASE2 and ML-IAP/LAMMPS deployment remain **optional** capabilities.

This split is scientifically important: the known direct-six-head CuEq source path is not reinterpreted as a mandatory production path. Training-only CuEq authority comes from PHASE1; selected-head source/DATA6 CuEq authority exists only after independent PHASE2 qualification.

## Provenance and reduction

`FinalGpu1Policy.v1`, `FinalGpu1EvidenceRecord.v1`, and `FinalGpu1QualificationRecord.v1` bind evidence to the exact release archive, locked foundation-model SHA-256 identities, and one positive CUEQ-DEP1 runtime. CuEq-dependent gates require an explicit runtime binding; structured CUEQ-DEP1, PHASE1, PHASE2, and PERF-CERT1 content digests are cross-checked during reduction. Measure-only terminal states must still carry a content-addressed evidence artifact. Handoff registrations are immutable within a run root. Initialization also rejects foundation files that do not match the two locked model identities.

`tools/run_mlff_final_gpu_qualification.py` advances to preflight v6 and provides `preflight`, `init`, `record`, `status`, `verify`, and `reduce` operations. The `verify` pass re-hashes the release archive, foundation models, registration records, and copied evidence before reduction. It also binds the manifest to the canonical FINAL-GPU1 policy and exact ordered matrix (gate IDs, acceptance classes, record paths, and state domain), so post-registration mutation or structural matrix drift fails closed. Source-tree execution is supported by the handoff CLIs, including the corrected PHASE1 qualifier bootstrap.

## Default-policy boundary

FINAL-GPU1 cannot modify generated campaign defaults. A positive final record may carry a PERF-CERT1 recommended profile and indicate that a later generated-default policy revision is required, but `generated_default_change_authorized` remains false in the final authority.

