---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: active
created_date: 2026-08-28
reviewed_source_head: 6f0d34366ca954eabe21740ddda96357afc12eb1
review_revision: 7
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes:
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V3
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V4
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V5
  - CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V6
---

# MLFF target-size scientific simplification — V7 final transition freeze

## 0. Objective and final scientific model

This workplan is the sole implementation authority for the current target-size architecture reset. V7 preserves the clean scientific model accepted in V6 and adds the source-level transition contract required to prevent the old architecture from surviving underneath new names.

The target-size question is deliberately one-dimensional:

> For one fixed MLFF training method/protocol and one fixed target-data construction policy, what is the smallest target-training cardinality `N` beyond which increasing `N` no longer produces a practically meaningful improvement in target accuracy?

Target-size selection is therefore a controlled **data-size convergence experiment**. Cross-validation is a later and separate **methodological-validation experiment**. Electronic-structure provenance is precise descriptive evidence, not an automatic training-compatibility partition.

The final current-generation lifecycle is:

```text
source labels + precise provenance
 -> canonical usable frame data
 -> neutral correlation/statistical development population
 -> one target-size train/evaluation split
      P_train        M3 reserve
         |             |
         |             +-> pi_eval -> M1 subset M2 subset M3
         |
         +-> one deterministic training order pi_train
                    |
              T_N = pi_train[:N]
                    |
       one common deterministic preparation
                    |
       paired optimizer seeds for each N
                    |
          n1/M1 -> n2/M2 -> n3/M3
                    |
           freeze N_selected/T_selected
                    |
             post-selection CV
                    |
             fresh final production
                    |
      downstream held-out/calibration/locked evidence
```

Priority remains:

```text
scientific/product correctness
  > minimum justified product/system complexity
  > performance/resource efficiency
  > development convenience / obsolete-state compatibility
```

Raw scientific inputs and independently valid low-level caches may be reused when their recipes remain valid. The old derived architecture is not migrated or reinterpreted. Full long GPU/real-production qualification remains deferred to the established final-release phase; functional regression/integration is mandatory throughout implementation.

---

## 1. Final-review findings that V7 freezes

The final Software Design review against source head `6f0d34366ca954eabe21740ddda96357afc12eb1` found several places where V6 could still have been implemented as a thin facade over the retired model. These are now explicit design constraints.

### 1.1 Provenance compatibility currently contaminates upstream identity

Current source does more than report `LabelDomain`:

- DATA2 builds compatibility domains, may fail on unresolved domains, assigns every source a `label_domain_id`, and computes atomic-reference identifiability by label domain;
- DATA3 requires every frame to have a resolved `label_domain_id` and hashes that compatibility-group ID into the label-payload/labeled-configuration fingerprint;
- DATA5 embeds `label_domain_id` into partition-condition and partition-unit identity;
- downstream difficulty, feature-fit, target-role, selection, materialization, EVAL2 and MLCV objects repeatedly use that domain identity as a scientific partition.

Therefore V7 does **not** merely ignore label domains inside target-size. The new current generation removes compatibility-group assignment from training eligibility, frame label identity, partition identity and target-size ownership.

The existing decomposed `ElectronicStructureFingerprint` remains useful and should be preserved or cleanly evolved. XC, DFT+U, hybrid, PAW/pseudopotential, spin, dispersion, selected energy-reference/smearing information, derivative conventions, numerical quality, k-points and software/parser provenance remain recorded precisely.

Different fingerprints may coexist in one user-authorized training corpus. DFT versus DFT+U versus hybrid versus differing smearing or numerical settings are **not** automatic hard blockers. Heterogeneity is reported as provenance diagnostics/warnings.

Hard rejection is limited to evidence that is unusable for the configured numerical training operation, for example:

- required numerical labels are absent;
- geometry or required labels are corrupt/non-finite;
- units/sign/conventions cannot be canonicalized into the configured training representation;
- source data fail an explicitly requested user filter;
- another concrete mechanical training-engine constraint is positively demonstrated.

### 1.2 Canonical label identity is not provenance-group identity

New DATA3 label identity must separate **what numerical labels are trained** from **where they came from**.

`label_payload_digest` (or its successor) binds the canonical numerical training payload and the semantic information needed to interpret it, such as:

- selected energy channel/semantic role as required for reproducibility;
- canonical energy units/reference representation used by training;
- canonical force/stress units/sign/convention identity;
- quantized energy/force/stress values under the label-fingerprint policy.

It must **not** hash an advisory compatibility-group/domain assignment.

Precise electronic-structure provenance is carried separately on the source/frame record, e.g. by `electronic_structure_fingerprint_digest` or an equivalent provenance reference. A correction to advisory grouping/reporting policy must not change frame UIDs, canonical numerical label identity, duplicate geometry identity, training membership, partition identity or target-size result when the actual canonical labels are unchanged.

A change that changes the actual canonical numerical label interpretation or values is scientific input change and does invalidate descendants.

### 1.3 DATA5 is not a neutral base today

Current DATA5 is simultaneously:

- label-domain partitioning;
- correlation/statistical units;
- outer roles;
- CV construction;
- leakage/blinding state.

That conflation must not survive. New current-generation pre-target statistical state retains the useful correlation/temporal/event/condition machinery but removes compatibility-domain partitioning and pre-target CV ownership.

Neutral partition/correlation identities may include actual physical/statistical facts such as:

- run/source lineage;
- temporal blocks/autocorrelation information;
- duplicate/near-duplicate/correlation family identity;
- structural realization/replica/reference-group identity;
- composition;
- temperature/condition;
- strain/regime;
- protected event windows;
- explicit user labels relevant to statistical grouping.

Electronic-structure provenance may be reported or used as an advisory diagnostic stratum, but it is not a mandatory split key or an independent role-budget axis.

### 1.4 TARGET-DATA2A cannot be adapted as the V7 boundary

Current `TargetDataRoleFreeze`/`TargetDataDomainRoleFreeze` are explicitly per-label-domain outer/CV role authorities. They verify CV roles while constructing target-size development authority. They are retired from the reachable V7 target-size path.

V7 replaces them with one simple study split authority over neutral target-development data. It owns only the training-authorized population and the exact target-size evaluation reserve/correlation evidence needed to prove disjointness.

### 1.5 Old selection kernels are useful; old scientific topology is not

Current MVSEL2/REPAIR2 contain valuable optimized algorithms: sparse forward CSR views, lazy exact scoring/frontiers, correlation balancing, diversity/representativeness scoring, active-shell repair, and independent reference/oracle paths.

Those algorithms may be reused or refactored internally.

The current-generation public/persisted topology is nevertheless only:

```text
P_train + frozen selection features/policy
 -> TargetTrainingOrder
      pi_train
      diagnostics
      policy/input identities
```

There is no current public/persisted FEAS1 -> MVIDX1 -> MVSEL2 -> REPAIR2 -> MVSTATE2 -> MVQUAL chain. There is no per-label-domain master order or intersection of qualified sizes across domains.

### 1.6 EVAL2 metric engine is retained; its old population authority is replaced

Current EVAL2 target metrics, correlation-block reductions, bootstrap/comparison machinery, target-first ranking and optimized caches are reusable.

Current `Eval2TargetRole` population semantics are not: they require label-domain identity and use development complements or CV monitor populations.

V7 introduces direct target-size roles for exact `M1`, `M2`, `M3` and a separate post-selection CV role. No complement subtraction/fallback and no target-size label-domain role remain.

### 1.7 Production materialization target-size mode cannot be carried forward

Current `ProductionMaterializationPlan` target-size candidate semantics require prescribed prefixes for every final/CV DATA7 domain and one evaluation cohort per label domain. Reusing those fields behind new names would recreate the retired architecture.

V7 target-size candidate materialization is an explicit current-generation contract around:

- exact `T_N` membership;
- common preparation identity;
- optimizer seed;
- target-size study/policy identity;
- exact active fidelity boundary/continuation ancestry;
- shared replay/training protocol;
- exact boundary evaluation role `M_i` handled by EVAL2.

The realization may be a refactored generic materialization plan or a lean target-size-specific input object, but it must call the existing shared DATA8/MACE/TRAIN2 lifecycle rather than create another training engine.

### 1.8 Old tests are old architecture evidence, not future requirements

Current tests deliberately assert the old route through MVSEL2/REPAIR2/MVQUAL2, old prepare receipt keys, fixed sizes, label-domain namespace resolution and per-final/CV-domain target-size materialization.

Those assertions must be replaced. Do not keep them green with aliases, adapters or shadow records.

Preserve the genuinely useful behavioral coverage from those tests:

- one public target-size scheduler;
- public `train`/`evaluate` cannot become a second screening owner;
- CV execution cannot precede selected-size freeze;
- exact continuation/restart boundaries;
- paired optimizer seeds;
- production epoch horizon independent of the screen;
- disk-backed state/restart checks;
- real DATA8/TRAIN2/EVAL2 owner tests;
- numerical-failure evidence semantics;
- optimized-kernel reference/performance tests.

---

## 2. Target-size experiment and seed semantics

### 2.1 Independent variable

The material experimental variable is:

```text
N = number of target configurations used for gradient training
```

For each candidate size:

```text
T_N = pi_train[:N]
```

All non-`N` scientific choices remain fixed except for stochastic realization controlled by the optimizer seed.

### 2.2 Deterministic common preparation

Current DATA7 feature/E0/weight fitting is deterministic and does not carry the optimizer seed. V7 preserves this distinction.

One common target-size preparation identity is frozen before candidate trajectories. It may derive from `P_train` and the configured foundation/training protocol, but never from `M1/M2/M3`, CV evaluation, outer held-out, calibration or locked evidence.

As applicable it freezes:

- feature/projection preprocessing policy and its fixed algorithmic seed when randomized numerical decomposition is needed;
- atomic reference/E0 policy and fitted common result;
- objective/property/configuration weight policy;
- replay source/exposure policy;
- foundation/model initialization identity;
- model architecture/head policy;
- optimizer/LR policy except optimizer seed;
- precision/backend;
- batch/exposure semantics;
- target-size metric/evaluation policy.

Do not introduce candidate-specific E0/normalization/objective refits merely because old APIs are domain-local. The purpose is to compare `N`, not to refit a different preprocessing problem at each `N`.

If the external training engine proves that a mathematically necessary quantity depends on `N`, that dependency must be explicit and is a design-reopen condition rather than a hidden implementation detail.

### 2.3 Optimizer-seed pairing

Stochastic training variation is controlled by the ordered optimizer seed set belonging to the sole enabled target-size training method.

Current policy freezes exactly two screening optimizer seeds by default/current production policy:

```text
[1, 2]
```

Two seeds are a deliberate statistical/computational compromise. More independent optimizer seeds could reduce stochastic uncertainty further, but they multiply training work and are not added adaptively or automatically in this architecture.

Required pairing:

```text
for each N:
    run seed 1
    run seed 2

compare N values using the same ordered seed identities
```

For a given optimizer seed, the same seed-controlled stochastic policy is reused for every `N` and through exact `n1 -> n2 -> n3` continuation. This pairs initialization/shuffling/stochastic training effects across candidate sizes and reduces seed variance when the two paired trajectories are aggregated.

The contract does **not** claim byte-identical random-number consumption after `N` changes: different dataset cardinalities can naturally change the sequence of minibatches or RNG draws. The invariant is same seed and same stochastic policy, not an impossible identical stochastic path across different datasets.

Current aggregation remains the policy-defined paired arithmetic mean unless deliberately changed by a future policy revision. Missing, duplicate, reordered or candidate-specific seed populations make the affected comparison incomplete/unrankable.

A seed-set change is a target-size scientific-policy change and invalidates target-size evidence and descendants.

### 2.4 Seed namespace hygiene

Only the optimizer seed pair is the replicate dimension of the target-size experiment.

Other seeds must have explicit separate ownership:

| Seed class | Target-size semantics |
| --- | --- |
| optimizer seeds from sole enabled training method | paired stochastic replicate dimension; same ordered seeds for every `N` |
| feature-projection/randomized linear-algebra seed | fixed preprocessing policy for entire study; not a replicate |
| replay split/subselection seed | fixed common training protocol; not a replicate |
| evaluation-order/sampling seed, if any | fixed M-ladder policy; not a replicate |
| EVAL2 bootstrap seed | fixed inferential reduction policy; not a training replicate |
| online/training diagnostic monitor seed | fixed diagnostic policy; not a replicate and cannot control target-size ranking |
| CV fold partition seed | post-selection CV only; absent from target-size identity |

No seed namespace may be implicitly inherited merely because it has the field name `seed`.

---

## 3. Precise provenance without compatibility enforcement

### 3.1 Preserve provenance facts

Retain or evolve the existing decomposed electronic-structure record:

- XC/theory settings;
- DFT+U settings;
- hybrid/dispersion settings;
- PAW/pseudopotential descriptors;
- spin settings;
- selected energy channel/reference/smearing semantics;
- force/stress units/sign/convention;
- numerical settings, k-points and SCF quality information;
- source software/version and parser provenance;
- resolution/partial-resolution notes.

### 3.2 Advisory reporting

Produce deterministic provenance diagnostics such as:

- counts/configurations by exact fingerprint or compact provenance group;
- which metadata dimensions vary across the corpus;
- unresolved/partial fields;
- selected energy-channel distribution;
- numerical-quality range/flags.

These records are observability/reporting evidence. A change only to advisory grouping/report presentation does not invalidate training computation.

### 3.3 No automatic domain eligibility split

Do not automatically reject, separate the target-size study, multiply candidate ladders, multiply capacity, or instantiate separate target heads because fingerprints differ.

If a future product genuinely requires different target heads/training protocols, that is a design reopen with explicit evidence; it is not inferred from current provenance metadata.

---

## 4. Neutral DATA2/DATA3/DATA5 scientific base

### 4.1 DATA2 source catalog

New current DATA2:

- stores precise source/electronic-structure provenance;
- stores selected canonical energy-channel evidence;
- does not fail merely because a compatibility domain is unresolved;
- does not require compatibility-domain assignment for a source to proceed;
- does not use compatibility domains as the owning scope for target-training atomic-reference feasibility.

Compatibility comparisons/groups may survive only as optional diagnostic/report helpers if clearly non-authoritative.

### 4.2 DATA3 frame identity

New current frame records carry source/provenance reference separately from canonical label identity.

Remove mandatory `label_domain_id` from the scientific identity path.

Frame UID remains occurrence identity based on source occurrence + frame index unless another independent reason requires change.

Canonical label payload must not contain compatibility-group assignment. Duplicate geometry remains geometry-only; labeled-configuration identity remains geometry + canonical numerical label payload.

### 4.3 Neutral statistical/correlation base

New pre-target statistical state owns:

- correlation/partition units;
- condition/regime/event/lineage evidence;
- outer protected roles if required by the broader product;
- pre-target leakage/disjointness evidence;
- no target-size label-domain fanout;
- no CV fold plan.

Partition condition/unit IDs do not include compatibility `label_domain_id`.

Cross-validation algorithms may be retained as reusable code but are invoked only after `T_selected` freezes.

### 4.4 Atomic reference/E0 diagnostics

Atomic-reference identifiability and fitting for the common target-size protocol operate on the common authorized preparation/training population, not independently per compatibility domain.

Provenance-stratified rank/identifiability reports are allowed as diagnostics.

---

## 5. Target-size data split and capacity

Let `U_size` be all user-authorized, numerically usable target-development configurations after any genuinely protected downstream/outer roles are excluded.

Canonical configuration:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

Resolve once:

```text
candidate_sizes = [2^p for p in pmin..pmax]
Nmax = max(candidate_sizes)
(m1,m2,m3) = [2^q for q in evaluation_size_powers]
(n1,n2,n3) = fidelity_epochs
```

Nominal lower bound:

```text
|U_size| >= Nmax + m3
```

This is not multiplied by provenance groups, label domains, CV folds, optimizer seeds, candidate count or cumulative inference work.

Correlation/duplicate constraints may make a nominal count infeasible, so preflight must prove an actual disjoint allocation.

One deterministic split owner constructs:

```text
P_train
M3  # exact evaluation reserve of m3 configurations
```

with:

```text
P_train intersect M3 = empty
|P_train| >= Nmax
|M3| = m3
```

Training support has priority. M3 should preferentially use redundant residual support while preserving useful representative coverage and respecting actual leakage/correlation constraints.

A correlation group constrains split assignment but does not become a label/provenance domain and does not multiply the target-size study.

---

## 6. One training order and one evaluation ladder

### 6.1 Target training order

Expose exactly one current target-training selection authority:

```text
build_target_training_order(P_train, frozen_features, policy)
 -> pi_train
 -> diagnostics
```

The implementation may reuse optimized old kernels for structural/environmental diversity, composition/condition/event support, fixed foundation-model residual/difficulty information, target-label tails, correlation balancing and deterministic repair of obvious support holes.

The output is one deterministic order. Each candidate is an exact prefix:

```text
T_N = pi_train[:N]
```

Simple candidate qualification:

- exact prefix exists at N;
- required canonical labels are usable;
- explicitly configured hard support obligations, if any, are met.

Rich coverage/diversity/residual diagnostics do not require multiple public gate objects.

### 6.2 Evaluation ladder

Order exact M3 once before the first candidate trajectory:

```text
pi_eval = deterministic order over M3
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
```

The ordering may use only frozen candidate-independent evidence. It cannot use target-size candidate predictions, survivor outcomes or selected N.

Persist representative/correlation diagnostics. M1/M2/M3 are evaluation configurations, not claims of IID independent samples.

---

## 7. Exact target-size screening

Preserve the accepted useful funnel:

```text
q qualified sizes
 -> n1 on M1: q -> min(q,4)
 -> n2 on M2: <=4 -> 2
 -> n3 on M3: 2 -> 1
```

Requirements:

- same ordered two optimizer seeds for every N;
- same deterministic common preparation for every N and seed;
- same training protocol except N and optimizer seed;
- exact continuation of model/optimizer/RNG state for survivors from n1 to n2 to n3;
- no restart from epoch zero at later rungs;
- ordinary target-success early stopping cannot truncate a screen boundary;
- target-side force metric and practical-equivalence policy own ranking;
- smaller N wins inside practical equivalence;
- replay/CV/physical/deployment evidence cannot rank or tie-break N;
- eliminated candidates receive no later ordinary screen work;
- M1/M2/M3 are direct evaluation populations, not complements;
- configured largest target size is the ceiling;
- if it remains materially superior, return typed `nonconverged_at_configured_ceiling` rather than inventing a rescue size;
- candidate-specific numerical TRAIN2/EVAL2 failures remain typed scientific failure evidence only where positively identified; ordinary programming/input/resource/lineage failures remain execution errors.

Terminal result freezes:

```text
N_selected
T_selected = pi_train[:N_selected]
```

Both are immutable for downstream CV/final production under the same training protocol.

---

## 8. Shared training/materialization boundaries

### 8.1 Target-size candidate materialization

The new target-size materialization contract contains no label-domain list and no CV fold list.

Each materialized target-size variant is identified by at least:

```text
N
optimizer_seed
T_N digest
common preparation digest
training protocol/family digest
active screening policy/boundary identity
```

There is exactly one target-size job per required `(N, optimizer_seed)` trajectory; `cross_validation_folds = 0` during target-size screening.

### 8.2 Reuse DATA8 and TRAIN2 execution machinery

Preserve:

- fixed-file caches and atomic promotion;
- replay staging;
- foundation checkpoint/head staging;
- MACE config generation;
- accelerator backend/precision behavior;
- shared TRAIN2 lifecycle/resource ownership;
- checkpoint publication and exact continuation;
- parallel scheduling/telemetry/resource budgets.

Do not fork a second execution engine for V7.

### 8.3 Training-harness validation input

MACE currently expects a target validation file. During target-size screening, any such training-harness validation/diagnostic input must be fixed and explicitly non-controlling:

- no gradient contribution;
- no LR-schedule mutation;
- no generic early-stop authority;
- no candidate ranking/survivor authority;
- no M1/M2/M3, outer held-out, calibration or locked data routed through a generic controlling path.

Only exact boundary EVAL2 on the authorized `M_i` controls target-size ranking.

### 8.4 EVAL2

Replace only the population/role authority. Reuse target metric calculation, correlation-block reductions, target-first comparisons, numerical guards, caches and resource-optimized inference path.

Target-size EVAL2 role identity directly binds exact M_i membership and correlation-block evidence. CV EVAL2 roles are created only after selected-data freeze.

---

## 9. Cross-validation is downstream-only

Only after `N_selected/T_selected` freeze:

```text
T_selected -> CV plan -> methodological validation
```

CV owns its own fold count, partition seed, fold monitoring/evaluation policy and any fold-local preparation required by the accepted CV methodology.

Rules:

- CV consumes only configurations in T_selected;
- correlation/duplicate groups constrain fold assignment but never pull unselected sibling frames back into the dataset;
- CV settings/results are absent from target-size identity;
- CV cannot change N_selected;
- CV failure is a methodological-validation failure;
- if CV demonstrates a need for a material training-method/protocol change, the changed method receives a new target-size experiment because the method whose convergence is being measured has changed.

New MLCV role records descend from selected-data identity and exact selected-frame memberships/correlation groups. The old DATA5/label-domain/unit-ID CV-role catalog is not current authority.

---

## 10. Fresh final production

After CV acceptance:

- start fresh from the accepted foundation/initialization;
- use full exact T_selected for target gradients;
- use the accepted common training method/protocol;
- production epoch horizon is independent of n3;
- frozen M3 may remain development/model-selection evidence if required;
- replay TRUE_DFT evidence may act only according to the accepted downstream admissibility policy;
- outer held-out/calibration/locked evidence remains downstream and is not retroactively described as independent if it influenced model selection.

---

## 11. Old -> new authority transition map

| Current source authority | V7 end state | Transition disposition |
| --- | --- | --- |
| `ElectronicStructureFingerprint` | precise provenance record | retain/evolve |
| `LabelCompatibilityPolicy`, compatibility decisions/domains as eligibility partitions | optional advisory provenance diagnostics only | remove from training eligibility/current scientific identity |
| `TrainingDataSource.label_domain_id` mandatory downstream assignment | separate provenance digest/reference; no compatibility-domain requirement | replace current schema/meaning |
| `label_payload_digest(... label_domain_id ...)` | canonical numerical label payload independent of advisory grouping | replace schema |
| `TrainingFrameRecord.label_domain_id` | provenance reference separate from numerical label identity | replace current schema |
| per-domain atomic-reference identifiability | common/global training-preparation identifiability + optional provenance diagnostics | replace authority |
| `PartitionConditionKey.label_domain_id`, `PartitionUnit.label_domain_id` | neutral statistical/correlation condition/unit identity | replace current schema |
| DATA5 `cross_validation_plans` pre-target ownership | post-T_selected CV plan | remove from current pre-target bundle |
| `TargetDataRoleFreeze` / per-domain role freeze | one target-size P_train/M3 split | retire from current path |
| DATA6 per-label/CV difficulty domains | explicit neutral P_train target-selection feature evidence; postselected CV evidence separately | refactor/reuse low-level prediction kernels |
| `FeatureFitDomain` final/CV label-domain topology for target-size | one explicit common target-size preparation population | refactor low-level fitters; retire old target-size dependence |
| FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL public chain | one `TargetTrainingOrder` + diagnostics | retain useful kernels internally; retire public current chain |
| fixed target sizes/ceiling | configured power ladder/ceiling | replace |
| `TargetSizeStudyCandidate.domain_prefix_digests` | one exact T_N data digest | replace |
| EVAL2 complement/coarse/CV target roles | exact M1/M2/M3 roles + separate postselected CV roles | replace role schema; retain metric engine |
| `ProductionMaterializationPlan` target-size per-domain prefix/eval fields | explicit V7 candidate membership/common-prep contract | remove old target-size fields from current path |
| old DATA5-derived `MlcvRoleCatalog` | exact T_selected postselection CV roles | replace current CV authority |
| target-size-v5 prepare contract/receipt and old record keys | new V7 generation/receipt | destructive reset; no migration |
| V5 topology tests | V7 scientific/transition tests | replace old topology assertions; preserve useful behavioral tests |

---

## 12. Persistence, restart and invalidation DAG

V7 is a new scientific generation. Do not migrate old derived target-size state.

### 12.1 Reuse boundary

Safe reuse is content/recipe driven, not schema translation.

- raw source files and manifest remain reusable;
- low-level parse/cache products may be reused only when their recipe does not depend on retired compatibility/domain semantics;
- precise electronic-structure fingerprint parsing may be reused if unchanged;
- DATA2 current authority is rebuilt because compatibility/eligibility semantics change;
- DATA3 authority is rebuilt because label-payload/frame schema changes;
- DATA4 authority should be rebuilt through current identities; low-level content-addressed geometry/descriptor cache hits may naturally survive where recipes remain exactly valid;
- DATA5 and all target-size/DATA6-selection/DATA7/DATA8/TRAIN2/EVAL2/CV/production descendants are rebuilt under V7.

Do not create a migration adapter merely to reuse old derived records.

### 12.2 Identity separation

Advisory provenance-report identity is separate from training-math identity.

A change only to how provenance fingerprints are grouped/presented must not invalidate target-size computation.

Training/target-size identity changes when materially relevant inputs change, including:

- actual source/frame membership or canonical numerical labels;
- canonical label interpretation/conversion policy;
- target/evaluation size powers;
- fidelity boundaries;
- ordered optimizer seed set;
- training-order policy/features that affect pi_train;
- split/evaluation-order policy that affects P_train/M ladder;
- common preparation/training scientific policy;
- target-size metric/practical-equivalence policy;
- foundation/replay scientific identity where part of the experiment.

CV-only settings such as fold count/partition seed invalidate CV descendants only.

Production-only budget/adaptive settings invalidate production descendants only.

### 12.3 Restart invariants

Same V7 scientific config/input must reconstruct the same:

- neutral frame/partition identities;
- P_train/M3 split;
- pi_train/pi_eval;
- common preparation;
- candidate T_N identities;
- ordered seed set;
- exact continuation ancestry;
- selected N/T_selected.

Old V5/current-generation derived state in a workspace is rejected with an actionable reset/reprepare message before any candidate reuse occurs.

---

## 13. Atomic transition strategy: no half-old/half-new current runtime

The implementation may build new components alongside old components **inside the implementation branch while they are unreachable**. This allows staged testing without forcing a giant untestable edit.

The production/current runtime may not expose both architectures simultaneously.

Frozen cutover rule:

```text
Before cutover:
    old current runtime remains complete
    new V7 components are internal/unreachable scaffolding

Atomic cutover stage:
    current prepare/select-target-size/config/persistence switch to V7
    old current target-size call edges/receipt keys are removed in same stage

After cutover:
    only V7 may be reachable as current runtime
    old code may remain briefly only if unreachable and scheduled for cleanup
```

Forbidden transitional realizations:

- runtime feature flag selecting V5 versus V7;
- “try V7, fallback V5”;
- constructing V7 objects from V5 domain maps;
- writing both old and new authoritative records;
- compatibility aliases that silently reinterpret old schemas as V7;
- retaining CV/domain requirements merely to satisfy old tests;
- using a new wrapper around old `TargetDataRoleFreeze`/MVQUAL/per-domain materialization while claiming one-study semantics.

---

## 14. Implementation gates

### Gate A — permanent documentation/spec reset

On the implementation branch, update normative architecture/specification/source-map/config documentation before executable cutover.

Required conceptual diagram:

```text
precise provenance (advisory)
 -> canonical usable frames
 -> neutral statistical/correlation base
 -> P_train/M3
 -> one pi_train + one pi_eval/M ladder
 -> paired-seed N convergence
 -> freeze T_selected
 -> post-selection CV
 -> final production
```

Document seed taxonomy and distinguish common deterministic preparation from optimizer-seed stochastic realization.

Do not merge future-state docs alone while executable code remains old.

### Gate B — neutral provenance and DATA3 identity substrate (new/inactive first)

Implement new current-generation source/frame identities:

- preserve exact electronic-structure provenance;
- remove unresolved compatibility-domain failure as generic training blocker;
- remove compatibility group from canonical label payload;
- carry provenance separately;
- update duplicate/labeled-configuration identity accordingly;
- replace per-domain atomic-reference feasibility as target-training authority.

Acceptance:

- mixed DFT, DFT+U, hybrid/smearing provenance remains usable when canonical labels are usable;
- unresolved/partial provenance is reported, not automatically rejected;
- mechanically unusable labels still fail;
- changing compatibility/grouping policy alone leaves frame UID, canonical label payload, labeled-configuration identity and target-usable membership unchanged;
- changing actual canonical label values/interpretation changes scientific identity;
- affected DATA2/DATA3/identity/duplicate regression passes.

### Gate C — neutral statistical base (new/inactive first)

Build/refactor current-generation partition/correlation state without label-domain identity and without CV plans.

Preserve proven temporal block/autocorrelation/event/lineage/condition algorithms.

Acceptance:

- compatibility/provenance grouping changes do not change partition unit identities/outer roles;
- actual condition/correlation changes do;
- protected outer roles remain disjoint where required;
- neutral correlation groups support later target split/CV;
- no pre-target CV plan is required;
- affected partition/leakage/blinding regression passes.

### Gate D — V7 target-size core against neutral substrate (still not public runtime)

Implement:

- power/evaluation/fidelity config resolver;
- one P_train/M3 split;
- one pi_train authority using refactored optimized kernels;
- one pi_eval/M1/M2/M3 ladder;
- one common deterministic preparation;
- exact candidate T_N identity;
- V7 target-size policy/evidence/reducer;
- exact M-rung EVAL2 role constructors using existing metric engine;
- seed taxonomy and ordered two-seed pairing.

Acceptance:

- one study independent of provenance-group count;
- Nmax+m3 capacity with no domain/fold/seed multiplier;
- exact nested T_N and M_i;
- deterministic split/orders/restart;
- same common preparation digest for every N and seed;
- exactly same ordered optimizer seeds for every N;
- seed-family identity independent of optimizer seed and variant identity seed-bound;
- missing/reordered seed evidence fails comparison;
- optimized kernels match reference/oracle semantics and retain bounded performance.

### Gate E — candidate materialization + shared TRAIN2/EVAL2 integration

Refactor target-size candidate materialization away from per-domain/CV `ProductionMaterializationPlan` semantics while preserving shared DATA8/TRAIN2 execution.

Assemble real semantic path:

```text
T_N + common preparation + optimizer seed
 -> DATA8 fixed target/replay files
 -> shared TRAIN2 exact boundary
 -> authenticated checkpoint/optimizer/RNG state
 -> EVAL2 exact M_i
 -> target-size evidence/reducer
```

Acceptance:

- exactly one target-size trajectory per `(N, optimizer_seed)`;
- CV folds are zero/not constructed;
- MACE config receives optimizer seed;
- same seed is reused across N and through continuation;
- n2 continues exact n1 state; n3 continues exact n2 state;
- common prep does not vary by seed/N;
- training-harness target-valid input is demonstrably non-controlling;
- M_i does not enter gradients/generic stopping;
- no complement population;
- no per-domain prescribed prefix/evaluation fields;
- real DATA8/TRAIN2/EVAL2 owner regression passes.

### Gate F — atomic current-runtime and persistence cutover

This is the single stage where current executable ownership changes.

In one coherent change:

1. bump current campaign/prepare target-size generation/contract;
2. switch current `prepare`/`select-target-size` to neutral DATA2/3/5 + V7 split/order/prep/study/materialization/EVAL2;
3. change current state/receipt record keys to V7 only;
4. remove current call edges to `TargetDataRoleFreeze`, public FEAS/MVIDX/MVSEL/REPAIR/MVQUAL plans, per-domain target-size resolver, complement EVAL2 roles and V5 candidate authority;
5. reject old derived workspace generation with actionable destructive-reset guidance;
6. retain guard that public ordinary `train`/`evaluate` commands cannot become a second target-size scheduler.

Required structural/real-owner evidence:

- current prepare receipt contains no old target-size chain keys;
- current core source/import graph has no reachable old target-size role/resolver calls;
- no current target-size record contains label-domain maps or CV plans;
- bounded integration through real config parser + SQLite store + current prepare/select-target-size + real V7 schemas/materialization/EVAL2;
- stage-local complete affected regression before continuing.

### Gate G — post-selection CV and fresh final production

Implement CV only after T_selected freeze using exact selected frame membership and neutral correlation groups.

Refactor MLCV roles away from DATA5 label-domain/CV lineage.

Then build fresh final production on full exact T_selected.

Acceptance:

- CV settings/fold seed cannot alter/rebuild target-size state;
- all CV frames are in T_selected;
- correlation groups do not cross forbidden fold roles;
- group identity never adds an unselected sibling frame;
- CV failure cannot choose another N;
- material method change after CV failure requires new target-size experiment;
- final production starts fresh and uses full T_selected;
- production horizon independent of n3;
- affected CV/MLCV/DATA7/DATA8/TRAIN2 regression passes.

### Gate H — destructive cleanup and public-surface simplification

After V7 runtime has passed stage-local regression, remove unreachable retired target-size architecture.

Delete/unexport as applicable:

- compatibility-domain training eligibility/fanout paths;
- old DATA3 compatibility-domain label identity schema from current use;
- old label-domain partition condition/unit current schemas;
- `TargetDataRoleFreeze` current target-size usage;
- public/persisted FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL target-size plans;
- fixed target-size/ceiling authorities;
- target-size `domain_prefix_digests`;
- complement/coarse EVAL2 population authorities;
- old target-size candidate per-domain prefix/evaluation materialization fields;
- old preselection MLCV role/catalog authority;
- V5 target-size prepare contract/receipt/migration aliases;
- tests whose only purpose is retired topology.

Retain/rename internal optimized kernels/reference oracles/benchmarks where V7 still uses them.

Run structural absence/import/package regression.

### Gate I — final functional closure

Re-derive affected surface from the assembled final diff.

Run:

- complete affected regression;
- broader/full repository suite because this change crosses DATA2/DATA3/DATA5/selection/materialization/persistence boundaries unless a smaller surface is independently proven sufficient;
- real-owner CLI integration from config through prepare -> target-size selection -> selected-data freeze -> CV creation -> final-production entry;
- restart/invalidation matrix;
- deterministic/reference/performance checks;
- documentation build/lint/reference/PDF checks;
- structural uniqueness/absence inspection.

Report separately:

1. functional acceptance;
2. M-ladder scientific decision-preservation qualification;
3. long GPU/real-production qualification (deferred to final target-machine release).

---

## 15. Mandatory acceptance matrix

At minimum prove all of the following.

### Provenance / identity

- DFT, DFT+U, hybrid, smearing, PAW/numerical/software differences are precisely recorded but do not automatically split/block target training;
- unresolved provenance fields are reportable without compatibility-domain failure when labels are usable;
- mechanically invalid/unconvertible labels fail cleanly;
- compatibility/report grouping policy change alone does not alter numerical label identity, partition identity, target pool or target-size result;
- no target-size current schema contains `label_domain_id` as a study dimension.

### Configuration / seeds

- default and non-default target/evaluation powers resolve correctly;
- no hidden scientific <=16384 guard;
- `[training].max_num_epochs` remains production horizon, not target-size n3;
- only the sole enabled method's ordered optimizer seed set owns target-size stochastic replicates;
- current default/required screening set is two seeds `[1,2]` unless explicitly changed by a new policy/config;
- same ordered seed set used at every N;
- feature-projection/replay/eval/bootstrap/monitor/CV seeds cannot masquerade as optimizer replicates;
- CV fold seed absent from target-size identity;
- target-size seed-set edit invalidates target-size descendants; CV fold-seed edit does not.

### Statistical data model

- exactly one study regardless of provenance-group count;
- nominal capacity Nmax+m3 and real disjoint feasibility;
- P_train and M3 disjoint under actual correlation constraints;
- one pi_train; exact T_N prefixes;
- one pi_eval; exact M1 subset M2 subset M3;
- evaluation order freezes before candidate results;
- no CV plan required to prepare/select target size.

### Preparation / training

- one common deterministic preparation identity reused for every N and optimizer seed;
- no candidate-specific E0/normalization/objective refit introduced by this redesign;
- same optimizer seed is paired across N;
- exact n1 -> n2 -> n3 continuation;
- ordinary early stop cannot truncate screen boundary;
- MACE required validation/diagnostic channel cannot control N ranking;
- replay/physical/deployment/CV evidence cannot rank N.

### EVAL2 / selection

- EVAL2 target-size role is exact M_i, not complement;
- retained metric/reduction engine produces reference-equivalent results;
- practical-equivalence smaller-N rule works;
- eliminated candidates receive no later work;
- configured-ceiling nonconvergence is typed;
- selected N/T_selected freeze before CV.

### CV / production

- CV uses only exact T_selected;
- no unit/group expansion introduces unselected frames;
- CV-only changes preserve target-size result/identity;
- CV failure does not choose another N;
- fresh production uses full T_selected;
- production max epoch independent n3.

### Transition / persistence

- old V5 workspace derived state cannot be silently reused/rebound;
- no dual V5/V7 runtime switch or fallback exists;
- current prepare receipt/state contains only V7 authority;
- current public exports/runtime do not expose old target-size plans as current authority;
- old per-domain/complement/CV-coupled target-size call edges are structurally absent;
- deterministic V7 restart reproduces split/orders/prep/candidates/selected data.

### Performance

- optimized selection/repair/EVAL2/DATA8/TRAIN2 machinery retained or replaced only with reference-equivalent implementations;
- no accidental scalar/repeated-domain algorithmic regression;
- bounded CPU/RAM/VRAM/I/O/reference benchmarks run where affected;
- full long GPU qualification remains deferred.

---

## 16. Structural absence checklist after cutover

The final current target-size path must not depend on or persist retired concepts equivalent to:

```text
FIXED_TARGET_SIZES
FIXED_TARGET_SIZE_CEILING
domain_prefix_digests
TargetDataRoleFreeze / TargetDataDomainRoleFreeze
size_development_complement
size_development_coarse
preselection cross_validation_plans as target-size input
per-domain target-size candidate/materializability/qualification maps
prescribed_final_development_prefixes
prescribed_training_domain_prefixes
prescribed_target_size_evaluation_frames
V5 target-size candidate authority/migration/receipt aliases
public FEAS/MVIDX/MVSEL/REPAIR/MVQUAL plan chain as current target-size state
```

`label_domain_id` may remain in explicitly historical code or optional provenance-report helpers during/after cleanup, but it must not occur in the reachable V7 target-size scientific path or new neutral partition/frame numerical-identity schemas.

---

## 17. Scientific M-ladder qualification

Functional tests do not prove that the default evaluation ladder `[256, 512, 1024]` preserves the same data-size decision as a larger reference population.

Separate retrospective/reference qualification should test:

1. M1 preserves reference-competitive candidates;
2. M2 preserves the reference finalist set;
3. M3 selects the same N under the practical-equivalence/smaller-size rule;
4. support/correlation diagnostics remain representative enough for the intended target population;
5. coverage-aware M ordering performs at least as well as sensible same-cardinality baselines where representative evidence exists.

Do not tune M using post-selection CV, calibration or locked evidence.

If representative evidence is unavailable, report `deferred/unavailable`, not passed.

---

## 18. Frozen, delegated and reopen rules

### Frozen

- precise electronic-structure provenance is advisory by default, not a compatibility training gate;
- canonical numerical label identity is separate from provenance grouping;
- compatibility grouping does not participate in frame/partition/target-size scientific identity;
- one target-size study across user-authorized usable target data;
- neutral pre-target statistical/correlation base, no pre-target CV plan;
- target-size independent variable is N;
- common deterministic preparation is held fixed across N and seeds;
- stochastic training is paired by the same ordered optimizer seeds across N;
- current screen uses two optimizer seeds as the statistical/computational compromise; no adaptive seed expansion;
- one P_train/M3 split, one pi_train, one pi_eval/M ladder, one reducer;
- power-configured candidate/evaluation ladders and configured ceiling;
- nominal Nmax+m3 capacity;
- exact continuation, target-side practical-equivalence ranking, smaller-N preference;
- CV only after selected-data freeze and incapable of changing N;
- fresh final production after CV acceptance;
- EVAL2 metric engine/shared DATA8/TRAIN2/resource machinery preserved where semantically valid;
- destructive new generation with no old-derived-state migration;
- atomic runtime cutover: no reachable mixed V5/V7 architecture;
- stage-local affected regression plus final affected/integration testing;
- long GPU production qualification deferred.

### Delegated

- concrete class/module/schema names for neutral DATA2/3/5, split, training order, common preparation and V7 materialization;
- whether advisory provenance grouping helpers are retained, renamed or replaced;
- internal vectorized/sparse/index representation;
- exact deterministic split/training/evaluation ordering heuristics consistent with frozen priorities;
- which MVSEL2/REPAIR2/EVAL2 low-level kernels are reused/refactored;
- exact content-addressed cache layout;
- exact local test-fixture/fake implementation below protected semantic owners;
- exact implementation of postselected CV-local preparation, provided it cannot feed back into target-size.

### Reopen only on evidence

1. the training engine demonstrably cannot consume mixed provenance after canonical unit/convention conversion;
2. a specific provenance difference is shown to make labels mathematically unusable together rather than merely heterogeneous/noisy;
3. removing compatibility domain from frame/partition identity breaks another material supported product responsibility that cannot be represented by provenance metadata/neutral grouping;
4. one deterministic training order cannot preserve required target-data support without a materially different scientific algorithm;
5. the default M ladder fails decision-preservation qualification;
6. a training transform is proven to require N-dependent fitting for correct size comparison;
7. two optimizer seeds are empirically inadequate for the required decision reliability and added compute is justified;
8. a real product requirement appears for separate target models/heads/studies rather than one mixed corpus;
9. a real implementation/performance bound invalidates the configured power-ladder or transition design;
10. the shared TRAIN2/DATA8/MACE interface cannot provide a non-controlling validation channel during exact screening without material redesign.

---

## 19. Freeze verdict

The final source-level review found that the largest remaining risk was not the V6 scientific model but **accidental retention of old authority through upstream identity and materialization schemas**. V7 closes that risk explicitly.

Implementation should not attempt to incrementally reinterpret the old architecture. Build the neutral foundations and V7 owners in inactive/tested form, then switch current runtime/persistence in one atomic cutover, then delete the old reachable topology.

The frozen scientific model is intentionally small:

```text
record provenance
 -> canonicalize usable labels
 -> neutral statistical data
 -> split train/evaluation
 -> order training data once
 -> compare N with two paired optimizer seeds
 -> freeze selected data
 -> validate methodology with CV
 -> train final model
```

Further issues are implementation/conformance defects unless they trigger one of the explicit reopen conditions above.
