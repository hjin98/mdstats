---
title: "mdstats 0.20.182a0"
subtitle: "SIZE-HALVE1 target-size correction"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.82in
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{microtype}
---

# Summary

`0.20.182a0` corrects target-size selection. Coverage is a hard admissibility
limit, not a proxy for training sufficiency. Every coverage-qualified size now
enters a 3-epoch target-only learning screen before successive reduction at 10
and 30 epochs.

# Scientific authority

The generated funnel is

$$
7 \rightarrow N_{\mathrm{coverage\ qualified}}
  \rightarrow_{3\ \mathrm{epochs}} \le4
  \rightarrow_{10\ \mathrm{epochs}} 2
  \rightarrow_{30\ \mathrm{epochs}} 1.
$$

TARGET-DATA2C advances to v3 full-ladder authority. TARGET-DATA2D advances to v2
3/10/30 authority. TARGET-DATA2E advances to v2 full-funnel provenance.
Historical PERF-P2/TARGET-DATA2C v2 evidence remains readable as archival
qualification but is stale for current generated campaigns.

# Epoch-3 screen

The coarse screen uses one fixed leakage-safe target-only EVAL2 role, default
256 configurations, deterministically balanced across development correlation
blocks. Replay inference, checkpoint-rescue search, bootstrap selection, and
physical verification are not purchased at epoch 3.

Generated preflight requires the 3-epoch endpoint to lie strictly past LR
warm-up. With current defaults, $3/30=0.10>0.05$.

# Exact continuation

Survivors continue the same nominal 30-epoch trajectory. Evidence authenticates
checkpoint/model, optimizer/scheduler, and Python/NumPy/Torch RNG state at both
3->10 and 10->30 boundaries. Optimizer updates and structures presented are
persisted alongside epoch count.

# Boundary convergence safeguard

At epoch 3 and 10, the largest hard-coverage boundary is preserved within its
practical-equivalence band. It may still be eliminated when materially worse.
At epoch 30, smaller-size preference is restored within final practical
equivalence. This prevents an early tie from hiding bounded-ladder
nonconvergence.

# Fidelity calibration requirement

SIZE-FIDELITY1 is now mandatory before PERF-P2R. It must use exhaustive
30-epoch calibration trajectories to verify epoch-3/10 survivor recall across
frozen screening seeds and to choose the smallest common coarse monitor that
preserves the full-role promotion decision up to practical equivalence. The
current 256-frame coarse monitor and 1.0 meV/A coarse equivalence width are
provisional defaults, not yet authorizing empirical claims.

# Performance roadmap

PERF-P2's historical lazy-truncation speedup is no longer a current campaign
claim. SIZE-FIDELITY1 is inserted before PERF-P2R, and PERF-P2R remains before PERF-P3 to optimize full-ladder coverage and
preprocessing reuse, target-only coarse evaluation, exact pause/resume,
stage-aware scheduling, checkpoint retention, and complete funnel performance.

No authorizing MACE/GPU runtime was supplied in this environment. GPU training
speed or VRAM benefits are therefore not inferred.

# Documentation

The canonical architecture advances to revision 48 and dependency-graph schema
30. The normative correction is
`docs/specs/training_data/mlff_size_halve1_target_size_revision_spec.md`.
