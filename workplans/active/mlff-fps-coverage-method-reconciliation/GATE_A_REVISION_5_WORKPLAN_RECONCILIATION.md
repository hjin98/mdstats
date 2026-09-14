# Gate A Revision 5 — workplan reconciliation after repair review

Date: 2026-09-14
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Candidate: Revision 5
Parent branch head reviewed before this repair: `10d47a48db209c9b14a17ab46e90dbc765875fa2`
Lifecycle: cycle-scoped coordination amendment; **not D1/D2 authority**

## 1. Purpose

This record reconciles the parent workplan with the resolved Revision-5 proposal without rewriting the historical plan. The parent remains the full scope owner. This file is the current Gate-A delta where Revision 5 has deliberately changed an earlier workplan option or where the repair review found a missing promotion artifact.

No D3/D4 behavior is authorized by this record.

## 2. Gate-A method state

The following Revision-5 choices now define the proposal submitted to independent review:

- `pi_train` is one deterministic coverage-progressive training order and every configured target membership is an exact prefix;
- `M3` is one exact model-selection reserve and exact full `M3` EVAL2 is used at every automatic training-fidelity boundary;
- `pi_eval`, `M1`, and `M2` are diagnostic probability-sampling evidence only;
- `pi_eval` therefore no longer owns automatic ranking/elimination/recommendation semantics and need not be deterministic before its randomization event; its **method and realized randomization evidence are reproducible/persisted**, while changing only that diagnostic realization cannot change target-size reducer identity;
- split selection preserves hard condition support and exact cardinality, minimizes exact condition-depletion cost globally, then uses dynamically recomputed retained-set structural redundancy only among completion-admissible choices;
- target membership does not consume foundation predictions, label-derived difficulty, mass density, material/profile pair-rule coordinates, or declared/profile groups;
- equal active semantic-family mass is a proposed no-prior metric baseline and still requires independent real-feature sensitivity/ablation evidence.

This supersedes parent-workplan language that still describes one deterministic `pi_eval` as the automatic nested `M1/M2/M3` decision ladder. That earlier wording remains historical context for why Gate A was reopened, not the current Revision-5 proposal.

## 3. Promotion-package repair

The parent Gate-A requirement to draft both D1 and D2 amendments is now represented by:

- `GATE_A_REVISION_5_D1_METHOD_AMENDMENT.md`;
- `GATE_A_REVISION_5_D2_METHOD_AMENDMENT.md`.

The D2 overlay is an exact application map against `docs/methods/mlff_numerical_algorithmic_method.md`; a reviewer no longer needs to infer permanent-paper edits from the combined D1/D2 candidate.

The D2 overlay also replaces the abstract exact completion-oracle wording with a reconstructible exact reference algorithm:

- canonical component order;
- exact rational depletion contributions;
- sparse memoized state `(component_index, remaining_cardinality, residual_condition_capacities)`;
- include/exclude recurrence;
- exact `J*`;
- exact residual-optimum test for completion admissibility;
- no floating objective/feasibility tolerance and no semantic approximation.

Alternative D3/D4 solvers remain delegated only if they are independently proven exact-equivalent to this reference result/predicate.

## 4. Gate-A evidence contract

The following are **promotion blockers until independently realized/assessed**:

1. real-feature equal-family weighting sensitivity/ablation on representative current target-order evidence;
2. representative provider/aggregation/transform precision sensitivity;
3. exhaustive bounded split fixtures comparing exact `J*` and completion admissibility to direct subset enumeration, including infeasible and multiple-optimum cases;
4. mutual-redundancy retained-set counterexample;
5. occurrence-key/UID/source/input/feature-column metamorphic checks under their stated invariance preconditions;
6. scalar medoid/FPS/proportional-scheduler reference checks;
7. exact-full-`M3` decision invariance to diagnostic `pi_eval` realization;
8. representative supported CPU/RAM feasibility for descriptor preparation, the exact split/completion algorithm, retained-set scoring, and K-bounded FPS;
9. independent audit of the capability-transfer map and bound local-structure numerical-contract lineage; and
10. a genuinely separate-context independent D1/D2 Challenge/Review over the assembled Revision-5 candidate, both amendment overlays, capability-transfer map, and applicable evidence.

A required unavailable check is **not a pass**. Author-side records may establish that a proposed rule is internally executable on bounded fixtures but do not satisfy the independent-PASS requirement.

## 5. Resource-feasibility interpretation

The repaired exact split problem is no longer claimed to have the old pseudo-polynomial `O(C*m3)` complexity. Its worst case can grow combinatorially with protected-component and condition-capacity structure.

Gate A therefore requires representative CPU/RAM feasibility rather than an invented wall-time threshold. The reviewer should record input dimensions, component-size distribution, number of represented conditions, `m3`, explored/memoized states, wall time, and peak RAM for representative supported cases. A result showing the exact method is operationally infeasible in the supported regime reopens D2.

The repair must not be made to pass by weakening condition retention, changing exact reserve cardinality, approximating `J*`, skipping completion-admissibility checks, or substituting a floating solver whose result is not exact-certified.

Production-scale GPU qualification remains deferred under the established project policy because Gate A's repaired ordering method is CPU/statistical and introduces no GPU-dependent numerical semantics.

## 6. Historical Applicability Set continuity

The parent workplan HAS remains applicable without change:

- `SP-001` APPLICABLE — consolidate responsibility rather than recreate selector topology;
- `FF-005` APPLICABLE — preparation owns target-order scientific state; downstream consumers must not reconstruct it;
- `SP-002` APPLICABLE — identity/currentness must fail closed;
- `SP-003` APPLICABLE — immutable prepared-generation reuse;
- `SP-004` APPLICABLE — later D3/D4 acceptance must traverse the real owner/integration boundary;
- `FF-001` through `FF-004` remain non-owning for this Gate-A method repair.

Accepted PEM basis remains `hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md`. No new PEM claim is created by this proposal-stage repair.

## 7. Gate state after this repair

- Revision-5 D1 amendment overlay: **materialized**.
- Revision-5 D2 amendment overlay: **materialized by this repair**.
- Exact D2 split/completion reference semantics: **materialized in proposal form**.
- Capability-transfer map: **materialized; independent audit pending**.
- Author-side bounded fixtures: **partial; not independent acceptance**.
- Required independent evidence suite: **pending**.
- Separate-context independent D1/D2 PASS: **pending**.
- Human ratification: **pending**.
- Permanent D1/D2 mutation: **blocked**.
- Behavior-changing D3/D4 implementation: **blocked**.

The next admissible action is execution of the Gate-A independent evidence/review handoff on the exact repaired candidate revision. Human ratification follows only if that review passes.
