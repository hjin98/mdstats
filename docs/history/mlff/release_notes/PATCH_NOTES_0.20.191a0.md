# mdstats 0.20.191a0

## MLFF PERF-CERT1

- Add the PERF-CERT1 end-to-end scientific/performance certification and recommendation authority.
- Freeze the optimized original MH-1/`omat_pbe` e3nn path as the authoritative comparison baseline.
- Keep CUEQ-PHASE1 training authorization and optional CUEQ-PHASE2 selected-head source/DATA6 authorization independent and content-addressed.
- Add complete-profile timing/throughput/VRAM/OOM/backoff telemetry for preparation, TARGET-DATA2B/2C, DATA6, TRAIN2, EVAL2, and total wall time.
- Require exact frozen hard-decision and target/DATA6/DATA7 selection identity; allow different final checkpoint bytes when existing scientific authorities still pass.
- Require a strictly positive end-to-end speedup before an accelerated profile can be recommended.
- Reject locked-test tuning regardless of measured speedup.
- Preserve `generated_default_change_authorized=false`; a later explicit policy revision is required for any generated-default migration.
- Add `tools/qualify_mlff_perf_cert1.py` for deferred evidence, assembly, and validation without launching GPU work.
- Advance FINAL-GPU1 preflight to v5 with an independent PERF-CERT1 state.
- Advance canonical MLFF architecture to revision 58 and dependency-graph schema 40. Positive accelerator execution remains deferred to FINAL-GPU1.
