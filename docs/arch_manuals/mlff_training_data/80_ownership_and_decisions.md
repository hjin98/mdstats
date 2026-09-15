# Part VII - Ownership, qualification, and extension boundaries

## Current authority model

The MLFF documentation stack is layered:

1. D1 owns scientific meaning and admissible claims.
2. D2 owns numerical algorithms and equivalence/failure semantics.
3. D3 owns software ownership, dependency/control flow, lifecycle, persistence, concurrency, resource, and deployment structure.
4. D4 specifications/code own exact schemas, constants, parser behavior, source-specific rules, runtime adapters, and implementation details under those upstream constraints.

A lower layer may produce evidence that challenges an upstream contract, but it cannot silently redefine that contract. Historical documents, workplans, reports, and generated publications are not alternate current authorities.

## Ownership table

| Product or decision | D3 owner / integration surface | Architectural responsibility | Upstream semantic owner |
|---|---|---|---|
| source and canonical label evidence | DATA2-family source adapters/contracts | normalize external inputs into canonical evidence and immutable identity | D1/D2 |
| conditions, eligibility, raw feature/event evidence | DATA3/DATA4 families | publish canonical evidence products without selecting target membership | D1/D2 |
| evidence roles and protected relations | DATA5/P1 family | persist neutral role/relation authority for downstream consumers | D1/D2 |
| pre-order fitted selection evidence | DATA6/DATA7 family | publish fit-domain-bound ordering inputs | D2 |
| target-size split, orders, and common preparation | P2/P3 owners | persist one generation and one common P3 preparation consumed by candidate execution | D2 |
| automatic target-size screen/reducer | P3 execution/reducer owner | schedule authorized work, persist evidence, expose recommendation/no-recommendation | D1/D2 |
| provisional design | operator through `select-target-size` / `CampaignStore` | maintain pre-freeze ordered design collection | D1 policy consequence + D3 control plane |
| frozen target bindings | `cross-validate` admission / `CampaignStore` | atomically freeze and expose immutable per-size target identities | D1/D2 consequence |
| common post-selection target monitor | P5 common-monitor owner over neutral `OUTER_MONITOR` | construct one immutable exact monitor record reused by all current CV/final P5 plans | D1/D2 |
| post-selection method identity | `PostSelectionMethodIdentity` owner | one current P5 method authority projected from real component owners | D1/D2 |
| role checkpoint admissibility | method (shared constraints) + CV/final role policy (target ceiling), composed once per authenticated run plan | one effective admissibility policy per run; no second threshold owner | D1/D2 |
| post-selection CV | P5 CV owner | build selected-only train/eval/purge fold plans, bind external common monitor, and publish per-size acceptance | D1/D2 |
| P5 fitted preparation | existing atomic-reference fit owner + P5 preparation owner | realize mode-correct fit ancestry and foundation composition-transfer evidence | D2 |
| fresh final production | P5 production owner | run fresh production using same common monitor and decide publication membership before qualification | D1/D2 |
| replay construction | replay `prepare` owner | construct/authenticate replay authority and monitor products | D1/D2 |
| training/evaluation adapter | training/MACE adapter and EVAL2 owners | realize accepted mode-specific method against external dependency/runtime | D2/D4 |
| execution/provider lifetime | stage/process owners | own schedulers, processes, providers, temporary accelerator state, restartable execution state | D3 |
| storage and I/O management | `mdstats.training_data.storage` | inventory, retention, archive, deduplication, cleanup, and storage admission over owner-declared artifacts | D3/D4 |
| downstream production qualification | `mdstats.training_data.qualification` | consume one frozen final publication and publish release evidence | D1 method boundary + D3 |

A specification may refine the realization of a row but may not create a second semantic owner for the same product.

## Current P5 authority versus DATA8 historical/general identity

`PostSelectionMethodIdentity` is the sole current P5 method authority. Current P5 plans, fitted preparations, materializations, run evidence, CV verdicts, and final publications descend from it.

The broad DATA8-era `TrainingProtocolIdentity` may continue to serve separately current non-P5 consumers that still explicitly depend on that representation and may remain readable as historical provenance. It is not a second P5 protocol graph and cannot authorize restored P5 merely because an old payload validates or deserializes.

Likewise, `TargetSizeCommonTrainingPolicy` remains a P3 owner. Foundation P5 may project genuinely shared components from common owners, but it does not bind the whole P3 policy digest or inherit P3-only objective/weighting/harness values.

## Common-monitor and selected-fold ownership

The common target checkpoint monitor is external to selected-fold membership. Its owner constructs one immutable monitor record from the neutral authorized `OUTER_MONITOR` parent under the accepted D2 sampler. Current CV and final plans all bind that same record digest.

The P1 protected-relation owner then proves cross-role separation between the realized monitor and every governed selected target membership. Monitor sampling and relation separation are separate ordered responsibilities; a relation conflict fails plan admission rather than mutating/resampling the monitor.

Selected-fold membership is limited to gradient training, held-out outer evaluation, and accepted purge/exclusion. Fold-local target checkpoint-monitor ownership is retired from current P5.

## Foundation-P5 preparation ownership

The existing atomic-reference fitter remains the sole E0 solver. Foundation adaptation uses selected-foundation-head residual inputs and P5 fitted preparation owns the downstream composition-transfer validation required for training/checkpoint/evaluation consumer compositions.

Foundation-P5 fitted preparation has no P3 objective-policy or fitted-configuration-weight authority. If scratch and foundation share one implementation schema, the representation is mode-disjoint and fail-closed: fields forbidden in one mode cannot be silently populated, ignored, defaulted, or included in current content identity.

The exact common-monitor record must exist before a foundation-P5 preparation can become current because the monitor's composition classes are governed transfer consumers. Monitor/held-out labels remain excluded from the fit.

## MACE execution ownership

The MACE adapter remains the only dependency-facing execution seam. It resolves loss/exposure by authenticated method mode:

- P3 target-size screening keeps its accepted weighted complete-batch realization;
- P5 scratch keeps its separately accepted weighted method;
- naive and multihead foundation P5 realize native MACE UniversalLoss with the accepted fixed objective and foundation exposure geometry.

A global loss-family mutation is not a valid owner change. Foundation P5 also remains on the qualified single-process path until a distributed realization is separately accepted as D2-equivalent.

## Final publication ownership

P5 final publication consumes already-frozen admissible final representatives and their already-authenticated target metric records on the exact shared common monitor. M3 is not a P5 checkpoint, ranking, currentness, plan, or publication ancestor.

`single_best_final_seed` reuses the accepted target-only representative-ordering semantics, including deterministic uncertainty/materiality/secondary/maturity/tie handling where applicable. It does not replace that policy with raw scalar-RMSE sorting and does not rerun target or M3 evaluation. `all_qualified_final_seeds` publishes the already-admissible required representatives without cross-seed ranking.

A separately authorized downstream M3 development/qualification probe remains a P3 descendant and does not feed back into P5 publication identity.

## Qualification as a downstream consumer

Qualification begins from an already frozen and published final product. Its integration graph is:

```text
current TargetBinding
  -> accepted post-selection CV
  -> accepted final-production publication decision
  -> QualificationInputBinding
  -> qualification plan / attempt
  -> deployment and physical-validation component evidence
  -> terminal qualification record / release evidence index
```

`QualificationInputBinding` authenticates the exact publication/member set, executable candidate identity, target-machine/environment identity as required by the current contract, frozen qualification specification, and evidence-role membership. Qualification does not own publication membership and performs no cross-seed or cross-size model selection.

The numerical definitions of physical observables remain with their analysis/method owners. Qualification coordinates those owners and binds their evidence to the frozen candidate.

Locked evidence has an explicit irreversible activation owner. Opening locked evidence is not itself proof that evaluation completed; the reveal history remains durable even if the current qualification lineage later becomes historical.

Missing external reference evidence is represented as a waiting state rather than a fabricated pass. An unavailable supported deployment capability is reported as unavailable/blocking rather than as scientific rejection.

## Qualification persistence

Qualification evidence is generation-scoped and split between immutable/content-authenticated evidence objects and attempt-local state/scratch. Currentness is derived from current P4/P5/P7 parents and a campaign-store pointer used only as a locator.

A terminal verdict produced for a stale publication, specification, executable identity, or environment remains historical and cannot be exposed as current. Locked-reveal history is append-only and is not reset by currentness changes.

## Storage handoff

Storage consumes owner-provided views rather than inferring authority from paths. It may reclaim, archive, deduplicate, restore, or report only within the artifact boundaries and retention references declared by the real owners.

Key rules are architectural:

- observation and mutation are separate invocation capabilities;
- retention is a transitive closure across current/restartable owner references;
- publication barriers prevent storage from racing a product between immutable-object publication and current-pointer installation;
- containment alone is not ownership of descendants;
- cold archive changes representation, not scientific currentness;
- audit state and storage control-plane records do not become scientific authority; and
- ambiguous ownership is retained/fail-closed rather than guessed.

Exact filesystem layouts, record schemas, leases, manifests, archive codecs, and integrity procedures are D4 specification/implementation details under these constraints.

## Unsupported generations and compatibility

Obsolete target-size or campaign-derived generations are historical evidence, not alternate current execution formats. Current loaders may use narrow detection logic to reject/quarantine them before semantic reuse, but may not translate their scientific meaning into a current generation without an explicitly accepted migration design.

For restored P5 this includes, at minimum, historical weighted-stress foundation trajectories, fold-local target checkpoint-monitor records, M3-dependent P5 final plans/publications, foundation preparations missing selected-head residual/transfer evidence, incompatible replay-layout/exposure records, and broad `TrainingProtocolIdentity` payloads used as purported current P5 authority.

Independent lower-level caches or source products may be reused only through their current owners and current validation rules. A historical file existing on disk is never sufficient evidence of currentness.

## Extension rules

A future extension may change component topology, persistence, execution representation, qualification structure, or dependency realization only if it preserves all applicable D1/D2 semantics and existing external/interface constraints.

If an extension changes the scientific question, evidence interpretation, or admissible claim, reopen D1. If it changes the estimator, deterministic construction, normalization, stochastic meaning, numerical error/failure semantics, or equivalence contract, reopen D2. If it changes only architecture/component/control flow while preserving D1/D2, it is D3. Local implementation detail under unchanged D3 is D4.

Prefer one owner, direct dependency flow, and removal/rewiring of obsolete machinery over additive wrappers or synchronized duplicate authority.

## Current durable invariants

The architecture must preserve these structural properties:

1. one current authority per semantic product;
2. immutable authenticated ancestry for downstream evidence;
3. no downstream feedback path that silently changes frozen target selection or method identity;
4. distinct target-size screening, post-selection CV, fresh production, and qualification lifecycles;
5. one external campaign-common target checkpoint monitor for current P5, shared by CV and final production;
6. selected-fold membership contains train/eval/purge, not target checkpoint-monitor membership;
7. one current P5 method identity and no competing DATA8 protocol authority;
8. foundation-P5 fitted preparation carries only semantically consumed P5 ancestry/evidence and validates composition transfer;
9. final P5 publication has no M3 selection/currentness ancestry;
10. final publication membership is decided before qualification;
11. currentness is re-established from authoritative parents rather than caller-held snapshots;
12. execution/storage/resource mechanisms cannot change D1/D2 results merely to fit a machine; and
13. unsupported historical state is rejected or kept historical rather than becoming a compatibility backdoor into current authority.