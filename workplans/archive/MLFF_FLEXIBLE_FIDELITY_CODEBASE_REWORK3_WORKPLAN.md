---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK3
protocol_version: 5.5.0
status: completed
completed_date: 2026-08-25
---

# MLFF Flexible-Fidelity Rework 3 Closure Workplan

## 1. Authority, objective, and starting point

This is the governing closure overlay for `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1`, Rework 1, and Rework 2 after independent Software Design review of `feat/mlff-end-to-end-performance-v1` at `3a3c4b97cbcb0a05ee19f70aaaf249f6c9e37958`.

The parent, Rework 1, and Rework 2 plans remain authoritative for every frozen decision and obligation not explicitly strengthened here. This overlay reopens only the affected closure surfaces. In particular, the accepted flexible-fidelity scientific architecture remains frozen:

```text
0 < n1 < n2 < n3 <= n

default fidelity = (1,3,10)
default full TRAIN2 horizon n = 30
```

The central target-size runtime, exact TRAIN2 continuation model, full-horizon authority, SIZE-FIDELITY final/reference role separation, production ordering semantics, candidate ladder, MVQUAL authority, paired seeds, target-only ranking, and GPU-production-qualification deferral are not reopened.

Objective: close the remaining semantic-identity, current-authority, integration, and regression defects so that the flexible-fidelity implementation can be accepted on one final candidate with executable evidence through the real campaign state/orchestration boundaries.

The Rework 2 closeout evidence record is superseded as an acceptance claim by this overlay. It remains historical development evidence, but R2W3/R2W4 are considered reopened until the obligations below pass on the final Rework 3 candidate.

## 2. Independent-review findings and routing

### R3-1 - BLOCKER: preparation semantic identity still authenticates execution-only controls

Classification: implementation nonconformance against Rework 2 O14.

Observed implementation: `_PREPARATION_CONFIG_PROJECTION_FIELDS["model"]` includes execution/cache realization controls such as `max_new_frames`, inference batch limits, estimated inference memory, VRAM calibration/reserve controls, pipeline enablement, persistence queue depth, checkpoint cadence, and artifact shard size. The adjacent implementation comment itself classifies the non-device/dtype model controls as calibration, persistence, or progress policy rather than preparation scientific identity.

Failure mode: changing only an execution realization knob can change `_preparation_config_digest()` and reject otherwise compatible completed preparation/preflight/materializations. This recreates the over-invalidation class that the positive semantic projection was introduced to remove.

Required end state: preparation semantic identity authenticates only inputs/policies that can change authoritative DATA2-DATA8 scientific content, membership, fitted state, required materialization topology, or model-dependent scientific preprocessing. Execution strategy, batching, resource limits, progress, checkpoint cadence, cache/shard layout, and persistence mechanics do not invalidate scientific preparation unless repository evidence proves that a specific field changes authoritative prepared outputs.

### R3-2 - BLOCKER: final regression/closeout claim is contradicted by current repository tests

Classification: acceptance nonconformance.

Observed implementation: current architecture is revision 106 and describes configurable fidelity, while current tests still assert revision 105, `fixed target-size study`, and `0 -> 3 epochs -> 10 epochs -> 30 epochs`. These failures intersect the exact documentation/architecture surface changed by flexible fidelity and therefore cannot be classified as unrelated baseline failures.

Required end state: all current normative-documentation tests assert revision-106 semantic fidelity behavior. Historical fixed-fidelity assertions remain only in explicitly historical fixtures/compatibility tests. Final affected-surface regression must execute after these test contracts are corrected.

### R3-3 - HIGH: canonical current dependency graph still encodes fixed numeric fidelity stages

Classification: current-authority/documentation nonconformance.

Observed implementation: `docs/arch_manuals/mlff_training_data_dependency_graph.json` identifies itself as the current conceptual dependency/ownership graph but still contains `SIZE_STUDY_EPOCH3`, `SIZE_STUDY_EPOCH10`, and `SIZE_STUDY_EPOCH30` with fixed sequential edges.

Required end state: the current dependency graph models semantic stage authorities (`COARSE_SCREEN`, `SHORT_SCREEN`, `FINAL_SCREEN`, plus independent full TRAIN2 horizon/schedule authority where relevant) and their dependency direction without presenting 3/10/30 as current architecture. Generated defaults may remain documented as defaults; historical graphs/fixtures remain historical.

### R3-4 - HIGH: mandatory A/B/C/D1/D2/D3 acceptance is too helper-level

Classification: acceptance/workplan-conformance gap.

Observed implementation: A/B/C largely construct `TargetSizeStudyPlan`, SIZE-FIDELITY, and PERF-P2R helpers directly. D1/D2 exercise more migration logic but mock several identity, materialization, study, and validation boundaries that the assembled acceptance was intended to prove.

Required end state: bounded integration tests exercise the real configuration normalization, `CampaignStore` persistence, stage/status/advance/restart consumers, target-size orchestration, evidence attachment/reduction, selected-size freeze, and production-horizon authorization. Expensive MACE/data/GPU execution may be mocked at the external compute boundary, but the semantic identity/invalidation/orchestration mechanisms under test may not be replaced by helper-level reimplementations or mocks.

### R3-5 - HIGH: exact independent invalidation-frontier proof remains incomplete

Classification: acceptance nonconformance against Rework 1 O10-R1 and Rework 2 O15.

Observed implementation: independent `n1`, `n2`, and `n3` tests prove preparation-digest invariance, but they do not independently prove the complete persisted record/stage frontier. A general TRAIN2 reset test and combined migration cases do not substitute for four independent product-level perturbations of `n1`, `n2`, `n3`, and `n`.

Required end state: dedicated tests independently change each boundary and assert exactly which prepare/preflight/DATA8, target-size/fidelity, TRAIN2/checkpoint, SIZE-FIDELITY/PERF-P2R, status, and forensic records are preserved, invalidated, or regenerated.

### R3-6 - MEDIUM: current migration documentation is internally inconsistent

Classification: documentation drift.

Observed implementation: the revision-106 architecture broadly says there is no migration path for superseded campaign generations, while the accepted flexible-fidelity contract intentionally supports a narrow, fail-closed migration from the immediately preceding fixed-fidelity campaign generation when historical compatibility can be proven.

Required end state: current documentation distinguishes unsupported superseded scientific architectures from the explicitly supported immediate fixed-fidelity -> flexible-fidelity restart/migration boundary. It must not imply either blanket backward compatibility or blanket absence of the supported migration path.

## 3. Frozen closure design

### 3.1 Separate scientific preparation identity from execution realization

The positive semantic projection remains the correct design. Repair its field ownership; do not revert to whole-config hashing or a negative exclusion filter.

Preparation semantic identity includes, at minimum, authorities that can change:

- source/catalog admission and source/input identities;
- frame/label-domain semantics and manifest inference;
- evidence-role/domain construction used by preparation;
- DATA4-DATA6 scientific feature/model preprocessing identity;
- DATA7 fitted statistics, selection, coverage, repair/MVQUAL inputs;
- DATA8 scientific bytes and required variant/materialization topology;
- foundation/model identity and precision/backend choices when they materially change authoritative prepared scientific values;
- training method/seed/fold topology only where it determines required preparation variants/materializations;
- replay source/split/materialization policy where it changes DATA8 inputs.

Preparation semantic identity excludes fields whose only effect is execution realization, including, unless direct evidence proves otherwise:

- inference batch-size/capacity and estimated-memory controls;
- VRAM calibration/reserve/throughput controls;
- pipeline overlap and persistence queue depth;
- checkpoint/journal cadence;
- artifact shard/cache layout;
- worker counts, CPU/RAM/GPU fractions, telemetry/progress cadence;
- temporary bounded-work/debug limits such as `max_new_frames` when they do not define the completed authoritative product;
- target-size fidelity tuple and ranking-only controls;
- full TRAIN2 horizon/LR/checkpoint/stopping controls;
- evaluation/verification/presentation/documentation-only controls.

If an execution field changes a reconstructible cache layout, use existing cache/realization identity or introduce the smallest justified execution-only identity. Do not make scientific preparation identity carry cache layout merely to simplify reuse checks.

A whole-config SHA may remain provenance only. No second preparation-scientific authority may be introduced.

### 3.2 Exact invalidation ownership remains stage-scoped

Frozen frontier:

```text
change n1/n2/n3 only
  -> preserve compatible prepare + screening preflight + DATA7/DATA8 materializations
  -> invalidate/reset target-size/fidelity state/evidence and cross-dependent SIZE-FIDELITY/PERF-P2R state
  -> preserve unrelated forensic/provenance records
  -> first authorized screen follows the new n1

change n only
  -> preserve compatible prepare + screening preflight + DATA7/DATA8 materializations
  -> invalidate TRAIN2 schedule/training/checkpoint identity and every cross-dependent artifact whose meaning includes n
  -> reject cross-horizon checkpoint continuation
  -> establish the new full-n schedule before new TRAIN2 work

change execution-only preparation realization
  -> preserve scientific preparation identity and completed authoritative preparation
  -> invalidate/rebuild only the execution cache/realization whose own identity truly depends on the changed field, if any

change preparation-owned scientific input/policy
  -> invalidate prepare/preflight/materialization and all dependent downstream state

change presentation/documentation-only field
  -> no scientific/preparation invalidation
```

Historical fixed target-size evidence must never be relabeled as flexible evidence.

### 3.3 Current architecture authority must be semantic and internally synchronized

Current architecture sources, dependency graph, current specs/guides/config comments, CLI/status/error strings, and nonhistorical tests must describe semantic stages and configured values. Fixed `3/10/30` is permitted only for:

- explicit immediately preceding historical migration validation;
- historical fixtures/oracles/release notes/archived plans;
- generated-default statements that are clearly labeled defaults, not architecture identity.

Revision metadata, revision index/history, assembled Markdown, dependency graph, tracked generated PDFs/manifests, and tests that certify current documentation must agree on revision 106 flexible-fidelity semantics.

Do not rewrite historical release/architecture notes merely to remove old numbers.

### 3.4 Assembled tests must traverse product ownership boundaries

Synthetic/bounded data is preferred. The integration harness should enter through current campaign configuration and persistent state, not by reconstructing the target-size algorithm inside the test.

Required real boundaries include, as applicable:

```text
campaign TOML/current-or-historical config
 -> normalization/schema compatibility
 -> CampaignPaths/CampaignStore
 -> preparation/preflight reuse identity
 -> target-size study persistence and orchestration
 -> semantic TRAIN2 stage authorization
 -> evidence persistence/reduction
 -> status/advance/restart consumer
 -> selected target size freeze
 -> production full-n authorization
```

Mock only expensive or unavailable external compute/data boundaries. Do not monkeypatch `_preparation_config_digest`, the invalidation routine, target-size study owner, stage-config identity, or equivalent owning mechanisms in a test whose claim is that those mechanisms work end-to-end.

## 4. Implementation obligations

### O18 - Repair preparation scientific/execution identity separation

**Protected concern:** eliminate false expensive upstream invalidation without broadening unsafe scientific reuse.

**Required end state:** `_preparation_config_digest()` or its successor hashes one explicit positive scientific/materialization projection. Execution-only changes do not alter it; all preparation-owned scientific changes do.

**Required implementation consequences:**

- audit every currently included preparation-projection field and classify it as scientific/materialization-owned or execution-only;
- remove execution-only fields from preparation semantic identity;
- retain device/dtype/backend or other fields only when they materially change authoritative prepared scientific values/bytes;
- keep source/model/input identity checks fail-closed;
- keep reconstructible execution/cache identities separate where needed;
- preserve historical receipt validation before current re-authentication;
- do not bind completed DATA7/DATA8 reuse to fidelity/horizon or unrelated execution knobs;
- delete or consolidate duplicate identity helpers if the repair exposes overlapping authorities.

**Acceptance evidence:**

1. table-driven perturbation of every execution-only field currently at risk proves unchanged preparation semantic digest and completed-prepare reuse;
2. representative source/model/coverage/selection/seed-topology/preparation-affecting changes prove changed digest and upstream invalidation;
3. `n1`, `n2`, `n3`, `n`, and presentation-only perturbations preserve preparation identity;
4. cache-layout/execution changes invalidate only their own reconstructible realization if such an identity exists;
5. historical receipt corruption or ambiguous compatibility still fails closed.

### O19 - Reconcile current architecture/documentation/test authority

**Protected concern:** prevent current normative surfaces and their tests from teaching or enforcing superseded fixed-fidelity semantics.

**Required end state:** revision-106 current authority is semantic and synchronized across editable sources, dependency graph, assembled publications, revision index, and current-documentation tests.

**Required implementation consequences:**

- replace current dependency-graph `SIZE_STUDY_EPOCH3/EPOCH10/EPOCH30` nodes/edges with semantic stage identities and independent full-horizon ownership where needed;
- update `tests/test_mlff_doc_arch1_specification.py` and `tests/test_mlff_progress_reporting_format_specification.py` to revision 106 and semantic target-size expectations;
- add/repair revision-106 history/index entry according to repository convention without rewriting historical revision notes;
- reconcile current migration wording so the narrow supported fixed-generation upgrade is explicit while unsupported older generations remain unsupported;
- structurally classify remaining fixed-number occurrences on current flexible-fidelity surfaces;
- regenerate tracked Markdown/PDF/manifest descendants from authoritative sources where changed.

**Acceptance evidence:**

- current doc/architecture specification tests pass;
- dependency graph contains no current numeric-stage authority nodes for flexible fidelity;
- current normative sources contain no fixed `3/10/30` authority language outside explicitly labeled default/historical contexts;
- generated-source integrity checks pass.

### O20 - Prove exact independent invalidation frontier

**Protected concern:** upstream reuse must not become unsafe downstream reuse, and one combined test must not conceal boundary-specific mistakes.

**Required end state:** independent product-level perturbations of `n1`, `n2`, `n3`, and `n` prove exact preserved/invalidated state.

**Required implementation consequences:**

- construct persisted pre-change campaign state with prepare/preflight/DATA8, target-size state/evidence, TRAIN2 schedule/checkpoint state where relevant, SIZE-FIDELITY/PERF-P2R state, status stages, and forensic/provenance records;
- perturb each of `n1`, `n2`, `n3`, `n` separately through current config/normalization/restart consumers;
- assert exact record/stage frontier rather than only digest inequality/equality;
- for `n`, prove cross-horizon checkpoint rejection and new schedule authentication;
- for tuple changes, prove first new work authorization uses the configured new `n1` and no old fixed/flexible evidence is relabeled;
- add execution-only and presentation-only frontier controls so over-invalidation is also covered.

**Acceptance evidence:** a four-case frontier matrix plus preparation-affecting, execution-only, and presentation-only controls, all through persistent campaign consumers.

### O21 - Execute genuine assembled A/B/C/D1/D2/D3 integration

**Protected concern:** helper-level green tests cannot prove configuration/persistence/orchestration/restart behavior.

**Required end state:** all mandatory cases run through the assembled bounded product path on the same candidate.

**Mandatory cases:**

- **A - fresh default `(1,3,10)/30`:** config -> prepare/preflight-compatible state -> coarse/short/final-screen authorization/evidence -> reductions -> selected size -> status/restart -> production horizon 30.
- **B - fresh nondefault `(2,5,12)/40`:** exact nondefault config normalization; stage authorization at 2/5/12; eliminated candidates receive no later work; progress/status show authorized endpoint separately from schedule horizon 40; selected size freezes; production authorizes full 40.
- **C - `(1,3,30)/30`:** one physical endpoint may satisfy final-screen/reference data while semantic validation keeps both roles distinct; no duplicate required physical work is introduced.
- **D1 - historical completed preflight -> default flexible `(1,3,10)/30`:** historical authority validates; prepare/preflight/DATA8 are reused; historical target-size evidence cannot masquerade as flexible evidence; first new authorization is epoch 1.
- **D2 - historical completed preflight -> `(2,5,12)/40`:** upstream reuse survives horizon change; new full-40 schedule identity is established; cross-horizon checkpoint reuse is rejected; first new screen is epoch 2.
- **D3 - preparation-affecting historical/config change:** reuse fails closed or reruns from the narrow correct upstream boundary.

The test harness may fake MACE subprocess success, bounded prediction arrays, or heavy source materialization, but must preserve real configuration, identity, persistence, orchestration, state transition, and status/restart consumers.

### O22 - Re-establish final regression and closeout evidence

**Protected concern:** no workplan may be archived on contradictory or unexecuted affected tests.

**Required end state:** one final candidate passes semantic/conformance reconciliation plus fresh affected-surface regression and assembled integration after every material executable/documentation contract edit.

**Required implementation consequences:**

- re-derive the final affected behavioral surface from the assembled diff and callers/consumers;
- include at minimum flexible-fidelity policy/study, campaign CLI/config/status/advance/restart, preparation/preflight/materialization reuse, TRAIN2 runtime continuation/schedule identity, SIZE-FIDELITY, PERF-P2R, current architecture/dependency-graph/docs tests, migration/persistence, and progress reporting;
- run repository-required checks and broaden to the full available suite if the affected surface cannot be bounded confidently;
- do not classify a failure as baseline/unrelated when its assertion intersects revision 106, target-size fidelity, preparation identity, campaign migration, or another changed surface;
- record concrete failing test identities/reasons for any legitimately unrelated baseline failures rather than relying only on aggregate counts;
- no GitHub CI status is required if the repository does not provide one, but absence of CI cannot substitute for local executed evidence.

Production qualification remains **deferred**. Do not run long data-heavy GPU qualification during this repair. Bounded functional/integration tests and ordinary accelerator smoke tests remain allowed where repository tests require them.

## 5. Implementation authority

### Frozen

- `0 < n1 < n2 < n3 <= n`;
- generated defaults `(1,3,10)/30`;
- one target-size policy authority for the three screen boundaries and independent TRAIN2 budget authority for `n`;
- exact same-trajectory continuation with `execution_epoch_limit` as a pause/work boundary, not a shortened schedule;
- fixed target-size candidate population and MVQUAL hard admission;
- `q -> min(q,4) -> 2 -> 1` funnel and paired-seed target-only ordering;
- final-screen `n3` and full-reference `n` remain distinct semantic roles;
- SIZE-FIDELITY uses production ordering/equivalence semantics and full-`n` reference behavior;
- semantic stage-scoped invalidation and historical validation before re-authentication;
- target-size candidate/DATA8 scientific identity is independent of downstream fidelity/horizon when bytes/topology are unchanged;
- current documentation is semantic; historical records remain historical;
- full production/GPU qualification remains deferred.

### Delegated

- exact helper/type names for scientific versus execution-only configuration projections;
- whether an existing cache/realization digest can absorb execution-only fields or a minimal new execution identity is justified;
- exact temporary test fixture/fake subprocess mechanics, provided owning product logic remains real;
- exact semantic dependency-graph node names;
- exact current schema bump only if persisted current record shape materially changes.

### Reopen only on evidence

Reopen only the affected design surface if repository evidence proves that:

- a field classified here as execution-only actually changes authoritative DATA2-DATA8 scientific bytes/membership/topology;
- the current positive projection cannot reconstruct a required preparation dependency safely;
- historical receipts lack enough evidence for a particular supported migration, in which case fail closed at the narrowest safe rerun boundary;
- assembled integration exposes a new scientific/state-machine defect that invalidates a frozen fidelity premise.

Do not reopen the flexible-fidelity scientific architecture merely because documentation/tests or migration mechanics are inconvenient.

## 6. Initially expected affected behavioral surface

Primary executable/state surfaces:

- `mdstats/training_data/_campaign_cli_core.py`;
- preparation/preflight receipt and semantic config identity;
- DATA7/DATA8 materialization/reuse consumers;
- target-size study persistence/orchestration/status/advance/restart;
- TRAIN2 schedule/checkpoint continuation identity;
- SIZE-FIDELITY and PERF-P2R consumers where invalidation or assembled tests touch them;
- progress reporting for authorized endpoint versus full schedule horizon.

Primary tests:

- `tests/test_mlff_flexible_fidelity.py`;
- `tests/test_mlff_campaign_cli.py` and semantic orchestration/status tests;
- target-size topology/persistence/continuation tests;
- `tests/test_mlff_train2b_runtime.py`;
- SIZE-FIDELITY/PERF-P2R tests;
- `tests/test_mlff_doc_arch1_specification.py`;
- `tests/test_mlff_progress_reporting_format_specification.py`;
- any migration/restart/materialization tests discovered from the final callers/consumers.

Current authority/publication surfaces:

- `docs/arch_manuals/mlff_training_data_dependency_graph.json`;
- canonical architecture chapter sources and assembled Markdown;
- revision index/history entry for revision 106;
- current target-size/SIZE-FIDELITY/config/spec/guides that still conflict with the semantic architecture;
- tracked generated PDFs/manifests whose authoritative sources change.

Implementation must independently re-derive the final affected surface from the assembled diff before final regression.

## 7. Implementation sequence and gates

### R3W0 - Reproduce and classify identity/documentation blockers

- add/confirm execution-only preparation-digest reproducers;
- enumerate currently included preparation projection fields and classify ownership;
- capture the stale revision-105/fixed-fidelity tests and fixed numeric dependency-graph nodes as explicit failing/structural evidence;
- identify the real public/persistent boundaries needed for assembled A/B/C/D1/D2/D3 without mocking their owning mechanisms.

Closure: no unknown preparation identity field or current numeric-stage authority remains unclassified; failing evidence exists for each repaired blocker.

### R3W1 - Scientific/execution identity repair

Implement O18 and the execution-only/presentation/preparation controls of O20.

Semantic closure: one preparation-scientific identity authority; no execution-only leakage; no unsafe reuse widening.

Functional closure: focused identity/receipt/reuse tests plus stage-local affected prepare/preflight/materialization/restart regression.

### R3W2 - Exact fidelity/TRAIN2 frontier and assembled persistence/orchestration

Implement O20 and O21 using real config/persistent campaign consumers.

Semantic closure: each tuple/horizon change reaches exactly the intended dependency frontier; historical evidence is never relabeled; full schedule identity remains independent of stage limits.

Functional closure: independent `n1`/`n2`/`n3`/`n` frontier tests and A/B/C/D1/D2/D3 assembled bounded integration pass before documentation closeout.

### R3W3 - Current authority/documentation synchronization

Implement O19 after executable behavior is stable.

Update current semantic dependency graph, architecture/spec wording, migration wording, revision index, and current tests; regenerate tracked descendants as required. Historical records remain unchanged.

Closure: structural fixed-number classification and current documentation tests pass. Documentation-only edits do not force reruns of unrelated numerical evidence, but any executable/test-contract changes receive their affected checks.

### R3W4 - Final assembled acceptance

Implement O22:

1. reconcile every parent/Rework1/Rework2/Rework3 material obligation against the assembled candidate;
2. inspect for duplicate identity authority, stale numeric-stage current paths, unsafe reuse, and unintended complexity;
3. re-derive final affected behavioral surface;
4. run fresh complete affected-surface regression;
5. run A/B/C/D1/D2/D3 on the same candidate;
6. run repository-required checks and broader/full available suite when impact cannot be bounded confidently;
7. attribute only demonstrably unrelated pre-existing failures, with concrete test identities and reasons.

No workplan may be called complete while a required affected check is unexecuted or failing.

### R3W5 - Closeout

Only after R3W4 passes:

- update final current generated documentation descendants if needed;
- mark this workplan completed and archive it according to repository policy;
- update active-workplan index to state that Rework 3, not the earlier Rework 2 closeout record, is the final flexible-fidelity closure evidence;
- prepare implementation handoff.

Do not perform full production GPU qualification here.

## 8. Handoff closure

Every independent-review finding maps losslessly to implementation and acceptance:

- execution-only preparation identity leakage -> O18 + R3W1 + execution-only frontier controls;
- revision-105/fixed-fidelity current tests -> O19 + R3W3 + O22;
- numeric current dependency graph -> O19 structural authority repair;
- helper-level A/B/C/D1/D2/D3 -> O21 real-boundary integration;
- incomplete independent `n1/n2/n3/n` frontier -> O20 four-case persistent-state matrix;
- migration wording inconsistency -> O19 documentation reconciliation;
- invalidated Rework 2 closeout evidence -> O22 fresh final acceptance on one candidate.

No known material review finding, protected concern, or required cross-module consequence is intentionally omitted.

## 9. Risks and redesign triggers

- Positive projections are safer than negative filters but can omit a newly introduced scientific dependency. The field-classification tests and source/model/preparation controls must therefore prove both non-over-invalidation and fail-closed scientific invalidation.
- Some execution controls may affect reconstructible cache bytes. That does not automatically make them scientific preparation authority; authenticate the cache realization separately unless the authoritative scientific product genuinely changes.
- Documentation tests may reveal additional stale fixed-stage assumptions outside the files named above. Treat these as affected-surface consequences, not reasons to weaken semantic architecture.
- A historical campaign may lack enough persisted evidence to prove compatibility. Fail closed at the narrowest safe boundary rather than inventing compatibility or forcing blanket recomputation for all campaigns.
- If genuine assembled integration reveals a new scientific/state-machine defect unrelated to the findings above, route it explicitly and reopen only that affected design surface.

## 10. Completion record

Completed on `feat/mlff-end-to-end-performance-v1` after repairing the
preparation semantic projection, adding bounded persistent target-size
orchestration coverage for default and nondefault fidelity schedules, and
synchronizing revision-106 current authority.

Final bounded affected-surface evidence on this candidate:

- `200 passed, 1 skipped` across flexible-fidelity, campaign/store,
  target-size, TRAIN2 runtime, SIZE-FIDELITY, PERF-P2R, migration-reuse, and
  current documentation surfaces;
- the one skip requires an unavailable real LTA training root;
- GPU/production qualification remains explicitly deferred.
