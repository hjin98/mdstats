# mdstats 0.20.172a0 patch notes

## Gate

`DEPLOY-VERIFY1` - selected-checkpoint, target-head export, and ML-IAP/LAMMPS deployment numerical parity.

## Implemented

- Added immutable DEPLOY-VERIFY1 policy, probe-set, channel-comparison, LAMMPS run-0, per-run, and campaign authority records.
- Restrict deployment candidates to final-development EVAL2 winners. During target-size Stage C, only the two screening-seed finalists are verified; after `N_target` selection, only selected-size final-development production seeds are candidates. CV-fold models remain evidence-only.
- Select at most 16 probe configurations by deterministic correlation-block round-robin so independent trajectory/source blocks receive one representative before any block receives a second. Probe membership binds EVAL2 role/artifact identities, ordered frame UIDs, block IDs, and configuration indices.
- Reconstruct the exact EVAL2-selected raw checkpoint with its authenticated DATA8 configuration and compare predictions from the explicit target head against the exported target-only MACE model. The target-head export transform has its own recomputed fail-closed identity.
- Convert the exact target-only model to ML-IAP and invoke the configured LAMMPS executable with `pair_style mliap unified ... 0` and `run 0` for every probe. Energy and forces, plus stress for fully periodic supported cases, are compared back to target-only Python MACE predictions.
- Default parity tolerances are `rtol=1e-5, atol=1e-6` for float32 and `rtol=1e-9, atol=1e-10` for float64. These are configuration-controlled and identity-bearing.
- Freeze selected checkpoint/model bytes, target-only bytes/export identity, ML-IAP bytes/export digest, probe identity, LAMMPS executable absolute path and SHA-256, launch arguments, and run-0 prediction digest. Any changed authority or deployment bytes force a fresh check.
- TRAIN2 `verify` now executes DEPLOY-VERIFY1. On success it intentionally leaves the overall verification stage `WAITING` for PES-VERIFY1; absence/failure of the configured ML-IAP/LAMMPS runtime fails closed rather than accepting Python-only parity.
- Synchronized generated campaign configuration, `campaign.toml.example`, GUIDE text, README, public API, version metadata, architecture manual, and EVAL2/DEPLOY specification tests.

## Intentionally deferred

- PES-VERIFY1 finite-displacement local-PES/restoring-force qualification.
- RELAX-VERIFY1 zero-K topology/geometry fidelity.
- DYN-VERIFY2 short structural dynamics qualification.
- Physical completion of TARGET-DATA2D Stage C, TARGET-DATA2E final corpus materialization, and SELECT2 production publication.

## Qualification

- Gate/core regression batch: 130 passed across DEPLOY-VERIFY1, EVAL2, TRAIN2A/B, TARGET-DATA2A-E, FOUNDATION-AUDIT1, and DATA5 role lineage.
- Campaign/deployment regression batch: 120 passed, 1 expected skip across campaign CLI/performance, checkpoint materialization, DATA6/DATA8, prediction caching, deployment and production-gate integrity.
- Real ML-IAP/LAMMPS parity is campaign-time evidence and was not fabricated in this container; the implementation is unit/regression-qualified with a mocked run-0 parser contract and fails closed when the configured executable is unavailable.
