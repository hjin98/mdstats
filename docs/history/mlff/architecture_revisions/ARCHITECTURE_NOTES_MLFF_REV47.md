---
title: "MLFF Architecture Revision 47"
subtitle: "PERF-P2 lazy TARGET-DATA2C authority v2"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.82in
fontsize: 10pt
---

# Revision 47

Revision 47 closes `PERF-P2` in `mdstats 0.20.181a0` and makes
`TargetDataLadderPlan.v2` the current TARGET-DATA2C authority.

The ladder now materializes configured rungs in ascending order and stops only
after the active TARGET-DATA2D shortlist width has been satisfied by the same
global coverage-plus-mandatory predicate used by Stage A. The canonical width
is four, but noncanonical configured widths are preserved exactly.

v2 records the configured sequence, exact materialized prefix, global rung
qualification records, early-stop qualifiers, intentionally skipped sizes,
pool-unavailable sizes, monotonicity contract, last materialized rung, and stop
reason. Legacy v1 remains readable as a qualification oracle but is stale for
current campaign authority.

Qualification against exhaustive v1 preserves Stage-A survivor sizes,
survivor membership, coverage-report digests, mandatory status, and the
TARGET-DATA2D shortlist. A 37,633-frame supplied-data-derived forced early-stop
fixture reduces median wall time from 7.867 s to 1.556 s and serialized ladder
authority from 4,729,481 B to 591,058 B. The exhaustive fallback path remains
exact; its noisy timing is not promoted as a speed claim.

`PERF-P3` - CPU structural and reduction hardening - is next.
