---
title: "SIZE-FIDELITY1 execution readiness"
subtitle: "mdstats 0.20.183a0 - architecture revision 49"
date: "2026-08-15"
geometry: margin=0.82in
fontsize: 10pt
---

# Status

**State:** execution-ready; scientific calibration pending.

`mdstats 0.20.183a0` implements the SIZE-FIDELITY1 calibration authority and freezes the exhaustive execution matrix, but this host cannot close the scientific gate. The supplied environment contains MACE 0.3.16 source dependencies, no authorizing foundation checkpoint, and CPU-only PyTorch 2.10.0+cpu; CUDA availability is false.

PERF-P2R therefore remains blocked. No three-epoch fidelity or GPU-performance claim is inferred from CPU-side structural tests.

# Scientific calibration contract

For $N_K$ hard-coverage-qualified sizes and $N_s$ frozen calibration seeds, calibration itself performs no halving:

$$
N_{\mathrm{train}} = N_KN_s.
$$

Every run is uninterrupted to 30 epochs. With candidate coarse endpoints $\{3,4,5\}$ and fixed 10/30 boundaries, one full-development inference authority is purchased at five checkpoints per run:

$$
N_{\mathrm{infer}} = 5N_KN_s.
$$

The 128/256/512/1024 monitor candidates are deterministic reductions of those same authenticated per-frame predictions; monitor-size calibration does not multiply MACE inference.

A candidate setting passes only if, for every frozen seed:

1. monitor and full-development coarse promotion sets are identical;
2. both eventual 30-epoch target finalists survive the coarse top-four screen;
3. both eventual finalists survive the epoch-10 top-two screen;
4. the eventual target winner survives both screens;
5. an eventual largest-size boundary finalist is never falsely eliminated; and
6. checkpoint/run/foundation/policy/schedule/evaluation identities prove one uninterrupted trajectory.

Spearman rank correlation is diagnostic only and cannot waive a survivor-recall failure.

# Default execution envelope

| Coverage-qualified sizes | 30-epoch runs | Full-role inference endpoints |
|---:|---:|---:|
| 3 | 9 | 45 |
| 4 | 12 | 60 |
| 5 | 15 | 75 |
| 6 | 18 | 90 |
| 7 | 21 | 105 |


If all seven default sizes qualify, the calibration requires **21 uninterrupted 30-epoch runs** and **105 full-role inference endpoints**. These are execution counts, not wall-time estimates.

# CPU-side qualification

- package-wide `compileall`: pass;
- focused SIZE-FIDELITY1/SIZE-HALVE1/DATA2D slice: **30 passed**;
- adjacent DATA2C/D/E, EVAL2 and PERF specification slice: **71 passed**, 2 existing velocity-reconstruction warnings;
- package-wide collection with the historical test-helper path enabled: **3,000 tests collected**, three expected optional/runtime skips, no collection errors;
- fail-closed serialization, exact metric-grid completeness, common-role identity, exact monitor/full promotion equivalence, both-finalist recall, boundary recall and deterministic recommendation are covered by regression tests.

One archival ADAPT-EVAL1 specification still asserts the exact historical package literal `0.20.140a0`; it fails against `0.20.183a0`. It is recorded as historical test debt rather than rewritten for this gate.

# Authorizing run required

SIZE-FIDELITY1 closes only after the exhaustive real MACE calibration matrix is collected from the authorizing foundation checkpoint and a qualifying GPU/runtime. The resulting report must select a passing coarse endpoint, monitor size and early practical-equivalence width or fail closed. Coverage-based four-size truncation is not an allowed fallback.
