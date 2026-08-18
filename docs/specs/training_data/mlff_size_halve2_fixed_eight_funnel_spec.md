---
title: "MLFF SIZE-HALVE2 Fixed-Eight Successive-Fidelity Specification"
subtitle: "Coverage-qualified-only q-to-4-to-2-to-1 control plane"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.70in
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{microtype}
---

# Status

**Gate:** `SIZE-HALVE2`  
**Release:** `mdstats 0.20.206a0`  
**Architecture revision:** 73  
**Dependency-graph schema:** 55  
**Status:** implemented pre-migration control plane  
**Next gate:** `SIZE-FIDELITY2`

# Fixed candidate population

The only possible candidate sizes are `128, 256, 512, 1024, 2048, 4096, 8192, 16384`. Dynamic rescue sizes are forbidden. Each candidate binds all REPAIR1 domain-rung identities and its independently rescored MVQUAL1 hard-coverage state.

Hard coverage precedes training. Let `q` be the count of independently hard-qualified fixed sizes. `q < 4` fails closed for the future MV funnel. Coverage-failing or unavailable sizes cannot purchase TRAIN2 and cannot be inserted to fill the bracket. MVQUAL1 same-N and N95 non-regression must pass before work is authorized.

# Successive-fidelity geometry

The exact survivor geometry is:

```text
3 epochs:  q -> min(q,4)
10 epochs: 4 -> 2
30 epochs: 2 -> 1
```

Every hard-qualified candidate starts once under the common nominal 30-epoch schedule. The 10-epoch run must continue the exact epoch-3 checkpoint, optimizer, and RNG state; the 30-epoch run must continue the exact epoch-10 state. Foundation, evaluation-role, TRAIN2-policy, training-run, and schedule identities cannot change. Normalized schedule progress is exactly 3/30 and 10/30 at the early endpoints, and optimizer-update/structure-exposure counts must strictly increase across each continuation. PERF-P2R stage plans therefore authorize incremental `0->3`, `3->10`, and `10->30` work without repaying completed epochs.

# Ranking and convergence

At epochs 3 and 10, the largest hard-qualified fixed size is preserved only inside its practical-equivalence band. It may still be eliminated when materially worse. Final epoch-30 selection uses the smaller-size preference within practical equivalence together with complete target/replay/physical admissibility. If the largest qualified fixed boundary remains materially better than its smaller admissible finalist, the authority returns `nonconverged_at_fixed_ceiling`.

**Migration boundary.** `size_halve2_plan` is receipt-bound pre-migration evidence, not the production TARGET-DATA2D authority. Revision-64 DATA2C v4/DATA2D v2, DATA8 membership, and generated defaults remain unchanged until SIZE-FIDELITY2 passes and MVMIGRATE1 explicitly migrates them.
