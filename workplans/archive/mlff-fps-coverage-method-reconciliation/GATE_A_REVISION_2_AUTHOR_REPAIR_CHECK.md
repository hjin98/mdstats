# Gate A Revision 2 author-side repair check

Date: 2026-09-13
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 2
Basis review: `GATE_A_INDEPENDENT_D1_D2_REVIEW.md`
Status: author-side repair check; **not independent acceptance evidence**.

## Closure check against independent findings

- B1: CLOSED IN PROPOSAL. Evaluation condition-frame scheduler removed. `pi_eval` is a frozen simple-random-sample-without-replacement frame-cluster permutation; the prefix EVAL2 statistic is explicitly a ratio estimator for the exact M3 force-component ratio of totals.
- B2: CLOSED IN PROPOSAL. Finite-population sampling interpretation, design consistency, zero M3 sampling error, and a diagnostic linearization uncertainty route are explicit.
- B3: CLOSED IN PROPOSAL. Split now has a label-blind exact objective: among exact feasible protected-component subsets, minimize additive neutral-condition depletion `sum_g sum_c n(g,c)/N_c`. Geometry is deliberately excluded from split scoring to avoid circular fitting.
- B4: CLOSED IN PROPOSAL. `mu_sel`, `mu_loss`, and `mu_eval` are distinct and the training weight-policy identity is frozen without feeding fitted weights backward into membership.
- B5: CLOSED ENOUGH FOR RE-REVIEW, NOT SELF-PROVEN. D1 coverage claim is narrowed to frame-level raw + material-neutral structural summaries. Metric weighting is by named semantic family with equal prior family mass; sensitivity/ablation and rare-local-structure falsification remain mandatory independent evidence.
- B6: CLOSED IN PROPOSAL. Type-7 quantiles, fixed coordinate traversal, coordinate-median medoid, exact integer condition deficits, exact length-prefixed SHA-256 encoding, and dimension-aware FP64 equivalence bounds are explicit.
- G1: CLOSED. Condition anchors are a method feasibility invariant, not optional hard qualification.
- G2: CLOSED. N is configuration cardinality; correlation/effective independence remains split/diagnostic evidence with an explicit limitation.
- G3: CLOSED. Occurrence-lineage sensitivity is declared; evaluation random priority uses geometry before occurrence tie.
- G4: CLOSED. Target-order-dependent stale descendants and preserved unrelated evidence are enumerated.

## New self-challenge points deliberately left for independent review

1. The neutral-condition depletion objective is additive and intentionally does not optimize geometry. Independent review should attempt a case where additive depletion still harms a scientifically scarce cross-condition structure and decide whether the narrowed D1 claim makes that acceptable.
2. Equal semantic-family metric mass is a symmetry/no-prior baseline, not empirically proven optimal. Material instability under reasonable family regrouping is a D2 blocker.
3. The proposed `8*gamma_d` distance equivalence and `32*u` scale-degeneracy envelopes require higher-precision falsification; they must not be accepted because they are written down.
4. The SRSWOR ratio estimator can be noisy or biased at small m when atom count and error are strongly associated. The uncertainty fixture must quantify this and determine whether configured M1/M2 remain scientifically useful; if not, evaluation sizes or estimator design must reopen at D1/D2 rather than being patched in D4.
5. Source-repackaging sensitivity is now explicit, but independent review should verify that the chosen scientific identity does not let irrelevant source-path changes steer non-tied training membership.

## Disposition

Revision 2 is **ready for a fresh independent Gate A review**, not ready for promotion. Permanent D1/D2 and D3/D4 behavior remain unchanged until that review passes and the human owner ratifies the resulting method.