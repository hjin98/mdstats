---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1
protocol_version: 5.5.0
status: completed
completed_date: 2026-08-25
archived_with: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK2
---

# MLFF Flexible-Fidelity Codebase Rework Workplan

## 1. Objective and accepted end state

Replace the current fixed target-size 3 -> 10 -> 30 screening architecture with a configurable three-boundary successive-fidelity funnel `(n1, n2, n3)`, default `(1, 3, 10)`, while preserving an independent full TRAIN2 training horizon `n`, default `30`.

The completed product must satisfy:

```text
0 < n1 < n2 < n3 <= n

all qualified candidates: 0 -> n1
coarse survivors:       n1 -> n2
short finalists:        n2 -> n3
target-size freeze:           at n3
production model:        0 -> n
```

Every screening checkpoint belongs to one uninterrupted TRAIN2 trajectory whose optimizer, LR schedule, RNG/data ancestry, training identity, and full planned horizon are defined for `n`. A screening boundary is only a work-authorization/pause boundary; it must not become a shortened independent schedule.

This workplan is the accepted Part 2 implementation contract. It explicitly adopts Protocol 5.5.0 and supersedes older active-workplan requirements only on the target-size fidelity epoch/state/schema/configuration surface, as recorded in `workplans/active/README.md`. Unrelated lifecycle, performance, scientific, resource, and acceptance requirements remain authoritative.

## 2. Diagnosis and protected concerns

This is a cross-cutting authority/state/schema correction, not a default-literal edit.

### P1 - duplicated epoch authority

Current target-size code hard-codes 3/10/30 in policy validation, state/outcome names, serializer fields, evidence validation, orchestration branches, and progress text. PERF-P2R additionally carries short/final epoch fields, while campaign training owns `max_num_epochs`.

Protected concern: one semantic owner must exist for the three screen boundaries and one independent owner must exist for full training horizon. No downstream helper may create a competing epoch authority.

### P2 - third screen is incorrectly coupled to production horizon

Current PERF-P2R and campaign orchestration derive production training from `fidelity_epochs[-1]`. That is only accidentally correct while n3 == n == 30.

Protected concern: target-size selection must freeze at n3 while production training remains independently authorized to full `n`.

### P3 - SIZE-FIDELITY reference is accidentally the third screen

Current SIZE-FIDELITY1 uses the last target-size fidelity checkpoint as the eventual/reference outcome. With `(1,3,10)/30`, that would qualify early screens against epoch 10 instead of the full epoch-30 trajectory.

Protected concern: scientific low-fidelity qualification must compare screening decisions against full-horizon reference behavior at `n` and must not weaken existing recall/equivalence criteria to preserve a preferred default.

### P4 - restart identity can be corrupted by shortened schedules

TRAIN2 already supports `execution_epoch_limit` as a pause boundary and validates continuation against full schedule/budget/protocol identities. Replacing that mechanism or building stage-local schedules would risk silently changing optimization history.

Protected concern: surviving candidates must resume exact authenticated checkpoints on the same full-`n` trajectory; stage transitions may change runtime-plan/work-authorization identity but not scientific training/schedule identity.

### P5 - current public/persisted state encodes numeric stages

Current outcomes, fields, methods, exports, and schemas include `awaiting_epoch_3`, `epoch3_*`, `epoch10_*`, `epoch30_*`, and stage `final` where the meaning is the third screen.

Protected concern: current product semantics must be independent of configured numbers. Historical persisted state must never be silently reinterpreted under new defaults.

### P6 - current configuration does not have a real fidelity authoring surface

The Part 1 closeout removed misleading target-size epoch keys from `campaign.toml.example`. The current runtime still uses top-level campaign schema v1 and fixed `TargetSizeStudyPolicy`; historical target-size epoch-looking keys were not authoritative runtime inputs.

Protected concern: new current configuration must have one canonical tuple input and one canonical full-horizon input, while historical campaigns retain their actual historical fixed semantics rather than invented semantics from decorative keys.

### P7 - warm-up heuristic conflicts with the accepted default

Current CLI requires the first target-size boundary to lie strictly after TRAIN2 LR warm-up. With default warm-up fraction 0.05, `(1,3,10)/30` has `1/30 < 0.05` and would be rejected before scientific calibration can evaluate it.

Protected concern: early-screen scientific adequacy is a SIZE-FIDELITY question, not a schedule-phase-position heuristic. The full TRAIN2 LR schedule must not be retimed merely to permit epoch 1.

### P8 - reporting conflates authorized stage work with schedule horizon

The current MACE progress probe uses one `max_epochs` denominator, which can make a bounded screen appear to authorize the full schedule.

Protected concern: operators must be able to distinguish current authorized endpoint from full schedule horizon without altering the schedule itself.

### P9 - performance accounting must preserve continuation savings

Current PERF-P2R correctly models incremental continuation in structure-epoch terms, but its epoch fields still encode fixed/final semantics.

Protected concern: screening work must count only incremental continuation work and must remain target-size weighted. Candidate-epoch counts may be diagnostic but cannot replace structure-epoch workload accounting.

### P10 - documentation is intentionally one generation behind until runtime changes

Part 1 closed with current documentation truthfully describing fixed 3/10/30 behavior; the flexible design lives only in this workplan until executable acceptance succeeds.

Protected concern: current normative docs must be updated only after the executable flexible contract is real, then regenerated from their authoritative sources without rewriting historical records.

## 3. Engineering envelope and preserved behavior

The implementation changes fidelity geometry only. Preserve all unrelated target-size-v5 scientific and product behavior unless direct evidence proves a required local reconciliation:

- fixed candidate universe `(128,256,512,1024,2048,4096,8192,16384)`;
- REPAIR2-prefix materializability and MVQUAL2 hard admission;
- minimum three qualified sizes;
- funnel counts `q -> min(q,4) -> 2 -> 1`;
- paired screening optimizer seed authority from the sole enabled training method;
- arithmetic-mean paired-seed aggregation;
- existing equivalence-aware target-size ordering and deterministic tie behavior;
- target-only authority for all target-size screening decisions;
- existing typed numerical/scientific failure semantics and terminal outcomes;
- no replay/physical hard-pass authority inside target-size selection;
- TRAIN2 `TrainingBudgetPolicy.planned_epochs` and optimizer `max_num_epochs` consistency;
- durable per-epoch checkpoint and exact-continuation machinery;
- existing CUDA/GPU production qualification deferral.

Non-goals:

- do not change the target-size candidate ladder;
- do not redesign REPAIR2/MVQUAL2;
- do not change target/replay scientific weights, LR schedule shape, or warm-up fraction merely to accommodate the new fidelity tuple;
- do not introduce a second full-horizon setting under target-size configuration;
- do not broaden this work into full production GPU qualification;
- do not retain obsolete current numeric-stage APIs merely for cosmetic backward compatibility unless a real supported compatibility contract is found.

## 4. Frozen product design and ownership

### 4.1 Epoch authorities

Frozen:

- `TargetSizeStudyPolicy.fidelity_epochs` is exactly three positive strictly increasing integers `(n1,n2,n3)`.
- Default tuple is `(1,3,10)`.
- Full horizon `n` is owned by `TrainingBudgetPolicy.planned_epochs`, synchronized with `MaceOptimizerPolicy.max_num_epochs` through existing protocol validation.
- Default `n` remains `30`.
- Cross-policy assembly validates `n3 <= n`.
- Target-size policy must not own or duplicate `n`.

Required consequence: any artifact depending on both tuple and horizon must receive/check both authorities or their authenticated digests; it may not infer `n` from `n3`.

### 4.2 Semantic state machine

Current semantic stages are:

```text
coarse
short
final_screen
production
```

Target-size study outcomes are semantic equivalents of:

```text
awaiting_coarse_screen
awaiting_short_screen
awaiting_final_screen
selected
```

Terminal failure/nonconvergence outcomes remain otherwise unchanged.

Required consequence: current fields/methods/serializer keys/public exports that encode `epoch3`, `epoch10`, or `epoch30` must become semantic. Stage-to-boundary mapping is derived from the active tuple, never from a global numeric map.

Suggested canonical current names:

```text
coarse_survivor_limit
short_finalist_count
coarse_outcomes
coarse_survivor_sizes
short_outcomes
short_finalist_sizes
final_screen_outcomes
attach_coarse_outcomes
attach_short_outcomes
attach_final_screen_outcomes
```

Exact spelling may follow repository conventions, but numeric epoch values must not be embedded in current names.

### 4.3 TRAIN2 continuation

Frozen:

- reuse `Train2RuntimePlan.execution_epoch_limit` and existing exact continuation machinery;
- stage execution limits are n1, n2, n3, and n for coarse, short, final-screen, and production work respectively;
- `TrainingBudgetPolicy`, LR policy, optimizer policy, training protocol, planned epochs, planned structures, and schedule identity remain full-`n` authorities throughout all screen continuations;
- a survivor resumes the prior authenticated checkpoint/optimizer/RNG/EMA state;
- eliminated candidates receive no later work.

Required consequence: runtime-plan digests may legitimately differ across stage limits while schedule/training/checkpoint scientific identity remains compatible for continuation. Do not put the execution limit into a scientific identity in a way that makes legitimate continuation appear to be a different schedule.

### 4.4 Warm-up rule reconciliation

Frozen design change:

- remove the current hard requirement `n1 / n > train2_warmup_end_fraction` from target-size policy/config assembly;
- retain the TRAIN2 LR schedule and default warm-up fraction unchanged;
- allow a valid tuple such as `(1,3,10)/30` even when n1 lies inside warm-up;
- SIZE-FIDELITY1, not a phase-position heuristic, decides whether such an early screen is scientifically faithful.

This does not pre-qualify epoch 1 scientifically. If representative SIZE-FIDELITY evidence later fails the accepted criteria, reopen only the default tuple decision; do not restore the warm-up heuristic or weaken qualification.

### 4.5 Campaign configuration generation

Frozen:

- current flexible campaign configuration advances from top-level campaign schema v1 to a new schema generation; at the reviewed branch this is `mdstats.mlff-campaign-cli.v2`;
- v2 current authoring uses:

```toml
[target_data.size_convergence]
fidelity_epochs = [1, 3, 10]

[training]
max_num_epochs = 30
```

- `init` writes `fidelity_epochs` explicitly;
- resolved current policy always contains the tuple and full horizon even if API-level constructors expose defaults;
- v2 rejects the old three target-size epoch keys and rejects mixed-generation old/new keys;
- legacy full horizon is recovered from historical canonical training authority, never from `final_training_epochs`.

Historical v1/schema-less TRAIN2 campaigns:

- preserve actual historical fixed fidelity `(3,10,30)`;
- do not reinterpret old decorative `coarse_training_epochs`, `short_training_epochs`, or `final_training_epochs` as previously effective authorities;
- if those legacy-looking keys are present with exactly the historical fixed values, they may be normalized/ignored through an explicit compatibility path with one actionable warning;
- if they contain non-historical values, fail closed because the old runtime did not honor them and their intended semantics cannot be reconstructed safely;
- a legacy config containing the new `fidelity_epochs` field without the new schema boundary fails as mixed-generation input.

Configuration normalization must happen centrally before downstream policy assembly.

### 4.6 Persistence and restart compatibility

Frozen:

- authoritative persisted target-size study/restart state from the immediately preceding fixed generation must be either migrated exactly or rejected with an explicit supported-boundary error; no new-default substitution is allowed;
- validate an old artifact's digest under its old schema before semantic conversion;
- old fixed generation reconstructs `(3,10,30)` and historical full horizon from authenticated historical training/budget evidence;
- current writers emit only new semantic schemas;
- derived caches/performance/qualification artifacts may be invalidated and rebuilt instead of migrated when they are not authoritative user/restart state and rebuilding is cheaper/safer;
- exact schema suffixes for new internal artifacts are delegated, but every materially changed serialized record must use a distinct current schema/version.

Known old current-generation surfaces that require explicit classification during implementation include target-size policy v6, training evidence v7, trajectory-failure v1, stage-outcome v1, target-size plan v8, SIZE-FIDELITY v2/v1 artifacts, and PERF-P2R v2/v3/v1 artifacts.

### 4.7 SIZE-FIDELITY1

Frozen scientific roles:

```text
production coarse screen = n1
production short screen  = n2
production final screen  = n3
full reference endpoint  = n
```

Execution plan must carry/derive distinct semantic fields equivalent to:

```text
short_screen_epoch
final_screen_epoch
reference_training_epoch
required_checkpoint_epochs = unique(coarse_calibration_candidates, n2, n3, n)
```

Calibration-policy requirements:

- first coarse calibration candidate equals production n1;
- every coarse calibration candidate is strictly less than n2;
- first coarse equivalence width equals production coarse equivalence width;
- existing required coarse/short finalist recall thresholds and monitor-decision-equivalence policy are preserved;
- for default `(1,3,10)`, the current fixed `(3,4,5)` coarse candidate default is invalid and must be replaced by a valid default such as `(1,2)`; nondefault tests must pass explicit valid candidates, e.g. `(2,3,4)` for `(2,5,12)`.

Reference finalist/winner behavior must be derived from full-role metrics at epoch `n`, not n3. Current `eventual_*` naming must become `reference_*` or equivalent. The final-screen decision must be assessed for consistency with the full-horizon reference outcome under the existing target-size equivalence/ordering rules; earlier screens must not falsely eliminate the full-horizon reference winner/finalists under the existing qualification criteria.

When `n3 == n`, one physical checkpoint/evaluation can satisfy both roles. Deduplicate physical work while retaining both semantic roles in validation/reporting.

### 4.8 PERF-P2R

PERF-P2R must consume screen boundaries from target-size policy and full horizon from TRAIN2 budget. Its active stage plan has semantically distinct fields equivalent to:

```text
stage
start_epoch
target_epoch
schedule_horizon_epoch
```

Required geometry:

```text
coarse       start=0   target=n1 schedule=n
short        start=n1  target=n2 schedule=n
final_screen start=n2  target=n3 schedule=n
production   start=0   target=n  schedule=n
```

`PerfP2RParameterGrid` must not remain a second authority for active n2/n3 boundaries. Calibration/benchmark candidate dimensions may remain where they have a distinct role, but active screen geometry comes from the target-size policy.

Primary workload accounting is structure-epochs. For admissible candidate set A, coarse survivor set S, final-screen input set F, and target-size value `N_i` structures per epoch:

```text
W_screen = n1 * sum_A(N_i)
         + (n2-n1) * sum_S(N_i)
         + (n3-n2) * sum_F(N_i)

W_reference = n * sum_A(N_i)
W_production = n * N_selected
```

Production work is separate from screening savings. Candidate-epoch count

```text
|A|*n1 + |S|*(n2-n1) + |F|*(n3-n2)
```

may remain as a secondary scheduling diagnostic, not as a replacement for structure-epoch accounting.

### 4.9 Campaign orchestration

Frozen:

- campaign train/evaluate/select paths consume one semantic stage geometry rather than independently re-deriving numeric epochs in multiple branches;
- selected state authorizes production to canonical `n`, not n3;
- continuation authorization is semantic (`start_epoch > 0` / stage says continuation), not `target_epoch > 3`;
- EVAL2 attaches evidence through semantic stage mapping from active policy;
- parent evidence comes from the previous semantic stage, not literal epoch branching;
- selected/frozen target size is printed after final-screen reduction.

Suggested realization: reuse/extend one stage-plan abstraction across orchestration and PERF-P2R where that reduces duplicate authority without making a performance artifact a mandatory scientific owner. Equivalent single-source stage geometry is acceptable.

### 4.10 Progress and status

Screening progress must distinguish current authorized endpoint from full schedule horizon. Stable structured semantics are preferred:

```text
stage=coarse-screen;       epoch=1/1;  schedule_horizon=30
stage=short-screen;        epoch=2/3;  schedule_horizon=30
stage=final-screen;        epoch=7/10; schedule_horizon=30
stage=production;          epoch=17/30
```

For nondefault `(2,5,12)/40`, stage denominators must be `/2`, `/5`, `/12`, and production `/40`. ETA/remaining-work computation for a bounded screen must use authorized stage work, while LR schedule progress continues to use full `n`.

### 4.11 Identity and cache semantics

Frozen:

- tuple `(n1,n2,n3)` participates in target-size policy/state/evidence identity wherever screen geometry changes meaning;
- full `n` participates in TRAIN2 budget/LR/schedule/training/checkpoint identity;
- cross-dependent execution/qualification plans authenticate both;
- changing any one screen boundary invalidates dependent target-size evidence/plans;
- changing `n` invalidates schedule/training/checkpoint identity and cross-dependent plans;
- a checkpoint from n=30 cannot be reused as the same scientific trajectory under n=40 merely because its current epoch matches;
- presentation-only fields must not unnecessarily invalidate scientific caches.

### 4.12 Public API and compatibility

Current public exports must use semantic stage/outcome/attach names. Numeric-stage public aliases are not retained by default.

If repository evidence demonstrates a real supported public compatibility requirement, the implementer may retain narrowly scoped deprecated wrappers that delegate to semantic current APIs, emit appropriate deprecation signaling, and never appear in current schemas/config/writers. This is a local reconciliation, not a second current authority.

### 4.13 Documentation publication

Only after the executable flexible contract passes its integrated runtime gate, reconcile current documentation from fixed 3/10/30 to flexible fidelity. Historical/archive records remain unchanged.

At minimum inspect/update authoritative sources and generated descendants for:

- README current overview;
- `campaign.toml.example` and generated `init` template;
- canonical MLFF architecture chapters and generated architecture Markdown/PDF/manifest;
- training-data dependency graph and Stage-11 graph;
- target-size, SIZE-FIDELITY1, PERF-P2R, progress-reporting, data-stage, and FINAL-GPU1 current specifications;
- campaign CLI user guide and current FINAL-GPU1 runbooks;
- documentation specification tests.

Current docs must describe implemented present behavior, not future workplan chronology.

## 5. Delegated implementation mechanics

The implementer may choose, while preserving all frozen semantics:

- exact helper/class boundaries and module-local factoring;
- enum vs string representation where repository conventions allow either;
- exact new internal schema suffixes and authority-version suffixes;
- whether a derived artifact is migrated or explicitly invalidated/rebuilt when it is not authoritative restart/user state;
- exact deprecation wrapper placement if a real compatibility requirement is discovered;
- exact structured progress field names and text punctuation;
- exact shared default constant placement;
- exact test file organization and lightweight fixtures;
- whether one shared stage-geometry value object is reused by target-size orchestration and PERF-P2R, provided ownership remains target-size tuple + TRAIN2 horizon.

Implementation may incorporate newly discovered local consequences required to realize this contract. It must not silently change a frozen product decision.

## 6. Reopen only on evidence

Reopen only the minimum affected design surface if evidence proves one of the following:

1. canonical full-horizon ownership is no longer `TrainingBudgetPolicy.planned_epochs` synchronized with optimizer max epochs;
2. existing TRAIN2 continuation cannot preserve identical full-`n` schedule/training ancestry across new pause boundaries;
3. authoritative historical target-size restart state cannot be reconstructed safely from its authenticated old schema;
4. representative SIZE-FIDELITY evidence demonstrates the default `(1,3,10)` fails existing scientific qualification criteria;
5. a nondefault integration case exposes a hidden authority/schema coupling requiring a material public/persistence redesign not covered here;
6. repository policy requires supported public compatibility that cannot be provided by a quarantined deprecated adapter;
7. current configuration resolution architecture cannot support an explicit schema-generation boundary without creating a second scientific authority.

A default-tuple failure does not reopen the flexible architecture. Preserve unrelated completed stages/evidence and reopen only the default decision.

## 7. Lossless implementation obligations

Each obligation below is mandatory. Suggested realizations are adaptable; required consequences are not.

### O1 - Canonical flexible target-size policy

Protected concern: eliminate fixed numeric epoch authority without changing unrelated target-size science.

Required end state:

- `TargetSizeStudyPolicy.fidelity_epochs` accepts exactly three strictly increasing positive integers and defaults `(1,3,10)`;
- semantic survivor/finalist field names replace `epoch3_survivor_limit` / `epoch10_finalist_count` on current surfaces;
- fixed candidate universe, minimum qualifiers, funnel counts, seed aggregation, and equivalence behavior are preserved;
- `n3 <= n` is validated only where tuple and TRAIN2 budget are both available.

Owning/affected surface: `target_size_study.py`, policy assembly, package exports, policy tests.

Forbidden: hard-coding the new default as the only accepted tuple; giving target-size policy its own full-horizon field.

Acceptance evidence:

- focused tuple validation/property tests;
- source/absence check for fixed `_STAGE_FOR_EPOCH`-style current authority;
- default and `(2,5,12)` policy tests;
- cross-policy n3<=n tests.

Stage: S1.

### O2 - Campaign configuration v2 and historical normalization

Protected concern: one current authoring authority and truthful legacy semantics.

Required end state:

- campaign config v2 exposes explicit `fidelity_epochs` and existing `training.max_num_epochs`;
- generated `init` writes both;
- normalization/validation happens centrally before policy consumers;
- v1/schema-less TRAIN2 campaigns reconstruct historical fixed `(3,10,30)`;
- legacy-looking decorative epoch keys are never treated as historical semantic authorities;
- mixed generations, incomplete/ambiguous migration, and non-historical legacy-looking values fail closed.

Owning/affected surface: `_campaign_cli_core.py` config loader/resolver/template, config tests, `campaign.toml.example` after executable gate.

Acceptance evidence:

- v2 happy path `(1,3,10)/30` and `(2,5,12)/40`;
- v1/schema-less historical path;
- v1 with historical decorative keys;
- v1 with non-historical decorative values -> clear rejection;
- mixed v1/new tuple -> reject;
- v2 old-key/mixed-key -> reject;
- resolved policy snapshot/digest contains effective tuple and full horizon.

Stage: S1.

### O3 - Semantic target-size state and schemas

Protected concern: configured values must not be encoded into current state/API/persistence terminology.

Required end state:

- awaiting states, stage fields, plan fields, attach methods, evidence/failure validation, and serializers are semantic;
- stage boundaries are derived from the active policy;
- current serializers use new schema identifiers;
- current writers never emit old numeric keys;
- immediate prior authoritative target-size restart state is migrated exactly after validating old digest, or explicitly rejected if a specific record cannot be reconstructed.

Owning/affected surface: `target_size_study.py`, package exports, campaign store/restart readers, serializer tests.

Required migration consequence: old fixed records map numeric fields/stage `final` to semantic fields/`final_screen` while retaining historical `(3,10,30)` and authenticated planned horizon. Conversion happens after old-schema validation, not by feeding old payloads into new constructors and ignoring fields.

Acceptance evidence:

- semantic round-trip tests;
- old-schema fixture digest validation then migration;
- corrupted old digest rejection;
- off-boundary evidence rejection under configurable tuples;
- source/absence scan proving numeric-stage names are absent from current writers/API except isolated legacy adapter/tests.

Stage: S2.

### O4 - Exact full-horizon TRAIN2 continuation

Protected concern: screening must not alter optimization trajectory.

Required end state:

- coarse/short/final-screen limits are n1/n2/n3 on a full-n `Train2RuntimePlan`;
- survivors resume prior checkpoint/optimizer/RNG/EMA state;
- planned epochs/structures, budget/LR/training identities remain full n;
- eliminated candidates are not scheduled later;
- off-boundary or wrong-horizon checkpoints cannot satisfy a screen.

Owning/affected surface: `train2_runtime.py` only where necessary, campaign execution/orchestration, target-size evidence construction, restart tests.

Required consequence: reuse existing continuation checks rather than duplicate them. Any edit to TRAIN2 runtime itself must be justified by a concrete gap.

Acceptance evidence:

- `(2,5,12)/40` pause/resume at 2 -> 5 -> 12;
- no-restart-from-zero assertions;
- restart after each exact boundary reconstructs same next action;
- interruption before boundary cannot rank;
- changing n from 40 changes schedule/training identity and rejects old checkpoint;
- runtime-plan limit changes do not falsely change the underlying full schedule identity.

Stage: S3.

### O5 - Semantic campaign orchestration and selection freeze

Protected concern: duplicate numeric branches can reintroduce n3/n coupling even if core policy is flexible.

Required end state:

- train/evaluate/select orchestration consumes semantic current stage geometry;
- production after selected state runs to canonical n;
- continuation authorization follows stage start/continuation semantics, not `>3`;
- EVAL2 attaches outcomes by semantic stage;
- parent ancestry is previous semantic boundary;
- selected target size is printed/frozen only after final-screen reduction.

Owning/affected surface: `_campaign_cli_core.py`, campaign execution tasks/status, CLI orchestration tests.

Acceptance evidence:

- default and nondefault orchestration tests;
- production target n != n3 test;
- q=3 funnel case;
- terminal insufficient-qualified/insufficient-comparable/nonconverged outcomes remain behaviorally unchanged;
- target-only screen authorization preserved.

Stage: S3.

### O6 - Retire the coarse-after-warmup hard heuristic

Protected concern: accepted default must be structurally legal without altering TRAIN2 schedule science.

Required end state:

- valid `(1,3,10)/30` config with default warm-up fraction 0.05 reaches target-size planning;
- no target-size validator requires n1 to be after warm-up;
- TRAIN2 warm-up/adaptation/refinement policy is unchanged;
- scientific adequacy remains deferred to SIZE-FIDELITY qualification.

Owning/affected surface: `_target_size_study_policy` or its replacement, config/assembly tests.

Acceptance evidence:

- regression reproducing current rejection and proving it is removed;
- LR policy/digest unchanged for otherwise identical n=30 protocol;
- no code changes that retime warm-up solely for fidelity.

Stage: S1/S3, closed before nondefault integration.

### O7 - SIZE-FIDELITY full-reference redesign

Protected concern: early screens must be qualified against the actual full training outcome.

Required end state:

- execution plan distinguishes n2, n3, and reference n;
- required checkpoint union includes n exactly once;
- reference finalist/winner/order derives only from full-role epoch n metrics;
- candidate assessment/report uses `reference_*` semantics;
- existing recall/equivalence thresholds remain hard as currently defined;
- final-screen result is checked for consistency with full-horizon reference selection semantics;
- n3==n reuses one physical checkpoint without losing role distinction;
- new schema generations isolate old v2/v1 artifact semantics.

Owning/affected surface: `size_fidelity.py`, exports, Stage-11 graph/spec after executable gate, tests.

Acceptance evidence:

- synthetic `(2,5,12)/40` metrics where epoch-12 ordering differs from epoch-40 ordering, proving epoch 40 is reference;
- default `(1,3,10)/30` with valid coarse candidate grid such as `(1,2)`;
- n3==n case `(1,3,30)/30` with one physical epoch-30 checkpoint;
- reference-horizon identity mismatch rejection;
- recall/equivalence thresholds unchanged unless an independently approved scientific redesign occurs.

Stage: S4.

### O8 - PERF-P2R geometry and workload accounting

Protected concern: performance control plane must not become a second scientific epoch authority and must preserve true continuation savings.

Required end state:

- stage `final` becomes `final_screen` where it means the third screen;
- active screen boundaries come from target-size policy; full horizon comes from TRAIN2 budget;
- stage plan carries target and schedule horizon independently;
- production target is n;
- primary structure-epoch accounting uses incremental deltas and target-size weighting;
- exhaustive/reference comparator uses full n;
- obsolete `short_training_epochs` / `final_training_epochs` current fields are removed where they mean active screen boundaries;
- affected schemas are bumped or invalidated explicitly.

Owning/affected surface: `perf_p2r.py`, consumers, benchmark/control-plane tests.

Acceptance evidence for `(2,5,12)/40`:

```text
coarse       target=2  schedule=40
short        target=5  schedule=40
final_screen target=12 schedule=40
production   target=40 schedule=40
```

and exact workload assertions:

```text
W_screen = 2*sum_A(N_i) + 3*sum_S(N_i) + 7*sum_F(N_i)
W_reference = 40*sum_A(N_i)
```

plus candidate-epoch diagnostic if retained. Verify no duplicate materialization/inference is introduced solely by role separation.

Stage: S5.

### O9 - Progress/status semantics

Protected concern: user-visible progress must not overstate authorized work.

Required end state:

- progress data carries semantic stage target and full schedule horizon separately;
- screening phase denominator uses n1/n2/n3;
- schedule horizon remains n for LR/training context;
- production denominator is n;
- ETA for bounded work is stage-bounded;
- persisted status, snapshots, and restart/status consumers use semantic stage names.

Owning/affected surface: `_MaceTrainingProgressProbe`, its producers/consumers, campaign status sidecars, CLI tests.

Acceptance evidence:

- `(2,5,12)/40` structured progress at representative epochs;
- default `(1,3,10)/30` progress;
- production `/40` or `/30` behavior;
- stable-interface assertions preferred over punctuation snapshots.

Stage: S3.

### O10 - Identity, cache, and reuse closure

Protected concern: changed tuple/horizon must invalidate only semantically dependent state and must never permit unsafe cross-schedule reuse.

Required end state:

- tuple perturbations alter target-size-dependent identities;
- n perturbation alters schedule/training/checkpoint and cross-dependent plan identities;
- stage execution limit alone does not destroy legitimate same-schedule continuation;
- old fixed evidence cannot masquerade as new-default evidence;
- derived caches either migrate with explicit semantic identity or rebuild.

Owning/affected surface: target-size digests, training/evidence digests, campaign store/reuse paths, SIZE-FIDELITY/PERF-P2R plan digests, tests.

Acceptance evidence:

- change n1 only, n2 only, n3 only, n only;
- stale cache rejection;
- cross-horizon checkpoint rejection;
- same inputs/tuple/horizon digest stability;
- presentation-only changes do not invalidate scientific artifacts.

Stage: S2-S5 with final consolidation in S6.

### O11 - Public API and legacy containment

Protected concern: compatibility code must not recreate dual current authorities.

Required end state:

- `mdstats.training_data` and top-level `mdstats` export semantic current names;
- numeric-stage names are absent from current public API unless a real compatibility obligation is found;
- any retained compatibility wrapper is explicitly deprecated/quarantined and cannot write current schemas/configuration;
- old terms remain only in migration fixtures/adapters or historical documentation.

Owning/affected surface: `mdstats/training_data/__init__.py`, `mdstats/__init__.py`, API tests, legacy adapter.

Acceptance evidence:

- import/export tests for semantic names;
- negative/absence assertions for numeric current exports;
- compatibility warning/delegation tests if wrappers are required.

Stage: S2/S6.

### O12 - Current documentation and publication reconciliation

Protected concern: permanent current documentation must describe the accepted present implementation, not the pre-change runtime or a future plan.

Required end state after executable integration passes:

- current architecture/specs/guides/config examples describe `(n1,n2,n3)` plus independent n;
- default `(1,3,10)/30` is clearly a default, not an architectural constant;
- SIZE-FIDELITY reference endpoint is n;
- PERF-P2R geometry and structure-epoch cost are correct;
- reporter examples distinguish stage endpoint and schedule horizon;
- generated architecture/PDF/manifest descendants are regenerated from canonical sources;
- historical archives remain truthful.

Acceptance evidence:

- doc authority/leakage search;
- generated-source equality/hash checks;
- changed local-link checks;
- render/parse visual QA for changed tracked PDFs;
- documentation tests aligned with the implemented runtime.

Stage: S7, only after S6 executable integration passes.

## 8. Initially expected affected surface

Implementation must begin with a full local search and expand this list based on actual callers/serializers. At the reviewed branch, known affected surfaces include:

Executable/runtime:

- `mdstats/training_data/target_size_study.py`
- `mdstats/training_data/size_fidelity.py`
- `mdstats/training_data/perf_p2r.py`
- `mdstats/training_data/_campaign_cli_core.py`
- `mdstats/training_data/campaign_execution.py` where continuation/status semantics require it
- `mdstats/training_data/train2_runtime.py` only if an actual gap exists; prefer reuse
- `mdstats/training_data/train2_policy.py` only for shared policy integration, not schedule retiming
- `mdstats/training_data/protocol.py` only as needed for canonical cross-policy validation/reuse of existing budget consistency
- campaign store/persistence readers/writers touched by target-size state
- `mdstats/training_data/__init__.py`
- `mdstats/__init__.py`
- `mdstats/_version.py` and release/version metadata according to repository policy

Configuration/user-facing:

- `campaign.toml.example`
- generated `init` template in campaign CLI
- CLI/status/progress payloads and snapshots

Tests:

- target-size policy/state/ranking/failure tests
- TRAIN2 runtime/pause/restart/checkpoint identity tests
- campaign config/protocol tests
- campaign train/evaluate/select orchestration tests
- SIZE-FIDELITY1 tests
- PERF-P2R tests
- cache/reuse/digest tests
- package export/API tests
- documentation specification tests
- new integrated default/nondefault flexible-fidelity tests

Current docs after executable gate:

- README current overview
- canonical MLFF architecture chapter sources and generated architecture artifacts
- MLFF training-data dependency graph
- Stage-11 dependency graph
- current target-size/SIZE-FIDELITY/PERF-P2R/progress specifications
- current campaign user guide and FINAL-GPU1 runbooks/specs
- direct indexes/navigation for these documents

Historical/archive documents are inspection context, not rewrite targets.

## 9. Material implementation stages and dual closure

### S0 - Intake, characterization, and authority inventory

Actions:

1. Record exact starting commit.
2. Search source/tests/config/current docs for fixed epoch/state/schema names and semantic equivalents.
3. Enumerate every current serializer/deserializer and campaign-store record involving target-size policy/state/evidence.
4. Locate all consumers of `TargetSizeStudyPolicy`, outcome constants, `next_training_epoch`, attach functions, PERF-P2R plans, SIZE-FIDELITY plans, and progress fields.
5. Classify persisted artifacts as authoritative restart/user state vs rebuildable derived state.
6. Run existing affected regression subsets before edits; add characterization tests for migration/restart gaps where necessary.

Semantic/conformance closure:

- one complete task-local affected surface exists;
- no unknown major state/persistence owner remains;
- pre-change fixed behavior needed for migration is characterized.

Functional closure:

- affected baseline tests execute and pass, or pre-existing unrelated/unavailable failures are explicitly attributed;
- unavailable dependencies are not counted as passes.

### S1 - Policy and configuration authority

Assigned obligations: O1, O2, O6.

Actions:

- implement flexible policy fields/default/validation;
- implement campaign config v2 normalization and historical v1 path;
- validate n3<=n at canonical assembly;
- retire coarse-after-warmup hard guard without changing LR schedule;
- update focused config/policy tests.

Semantic closure: exactly one tuple authority and one full-horizon authority; no hidden warm-up eligibility rule remains.

Functional closure before S2: policy/config/protocol affected regressions pass, including default `(1,3,10)/30` and nondefault `(2,5,12)/40` assembly.

### S2 - Semantic target-size state, persistence, and API

Assigned obligations: O3, O10 target-size portion, O11.

Actions:

- refactor current state/outcome/fields/methods/exports to semantic names;
- derive boundaries from policy;
- bump current schemas;
- implement exact old fixed-generation target-size restart migration or explicit justified rejection where reconstruction is impossible;
- update API/serialization tests.

Semantic closure: current writers/exports have no numeric-stage authority; legacy path is isolated and validates old digest first.

Functional closure before S3: complete target-size state/ranking/failure/persistence/API affected regressions pass.

### S3 - TRAIN2 continuation, campaign orchestration, and progress

Assigned obligations: O4, O5, O9.

Actions:

- thread semantic stage geometry through train/evaluate/select;
- use full n for production and schedule context;
- reuse execution limits/continuation for screening;
- replace literal epoch branching and `>3` continuation logic;
- update progress/status structure and selected-size freeze message.

Semantic closure: stage work authorization and full schedule identity are distinct; no orchestration path derives n from n3.

Functional closure before S4:

- TRAIN2 pause/restart affected regressions;
- campaign orchestration regressions;
- exact-boundary/parent-ancestry tests;
- progress/status tests;
- `(2,5,12)/40` continuation through 2,5,12 using bounded fixtures.

### S4 - SIZE-FIDELITY1 full-reference semantics

Assigned obligation: O7 plus relevant O10 identity.

Actions:

- refactor execution plan/assessment/report/reference naming;
- add independent reference n;
- update default coarse calibration candidates to a tuple valid for `(1,3,10)` without weakening scientific thresholds;
- implement n3==n role dedup;
- version/rebuild/migrate affected artifacts as classified.

Semantic closure: all reference finalist/winner decisions are full-n derived; no current `eventual` term means n3.

Functional closure before S5: complete SIZE-FIDELITY1 affected regression including n3-vs-n disagreement and n3==n cases passes.

### S5 - PERF-P2R and performance identity

Assigned obligation: O8 plus relevant O10 identity.

Actions:

- remove duplicate active screen-boundary ownership;
- add schedule horizon to stage plans;
- rename final screen semantically;
- update structure-epoch exposure/reference math and schemas;
- verify reuse/no-duplicate-work behavior with lightweight fixtures.

Semantic closure: target-size policy owns n1/n2/n3; TRAIN2 owns n; PERF-P2R only projects them.

Functional closure before S6: complete PERF-P2R affected regression with `(2,5,12)/40` stage geometry and weighted incremental cost passes.

### S6 - Assembled executable integration and compatibility closure

Assigned obligations: O1-O11 assembled.

Mandatory integration cases through real product boundaries:

#### Case A - default

```text
fidelity=(1,3,10)
n=30
warmup_end_fraction=0.05
```

#### Case B - anti-hardcoding

```text
fidelity=(2,5,12)
n=40
```

#### Case C - role coincidence

```text
fidelity=(1,3,30)
n=30
```

Each applicable case must exercise configuration resolution -> policy assembly -> target-size stage planning -> evidence admission -> survivor transitions -> freeze -> production horizon -> status/progress, using bounded/synthetic training/evidence where necessary.

Case B must prove at least:

1. all initial candidates authorize only 0->2;
2. only coarse survivors authorize 2->5;
3. only short finalists authorize 5->12;
4. exact 2/5/12 evidence is required;
5. off-boundary evidence is rejected;
6. all screen checkpoints authenticate a 40-epoch schedule;
7. target size freezes after 12;
8. production target is 40, not 12;
9. screening progress denominators are 2/5/12;
10. schedule horizon 40 is separately available;
11. production progress/planning is 40;
12. tuple perturbation invalidates target-size-dependent identity;
13. n perturbation invalidates TRAIN2/cross-dependent identity;
14. n=40 checkpoint is rejected under incompatible full horizon;
15. eliminated candidates receive no later work;
16. structure-epoch exposure uses incremental deltas.

Case C proves final-screen/reference role coincidence without duplicate physical evidence.

Semantic closure:

- reconcile every O1-O11 requirement against assembled source;
- perform structural/absence scan for numeric current-path state/API/schema/config ownership;
- inspect for duplicated epoch authority, stale fallback paths, and unnecessary compatibility layers.

Functional closure before documentation:

- default/nondefault/coincident integrations pass;
- complete assembled executable affected regression passes;
- repository-required lint/type/static checks for touched Python surface pass;
- if shared orchestration impact cannot be bounded, run broader available test suite;
- no newly affected/unexecuted required functional check remains except explicitly external production qualification.

### S7 - Documentation and publication reconciliation

Assigned obligation: O12.

Precondition: S6 executable flexible contract accepted.

Actions:

- rewrite current normative/user documentation from fixed runtime to implemented flexible runtime;
- update current config examples and generated init examples;
- advance architecture/version metadata according to repository conventions;
- regenerate tracked derived Markdown/PDF/manifest artifacts from canonical sources;
- preserve historical archives.

Semantic closure: current docs and executable behavior agree; future-workplan caveats are removed from current product docs because Part 2 is now implemented.

Mechanical closure: doc tests, link checks, source-chain checks, PDF render/parse/visual QA, and legacy-leak classification pass.

### S8 - Final accepted-contract reconciliation and final affected-surface acceptance

Actions:

1. Reconcile every O1-O12 obligation against the final assembled candidate.
2. Re-derive affected behavioral surface from final diff/callers/consumers; do not rely only on S0 list.
3. Account for every affected path with executed regression/integration evidence or an explicit blocking unavailable check.
4. Rerun complete affected-surface regression after all executable edits that could invalidate earlier evidence.
5. Run final default/nondefault/coincident integrations on the same candidate.
6. Run repository-required checks and broader suite if impact is not confidently bounded.
7. Re-run structural legacy leakage search and classify every remaining hit.
8. Verify current documentation/configuration/persistence/API all describe one authority model.
9. Inspect for product-complexity regression: duplicate state, duplicate epoch authority, stale adapters, obsolete numeric wrappers, repeated inference/materialization, or redundant migration machinery.
10. Update package/release/version metadata required by repository policy.

Final acceptance requires both:

- semantic/conformance closure: every accepted obligation is satisfied or legitimately reconciled without changing frozen intent; and
- functional closure: all required affected regression/integration/repository checks pass.

Green tests do not compensate for an omitted obligation. Structural conformance does not substitute for executable testing.

## 10. Mandatory focused and regression acceptance matrix

### Tuple validation

Must reject:

```text
(0,3,10)
(1,1,10)
(3,1,10)
(1,10,3)
wrong-length tuples
non-integer/invalid parsed values
(1,3,31) with n=30
```

Must accept:

```text
(1,3,10) with n=30
(2,5,12) with n=40
(1,3,30) with n=30
```

### Funnel and scientific ordering preservation

Test at q=3, q=4, and a larger admitted set where practical:

- coarse survivor cap remains `min(q,4)`;
- short finalist count remains 2 when comparison permits;
- final screen selects one target size using unchanged equivalence-aware ordering;
- paired seeds and arithmetic mean aggregation remain intact;
- typed candidate-specific numerical failures preserve existing comparison/terminal semantics;
- target-size selection remains target-only.

### Exact-boundary and continuation

- evidence stage completed epoch must equal configured stage boundary;
- evidence planned horizon/schedule identity must equal canonical n;
- short parent is exact coarse checkpoint/optimizer/RNG ancestry;
- final-screen parent is exact short ancestry;
- interrupted segment cannot be ranked early;
- no later work for eliminated candidate;
- restart at every screen boundary reproduces next action.

### Configuration generations

- v2 current config explicit tuple + n;
- generated `init` v2 contains tuple;
- v1/schema-less historical fixed semantics;
- historical decorative 3/10/30 keys handled explicitly without granting them authority;
- non-historical decorative values rejected;
- mixed old/new generation rejected;
- full horizon recovered from training authority, never legacy final-screen-looking field.

### Persistence

For every materially changed authoritative current artifact:

- new schema/version differs from old;
- current round trip is stable;
- old supported fixture validates old digest before migration;
- converted semantic identity preserves historical meaning;
- corrupt/ambiguous old input fails closed;
- current writer emits no numeric-stage keys.

Rebuildable derived artifacts may instead prove clear old-generation rejection plus deterministic rebuild.

### SIZE-FIDELITY

- reference metrics are epoch n even when n3 differs;
- n3==n deduplicates physical checkpoint;
- reference finalist/winner retention uses existing thresholds/equivalence policy;
- coarse candidate grid constraints relative to n1/n2;
- monitor metrics continue to derive from authenticated full-role prediction authority rather than repeated inference;
- rank correlation remains diagnostic, not a replacement for hard recall.

### PERF-P2R

- exact semantic stage geometry for default and nondefault;
- weighted structure-epoch delta formula;
- exhaustive/reference denominator uses n;
- production cost/horizon separate from screening;
- no active n2/n3 duplicate authority in parameter grid.

### Progress/status

- stage endpoint denominator and schedule horizon separated;
- ETA uses bounded authorized work;
- restart/status serialization semantic;
- selected size printed after final screen;
- production messages use n.

### Identity/cache

- stable identical inputs;
- perturb each n1/n2/n3 independently;
- perturb n independently;
- cross-horizon checkpoint rejection;
- stale old fixed evidence rejection under new default;
- no invalidation from presentation-only change.

### Public API/absence

- semantic exports import correctly;
- current public surface does not expose numeric-stage ownership unless explicitly deprecated by supported contract;
- current source/config/schema writers contain no unquarantined `awaiting_epoch_3`, `epoch3_*`, `epoch10_*`, `epoch30_*`, `final_training_epochs` meaning n3, or hard-coded `planned_epochs == 30` target-size logic.

## 11. Legacy leakage inventory

Before editing and again at final closure, search at least for:

```text
3/10/30
3 -> 10 -> 30
(3, 10, 30)
epoch3_
epoch10_
epoch30_
awaiting_epoch_3
awaiting_epoch_10
awaiting_epoch_30
STAGE_FINAL
final_training_epochs
short_training_epochs
planned_final_epoch
planned_epochs == 30
planned_epochs != 30
execution_epoch_limit > 3
/30
```

Also inspect semantic equivalents that do not use these exact strings.

Allowed final hits:

- quarantined old-schema adapters/parsers;
- migration fixtures/tests intentionally exercising historical artifacts;
- historical/archive documentation/workplans;
- unrelated legitimate literal 30 uses.

Not allowed:

- current runtime state/API/config/schema ownership;
- current reporter assumptions;
- current production horizon inferred from third screen;
- current SIZE-FIDELITY reference inferred from third screen;
- current PERF-P2R active boundary ownership duplicated outside target-size policy.

## 12. Scientific default qualification boundary

Functional implementation must support default `(1,3,10)/30` without changing the LR schedule or scientific thresholds.

During implementation, run all lightweight representative SIZE-FIDELITY evidence available in the repository/environment. Do not claim production scientific qualification from synthetic/CPU-only tests.

If representative empirical evidence demonstrates epoch 1 fails existing required recall/equivalence criteria:

1. stop only default-dependent acceptance;
2. preserve the flexible architecture and all valid implementation stages;
3. do not weaken the scientific gate;
4. report the evidence and reopen the default tuple decision for the smallest justified adjustment.

If representative production evidence is unavailable, functional closure may proceed with default architecture tests while FINAL-GPU1 empirical qualification remains explicitly deferred.

## 13. Production qualification disposition

Full production/data-heavy GPU qualification is not part of routine Part 2 implementation acceptance and must not be used as a substitute for regression/integration.

Required now:

- deterministic/focused unit tests;
- stage-local affected regressions after each executable stage;
- bounded continuation/restart tests;
- default/nondefault/coincident integration tests;
- lightweight scientific/reference and performance accounting checks;
- final affected-surface regression/integration;
- documentation publication verification.

Deferred:

- long real-data training qualification;
- machine-specific wall-time/RAM/VRAM/utilization characterization;
- final CUDA/CuEquivariance scientific qualification under FINAL-GPU1.

## 14. Final handoff checklist

The implementer must not declare completion until all applicable items are explicitly reconciled:

- [ ] Work started from the recorded current branch head and S0 affected surface was completed.
- [ ] Campaign config explicitly adopted the new generation and v1 historical semantics remain truthful.
- [ ] `TargetSizeStudyPolicy` supports exactly three configurable boundaries, default `(1,3,10)`.
- [ ] Cross-policy invariant `0 < n1 < n2 < n3 <= n` is enforced.
- [ ] TRAIN2 remains the sole full-horizon owner and optimizer consistency enforcement is reused.
- [ ] Coarse-after-warmup hard eligibility rule is removed; LR schedule is not retimed.
- [ ] Current target-size states/fields/methods/exports are semantic.
- [ ] Current serializers have new semantic schemas and current writers emit no numeric-stage keys.
- [ ] Authoritative old fixed restart state is migrated exactly or explicitly rejected where impossible; no silent new-default substitution.
- [ ] Survivors continue exact prior checkpoints on one full-n trajectory.
- [ ] Eliminated candidates receive no later work.
- [ ] Exact configured boundaries are the only ranking checkpoints.
- [ ] Final-screen freeze is at n3 and production training target is n.
- [ ] SIZE-FIDELITY reference endpoint is n, not n3.
- [ ] Default SIZE-FIDELITY coarse candidate grid is valid for `(1,3,10)` and hard criteria are unchanged.
- [ ] n3==n role coincidence deduplicates physical work.
- [ ] PERF-P2R projects tuple+n without owning duplicate active endpoints.
- [ ] PERF-P2R structure-epoch cost uses incremental target-size-weighted deltas.
- [ ] Reporter/status separates stage endpoint from schedule horizon.
- [ ] Tuple and n changes invalidate exactly the dependent identities; cross-horizon checkpoint reuse is rejected.
- [ ] Default `(1,3,10)/30` integration passes.
- [ ] Nondefault `(2,5,12)/40` integration passes all anti-hardcoding assertions.
- [ ] Coincident `(1,3,30)/30` integration passes without duplicate physical reference evidence.
- [ ] q=3 funnel and existing terminal/scientific failure behavior remain covered.
- [ ] Public current API has no unquarantined numeric-stage ownership.
- [ ] Current documentation/specs/guides/config examples are reconciled only after executable acceptance.
- [ ] Generated documentation artifacts are regenerated/verified from canonical sources.
- [ ] Final accepted-contract reconciliation found no omitted obligation or duplicate authority.
- [ ] Final affected-surface regression, integration, and repository-required checks pass.
- [ ] Every remaining legacy-pattern hit is classified as legacy/history/unrelated.
- [ ] Heavy GPU production qualification remains deferred and is not claimed.

## 15. Risks and bounded redesign triggers

### Scientific default risk

Epoch 1 may be too noisy to satisfy full-horizon finalist/winner fidelity. This can invalidate the default, not the configurable architecture.

### Legacy-state ambiguity

Historical artifacts may omit context needed for exact migration. Authoritative state fails closed if meaning cannot be reconstructed; derived state may be rebuilt. Do not guess.

### Shared campaign CLI blast radius

`_campaign_cli_core.py` is a large shared orchestration surface. Limit edits to resolved config, stage geometry, continuation authorization, evidence attachment, progress/status, and directly affected consumers. Final affected-surface re-derivation must account for any broader propagation.

### Public API blast radius

Numeric outcome/attach symbols are exported at both training-data and top-level package surfaces. Removal can affect consumers beyond local tests. Retain deprecated wrappers only if actual repository compatibility policy requires them; otherwise prefer one clean semantic API.

### Performance regression

Role separation can accidentally duplicate checkpoint materialization or inference at n3/n, especially when n3==n. Reuse authenticated evidence where semantic identity matches and verify structure-epoch/inference counts with bounded tests.

### Documentation lifecycle risk

Part 1 intentionally left current docs fixed. Do not update them early during a partially implemented runtime. Publish flexible current docs only after S6 executable integration acceptance, then re-run final acceptance on the assembled implementation+documentation candidate.

## 16. Handoff closure statement

This Protocol 5.5.0 revision preserves the accepted flexible-fidelity product design while making the implementation consequences explicit and testable. The implementer is not expected to rediscover the architecture. Local realization and newly discovered necessary consequences may proceed when they preserve the protected concerns and frozen decisions above. Any need to change a frozen scientific, ownership, persistence, or compatibility decision requires evidence and a bounded design reopen.
