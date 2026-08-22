# Historical narrative: target-size policy evolution

**Status:** non-normative history  
**Current authority:** `docs/specs/training_data/mlff_target_subset_size_study_spec.md`

## Motivation

Target-training cardinality evolved from a loosely coupled mixture of selection budgets, progressively generated ladders, rescue sizes, and later successive-fidelity screening. The architecture reset consolidates those ideas into one typed scientific policy.

This history records why. It does not preserve old ladder schemas as current behavior.

## Early budget-derived ladders

Earlier designs allowed DATA7-style selection budgets and quota/FPS logic to determine both membership and candidate target sizes. This created two problems:

1. target membership could disagree with the later multi-view selector; and
2. a generic integer budget could become target-size authority without a clear semantic boundary.

Later multi-view work added exact coverage qualification and progressively larger candidate rungs. Rescue policies could create additional upper rungs when the initial ladder did not converge.

The resulting flexibility made the experiment harder to interpret and increased the number of persisted selector/dataset states.

## Fixed nominal population

The redesign adopts a deliberately boring fixed population:

```text
128, 256, 512, 1024, 2048, 4096, 8192, 16384
```

A rung is materializable only when every required final-development/CV training domain contains enough eligible candidates. A rung is qualified only when independent MVQUAL evidence passes every frozen hard requirement in every required domain.

This separates three questions that older designs blurred:

- how much evidence exists;
- which nominal sizes satisfy scientific coverage;
- which qualified size gives sufficient learning performance.

## Nested membership and monotone hard coverage

The current policy relies on one repaired master order per domain. Every candidate size is a prefix. This makes size the primary experimental variable instead of simultaneously changing cardinality and arbitrary subset membership.

Because prefixes only add candidates, positive hard-coverage and obligation satisfaction cannot regress with increasing size. A pass/fail/pass qualification pattern is therefore treated as an invariant violation rather than a reason to repair individual rungs independently.

## Successive fidelity

The fixed size population can still be expensive to train to full fidelity. The production policy therefore uses exact continuation at 3, 10, and 30 epochs:

```text
q qualified sizes
 -> min(q,4)
 -> 2
 -> 1
```

Candidates use the same frozen seed set and common training protocol. Ordinary target-success early stopping is disabled during the experiment so nominal size is not confounded with achieved fidelity.

Early screens use a 1 meV/Angstrom practical-equivalence width and prefer the smaller size when performance is indistinguishable. Final selection requires the complete hard-admissibility policy.

## Why rescue sizes were removed

Generated intermediate or upper rescue sizes obscure whether the predefined experiment actually converged and create additional state/materialization paths. The current policy therefore reports typed non-convergence at the available or fixed ceiling instead of synthesizing a convenient integer.

A non-convergence result is information about the available training evidence and model-learning curve, not an implementation failure to hide.

## Production versus qualification

Exhaustively training every candidate to final fidelity is useful for calibrating the screening policy but is not a reasonable default production workload. Earlier qualification experience also showed that exhaustive evidence generation can dominate disk/RAM and runtime.

The current distinction is explicit:

- production follows the bounded successive-fidelity funnel;
- release/algorithm qualification may train eliminated candidates retrospectively under a dedicated bounded qualification design to estimate survivor recall.

If the screen is unreliable, revise the screen rather than making every production campaign exhaustive.

## Durable lessons

1. Target size needs a typed policy owner independent of monitor/replay/batch/pool cardinalities.
2. Fold-local membership and protocol-global cardinality can coexist without leaking held-out fold performance into size selection.
3. Fixed candidate populations make non-convergence visible and reproducible.
4. Common fidelity boundaries and paired seeds are required for interpretable size comparisons.
5. Hard scientific admissibility should remain a constraint rather than a score bonus.
6. A scientific ladder should be represented as prefix metadata over shared state, not product-scale copies per rung.
