# Gate A Revision 5 repair status

Date: 2026-09-14
Parent workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Implementation-repair workplan: `GATE_A_REVISION_5_IMPLEMENTATION_REPAIR_WORKPLAN.md`
D1/D2 implementation subject: `hjin98/mdstats@029653d8f6a7001c766368bef1de6efdf2933aa8`
Status: **implementation-materialization blockers repaired; Gate A remains open for required evidence, independent review, and human ratification**.

## Repaired after NO-PASS review of `7ae141f3...`

1. Rebuilt canonical D1 and D2 from accepted baseline `e8d04144...` rather than editing the lossy whole-paper rewrite.
2. Restored unaffected accepted D2 source/strain/stress/autocorrelation/common-training/optimizer/CV/replay/final-production/dependency/precision semantics, including explicit strain formulas.
3. Preserved the Revision-5 target-order method without conceptual redesign.
4. Restored structural-policy constraints: candidate-size powers of two, three fidelity epochs, ordered unique nonnegative seeds, and minimum qualified-candidate count.
5. Defined configured diagnostic cardinalities `0 < m1 < m2 < m3`, all positive powers of two under current policy; `m1/m2` are diagnostic-only and `m3=|M3|` is the exact decision population.
6. Restored the accepted tiny fixed floating-point comparison guard beyond scientific `epsilon`; no unbounded D4 tolerance delegation remains.
7. Restored full post-selection CV failure handling and both accepted final-publication modes.
8. Added the explicit D1 limitation that exact `M3` is a training-support-prioritized finite development/model-selection reserve and is not claimed to provide an unbiased broader physical/deployment-population error estimate.
9. Added the current implementation-repair workplan and rebound the independent-review handoff to exact D1/D2 implementation commit `029653d8...`.
10. Restored the accepted D2 bibliography provenance after final verification; this did not change method semantics.

## Authority state

Accepted current D1/D2 authority remains the immutable 2026-09-13 baseline at `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d` until the Gate-A proposal passes separate-context independent review and is explicitly ratified by the human owner.

On branch `design/mlff-fps-coverage-method-reconciliation`, the canonical paths

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`

contain the **proposed assembled Gate-A candidate**, not accepted current authority.

The amendment overlays and combined Revision-5 candidate remain provenance/cross-check artifacts; they are not the primary review subject after materialization.

## Still open by design

- representative real-feature family-weight sensitivity/ablation;
- representative provider/aggregation precision sensitivity;
- independent exact-solver/reference evidence as required by the handoff;
- representative exact-method CPU/RAM feasibility;
- independent target-order metamorphics/reference checks;
- independent capability-transfer/provider-lineage audit;
- genuinely separate-context assembled D1/D2 review;
- explicit human ratification after PASS FOR HUMAN RATIFICATION.

The prior bounded author-side exhaustive checks narrow concern around the exact `J*`/completion recurrence but do not count as the required separate-context Gate-A review.

Behavior-changing D3/D4 remains blocked until Gate A passes and the human owner ratifies the exact independently reviewed bundle. Production-scale GPU qualification remains deferred to final release.