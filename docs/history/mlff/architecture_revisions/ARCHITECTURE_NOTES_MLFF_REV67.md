---
title: "MLFF architecture revision 67"
subtitle: "TARGET-DATA2B-FEAS1 implementation"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.78in
fontsize: 10pt
---

# MLFF architecture revision 67 - TARGET-DATA2B-FEAS1 implemented

**Release:** `mdstats 0.20.200a0`  
**Dependency-graph schema:** 49

Revision 67 implements the first gate of the optimized multi-view target-data roadmap. FEAS1 now produces an authenticated diagnostic record from the frozen TARGET-DATA2A/TARGET-DATA2B authorities before TARGET-DATA2C runs.

The gate measures exact self-excluded and correlation-unit-excluded support, records fragile witness mass by support degree, derives optimistic per-family coverage cardinality lower bounds, and combines them with protected-stratum, extent, and correlation-interval reservation bounds. A lower bound above the fixed 16,384 ceiling is `provably_capacity_infeasible`.

This revision does **not** change target selection. Revision-64 TARGET-DATA2C v4 remains the executable compatibility path. The next implementation gate is TARGET-DATA2C-MVIDX1.
