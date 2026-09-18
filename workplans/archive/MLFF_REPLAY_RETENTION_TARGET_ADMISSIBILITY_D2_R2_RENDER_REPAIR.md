---
kind: representation-repair-record
protocol_version: 6.4.0
status: COMPLETE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
domain: D2
reviewed_semantic_target: 4f161b1c4820de10abe638287b13152147d12fd9
reviewed_semantic_blob: 3e7fb744fc733f23bbd93a8347246cfa306ebe89
independent_review_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D2_INDEPENDENT_REVIEW_R2.md
independent_review_commit: f1fbb09e7aa368808b0e3d73cd0e559d91d912d3
repaired_D2_blob: e6f0cdea54964a3bc2962a4ecacf44a7625f33fa
repair_date: 2026-09-18
semantic_change: false
---

# D2 R2 renderer-only repair

This repair changes representation only. It does not change the reviewed D2 numerical method, decision relation, threshold, ordering, tie rule, currentness rule, equivalence relation, failure classification, or D2-to-D3 handoff.

Renderer repairs:

1. replace the disallowed LaTeX macro `\operatorname{RN}` by semantically identical `\mathrm{RN}`;
2. replace `\operatorname{epoch}(c)` and `\operatorname{sha256}(c)` in the within-run tie key by explicitly defined renderer-safe symbols `e(c)` and `h(c)`;
3. replace `\operatorname{optimizer_seed}(s)` by the already-bound optimizer-seed variable `s` in the cross-seed tie key;
4. define `e(c)`, `h(c)`, and `s` in adjacent prose so the total lexicographic orders are unchanged.

Verification on the repaired canonical D2 source found:

- zero occurrences of `\operatorname`;
- no standalone single-dollar display delimiters;
- no raw LaTeX outside inline/display math;
- balanced unescaped braces in every display-math block.

The independently reviewed semantic target remains the provenance basis. This repaired D2 blob is algebraically and decision-equivalent and is the representation-safe candidate to ratify.
