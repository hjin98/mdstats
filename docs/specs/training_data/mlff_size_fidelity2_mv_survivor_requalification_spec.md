---
title: "MLFF SIZE-FIDELITY2 Survivor-Requalification Specification"
subtitle: "q=4..8 retrospective 3/10/30 fidelity authority"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.55in
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{microtype}
---

# Status

**Gate:** `SIZE-FIDELITY2`  
**Release:** `mdstats 0.20.207a0`  
**Architecture revision:** 74; **dependency-graph schema:** 56  
**Status:** pre-migration control plane implemented; positive GPU qualification deferred to `FINAL-GPU1`  
**Next:** `TARGET-DATA2C-MVMIGRATE1`

# Calibration and continuation authority

For hard-qualified population `q_max`, calibrate every available `q in 4..q_max`. Qualified sizes must be a contiguous suffix of `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`. For each frozen optimizer seed, train every qualified size **once** on the common nominal 30-epoch schedule with halving disabled and evaluate epochs `3, 10, 30`. Every q width is reconstructed from this same trajectory matrix, so work is `n_seed * q_max`, not separate q-specific campaigns.

Epoch 10 authenticates the epoch-3 checkpoint/optimizer/RNG parent; epoch 30 authenticates epoch 10. Foundation, evaluation role, TRAIN2 policy, training-run identity, and schedule identity cannot drift. Schedule progress is exactly `3/30`, `10/30`, `30/30`, with strictly increasing update/exposure counts.

# Survivor-recall and fixed-ceiling authority

For each seed/q width, the complete epoch-30 population defines the eventual two finalists using SIZE-HALVE2 deterministic practical-equivalence ordering. Reconstruct:

```text
epoch 3:   q -> min(q,4)
epoch 10:  4 -> 2
epoch 30:  complete q population is calibration truth
```

Both eventual finalists must survive epochs 3 and 10 for **every** seed/q width: required finalist recall is `1.0` at both boundaries. Winner recall is diagnostic only. If 16,384 remains materially superior to every smaller admissible candidate beyond the frozen practical-equivalence width, qualification fails as fixed-ceiling nonconvergence.

# Monitor derivation and migration boundary

The monitor grid is `128, 256, 512, 1024`. Every epoch-3 monitor score derives from the **same full-prediction digest** as the full-role score; later checkpoints cannot request monitor inference. Additional monitor-model inference count is therefore exactly zero. Recommend the smallest monitor whose epoch-3 promotion set exactly matches full-role promotion for every seed/q width and retains the eventual finalists.

`size_fidelity2_execution_plan` is content-addressed to SIZE-HALVE2 and included in the prepare restart receipt; blocked SIZE-HALVE2 yields a blocked no-work plan. Qualification reports require the exhaustive trajectory/checkpoint matrix, and unit fixtures cannot masquerade as production GPU evidence. Positive MACE/GPU execution remains deferred to `FINAL-GPU1`.

This gate changes no generated policy: revision-64 TARGET-DATA2C v4/TARGET-DATA2D v2 remain authoritative until `TARGET-DATA2C-MVMIGRATE1` explicitly migrates policy after the required evidence exists.
