---
title: "MLFF Architecture Revision 88"
author: "mdstats development"
date: "2026-08-17"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 88

**Release:** `mdstats 0.20.221a0`  
**Gate:** `TARGET-DATA2B-FEAS1-PERF1`  
**Dependency-graph schema:** `70`

Revision 88 is exact-equivalence CPU execution hardening for TARGET-DATA2B-FEAS1 and the immediately downstream MVIDX1 sparse-row build. It changes no coverage metric, radius, threshold, hard obligation, candidate ceiling, selector policy, persisted scientific schema, or target-frame identity.

The historical FEAS1 path alternated a multi-threaded cKDTree query with a serialized Python witness loop. Each witness separately mapped neighbor rows to candidate frames, called `np.unique`, updated candidate gains, and accumulated support-degree bins. That structure explains the observed low average CPU utilization. CUDA was never part of this stage and remains intentionally unused.

The new exact kernel compresses each bounded query block in compiled NumPy operations. `(witness row, candidate frame)` pairs are packed and uniqued into canonical row-major/candidate-major order; candidate gains use unbuffered `np.add.at` in the same historical arithmetic order; support degrees use vectorized bincounts and one witness-order FP64 accumulation per family. MVIDX1 writes the same canonical candidate stream directly from this kernel.

FEAS1 additionally schedules independent feature families concurrently. Automatic mode partitions the existing CPU-thread budget across family workers and native cKDTree workers, while explicit execution-only overrides remain available. `StageResourceScope` validates the nested CPU-lane product.

Focused qualification requires exact report/graph equivalence across block sizes, tree-worker counts, and family-worker counts, plus regression-clean MVSEL1/REPAIR1/MVPERF1 behavior. A four-family 8,192-candidate synthetic development benchmark on the eight-thread qualification host measured approximately 1.65x wall-time improvement with exact family-report identity.

GPU qualification remains deferred to the final consolidated FINAL-GPU1 handoff. Revision 88 does not introduce or authorize a GPU neighborhood backend.
