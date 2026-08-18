# mdstats 0.20.79a0: legacy training-campaign digest migration

## Problem

Training jobs completed under earlier 0.20.7x revisions can leave a valid
`training_campaign` record whose nested campaign-policy payload uses the older
v2 schema. 0.20.77a0 introduced the v3 policy schema for method-specific seeds
and fold counts. Loading the old policy into the current object is valid, but
re-serializing it changes the parent plan digest. Earlier code compared only
against that newly computed digest and therefore raised:

```text
TrainingDataSerializationError: Training-campaign plan digest mismatch.
```

## Fix

`TrainingCampaignPlan.from_dict` now accepts either:

- the canonical digest of the current in-memory plan; or
- the canonical digest of the exact serialized legacy plan payload.

The second path remains fail-closed. The stored parent digest must match the
exact legacy payload, and nested campaign-policy and run-plan records must still
pass their independent schema and digest checks. A changed field with the old
digest is rejected.

On the first successful `evaluate`, the verified legacy plan is rewritten once
in the current canonical schema. This migration does not alter run IDs, DATA8
job identities, checkpoints, execution records, or completed model bytes.

## Resume

Install 0.20.79a0 and rerun `evaluate`. Do not rerun `prepare`, `preflight`, or
training solely for this migration.
