# Gate A Revision 5 repair status

Date: 2026-09-14
Parent workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Implementation-repair workplan: `GATE_A_REVISION_5_IMPLEMENTATION_REPAIR_WORKPLAN.md`
D1/D2 implementation subject: `hjin98/mdstats@df587cb161080fdc6b3f63656e2051a2708dbe47`
Bound local-structure numerical specification blob: `ee7ecb7deb0412bdec5ca24b81d539e2d8ee6569`
Status: **known implementation/reconstructibility blockers repaired; Gate A remains open for required evidence, separate-context independent review, and human ratification**.

## Repaired after author-side NO-PASS review of `029653d8...`

1. **Scientific occurrence identity.** Replaced source-content-only target-order identity with `mdstats.target-order-scientific-occurrence-key.v4`, binding accepted `source_occurrence_signature`, frame index, condition, and geometry. Exact `U_size` `kappa` values are required unique; a collision fails closed rather than falling through to traversal or lexical UID order.
2. **Component numerical tie identity.** Defined `mdstats.target-order-component-tie-key.v1` from sorted member `kappa` values for singleton and multi-frame components. Numerical ties no longer depend on UID-derived P1 component serialization. P1 split-exclusion authority, projected membership, ancestry, and currentness remain separately bound and can stale the split.
3. **Analysis-owned local-structure numerical authority.** Completed `docs/specs/analysis/local_structure_features_spec.md` at its real owner with the already implemented switch, weighted-distance, entropy, radial, density, angular-Legendre, bond-orientational, missing-mask, feature-order, default-policy, and binary64/backend-equivalence semantics. The MLFF D2 paper binds exact reconciled blob `ee7ecb7deb0412bdec5ca24b81d539e2d8ee6569`; feature values were not redesigned.
4. **Canonical metric coordinate order.** D2 now defines the complete semantic accumulation key and exact family/scope/element/feature/statistic/numerical-vs-missing ordering required by left-to-right binary64 distance reduction. Provider serialization/column order is not numerical authority.
5. **Representative terminology.** Replaced ambiguous condition “medoid” terminology with **median-nearest representative**: the observed frame nearest the coordinate-wise type-7 median vector, not a minimum-total-pairwise-distance medoid.
6. **D1 layer-boundary wording.** Clarified that D1 owns one target-order metric policy/schema while D2 realizes separately fitted `d_U` and `d_P` instances on their authorized fit domains.
7. **Review oracles.** Added copied-occurrence, `kappa` uniqueness, component-key/P1-separation, provider-equation, coordinate-order/column-permutation, and median-nearest-reference checks to the D2 falsification contract and independent-review handoff.

## Previously repaired and preserved

The prior lossless repair remains intact:

- canonical D1/D2 are based on accepted baseline `e8d04144...` rather than the lossy whole-paper rewrite;
- unaffected source/strain/stress/autocorrelation/common-training/optimizer/CV/replay/final-production/dependency/precision semantics remain preserved;
- target-size candidate/fidelity/seed structural restrictions and diagnostic `m1/m2/m3` semantics remain explicit;
- only the accepted tiny fixed floating-point comparison guard supplements scientific `epsilon`;
- exact `M3` is explicitly a training-support-prioritized finite development/model-selection reserve and is not claimed to be an unbiased estimator of broader physical/deployment-population error; and
- the Revision-5 core remains exact protected split + exact rational `J*` + completion admissibility + retained-set rescoring + separate `d_U/d_P` + condition-local FPS + proportional scheduling + one exact `pi_train` + exact nested prefixes + full exact `M3` automatic decisions + diagnostic-only `M1/M2`.

## Authority state

Accepted current D1/D2 authority remains the immutable 2026-09-13 baseline at `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d` until the Gate-A proposal passes separate-context independent review and is explicitly ratified by the human owner.

On branch `design/mlff-fps-coverage-method-reconciliation`, the canonical paths

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`; and
- the reconciled analysis numerical specification used by this proposal

contain or support the **proposed assembled Gate-A candidate**, not newly accepted D1/D2 authority.

The amendment overlays, combined Revision-5 candidate, prior review records, and capability-transfer map remain provenance/cross-check artifacts; they are not the primary review subject after materialization.

## Still open by design

- representative real-feature equal-family sensitivity/ablation and bounded reweight challenge;
- representative provider/aggregation precision sensitivity;
- independent copied-occurrence, component-key, coordinate-order, and other target-order metamorphic/reference checks;
- independent exact-solver/reference evidence as required by the handoff;
- representative exact-method CPU/RAM feasibility;
- independent capability-transfer/provider-lineage audit;
- genuinely separate-context assembled D1/D2 review of exact commit `df587cb1...` and bound specification blob `ee7ecb7...`; and
- explicit human ratification after PASS FOR HUMAN RATIFICATION.

The prior bounded author-side exhaustive checks narrow concern around the exact `J*`/completion recurrence but do not count as the required separate-context Gate-A review.

Behavior-changing D3/D4 remains blocked until Gate A passes and the human owner ratifies the exact independently reviewed bundle. Production-scale GPU qualification remains deferred to final release.