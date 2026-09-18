---
kind: representation-repair-record
protocol_version: 6.4.0
status: COMPLETE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
domain: D2
reviewed_semantic_target: 4f161b1c4820de10abe638287b13152147d12fd9
reviewed_semantic_blob: 3e7fb744fc733f23bbd93a8347246cfa306ebe89
prior_renderer_repair_target: 1505a22b0940eb44f4c8a1820e3e26e2263c8a79
prior_renderer_repair_blob: e6f0cdea54964a3bc2962a4ecacf44a7625f33fa
repaired_D2_blob: 30e6e6336cf41a05879650a3a2d7d583c4ef713a
repair_date: 2026-09-18
semantic_change: false
---

# D2 R2 renderer-only repair 2 — D2.DEF.027

The prior renderer repair removed disallowed `\\operatorname` uses, but D2.DEF.027 still contained renderer-hostile escaped set braces and compound restricted-sum subscripts.

This repair rewrites D2.DEF.027 only:

- `O_c(S)` is defined by the same membership predicate rather than escaped literal set braces;
- the exact restricted witness subsets are named `W_m^0(c;S)` and `W_m^1(c)` through membership predicates;
- the candidate-gain and residual-gain expressions then sum over those named sets.

The selected witness sets, summands, denominators, hard-gain counts and every downstream numerical decision are unchanged.

Focused D2.DEF.027 verification found no `\\operatorname`, `\\substack`, raw escaped `\\#`, escaped literal set-brace macros, malformed display delimiters, raw LaTeX outside math, or unbalanced display braces. Whole-file structural scanning also found no malformed display delimiters, raw LaTeX outside math, or unbalanced display braces.

This is representation-only and preserves the independent D2 R2 PASS.
