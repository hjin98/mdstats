# MLFF Architecture Notes - Revision 58

**Date:** 2026-08-15  
**Release:** mdstats 0.20.191a0  
**Gate:** PERF-CERT1

## Revision summary

Revision 58 implements the PERF-CERT1 end-to-end scientific/performance certification control plane. The optimized original MH-1/`omat_pbe` e3nn path remains the authoritative baseline. CUEQ-PHASE1 remains the independent pure-CuEq training authority; CUEQ-PHASE2 remains the optional selected-head CuEq source/DATA6 authority.

PERF-CERT1 compares complete frozen-workload profiles rather than isolated kernels. Each profile binds the scientific source/protocol, locked MH-1 and MPA-0 identities, workload identity, source/training executable realizations, dependency/runtime identities, deterministic target/DATA6/DATA7 selections, target size/seed, checkpoint/head identities, target/replay metrics, EVAL2/deployment/physical decisions, and end-to-end timing/throughput/VRAM/OOM/backoff telemetry.

Different final checkpoint bytes are permitted. Certification instead requires exact agreement of frozen hard scientific decisions. A faster profile fails if it changes target or DATA6/DATA7 selection, replay retention, checkpoint admissibility, EVAL2, or available deployment/physical outcomes. Locked-test tuning is also a hard failure.

The v1 recommendation requires a strictly positive total end-to-end speedup over the authoritative baseline. PHASE2 is optional: a failed selected-head source profile cannot block a passing e3nn-source + CuEq-training profile. If multiple accelerated profiles pass, lowest total wall time wins with profile ID as deterministic tie-breaker.

A positive PERF-CERT1 gate may recommend a phase-separated acceleration profile, but `generated_default_change_authorized` remains false. Any generated-default change requires a separate documented policy revision with migration and compatibility tests.

Positive accelerator evidence remains deferred to the single FINAL-GPU1 workstation campaign. FINAL-GPU1 preflight advances to v5 and reports CUEQ-DEP1, PHASE1, optional PHASE2, and PERF-CERT1 as independent authorities.


Public implementation is provided by `mdstats/training_data/perf_cert1.py` and `tools/qualify_mlff_perf_cert1.py`; dependency-graph schema 40 records the gate as implemented with positive accelerator evidence pending FINAL-GPU1.
