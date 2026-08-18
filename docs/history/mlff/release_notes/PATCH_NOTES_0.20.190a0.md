# mdstats 0.20.190a0

- Implement CUEQ-PHASE2 as an optional selected-head pure-CuEq source-execution/DATA6 qualification authority while preserving original six-head MH-1/`omat_pbe` as the scientific source identity.
- Freeze the exact MH-1 source checkpoint, source-potential digest, EXTRACT1 selected-head checkpoint, and EXTRACT1 qualification digest in `CueqPhase2Policy.v1`.
- Add deterministic stratified development-corpus evidence with an explicit hard guard against locked-test tuning.
- Reuse the existing `MaceAccelerationParityRecord` for energy/force/stress/descriptor numerical acceptance; add foundation-difficulty, frozen-transform PCA/FPS, and exact DATA6/DATA7 selection parity without relaxing any tolerance.
- Content-address the selected-head/CuEq execution realization and require explicit scientific-source plus execution-realization lineage for caches and optional pseudolabel/E0 generation.
- Make pseudolabel authorization conditional on explicit value/E0 parity evidence; a source/DATA6 pass alone does not authorize pseudolabel execution.
- Keep direct six-head CuEq execution and generated-default changes permanently unauthorized at this gate.
- Add `tools/qualify_mlff_cueq_phase2.py` and advance FINAL-GPU1 preflight to v4 with independent CUEQ-PHASE1 and CUEQ-PHASE2 deferred states.
- Advance canonical MLFF architecture to revision 57 and dependency-graph schema 39. Positive accelerator evidence remains deferred to FINAL-GPU1; PERF-CERT1 is the next implementation gate.
