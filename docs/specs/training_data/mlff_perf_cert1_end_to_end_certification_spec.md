---
title: "MLFF PERF-CERT1 End-to-End Scientific and Performance Certification"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
---

# PERF-CERT1 specification

**Gate:** `PERF-CERT1`  
**Implementation release:** `mdstats 0.20.191a0`  
**Architecture revision:** 58  
**Dependency-graph schema:** 40  
**Positive accelerator execution:** deferred to `FINAL-GPU1`

## Purpose

PERF-CERT1 is the end-to-end release certification authority above the already-separated accelerator gates. It decides whether a complete accelerated execution profile is scientifically admissible and operationally beneficial enough to be **recommended**. It does not create a new scientific tolerance and it does not change generated campaign defaults.

The authoritative comparison baseline remains the optimized original MH-1/`omat_pbe` e3nn path. CUEQ-PHASE1 may separately authorize pure-CuEq training from the EXTRACT1-qualified selected-head checkpoint. CUEQ-PHASE2 may optionally authorize the derived selected-head pure-CuEq source/DATA6/source-evaluation path. PERF-CERT1 combines only execution paths already authorized by those upstream gates.

## Profile matrix

PERF-CERT1 recognizes four profile kinds:

1. `authoritative_e3nn_baseline`: source inference and training both use e3nn.
2. `e3nn_source_cueq_training`: source/DATA6 remain e3nn and only training uses pure CuEq; this requires a positive CUEQ-PHASE1 authority.
3. `selected_head_cueq_source_cueq_training`: the EXTRACT1-derived selected-head source/DATA6 path and training both use pure CuEq; this requires positive CUEQ-PHASE1 and CUEQ-PHASE2 authorities on the same CUEQ-DEP1 runtime.
4. `compatibility_fallback`: an intentionally retained compatibility path. It may be scientifically assessed but cannot become the accelerated recommendation merely by existing.

CUEQ-PHASE2 remains optional. A missing or failed PHASE2 assessment cannot invalidate an otherwise passing `e3nn_source_cueq_training` profile.

## Frozen scientific identities

Every profile record binds:

- the original scientific-source digest and exact MH-1 SHA-256;
- the exact MPA-0 replay/foundation SHA-256 used by the campaign;
- `omat_pbe` as the target/source head;
- one scientific-protocol digest covering all non-execution semantics;
- one content-addressed execution realization for source work and one for training;
- the dependency-lock and runtime-record identities;
- the exact workload identity used for timing comparisons; and
- explicit target-size/seed, checkpoint, target-head, EVAL2, deployment, and physical-verification evidence.

Different final checkpoint bytes are allowed. Accelerator kernels can produce different valid optimization trajectories, so checkpoint-byte equality is not a scientific criterion. The gate instead requires agreement of the hard scientific decisions and the existing upstream scientific authorities.

## Hard-decision identity

For baseline-relative certification, PERF-CERT1 requires exact identity of the decisions that are not allowed to move under an execution-only optimization:

- TARGET-DATA2B family order;
- TARGET-DATA2C deterministic selection;
- DATA6 deterministic selection;
- DATA7 deterministic selection;
- final selected target size;
- final selected seed;
- replay-retention decision;
- checkpoint-admissibility decision;
- target-head extraction decision;
- EVAL2 pass/fail decision;
- deployment verification availability/pass state; and
- physical verification availability/pass state.

The record also carries descriptor, foundation-difficulty, and PCA/FPS parity states. No PERF-CERT1 policy may relax the numerical parity thresholds owned by earlier gates.

A faster profile that changes any required hard decision fails certification.

## Performance evidence

Each profile records the same frozen workload and at minimum:

- total preparation wall time;
- TARGET-DATA2B wall time and families/s;
- TARGET-DATA2C selection/scoring time;
- DATA6 wall time and frames/s;
- DATA6 peak allocated, reserved, and headroom VRAM;
- training wall time and updates/s;
- evaluation wall time;
- total end-to-end wall time;
- CUDA OOM count; and
- runtime backoff count.

The default v1 policy requires a strictly positive end-to-end speedup: `baseline_total_wall_time / candidate_total_wall_time > 1.0`. This is deliberately an operational-benefit threshold, not a scientific tolerance. A scientifically valid but non-faster candidate remains non-recommended.

PERF-P2R, VRAM1/PERF-P4, and PERF-P5 remain the component-level execution authorities that feed the final release campaign. PERF-CERT1 does not replace those measurements; it binds their production realization into one complete-profile decision.

## Upstream authorization rules

`PerfCert1UpstreamAuthority.v1` is content-addressed from the CUEQ-PHASE1 and CUEQ-PHASE2 qualification digests plus their authorization states. The builder requires both records to name the same CUEQ-DEP1 runtime.

A candidate using `cueq_pure` for training is rejected unless CUEQ-PHASE1 passed and authorized phase-separated training. A candidate using `cueq_pure` for source/DATA6 execution is independently rejected unless CUEQ-PHASE2 passed and authorized its required selected-head source, DATA6, and source-evaluation paths.

No negative upstream gate can silently fall back and become positive PERF-CERT1 evidence.

## Recommendation semantics

A PERF-CERT1 profile assessment passes only when both scientific admissibility and the required operational benefit pass. The gate-level record passes when:

1. a valid authoritative e3nn baseline is present;
2. positive CUEQ-PHASE1 training authority exists;
3. at least one accelerated profile is supplied; and
4. at least one accelerated profile passes its complete baseline-relative assessment.

When multiple accelerated profiles pass, the recommended profile is the one with the lowest measured total end-to-end wall time; profile ID is the deterministic tie-breaker.

A failing optional PHASE2 profile is retained as evidence but is not a global blocker when a PHASE1 profile passes.

## Default-policy boundary

A positive PERF-CERT1 record may set `phase_separated_acceleration_profile_recommended=true`. It **always** keeps `generated_default_change_authorized=false`.

Changing a generated campaign default is a separate policy revision. That later revision must update the generated campaign configuration explicitly, include migration/compatibility tests, preserve interpretation of historical evidence, and must not silently migrate caches or rewrite prior campaign TOMLs.

## Locked-test and provenance boundary

The locked test may evaluate a previously frozen profile but cannot be used to tune acceleration choices, thresholds, batch sizes, backoff policy, profile selection, or recommendation ranking. `locked_test_used_for_tuning=true` is a hard failure regardless of measured speedup.

Profile timing is admissible only when the scientific protocol and workload digests match the authoritative baseline. Performance numbers from a different workload cannot be compared by this gate.

## FINAL-GPU1 execution

`0.20.191a0` implements the PERF-CERT1 control plane and advances FINAL-GPU1 preflight to v5. The exact preflight schema is:

```text
mdstats.mlff-final-gpu1.preflight.2026-08.v5
```

Development-host preflight emits a valid fail-closed PERF-CERT1 record with missing-baseline/profile blockers and does not launch accelerator work.

The user's final workstation run will populate the same schemas with the positive CUEQ-DEP1, PHASE1, optional PHASE2, authoritative e3nn baseline, accelerated profile, and component-performance evidence. This preserves the project decision to avoid iterative GPU qualification during development.

## Public schemas

- `mdstats.perf-cert1-policy.v1`
- `mdstats.perf-cert1-telemetry.v1`
- `mdstats.perf-cert1-profile.v1`
- `mdstats.perf-cert1-upstream-authority.v1`
- `mdstats.perf-cert1-profile-assessment.v1`
- `mdstats.perf-cert1-qualification.v1`

