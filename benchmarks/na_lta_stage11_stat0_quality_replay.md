# Na-LTA Stage 11E-STAT0 real-source replay

- Source: supplied 1,500-step `vasprun.xml`
- Outcome: `degraded_quality`
- Analysis may continue: `true`
- Verdict signature: `2103773604b36f95f7606305e81873bad51e4c73c821f4740145d6d7519a9ad9`
- Realized ensemble consistency: `degraded`
- Cell-matrix relative deviation: `0.000000000000e+00`
- Wall time: 17.021 s
- Warnings: VelocityReconstructionWarning, TrajectoryDegradedQualityWarning

## Ionic temperature

- Degrees of freedom: 501
- Mean: 320.189127 K
- Standard deviation: 14.293740 K
- Effective sample count: 151.164964
- Autocorrelation time: 4.961467 frames
- Observed-span drift: -7.848036 K

## NVE energy diagnostics

- Drift: -0.204552395701 eV/ps
- Drift per atom: -0.001217573784 eV/(atom ps)
- Detrended standard deviation: 0.003252913531 eV
- Maximum frame-to-frame jump: 0.000011892917 eV/atom
- Energy identity residual: 1.000012161967e-08 eV

## Verdict reasons

- `quality.ediff`
- `quality.lreal`
- `quality.temperature_stability`
- `quality.nve_energy_drift`

## Interpretation

The trajectory remains structurally analyzable. The measurable NVE energy drift and
soft numerical-control warnings are retained as degraded-quality metadata. STAT0 does
not select a production interval or authorize a PMF.
