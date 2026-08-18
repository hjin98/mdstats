---
title: "MLFF Architecture Revision 51"
date: "2026-08-15"
version: "0.20.184a0"
---

# Revision 51

Revision 51 closes the CPU/control-plane implementation portion of PERF-P2R while preserving the FINAL-GPU1 deferral policy introduced after the foundation checkpoints were supplied.

## PERF-P2R implementation

- Add a parameterized `PerfP2RStagePlan` for coarse, short, final, and production work authorization. Campaign dispatch no longer carries independent hard-coded 3/10/30 branches and supports coarse boundaries 3, 4, and 5.
- Add an exact structure-epoch exposure authority so incremental continuation work is auditable and repaid prefixes are detectable.
- Add an authenticated content-addressed DATA8 fixed-file cache. Its recipe binds dataset/role, frame-catalog identity, DATA7 authority, weights/policy, exact frame UID order, and configuration scaling/type.
- Reuse one frame-array index across DATA7/DATA8 materialization where the frame-catalog authority is unchanged.
- Treat the shared DATA8 cache as reconstructable campaign state and remove it after preparation when safe.
- Preserve stage evidence permissions: coarse work is target-only; replay/physical evidence is authorized only at later scientific boundaries.

## Qualification split

CPU/control-plane implementation can be qualified independently of accelerator execution. The following remain deferred to FINAL-GPU1:

- SIZE-FIDELITY1 empirical survivor calibration;
- resumed versus uninterrupted MACE endpoint parity;
- target/replay/physical endpoint equality on the authorizing runtime;
- GPU utilization and VRAM;
- whole-funnel MACE throughput and pause/resume overhead.

`I(PERF-P2R)=implemented` therefore does not imply `Q(PERF-P2R)=pass`.

## Bounded CPU evidence

On the deterministic DATA8 fixture, 15 authenticated cache-hit builds reproduced the exact fresh DATA8 authority and reduced median wall time from 79.696 ms to 17.333 ms (4.598x, 78.25% lower). The complete 3/4/5-epoch by 3--7-size exposure grid is also recorded. These are CPU/control-plane measurements only.

## Roadmap

PERF-P3 is the next implementation gate. FINAL-GPU1 remains the single final-release accelerator/scientific qualification wave.
