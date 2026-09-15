---
title: "mdstats MLFF Training-Data Architecture"
artifact_level: "D3 software architecture and integration"
status: "current normative D3 architecture"
accepted_date: "2026-09-15"
---

# mdstats MLFF Training-Data Architecture (D3)

## 1. Purpose and authority

This manual is the current D3 software-architecture authority for the machine-learned force-field (MLFF) branch of mdstats. It replaces the former pre-SSDP architecture manual that mixed scientific formulation, numerical algorithms, software architecture, and source-specific implementation detail in one document family.

The current authority chain is directional:

1. **D1 - scientific/mathematical authority:** `docs/methods/mlff_scientific_method.md`, with `docs/methods/mlff_target_training_order_scientific_method.md` as the accepted scoped owner for `TargetTrainingOrder` / `pi_train` scientific meaning.
2. **D2 - numerical/algorithmic authority:** `docs/methods/mlff_numerical_algorithmic_method.md`, with `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md` as the accepted scoped owner for target-training-order numerics.
3. **D3 - software architecture/integration authority:** this manual and the detailed chapter set under `docs/arch_manuals/mlff_training_data/`, including `45_target_training_order.md` as the canonical detailed D3 owner for the restored target-order subsystem.
4. **D4 - exact specification/concretization authority:** `docs/specs/training_data/` and the implementation owners it indexes.

D3 owns subsystem decomposition, dependency and control flow, lifecycle boundaries, interfaces, durable state and currentness, persistence/recovery, concurrency/resource topology, deployment seams, and architectural compatibility. D3 may restate a D1/D2 consequence where local comprehension requires it, but such restatement is not independently tunable authority.

The exact pre-promotion mixed architecture, including its chapter sources, assembled Markdown, PDF, PDF manifest, dependency graph, publication configuration, and assembler, is preserved under `docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/`. That snapshot is historical provenance only.

## 2. Architectural pipeline

The current MLFF path is:

```text
external source evidence
  -> source adapters
  -> canonical frame/label/condition evidence
  -> neutral evidence roles and protected relations
  -> exact P_train + M3 split
  -> target-order selector inputs on exact P_train
  -> sole fitted TargetCoverageReference
  -> one canonical membership-obligation authority
  -> one shared FEAS1/NEIGHBOR1 construction
  -> MVIDX representation
  -> MVSEL2 / configured REPAIR2 / exact reconstruction
  -> one complete TargetTrainingOrder + independent MVQUAL
  -> current P2 public target-size definition
  -> one common target-size training preparation
  -> optional target-size diagnostic screen/reducer
  -> operator-owned provisional design
  -> cross-validate admission and atomic target-binding freeze
  -> campaign-common post-selection target monitor
  -> post-selection cross-validation
  -> fresh final production and publication decision
  -> downstream production qualification
```

`pi_eval/M1/M2/M3` remain under their existing current owners. The restored target-order subsystem is candidate-outcome independent: target-size model outcomes, M3, CV, replay, production, and qualification evidence have no reverse edge into target membership.

The architecture deliberately prevents reverse control. Post-selection CV cannot reselect a target membership. Qualification cannot choose publication members. Storage cannot create scientific currentness. Runtime adapters cannot redefine D1/D2 semantics merely because an external dependency behaves differently.

## 3. Package and subsystem ownership

The principal package-level boundaries are:

- `mdstats.data`: canonical source/frame evidence and source-normalization interfaces;
- `mdstats.sampling`: shared correlation/sampling primitives used by MLFF owners;
- `mdstats.training_data`: MLFF evidence construction, target-order selection, campaign state, persistence, orchestration, replay preparation, storage, and qualification integration;
- `mdstats.training`: training/checkpoint/evaluation execution seams, including the qualified MACE adapter and evaluation owners; and
- `mdstats.cli`: operator-facing composition only; command routing must not become a second semantic owner.

Detailed D3 ownership is in `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`.

## 4. Canonical evidence and adapter boundary

External-source conventions are translated once at source-adapter boundaries. Central MLFF components consume canonical evidence rather than rediscovering VASP-, ASE-, MACE-, path-, or file-layout-specific semantics.

Downstream artifacts bind immutable upstream identities. Membership-bearing products bind exact member and parent identities. Fitted products additionally bind their authorized fit domain and method/policy identity. Cache identifiers, file paths, and display metadata are not authority unless an owning contract explicitly promotes them.

The architecture distinguishes authoritative evidence, fitted method products, restartable execution state, generated reports, and disposable caches/scratch. Cleanup and storage decisions preserve those classes rather than inferring importance from pathname or age.

See `20_data_contracts.md` for the D3 evidence/integration boundary. Scientific label meaning is owned by D1; numerical identity construction is owned by D2; exact serialized records and adapter behavior are D4.

## 5. Statistical and fitted-product integration

The architecture keeps target-order selector fitting and common target-size training preparation separate.

For the restored `pi_train` path, DATA6/DATA7-era surfaces may provide authenticated raw/provider/lineage inputs, but `TargetCoverageReference` is the **sole selector-specific fitted numerical product** on exact `P_train`. One canonical membership-obligation authority is projected once from accepted automatic evidence plus current P2 explicit support policy. FEAS1, MVIDX, MVSEL2/REPAIR2, and MVQUAL consume or represent that authority; they do not create competing definitions.

The exact target-order architecture is owned by `45_target_training_order.md`. The normal prepared path computes the exact NEIGHBOR1 relation once, exposes FEAS1 reductions from that shared construction, and lets MVIDX adopt/invert the authenticated relation rather than recomputing geometry.

After the target-size split/orders exist, **common target-size training preparation** is constructed once and is shared unchanged across P3 candidate sizes where D2 requires common fitted state. Candidate projection is downstream of common P3 preparation and cannot become a hidden refit owner.

Post-selection foundation adaptation has a separate fitted-preparation lineage. It projects only genuinely shared component owners; it does not bind the whole P3 common-training policy. The existing atomic-reference fitter remains the sole E0 solver, while P5 fitted preparation binds selected-foundation-head residual inputs and the composition-transfer evidence required by D2.

See `30_statistical_design.md` for producer/consumer, fitted-product, common-monitor, and invalidation structure. Exact estimators and deterministic constructions remain D2 authority.

## 6. Target-size lifecycle and control plane

The target-size lifecycle has four distinct control products:

1. one prepared target-size generation containing the current P2 definition, complete `TargetTrainingOrder`, configured-prefix qualification, `pi_eval`, and common P3 preparation;
2. optional diagnostic evidence and recommendation/no-recommendation;
3. an operator-owned provisional design; and
4. immutable per-size target bindings frozen atomically at `cross-validate` admission.

The automatic diagnostic is evidence, not a freeze owner. `CampaignStore` persists the provisional/frozen control state and current revision. It is also the sole completed prepared-generation currentness/adoption authority. Pre-adoption MVSTATE/history/checkpoint state belongs to the existing prepare/prepared-storage lifecycle as authenticated reconstructible build state and is never a second currentness plane.

Manual `select-target-size N` and automatic diagnostic selection consume the already-prepared compact P2 order/qualification projection. They do not map NEIGHBOR/MVIDX, restore selector checkpoints, or reconstruct selector science.

`cross-validate` admission authenticates the current prepared generation, re-derives every exact selected membership from the prepared complete order, and freezes the collection before numerical CV work.

Currentness is established from authoritative parents at exposure/publication time rather than from caller-held objects. Long-running work uses compare-and-set publication/reconciliation so stale workers cannot install superseded results as current.

See `45_target_training_order.md` for target-order ownership/restart/resource architecture and `50_target_size_selection.md` for lifecycle, freeze, restart, and invalidation structure. Candidate membership algorithms, normalization, evaluation, and reducer mathematics are D2 authority.

## 7. Restored post-selection method ownership

Current P5 has one method authority: `PostSelectionMethodIdentity`. The broad DATA8-era `TrainingProtocolIdentity` may remain for separately current non-P5 consumers and historical provenance, but it cannot authorize restored P5.

The current P5 lineage is:

```text
TargetBinding
  -> PostSelectionMethodIdentity
  -> CV/final role policy
  -> CV/final role plan
  -> fitted P5 preparation
  -> PostSelectionMaterialization
  -> run/checkpoint/evaluation evidence
  -> CV acceptance or final publication
```

The P5 method identity is a projection of real method-bearing component owners, not a digest of the whole P3 `TargetSizeCommonTrainingPolicy`. P3-only objective/weighting/harness edits therefore do not become false P5 currentness parents.

## 8. Common target-monitor topology

Current post-selection checkpoint/adaptive-stop control consumes one immutable campaign-common exact target monitor, `M_mon`, built once from the neutral label-usable `OUTER_MONITOR` parent. The same monitor-record digest is bound by every current selected-size CV plan and every final-production plan.

`M_mon` is external to selected-fold membership. A selected fold contains gradient training, held-out outer evaluation, and accepted purge/exclusion only.

Monitor construction and protected-relation qualification are distinct ordered owners: construct the exact D2 monitor first, then prove cross-role separation against every governed selected target membership using canonical P1 relation authority. Relation collision makes P5 infeasible; it is not repaired by filtering, replacement, or resampling. Failure to realize the accepted exact cardinality likewise fails closed.

Replay monitoring remains a separate replay-domain product.

## 9. Training, replay, CV, and production integration

Target and replay remain distinct evidence domains. Replay construction is owned by preparation; post-selection consumers authenticate prepared replay authority rather than silently rebuilding its scientific split or label policy. Canonical replay omission resolves TRUE_DFT; explicit pseudo replay remains opt-in and requires independent TRUE_DFT replay monitoring.

The MACE adapter is the one dependency-facing execution seam and resolves method realization by authenticated mode. P3 screening keeps its accepted weighted complete-batch path; P5 scratch keeps its separately accepted weighted method; naive and multihead foundation P5 realize the accepted native UniversalLoss method and foundation exposure geometry. No global loss switch may change an unaffected method family.

Foundation P5 remains on the qualified single-process path. Its deterministic two-head exposure binds replay/`pt_head` first then target before shuffle, no implicit target duplication, and accepted `drop_last=true` geometry. A distributed foundation path requires separate D2-equivalence acceptance.

Checkpoint selection, CV, and final production are separate owners. Held-out CV evidence cannot select its own checkpoint. Final production is a fresh lineage and cannot warm-start from a screen or CV checkpoint.

Per-size descendants bind a role-neutral target binding. Role-specific horizons/policies then descend independently, preventing unrelated production-budget changes from contaminating already accepted CV identity.

Final production uses the same common target monitor as accepted CV. M3 is not P5 checkpoint, ranking, plan, currentness, or publication ancestry. M3 remains P3 evidence and may support a separately authorized downstream probe through the P3 owner.

For `single_best_final_seed`, publication consumes only already-frozen admissible representatives and their already-authenticated common-monitor target metric records, reusing the accepted target-only representative-ordering semantics. It performs no second target or M3 evaluation. Publication membership is frozen before downstream qualification.

See `40_training_evaluation.md` for full training/replay/currentness integration. Loss mathematics, replay numerical semantics, fold algorithms, monitor sampling, E0 transfer, checkpoint admissibility, and final-product numerical ordering remain D1/D2 authority; exact dependency arguments, schemas, and source probes remain D4.

## 10. Execution, restart, storage, and resources

The detailed execution architecture in `60_execution_performance.md` remains D3 authority because process topology, scheduler admission, provider lifetime, persistence/recovery, storage ownership, archival/deduplication, and GPU/VRAM concurrency are software-architecture concerns. Target-order-specific execution/restart/resource ownership is detailed in `45_target_training_order.md` and integrated into that general resource plane.

The governing invariants are:

- sequential execution is the semantic reference unless D2 explicitly defines otherwise;
- parallel/distributed execution may change scheduling and resource use only while preserving D1/D2 identities/results within the accepted equivalence contract;
- accepted progress is immutable evidence while attempt-local scratch remains reclaimable under its execution owner;
- target-order pre-adoption continuation is authenticated reconstructible prepare-owned build state, not completed-generation currentness;
- the normal target-order prepared path performs one shared exact NEIGHBOR1 geometry build for FEAS1 and MVIDX;
- target-order OOC sparse storage preserves bounded anonymous memory, O(1)-in-family-count mapped descriptors, transactional publication, and protected-reference-safe cleanup;
- providers/processes have explicit lifetime owners and are retired at their ownership boundaries;
- storage consumes owner-declared views and cannot infer currentness from paths;
- retention is the transitive closure of current/restartable owner references;
- ambiguous ownership or unavailable trustworthy resource state fails closed rather than guessing; and
- resource adaptation may alter concurrency but cannot change scientific membership, numerical method, precision policy, label semantics, or accepted foundation-P5 single-process exposure to fit the machine.

Current P5 generations reject materially incompatible old stress/fold-local/M3-P5/from-scratch-E0/target-first/missing-transfer state before restart or publication reuse. Target-order cutover similarly rejects old `candidate_independent_priority.v1` order products as stale/reconstructible rather than migrating their ranks. Generation advancement is narrow: P5-only changes do not blanket-stale unchanged P1/P2/P3 evidence.

Exact locks, manifests, schemas, process signals, paths, and source probes are D4 details unless their semantics are explicitly elevated by the D3 contract.

## 11. Downstream qualification boundary

Production qualification consumes an already frozen final publication. Its D3 integration graph is:

```text
current target binding
  -> accepted post-selection CV
  -> accepted final publication decision
  -> QualificationInputBinding
  -> qualification plan/attempt
  -> deployment and physical-validation evidence
  -> terminal qualification/release evidence
```

Qualification does not own target selection, target-order membership, training-method acceptance, checkpoint selection, or publication membership. Locked evidence has an explicit irreversible activation boundary. Missing external references and unavailable deployment capabilities remain explicit waiting/blocking states rather than fabricated scientific outcomes.

Physical-observable algorithms remain owned by their analysis/method families. Qualification coordinates and binds their evidence; it does not redefine those algorithms.

See `80_ownership_and_decisions.md` for qualification/storage handoff and extension routing.

## 12. D3 structural invariants

The current architecture must preserve:

1. one current semantic owner for each decision/product;
2. dependency direction `D1 -> D2 -> D3 -> D4 -> runtime/generated evidence`;
3. immutable authenticated ancestry for consequential descendants;
4. one canonical evidence plane between source adapters and MLFF consumers;
5. one current `P_train` and one complete `TargetTrainingOrder`, with configured `T_N` memberships exact prefixes;
6. sole `TargetCoverageReference` fitted selector ownership;
7. one canonical target-order obligation authority, one normal-path exact NEIGHBOR1 construction, MVIDX as sparse representation, and independent MVQUAL;
8. target-order pre-adoption restart state subordinate to `prepare`/prepared-storage rather than CampaignStore currentness;
9. distinct target-size screening, post-selection CV, fresh production, and qualification lifecycles;
10. one current P5 method authority and no competing DATA8 protocol graph;
11. one external campaign-common target checkpoint monitor shared by current CV and final production;
12. selected-fold membership limited to train/eval/purge roles;
13. foundation-P5 fitted preparation bound to selected-head residual and composition-transfer evidence without inert P3 weighting ancestry;
14. no downstream feedback path that silently changes a frozen upstream decision;
15. P5 final publication free of M3 selection/currentness ancestry;
16. final publication membership decided before qualification;
17. currentness re-established from authoritative parents instead of stale caller state;
18. execution/storage/resource mechanisms preserving D1/D2 semantics rather than modifying the experiment to fit a machine;
19. source-specific knowledge localized at adapter/D4 boundaries;
20. unsupported historical generations remaining historical unless an explicitly accepted migration design exists; and
21. generated reports/publications remaining descendants rather than becoming independent authority.

## 13. Change and challenge routing

Classify changes by semantic effect:

- scientific question, observables, evidence interpretation, validity, or permitted claim -> D1;
- estimator, deterministic construction, approximation/error, normalization, precision/stochastic/failure semantics -> D2;
- subsystem ownership, dependency/control flow, persistence/recovery, concurrency/resources, deployment structure -> D3;
- local implementation, schema, parser, exact dependency argument/probe, helper, concrete serialization -> D4.

A lower-layer contradiction with coherent upstream authority is a conformance defect in the lower layer. If upstream authority itself is contradictory, materially ambiguous, or infeasible, challenge that upstream owner rather than adding a compensating wrapper.

Prefer direct ownership and rewiring/removal of obsolete machinery over additional synchronized state, adapters, compatibility paths, or duplicate semantic owners.

## 14. Detailed D3 sources and provenance

The detailed canonical D3 chapter set is:

- `00_front_matter.md` - authority boundary and package-level pipeline;
- `10_foundations.md` - layering and structural invariants;
- `20_data_contracts.md` - canonical evidence, adapter, identity, and artifact boundaries;
- `30_statistical_design.md` - evidence-flow, common-monitor, and fitted-product integration;
- `40_training_evaluation.md` - replay/training/CV/production integration;
- `45_target_training_order.md` - restored target-order ownership, sparse/restart/resource architecture, and D4 handoff;
- `50_target_size_selection.md` - lifecycle, operator ownership, freeze, restart/currentness;
- `60_execution_performance.md` - bounded execution, recovery, storage, resources, performance;
- `80_ownership_and_decisions.md` - ownership, qualification/storage handoff, extension boundaries; and
- `90_references.md` - retained architecture/tooling references.

This top-level manual is itself canonical D3 authority alongside those chapters; it is not a generated aggregate.

The lossless transition is documented by:

- `docs/history/mlff/MLFF_D1_D2_PROMOTION_2026-09-13.md`;
- `docs/history/mlff/MLFF_D1_D2_PROMOTION_PRESERVATION_MAP_2026-09-13.md`; and
- `docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/`.

The archived mixed manual is a pre-SSDP record bound to repository snapshot `cab2d4942042e0452df19d5a62f890db108ff49f` on 2026-09-13. It is retained for provenance and information-completeness recovery, not as current authority.
