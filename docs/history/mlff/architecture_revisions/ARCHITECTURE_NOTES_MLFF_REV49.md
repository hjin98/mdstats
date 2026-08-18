---
title: "MLFF Architecture Revision 49"
subtitle: "SIZE-FIDELITY1 calibration authority"
date: "2026-08-15"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 49

Revision 49 implements the control-plane and scientific-evidence authority for **SIZE-FIDELITY1**. It does not claim that the current three-epoch coarse screen is production-certified. That conclusion still requires exhaustive MACE trajectories from an authorizing foundation checkpoint and GPU/runtime.

## Why this gate exists

SIZE-HALVE1 corrected the target-size funnel so hard coverage is admission only. Every coverage-qualified size competes through learning evidence. The remaining unresolved question is whether a cheap early screen is faithful enough to discard sizes safely.

A global rank statistic cannot answer that question by itself. A screen is scientifically acceptable only if it preserves the later candidates that matter. Revision 49 therefore makes **survivor recall** the hard calibration authority.

## Implemented authority

`mdstats.training_data.size_fidelity` adds versioned, SHA-256-authenticated records for:

- the calibration policy;
- the exhaustive execution plan;
- target-only checkpoint metrics;
- per-setting candidate assessments; and
- the final calibration qualification report.

The authority version is:

```text
mdstats.size-fidelity1.coarse-screen-calibration.2026-08.v1
```

The default calibration campaign freezes optimizer seeds 1/2/3, candidate coarse endpoints 3/4/5, monitor sizes 128/256/512/1024, and early practical-equivalence widths 1/2/4 meV/Angstrom.

## Exhaustive calibration semantics

Calibration itself never halves the ladder. Every hard-coverage-qualified size is trained to 30 epochs for every frozen calibration seed. Epochs 3, 4, 5, 10, and 30 are checkpoints on one uninterrupted trajectory.

For each seed, the 30-epoch full-development target ranking defines the retrospective top-two finalists. A candidate coarse rule passes only if:

1. the coarse monitor produces the same promotion set as the full development role;
2. both eventual 30-epoch target finalists survive the coarse top-four screen;
3. both finalists survive the epoch-10 top-two screen;
4. the eventual target winner survives both screens;
5. the largest target-size boundary is never falsely eliminated when it is a later finalist; and
6. all role evaluations at one endpoint refer to the same checkpoint and uninterrupted training run.

Both-finalist recall is required at epoch 10. This is stronger than winner-only recall and is necessary because later replay or physical hard gates can disqualify the first target finalist.

## Evaluation-efficiency correction

Monitor-size calibration must not multiply MACE inference. Each checkpoint is inferred once on the complete leakage-safe development role. Authenticated per-frame predictions are then reduced over deterministic 128/256/512/1024 monitor views.

For $N_K$ coverage-qualified sizes and $N_s$ seeds,

$$
N_{\mathrm{train}} = N_KN_s,
\qquad
N_{\mathrm{infer}} = 5N_KN_s.
$$

The monitor grid changes only post-inference reductions.

## Recommendation and failure behavior

Passing settings are ordered by earliest faithful coarse endpoint, then smallest monitor, then smallest tested early equivalence width at or above the current production default. No setting passing all hard requirements means the gate fails closed.

If three epochs are insufficient, the correction is a later coarse endpoint, larger monitor, wider early equivalence band, or newly versioned funnel. Coverage-based target-size truncation cannot return as a fallback.

## Roadmap effect

The roadmap remains:

```text
SIZE-HALVE1
    -> SIZE-FIDELITY1
    -> PERF-P2R
    -> PERF-P3
```

Revision 49 changes SIZE-FIDELITY1 from *planned* to **implemented, awaiting authorizing run**. PERF-P2R remains blocked until a real calibration report passes.

## Current evidence boundary

The supplied environment contains MACE 0.3.16 source dependencies but no authorizing foundation checkpoint and no qualifying GPU campaign. CPU qualification can therefore verify serialization, matrix completeness, deterministic retrospective reductions, exact monitor/full comparison logic, recommendation behavior, and fail-closed validation. It cannot establish the scientific fidelity of the three-epoch production screen.

## References

- K. Jamieson and A. Talwalkar, "Non-stochastic Best Arm Identification and Hyperparameter Optimization," PMLR 51, 240-248 (2016). https://proceedings.mlr.press/v51/jamieson16.html
- C. Spearman, "The Proof and Measurement of Association between Two Things," *American Journal of Psychology* 15, 72-101 (1904). https://doi.org/10.2307/1412159
- I. Batatia et al., "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields," NeurIPS 35 (2022). https://papers.neurips.cc/paper_files/paper/2022/hash/4a36c3c51af11ed9f34615b81edb5bbc-Abstract-Conference.html
