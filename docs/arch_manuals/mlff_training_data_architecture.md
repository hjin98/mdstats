---
title: "mdstats MLFF Training-Data Architecture"
artifact_level: "D3 software architecture and integration"
status: "current normative D3 architecture"
accepted_date: "2026-09-13"
---

# mdstats MLFF Training-Data Architecture (D3)

## 1. Purpose and authority

This manual is the current D3 software-architecture authority for the machine-learned force-field (MLFF) branch of mdstats. It replaces the former pre-SSDP architecture manual that mixed scientific formulation, numerical algorithms, software architecture, and source-specific implementation detail in one document family.

The current authority chain is directional:

1. **D1 - scientific/mathematical authority:** `docs/methods/mlff_scientific_method.md`.
2. **D2 - numerical/algorithmic authority:** `docs/methods/mlff_numerical_algorithmic_method.md`.
3. **D3 - software architecture/integration authority:** this manual and the detailed chapter set under `docs/arch_manuals/mlff_training_data/`.
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
  -> candidate-independent pre-order selection evidence
  -> one target-size generation (P_train/M3, pi_train, pi_eval)
  -> one common target-size training preparation
  -> optional target-size diagnostic screen/reducer
  -> operator-owned provisional design
  -> cross-validate admission and atomic target-binding freeze
  -> post-selection cross-validation
  -> fresh final production and publication decision
  -> downstream production qualification
```

The architecture deliberately prevents reverse control. Post-selection CV cannot reselect a target membership. Qualification cannot choose publication members. Storage cannot create scientific currentness. Runtime adapters cannot redefine D1/D2 semantics merely because an external dependency behaves differently.

## 3. Package and subsystem ownership

The principal package-level boundaries are:

- `mdstats.data`: canonical source/frame evidence and source-normalization interfaces;
- `mdstats.sampling`: shared correlation/sampling primitives used by MLFF owners;
- `mdstats.training_data`: MLFF evidence construction, selection, campaign state, persistence, orchestration, replay preparation, storage, and qualification integration;
- `mdstats.training`: training/checkpoint/evaluation execution seams, including the qualified MACE adapter and evaluation owners; and
- `mdstats.cli`: operator-facing composition only; command routing must not become a second semantic owner.

Detailed D3 ownership is in `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`.

## 4. Canonical evidence and adapter boundary

External-source conventions are translated once at source-adapter boundaries. Central MLFF components consume canonical evidence rather than rediscovering VASP-, ASE-, MACE-, path-, or file-layout-specific semantics.

Downstream artifacts bind immutable upstream identities. Membership-bearing products bind exact member and parent identities. Fitted products additionally bind their authorized fit domain and method/policy identity. Cache identifiers, file paths, and display metadata are not authority unless an owning contract explicitly promotes them.

The architecture distinguishes authoritative evidence, fitted method products, restartable execution state, generated reports, and disposable caches/scratch. Cleanup and storage decisions preserve those classes rather than inferring importance from pathname or age.

See `20_data_contracts.md` for the D3 evidence/integration boundary. Scientific label meaning is owned by D1; numerical identity construction is owned by D2; exact serialized records and adapter behavior are D4.

## 5. Statistical and fitted-product integration

The architecture keeps two candidate-independent fitted stages separate:

- **pre-order selection evidence**, which can contribute authorized priority evidence to the one canonical target-training order; and
- **common target-size training preparation**, which is constructed after the target-size split/orders and is shared unchanged across candidate sizes where D2 requires common fitted state.

P2/P3 consume upstream relation and evidence products; they do not reconstruct protected relations or create alternate membership selectors. Candidate projection is downstream of common preparation and cannot become a hidden refit owner.

Post-selection fold-local fitted state belongs only to the fold-authorized training domain and cannot mutate the frozen target binding.

See `30_statistical_design.md` for producer/consumer, fitted-product, and invalidation structure. The exact estimators and deterministic constructions remain D2 authority.

## 6. Target-size lifecycle and control plane

The target-size lifecycle has four distinct control products:

1. one prepared target-size generation;
2. optional diagnostic evidence and recommendation/no-recommendation;
3. an operator-owned provisional design; and
4. immutable per-size target bindings frozen atomically at `cross-validate` admission.

The automatic diagnostic is evidence, not a freeze owner. `CampaignStore` persists the provisional/frozen control state and current revision. `cross-validate` admission authenticates the current prepared generation, re-derives every exact selected membership, and freezes the collection before numerical CV work.

Currentness is established from authoritative parents at exposure/publication time rather than from caller-held objects. Long-running work uses compare-and-set publication/reconciliation so stale workers cannot install superseded results as current.

See `50_target_size_selection.md` for lifecycle, freeze, restart, and invalidation structure. Candidate membership algorithms, normalization, evaluation, and reducer mathematics are D2 authority.

## 7. Training, replay, CV, and production integration

A complete training method identity is resolved once and realized through the qualified execution seam. Target and replay remain distinct evidence domains. Replay construction is owned by preparation; post-selection consumers authenticate prepared replay authority rather than silently rebuilding its scientific split or label policy.

Checkpoint selection, CV, and final production are separate owners. Held-out CV evidence cannot select its own checkpoint. Final production is a fresh lineage and cannot warm-start from a screen or CV checkpoint. Publication membership is decided before downstream qualification, so qualification cannot become hidden product selection.

Per-size descendants bind a role-neutral target binding. Role-specific horizons/policies then descend independently, preventing unrelated production-budget changes from contaminating already accepted CV identity.

See `40_training_evaluation.md` for training/replay/currentness integration. Loss mathematics, replay numerical semantics, fold algorithms, checkpoint admissibility semantics, and final-product numerical selection remain D1/D2 authority; exact dependency arguments and source probes remain D4.

## 8. Execution, restart, storage, and resources

The detailed execution architecture in `60_execution_performance.md` remains D3 authority because process topology, scheduler admission, provider lifetime, persistence/recovery, storage ownership, archival/deduplication, and GPU/VRAM concurrency are software-architecture concerns.

The governing invariants are:

- sequential execution is the semantic reference unless D2 explicitly defines otherwise;
- parallel/distributed execution may change scheduling and resource use only while preserving D1/D2 identities/results within the accepted equivalence contract;
- accepted progress is immutable evidence while attempt-local scratch remains reclaimable under its execution owner;
- providers/processes have explicit lifetime owners and are retired at their ownership boundaries;
- storage consumes owner-declared views and cannot infer currentness from paths;
- retention is the transitive closure of current/restartable owner references;
- ambiguous ownership or unavailable trustworthy resource state fails closed rather than guessing; and
- resource adaptation may alter concurrency but cannot change scientific membership, numerical method, precision policy, or label semantics to fit the machine.

Exact locks, manifests, schemas, process signals, paths, and source probes are D4 details unless their semantics are explicitly elevated by the D3 contract.

## 9. Downstream qualification boundary

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

Qualification does not own target selection, training-method acceptance, checkpoint selection, or publication membership. Locked evidence has an explicit irreversible activation boundary. Missing external references and unavailable deployment capabilities remain explicit waiting/blocking states rather than fabricated scientific outcomes.

Physical-observable algorithms remain owned by their analysis/method families. Qualification coordinates and binds their evidence; it does not redefine those algorithms.

See `80_ownership_and_decisions.md` for the qualification/storage handoff and extension routing.

## 10. D3 structural invariants

The current architecture must preserve:

1. one current semantic owner for each decision/product;
2. dependency direction `D1 -> D2 -> D3 -> D4 -> runtime/generated evidence`;
3. immutable authenticated ancestry for consequential descendants;
4. one canonical evidence plane between source adapters and MLFF consumers;
5. distinct target-size screening, post-selection CV, fresh production, and qualification lifecycles;
6. no downstream feedback path that silently changes a frozen upstream decision;
7. final publication membership decided before qualification;
8. currentness re-established from authoritative parents instead of stale caller state;
9. execution/storage/resource mechanisms preserving D1/D2 semantics rather than modifying the experiment to fit a machine;
10. source-specific knowledge localized at adapter/D4 boundaries;
11. unsupported historical generations remaining historical unless an explicitly accepted migration design exists; and
12. generated reports/publications remaining descendants rather than becoming independent authority.

## 11. Change and challenge routing

Classify changes by semantic effect:

- scientific question, observables, evidence interpretation, validity, or permitted claim -> D1;
- estimator, deterministic construction, approximation/error, normalization, precision/stochastic/failure semantics -> D2;
- subsystem ownership, dependency/control flow, persistence/recovery, concurrency/resources, deployment structure -> D3;
- local implementation, schema, parser, exact dependency argument/probe, helper, concrete serialization -> D4.

A lower-layer contradiction with coherent upstream authority is a conformance defect in the lower layer. If the upstream authority itself is contradictory, materially ambiguous, or infeasible, challenge that upstream owner rather than adding a compensating wrapper.

Prefer direct ownership and rewiring/removal of obsolete machinery over additional synchronized state, adapters, compatibility paths, or duplicate semantic owners.

## 12. Detailed D3 sources and provenance

The detailed canonical D3 chapter set is:

- `00_front_matter.md` - authority boundary and package-level pipeline;
- `10_foundations.md` - layering and structural invariants;
- `20_data_contracts.md` - canonical evidence, adapter, identity, and artifact boundaries;
- `30_statistical_design.md` - evidence-flow and fitted-product integration;
- `40_training_evaluation.md` - replay/training/CV/production integration;
- `50_target_size_selection.md` - lifecycle, operator ownership, freeze, restart/currentness;
- `60_execution_performance.md` - bounded execution, recovery, storage, resources, performance;
- `80_ownership_and_decisions.md` - ownership, qualification/storage handoff, extension boundaries; and
- `90_references.md` - retained architecture/tooling references.

The lossless transition is documented by:

- `docs/history/mlff/MLFF_D1_D2_PROMOTION_2026-09-13.md`;
- `docs/history/mlff/MLFF_D1_D2_PROMOTION_PRESERVATION_MAP_2026-09-13.md`; and
- `docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/`.

The archived mixed manual is a pre-SSDP record bound to repository snapshot `cab2d4942042e0452df19d5a62f890db108ff49f` on 2026-09-13. It is retained for provenance and information-completeness recovery, not as current authority.
