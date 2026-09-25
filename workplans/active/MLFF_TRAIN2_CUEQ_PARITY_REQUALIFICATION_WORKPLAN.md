---
kind: implementation-workplan
protocol_version: 6.4.0
status: active
workplan_id: MLFF-TRAIN2-CUEQ-DOCTOR-SANITY-REPAIR
created_date: 2026-09-24
revision: 43
reviewed_date: 2026-09-25
workplan_review_status: SIMPLIFIED_D4_DOCTOR_REPAIR_PENDING_REAL_HOST_CONFIRMATION
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
