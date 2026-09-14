# Part IV - Training, replay, evaluation, and production integration

## Purpose and boundary

This chapter defines the D3 component and lifecycle structure that realizes the accepted training, replay, checkpoint, cross-validation, and final-production method. Scientific training semantics are D1; the numerical method is D2. D3 owns the software owners, interfaces, dependency direction, persistent products, currentness fences, and execution seams that keep those semantics from being redefined by orchestration.

Target membership and the target-size decision are upstream. This chapter cannot create a second membership or size authority.

## Training-method integration

Post-selection execution resolves one shared method identity from the accepted preparation and configuration owners, then derives role-specific plans from that identity:

```text
frozen target binding
  -> shared post-selection method identity
  -> CV policy / production policy
  -> CV plan / production plan
  -> run materialization and execution
  -> checkpoint/evaluation evidence
  -> acceptance or publication decision
```

The shared method identity records the method-bearing inputs needed to authenticate execution. Exact numerical meaning and equivalence requirements are D2. Exact fields, defaults, validation rules, and serialization are D4. There is no caller-owned shadow method identity and no independently defaulted CLI path.

## Replay ownership

Replay has one construction owner and a strict lifecycle boundary.

- `doctor` checks prerequisites and reports deferred construction-dependent facts; it does not build replay scientific products.
- `prepare` owns replay authentication, construction/reuse, deterministic split products, required prediction-dependent products when applicable, replay transport, and the independent replay monitor.
- cross-validation, final production, restart, and representative re-evaluation are consumers of the published replay authority. They may reconstruct disposable transport/index views from authenticated parents, but they do not create a new replay split, prediction authority, or qualification lineage.

Target and replay remain separate product families. A replay-only lineage change invalidates the post-selection descendants that consume it without mutating the frozen target-size evidence.

Replay current aliases are mutable locators to immutable/content-authenticated products. Publication is atomic after the required filesystem products exist, and stale builders cannot overwrite a newer current authority. External replay input is reauthenticated at the owner boundary before current aliases are published.

Execution/storage details such as prediction batch width, shard width, cache locator, graph-cache layout, progress reporting, and other representation choices remain non-semantic unless the owning D2/D4 contract says otherwise.

## Checkpoint and evaluation ownership

Checkpoint selection is a dedicated owner downstream of training evidence and upstream of held-out evaluation. It consumes only the evidence classes authorized by D1/D2. A held-out post-selection fold cannot participate in choosing the checkpoint on which it is later evaluated.

The EVAL2 owner authenticates the selected checkpoint, exact evaluation membership, target head, prediction inputs, and metric lineage before durable publication. Device batching and provider reuse are execution strategies only when they preserve the D2 numerical result under its equivalence contract.

A no-admissible-checkpoint outcome remains a typed method failure. D3 does not provide a fallback route to an inadmissible checkpoint.

## MACE adapter seam

The MACE adapter is the single dependency-facing execution seam. It owns the current package/source qualification, argument realization, loader/exposure realization, checkpoint transport, precision/backend binding, and source-shape/runtime guards required to make the pinned dependency execute the D2 method.

Dependency quirks and exact source probes belong to D4 and qualification evidence, not timeless D3 doctrine. Replacing the pinned MACE version or adapter mechanism is admissible when the replacement proves the same accepted D1/D2 semantics or explicitly reopens the affected upstream authority.

Generated model inputs and extended-XYZ/materialized views carry only the fields needed by their consumer. Longer provenance and policy ancestry remain in sidecar/persistent records rather than being encoded into a transport format as a second authority.

## Post-selection cross-validation integration

Cross-validation operates once per frozen target binding and uses fresh run lineages. For each selected size, the D3 graph is:

```text
TargetBinding_i
  -> shared method identity
  -> CV policy for i
  -> selected-only fold plan
  -> required fold/seed runs
  -> frozen representative per run
  -> held-out fold evaluation
  -> per-size CV verdict
```

The size dimension is outside the fold/seed machinery. Sibling sizes do not share fold membership, run evidence, pointers, or acceptance records. Campaign-level acceptance is all-sizes: every frozen binding must hold current accepted CV ancestry before final production is admitted.

A valid completed sibling remains reusable after another size fails or is interrupted. A scientific rejection is persisted as such; a corruption, lineage failure, or execution failure is not converted into a scientific verdict.

## Target binding versus full frozen design entry

The full frozen design entry is an audit/control-plane record and may include selection provenance and role horizons. The role-neutral `TargetBinding` is the scientific target projection consumed by P5/P7 descendants. It contains the generation/preparation ancestry, selected `N`, exact `T_N`, and canonical-order identity, but excludes sibling-list position, selection provenance, and role-specific horizons.

This decomposition prevents a production-budget edit from changing the identity of already accepted CV evidence and prevents adding a sibling selected size from changing another size's target identity.

## Fresh final production

Final production begins only after the collection-wide CV admission barrier succeeds. Every production run starts from the accepted initialization/foundation family with fresh optimizer/RNG/run state and trains the complete exact selected target binding under its production policy. Screen and CV checkpoints are not warm-start parents.

Per required production seed, the run owner publishes authenticated representative/evaluation evidence. The final-production publication owner then decides the published member set before downstream qualification. Downstream qualification consumes that publication and has no API to add, remove, or reorder members.

Current publication requires reauthentication of the current campaign revision, target binding, accepted method/CV ancestry, production plan, and produced artifacts in the same publication boundary. Superseded runs remain historical evidence but cannot install a current pointer.

## Currentness and pointer semantics

Campaign-store pointers are locators, not authority by themselves. Every public read that exposes a post-selection or production product re-resolves the current target binding and relevant method/replay lineage, then authenticates the pointed object against them.

A currentness change never deletes historical evidence merely to make status look clean. It changes which immutable descendant can be exposed as current.

## Downstream qualification boundary

Deployment parity, physical potential validation, uncertainty calibration, and locked testing are downstream consumers of the frozen final publication. Their numerical observables remain owned by their respective analysis/method families. Qualification may pass, reject, wait for reference evidence, or report unavailable capability for the exact frozen product; it cannot rewrite target selection, CV acceptance, production checkpoints, or publication membership.

The currently accepted release path is single-size. A completed multi-size experiment has multiple final products but no D1/D2/D3 rule for selecting one release winner, so consequential qualification is not silently started for that collection.

## Failure and recovery

Execution/restart may recover authenticated incomplete work under the exact same plan and parent identities. It may not repair semantic drift by rebinding a stale checkpoint, replay product, method identity, or target membership.

Provider lifetime, temporary accelerator state, caches, and materialized transport are owned and retired by their D3/D4 lifecycle owners. Garbage collection is not an ownership mechanism.
