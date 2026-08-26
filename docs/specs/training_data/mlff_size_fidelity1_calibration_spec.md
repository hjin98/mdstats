# MLFF SIZE-FIDELITY1 coarse-screen calibration specification

**Status:** current normative calibration contract for the flexible-fidelity target-size runtime; accelerator/scientific production qualification deferred to FINAL-GPU1
**Architecture:** revision 106
**Runtime authority:** `mdstats.size-fidelity1.coarse-screen-calibration.flexible-fidelity.2026-08.v4`

## 1. Scope and ownership

SIZE-FIDELITY1 qualifies whether the current low-fidelity target-size screens
preserve the target-size outcome implied by exhaustive uninterrupted
full-horizon TRAIN2 trajectories. It is a calibration/qualification authority;
it does not select the ordinary campaign target size and it does not own a
separate training schedule.

The current runtime generation has a configurable target-size funnel:

```text
coarse screen:  n1
short screen:   n2
final screen:   n3
full reference: n
```

`n1 < n2 < n3 < n`. `TargetSizeStudyPolicy` owns the three screen boundaries
and the paired-screening seed identity used by the ordinary target-size study;
the separate production/reference budget owns `n` for this calibration. The
generated default is screen `(1, 3, 10)` with production/reference `30`, but
all four values are authenticated configuration, not fixed-generation
assumptions. `SizeFidelityCalibrationPolicy` owns the calibration grid used to
challenge provisional low-fidelity choices.


## 2. Exhaustive trajectory and checkpoint contract

Calibration uses every required coverage-qualified target size for every frozen
calibration seed. Each `(seed, target size)` pair identifies one uninterrupted
TRAIN2 trajectory whose full endpoint is `n`.

The default calibration policy examines:

```text
screening seeds:                   1, 2, 3
coarse endpoint candidates:        3, 4, 5
coarse monitor-size candidates:    128, 256, 512, 1024
coarse equivalence candidates:     1, 2, 4 meV/Angstrom
short-screen endpoint:             n2
final-screen endpoint:             n3
full reference endpoint:           n
```

The first coarse endpoint and first coarse equivalence width must equal the
current production coarse policy. Candidate coarse epochs must precede `n2`.
At least three frozen calibration seeds are required.

For `q` qualified sizes and `s` calibration seeds, the execution plan therefore requires

```text
N_train = q * s
```

uninterrupted training trajectories. The required checkpoint set is the union of the configured coarse candidates, the configured short and final-screen boundaries `n2` and `n3`, and the configured full-reference endpoint `n`.

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

For each calibration seed, the reference ranking is derived from full-horizon
`n` target evidence across every qualified size. The first two rankable
candidates are the **eventual full-reference target finalists** and the first
is the eventual target winner.

For each tested coarse endpoint/monitor/equivalence candidate, SIZE-FIDELITY1 reconstructs:

1. a full-development coarse promotion set;
2. the corresponding coarse-monitor promotion set;
3. the `n2` finalist set produced from coarse survivors;
4. the `n3` production final-screen decision; and
5. the eventual full-`n` reference finalists/winner.

The current hard requirements are:

- coarse-monitor and full-development promotion sets are identical when `require_monitor_decision_equivalence` is enabled;
- both eventual full-reference target finalists survive the coarse screen for every calibration seed;
- both eventual full-reference target finalists survive the short screen for every calibration seed;
- the `n3` final-screen winner and ordering use the production final comparator and agree with the accepted full-reference rule;
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

## 8. Final-screen/reference role coincidence

When `n3 == n`, one physical checkpoint/evaluation serves both roles. The
qualification record nevertheless retains two semantic roles and verifies their
agreement; physical deduplication does not erase the final-screen check.

When `n3 < n`, the final screen and full reference are distinct authenticated
metrics from the same uninterrupted trajectory.

## 9. Persistence and failure behavior

`SizeFidelityCalibrationPolicy`, `SizeFidelityExecutionPlan`, and
`SizeFidelityQualificationReport` use flexible-fidelity schemas. Deserialization
rejects unsupported schema generations and validates content digests.

Qualification fails closed when required evidence is missing or extra, identity/continuity is inconsistent, too few target candidates are valid, hard recall/equivalence requirements fail, or a recommendation does not reference a passing assessment.

The report may be implementation-complete while final accelerator/scientific runtime qualification remains open. Positive CUDA/CuEquivariance and whole-funnel production claims remain part of FINAL-GPU1 and are not implied by bounded CPU/control-plane testing.

## 10. Related current authorities

- `mlff_target_subset_size_study_spec.md` owns the ordinary configurable screen `n1/n2/n3` target-size selection policy and its strict split from production horizon `n`.
- `mlff_perf_p2r_successive_fidelity_execution_spec.md` owns efficient execution/performance realization for the current target-size funnel and calibration parameter surface.
- `mlff_progress_reporting_format_spec.md` owns presentation grammar only.

## References

- Kevin Jamieson and Ameet Talwalkar, "Non-stochastic Best Arm Identification and Hyperparameter Optimization," *Proceedings of Machine Learning Research* 51, 240-248 (2016).
- Charles Spearman, "The Proof and Measurement of Association between Two Things," *American Journal of Psychology* 15, 72-101 (1904).
- Ilyes Batatia et al., "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields," *NeurIPS* 35 (2022).
