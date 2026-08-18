# MLFF architecture revision 56

**Release:** `mdstats 0.20.189a0`  
**Gate:** CUEQ-PHASE1 implementation  
**Date:** 2026-08-15

Revision 56 implements the training-only pure-CuEq qualification authority while preserving the final-release-only GPU policy.

## Decisions

- Source-foundation inference, DATA6, pseudolabel generation, source-baseline evaluation, and their cache identities remain original MH-1/`omat_pbe`/e3nn.
- Only training from the EXTRACT1-qualified selected-head checkpoint may vary to `cueq_pure`.
- Every e3nn/CuEq pair binds the same CUEQ-DEP1 runtime digest and enumerates the scientific/training inputs that must remain identical.
- The short screen is frozen to 5-10 epochs (default 8) and is non-authorizing by itself.
- Production training authorization additionally requires at least one representative full paired trajectory.
- Final checkpoint bytes need not match. Acceptance is based on existing replay, finiteness, checkpoint-admissibility, extraction, EVAL2, and available physical-verification authorities.
- Metric deltas and GPU performance telemetry are evidence only; no existing scientific tolerance is relaxed.
- A CUEQ-PHASE1 pass authorizes only phase-separated e3nn-source + pure-CuEq-training execution. It cannot authorize source CuEq, DATA6 CuEq, or a generated-default change.
- FINAL-GPU1 preflight advances to v3 and exposes the CUEQ-PHASE1 schema/deferred state without running the GPU campaign during development.

## Qualification state

The phase-1 schema, pair reducer, gate reducer, serialization/tamper protection, deferred-state tooling, and final-GPU handoff are CPU/control-plane qualified. Positive runtime and paired short/full trajectories remain deferred to FINAL-GPU1 by design.

## Next gate

CUEQ-PHASE2 implementation is next as an **optional** selected-head source-execution/DATA6 accelerator qualification. It must not be allowed to weaken the original-MH-1/e3nn source authority or the CUEQ-PHASE1 separation boundary.
