---
geometry: margin=0.48in
fontsize: 9pt
---

# TARGET-DATA2-MVPLAN2 optimized roadmap

**Release:** `mdstats 0.20.199a0`  
**Architecture revision:** `66`  
**Dependency-graph schema:** `48`  
**Status:** plan-only optimization freeze; implementation still begins at `TARGET-DATA2B-FEAS1`.

## Fixed scientific scope

The possible generated target sizes remain `128, 256, 512, 1024, 2048, 4096, 8192, 16384`; 16,384 is a hard ceiling. TARGET-DATA2B/TARGET-DATA2D hard coverage remains 0.95 by default with extents, protected strata, mandatory reservations, DATA5 leakage/correlation boundaries, and locked-test isolation unchanged. Revision-64 dynamic rescue remains executable until MVMIGRATE1.

## Revision-66 algorithm freeze

FEAS1 treats full-pool self-coverage only as a consistency check. It measures cross-support fragility after self/correlation-unit exclusion and derives an optimistic cardinality lower bound; a lower bound above 16,384 is `provably_capacity_infeasible` without pretending subset optimization can solve it.

MVIDX1 builds exact bidirectional sparse candidate<->witness adjacency plus first-class extent/stratum/mandatory obligation indices. Production storage is CSR/CSC-equivalent compact binary sidecars, optionally memmapped; dense persistent all-pairs matrices and Python-object neighbor graphs are forbidden. Scientific graph evidence is content addressed separately from reconstructible gain/heap/scratch caches.

MVSEL1 is deterministic and two phase. Phase A satisfies hard obligations and worst-view coverage first; new weighted coverage, provenance balance, density-aware representative gain, diversity, and stable UID follow lexicographically. Phase B fills larger prefixes using a frozen diminishing-return representative objective rather than pure FPS. Gain accumulation is FP64, parallel reductions are deterministic, and stable frame UID resolves final ties.

REPAIR1 uses witness coverage multiplicity to compute exact unique contribution, then evaluates only deficit-directed removal/replacement shortlists. Exchanges are active-shell only, strictly improving, bounded, restart-stable, and inherit the removed frame rank.

MVPERF1 inherits PERF-P2/P2R/P3/P4/P5: incremental state/reuse, authenticated stage products, one StageResourceScope across Python/native/BLAS workers and memory, bounded sparse/memmap storage, streamed hashing, and explicit scaling telemetry. Approximate neighbors/coverage, learned selectors, GPU graph selection, and DPP authority are not part of this sequence.

MVQUAL1 requires same-N hard non-regression, non-worse worst-view deficit, non-increasing N95, redundancy/cost telemetry, independent TARGET-DATA2D audit, and limited same-N legacy-vs-MV learning controls.

## Successive fidelity

Hard coverage occurs before training. If `q` fixed sizes qualify, `q < 4` fails closed. Only qualified sizes are trained:

`3 epochs: q -> min(q,4)`; `10 epochs: 4 -> 2`; `30 epochs: 2 -> 1`.

Therefore q=8 gives the intended `8 -> 4 -> 2 -> 1`. Coverage-failing sizes are never trained merely to populate the bracket. SIZE-FIDELITY2 calibrates available `q=4..8` admission widths from uninterrupted trajectories and inherits authenticated DATA8/restart reuse.

## Frozen implementation order

1. `TARGET-DATA2B-FEAS1` - self-consistency, cross-support fragility, cardinality lower bounds.
2. `TARGET-DATA2C-MVIDX1` - exact sparse bidirectional graph and hard-obligation index.
3. `TARGET-DATA2C-MVSEL1` - deterministic two-phase progressive selector.
4. `TARGET-DATA2C-REPAIR1` - multiplicity-based unique contribution and targeted shell exchange.
5. `TARGET-DATA2C-MVPERF1` - exact-equivalence sparse/incremental hardening and cost authority.
6. `TARGET-DATA2C-MVQUAL1` - same-N scientific/learning qualification.
7. `SIZE-HALVE2` - coverage-qualified-only `q -> min(q,4) -> 2 -> 1` integration.
8. `SIZE-FIDELITY2` - q=4..8 survivor-fidelity calibration.
9. `TARGET-DATA2C-MVMIGRATE1` - generated-default migration and revision-64 rescue retirement.

