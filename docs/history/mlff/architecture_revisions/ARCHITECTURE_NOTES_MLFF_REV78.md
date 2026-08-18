---
title: "MLFF Architecture Revision 78"
subtitle: "REPLAY-UNIFY1B source-true-label cache and lazy materialization"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 78

Revision 78 advances the frozen REPLAY-UNIFY1 migration through **REPLAY-UNIFY1B** while leaving live TRAIN2/DATA8 replay execution on the historical path until Gate D. The one selected `[paths].replay_set` source remains the sole new replay input authority established in Revision 77.

Gate B adds `mdstats.replay-true-label-cache.v1`. `ReplayTrueLabelCache` records the canonical geometry-to-source-label identity mapping without duplicating numerical arrays. Its logical identity is independent of source ordering/location. Missing energy/force truth is explicit; any requested materialized role containing incomplete truth fails closed. Optional stress is preserved when present.

Gate B also adds `mdstats.replay-true-label-view.v1` and lazy `materialize_replay_true_label_views()`. Materialized `REF_energy`, `REF_forces`, and optional `REF_stress` ExtXYZ files are transport caches rather than replay authority. A view's stable logical digest binds the exact split role, geometry set, source-label set, true-label cache, and split manifest; the transport record separately authenticates file SHA-256. Existing authenticated views are reused without reading the source, and deleted views are reconstructed without any foundation-model inference.

When train and monitor are both missing, mdstats performs **one bounded-memory source pass** and routes frames into both outputs. A profiling pass removed an accidental quadratic implementation in which whole-corpus cache/split digests were recomputed for each frame; those immutable values are now computed once per materialization call.

The supplied `LTA_replay/mp_replay_selected.extxyz` directly qualifies the intended default: 12,000 source configurations, all 12,000 with complete finite energy/forces and stress, split exactly 10,000 train / 2,000 monitor. On the development CPU host, source inspection measured about 9.4 s; cold monitor materialization including inspection about 15.8 s; cold dual-role 12k materialization including inspection about 20.3 s at roughly 278 MB peak RSS; and an authenticated dual-role cache hit about 0.23 s with zero source parsing. These are development-host qualification observations, not portable performance guarantees.

Anti-masquerade validation rejects a true-label cache paired with a source artifact that has the same geometry set but different source-label identities. The historical true-label directory/materialization APIs remain readable and unchanged; campaign integration is deliberately deferred.

**Release:** `mdstats 0.20.211a0`  
**Dependency-graph schema:** 60  
**Next gate:** `REPLAY-UNIFY1C` - batched foundation pseudo-label cache, audit, and qualification.
