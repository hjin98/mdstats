---
title: "mdstats MLFF Training-Data Architecture"
artifact_level: "D3 software architecture and integration"
status: "proposed D3 renewal candidate pending independent review"
accepted_current_baseline_date: "2026-09-15"
candidate_date: "2026-09-18"
---

# mdstats MLFF Training-Data Architecture (D3)

## 1. Purpose and authority

This branch carries a proposed D3 renewal of the MLFF software architecture. Until the renewed candidate passes the required independent D3 Review and is accepted-current, the accepted baseline remains the pre-renewal canonical architecture. The candidate preserves that baseline except for the explicitly reviewed replay-retention/target-admissibility ownership/currentness cutover described here. It continues the post-SSDP separation from the former mixed scientific/numerical/architecture manual.

The layered authority chain is directional; for D3 this branch carries the proposed replacement while the pre-renewal revision remains accepted-current until Gate D closes:

1. **D1 - scientific/mathematical authority:** `docs/methods/mlff_scientific_method.md`, with `docs/methods/mlff_target_training_order_scientific_method.md` as the accepted scoped owner for `TargetTrainingOrder` / `pi_train` scientific meaning.
2. **D2 - numerical/algorithmic authority:** `docs/methods/mlff_numerical_algorithmic_method.md`, with `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md` as the accepted scoped owner for target-training-order numerics.
3. **D3 - software architecture/integration authority:** the accepted-current pre-renewal revision of this manual/chapter set; this branch revision is the proposed replacement candidate. `45_target_training_order.md` remains the unchanged canonical detailed D3 owner for the restored target-order subsystem.
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
  -> published full-model representation of the selected representatives
  -> downstream production qualification
```

`pi_eval/M1/M2/M3` remain under their existing current owners. The restored target-order subsystem is candidate-outcome independent: target-size model outcomes, M3, CV, replay, production, and qualification evidence have no reverse edge into target membership.

Selection and representation are separate owners. The publication decision owns which seeds ship; a subordinate record owns the serialized full MACE models materialized from those seeds' exact selected representative checkpoints, beneath the protected campaign models container. Qualification keeps the checkpoint as its independent scientific reference and consumes the published model bytes only as a deployment source, so deployment parity stays a real oracle. The trainer's own terminal `.model` is the last TRAIN2 epoch, is not the selected representative, and is never a product.

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

Target and replay remain distinct evidence domains. Replay construction is owned by preparation; post-selection consumers authenticate prepared replay authority rather than rebuilding its scientific split or label policy. Canonical replay omission resolves TRUE_DFT; explicit pseudo replay remains opt-in and requires independent TRUE_DFT replay monitoring.

The P5 training path separates four dependency classes: a training-only method plus pre-fit `TrainingTrajectoryIdentity` derived from already-available training-bearing inputs; descendant fitted preparation/materialization/fixed-budget TRAIN2 whose exact realized preparation/runtime state is authenticated separately for continuation; assessment-independent `EvaluationMeasurementIdentity` records for target/replay numerical measurements; role hard-decision plus D2.DEF.059A policy for per-run checkpoint assessment/representative, with D2.DEF.059B reserved for aggregate final publication; and a replay-warning diagnostic policy whose descendants are reports only.

Assessment-only edits cannot change a TRAIN2 trajectory. Every governed durable checkpoint is assessed before P5 representative selection. Foundation-P5 within-run selection is the strict D2 lexicographic minimum `(target RMSE, epoch, checkpoint SHA-256)` over hard-admissible checkpoints. For `single_best_final_seed`, frozen seed representatives are ordered by `(target RMSE, optimizer seed, checkpoint SHA-256)`. `all_qualified_final_seeds` remains unranked.

Foundation generated/default target thresholds are `75/75/50 meV/angstrom` for CV checkpoint, default-force CV outer acceptance, and production checkpoint quality respectively. Replay warning/hard generated defaults are `50/100 meV/angstrom`. The warning has no hard-decision edge. Alternative CV outer metrics keep their own accepted units/default resolution.

Final production uses the same common target monitor as accepted CV. Current CV authorization is required for current final assessment/publication. A historically fresh final TRAIN2 trajectory may be reused only after current CV reclosure accepts and exact training-semantic equivalence is proven. M3 remains outside P5 checkpoint/ranking/currentness/publication ancestry.

See `40_training_evaluation.md` for the detailed ownership graph. D1/D2 remain authoritative for the numerical predicates, exact ordering/ties, equivalence relations and failure semantics.


## 10. Execution, restart, storage, and resources

The detailed execution architecture in `60_execution_performance.md` remains D3 authority. Parallel/resource adaptation preserves D2 equivalence and cannot alter scientific membership, numerical method, precision policy, label semantics, or accepted foundation-P5 exposure.

Post-cutover P5 run roots are keyed by the pre-fit training trajectory rather than a full assessment plan. Fitted/materialized training state, generated configuration, checkpoints and runtime history live there as descendants whose exact digests are separately authenticated. Authenticated terminal TRAIN2 seals the existing topology/completion proof before EVAL2. The proof retains opened-descriptor `O_NOFOLLOW`/`fstat` authentication, non-reclaimable manifest/anchor infrastructure, completion independent of assessment-file presence, idempotent proof reuse after cold movement, and fail-closed tamper/root-mismatch behavior. Current CV/final assessments are immutable descendants outside that sealed root and are located through the existing CampaignStore pointer/currentness plane.

A policy-only change reuses a training-equivalent root and assessment-independent measurements where D2 equivalence is provable; otherwise only the required EVAL2 measurement is recomputed. Already sealed historical roots are never renamed, copied, symlinked or rewritten. A terminal-but-unsealed historical root has exactly one append-only completion-proof exception under the existing P5 run-activity owner after exact authentication, with no pre-existing byte rewrite. Interrupted legacy training continues only through exact authenticated historical runtime/protocol/preparation ancestry after training-equivalence proof. Legacy roots are never located by store scanning.

Storage continues to consume owner-declared views. Retention is the transitive closure of current/restartable references. Any EVAL2/reassessment reading a sealed training root holds the existing P5 run-activity exclusion for the full numerical-read interval so archive/dedup/reclamation cannot race it. No second storage plane or reader-lock protocol is introduced.

Production-scale GPU qualification remains deferred to the final complete release package for the user's machine.

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

1. one current semantic owner for each decision/product and acyclic D1 -> D2 -> D3 -> D4 dependency direction;
2. immutable authenticated ancestry for consequential descendants;
3. one current `P_train` / complete `TargetTrainingOrder` and exact configured prefixes;
4. one canonical target-order obligation authority, one normal-path exact NEIGHBOR1 build, MVIDX as representation, and independent MVQUAL;
5. distinct target-size screening, post-selection CV, fresh production, and qualification lifecycles;
6. one current P5 training-method authority and one acyclic pre-fit training-trajectory/root identity excluding fitted-result descendants and assessment-only policy;
7. one external campaign-common target checkpoint monitor shared by CV and production;
8. selected-fold membership limited to train/eval/purge;
9. assessment-independent numerical measurement identity;
10. warning-only replay policy isolated from hard decisions;
11. complete checkpoint assessment plus exact D2.DEF.059A within-run ordering and D2.DEF.059B aggregate publication ordering;
12. distinct currentness scopes for `tau_CV`, `theta_CV`, `tau_prod`, replay hard/warning policy, 059A per-run selection and 059B publication-only policy; final-seed assessment currentness excludes current-CV authorization and 059B/publication mode;
13. sealed training-only P5 roots before EVAL2, with assessments external to the root, accepted topology/anchor race-safety and cold-storage invariants preserved, already sealed historical roots read-only, and only the narrow append-only seal exception for terminal-but-unsealed legacy roots;
14. no in-place historical verdict reclassification and no scalar-only measurement reuse;
15. current CV reauthorization before reuse of historical final production for current assessment/publication;
16. P5 final publication free of M3 selection/currentness ancestry and fixed before qualification;
17. currentness re-established from authoritative parents rather than paths/caller snapshots/scans;
18. execution/storage/resource mechanisms preserve D1/D2 semantics rather than modifying the experiment to fit a machine;
19. source-specific knowledge remains localized at adapter/D4 boundaries; and
20. unsupported historical generations remain historical unless an explicitly accepted narrow migration proves equivalence.

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
