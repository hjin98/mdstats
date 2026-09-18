# Part VII - Ownership, qualification, and extension boundaries

## Current authority model

The MLFF documentation stack is layered:

1. D1 owns scientific meaning and admissible claims.
2. D2 owns numerical algorithms and equivalence/failure semantics.
3. D3 owns software ownership, dependency/control flow, lifecycle, persistence, concurrency, resource, and deployment structure.
4. D4 specifications/code own exact schemas, constants, parser behavior, source-specific rules, runtime adapters, and implementation details under those upstream constraints.

For the `TargetTrainingOrder` / `pi_train` surface, the accepted scoped D1/D2 owners are `docs/methods/mlff_target_training_order_scientific_method.md` and `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`; the canonical detailed D3 owner is `45_target_training_order.md`.

A lower layer may produce evidence that challenges an upstream contract, but it cannot silently redefine that contract. Historical documents, workplans, reports, and generated publications are not alternate current authorities.

## Ownership table

| Product or decision | D3 owner / integration surface | Architectural responsibility | Upstream semantic owner |
|---|---|---|---|
| source and canonical label evidence | DATA2-family source adapters/contracts | normalize external inputs into canonical evidence and immutable identity | D1/D2 |
| conditions, eligibility, raw feature/event evidence | DATA3/DATA4 families | publish canonical evidence products without selecting target membership | D1/D2 |
| evidence roles and protected relations | DATA5/P1 family | persist neutral role/relation authority for downstream consumers | D1/D2 |
| target-order raw/provider lineage inputs | DATA6/DATA7-era input surfaces under `prepare` | publish authenticated selector inputs/lineage without owning fitted selector metrics or membership | scoped target-order D1/D2 |
| target-order fitted reference | `TargetCoverageReference` owner | sole selector-specific fitted numerical product over exact `P_train` | scoped target-order D2 |
| canonical target-order obligations | prepare-derived canonical obligation owner | define one canonical locus/incidence/effective-minimum authority for FEAS/MVIDX/MVSEL/REPAIR/MVQUAL | scoped target-order D1/D2 + current P2 explicit policy |
| FEAS1 / exact neighborhood relation | shared FEAS1/NEIGHBOR1 preparation owner | compute exact geometry once on the normal path, reduce feasibility/capacity, publish authenticated NEIGHBOR1 relation | scoped target-order D2 |
| target-order sparse representation | MVIDX owner | represent exact NEIGHBOR1 and canonical-obligation incidence/correlation codes without redefining semantics | scoped target-order D2 |
| target-training order | MVSEL2/REPAIR2 under P2 preparation | construct one complete `pi_train`, repair configured shells, reconstruct exact continuation | scoped target-order D2 |
| configured-prefix membership qualification | independent MVQUAL owner feeding P2 | independently verify accepted membership predicates; no size ranking | scoped target-order D1/D2 |
| target-size split, public order/qualification projection, and common preparation | P2/P3 owners | persist one generation/public P2 definition and one common P3 preparation consumed by candidate execution | D2 |
| automatic target-size screen/reducer | P3 execution/reducer owner | schedule authorized work, persist evidence, expose recommendation/no-recommendation | D1/D2 |
| provisional design | operator through `select-target-size` / `CampaignStore` | maintain pre-freeze ordered design collection | D1 policy consequence + D3 control plane |
| frozen target bindings | `cross-validate` admission / `CampaignStore` | atomically freeze and expose immutable per-size target identities | D1/D2 consequence |
| common post-selection target monitor | P5 common-monitor owner over neutral `OUTER_MONITOR` | construct one immutable exact monitor record reused by all current CV/final P5 plans | D1/D2 |
| post-selection training-method identity | `PostSelectionMethodIdentity` owner | one current P5 training-method authority projected from trajectory-generating component owners; assessment-only policy is excluded | D1/D2 |
| training trajectory position/root | P5 training-position and runtime/completion owners | derive one pre-fit restart/root identity from already-available training-bearing inputs; fitted preparation is its descendant and exact realized preparation/runtime ancestry is authenticated separately; seal terminal TRAIN2 before assessment | D2 continuation/equivalence + D3 |
| evaluation measurement identity | EVAL2 measurement owner | publish assessment-independent checkpoint/population/metric/provider measurements sufficient for exact reuse proof | D2 |
| role hard checkpoint assessment | CV/final assessment-plan owners | bind role target ceiling, shared catastrophic replay hard policy, fixed strict-selection identity, and consume complete checkpoint measurements | D1/D2 |
| replay warning diagnostic | existing replay-policy resolver diagnostic projection | publish warning/report evidence only; no hard-decision or representative edge | D1/D2 |
| post-selection CV | P5 CV assessment owner | assess complete checkpoint universes, freeze strict representatives, evaluate held-out representatives, and publish per-size current acceptance outside sealed training roots | D1/D2 |
| P5 fitted preparation | existing atomic-reference fit owner + P5 preparation owner | realize mode-correct fit ancestry and foundation composition-transfer evidence | D2 |
| fresh final production | P5 production owner | execute or reuse training-equivalent fresh lineages only after current CV authorization; assess complete checkpoint universes and decide publication before qualification | D1/D2 |
| replay construction | replay `prepare` owner | construct/authenticate replay authority and monitor products | D1/D2 |
| training/evaluation adapter | training/MACE adapter and EVAL2 owners | realize accepted mode-specific method against external dependency/runtime | D2/D4 |
| execution/provider lifetime | stage/process owners | own schedulers, processes, providers, temporary accelerator state, restartable execution state | D3 |
| target-order pre-adoption continuation | existing `prepare` / prepared-storage lifecycle | own authenticated reconstructible MVSTATE/history/checkpoint build state without creating currentness | target-order D3/D2 identity constraints |
| storage and I/O management | `mdstats.training_data.storage` | inventory, retention, archive, deduplication, cleanup, and storage admission over owner-declared artifacts | D3/D4 |
| downstream production qualification | `mdstats.training_data.qualification` | consume one frozen final publication and publish release evidence | D1 method boundary + D3 |

A specification may refine the realization of a row but may not create a second semantic owner for the same product.

## Target-order ownership boundary

The restored target-order architecture has one direct current chain beneath `prepare`: exact `P_train` -> sole `TargetCoverageReference` -> one canonical obligation authority -> one shared FEAS1/NEIGHBOR1 construction -> MVIDX representation -> MVSEL2/configured REPAIR2/exact reconstruction -> one complete `TargetTrainingOrder` -> independent MVQUAL -> current P2 projection.

DATA6/DATA7 fitted selector metric/reference ownership is retired. MVIDX is representation, not obligation or geometry meaning. MVQUAL is admissibility evidence, not target-size model ranking. `CampaignStore` is the sole completed-generation currentness owner; pre-adoption selector checkpoints are reconstructible build state and cannot become a second currentness plane.

Manual and automatic target-size selection consume the compact prepared P2 definition. They do not reconstruct selector science. P3 screen evidence, M3, CV, replay, production, and qualification have no reverse control edge into target-order membership.


## Current P5 method, trajectory, measurement, and assessment ownership

`PostSelectionMethodIdentity` is the sole current P5 training-method authority. It contains trajectory-generating method coordinates only. Checkpoint warning/hard thresholds, CV outer acceptance, within-run strict representative ordering, and final cross-seed ordering are assessment semantics and cannot enter the training method merely because historical schemas bundled them.

Every P5 run has one pre-fit `TrainingTrajectoryIdentity` derived only from already-available training-bearing position inputs. Fitted preparation, materialization, generated training configuration, checkpoint/runtime ancestry, and the sealed run root descend from that identity. The fitted-preparation/result digest is not an input to its own parent identity; materialization/runtime/continuation authenticate that exact realized state separately. A policy-only edit reproduces the same training position, while a changed realized fitted state under the same position fails closed rather than creating a dependency cycle.

EVAL2 owns immutable `EvaluationMeasurementIdentity` records independently of assessment thresholds/full role plans. CV/final assessment owners apply the current hard policy and D2 strict-order identity to those records. Warning classification is a separate diagnostic descendant.

The broad DATA8-era `TrainingProtocolIdentity` may continue for separately current non-P5 consumers and historical provenance, but it is not a second P5 protocol graph. Likewise `TargetSizeCommonTrainingPolicy` remains a P3 owner and is not imported wholesale into P5.

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

P5 final publication consumes already-frozen hard-admissible final representatives and their authenticated target RMSE records on the exact shared common monitor. M3 is not a P5 checkpoint, ranking, currentness, plan, or publication ancestor.

Within each final seed, the representative is the D2 lexicographic minimum by `(target RMSE, epoch, checkpoint SHA-256)` over the complete hard-admissible checkpoint universe. For `single_best_final_seed`, the publication owner then chooses among frozen seed representatives by `(target RMSE, optimizer seed, checkpoint SHA-256)`. Replay warning/margin, secondary metrics, uncertainty/bootstrap, maturity, and practical-equivalence bands are diagnostics or owners for other methods only; they cannot override a lower P5 target RMSE. `all_qualified_final_seeds` remains unranked.

No second target or M3 evaluation is performed at publication. Current CV authorization is required before current final assessment/publication, including when a historically fresh final TRAIN2 trajectory is reused after exact training-equivalence proof.

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

Target-order OOC/packed sparse artifacts and pre-adoption checkpoints remain subordinate owner-declared prepared/storage products. Storage may inventory or reclaim them only through their real owner boundaries; it cannot infer selector currentness from their path or content-address alone.

P5 post-cutover run roots are closed training-only subtrees sealed at authenticated terminal TRAIN2. Current assessment objects are external descendants, not members of that root. The completion topology/anchor remain non-reclaimable owner infrastructure and retain opened-descriptor no-follow authentication, cold-storage-independent completion, idempotent proof reuse, and fail-closed tamper behavior. Already sealed historical roots are read-only; a terminal-but-unsealed historical root has one narrow append-only seal exception under the existing run-activity owner after exact authentication, with no rewrite of pre-existing bytes. A root-consuming EVAL2/reassessment holds the existing P5 run-activity exclusion for the whole numerical-read interval; storage mutation honors that owner exclusion. No second reader-lock or assessment store is introduced.

Exact filesystem layouts, record schemas, concrete lease APIs, manifests, archive codecs, and integrity procedures are D4 specification/implementation details under these constraints.

## Unsupported generations and compatibility

Obsolete target-size or campaign-derived generations are historical evidence, not alternate current execution formats. Current loaders may use narrow detection logic to reject/quarantine them before semantic reuse, but may not translate their scientific meaning into a current generation without an explicitly accepted migration design.

For the restored target order, current `candidate_independent_priority.v1` order products become stale/reconstructible at the multi-view cutover. They are rebuilt from current parents; their ranks are not migrated and no old/new selector router remains after cutover.

For restored P5, unsupported historical state includes historical weighted-stress foundation trajectories, fold-local target checkpoint-monitor records, M3-dependent P5 final plans/publications, foundation preparations missing selected-head residual/transfer evidence, incompatible replay-layout/exposure records, and broad `TrainingProtocolIdentity` payloads used as purported current P5 authority.

Independent lower-level caches or source products may be reused only through their current owners and current validation rules. A historical file existing on disk is never sufficient evidence of currentness.

## Extension rules

A future extension may change component topology, persistence, execution representation, qualification structure, or dependency realization only if it preserves all applicable D1/D2 semantics and existing external/interface constraints.

If an extension changes the scientific question, evidence interpretation, or admissible claim, reopen D1. If it changes the estimator, deterministic construction, normalization, stochastic meaning, numerical error/failure semantics, or equivalence contract, reopen D2. If it changes only architecture/component/control flow while preserving D1/D2, it is D3. Local implementation detail under unchanged D3 is D4.

Prefer one owner, direct dependency flow, and removal/rewiring of obsolete machinery over additive wrappers or synchronized duplicate authority.


## Current durable invariants

The architecture must preserve these structural properties:

1. one current authority per semantic product and dependency direction from D1/D2 through D3/D4 to evidence;
2. immutable authenticated ancestry for consequential descendants;
3. one current `P_train` and complete target-training order with exact configured prefixes;
4. sole `TargetCoverageReference` ownership, one canonical obligation authority, one shared exact neighborhood build, MVIDX as representation, and independent MVQUAL;
5. target-order pre-adoption restart state subordinate to `prepare`/prepared storage rather than CampaignStore currentness;
6. distinct target-size screening, post-selection CV, fresh production, and qualification lifecycles;
7. one current P5 training-method authority and no competing DATA8 protocol graph;
8. one acyclic pre-fit `TrainingTrajectoryIdentity`/root owner above fitted preparation/materialization/runtime; exact fitted-preparation/result ancestry is authenticated separately for continuation, and assessment-only coordinates are excluded;
9. one external campaign-common target checkpoint monitor shared by current CV and final production;
10. selected-fold membership limited to train/eval/purge roles;
11. assessment-independent target/replay numerical measurement identity sufficient to prove D2 reuse or force recomputation;
12. warning-only replay policy has no hard-admissibility, representative, CV-acceptance, production-authorization, or publication edge;
13. complete governed-checkpoint assessment precedes strict P5 representative selection;
14. `tau_CV`, `theta_CV`, `tau_prod`, replay hard/warning policy, D2.DEF.059A within-run ordering, and D2.DEF.059B aggregate publication ordering have distinct currentness scopes; final-seed assessment identity excludes current-CV authorization and 059B/publication mode;
15. post-cutover P5 run roots are training-only and sealed at authenticated terminal TRAIN2 before EVAL2 with the accepted race-safe/non-reclaimable/idempotent/tamper-fail-closed topology proof; already sealed historical roots remain read-only and the only legacy mutation is the explicitly authorized append-only seal of a terminal-but-unsealed root;
16. current CV/final assessments are immutable external descendants located through the existing CampaignStore currentness plane, never assessment files written into sealed roots;
17. root-consuming EVAL2/reassessment is excluded from concurrent archive/dedup/reclamation by the existing P5 run-activity owner;
18. historical verdicts remain immutable history; current reassessment publishes new records and historical numeric reuse requires exact D2 measurement equivalence;
19. historically fresh final production cannot become current publication input until current CV reauthorization accepts;
20. foundation-P5 fitted preparation carries only semantically consumed training ancestry/evidence and validates composition transfer;
21. final P5 publication has no M3 selection/currentness ancestry and publication membership is decided before qualification;
22. currentness is re-established from authoritative parents rather than caller snapshots, path guesses, newest-mtime selection, or store scans;
23. execution/storage/resource mechanisms cannot change D1/D2 results merely to fit a machine; and
24. unsupported historical state is rejected or retained as history rather than becoming a compatibility backdoor.
