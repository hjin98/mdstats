---
kind: author-repair-closure
protocol_version: 6.4.0
status: READY_FOR_FRESH_INDEPENDENT_R5_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
prior_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R4.md
prior_immutable_target: 86fa8acec3cfc84584bfbd380163545d80de7a27
primary_d4_evidence_commit: dbe6c552b216d583caf9230d2c1e0879b68f8c3e
primary_d4_evidence_run: 35300235175
confirmatory_d4_evidence_commit: 17af93877ba312600ab1bf7a2f1f2990c9c2ef00
confirmatory_d4_evidence_run: 35300268107
---

# MLFF D1/D2 Protocol-6.4 R5 repair closure

## 1. Author-side disposition

Independent Review R4 returned NO-PASS for one representation blocker only: the direct dependency trace was structurally valid but still semantically incomplete. R4 found no D1/D2 semantic defect, accepted the renderer repair and closed the D4 executable-evidence blocker.

R5 changes only the derived dependency representation and lifecycle evidence. It does not modify either proposed D1/D2 kernel or any executable D4 owner/test.

## 2. R4-B1 repair

The R5 audit applies the workplan's direct-edge criterion semantically to all 106 formal subjects rather than using row-count/resolution/acyclicity as a completeness proxy.

Fourteen edges are added across nine rows:

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

These close the R4 review witnesses and the additional same-class domain/owner omissions discovered by the complete pass.

The audit explicitly rejected false-positive over-connection: `D2.DEF.029` does not depend on `D2.DEF.020` merely because it states that its selector predicate is intentionally distinct from MVQUAL, and `D2.DEF.060A` remains a relation-selection registry rather than depending directly on every value-producing operand.

## 3. Structural and reverse-impact verification

On the repaired graph:

- all 106 formal candidate objects have exactly one trace row;
- every candidate/import prerequisite resolves;
- no object-level dependency cycle exists;
- D1 remains independent of D2 concretization;
- explicit local formal-ID references are represented except deliberate non-dependency language;
- reverse traversal now reaches numerical covered-mass descendants from `D1.DEF.015`, fold/E0 descendants from `D1.DEF.006` and `D1.DEF.024`, configured-shell repair from the configured-size owner, and monitor-separation descendants from exact configured-prefix owners.

This is author evidence only. Fresh independent R5 Review must attempt to falsify the graph again.

## 4. D4 evidence applicability

No executable file changes in R5. The R4-reviewed D4 owner/test blobs remain intended evidence targets:

- `coverage_reference.py` blob `15d20eae5a7b481d636d20fc2281c743e9abe0df`;
- focused FP64 regression blob `8da42708ac601b335dfb3c9d818c302baccb1a78`;
- real-owner suite blob `01c6d99872c136cff91777e65ce8331807f8a016`.

Passing runs `35300235175` and `35300268107` remain applicable to an R5 documentation-only descendant only if the immutable target preserves those exact blobs. The target-binding check must verify that condition before handoff.

GPU qualification is unrelated to this representation repair and remains deferred.

## 5. R5 review gate

A clean descendant containing the R5 trace, active workplan and this closure may be bound as the new immutable R5 candidate once exact blob/applicability and graph checks are repeated at that SHA.

Fresh independent Review must inspect the complete assembled candidate against accepted `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`, not merely confirm the fourteen edge additions. PASS still requires stakeholder ratification before canonical promotion.
