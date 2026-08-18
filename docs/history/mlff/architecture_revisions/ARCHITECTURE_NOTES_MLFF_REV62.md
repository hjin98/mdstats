# MLFF architecture revision 62 - DATA6 verified-recovery hotfix

**Release:** `mdstats 0.20.195a0`  
**Gate:** `DATA6-RECOVERY-HF1`  
**Dependency-graph schema:** `44`

Revision 62 repairs an orchestration-only defect in `campaign_cli._prepare_sweep()`. The verified DATA6 recovery path uses NumPy to choose a bounded, deterministic calibration subset when the requested sweep is larger than `batch_calibration_stress_structures`, but the module lacked `import numpy as np`. Workstation recovery therefore raised `NameError` before calibration or inference.

The repair restores the import and adds branch-level regression coverage. No scientific or materialization contract changes: model identity, DATA6 descriptors/predictions, source e3nn execution, TRAIN2 CuEq execution, PCA/FPS transforms, DATA7 selection fingerprints, and restart digests retain their existing authorities.
