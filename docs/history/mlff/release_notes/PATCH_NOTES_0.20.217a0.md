# mdstats 0.20.217a0 - TRAIN2 repeatability diagnostic refinement

This release refines the non-authorizing CUEQ repeatability investigation. It does not change the active TRAIN2 FP32 parity tolerance.

- Print complete e3nn-self and CuEq-self `Fmax`, `Frmse`, `Fp99`, `Fp99.9`, and `|dF| > 1e-5` count distributions.
- Retain the existing paired e3nn/CuEq cross-backend statistics.
- Add an isolated deterministic-control subprocess configured before CUDA initialization with `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `torch.use_deterministic_algorithms(True)`, deterministic debug mode `error`, `cudnn.benchmark=False`, and `cudnn.deterministic=True`.
- If deterministic execution is unsupported or fails, print and persist the exact failure without falling back.
- Persist the control result as `mdstats.training-acceleration-deterministic-control-diagnostic.v1`.
- Keep TRAIN2 FP32 parity at `rtol=1e-5, atol=1e-5`; no authorizing criterion changes in this release.
