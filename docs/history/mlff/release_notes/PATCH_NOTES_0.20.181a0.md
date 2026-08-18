---
title: "mdstats 0.20.181a0 Patch Notes"
subtitle: "PERF-P2 lazy TARGET-DATA2C authority v2"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.82in
fontsize: 10pt
---

# `mdstats 0.20.181a0`

This release closes MLFF gate `PERF-P2`.

## Changed

- Advances TARGET-DATA2C plan authority from v1 to v2.
- Materializes and scores nested target-size rungs lazily.
- Stops only after the active TARGET-DATA2D shortlist width is globally fixed.
- Records explicit global rung qualifications, intentional non-materialization,
  pool-unavailable sizes, stop reason, and monotonicity contract.
- Keeps legacy v1 readable as a regression oracle while rejecting it as stale
  current campaign authority.
- Makes exact single-rung cKDTree worker count execution-only and digest
  invariant.
- Updates TARGET-DATA2D to consume v2 materialized qualification evidence
  without treating intentionally absent larger rungs as failures.

## Qualification

Exhaustive v1 and lazy v2 produce identical Stage-A survivor sizes and exact
survivor evidence on both exhaustive-fallback and forced-early-stop fixtures.
On the supplied-data-derived early-stop fixture, three fresh-process samples
show an 80.23% median wall-time reduction and an 87.50% reduction in serialized
ladder authority size.

The fallback timing is intentionally not claimed as a speedup because its
observed ranges overlap and are cloud-scheduler sensitive.

## Next

`PERF-P3` - CPU structural and reduction hardening.
