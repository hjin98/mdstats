---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_D1_REPAIR_R2_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
failed_reviewed_candidate: 06f1255ed39f41d178daf73985829a2190a2bee8
repair_basis_review_commit: a1e086645708b273382ed3742a8788ce01592b80
d1_candidate_blob: 8667ee1abdb568a58ac945c87c9e2d7386dcf49b
scope:
  - docs/methods/mlff_scientific_method.md
---

# D1 replay-retention renewal R2 dependency trace

## 1. Status and semantics

This file is a bounded Protocol-6.4 review aid, not D1 authority. It records direct semantic prerequisites for the D1 objects changed or introduced by the replay-retention / target-admissibility renewal.

Edge direction is:

```text
SUBJECT -> DIRECT_PREREQUISITE
```

A prerequisite belongs here when changing that prerequisite can directly change the subject's denotation, domain, validity or interpretation. Transitive edges and D2/D3 realization dependencies are omitted.

The repaired canonical D1 candidate is the same-commit blob `8667ee1abdb568a58ac945c87c9e2d7386dcf49b`. Accepted-current authority remains `main@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2` until fresh independent Review PASS and exact-target stakeholder ratification.

## 2. Direct D1 dependency edges

| Subject | Direct prerequisites | Why direct |
| --- | --- | --- |
| `D1.DEF.022` | `D1.DEF.020`; `D1.DEF.021`; `D1.IMP.P5` | Exact foundation identity, replay label-mode family, and imported replay/source/exposure semantics directly define replay lineage. |
| `D1.DEF.022A` | `D1.DEF.020`; `D1.DEF.022`; `D1.IMP.P5` | Signed retention uses exact frozen `Phi`, replay lineage/monitor, and imported P5 force-RMSE evidence meaning. |
| `D1.DEF.025` | `D1.DEF.023`; `D1.DEF.024`; `D1.IMP.P5` | Role thresholds act on the common monitor / held-out fold roles imported for foundation P5. |
| `D1.DEF.026` | `D1.DEF.022A`; `D1.DEF.023`; `D1.DEF.025`; `D1.IMP.P5` | Governed checkpoint universe comes from accepted P5 cadence/fixed-budget trajectory; hard replay, common target metric and role ceiling define `H_rho`. |
| `D1.DEF.027` | `D1.DEF.026`; `D1.IMP.P5` | Final publication orders already-frozen P5 representatives under the imported publication modes. |
| `D1.AX.009` | `D1.DEF.024`; `D1.DEF.025`; `D1.DEF.026`; `D1.IMP.P5` | Fixed-budget fold positions, role thresholds and governed representative selection directly determine CV acceptance. |
| `D1.AX.010` | `D1.DEF.012`; `D1.DEF.020`; `D1.DEF.022`; `D1.DEF.022A`; `D1.DEF.023`; `D1.DEF.025`; `D1.DEF.026`; `D1.IMP.P5` | Fresh production binds selected target, exact foundation/replay lineage, common monitor, production ceiling and governed checkpoint representative. |
| `D1.AX.010A` | `D1.DEF.022A`; `D1.DEF.025`; `D1.DEF.026`; `D1.DEF.027`; `D1.AX.009`; `D1.AX.010` | Warning/hard/target/selection currentness and historical final reassessment depend directly on the amended replay, threshold, representative, publication, CV and fresh-production meanings. |

## 3. R1 finding closure map

| R1 finding | Repaired owner | Closure |
| --- | --- | --- |
| D1-R1 checkpoint universe | `D1.DEF.026` | Defines `C_rho` as every checkpoint position required by accepted cadence and durably committed by the realized fixed-budget trajectory; all members require assessment; quality-dependent shortlist/subset substitution is forbidden. |
| D1-R2 exact foundation baseline | `D1.DEF.022`, `D1.DEF.022A` | Exact frozen `Phi` is mandatory whenever replay-retention assessment is enabled, independent of replay training-label mode. |
| D1-R3 warning-only currentness | `D1.AX.010A` | `delta_warn` moves diagnostics only and cannot change hard admissibility, representative, outer-evaluation membership, CV/final authorization or publication membership. |
| D1-R4 boundary ownership | `D1.DEF.022A` | D1 retains force-error dimension and strict exceedance/inclusive-equality semantics; D2 owns only numerical realization/oracles. |
| D1-R5 TRUE_REFERENCE terminology | `D1.DEF.022A`, `D1.AX.010`, ledger/handoff | Canonical D1 role is true-reference; project DFT / `true_dft` is stated only as current realization. |
| D1-R6 renderer representation | canonical D1 file | All standalone display fences use accepted `$$ ... $$` form. |

## 4. Falsification checks for R2 re-review

Fresh re-review should specifically challenge:

1. whether `C_rho` can still be narrowed by evaluator policy, artifact availability or integrity handling rather than hard assessment;
2. whether every replay-degradation value is bound to the same exact frozen `Phi` whose inherited capability is claimed;
3. whether any warning-only threshold path can move a hard decision or publication member;
4. whether D2 can change strict/inclusive replay threshold relations or the force-error dimension;
5. whether any wording creates a third replay role distinct from accepted `TRUE_REFERENCE | FOUNDATION_PSEUDO`;
6. whether any collateral P1-P4, target-order, P3, E0/objective/exposure, monitor/fold or downstream-qualification meaning changed.

No D2/D3/D4 conclusion is carried by this trace.
