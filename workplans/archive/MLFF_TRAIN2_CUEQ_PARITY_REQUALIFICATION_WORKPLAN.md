---
kind: implementation-workplan
protocol_version: 6.4.0
status: closed-pass
closed_date: 2026-09-25
implementation_evidence_head: 40758c1b447f8e1b149359359515ccd75b237edb
workplan_id: MLFF-TRAIN2-CUEQ-DOCTOR-SANITY-REPAIR
created_date: 2026-09-24
revision: 44
reviewed_date: 2026-09-25
workplan_review_status: SIMPLIFIED_D4_DOCTOR_REPAIR_IMPLEMENTER_TEST_EXECUTION_AUTHORIZED
branch: design/mlff-train2-cueq-parity-requalification
basis_commit: 6573954a76cbd7c264384c7344c874ab70a3470b
highest_affected_domain: D4
d1_d2_change: false
---

# MLFF TRAIN2 CuEq doctor sanity-check repair

## 0. Disposition

The Candidate-1 through Candidate-10 D2 qualification architecture and its
Stage-C/campaign-key machinery are **superseded as unjustified overdesign for
this task**. The complete history remains recoverable in Git through
`87ea7fbd3323fc3e6458c14e473970d20f3174bc`; it is not current implementation authority and must not be
resumed as a continuation plan.

The governed problem is narrow: routine `doctor` rejects an otherwise healthy
FP32 CuEq TRAIN2 realization because its engineering pre-check is tighter than
ordinary observed FP32 backend variability.

This cycle is re-derived as a local D4 repair.

## 1. Protected outcome

Routine `doctor` should catch an unavailable, non-finite, grossly inconsistent,
or discrete-selection-changing CuEq realization without treating the smoke check
as a scientific backend-equivalence proof.

The intended campaign remains:

```toml
[acceleration]
backend = "e3nn"
training_backend = "cueq"
only_cueq = false
require_available = true
```

## 2. Minimal repair

Restore the executable repository surface to the pre-requalification design and
retain the existing small doctor probe.

Change only the coarse FP32 sanity margins:

```text
stable-channel absolute ceiling: 1e-6 -> 1e-5
force self-noise ratio ceiling:   1.25 -> 1.5
```

Keep unchanged:

- CuEq/runtime availability checks;
- selected-head/model/runtime identity checks;
- finite-output failure;
- exact selection-fingerprint agreement;
- catastrophic `Fmax` guard;
- FP64 behavior;
- explicit no-silent-fallback behavior;
- source/DATA6 e3nn behavior.

The repeated metrics may remain as diagnostics because they already exist, but
they carry no D2 scientific meaning and require no statistical proof campaign.

## 3. Explicitly removed scope

This repair does **not** require or authorize:

- Candidate-10 exact keys or qualification records;
- Stage-C triplets, stochastic laws, confidence bounds, or projection oracles;
- target-size selection;
- `prepare`, `cross-validate`, or `train-production` as repair steps;
- CV or production plans;
- campaign progression beyond the doctor command;
- D1/D2/D3 redesign.

## 4. Acceptance

Repository acceptance is bounded to the changed doctor policy and affected
callers/tests.

Real-host acceptance is exactly one operation on the intended RTX 3090 campaign:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml doctor
```

Accept when:

1. genuine runtime/model/resource failures still fail closed;
2. the ordinary FP32 CuEq discrepancy no longer trips the coarse sanity margin;
3. selection remains identical and outputs finite; and
4. doctor exits successfully.

**Stop after doctor.** No campaign `prepare` or training is part of this repair.

## 5. Reopen condition

Reopen beyond D4 only if a future real training run supplies concrete evidence
that CuEq changes a scientifically consequential result, not merely because a
small pre-check metric differs at FP32 roundoff scale.

## 6. Revision-44 implementer test and closeout gate

The code simplification at `d093d0231a8885f935b6affb19dd924296e53c3c` is the complete intended implementation scope. The implementer is now authorized to **test and, only if a test exposes a defect in this bounded repair, make the minimum local correction necessary**. No new numerical method, qualification framework, lifecycle state, authorization registry, campaign key, wrapper, or downstream campaign work is authorized.

### 6.1 Repository checks

Run from the repository root in the MACE environment:

```bash
conda run -n mace python -m pytest -q \
  tests/test_mlff_cueq_train_default1.py \
  tests/test_mlff_cueq_train_noise_normalized_parity.py \
  tests/test_mlff_cueq_train_noise_normalized_parity_specification.py \
  tests/test_mlff_mace_execution_semantics_assembled.py \
  tests/test_mlff_final_gpu1.py
```

Also run:

```bash
conda run -n mace python -m py_compile \
  mdstats/training_data/_campaign_cli_core.py \
  mdstats/training_data/acceleration.py

git diff --check
```

If an affected test fails because it still encodes the superseded Candidate-10/Stage-C design, repair or remove that stale oracle rather than restoring the superseded machinery. If a test exposes an actual regression in the retained doctor behavior, repair the existing owner directly and rerun the focused group.

Do not broaden into unrelated full-suite cleanup. Additional tests are warranted only when a focused failure identifies a concrete affected caller or when the above group cannot honestly establish the changed behavior.

### 6.2 Real-host acceptance

After repository checks pass, run exactly one campaign operation using the intended configuration:

```bash
conda run -n mace python tools/mdstats-mlff-campaign.py \
  --config /home/samjin/QE/lammps-proj/zeolite/05_mace_training/LTA/mh1/FP32/campaign.toml \
  doctor
```

The real-host acceptance target is the RTX 3090 doctor path. Record the actual output/exit status. The expected ordinary FP32 discrepancy should pass the coarse sanity margins while all genuine runtime/model/resource/finiteness/selection guards remain active.

### 6.3 Hard stop

After the real-host doctor command:

- **STOP.**
- Do not run `prepare`.
- Do not run `select-target-size`.
- Do not run `cross-validate`.
- Do not run `train-production`.
- Do not resurrect Candidate-10 or Stage-C machinery.

If repository tests and the real-host doctor pass, update this workplan to PASS/CLOSED and archive it. If doctor still fails, diagnose only the immediate doctor sanity-check failure and keep the repair local unless concrete evidence demonstrates a scientifically consequential CuEq defect.

## 7. Revision-44 execution and closeout — 2026-09-25

### Disposition

**PASS / CLOSED.** The implementation already present at execution head
`40758c1b447f8e1b149359359515ccd75b237edb` includes the complete bounded repair
from `d093d0231a8885f935b6affb19dd924296e53c3c`. No additional product-code
correction was needed. This is a D4-only closeout; no D1-D3 authority changed.

### Repository evidence

Executed from the repository root in Conda environment `mace`:

```bash
conda run -n mace python -m pytest -q \
  tests/test_mlff_cueq_train_default1.py \
  tests/test_mlff_cueq_train_noise_normalized_parity.py \
  tests/test_mlff_cueq_train_noise_normalized_parity_specification.py \
  tests/test_mlff_mace_execution_semantics_assembled.py \
  tests/test_mlff_final_gpu1.py
```

Result: **23 passed, 2 skipped, 0 failed** (268.39 seconds; 1540 warnings).
The skips were the assembled CUDA-specific CuEq TRAIN2 case
(`tests/test_mlff_mace_execution_semantics_assembled.py:973`, reported as
CUDA-specific) and the locked foundation-model preflight
(`tests/test_mlff_final_gpu1.py:75`, locked models not mounted).

```bash
conda run -n mace python -m py_compile \
  mdstats/training_data/_campaign_cli_core.py \
  mdstats/training_data/acceleration.py
git diff --check
```

Both static checks exited 0.

### RTX 3090 doctor evidence

The specified command was:

```bash
conda run -n mace python tools/mdstats-mlff-campaign.py \
  --config /home/samjin/QE/lammps-proj/zeolite/05_mace_training/LTA/mh1/FP32/campaign.toml \
  doctor
```

The first sandboxed invocation stopped before doctor checks because the
sandbox denied creation of the campaign writer lock. The same command was
rerun with the filesystem access required by the user-authorized doctor
operation; it exited **0** and reported **Doctor passed**. The active device
was an NVIDIA GeForce RTX 3090 (23.6 GiB). CuEq was available; the configured
TRAIN2 realization was `cueq_pure`; selected-head and resource checks passed.
The all-pairs sanity result was `passed=True`, with selection identical for
100/100 cross comparisons and self-selection identical for 45/45 comparisons
per backend. Force ratios (RMSE, p99, p99.9) were `(0.954, 1.013, 1.059)`;
cross Fmax was `2.146e-06` against a `2.861e-06` limit. No `prepare`,
`select-target-size`, `cross-validate`, or `train-production` command was run.

The doctor reported that `mace/calculators/mace.py` differed from the locked
source bytes, while the required semantic compatibility probes passed and
doctor continued under semantic source qualification. TorchScript deprecation
warnings were also emitted; neither warning changed the successful doctor
exit or sanity result.

### Closeout learning and lifecycle

No Project Engineering Memory update is warranted for this bounded, task-local
D4 repair. No implementation rework, normative-document update, or upstream
Challenge was required. The plan is archived as historical coordination and
execution evidence; campaign progression remains outside this cycle.
