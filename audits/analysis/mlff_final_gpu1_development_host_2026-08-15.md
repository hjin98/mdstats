---
title: "MLFF FINAL-GPU1 Development-Host Qualification Report"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
---

# Result

**Release:** `mdstats 0.20.192a0` / architecture revision 59 / dependency-graph schema 41  
**FINAL-GPU1 control plane:** PASS  
**Positive CUDA/CuEquivariance qualification:** NOT EXECUTED on this host  
**Development preflight state:** `deferred_not_executed`

The development host is used only to qualify the handoff implementation, provenance guards, serialization, documentation, and CPU/reference behavior. It is not used to infer accelerator success.

# Host/runtime snapshot

| Component | Development-host state |
|---|---|
| Python | 3.13.5 |
| PyTorch | 2.10.0+cpu |
| CUDA | unavailable |
| MACE | 0.3.16 |
| e3nn | 0.4.4 |
| CuEquivariance core | unavailable |
| CuEquivariance Torch | unavailable |
| CuEquivariance Torch ops | unavailable |
| OpenEquivariance | unavailable |

The v6 preflight therefore records the expected blockers `torch_cuda_available` and `cueq_dep1_runtime_freeze`. The in-archive development-host preflight also records `release_artifact_binding` because the final source-archive digest is generated only after the archive is sealed; a release-bound sidecar preflight is generated afterwards.

# Locked foundation identities

| Foundation | SHA-256 | Result |
|---|---|---|
| MACE-MH-1 | `ec00a2705854622f...` | PASS |
| MACE-MPA-0-medium | `75428afe3a1d7d80...` | PASS |

The complete digests are stored in the v6 preflight and FINAL-GPU1 policy. Real-model reference checks were run separately with the supplied model paths and passed.

# Final handoff controls

Revision 59 implements an immutable 15-item matrix with seven must-pass release blockers, six measure-only optimization results, and two optional capability results. Every registered artifact is content-addressed and tied to one source-release archive. CuEq-dependent evidence additionally binds one CUEQ-DEP1 runtime digest. Final reduction rejects missing required evidence, unfinished measure-only measurements, release/runtime drift, foundation drift, structured CUEQ/PERF digest drift, or a negative PERF-CERT1 authority.

The handoff registrar is append-only for a run root: initialized roots cannot be silently reinitialized and registered gate evidence cannot be overwritten. Initialization also rejects foundation files that do not match the locked MH-1/MPA-0 identities. An integrity pass re-hashes the release archive, model inputs, evidence files, and records, requires the canonical FINAL-GPU1 policy, and binds the exact ordered 15-item matrix (gate, acceptance, record path, state domain) before reduction so post-registration mutation or structural manifest drift becomes a release blocker rather than an undetected provenance change.

# Validation summary

The current FINAL-GPU1/CUEQ/PERF-CERT1 focused slice completes with **29 passed and 1 expected real-model mount skip**. A separate current synchronization slice completes **19/19 passed**. The skipped supplied-model identity check passes separately when pointed at the locked MH-1 and MPA-0 files. One broader archival PERF-P3 specification remains intentionally version-pinned to `0.20.187a0` and is not rewritten as a current-release test. The source-tree CLI surface, including the corrected PHASE1 qualifier bootstrap, is exercised from outside the repository working directory.

PDF preflight is clean for the revision-59 architecture note, FINAL-GPU1 specification, workstation runbook, patch notes, and 198-page canonical MLFF architecture manual. Visual inspection covered the gate-local specification/runbook pages and the canonical revision-59 tail page.

# Authorization boundary

This report does **not** authorize CuEq training, CuEq source execution, a PERF-CERT1 recommendation, or a generated-default change. Positive accelerator authority must be produced by the final workstation bundle. Even after a positive FINAL-GPU1 reduction, generated-default migration remains a separate explicit policy revision.
