---
kind: author-repair-closure
protocol_version: 6.4.0
status: READY_FOR_FRESH_INDEPENDENT_R6_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
prior_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R5.md
prior_immutable_target: 058b856df249bd28212ba70e459babd1f29a6c42
primary_d4_evidence_commit: dbe6c552b216d583caf9230d2c1e0879b68f8c3e
primary_d4_evidence_run: 35300235175
confirmatory_d4_evidence_commit: 17af93877ba312600ab1bf7a2f1f2990c9c2ef00
confirmatory_d4_evidence_run: 35300268107
---

# MLFF D1/D2 Protocol-6.4 R6 repair closure

## 1. Author-side disposition

Independent Review R5 returned NO-PASS solely because the direct dependency
trace still omitted local symbol/domain owners. It found no Serious Challenge
to accepted D1/D2, no semantic-kernel defect, no renderer blocker and no D4
evidence blocker.

R6 changes only the derived dependency representation and lifecycle evidence.

## 2. R5 blocker repair

The repair adds seventeen direct edges across thirteen subjects:

```text
D1.AX.003  -> D1.DEF.012
D1.AX.004  -> D1.DEF.010
D1.AX.004  -> D1.DEF.012
D1.AX.004  -> D1.DEF.013
D1.AX.004  -> D1.DEF.017
D1.DEF.013 -> D1.DEF.010
D1.DEF.020 -> D1.DEF.006
D1.AX.008  -> D1.DEF.009
D1.AX.008  -> D1.DEF.012
D1.AX.010  -> D1.DEF.008
D2.DEF.012 -> D1.DEF.016
D2.DEF.021 -> D1.DEF.016
D2.DEF.030 -> D2.DEF.012
D2.DEF.031 -> D2.DEF.012
D2.DEF.041 -> D1.DEF.006
D2.DEF.050 -> D2.DEF.007
D2.AX.003  -> D1.DEF.012
```

This includes all ten same-class edges specified by R5 Review and seven further
direct-owner dependencies found by re-running the complete local-symbol/domain
pass rather than stopping at the review witnesses.

No accepted scientific or numerical meaning is changed.

## 3. Deliberate non-edges

R6 records rather than hides the principal challenged non-edges:

- fold construction `D2.DEF.056` obtains `T_N/M_mon` semantics through
  direct parent `D1.DEF.024`;
- production `D2.AX.005` obtains lower M3/monitor/replay/threshold coordinates
  through its direct production/checkpoint parents;
- selector-information exclusions are role-class semantics, not dependencies on
  later realized post-selection memberships;
- `D2.DEF.029` is explicitly distinct from `D2.DEF.020`;
- `D2.DEF.060A` selects comparison relations and does not directly consume
  every value-generating operand.

These cases are transitive or genuine non-dependencies under the workplan
criterion, not omitted for graph sparsity alone.

## 4. Author verification

On the repaired candidate graph:

- 106 formal objects are represented by 106 rows;
- every prerequisite resolves;
- no object-level cycle exists;
- no D1 object depends on D2;
- reverse-impact from the R5 witness owners reaches the challenged propositions;
- explicit formal-ID comparison has one intentional non-edge only:
  `D2.DEF.029 !-> D2.DEF.020`.

Fresh independent R6 Review remains responsible for falsification.

## 5. D4 evidence applicability

No executable source or test changes are introduced by R6. Target binding must
reconfirm these expected blobs:

- D1 kernel: `dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498`;
- D2 kernel: `74c0c0588617b7f48fd93bc21e534f538f037ef8`;
- weighted-quantile owner:
  `15d20eae5a7b481d636d20fc2281c743e9abe0df`;
- focused FP64 regression:
  `8da42708ac601b335dfb3c9d818c302baccb1a78`;
- real-owner suite:
  `01c6d99872c136cff91777e65ce8331807f8a016`.

If those identities remain exact, passing CPU runs `35300235175` and
`35300268107` remain current evidence. No executable rerun is required solely
for this trace-only repair.

GPU qualification remains deferred.

## 6. R6 review gate

Bind a clean immutable R6 target only after exact graph/blob checks at the target
SHA. Fresh independent Review must inspect the whole assembled candidate against
accepted `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`, not merely confirm the new
edges. PASS still requires stakeholder ratification before canonical promotion.
