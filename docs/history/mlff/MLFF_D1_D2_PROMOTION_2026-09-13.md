# MLFF D1/D2 authority promotion - 2026-09-13

## Decision

On 2026-09-13 the human owner explicitly accepted the reconstructed MLFF D1 and D2 papers after the independent lossless reconstruction review and renderer follow-up. This promotion changes documentation authority placement; it does not introduce a new scientific method or numerical algorithm.

Current authority is now:

1. `docs/methods/mlff_scientific_method.md` - normative D1 scientific/mathematical authority.
2. `docs/methods/mlff_numerical_algorithmic_method.md` - normative D2 numerical/algorithmic authority.
3. `docs/arch_manuals/mlff_training_data_architecture.md` plus `docs/arch_manuals/mlff_training_data/` - normative D3 software architecture/integration authority constrained by D1/D2.
4. `docs/specs/training_data/` and implementation owners - D4 exact specification/concretization authority constrained by D1-D3.

## Lossless migration

The pre-promotion architecture mixed D1 scientific semantics, D2 numerical algorithms, D3 integration structure, and D4-facing implementation detail in one manual family. Promotion therefore uses the Lossless Representation Rule:

- accepted D1/D2 semantics are not rewritten or compressed during promotion;
- D3 is narrowed to component ownership, dependency/control flow, lifecycle, persistence, concurrency/resources, deployment, currentness, and interface consequences;
- exact schema/constants/source/runtime detail stays with D4 specifications and code owners;
- the full pre-promotion mixed architecture source/publication/tooling set is preserved under `docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/`; and
- the old monolithic assembler/PDF publication chain is retired from current authority rather than preserved as a parallel representation.

The current D3 entrypoint is a canonical human-facing architecture manual, with detailed D3 chapters underneath it. The reconstruction evidence and review documents remain provenance, not parallel current authority.

## Semantic preservation

No target membership, target-size policy, numerical estimator, optimizer-normalization rule, loss semantics, replay semantics, cross-validation rule, production rule, qualification boundary, or execution/resource invariant is changed by this promotion. Statements previously duplicated in D3 now route to D1/D2 rather than remaining independently tunable copies.

The detailed Part VI execution/storage architecture remains current D3 because scheduling, restart, provider lifetime, storage ownership, GPU admission, concurrency, and performance qualification are genuine software-architecture concerns. Where Part VI restates a scientific or numerical constraint, the upstream D1/D2 document controls.

## Snapshot binding

The archived pre-SSDP architecture representation is bound to:

- documentation transition parent: `cab2d4942042e0452df19d5a62f890db108ff49f`;
- semantic reconstruction/current-mdstats baseline: `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`; and
- transition/review date: `2026-09-13`.

The archive therefore preserves both the exact documentation bytes that were retired and the mdstats implementation snapshot against which the reconstruction was reviewed.

## Known lower-layer conformance challenges

Promotion does not silently repair or normalize lower-layer implementation discrepancies discovered during reconstruction. The challenge record `MLFF_D1_D2_RECONSTRUCTION_IMPLEMENTATION_CHALLENGES_2026-09-13.md` remains applicable, including:

- configuration-weight realization: the generic `ConfigurationWeightPolicy` carries more semantics than the currently visible P3/P5 fitting path appears to consume; and
- non-default atomic-reference priors: the configured atomic-number keyed prior appears at risk of being indexed by count-matrix column position in the current solver realization.

These are D3/D4 conformance questions against the accepted D1/D2 method. They are not reasons to weaken the promoted method papers. Repair, if requested, must be routed to the owning layer and should prefer reuse/rewiring of existing owners over additive duplicate machinery.

## Renderer representation

The accepted D1/D2 papers retain the renderer-safe notation established by review finding R12: textual math annotations use `\text{...}`, angstrom units use Unicode `Å` inside text labels, and unsupported `\operatorname{...}` / `\AA` markup is absent.
