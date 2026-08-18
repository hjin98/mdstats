---
geometry: margin=0.7in
fontsize: 9.5pt
---

# MLFF architecture revision 66 - optimized multi-view selector implementation freeze

**Release:** `mdstats 0.20.199a0`  
**Gate:** `TARGET-DATA2-MVPLAN2`  
**Dependency-graph schema:** `48`

Revision 66 hardens the revision-65 multi-view target-data roadmap before implementation. It remains a plan-only authority: revision-64 TARGET-DATA2C v4 is still the executable selector until `TARGET-DATA2C-MVMIGRATE1` passes.

The principal corrections are: FEAS1 no longer treats full-pool self-coverage as meaningful support feasibility; MVIDX1 is frozen as an exact sparse bidirectional coverage graph; hard extents/strata become first-class obligations; MVSEL1 becomes deterministic two-phase coverage-first/density-aware selection; REPAIR1 uses coverage multiplicity rather than literal leave-one-out recomputation; and MVPERF1 inherits the prior incremental-state, cache-reuse, unified resource-budget, bounded-memory, and streaming-persistence rules.

The fixed target-size set remains `128, 256, 512, 1024, 2048, 4096, 8192, 16384`. Only hard-coverage-qualified sizes may enter training. If `q` sizes qualify, the successive-fidelity funnel is `q -> min(q,4) -> 2 -> 1` at `3 -> 10 -> 30` epochs; `q=8` realizes the intended `8 -> 4 -> 2 -> 1` path. Fewer than four qualifiers fails closed before the 10-epoch stage.

Deterministic FP64 gain accumulation, stable frame-UID tie breaking, exact nested-prefix/rung invariants, shell-rank inheritance, authoritative-versus-cache persistence separation, saturation diagnostics, and selection-cost telemetry are now normative. Active data acquisition, approximate nearest neighbors, learned selectors, DPP authority, and GPU graph selection are explicitly outside this implementation sequence.
