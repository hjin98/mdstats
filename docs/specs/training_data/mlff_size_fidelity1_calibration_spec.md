# MLFF SIZE-FIDELITY1 coarse-screen calibration specification

**Status:** current normative calibration contract for the fixed target-size-v5 runtime; accelerator/scientific production qualification deferred to FINAL-GPU1
**Architecture:** revision 105
**Runtime authority:** `mdstats.size-fidelity1.coarse-screen-calibration.target-size-v5.2026-08.v2`

## 1. Scope and ownership

SIZE-FIDELITY1 qualifies whether the current low-fidelity target-size screens preserve the target-size outcome implied by exhaustive uninterrupted target-size-v5 training trajectories. It is a calibration/qualification authority; it does not select the ordinary campaign target size and it does not own a separate training schedule.

The current runtime generation has a fixed target-size funnel:

```text
coarse screen:  epoch 3
short screen:   epoch 10
final decision: epoch 30
```

`TargetSizeStudyPolicy` owns those current production boundaries and the paired-screening seed identity used by the ordinary target-size study. `SizeFidelityCalibrationPolicy` owns the calibration grid used to challenge the provisional low-fidelity choices. SIZE-FIDELITY1 consumes authenticated target-only endpoint evidence and reports whether a calibration candidate satisfies the hard survivor-fidelity requirements.


## 2. Exhaustive trajectory and checkpoint contract

Calibration uses every required coverage-qualified target size for every frozen calibration seed. Each `(seed, target size)` pair identifies one uninterrupted TRAIN2 trajectory whose current full endpoint is epoch 30.

The default calibration policy examines:

```text
screening seeds:                   1, 2, 3
coarse endpoint candidates:        3, 4, 5
coarse monitor-size candidates:    128, 256, 512, 1024
coarse equivalence candidates:     1, 2, 4 meV/Angstrom
short-screen endpoint:             10
full/final reference endpoint:     30
```

The first coarse endpoint and first coarse equivalence width must equal the current production target-size-v5 coarse policy. Candidate coarse epochs must precede epoch 10. At least three frozen calibration seeds are required.

For `q` qualified sizes and `s` calibration seeds, the execution plan therefore requires

```text
N_train = q * s
```

uninterrupted training trajectories. The required checkpoint set is the union of the configured coarse candidates with epochs 10 and 30.

## 3. One inference authority, multiple monitor views

Each required checkpoint is evaluated once on the authenticated full-development target role. Coarse monitor metrics are deterministic reductions of that full-role prediction authority rather than independent model-inference jobs.

The execution plan requires:

```text
monitor_views_derived_from_full_predictions = true
```

and rejects a plan that would multiply inference solely because several monitor cardinalities are being compared. Full-development and coarse-monitor evidence at the same epoch must authenticate the same physical checkpoint.

## 4. Identity and continuity

Every metric authenticates foundation identity, training-policy identity, schedule identity, training-run identity, checkpoint identity, evaluation-role identity, and target-evaluation identity.

For one `(seed, target size)`:

- all checkpoint/evaluation roles must identify one uninterrupted training-run digest;
- all roles at one epoch must agree on the checkpoint digest;
- the calibration matrix must exactly equal the frozen scientific grid; missing or extra scientific keys fail closed;
- evaluation-role identity may not drift across seeds, sizes, or epochs.

A restart or persistence realization may change storage mechanics but may not change the scientific trajectory or checkpoint ancestry.

## 5. Reference finalists and hard survivor fidelity

For each calibration seed, the current reference ranking is derived from target evidence at epoch 30 across every qualified size. The first two rankable candidates are the **eventual 30-epoch target finalists** and the first is the eventual target winner.

For each tested coarse endpoint/monitor/equivalence candidate, SIZE-FIDELITY1 reconstructs:

1. a full-development coarse promotion set;
2. the corresponding coarse-monitor promotion set;
3. the epoch-10 finalist set produced from coarse survivors; and
4. the eventual epoch-30 reference finalists/winner.

The current hard requirements are:

- coarse-monitor and full-development promotion sets are identical when `require_monitor_decision_equivalence` is enabled;
- both eventual epoch-30 target finalists survive the coarse screen for every calibration seed;
- both eventual epoch-30 target finalists survive the epoch-10 screen for every calibration seed;
- the largest target-size boundary is not falsely removed when it is an eventual finalist;
- one uninterrupted trajectory identity is preserved.

The default required coarse-finalist recall and short-finalist recall are both `1.0`. A candidate that misses an eventual finalist fails; an attractive average ranking cannot compensate for that failure.

Winner recall is recorded, but finalist recall is the stronger current hard scientific criterion.

## 6. Diagnostics are not acceptance substitutes

SIZE-FIDELITY1 records diagnostics including Spearman rank correlation and seed-to-seed survivor sets. These are useful for understanding fidelity but are not substitutes for the hard survivor requirements.

A high Spearman correlation may coexist with the one false elimination that matters scientifically. Accordingly, rank correlation remains diagnostic only.

## 7. Deterministic recommendation

Among calibration candidates satisfying every hard requirement, recommendation prefers:

1. the earliest faithful coarse endpoint;
2. then the smallest faithful coarse monitor;
3. then the smallest passing tested equivalence width at or above the current production default.

A failed candidate does not become acceptable by weakening the frozen recall/equivalence requirements. Scientific-policy revision requires an explicit design/qualification change.

## 8. Current fixed-generation role coincidence

In the current runtime, the third target-size screen and the exhaustive SIZE-FIDELITY1 reference endpoint are both epoch 30. One epoch-30 checkpoint therefore serves both roles physically.

That equality is a property of the current fixed target-size-v5 generation. It is part of this generation's implemented calibration contract rather than a separate second-training requirement.

## 9. Persistence and failure behavior

`SizeFidelityCalibrationPolicy`, `SizeFidelityExecutionPlan`, and `SizeFidelityQualificationReport` use target-size-v5 v2 schemas. Deserialization rejects unsupported schema generations and validates content digests.

Qualification fails closed when required evidence is missing or extra, identity/continuity is inconsistent, too few target candidates are valid, hard recall/equivalence requirements fail, or a recommendation does not reference a passing assessment.

The report may be implementation-complete while final accelerator/scientific runtime qualification remains open. Positive CUDA/CuEquivariance and whole-funnel production claims remain part of FINAL-GPU1 and are not implied by bounded CPU/control-plane testing.

## 10. Related current authorities

- `mlff_target_subset_size_study_spec.md` owns the ordinary fixed `3/10/30` target-size selection policy.
- `mlff_perf_p2r_successive_fidelity_execution_spec.md` owns efficient execution/performance realization for the current target-size funnel and calibration parameter surface.
- `mlff_progress_reporting_format_spec.md` owns presentation grammar only.

## References

- Kevin Jamieson and Ameet Talwalkar, "Non-stochastic Best Arm Identification and Hyperparameter Optimization," *Proceedings of Machine Learning Research* 51, 240-248 (2016).
- Charles Spearman, "The Proof and Measurement of Association between Two Things," *American Journal of Psychology* 15, 72-101 (1904).
- Ilyes Batatia et al., "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields," *NeurIPS* 35 (2022).
