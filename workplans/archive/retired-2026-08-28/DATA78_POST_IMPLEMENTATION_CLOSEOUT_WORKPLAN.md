---
kind: implementation-workplan
workplan_id: DATA78-CLOSEOUT1
protocol_version: 5.2.0
---

# DATA78-CLOSEOUT1 — Post-implementation materialization closeout

**Status:** active — C8-C13 implemented and locally qualified on supplied latest source; C14 target-host profiling and C15 target-host closeout remain pending
**Current authority:** `docs/specs/training_data/mlff_data9a9b_production_materialization_spec.md`, `docs/specs/training_data/mlff_cpu_resource_budget_spec.md`, `docs/arch_manuals/mlff_training_data/60_execution_performance.md`
**Effective source baseline:** supplied `mdstats-feat-target-size-v5-redesign (10).zip`, SHA-256 `ff667985d7c29c3f088229799a7af9ded8a7afc6e037e42a1682fdae1f141307`
**Current implementation baseline:** supplied `mdstats-feat-target-size-v5-redesign (11).zip`, SHA-256 `1279f179adaaca66d757705cd59c16f9c197a40228deafc1b3a8d9d206dd50e1`; archive comment/source commit `8c4cd16ab8fe0add381f0234897cc9b91ccc8daa`; local patch-baseline commit `6620f8a6539e8af4f5cbdeef1764598072138262`
**Applied C5 implementation:** `DATA78_C5_target_size_planning_fit_core_latest10_v2.patch`, SHA-256 `5dfbd3a58f0df38f86c7aa0ba14ad32823c74e7fbf1aaf729c58692b4034d70d`
**Equivalent user patch chain:** `DATA78_C5_target_size_planning_fit_core_latest10.patch` + `DATA78_C5_top_level_prefix_matrix_export_hotfix.patch` produces byte-identical source to the v2 patch above.

## Objective

Close the remaining DATA7/DATA8 correctness, restart, cache-determinism, resource-accounting, orchestration, and performance gaps without changing target-size scientific semantics, weakening exact hashes/digests, or creating another scientific authority or nested scheduler.

The immediate requirement is stronger than fixing the currently observed `KeyError`: recent C5 changes crossed several semantic namespaces and cache boundaries without an execution-level integration test. The next implementation must correct the owning boundaries and then prove the complete `_prepare_materialization()` path in seconds before another target-host run is requested.

## Engineering envelope and invariants

- Runtime CPU budget remains the live 90% rule; never encode workstation-specific `28` as policy.
- DATA6 owns GPU work. DATA7/DATA8 remain CPU-side; the target-host log already shows ~22.7 GiB free on the RTX 3090 at this boundary.
- External authoritative inputs are copied/authenticated into mdstats-owned immutable snapshots before reusable hardlinking.
- Target-size candidate membership remains exactly the authenticated REPAIR2 prefix for the requested candidate size.
- Candidate evaluation membership remains the development complement of the **maximum qualified** target-size prefix, never a shrinking stage survivor set.
- `TargetCoverageDomainReference.label_domain_id`, `source_label_domain_id`, and `training_domain_digest` are distinct semantic identities and must never be used interchangeably.
- `ProductionMaterializationPlan` owns canonical DATA5/CV feature-fit domains; callers must not be able to redefine the scientific domain set for convenience.
- A shared recipe is a deterministic scientific/execution contract. If two locally available results for one recipe differ, fail closed rather than choose an arbitrary winner.
- DATA7 fitted-core reuse is execution-only. A complete validated `Data7PreparationBundle` remains the scientific artifact authority.
- Completed/restart caches are reconstructible. Corrupt or stale execution caches may be discarded and rebuilt without weakening scientific validation.
- No performance optimization may change exact component digests, final DATA7 bundle digests, DATA8 bytes/identities, selection membership, or numerical policy.
- Domain-level and any future within-domain concurrency must not nest blindly or oversubscribe CPU/RAM.
- Regression qualification for memory-sensitive materialization tests must use fresh-process groups or explicit resource snapshots so pytest/cgroup memory retention is not misdiagnosed as a product admission failure.

## Completed foundation gates retained from earlier closeout

C1-C4 remain accepted: immutable external-input snapshotting, shared MLCV realization/frame-index reuse, DATA8 transient RAM/disk accounting, and real materialization restart/failure semantics. C6 GPU release is also materially observed on the target RTX 3090. These are not reopened unless the corrective implementation regresses them.

C5A-C5D produced useful architecture that is retained in principle: linear target-prefix materialization, immutable digest memoization, corrected DATA7 full-recipe scope, and selection-invariant fitted-core reuse. However, C5G is **reopened** because unit/lower-layer qualification failed to exercise the actual campaign bridge and several runtime/authority defects escaped.

## Post-C5 bug chronology and final-review findings

### F1 — top-level bulk-prefix export escaped tests — fixed in current v2, regression lesson

The first C5 workstation run failed because `_prepare_materialization()` called `mdstats.materialize_candidate_prefix_matrix()` while the top-level lazy facade did not export it. The v2 patch/hotfix fixes this, but the failure proves lower-level helper tests are not sufficient. The real campaign orchestration must become an acceptance test.

### F2 — coverage-authority ID passed to DATA2A role namespace — blocking

Current C5 planning builds `target_labels` from `TargetCoverageDomainReference.label_domain_id`. CV coverage domains use synthetic authority IDs such as:

`<source-label>::cross_validation_training:fold0:<training-domain-digest>`

The code then calls `TargetDataRoleFreeze.domain(label)`, whose keys are source label-domain IDs. This causes the observed workstation `KeyError`.

### F3 — candidate evaluation map has the inverse namespace mismatch — blocking latent crash

A one-line F2 fix is insufficient. The current evaluation dictionary is keyed by coverage-authority IDs but later read using `FeatureFitDomain.label_domain_id` (source label-domain ID). A scratch correction of F2 reaches this second `KeyError` during materialization-plan construction.

### F4 — eager all-domain × all-size bulk planning is unnecessary and enlarged the failure surface — high

Screening variants have `folds=0`, yet the current bulk matrix materializes every final/CV coverage domain for every requested size. Screening only needs the actual final-development training domains plus the final-domain maximum-qualified prefix used for the comparison cohort. The synthetic CV IDs that caused F2 were not needed for the observed screening run at all.

### F5 — `feature_fit_domains=` weakens canonical plan ownership — blocking authority regression

C5 added an optional feature-domain injection to `build_production_materialization_plan()`. The builder accepts supplied same-lineage domains without proving they equal the canonical domains derived from DATA5 + CV plans. Dynamic review confirmed a plan with four canonical domains can be rebuilt with only the three CV domains and zero final-development domains.

The micro-optimization is not worth the authority bypass. Canonical domains must be rebuilt by the plan owner.

### F6 — plan topology validation is not strong enough as defense in depth — high

`ProductionMaterializationPlan.__post_init__()` currently requires unique content digests and checks the set of CV `(label, fold)` pairs, but it does not explicitly reject duplicate topology keys or require exactly one final-development domain per source label. A malformed/injected plan can therefore survive farther than it should. Strengthen topology invariants independently of F5.

### F7 — fitted-core cache has recipe identity but no result identity — blocking fail-closed gap

`_data7_fit_core_digest()` authenticates inputs to metric/E0/weight construction, but `_ReusableData7FitCore` and its index do not authenticate the actual fitted result. Two valid carriers can satisfy the same recipe predicate while carrying different fitted metric/E0/weight digests. Current in-memory registration can silently overwrite one with the other.

### F8 — fitted-core index publication is last-writer-wins — blocking race gap

The fitted-core index uses atomic `os.replace`. Two publishers can both observe no index, publish different carriers for the same recipe, and each proceed without ever observing a conflict. Adding metadata alone is insufficient; publication must be create-once/validate-winner.

### F9 — the full shared DATA7 cache has the same deterministic-result gap — newly confirmed, blocking

Dynamic review produced two different internally valid DATA7 bundles that both satisfy `_data7_bundle_matches_plan()` for the same full DATA7 recipe. Publishing the first and then attempting to publish the divergent second silently returned the first winner rather than detecting the disagreement.

For a full DATA7 recipe, once a producer has actually computed a local bundle, a concurrent/existing winner must match that producer's exact scientific bundle digest; deterministic archive bytes should also remain exact for the current writer schema.

### F10 — reusable fitted-core validation can convert a stale execution cache into a hard run failure — medium/high

The production layer first applies a coarse plan predicate to a carrier, then passes it into `build_data7_preparation_bundle()`, where exact foundation prediction/reference inputs are checked. If the coarse predicate passes but the exact reuse contract fails, the build raises instead of invalidating that reconstructible carrier and performing a fresh fit. Execution-cache invalidity should not make an otherwise valid scientific run impossible.

### F11 — RAM admission still charges selection-only reuse as a full fit — newly confirmed, medium/high

The queue estimate is always `_estimate_data7_domain_peak_bytes(...)`, even when an authenticated fitted-core carrier exists. Dynamic review created a valid fitted-core cache and then ran the next target size with a RAM budget one byte below the full-fit estimate; the run was rejected with `DeterministicWorkQueueMemoryError` before it could use the much cheaper/memory-mapped reuse path.

Reuse needs its own conservative peak-memory estimate or an admission class that reflects carrier load + selection/coverage + archive realization rather than refitting.

### F12 — orchestration tests are structurally too shallow — blocking acceptance gap

The target-authority tests and C5 lower-layer tests pass while the real campaign path crashes. Existing topology checks mainly inspect source strings; fitted-core tests call `run_restartable_production_materialization()` directly. No fast test drives the real bridge:

`TargetCoverageReference -> _prepare_materialization() -> target-size membership projection -> ProductionMaterializationPlan -> first DATA7 call`.

### F13 — workplan provenance/status drifted — process correctness gap

The prior active workplan still named local baseline `473c455` and marked C5G locally complete even after the source was rebased to supplied `(10)` and workstation integration failures appeared. The exact source archive and patch SHA above are now the closeout baseline.

### F14 — remaining performance work is still conditional, not yet a correctness fix

After correctness is stabilized, `folds=0, domains=1` still gives one outer DATA7 worker with BLAS/OpenMP/PyTorch CPU width 1. The fitted core may therefore remain CPU-underutilized. Full DATA7 archives also still duplicate the fitted matrix/weights across candidate sizes. Both require target-host profiling after C8-C13; do not add another scheduler or split persistence format before measurement.

## Corrective gates

### C8 — Freeze exact baseline and install a fast real orchestration acceptance seam

**Goal:** make the costly workstation run the final qualification step rather than the debugger.

**Work:**

- bind implementation and tests to the exact effective source baseline recorded above;
- add a fast integration fixture that calls the real `_prepare_materialization()` orchestration;
- stub only genuinely heavyweight/external boundaries (final MACE training/materialization execution where necessary), not target-role/coverage/REPAIR2/target-size/plan construction;
- stop relying on `inspect.getsource()` as evidence that orchestration semantics work.

**Required matrix:**

1. pre-selection screening: coverage authority contains final + CV domains while the variant itself has `folds=0`;
2. selected production with canonical CV plans;
3. selected production with noncanonical/per-seed CV partition authority;
4. multi-label-domain case if the existing fixture can express it cheaply;
5. completed-materialization reuse path;
6. 3 -> 10 -> 30 epoch target-size continuation without changing the fixed comparison cohort.

**Acceptance:** each case reaches at least first real materialization invocation/validated reuse without namespace/export/plan-construction exceptions; the suite runs in seconds.

### C9 — Replace ad-hoc target-prefix dictionaries with one namespace-safe execution resolver

**Goal:** confine coverage synthetic identities to one boundary and eliminate F2-F4 rather than patching dictionary keys individually.

**Design:** introduce one internal, nonpersistent target-size materialization resolver owned by campaign preparation. It references existing scientific authorities and is not serialized as a new authority.

Its public-to-caller keys are explicit:

- `(training_domain_digest, target_size) -> exact prescribed prefix`;
- `source_label_domain_id -> fixed candidate evaluation cohort` for final-development domains only.

Internally it may use `TargetCoverageDomainReference.label_domain_id` only to query REPAIR2/target-size candidate prefix authority.

**Rules:**

- build a unique `training_domain_digest -> TargetCoverageDomainReference` map and fail on ambiguity;
- build a unique final-development `source_label_domain_id -> TargetCoverageDomainReference` map and fail on ambiguity;
- verify mapped coverage kind/fold/source label agrees with the requested `FeatureFitDomain`;
- cache prefixes lazily for actual requested training domains/sizes instead of materializing all coverage domains × all sizes;
- for candidate evaluation, use the authenticated final coverage domain's own `frame_uids` and subtract its maximum-qualified prefix; no `TargetDataRoleFreeze.domain(synthetic-id)` lookup is necessary;
- keep the maximum-qualified size fixed across 3/10/30 stages;
- selected production does not construct a candidate evaluation cohort.

**Acceptance:** synthetic coverage authority IDs do not escape the resolver into role-freeze, plan evaluation keys, or DATA7 domain maps; prefix helper call count scales with unique requested `(training domain, size)` pairs.

### C10 — Restore canonical feature-domain ownership and strengthen plan topology invariants

**Goal:** eliminate F5/F6 and make malformed domain topology fail at the earliest owner.

**Work:**

- remove the `feature_fit_domains=` bypass from `build_production_materialization_plan()`;
- always derive canonical domains from DATA5 + the supplied authenticated CV plans inside the plan builder;
- campaign-local feature-domain caching may still be used for coverage lookup/performance, but it does not define plan authority;
- strengthen `ProductionMaterializationPlan.__post_init__()` to require unique topology keys `(label_domain_id, kind, fold_index)`;
- require exactly one final-development domain for every source label represented by the plan;
- require CV topology exactly equals the configured CV-plan folds without duplicate domains;
- retain exact prescribed-prefix binding to every canonical final/CV domain for target-size-controlled materialization.

**Acceptance:** missing final domain, duplicate final domain, duplicate CV topology key, wrong CV fold membership, and arbitrary same-lineage injected domain fixtures all fail before DATA7 execution.

### C11 — Add deterministic DATA7 result identities and race-safe publication

**Goal:** one recipe must never silently map to two different results.

#### C11A — full DATA7 recipe cache

- when a producer has computed a local DATA7 bundle and a cache winner already exists or wins concurrently, require winner `bundle_digest == local bundle.content_digest`;
- for the current deterministic archive writer, also test exact file SHA equality for equivalent bundles; any unexpected byte divergence is a persistence determinism defect, not a reason to weaken validation;
- retain ordinary cache-hit reuse without refitting when no local result exists to compare.

#### C11B — fitted-core result identity

Define an execution-only fitted result digest over exactly the reused components, for example:

`H(fitted_metric.content_digest, atomic_reference_fit.content_digest, training_weights.content_digest, checkpoint_metric_policy.policy_digest)`.

- add the result digest to `_ReusableData7FitCore` and a new fitted-core index schema;
- old reconstructible v1 fit-core indices may be treated as cache misses rather than migrated in place;
- every index load verifies the carrier reproduces the recorded fitted-result digest;
- in-process promoted carrier registration uses one centralized conflict-checking helper rather than raw dictionary assignment.

#### C11C — create-once publication

- replace fitted-core `os.replace` last-writer-wins publication with create-once/validate-winner semantics;
- concurrent equivalent publishers converge;
- concurrent divergent fitted results for one fit-core recipe hard-fail and report both result digests/carrier identities;
- if cross-platform numerical drift is ever observed, version/strengthen the recipe identity rather than silently selecting one result.

**Acceptance:** direct sequential and true concurrent tests prove divergent full DATA7 results and divergent fitted-core results cannot be silently accepted for one recipe.

### C12 — Make fitted-core reuse validation and resource admission execution-cache-safe

**Goal:** a reconstructible cache should accelerate a valid run, never make it fail solely because the cached carrier is stale or because admission assumes a full refit.

**Work:**

- factor one exact fitted-component reuse validator used by both `build_data7_preparation_bundle()` and production cache selection; include exact domain/lineage/policies plus foundation prediction vector, reference E0 mapping, and foundation identity where residual fitting is active;
- if an execution-cache carrier fails this validator, invalidate/drop that carrier/index and perform a fresh fit; direct explicit API misuse may still raise;
- add a conservative reuse-path RAM estimate covering authenticated carrier mmap/load, selection/coverage realization, and archive output without charging the full feature-fit peak;
- keep a safe floor and fail if the reuse path itself cannot fit;
- preserve the 128-frame amortization floor unless representative evidence justifies changing it.

**Acceptance:** a stale fit-core index cannot crash an otherwise valid materialization; a cache-reuse workload that fits the reuse estimate is not rejected merely because the hypothetical full-fit estimate exceeds RAM.

### C13 — End-to-end regression and adversarial qualification before any target-host rerun

**Goal:** close the class of bugs that previously escaped local testing.

**Required tests:**

- top-level/public export smoke for every campaign-called facade symbol, or direct-owner import if the bulk helper is intentionally made internal;
- C8 three-state orchestration matrix;
- candidate evaluation cohort equals `final_coverage_domain.frame_uids - max_qualified_prefix` exactly;
- no CV/synthetic authority ID is ever passed to DATA2A role lookup;
- each actual `FeatureFitDomain.content_digest` receives the prefix from the matching coverage `training_domain_digest`;
- selected canonical and per-seed CV production bind every domain exactly once;
- exact refit-vs-fitted-core-reuse equality for component and final DATA7 digests;
- persistent restart after fitted-core publication;
- v1 full-DATA7 cache compatibility;
- full DATA7 same-recipe divergent-result rejection;
- fitted-core same-recipe divergent-result rejection, sequential and concurrent;
- stale fitted-core carrier invalidation + fresh-fit fallback;
- reuse-aware constrained-RAM admission;
- out-of-order DATA7 completion/failure/restart and DATA8 snapshot/resource tests from C1-C4 remain green.

**Regression execution policy:** run memory-heavy materialization groups in fresh processes or with explicit resource snapshots. Compare known stale/baseline failures against the exact `(10)` baseline rather than allowing them to obscure new regressions.

**Current review evidence before implementation:**

- target role/coverage/target-size/topology subset: 67 passed;
- C5/parallel/restart DATA7 materialization subset: 10 passed;
- campaign performance: 11 passed;
- prior broader review: production materialization 37/39 with 2 failures reproduced on untouched `(10)`; campaign CLI 39 passed, 1 skipped, 4 failures reproduced on untouched `(10)`;
- despite these passes, the real workstation orchestration still failed, which is why the C8 integration gate is mandatory.

**C8-C13 local implementation evidence on supplied `(11)` baseline:**

- target-size v5 topology/study: 49 passed;
- production materialization: all 47 non-baseline tests passed in fresh-process groups; the two remaining preflight tests fail identically on untouched `(11)` because their monkeypatch targets the lazy facade while `command_preflight()` resolves the core owner directly;
- DATA7/DATA8/campaign-performance runtime and artifact group: 39 passed; the two specification-only failures (`SelectionBudgetPolicy` token and historical `0.20.35a0` architecture-status assertion) reproduce identically on untouched `(11)`;
- DATA9A9C + TRAIN2A + TRAIN2B + downstream DATA9B runtime group: 53 passed, 1 skipped because the optional supplied MACE smoke package is unavailable, and 2 failures reproduce identically on untouched `(11)` (STOR2 test fixture lacks immutable DATA8 authority; CUEQ provider test uses a non-MACE `b"model"` checkpoint while patching the facade rather than the core owner);
- the C8 bridge drives real `_prepare_materialization()` through screening `folds=0`, selected canonical CV, and selected derived/per-seed CV to the first DATA7 invocation;
- adversarial C11/C12 coverage passes for full-DATA7 deterministic-result rejection, sequential/concurrent fitted-core divergence rejection, stale-carrier invalidation/refit, exact residual-foundation reuse validation, and reuse-aware constrained-RAM admission;
- C1-C4 restart/out-of-order/DATA8 snapshot/resource regressions remain green inside the production-materialization group.
- permanent architecture/specification Markdown changes were republished to the tracked assembled Markdown/PDF artifacts; PDF render inspection shows no clipping, overlap, black boxes, or broken glyphs.

### C14 — Reprofile only after correctness closes; conditionally optimize the remaining bottleneck

**Goal:** determine whether further complexity is materially justified after one correct fitted core is reused across sizes/seeds.

**Target-host evidence:**

- planning wall time and prefix-helper call count;
- fitted-core construction count and wall time;
- selection/coverage time per size;
- DATA7 archive read/write bytes and wall time;
- CPU utilization and effective worker count;
- peak RSS and admission decisions;
- DATA8 fixed-file throughput and storage saturation;
- cold computation, shared-cache reuse, and completed-materialization reuse reported separately.

**Conditional redesign triggers:**

- if one remaining fitted core is wall-time dominant and CPU/memory bandwidth are materially idle, design within-domain component parallelism using the existing global 90% budget; do not blindly raise BLAS width or nest schedulers;
- if repeated full DATA7 archive I/O/storage becomes material after compute reuse, design a shared immutable core + small selection-overlay persistence format; otherwise keep the simpler full-bundle archive;
- if DATA8 throughput saturates storage at low width, encode an evidence-backed width cap rather than adding more workers.

### C15 — Documentation, provenance, final patch, and archive

**Goal:** only declare closeout complete after the corrected product path and target-host qualification agree.

**Work:**

- reconcile architecture/spec text to the accepted resolver/cache ownership and result-determinism contracts;
- remove superseded ad-hoc target-prefix dictionaries/helpers if the resolver replaces them;
- remove the plan-domain injection API and any tests/docs that treat it as supported;
- update workplan evidence with exact source Git commit if available, otherwise retain archive SHA provenance;
- run `compileall`, `git diff --check`, focused/integrated regressions, and exact `git apply --check` against the supplied latest source tree;
- produce one incremental patch against the exact baseline used for implementation;
- archive this workplan only after the target-host preparation reaches/finishes the intended DATA7/DATA8 path and C14 decides whether further performance work is warranted.

## Non-goals for the corrective patch

- no change to target-size selection/convergence statistics or fixed ladder;
- no new persistent scientific target-membership authority;
- no GPU work in DATA7/DATA8;
- no nested domain × component scheduler before C14 profiling;
- no physical DATA7 core/overlay archive split before archive I/O is measured as material;
- no weakening of SHA/content-digest validation to make caches appear reusable;
- no broad cleanup of unrelated baseline test debt.

## Freeze disposition

This plan is design-complete for the next corrective implementation. C8-C13 are blocking before another expensive workstation prepare run. C14 is deliberately evidence-driven and may terminate with “no further scheduler/persistence change required.” C15 is the only archive/merge-closeout gate.
