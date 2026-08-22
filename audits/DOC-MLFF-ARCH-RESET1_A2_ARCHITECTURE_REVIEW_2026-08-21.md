# DOC-MLFF-ARCH-RESET1 A2 — architecture comprehension review

**Status:** PASS  
**Branch:** `docs/mlff-architecture-reset`  
**Reviewed canonical chapters:** `00`, `10`, `20`, `30`, `40`, `50`, `60`, `80`, `90`

## Structural review

The canonical architecture now reads in concept order:

1. purpose, authority, stable terminology, and workflow map;
2. scientific/statistical foundations;
3. source/data/evidence contracts;
4. evidence roles and fitted preparation;
5. training, validation, deployment, and calibration;
6. multi-view target-subset construction and target-size study;
7. bounded execution/restart/performance;
8. sole-owner and extension-boundary summary;
9. references.

The architecture no longer requires a status/gate chapter. `70_status_and_gates.md` remains absent and the canonical-source README no longer lists it.

## Semantic review

The revised chapters agree on these dependency boundaries:

- DATA7 produces fitted selection inputs and does not produce target membership.
- MVSEL2/REPAIR2 produce one repaired master order per training domain.
- MVSTATE2 is reconstructible continuation state, not a migration envelope.
- MVQUAL independently qualifies required prefixes.
- `TargetSizeStudyPolicy` distinguishes available, nominal, materializable, qualified, and selected sizes.
- selected size is protocol-global; frame membership is domain-local.
- the size study uses authorized development/model-selection evidence, exact 3/10/30 continuation, paired seeds, and typed terminal outcomes.
- held-out CV validates an already-frozen protocol and cannot select target size or checkpoint.
- old campaign generations are unsupported rather than migrated.
- fixed target-size population is represented by one sparse/master-order authority plus prefix metadata rather than duplicated product-scale state.

## Human/AI retrieval review

The front matter provides a concept-first reading and context-retrieval index. Major changed chapters state purpose/ownership and include enough local dependency context to interpret terms without consulting release history.

Part V now introduces the mathematical coverage relation before implementation identifiers, then FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL, followed by size populations and the fidelity funnel. No later caveat reverses an earlier legacy explanation.

## Remaining work intentionally deferred to later gates

- A3 must rebuild the current specification index and exact policy/schema owners; architecture prose alone cannot remove conflicting spec authority.
- A4 must consolidate useful superseded selector/repair/size/migration history and delete residue.
- A5 must restore/validate the reproducible assembled Markdown/PDF publication source chain and perform stale-marker searches/visual inspection.

## Acceptance

- **PASS:** the current workflow can be followed linearly without learning old generations first.
- **PASS:** major chapters contain local owner/dependency context suitable for targeted retrieval.
- **PASS:** no rewritten current chapter presents MVSEL1, REPAIR1, MVSTATE-REUSE1, or migration machinery as a current authority.
- **PASS:** the revised explanations are single-generation rather than amendment/caveat chains.

A3 may proceed.
