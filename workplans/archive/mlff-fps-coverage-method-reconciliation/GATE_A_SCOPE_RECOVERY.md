# Gate A scope recovery — reconstruction first, no speculative redesign

Date: 2026-09-14
Accepted reconstruction baseline: `e8d04144f55c72d799ffcd3fe40c75e47078a66d`
Superseded proposed semantic candidate: `df587cb161080fdc6b3f63656e2051a2708dbe47`
Disposition: **Revision-5 replacement method withdrawn from promotion. Canonical D1/D2 return to the accepted reconstructed method.**

## Governing correction

The original project task is to reconstruct the missing MLFF D1 scientific-method and D2 numerical-method papers from current and historical repository evidence, while repairing only genuine, bounded defects exposed by that reconstruction.

The Gate-A iteration exceeded that scope by replacing the proven exact target-size split/order semantics with a substantially new method, including a globally minimum exact rational condition-depletion objective `J*`, a multidimensional completion-admissibility dynamic program, new split scoring, new target-order metric semantics, and revised evaluation-ladder authority. Those changes were proposals, not recovered authority.

That redesign is not justified merely because it is attractive on paper. In particular, the proposed `OPT(i,r,b)` recurrence has combinatorial state growth in the protected-component/condition-capacity structure, whereas the accepted reconstructed split uses an exact subset-sum dynamic program with pseudo-polynomial approximately `O(C*m3)` work and `O(m3)` predecessor state. Replacing a demonstrated working algorithm with an unproven substantially harder algorithm is outside the reconstruction mandate.

## What remains accepted

The canonical D1/D2 method papers are restored to the accepted 2026-09-13 reconstruction at `e8d04144...`. This preserves the demonstrated target-size method, including:

- one exact `U_size -> P_train + M3` split preserving inherited protected components;
- exact `M3` cardinality through the existing deterministic subset-sum allocation;
- pseudo-polynomial split construction rather than the proposed multidimensional `J*` solver;
- one deterministic target-training order and exact nested `T_N` prefixes;
- the accepted evaluation ladder/reducer semantics;
- common candidate-training preparation and the existing optimizer/replay/CV/final-production semantics.

The expanded `docs/specs/analysis/local_structure_features_spec.md` reconciliation may remain because it documents already implemented local-structure formulas and numerical semantics and was explicitly reconstructed as documentation-only, with no feature-value method change. It does not authorize a new target-order metric by itself.

## Genuine issues retained for bounded repair

This recovery does **not** sweep real defects under the rug. The following distinction governs future action:

1. **Obvious reconstructibility/correctness defect:** repair locally when the intended behavior is already determined by accepted evidence and the repair does not invent a new scientific method.
2. **Concrete methodological failure with a simple existing/proven remedy:** repair narrowly, preferably by restoring/reusing the existing owner/mechanism rather than introducing new topology.
3. **Potentially nicer, more optimal, or more theoretically robust alternative:** do not promote during reconstruction. Record separately only if later runtime/qualification evidence demonstrates an actual need.

The one material issue that motivated this branch remains real and should be isolated rather than used to justify wholesale redesign: the ordinary production path can supply no target-order priority evidence, reducing the current condition-balanced order to UID tie order. If repaired, the repair should reuse/consolidate an existing proven selection/coverage mechanism and preserve the accepted split/evaluation/target-size experiment unless a concrete counterexample proves those semantics themselves defective.

No new `J*`, completion-admissibility optimization, equal-family target metric, revised `M1/M2/M3` authority, or other Revision-5 replacement semantic is accepted by this recovery.

## Qualification boundary

Production-scale or representative real-data qualification is deferred. Algorithmic analysis remains appropriate for detecting obviously infeasible proposed algorithms before implementation; it is not a reason to block reconstruction of an already demonstrated method pending a new qualification campaign.

If later execution or qualification exposes a concrete failure in the accepted reconstructed method, that failure should open a separate bounded repair at the earliest owning layer with the failing evidence attached. It should not retroactively justify speculative redesign in the reconstruction task.

## Immediate repository state

After this recovery commit:

- `docs/methods/mlff_scientific_method.md` should match accepted reconstruction blob `88096157bf6b0ed158427976977931377af5ad59`;
- `docs/methods/mlff_numerical_algorithmic_method.md` should match accepted reconstruction blob `1f531478c6bc378a8e192bca6c16d3549c610641`;
- Revision-2 through Revision-5 Gate-A artifacts remain historical challenge/proposal evidence only;
- the Revision-5 evidence record remains useful as evidence that the proposed `J*` redesign was algorithmically risky, not as a promotion gate for the accepted reconstructed method.
