---
title: "mdstats 0.20.185a0 Patch Notes"
date: "2026-08-15"
status: "PERF-P3 CPU qualification"
geometry: margin=0.85in
---

# mdstats 0.20.185a0

This release implements PERF-P3 without changing scientific authority.

## Structural selection

- Add a direct local-structure array kernel for high-throughput DATA6 execution.
- Reuse immutable fixed-topology chemistry arrays across frames.
- Keep only coordinate scratch after larger pair/radial scratch benchmarked worse.
- Preserve exact dense pair geometry and FP64 operation order; a numerically close chunked radial alternative was rejected because it changed scientific bytes.

## Foundation audit

- Replace force-tail Python list accumulation plus concatenation with exact final-size preallocation.
- Add an execution-only mmap fallback controlled by `performance.foundation_audit_temporary_ram_mib` (generated default 512 MiB).
- Reject nonpositive temporary-memory thresholds.

## Resource control

- Add `StageResourceScope` to fail closed when nested Python/structural/tree/BLAS/PyTorch CPU execution exceeds the declared stage CPU budget.
- Apply native thread-pool limits where practical without incorporating execution settings into scientific digests.

## Bounded CPU evidence

- 168-atom, 300-frame LTA-like structural fixture: **7.42% lower median wall time**, exact output digest unchanged.
- 900,000-atom foundation-audit reduction fixture: **8.02% lower peak RSS**, exact audit digest unchanged.
- Audit preallocation/mmap is qualified as memory hardening, not a speed claim.

GPU qualification remains deferred to `FINAL-GPU1`. The next implementation gate is **VRAM1 + PERF-P4**.
