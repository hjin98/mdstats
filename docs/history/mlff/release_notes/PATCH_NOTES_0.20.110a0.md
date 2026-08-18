# mdstats 0.20.110a0 patch notes

This release closes MLFF gate PREC3.

## Precision-profile activation

- `single`: FP32 preparation/model/training/evaluation/verification/export and native FP32 profile-controlled critical operations.
- `double`: FP64 throughout.
- `refine`: FP64 non-training stages and 80/20 FP32→FP64 staged training by default, with optimizer/scheduler/EMA continuity from PREC2.

Explicit profiles bind critical precision into training, real-MACE preflight, checkpoint evaluation, and bounded NVE verification. Schedule-free legacy campaigns preserve the prior critical-FP64 behavior.

## Cross-stage evaluation and deployment

EVAL-MF can restore early FP32 and late FP64 refine checkpoints and evaluate both under the configured FP64 evaluation contract. Final target-head exports are converted to the profile deployment dtype with exact state verification and a deployment manifest, so an FP32-stage refine winner still produces a uniformly FP64 deployment model.

## Qualification

Focused and real-MACE 0.3.16/e3nn tests cover single/double inference, staged refine transition/restart, cross-stage FP64 evaluation, exact deployment conversion, and backward compatibility. `cuequivariance` is not available in the release environment; CuEq campaigns remain runtime-gated and must pass the normal real-MACE preflight in a CuEq-enabled environment.
