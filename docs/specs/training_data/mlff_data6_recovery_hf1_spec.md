# DATA6-RECOVERY-HF1 specification

**Release:** `mdstats 0.20.195a0`  
**Architecture revision:** `62`  
**Graph schema:** `44`

## Failure

When a DATA6 model-sweep checkpoint is absent, invalid, or not directly reusable, `_prepare_sweep()` enters verified recovery. For `N_requested > batch_calibration_stress_structures`, it selects a deterministic calibration subset with `np.linspace(..., dtype=np.int64)`. `campaign_cli.py` must therefore import NumPy as `np`.

## Acceptance

1. `campaign_cli` exposes the NumPy module as `np`.
2. A recovery test with ten requested frames and an eight-frame stress cap reaches batch-capacity calibration without `NameError`.
3. The deterministic sample remains `f0, f1, f2, f3, f5, f6, f7, f9` for that fixture.
4. No DATA6 scientific, selection, acceleration, or restart identity changes.
5. Existing TorchScript deprecation warnings remain warning-only and must not be misclassified as the crash.
