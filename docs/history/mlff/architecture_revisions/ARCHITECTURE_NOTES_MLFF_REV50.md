---
title: "MLFF Architecture Revision 50"
subtitle: "Deferred final-release GPU qualification"
date: "2026-08-15"
geometry: margin=0.78in
fontsize: 10pt
---

# Revision 50

Revision 50 changes **qualification scheduling**, not target-size science.

The supplied MACE-MH-1 and MACE-MPA-0-medium models are now present and match the foundation hashes already locked by the MH1 architecture. CPU/e3nn reference qualification can therefore continue during development.

All remaining MLFF GPU-dependent qualification is consolidated into `FINAL-GPU1`, executed once against the frozen final release package on the user's CUDA/CuEquivariance workstation. Intermediate releases must not request iterative GPU handoffs.

# Development-order change

`SIZE-FIDELITY1` remains scientifically open until its exhaustive MACE calibration is run, but it is no longer an implementation blocker. The reducer and candidate calibration grid are fully parameterized, so `PERF-P2R` and `PERF-P3` may be implemented before accelerator qualification.

The development path becomes:

$$
\text{SIZE-HALVE1}
\rightarrow
\text{SIZE-FIDELITY1 implementation}
\rightarrow
\text{PERF-P2R implementation}
\rightarrow
\text{PERF-P3}
\rightarrow
\cdots
\rightarrow
\text{FINAL-GPU1 qualification}.
$$

Final production release still requires a passing SIZE-FIDELITY1 scientific calibration and every required accelerator acceptance item.

# Locked model identities

| Foundation | Head | SHA-256 |
|---|---|---|
| MACE-MH-1 | `omat_pbe` | `ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde` |
| MACE-MPA-0-medium | `default` | `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638` |

The model binaries remain external locked inputs and are not duplicated into the mdstats distribution.

# FINAL-GPU1 scope

The final workstation package consolidates real CuEq activation/parity, DATA6 descriptor/selection parity, bounded CuEq training realization, generated-default MH-1 certification, SIZE-FIDELITY1 exhaustive calibration, and PERF-P2R whole-funnel GPU/VRAM performance. ML-IAP/LAMMPS deployment parity remains a separate capability because it also requires an appropriate `lmp` executable.

The development-host preflight is `deferred_not_executed`: both model hashes pass, MACE 0.3.16 and e3nn 0.4.4 are present, but PyTorch is CPU-only and CuEquivariance is absent.
