# mdstats 0.20.175a0 patch notes

## DYN-VERIFY2 short structural dynamics

This release implements the final pre-selection physical qualification gate in the post-0.20.162 MLFF revision.

### What changed

- Added immutable `DynVerifyPolicy`, `DynVerifyPlan`, `DynCaseMetric`, `DynVerifyRunRecord`, and `DynVerifyCampaignRecord` authorities.
- DYN-VERIFY2 consumes only RELAX-VERIFY1-qualified candidates and executes the exact DEPLOY-VERIFY1 ML-IAP artifact with the same authenticated LAMMPS executable and arguments.
- The default common rollout grid uses up to two correlation-balanced DFT-relaxed bases at 300 K and 800 K. Each case uses the same deterministic velocity seed across candidates.
- The first-release integration protocol is 0.5 fs timestep, 400-step/0.2 ps Langevin NVT with 100 fs damping, followed by 2000-step/1.0 ps NVE, sampled every 10 steps/5 fs. An explicit LAMMPS `run 0` frame is written before velocity creation so the structural reference is the exact common DFT-relaxed geometry.
- Numerical hard gates require finite dynamics, absolute NVE energy drift <= 0.026 eV/atom/ps, minimum pair distance >= 0.8 A, maximum force <= 100 eV/A, NVT mean temperature within 20%, and NVE mean temperature within 30% of the target.
- Persistent protected-structure gates monitor frozen reference-bond loss, new protected bonds, RMS/max protected displacement, bond RMSE, and angle RMSE. Damage must persist for 10 consecutive 5-fs samples (50 fs) before it becomes a hard structural failure, preventing one thermal flicker from rejecting a candidate.
- Generated LTA campaigns preserve the `framework` group; mobile alkali motion therefore does not count as framework destruction.
- All common base/temperature cases are hard gates. Numerical stability cannot compensate for persistent structural damage, and metrics are not averaged across cases to hide one broken framework.
- Completed DYN evidence authenticates the RELAX/DEPLOY authority, ML-IAP bytes, exact LAMMPS executable bytes and launch arguments, policy/case membership, trajectory/log bytes, and all reduced metrics.
- During TARGET-DATA2D Stage C, DYN-VERIFY2 binds the complete DEPLOY->PES->RELAX->DYN physical pass/fail chain to both target-size finalists and allows the existing reducer to resolve `N_target` or report bounded-ladder non-convergence. Production-size candidates remain waiting for SELECT2 after DYN.

### Compatibility

Historical campaigns and all pre-TRAIN2 policy generations keep their original semantics. DYN-VERIFY2 is part of the new TRAIN2 verification authority only. No historical checkpoint, selection score, or physical-verification record is reinterpreted.

### Testing

The gate includes adversarial tests for transient versus persistent topology damage, NVE energy drift, temperature failure, common-plan determinism, serialization/restart identity, Stage-C handoff, and a fake deterministic LAMMPS rollout/parser path. Real production DYN evidence still requires the campaign's configured DEPLOY-authenticated LAMMPS/ML-IAP runtime; no real deployment rollout is fabricated by the release tests.
