---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_R5_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 058b856df249bd28212ba70e459babd1f29a6c42
prior_candidate_target: 86fa8acec3cfc84584bfbd380163545d80de7a27
prior_review_result: R4_NO_PASS
branch: design/mlff-d1-d2-ssdp64-axiomatic-formalization
primary_d4_evidence_commit: dbe6c552b216d583caf9230d2c1e0879b68f8c3e
primary_d4_evidence_run: 35300235175
confirmatory_d4_evidence_commit: 17af93877ba312600ab1bf7a2f1f2990c9c2ef00
confirmatory_d4_evidence_run: 35300268107
---

# Independent Review R5 handoff — MLFF D1/D2 Protocol-6.4 formalization

## 1. Binding and independence

Perform a fresh full Protocol-6.4 assembled-candidate Review of immutable target

`058b856df249bd28212ba70e459babd1f29a6c42`

against accepted basis

`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

Treat this handoff, the R5 repair closure, all prior reviews, CI outcomes and PR comments as evidence/challenge material only. Do not inherit author or prior-review conclusions.

At handoff preparation the accepted `main` basis remained exactly `cb07d683...`.

## 2. Candidate surface

The semantic kernels are intentionally unchanged from R4/R3:

- D1: `workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`, blob `dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498`;
- D2: `workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`, blob `74c0c0588617b7f48fd93bc21e534f538f037ef8`.

R5 representation/evidence surface:

- `workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R5_FINAL.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_R5_REPAIR_CLOSURE.md`;
- active workplan and R4 independent-review record.

Executable evidence targets are unchanged:

- `mdstats/training_data/target_order/coverage_reference.py`, blob `15d20eae5a7b481d636d20fc2281c743e9abe0df`;
- `tests/test_mlff_target_order_weighted_quantiles_fp64.py`, blob `8da42708ac601b335dfb3c9d818c302baccb1a78`;
- `tests/test_mlff_target_order_real_owner.py`, blob `01c6d99872c136cff91777e65ce8331807f8a016`.

No temporary validation workflow is present in the immutable R5 target.

## 3. R5 trace repair to challenge independently

R4 found that structural graph checks had not established semantic directness. R5 adds fourteen direct edges across nine rows:

```text
D1.DEF.015 -> D1.DEF.008

D1.DEF.016 -> D1.DEF.005
D1.DEF.016 -> D1.DEF.008
D1.DEF.016 -> D1.DEF.015

D1.DEF.017 -> D1.DEF.009
D1.DEF.017 -> D1.DEF.014

D1.AX.007 -> D1.DEF.009

D1.DEF.023 -> D1.DEF.009
D1.DEF.023 -> D1.DEF.012

D1.DEF.024 -> D1.DEF.006

D2.DEF.019 -> D1.DEF.015

D2.DEF.034 -> D2.DEF.007

D2.DEF.041 -> D1.DEF.024
D2.DEF.041 -> D1.AX.010
```

Fresh review must not assume those edges are sufficient. Re-audit every one of the 106 formal subjects under the workplan criterion: a direct prerequisite is required when changing it can directly change the subject's denotation, domain, validity or interpretation; genuinely mediated effects remain transitive and should not be hand-duplicated.

Challenge in particular:

1. D1 scientific-domain dependencies for `P_train`, configured sizes, required family sets, obligations, role vocabulary, monitor separation and fold roles;
2. D2->D1 concretization edges for covered mass, qualification, E0 fit domains, monitor/fold/checkpoint semantics and fresh production;
3. configured-shell ownership in REPAIR2;
4. catch-all/currentness/continuation/failure objects;
5. the intentional non-edge `D2.DEF.029 !-> D2.DEF.020`: the former explicitly says its selector predicate is distinct from MVQUAL, so mere mention is not a prerequisite;
6. the intentional bounded registry semantics of `D2.DEF.060A`: do not connect every value-generating operand unless it actually defines the comparison relation.

Verify one row per formal object, exact endpoint/source closure, acyclicity, abstraction direction and reverse-impact reachability from fixed/configurable/derived anchors.

## 4. D1/D2 full review remains required

Reconstruct accepted D1/D2 from the four canonical method papers at the accepted basis and reattempt all substantive surfaces from prior reviews, including source/label physics, protected evidence roles, exact target-size experiment, target-order family/coverage/obligation semantics, P3 normalization/reducer/restart, foundation objective/E0/replay, monitor/CV/production threshold semantics, continuation/equivalence/fail-closed behavior and D2->D3 handoff.

Do not convert the trace-only R5 delta into a delta-only review. A kernel defect discovered during R5 remains a genuine blocker/Challenge even though author repair did not change those blobs.

## 5. D4 evidence applicability

R4 closed the D4 executable blocker. Passing runs:

- `35300235175` at `dbe6c552b216d583caf9230d2c1e0879b68f8c3e`;
- `35300268107` at `17af93877ba312600ab1bf7a2f1f2990c9c2ef00`.

Both passed:

```text
pytest -q tests/test_mlff_target_order_weighted_quantiles_fp64.py
pytest -q tests/test_mlff_target_order_real_owner.py
```

R5 target binding checks show the D4 owner, focused regression and real-owner suite blobs are exactly identical to both evidence commits. Differences from the evidence commits are documentation/review records plus removal of the temporary workflow. Review should independently recheck that applicability before reusing the evidence. No executable rerun is required merely because the dependency trace changed.

GPU qualification remains outside this CPU/documentation repair and is deferred by project policy.

## 6. Renderer, PEM/HAS and lifecycle

Recheck renderer-safe equivalence and current PEM/HAS applicability rather than inheriting prior PASS.

Return PASS only if the complete immutable R5 candidate is losslessly equivalent to accepted D1/D2, dependency/source closed and evidence-current. Otherwise return NO-PASS with precise owner-level repair instructions.

A PASS does not self-promote. Stakeholder ratification of the exact reviewed target remains required before canonical D1/D2 promotion. Do not merge from handoff alone.
