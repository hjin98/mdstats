---
title: "MLFF Architecture Revision 48"
subtitle: "SIZE-HALVE1 correction, SIZE-FIDELITY1 calibration, and PERF-P2R roadmap"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.82in
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{microtype}
  - |-
    \usepackage{xurl}
---

# Revision 48 decision

Revision 48 corrects the generated target-size selection rule discovered during
PERF-P2 qualification. Coverage is now **hard admission only**. It no longer
selects the four smallest passing sizes.

The corrected authority is

$$
7 \xrightarrow{\mathrm{hard\ coverage}} N_{\mathrm{eligible}}
  \xrightarrow{3\ \mathrm{epochs}} \le 4
  \xrightarrow{10\ \mathrm{epochs}} 2
  \xrightarrow{30\ \mathrm{epochs}} 1.
$$

The low-fidelity resource-allocation pattern is related to successive halving
[1,2], while mdstats retains its own deterministic target metrics, hard gates,
provenance, and exact restart semantics.

# Why the correction is required

The former Stage-A rule treated passing geometric/statistical coverage as
sufficient evidence that larger nested data sets could not improve training.
That implication is not valid. A small subset may span the required support yet
sample important regions too sparsely for an accurate learned potential.

Coverage therefore answers only whether a candidate is admissible. Training
response answers whether its sampling density/information content is adequate.

# Authority changes

Revision 48 advances current generated authority to:

- TARGET-DATA2C v3: every globally materializable rung is materialized;
- TARGET-DATA2D v2: hard coverage plus exact 3/10/30 successive fidelity;
- target-size training evidence v3: checkpoint, optimizer/scheduler, and RNG
  continuation ancestry;
- TARGET-DATA2E v2: complete coarse/short/final funnel provenance; and
- EVAL2 `size_development_coarse`: fixed common target-only epoch-3 role.

Historical TARGET-DATA2C v1/v2 and PERF-P2 evidence remain archival. They are
stale as current generated-campaign authority.

# Additional safeguards found during re-audit

## Coarse screen must be past warm-up

Generated preflight now requires

$$
E_3/E_{30} > p_{\mathrm{warmup,end}}.
$$

The defaults satisfy $3/30=0.10>0.05$. A screen inside warm-up is rejected.

## Common coarse evaluation role

The epoch-3 target monitor is a versioned policy field, default 256
configurations. It is a deterministic, correlation-block-balanced subset of the
same leakage-safe development complement used by the full size study. Every
candidate is evaluated on identical target frames. Replay inference is omitted
at epoch 3.

## Exact continuation includes RNG state

Promotion is an exact continuation, not retraining. The authority authenticates
checkpoint/model, optimizer/scheduler, and Python/NumPy/Torch CPU/CUDA RNG
state at both 3->10 and 10->30 boundaries. Evidence also records optimizer
updates and structures presented because equal epoch counts do not imply equal
compute exposure across data sizes.

## Early equivalence preserves the ladder boundary

Smaller-size preference is retained only at final 30-epoch qualification.
During epoch-3 and epoch-10 halving, the largest hard-coverage boundary is
preserved **within its practical-equivalence band**. It may still be eliminated
when materially worse. This keeps the workflow capable of detecting
`nonconverged_at_ladder_boundary` rather than deleting the boundary on an early
tie.

# SIZE-FIDELITY1 calibration

The re-audit found that introducing a 3-epoch screen creates a new scientific
approximation that must be calibrated before production performance promotion.
SIZE-FIDELITY1 therefore exhaustively continues all hard-coverage-qualified
rungs to 30 epochs for multiple frozen screening seeds and checks whether the
epoch-3 top four and epoch-10 top two retain the eventual 30-epoch winner and
finalists. The 256-frame coarse monitor is compared against the full development
role, and the coarse practical-equivalence width is calibrated from real
trajectory/seed variability. Both current values are provisional until this
evidence exists.

The continuation audit also extends beyond global RNG state: PERF-P2R must
authenticate DataLoader/sampler/worker ordering state or prove deterministic
epoch-boundary reconstruction. This closes a restart-equivalence gap that can
otherwise survive checkpoint/optimizer/RNG digest checks.

# Revised optimization roadmap

PERF-P2's lazy four-smallest truncation is superseded scientifically. The next scientific qualification gate is SIZE-FIDELITY1. PERF-P2R follows only after the epoch-3/10 fidelity and coarse-monitor calibration pass; PERF-P3 remains after PERF-P2R.

PERF-P2R must optimize the corrected semantics rather than recover the old
truncation indirectly. Its scope is:

1. exact full-ladder FPS/coverage state reuse;
2. authenticated nested-corpus prefix/index views instead of duplicate bytes;
3. frame-level graph/neighbor/preprocessing cache reuse across candidate sizes;
4. target-only epoch-3 endpoint evaluation with no replay/rescue/bootstrap/
   physical work;
5. exact in-place 3->10->30 pause/resume without repaying prefix epochs;
6. stage-aware single-/multi-GPU resource scheduling;
7. checkpoint retention/garbage collection after immutable elimination evidence;
   and
8. whole-funnel wall/VRAM/RSS/I/O/utilization qualification on an authorizing
   MACE/GPU runtime.

For qualifiers $A$, epoch-3 survivors $S_4$, and epoch-10 finalists $S_2$, the
useful target exposure proxy is

$$
W=3\sum_{i\in A}K_i+7\sum_{i\in S_4}K_i+20\sum_{i\in S_2}K_i.
$$

For all seven default sizes, $\sum K_i=16256$. The proxy reduction relative to
training all seven sizes to 30 epochs ranges from 17.56% when the largest sizes
survive to 85.67% when the smallest survive. This is not a wall-time prediction.

# Qualification boundary

The correction is fully testable for authority construction, serialization,
role construction, continuation identity, dispatch state, and CPU-side ladder
behavior in the current environment. No authorizing MACE/GPU runtime is
available here, so revision 48 does **not** claim empirical epoch-3/10 survivor
fidelity or measured 3/10/30 GPU training speed. Survivor-fidelity certification
belongs to SIZE-FIDELITY1; performance authority belongs to PERF-P2R.

# References

[1] Kevin Jamieson and Ameet Talwalkar. "Non-stochastic Best Arm Identification
and Hyperparameter Optimization." *Proceedings of AISTATS*, PMLR 51:240-248,
2016. <https://proceedings.mlr.press/v51/jamieson16.html>

[2] Lisha Li, Kevin Jamieson, Giulia DeSalvo, Afshin Rostamizadeh, and Ameet
Talwalkar. "Hyperband: A Novel Bandit-Based Approach to Hyperparameter
Optimization." *Journal of Machine Learning Research* 18(185):1-52, 2018.
<https://www.jmlr.org/papers/v18/16-558.html>
