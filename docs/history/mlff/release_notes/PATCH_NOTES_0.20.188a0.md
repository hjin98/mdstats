# mdstats 0.20.188a0

## CUEQ-DEP1 accelerator-runtime freeze

- Add content-addressed `CueqDep1RuntimeRecord.v1` and `CueqDep1Policy.v1`.
- Require CuEq core, PyTorch frontend, and CUDA-ops layers; add CUDA-13 ops-distribution discovery alongside cu12/cu11.
- Freeze installed distribution metadata/RECORD identities, imported module bytes, CUDA hardware/runtime, cuDNN, determinism/TF32/matmul settings, and relevant environment variables.
- Keep OpenEquivariance optional for the first pure-CuEq training phase.
- Add standalone CUEQ-DEP1 capture tooling and embed the same runtime authority in FINAL-GPU1 preflight schema v2.
- Preserve fail-closed behavior: missing CuEq/CUDA produces negative evidence and never silently falls back to another backend.
- Advance the canonical MLFF architecture to revision 55 and dependency-graph schema 37.

No GPU qualification is performed in this release. CUEQ-DEP1 final runtime qualification and all CuEq numerical/training evidence remain scheduled for FINAL-GPU1.
