# mdstats 0.20.122a0 patch notes

## ADAPT-PREC1 — binary learned-model precision

This release implements the first gate of the post-0.20.120 adaptive MLFF revision.

### Production precision contract

New `mdstats-mlff-campaign init` configurations support exactly two learned-model modes:

- `single`: FP32 model, training/autograd/optimizer state, MACE inference, verification,
  committee/member inference, and export;
- `double`: the same learned-model lifecycle in FP64.

Plain `init` remains `single`. The staged `refine` profile and a user-facing `mixed`
model mode are retired for new production campaigns. Generated TOML no longer contains a
`[training.precision]` schedule, and new DATA8/optimizer identities carry no executable
precision schedule. Consequently the historical FP32→FP64 optimizer/EMA promotion path
is unreachable from a newly generated campaign.

### FP64 scientific arithmetic remains invariant

The model dtype does not lower mdstats-owned scientific arithmetic. Critical/global
reductions where the qualified adapter applies, reference fitting, SVD/PCA, geometry,
SSE/RMSE/statistical reductions, observables, regression, and mdstats-owned persistent MD
bookkeeping remain FP64 under both model modes. This is not reported as a mixed model.

### Exact inference dtype

Evaluation, verification, and deployment inherit the learned-model dtype. Evaluation
explicitly disables checkpoint/template dtype casting, so an FP32 checkpoint cannot be
silently promoted and reported as an FP64 model. `double` remains FP64 through the same
surfaces.

### Historical compatibility

Historical staged precision policies/classes remain deserializable for audit, status,
storage, and archive compatibility. A historical `refine` campaign is reported as
read-only staged evidence; production `prepare`, `preflight`, `train`, `evaluate`, and
`verify` fail closed and require the user to choose a new `single` or `double` scientific
identity instead of silently reinterpreting history.

### Qualification

The focused precision/runtime suite passes 43 tests. The broader MLFF
specification/precision/real-MACE subset passes 169 tests with the one known pre-existing
missing `release/mlff_data9a9a_real_mpa0_restart_smoke.json` case deselected. An
additional 31 deployment/evaluation/compatibility tests pass. The full `test_mlff_*`
collection was also started and reached the sandbox time limit without an observed
failure before timeout; qualification therefore relies on the bounded high-value suites
above rather than claiming a completed full-suite run.

`ADAPT-MON1` remains the next implementation gate. Fixed 256-target/512-true-replay
monitor construction and the later adaptive stopping/evaluation redesign are not enabled
by this release.
