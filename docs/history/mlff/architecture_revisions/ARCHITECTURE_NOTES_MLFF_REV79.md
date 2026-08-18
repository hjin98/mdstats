---
title: "MLFF Architecture Revision 79"
subtitle: "REPLAY-UNIFY1C batched foundation pseudo-label cache and qualification"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 79

Revision 79 advances the frozen REPLAY-UNIFY1 migration through **REPLAY-UNIFY1C** while keeping live TRAIN2/DATA8 replay execution on the historical split-file path until Gate D. The sole new external replay authority remains the single selected replay source established in Revision 77.

Gate C adds `ReplayFoundationPredictionPolicy`, `ReplayFoundationPredictionCache`, and bounded prediction shards. The scientific prediction identity binds the exact foundation checkpoint SHA, resolved head, `FoundationInferenceIdentity`, dtype, backend/resolved e3nn-or-CuEq kernel, and execution device. Inference batch size and physical shard size are excluded from that identity. The default execution path reuses `MaceCalculatorProvider.predict_batch()`; source truth and calculator results are stripped from geometry copies before inference, preventing true-label leakage into pseudo-label generation.

A dedicated authenticated `mdstats.replay-foundation-audit-cache.v1` sidecar stores only scalar audit quantities needed by replay qualification. `ReplayPseudolabelQualificationPolicy` defaults to 20 eV/Angstrom maximum force, 5 eV/Angstrom force-component RMS, and 0.5 eV/Angstrom^3 maximum absolute stress. Threshold-only policy changes reclassify the compact sidecar with zero model calls and without loading ragged prediction-force payloads.

`materialize_replay_pseudolabel_views()` lazily generates only requested train/monitor ExtXYZ transport files from the authenticated source, prediction cache, qualification authority, and split manifest. Generated `REF_*` fields are a transport projection only; source truth remains a separate logical namespace. Existing authenticated views return without source parsing or prediction access, and deleted views reconstruct from cached predictions without reinference. Audit-sidecar and prediction-shard corruption fail closed at their respective use boundaries.

The supplied 12,000-frame LTA replay source was exercised end-to-end on the development host with a deterministic **non-MACE** provider to qualify control-plane scaling without violating the deferred-GPU policy. The run used 188 bounded batches and 47 prediction shards, classified 12,000/12,000 frames as eligible, and reproduced exactly 10,000 train / 2,000 monitor. After the compact audit-sidecar optimization, qualification measured about 0.13 s, threshold-only reclassification about 0.11 s, dual-role pseudo-label materialization about 9.34 s, and an authenticated view cache hit about 0.22 s, with roughly 280 MB peak RSS. These are not MACE throughput or numerical-parity claims.

Real MACE/CUDA/CuEq replay inference remains deliberately deferred to the regenerated one-shot FINAL-GPU1 bundle after REPLAY-UNIFY1E.

**Release:** `mdstats 0.20.212a0`  
**Dependency-graph schema:** 61  
**Next gate:** `REPLAY-UNIFY1D` - campaign integration and generated single-source replay configuration.
