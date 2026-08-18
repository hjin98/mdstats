# mdstats 0.20.195a0 - DATA6 verified-recovery hotfix

## Fixed

A workstation `prepare` run that could not directly reuse the compact DATA6 model-sweep checkpoint entered verified recovery and crashed at calibration-structure sampling with:

```text
NameError: name 'np' is not defined
```

`campaign_cli._prepare_sweep()` uses `np.linspace(..., dtype=np.int64)` when the requested DATA6 sweep contains more frames than the bounded calibration stress sample. The module was missing `import numpy as np`. Revision 62 restores that import.

## Scientific impact

None. The exception happened before batch-capacity calibration and before new DATA6 inference. Descriptor/prediction definitions, DATA6/DATA7 selection authority, foundation model identity, source e3nn policy, TRAIN2 CuEq policy, and restart/content digests are unchanged. Existing valid DATA6 artifacts remain reusable.

The TorchScript deprecation messages printed immediately before the traceback are MACE/PyTorch compatibility warnings and are not causal.

## Regression

The campaign performance suite now forces the checkpoint-recovery path with ten requested frame UIDs and an eight-structure calibration cap. The test verifies the deterministic `np.linspace` sample and stops only after reaching provider batch calibration.
