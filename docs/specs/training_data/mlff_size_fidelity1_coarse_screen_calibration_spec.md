---
title: "MLFF SIZE-FIDELITY1: Coarse-Screen Fidelity Calibration"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
  - |
    \usepackage{booktabs}
  - |
    \usepackage{longtable}
  - |
    \usepackage{array}
---

# Status and authority

**Gate:** `SIZE-FIDELITY1`  
**Authority implementation release:** `mdstats 0.20.183a0`  
**Authority class:** scientific qualification of `SIZE-HALVE1`; no performance credit  
**Implementation:** calibration authority and execution plan implemented  
**Scientific closure:** deferred to `FINAL-GPU1` on the final release package; supplied foundation checkpoints are now available

`SIZE-HALVE1` corrected target-size selection to

$$
\text{hard coverage}
\rightarrow
\text{coarse learning screen}
\rightarrow
\text{10-epoch screen}
\rightarrow
\text{30-epoch decision}.
$$

`SIZE-FIDELITY1` determines whether the coarse screen is scientifically faithful enough to eliminate target-size candidates. It does **not** assume that a low-epoch ranking is reliable merely because it is cheap.

The implementation authority is

```text
mdstats.size-fidelity1.coarse-screen-calibration.2026-08.v1
```

and is implemented in `mdstats.training_data.size_fidelity`.

`mdstats 0.20.184a0` changes qualification scheduling, not the calibration science. The supplied MACE-MH-1 and MACE-MPA-0-medium checkpoints match the previously locked hashes. GPU execution is deliberately deferred to `FINAL-GPU1`, so this gate remains a final-release blocker while PERF-P2R/PERF-P3 implementation proceeds against the full parameter grid. No GPU-derived default is authoritative before that final run.

# 1. Scientific question

Hard coverage establishes admissibility, not sampling sufficiency. A small nested subset can span every required range and stratum while remaining too sparse inside important regions of configuration space. The target-size funnel therefore uses observed learning behavior after coverage admission.

The resulting low-fidelity decision is useful only if it preserves the candidates that matter at the full training budget. The hard question is consequently a **survivor-recall** question:

> If every coverage-qualified size had been trained to 30 epochs, would the proposed coarse and 10-epoch screens have retained both target-side finalists that the 30-epoch evidence would identify?

Global rank correlation is not sufficient. One wrong elimination can invalidate the final target-size decision even when the overall ranking correlation is high.

# 2. Exhaustive calibration design

Calibration deliberately disables halving. For every frozen calibration seed $s$ and every hard-coverage-qualified target size $K$, run one uninterrupted 30-epoch TRAIN2 trajectory

$$
\theta_{0,s,K}
\rightarrow
\theta_{3,s,K}
\rightarrow
\theta_{4,s,K}
\rightarrow
\theta_{5,s,K}
\rightarrow
\theta_{10,s,K}
\rightarrow
\theta_{30,s,K}.
$$

The v1 default calibration matrix is:

| Parameter | Values |
|---|---|
| optimizer seeds | 1, 2, 3 |
| candidate coarse endpoints | 3, 4, 5 epochs |
| short endpoint | 10 epochs |
| full endpoint | 30 epochs |
| candidate coarse-monitor sizes | 128, 256, 512, 1024 configurations |
| candidate coarse equivalence widths | 1, 2, 4 meV/Angstrom |

At least three frozen optimizer seeds are mandatory. The candidate coarse endpoints are collected from the **same uninterrupted 30-epoch run**. A later endpoint is therefore a calibration fallback, not a separately restarted training schedule.

The first coarse endpoint and first equivalence width must equal the current production `TARGET-DATA2D` defaults. `SIZE-FIDELITY1` may recommend a later endpoint or a wider early equivalence band, but it may not silently tighten the current production band.

# 3. Evaluation roles and inference reuse

Every calibration checkpoint is evaluated on the leakage-safe full size-development role. Candidate coarse-monitor scores are derived as deterministic subsets of that same authenticated full-role prediction authority.

This is a scientific and performance requirement:

1. one model inference pass is purchased per checkpoint on the full development role;
2. per-frame predictions are authenticated and cached;
3. 128/256/512/1024 monitor scores are reduced from the corresponding deterministic frame views; and
4. no candidate monitor size causes an additional MACE inference pass.

For $N_K$ coverage-qualified sizes and $N_s$ calibration seeds, v1 therefore requires

$$
N_{\mathrm{train}} = N_K N_s
$$

uninterrupted training runs and

$$
N_{\mathrm{infer}} = 5N_KN_s
$$

full-role checkpoint inference passes for epochs 3, 4, 5, 10, and 30. The four coarse-monitor sizes do not multiply $N_{\mathrm{infer}}$.

# 4. Thirty-epoch reference decision

For each optimizer seed, the 30-epoch full-development target scores define the retrospective reference ranking. The existing final practical-equivalence width and smaller-size preference are used. Let the first two valid sizes in that order be

$$
F_s = \{K^{(1)}_{30,s}, K^{(2)}_{30,s}\}.
$$

These are the **eventual target finalists** for fidelity calibration. The top member is the eventual target winner.

`SIZE-FIDELITY1` intentionally calibrates the target-size learning funnel before replay and expensive physical verification. Replay and physical checks remain later hard admissibility gates. Preserving both target finalists is therefore stricter and safer than preserving only the target winner: if the first finalist later fails a hard replay/physical gate, the scientifically relevant alternative must not already have been eliminated by a coarse screen.

# 5. Retrospective funnel simulation

For a candidate coarse endpoint $e$, monitor size $M$, and coarse equivalence width $\epsilon_c$:

1. rank every coverage-qualified size from the $M$-configuration coarse monitor at epoch $e$ using the exact `TARGET-DATA2D` early-screen ordering;
2. retain at most four candidates;
3. rank those survivors at epoch 10 on the full development role with the production short-screen equivalence rule;
4. retain exactly two; and
5. compare both survivor sets with $F_s$ from the exhaustive 30-epoch trajectories.

The largest hard-coverage boundary receives the same early equivalence-band protection used by current `TARGET-DATA2D`. It is not protected when materially worse.

# 6. Hard qualification requirements

A candidate $(e,M,\epsilon_c)$ passes only when all requirements hold across **every** frozen calibration seed:

1. **monitor decision equivalence:** the monitor-based epoch-$e$ promotion set equals the promotion set obtained from the full development role at the same endpoint and equivalence width;
2. **coarse finalist recall:** both members of $F_s$ survive the coarse top-four screen;
3. **short finalist recall:** both members of $F_s$ survive the epoch-10 top-two screen;
4. **winner recall:** the eventual target winner survives both screens;
5. **boundary safety:** if the largest materialized target size belongs to $F_s$, it is not lost at either screen; and
6. **trajectory identity:** all evaluation roles at one seed/size/epoch reference the same checkpoint, and all endpoints for one seed/size reference one uninterrupted training-run identity.

The default required finalist-recall fractions are exactly

$$
R_{\mathrm{coarse}} = R_{10} = 1.
$$

No average-success criterion is permitted in v1.

# 7. Diagnostics

For each candidate calibration setting the report also records:

- epoch-coarse and epoch-10 winner recall;
- seed-specific survivor sets;
- boundary-miss count;
- monitor/full promotion-set agreement rate; and
- mean Spearman rank correlation between coarse and 30-epoch full-development target scores.

Spearman correlation is **diagnostic only**. It cannot compensate for a survivor-recall failure.

# 8. Recommendation ordering

Among candidates satisfying all hard requirements, the v1 recommendation is deterministic:

1. earliest faithful coarse endpoint;
2. smallest monitor size with exact promotion-set equivalence; then
3. smallest tested equivalence width at or above the current production default.

This ordering minimizes purchased training/evaluation work without weakening the hard recall contract.

If no candidate passes, `SIZE-FIDELITY1` fails closed. `PERF-P2R` remains blocked. The next scientific revision must increase the coarse endpoint, enlarge the monitor, widen the early equivalence band, or revise the funnel under a new authority version. Coverage-based truncation is not an allowed fallback.

# 9. Persisted authorities

The implementation provides:

- `SizeFidelityCalibrationPolicy`;
- `SizeFidelityExecutionPlan`;
- `SizeFidelityMetric`;
- `SizeFidelityCandidateAssessment`;
- `SizeFidelityQualificationReport`;
- `build_size_fidelity_execution_plan(...)`;
- `build_size_fidelity_qualification(...)`; and
- `validate_size_fidelity_qualification(...)`.

All records use canonical SHA-256-backed content digests and fail closed on schema or digest mismatch.

The execution plan freezes the complete seed-by-size run matrix and the checkpoint endpoints before training begins. In v1, monitor metrics **must** be derived from full-role prediction authority rather than repeated inference.

# 10. Current execution status

The supplied MACE-MH-1 and MACE-MPA-0-medium checkpoints are now present and match the locked foundation hashes. The development host still has CPU-only PyTorch and no qualifying CUDA/CuEquivariance runtime. Calibration machinery, serialization, fail-closed validation, retrospective reducer logic, execution-plan accounting, and real-model CPU/e3nn reference paths may therefore be qualified during development, but the scientific fidelity of the coarse screen remains unproven until the final workstation run.

`FINAL-GPU1` owns that missing evidence. PERF-P2R may proceed as an implementation gate only because it must support the complete calibration grid; it receives no GPU performance or production-policy authority until a real `SIZE-FIDELITY1` report passes.

# References

1. K. Jamieson and A. Talwalkar, "Non-stochastic Best Arm Identification and Hyperparameter Optimization," *Proceedings of AISTATS*, PMLR 51, 240-248 (2016). https://proceedings.mlr.press/v51/jamieson16.html
2. C. Spearman, "The Proof and Measurement of Association between Two Things," *The American Journal of Psychology* **15**, 72-101 (1904). https://doi.org/10.2307/1412159
3. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields," *Advances in Neural Information Processing Systems* **35** (2022). https://papers.neurips.cc/paper_files/paper/2022/hash/4a36c3c51af11ed9f34615b81edb5bbc-Abstract-Conference.html
