# CUEQ-REPEAT1-DIAG2: TRAIN2 FP32 Repeatability Diagnostic Refinement

## Purpose

Refine the non-authorizing revision-83 diagnostic after MPA-0/default measurements showed same-backend e3nn and CuEq `Fmax` repeatability envelopes extending above the paired e3nn/CuEq envelope. No parity or scientific-convergence tolerance changes in this gate.

## Ordinary execution-path statistics

The existing 10-repeat e3nn/pure-CuEq probe continues to run on the exact deterministic doctor corpus and selected TRAIN2 checkpoint/head. In addition to paired cross-backend statistics, run-1-versus-runs-2-through-10 self comparisons now record and print `Fmax`, `Frmse`, absolute-error `Fp99`, `Fp99.9`, and count of force components with absolute difference greater than `1e-5`, independently for e3nn-self and CuEq-self.

## Isolated deterministic control

Doctor launches a fresh subprocess over geometry-only copies of the same probe structures. Before CUDA initialization, the worker receives `CUBLAS_WORKSPACE_CONFIG=:4096:8`, enables `torch.use_deterministic_algorithms(True)`, sets deterministic debug mode to `error`, sets `torch.backends.cudnn.benchmark=False`, and sets `torch.backends.cudnn.deterministic=True`.

If the complete e3nn/CuEq path supports these controls, the worker returns a second full repeatability record and doctor prints it with `[DIAG-DET]`. If any operation is unsupported or fails, doctor prints and persists `unsupported_or_failed` with the exception. There is no fallback.

## Authority

The ordinary record remains the repeatability-diagnostic v1 schema; the deterministic control uses its own deterministic-control-diagnostic v1 schema. Both are non-authorizing. TRAIN2 FP32 parity remains `rtol=1e-5, atol=1e-5` pending interpretation of the refined workstation evidence.
