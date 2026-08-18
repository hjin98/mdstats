# MLFF architecture revision 42 - post-CERT DATA6 VRAM hardening and phase-separated CuEq qualification

This architecture-only revision records the post-CERT optimization plan added to
`docs/arch_manuals/mlff_training_data_architecture.{md,pdf}` on 2026-08-15. It does not change runtime behavior until the corresponding gates are implemented.

The current production authority is **MACE-MH-1 / `omat_pbe` / e3nn** for source-foundation inference, DATA6, pseudolabel generation, evaluation, and the first complete campaign baseline. The earlier CONFIG1/CERT1 language naming CuEq as the generated default is retained only as historical implementation context. Real RTX-3090 parity evidence for the original six-head MH-1 checkpoint remains fail-closed; the near-parity result for the EXTRACT1-derived single-head `omat_pbe` checkpoint motivates a later training-only accelerator experiment but does not authorize CuEq source inference.

The frozen gate order is:

1. `VRAM1` - advance DATA6 capacity evidence to workload-aware v2; calibrate the derivative-bearing production workload, clean calibration CUDA cache, measure allocated/reserved/driver-visible memory, use a deterministic stress-oriented calibration corpus, re-clamp against live headroom, select the smallest near-max-throughput safe batch, and persist OOM-derived safe caps without changing scientific outputs.
2. `E3NN-BASELINE` - complete and freeze one authoritative full MH-1/`omat_pbe`/e3nn campaign as the scientific/performance comparator.
3. `CUEQ-DEP1` - freeze the exact CuEquivariance runtime/dependency/GPU identity required to reproduce accelerator qualification; pure CuEq is sufficient for the first training experiment.
4. `CUEQ-PHASE1` - keep source inference/DATA6/pseudolabel/evaluation on original MH-1/e3nn while independently qualifying pure-CuEq training from the exact EXTRACT1-derived single-head checkpoint using paired short and representative full training trajectories.
5. `CUEQ-PHASE2` - optional later qualification of the derived single-head CuEq realization for source-execution/DATA6 acceleration, with explicit scientific-foundation versus executable-realization identity and a deterministic stratified development corpus.
6. `PERF-CERT1` - compare e3nn baseline, e3nn+VRAM1, phase-separated CuEq training, and any qualified CuEq source-execution path using both scientific decisions and end-to-end performance before any generated-default policy change.

Binding invariants are unchanged: no parity tolerance is relaxed to recover acceleration; direct six-head MH-1/CuEq source inference remains unauthorized on the recorded runtime; locked-test evidence is not used to tune accelerator policy; pseudolabel/source-potential lineage remains exact; and successful CuEq training never retroactively validates CuEq source inference.

Canonical gate definitions and acceptance criteria are in the final post-CERT1 optimization section of `docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`.

> Supersedence note (2026-08-15): this shorter roadmap is retained as historical architecture evidence. `ARCHITECTURE_NOTES_MLFF_REV43.md` and the final post-major-revision optimization section of the canonical manual supersede its gate ordering.
