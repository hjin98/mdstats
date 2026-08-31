# MLFF ADAPT-VERIFY1 adaptive final verification specification

Status: implemented in `mdstats 0.20.127a0`.

## Purpose

ADAPT-VERIFY1 closes the adaptive campaign's deployment-selection loop. It consumes only the
fully evaluated admissible candidates already purchased by ADAPT-EVAL1, verifies them in
authoritative full-score order, and publishes exactly one target-head model: the first candidate
that passes the bounded deployment/NVE gates.

It performs no new target/replay accuracy evaluation and does not restore EVAL-MF screening.

## Inputs and ordering

The authoritative parent is `AdaptiveFullEvaluationRecord`. Only its `admissible_candidates` enter
verification. Their order is the deterministic EVAL1 full-score order:

1. lower weighted full target/replay force score;
2. lower target force RMSE;
3. lower replay force RMSE;
4. lower original finalist rank;
5. stable checkpoint SHA-256.

By default `[verification].fallback_to_next_full_evaluation_candidate = true`.

The best candidate is verified first. If it fails a hard verification condition, the next already
fully evaluated admissible candidate is verified. Verification stops immediately at the first pass.
If fallback is disabled, failure of the best candidate is terminal.

## Verification matrix and hard gates

Each attempted candidate receives the complete configured verification matrix:

- every `[verification].structures` entry;
- every `[verification].temperatures_kelvin` value;
- the configured timestep, NVE step count, sampling interval, and velocity seed.

A candidate passes only if every case satisfies:

- finite model/trajectory observables;
- absolute energy drift <= `maximum_energy_drift_ev_per_atom_per_ps`;
- minimum pair distance >= `minimum_pair_distance_angstrom`;
- maximum force <= `maximum_force_ev_per_angstrom`.

A failure is a hard rejection of that deployment candidate. Verification does not modify its EVAL1
accuracy score or retroactively change RANK1/STOP1 evidence.

## Precision boundary

`[campaign].precision_profile` controls only learned-model arithmetic:

```text
single -> FP32 MACE inference and FP32 deployed learned-model bytes
double -> FP64 MACE inference and FP64 deployed learned-model bytes
```

There is no mixed or refine mode. No FP32 candidate is promoted to FP64 during verification or
export and no FP64 candidate is demoted.

mdstats-owned scientific arithmetic remains hard-coded FP64 in both modes, including persistent MD
state, energy/observable accumulation, drift regression, and reporting/statistical reductions.
The verification record exposes both `model_inference_dtype` and `scientific_analysis_dtype`.

## Target-head materialization and publication

An EVAL1 winner may be a cross-validation fold run or a final-development run. Historical committee
export requires final-development runs and therefore cannot be used to manufacture adaptive
selection semantics.

For each candidate, mdstats:

1. authenticates the frozen checkpoint or its qualified storage capsule;
2. reconstructs the exact checkpoint model without dtype-template casting;
3. extracts the target head into an internal verification-only artifact using the selected learned-
   model dtype;
4. runs bounded NVE on those exact target-head bytes;
5. deletes failed candidate model materializations; and
6. atomically promotes the exact passing bytes into `models/`.

The final deployed model is therefore byte-identical to the artifact that passed NVE. There is no
post-verification re-export or dtype conversion.

Adaptive production publishes a single `AdaptiveDeploymentModelRecord`. It does not fabricate a
legacy committee around a fold winner. Historical committee evidence remains readable for
historical evaluator paths.

## Evidence and restart semantics

Each NVE case has a content-addressed identity containing at least:

- adaptive full-evaluation candidate identity;
- checkpoint SHA-256 and target-head model SHA-256;
- verification structure SHA-256;
- temperature, timestep, NVE steps, sampling interval, and velocity seed;
- device and learned-model inference dtype;
- invariant FP64 scientific-analysis dtype;
- acceleration/critical-precision policy identities; and
- verification runtime identity.

Authenticated completed cases are reused after interruption.

`AdaptiveVerificationCandidateRecord` freezes one candidate's case digests, model bytes, full score,
full target/replay RMSE, dtype boundary, pass/fail outcome, and hard rejection reasons.

`AdaptiveVerificationRecord` freezes the score-ordered attempted candidate sequence. A successful
record must end at exactly one first passing candidate; evidence after a passing candidate is invalid.

`AdaptiveDeploymentModelRecord` binds the published model bytes to the passing full-evaluation
candidate and source checkpoint.

`AdaptiveProtocolFreezeRecord` binds the production qualification, campaign, full target and true-
replay domains, EVAL1 record, VERIFY1 record, deployment model, selected checkpoint, model dtype,
and invariant FP64 analysis dtype.

## Required final report content

`results/production-verification.json` publishes at least:

- selected EVAL1 finalist rank/batch and run/checkpoint provenance;
- common full target force RMSE;
- common true-replay force RMSE;
- target/replay weights, thresholds, and weighted full score;
- foundation replay RMSE and absolute/fractional degradation diagnostics;
- retained target energy, focus-force, stress, and worst-condition metrics;
- full target/replay domain identities and counts;
- every attempted candidate and its verification case results/rejection reasons;
- verification thresholds and fallback count;
- acceleration/backend identity;
- learned-model inference dtype and FP64 scientific-analysis dtype; and
- exact published model path and SHA-256.

## Acceptance criteria

ADAPT-VERIFY1 is qualified only if:

1. candidates are tried strictly in authoritative EVAL1 full-score order;
2. fallback occurs only after a hard verification failure and only among already fully evaluated
   admissible candidates;
3. no target/replay reevaluation is introduced by fallback;
4. completed NVE cases are restart-reused under exact identities;
5. failed candidate artifacts are not published;
6. the first passing candidate's exact verified target-head bytes are atomically published;
7. `single|double` model dtype is preserved through verification and deployment;
8. mdstats-owned state/analysis remains FP64;
9. a fold-run candidate may be deployed without synthetic committee/final-run substitution; and
10. historical committee/refine/EVAL-MF evidence cannot silently determine an adaptive winner.
