# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — G12A replay-transport/integration repair is **IMPLEMENTED; independent re-review pending** on 2026-09-14 against `HEAD` `2a93c331` plus the working-tree diff recorded under G12A below. Integration & Verification Review R3 (NO-PASS, G13 excluded) findings 1-6 are addressed at their existing owners with no D1/D2/D3 change. G0/G1/G1A remain CLOSED/PASS; the narrow G1B ancestry repair still awaits independent re-review. G13 pilot/three-fold CV, independent re-review, and closeout remain open.  
**Current authority:** accepted D1/D2 in `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md`; current D3 in `docs/arch_manuals/mlff_training_data_architecture.md` plus canonical chapters; current D4 restored-P5 handoff in `docs/specs/training_data/mlff_post_selection_p5_spec.md`, with G1B narrowly reopened as specified below  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  
**Pre-code closure evidence:** `audits/MLFF_POST_SELECTION_RESTORATION_G1_G1A_G1B_CLOSURE_2026-09-14.md`

## 1. Disposition

The upstream D1/D2 Serious Challenge is resolved for this restoration branch. The repaired D1/D2 pair passed independent falsification at `f310b4c15c6b0465b34013d329847abdb208bae2`, and the stakeholder authorized progression.

G1 authority/API/evidence census and G1A D3 reconciliation remain closed PASS. Independent implementation Review found no D1/D2 Serious Challenge and no D3 architecture contradiction: the accepted D3 dependency direction remains acyclic (`role plan -> fitted P5 preparation -> materialization -> evidence`). G1B remains narrowly reopened because the normative D4 P5 specification had stated that the CV/final plan itself binds `foundation fitted-preparation ancestry`, which reverses that dependency and would create a plan/preparation cycle if implemented literally. The repair is specification/test only and is not authority for a compensating runtime graph.

Stages A–D were implemented on code candidate `521bc932ec9b52cc769db32a2561fa4cd1b8eba8`, followed by the narrow G1B repair and R2 evidence. The assembled implementation remains substantially aligned with the restored method: current foundation loss/exposure, common-monitor routing, selected-head residual E0/transfer, currentness, and M3-free publication all route through existing owners rather than parallel machinery.

Integration & Verification Review R3 then reconstructed the actual assembled behavior across replay preparation, MACE loading/loss realization, restart/currentness, public configuration, current specifications, user guidance, and the P5->P7 handoff. It found no D1/D2 or D3 Serious Challenge, but it found one new executable D4 conformance defect: replay materializers copy source-frame metadata and can preserve `config_energy_weight`, `config_forces_weight`, and `config_stress_weight` values that native `UniversalLoss` actually consumes. That permits an external replay ExtXYZ to silently change the accepted fixed P5 functional while `PostSelectionMethodIdentity` still claims the frozen method. This is a local D4 transport/currentness defect under coherent D1-D3 and is repaired by G12A below.

R3 also found a stale structural test oracle that forbids the generic token `restart_latest` even though authenticated P5 continuation legitimately uses it, and current specification/documentation drift around `[objective]` ownership, generated CV defaults/public command surface, M3-free P7 publication ancestry, and restored-P5 MACE atomic-number realization. Those surfaces must be reconciled with the already-accepted runtime semantics; product code must not be regressed to satisfy stale prose/tests.

The repair remains deliberately reductive: remove wrong/retired semantics and rewire existing owners. Do not create a custom loss, second replay-weight layer, second replay parser, second sampler, second E0 solver, shadow trainer, parallel method/protocol registry, second currentness system, compatibility wrapper that merely preserves an obsolete current path, or a reverse plan->preparation binding added only to satisfy contradictory wording.

## 2. Frozen restored foundation-P5 method

For `naive_fine_tuning` and `multihead_replay`:

```text
P5 method authority              PostSelectionMethodIdentity family only
loss family                      native MACE UniversalLoss
huber_delta numeric value        0.01
energy Huber threshold           0.01 eV/atom
force base Huber threshold       0.01 eV/Angstrom
stress Huber threshold           0.01 eV/Angstrom^3
global E:F:S coefficients        1:10:1
general config_weight in P5      neutral transport only; exactly 1.0 where emitted
local property weights           binary label-availability masks only, exactly 0.0/1.0
target:replay training scalar    none
atomic-reference mode            foundation_residual
E0 transfer rule                 composition-level null-space identifiability
replay-label default             TRUE_DFT
pre-shuffle two-head layout      replay/pt_head || target
implicit target duplication      forbidden
force_mh_ft_lr                   true for multihead replay
foundation P5 drop_last          true for naive and multihead accepted paths
foundation P5 execution          qualified single-process path only
checkpoint target monitor        one protected campaign-common exact 256-frame M_mon
common-monitor plan lineage      same immutable monitor-record digest in every CV/final plan
monitor shortfall                P5 infeasible; no shrink/fallback/resample
CV fold default                  3; explicit K>=2 override allowed
held-out CV evidence             unavailable to fit/checkpoint choice
final single-best seed evidence  frozen representative metric record on common M_mon
P3 M3 role in P5                 none; P3 evidence/downstream probe only
replay degradation criterion     unchanged
production-scale GPU qualification deferred to final release
```

This work does not change P3 target-size screening loss/exposure, P5 scratch loss semantics, target-size membership/order/reducer semantics, replay geometry split, target/replay acceptance thresholds, optimizer-seed population, M3 P3 evidence identity, or final-release GPU qualification policy.

A successful assembled restoration proves the assembled restored method. It does not by itself identify which individual repaired semantic caused replay-retention improvement.

## 3. Governing invariants

### 3.1 Evidence roles

- P1/P2/P3 and frozen `T_N` / `T_selected` remain upstream and are preserved unless a direct dependency is demonstrated.
- The common target monitor is development/model-control evidence, supplies no gradients, and is not held-out CV evidence.
- Held-out CV evidence cannot affect target membership, fitted E0/preprocessing, stopping, checkpoint choice, monitor construction, or final seed ranking.
- Monitor/held-out geometry/composition may be inspected only to establish E0 transfer consumers; labels do not enter the fit.
- Final production starts fresh from the accepted foundation family and uses the same P5 method validated by CV.
- One common target monitor is reused across every selected size, fold, CV seed, and final-production seed/run.
- Sharing a monitor correlates checkpoint/model-control decisions; held-out folds remain the CV acceptance evidence.

### 3.2 Protected statistical separation

Exact frame disjointness is necessary but insufficient. Incompatible evidence roles also respect the canonical P1 split-exclusion taxonomy:

```text
correlation_unit
geometry_duplicate
protected_event
replica_lineage
structural_realization
```

The selected-only `SelectedRelationProjection` cannot alone prove target-versus-common-monitor separation because it excludes frames outside `T_selected`.

Required order:

```text
label-usable neutral OUTER_MONITOR
  -> exact D2 common-monitor sampling
  -> immutable M_mon record
  -> P1 cross-role protected-relation check against every governed T_N
  -> CV/final plan admission
```

A collision fails. No relation-prefilter, deletion, replacement, or resampling is permitted.

### 3.3 Replay

- TRUE_DFT is the canonical training default on the single-source interface.
- Foundation pseudo-label replay is explicit opt-in.
- Pseudo-label training requires independent TRUE_DFT replay monitoring.
- Changing label mode over the same prepared source/split does not change replay geometry membership.
- Replay retention is an admissibility constraint, not target-size ranking credit.
- Existing target-force and replay-degradation thresholds are not relaxed.
- Any still-current legacy split-file route must have unambiguous explicit label semantics; ambiguous omission fails closed.
- Source/user replay weighting metadata is not a foundation-P5 scientific authority. A current P5 replay transport must not inherit a non-neutral `config_weight` or non-binary property weights from the input frame.
- For every replay view consumed by current foundation P5, the effective transport semantics at the MACE loader boundary are `config_weight=1.0` and exact binary energy/force/stress availability masks. The masks are derived from the labels actually rendered into that view, not copied from source metadata.
- The rule applies equally to single-source TRUE_DFT, single-source foundation-pseudolabel, and every still-supported legacy split-file P5 route. Historical replay artifacts may remain readable as history, but a noncanonical replay transport cannot authorize current foundation-P5 execution.

### 3.4 Objective/weight taxonomy

Keep distinct:

1. global energy/force/stress coefficients;
2. general `ConfigurationWeightPolicy` / `config_weight` where a method consumes it;
3. local property-availability weights, which are exact binary masks in current foundation P5;
4. target/replay **training-head scalar** weights, retired for current P5; and
5. checkpoint/adaptive-stop `target_score_weight` / `replay_score_weight`, which remain current.

Foundation UniversalLoss does not consume general `config_weight` as an active P5 scientific layer, but native `UniversalLoss` does consume the per-property energy/force/stress weights. Therefore non-binary inherited property weights are not harmless transport metadata: they are a method violation. The fixed foundation-P5 objective is independent of P3 `[objective]` / `[weighting]` overrides.

### 3.5 Identity/currentness economy

- `PostSelectionMethodIdentity` is sole current P5 method identity.
- `TrainingProtocolIdentity` may remain for separately current non-P5 consumers/history but cannot authorize restored P5.
- `TargetSizeCommonTrainingPolicy` remains a P3 owner; current foundation P5 does not bind its whole digest.
- Exact monitor membership, fold membership, fitted E0 result, transfer result, checkpoints, and metrics are descendants, not pre-work method fields.
- P5-only generation changes do not blanket-stale unchanged P3 evidence.
- True P5 method changes invalidate dependent P5 evidence.
- A replay-view representation/currentness cutover must invalidate only derived replay transports whose canonical weight/mask semantics changed. It must preserve still-valid replay source, geometry split, true-label cache, foundation-prediction cache, and qualification evidence when their owning identities are unchanged; no expensive pseudo-label reinference is authorized merely to rewrite transport metadata.

## 4. Accepted numerical foundation-adaptation consequences

### 4.1 UniversalLoss

For pinned `mace-torch==0.3.16`, foundation P5 resolves native `UniversalLoss` with one numeric `huber_delta=0.01` and E:F:S `1:10:1`.

Accepted numerical behavior includes:

- per-atom energy Huber threshold `0.01 eV/atom`;
- force conditional-Huber base threshold `0.01 eV/Angstrom` with accepted reference-force-norm regimes;
- stress Huber threshold `0.01 eV/Angstrom^3` over all nine stored Cartesian entries;
- binary local property-availability masks;
- general `config_weight` not consumed as a foundation-P5 loss layer; and
- native reduction/distributed behavior preserved or upstream D2 reopened.

The three dimensional thresholds are meanings of one numeric parameter, not three live user knobs.

### 4.2 Stochastic exposure

For multihead replay:

```text
replay / pt_head dataset || target dataset -> native combined dataset
shuffle                                  -> enabled under accepted seed
target/replay training-head balance      -> none
intentional duplication                  -> none
real_pt_data_ratio_threshold             -> 0.0
force_mh_ft_lr                           -> true
combined drop_last                       -> true
```

The pre-shuffle replay-first layout is method-bearing under fixed seed. Do not add a reorder wrapper.

Naive foundation fine-tuning likewise uses the accepted shuffled target-only `drop_last=true` geometry. P3 target-size screening retains complete-batch `drop_last=false`.

Foundation P5 is single-process only until distributed equivalence is separately accepted.

### 4.3 Foundation-residual E0 and transfer

The existing atomic-reference fitter remains the sole solver.

- CV residual fit uses only fold gradient-training labels.
- final residual fit uses complete exact `T_selected`.
- exact selected foundation checkpoint/head is bound.
- foundation predictions/reference E0 inputs come from that same selected head.
- target and replay/pretraining head E0 mappings remain head-local where required.
- no new absent-element prior/anchor is introduced.

Let `C` be the authorized fit count matrix and `N_free` the unanchored null space after accepted identity-bound anchors. For every governed target composition vector `c` consumed by training, common-monitor checkpoint control, or held-out evaluation:

```text
c^T v = 0  for every v in N_free
```

Individual elemental coefficients need not be unique when the consumed composition-weighted correction is unique. Minimum-norm/zero fallbacks do not create identifiability.

Current fitted preparation binds required composition identity, numerical-rank tolerance/evidence, accepted anchor identity, and transfer result.

## 5. Common target monitor

Current P5 monitor policy:

```text
parent              neutral label-usable OUTER_MONITOR
requested size      256
realized size       256
seed                161803
membership          exact deterministic D2 algorithm
shortfall           infeasible
relation conflict   infeasible
```

The monitor record is immutable and shared. All sibling CV/final plans bind the same record digest.

Current MLCV target-light may equal this exact monitor membership; MLCV does not own a second target checkpoint sampler. Replay monitoring/training diagnostics remain separately owned.

## 6. Final publication

M3 is removed from P5 checkpoint/final-plan/final-seed-ranking/currentness ancestry.

Each final seed freezes an admissible representative plus its already-authenticated target metric record on common `M_mon`.

- `all_qualified_final_seeds`: publish all already-admissible required representatives.
- `single_best_final_seed`: reuse accepted target-only representative ordering over the frozen common-monitor metric records, including deterministic uncertainty/materiality/secondary/maturity/tie semantics where applicable.

Single-best performs no second target evaluation and no M3 evaluation. Ordering seed material derives deterministically from final-plan/publication ancestry, not completion order.

If accepted ordering cannot operate on common-monitor records without semantic change, reopen D2/D3; do not replace it with raw scalar minimum-RMSE sorting.

## 7. Historical Applicability Set

```yaml
pem_basis:
  accepted_project_state: 1b6b6f83918d31c4b27a0e60d7bc047ef58b6067
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-001
    disposition: APPLICABLE
    reason: MACE realization can drift from recorded method/foundation-head identity when model-affecting construction is duplicated or falls through defaults.
  - id: FF-002
    disposition: APPLICABLE
    reason: Old stress/fold-local/from-scratch-E0/target-first/M3-publication TRAIN2 state must not become continuation authority after cutover.
  - id: SP-001
    disposition: APPLICABLE
    reason: Remove duplicated loss/monitor/protocol/weight ownership and return responsibility to real owners.
  - id: SP-002
    disposition: APPLICABLE
    reason: Retired fields, incompatible fit modes, historical schemas, ambiguous replay defaults, stale run state, and stale derived replay transports must fail closed rather than be silently reinterpreted.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve independent immutable P1/P2/P3/selection and replay source/split/cache evidence rather than rebuilding or globally invalidating it.
  - id: SP-004
    disposition: APPLICABLE
    reason: Real pinned-MACE and real monitor/currentness/foundation-head/publication paths are required; helper-only proof is insufficient.
```

Refresh HAS if governing accepted PEM or branch authority materially advances before closeout.

## 8. G0-G1B gate state

### G0 — D1/D2 adjudication — **CLOSED / PASS**

Accepted restoration semantics are frozen in current branch D1/D2 and independently reviewed/ratified.

### G1 — authority/API/evidence census — **CLOSED / PASS**

Closure evidence: `audits/MLFF_POST_SELECTION_RESTORATION_G1_G1A_G1B_CLOSURE_2026-09-14.md`.

The census classifies current P5 owners, preserved P3 owners, historical DATA8/`TrainingProtocolIdentity` surfaces, monitor/MLCV owners, final M3 references, configuration/public surfaces, and currentness cutover responsibilities. Each semantic has one current owner and compatibility disposition.

### G1A — D3 architecture reconciliation — **CLOSED / PASS**

Canonical D3 reconciled:

```text
docs/arch_manuals/mlff_training_data_architecture.md
docs/arch_manuals/mlff_training_data/30_statistical_design.md
docs/arch_manuals/mlff_training_data/40_training_evaluation.md
docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
```

The top-level manual is itself canonical D3 authority alongside the chapters; it is not a generated aggregate.

### G1B — D4 handoff freeze — **REOPENED / REPAIR APPLIED; RE-REVIEW PENDING**

Normative restored-P5 handoff: `docs/specs/training_data/mlff_post_selection_p5_spec.md`.

Related current specs/index reconciled:

```text
docs/specs/training_data/mlff_online_monitor_spec.md
docs/specs/training_data/mlff_data_stage_plan_spec.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/specs/training_data/README.md
```

Independent implementation Review found one internal contract contradiction in the normative P5 spec. Section 1 correctly freezes the acyclic chain `role plan -> PostSelectionFittedPreparation`, matching accepted D3. Sections 11 and 13 nevertheless listed `foundation fitted-preparation ancestry where applicable` as a parent that the CV/final plan itself SHALL bind. A plan cannot both own and descend from its fitted preparation without a cycle.

**Required narrow repair:**

1. Preserve the accepted D3/workplan direction: role plan first; fitted preparation binds its owning CV/final run-plan ancestry; materialization/run evidence then bind the fitted-preparation digest.
2. Remove `foundation fitted-preparation ancestry where applicable` from the CV-plan/run-plan and final-plan parent lists in D4 sections 11 and 13. Do not add a reverse runtime edge, deferred placeholder, wrapper, second plan schema, or other machinery to make the contradictory text executable.
3. State explicitly in the fitted-preparation/materialization contract that current foundation fitted preparation binds the owning role/run plan plus common-monitor/required-composition transfer ancestry, and that downstream materialization/run evidence binds the resulting preparation.
4. Add/retain a real-owner D4 test that falsifies reverse ancestry: current CV/final plans must not carry a fitted-preparation parent, while a current foundation fitted preparation must authenticate its owning plan/run ancestry.
5. Perform a narrow independent G1B re-review and freeze the corrected D4 handoff. Reopen D3 only if evidence shows the accepted acyclic dependency graph cannot represent the required lineage; current Review found no such evidence.

No D1/D2 method change and no product-runtime modification is authorized by this G1B repair.

## 9. Implementation staging

### Stage A — method/exposure/config/identity cutover

Implement G2, G3, G3A, G8, and method/exposure portions of G10.

Preserve/regression-protect existing G9 checkpoint/adaptive-stop score/admissibility constants here, but do **not** claim current target-monitor routing until the exact common monitor exists.

Run focused tests and affected regression before Stage B.

### G2 — mode-specific native UniversalLoss realization

- remove only foundation-adaptation UniversalLoss->stress mutation;
- preserve source qualification, restart/CUDA/precision/runtime repairs and P3 complete-batch patch;
- do not globally flip P3/scratch loss-family semantics;
- resolve foundation P5 loss by authenticated mode at existing MACE seam;
- verify native loss class/parameters after MACE mutation regions;
- bind `huber_delta=0.01`, E:F:S `1:10:1`, conditional-force and nine-entry stress semantics;
- preserve binary masks and neutral general `config_weight` transport;
- verify `force_mh_ft_lr=true`, `real_pt_data_ratio_threshold=0.0`.

**Acceptance:** real parser/runtime evidence shows accepted foundation UniversalLoss while unaffected P3/scratch controls remain unchanged.

### G3 — retire training-head scalar weighting

- remove current config/identity/plan/materialization/runtime application of target/replay training-head scalar weights;
- keep target/replay checkpoint/adaptive-stop score weights;
- old current-schema head-scalar fields fail closed or remain historical only under explicit reader.

### G3A — decouple foundation P5 from P3 objective/configuration weighting

- remove whole `TargetSizeCommonTrainingPolicy` digest from current P5 identity/preparation;
- add/project only real shared component owners;
- do not fit/bind nontrivial configuration weights for foundation P5;
- preserve P3 `[objective]` / `[weighting]` and P5 scratch behavior.

### G8 — restore accepted replay/exposure/default semantics

- canonical replay omission -> TRUE_DFT;
- ambiguous legacy omission -> fail closed;
- replay/`pt_head` first, then target, before shuffle;
- no implicit target duplication;
- `force_mh_ft_lr=true`;
- naive and multihead foundation `drop_last=true`;
- distributed foundation P5 rejected;
- P3 complete-batch unchanged.

### Stage B — foundation residual E0/transfer implementation

Implement the code path and manufactured falsification for G4, but do not authenticate a current foundation preparation/run yet.

### G4 — selected-head foundation-residual E0 + transfer

Implement/test:

- mode resolution (`FOUNDATION_RESIDUAL` for foundation modes; scratch unchanged);
- exact selected foundation-head prediction/reference-E0 acquisition;
- existing residual-fit owner wiring;
- rank/null-space/tolerance/anchor evidence;
- `c^T v = 0` transfer validator;
- authorized training/consumer composition extraction;
- wrong-head, label-leakage, rank-deficient, absent-element, and minimum-norm falsification.

Stage B manufactured monitor composition sets are test oracles only. G4 is not current-run complete until Stage C binds actual `M_mon` composition ancestry and reruns transfer.

### Stage C — common monitor + CV/final topology

Implement G5, G6, G7, target-monitor-routing portion of G9, and common-monitor completion of G4 as one topology stage.

### G5 — exact common `M_mon`

- construct once from neutral label-usable `OUTER_MONITOR`;
- exact 256 or infeasible;
- use accepted D2 quota/marker/order/systematic selection;
- persist immutable record;
- after sampling, prove P1 cross-role separation against every governed `T_N`;
- relation conflict fails without resampling;
- validate label usability.

### G6 — bind common monitor into every CV/final plan and remove M3 P5 ancestry

- every sibling CV/final plan binds same monitor-record digest;
- selected fold contains train/eval/purge only;
- current MLCV target-light == common monitor; no second target sampler;
- final plan removes `m3_evaluation_size` / `m3_membership_digest` and M3 target-monitor routing;
- final publication consumes frozen common-monitor representative records;
- single-best reuses accepted target-only ordering semantics; no new target/M3 evaluation.

### G7 — CV default/current schema cutover

- one current fold-default resolver -> 3;
- explicit `K>=2` override;
- remove current `checkpoint_monitor_components_per_fold` and equivalent fold target-monitor fields;
- historical schemas readable only as history where supported;
- all required fold/seed acceptance unchanged.

### G9 — route current checkpoint/adaptive-stop target evidence to `M_mon`

Stage A preserves score/admissibility semantics. Stage C changes only the target evidence parent:

```text
old fold/final/M3 target parent -> exact authenticated common M_mon
```

No temporary monitor owner or wrapper is permitted.

### G4 Stage-C completion

After exact common monitor exists:

1. derive its required composition classes from geometry/count evidence without using monitor labels for fitting;
2. bind monitor record/composition-set ancestry into fold/final fitted preparation;
3. combine with other governed training/evaluation consumer compositions;
4. rerun transfer feasibility; and
5. refuse current materialization/run admission if transfer fails.

## 10. Stage D — assembled currentness/runtime/spec/document integration

Complete G10-G12 after Stages A-C. G12A below is a post-review repair gate added by Integration & Verification Review R3. Later documentation may reconcile examples/generated views/history, but cannot change the frozen G1B method-bearing contract without reopening G1B/upstream owner as applicable.

### G10 — method identity, runtime evidence, restart/currentness cutover

Runtime evidence binds, at minimum, all material fields frozen by `mlff_post_selection_p5_spec.md`, including:

```text
training role/mode
P5 method identity / P5 preparation-policy digest
foundation checkpoint + selected head
resolved native loss/class/parameters and dimensional interpretations
binary property-mask policy / E:F:S
atomic-reference fit mode + membership/input/result
rank/null-space/tolerance/anchor + required composition-set + transfer result
target/replay memberships/counts
ordered replay-first pre-shuffle layout
shuffle/sampler seed/policy
single-process identity
batch/drop_last/batches-per-epoch
force_mh_ft_lr / no-duplication evidence
LR / EMA / precision / backend
common monitor parent/policy/record/membership exact count 256
P1 separation evidence
replay monitor lineage
fold train/eval/purge membership
method/CV/final/run-plan digests
final publication common-monitor metric lineage
```

Advance generations at the narrowest real owner. Old stress/fold-local/M3-P5/from-scratch-foundation/target-first/missing-transfer state fails currentness before restart/execution/publication. Preserve independent upstream P1/P2/P3/T_selected evidence.

### G11 — counterfactual falsification matrix

At minimum reject:

1. identity says UniversalLoss but runtime resolves stress;
2. global loss repair changes P3 or P5 scratch;
3. wrong UniversalLoss delta/E:F:S/conditional-force/stress reduction;
4. separate live property delta knobs;
5. foundation P5 still fits/binds nontrivial configuration weight;
6. P3 objective/weight edit stales foundation P5 without real shared change;
7. retired training-head scalar fields remain current;
8. score/adaptive-stop weights are deleted with training-head weights;
9. canonical replay omission not TRUE_DFT;
10. ambiguous legacy omission silently pseudo;
11. label mode changes replay geometry split;
12. foundation mode resolves from-scratch E0;
13. residual fit lacks exact selected-head predictions/reference E0;
14. monitor/held-out labels leak into fit;
15. wrong selected foundation head used;
16. transferable rank-deficient composition is falsely rejected;
17. non-transferable composition falsely accepted;
18. absent required element passes without accepted anchor;
19. minimum-norm/zero fallback treated as identification;
20. exact monitor shortfall continues;
21. relation-conflicting monitor member is filtered/replaced/resampled;
22. monitor deterministic selection differs from D2;
23. monitor record identity depends on one selected size;
24. selected-only relation projection misses cross-role leakage;
25. sibling CV/final plans bind different monitor records;
26. current MLCV independently samples target checkpoint evidence;
27. common monitor copied into selected-fold membership;
28. target labels unusable/incompatible but accepted;
29. default K resolves to five or another value;
30. legacy DATA5 role-budget/CV semantics become current;
31. implicit target duplication occurs;
32. `force_mh_ft_lr` false/absent or LR/EMA mutated;
33. naive/multihead foundation exposure geometry differs;
34. distributed foundation P5 admitted;
35. replay/target order reversed under same seed;
36. P3 complete-batch behavior changes;
37. numerically material precision/backend change lacks identity change;
38. incompatible old checkpoint/preparation resumes as current;
39. broad old `TrainingProtocolIdentity` CV evidence authorizes current final production;
40. P5 method/preparation still binds whole P3 policy;
41. final plan/publication binds/evaluates M3 to choose seed;
42. downstream M3 probe forces M3 back into P5 identity;
43. execution-only field incorrectly changes scientific method identity;
44. P5-only generation blanket-stales unchanged P3 evidence;
45. true method field fails to invalidate dependent P5 evidence;
46. Stage A claims common-monitor routing before authenticated monitor exists;
47. manufactured monitor composition authorizes current foundation transfer;
48. shared scratch/foundation preparation silently ignores forbidden cross-mode fields;
49. old weight-bearing foundation preparation deserializes and becomes current;
50. single-best publication becomes raw scalar-RMSE sort;
51. final publication reruns target or M3 evaluation;
52. D3 source regresses target checkpoint monitor to fold-local membership;
53. Stage D changes a frozen method-bearing G1B contract without reopening authority;
54. replay source `config_weight != 1` survives into current foundation-P5 training as an active scientific weight or is represented as method authority;
55. non-binary source `config_energy_weight` survives into a current TRUE_DFT or pseudolabel replay view and changes native UniversalLoss;
56. non-binary source `config_forces_weight` survives into a current TRUE_DFT or pseudolabel replay view and changes native UniversalLoss;
57. non-binary source `config_stress_weight` survives into a current TRUE_DFT or pseudolabel replay view and changes native UniversalLoss;
58. a replay frame without rendered stress reaches MACE with a positive stress mask, or a frame with valid rendered stress reaches MACE with a zero stress mask;
59. the supported legacy split-file P5 route bypasses the same neutral/binary replay-weight semantics;
60. an old v1 replay transport/receipt produced before canonical weight-mask semantics is reused as current after the repair;
61. the replay-transport repair invalidates an unchanged expensive foundation-prediction cache or forces foundation pseudo-label reinference merely to rewrite ExtXYZ transport metadata;
62. the stale P5-F oracle is satisfied by deleting/disguising legitimate authenticated P5 `--restart_latest` continuation rather than narrowing the oracle to actual screening-owner reachability;
63. generated config/user documentation still claims `[objective]` changes foundation P5 UniversalLoss coefficients;
64. current campaign CLI specification still advertises the wrong command surface or stale CV/init defaults;
65. current P7 specification still makes target-size `M3` a P5 final-publication/currentness parent; and
66. broad DATA8 atomic-number union prose is allowed to redefine restored foundation-P5 checkpoint reconstruction despite the scoped P5 owner and real assembled replay-only-species path.

Each is rejected by a real owner, corrected at the owning representation, or documented inapplicable with evidence. Word-presence alone is insufficient where runtime semantics are the claim.

### G12 — real-owner assembled qualification

Exercise the real path:

```text
campaign config
 -> PostSelectionMethodIdentity / P5 preparation-policy projection
 -> foundation/head residual inputs
 -> transfer owner
 -> exact neutral common-monitor record
 -> P1 cross-role separation evidence
 -> sibling CV plans binding same monitor
 -> target/replay materialization
 -> parser-facing MACE config
 -> existing source-qualified MACE seam
 -> native MACE UniversalLoss for foundation modes
 -> selected-head E0 realization
 -> replay-first combined loader or naive target-only loader
 -> single-process optimizer update
 -> persistence/restart evidence
 -> adaptive stop/checkpoint on M_mon
 -> held-out EVAL2 for CV only
 -> fresh final representative on same M_mon
 -> final publication with no M3 P5 ancestry
```

Also run unaffected controls:

```text
P3 target-size remains weighted + complete-batch
P5 scratch remains on separately accepted weighted method
retained downstream M3 probe resolves from P3 owner only
```

Mocks may exist only below/outside the semantic owner being proved. Static source checks alone cannot close runtime realization claims.

Production-scale GPU qualification remains deferred to final release.

### Independent implementation Review R1 — 2026-09-14 — **NO-PASS**

Reviewed assembled code candidate `521bc932ec9b52cc769db32a2561fa4cd1b8eba8` plus derived-document head `f71c5b9af34454940814445fd2e50b97265526d1` against this workplan, current D1/D2, current D3, the G1/G1A/G1B closure record, current P5 D4 specification, changed implementation/test surfaces, and applicable HAS entries.

**Serious Challenge:** none to D1/D2 or D3. The accepted D3 dependency graph is coherent and directly supports the implemented plan->preparation direction.

**Blocking findings:**

1. **D4/G1B ancestry contradiction.** `mlff_post_selection_p5_spec.md` section 1 says `role plan -> PostSelectionFittedPreparation`, but sections 11 and 13 require the CV/final plan to bind fitted-preparation ancestry. G1B is reopened with the narrow repair above. Product code must not be changed to manufacture this cycle.
2. **Candidate-bound G11/G12 evidence was not yet reusable closure evidence.** The workplan's prior status text referred to an uncommitted working-tree run and a 223-test-file regression, while the reviewed implementation was commit `521bc932...` with a subsequent derived-doc commit. Exact-candidate evidence was rerun later and is recorded below.
3. **G13 remains intentionally open.** Run the bounded scientific pilot, record the prescribed baseline/restored metrics and exact method/monitor/E0/exposure identities, then run the required three-fold affected qualification. If correctly restored TRUE_DFT replay still shows material forgetting comparable to the prior failure regime, reopen D1/D2 rather than layering another D4 compensation.

**Nonblocking observations:**

- Current code inspection found one P5 method family, one current common-monitor construction owner, one existing atomic-reference solver reused for foundation residual E0, existing EVAL2 ordering reused for final single-best publication, and fail-closed historical/currentness boundaries; no second product owner is justified by this Review.
- The common monitor is deterministically re-resolved per selected context but binds identical content identity/separation ancestry; this is not a semantic blocker while sibling-plan digest equality remains enforced. Do not add a new monitor cache/registry merely to make object construction singular.
- Historical scheduler/resource regression tests removed only where their tested helper was itself retired; real scheduler/process/restart tests and memory-backoff/zero-admission owner tests remain. Do not restore obsolete helper-specific oracles merely for line-count parity.
- Serena/Semgrep-specific execution was unavailable in the remote review environment; structural/symbol/file inspection was performed through the repository connector. This limits analyzer-specific completeness claims but does not relax any qualification gate.

### Candidate-bound post-review evidence — 2026-09-14

The narrow G1B repair was applied without adding a runtime owner, wrapper, schema, or reverse dependency. The tested repaired implementation/spec/test state was `HEAD` `10d09f4d192b5788f67f75e0a84bd139c8802b00` plus the four-file implementation/spec/test working-tree diff, whose SHA-256 was `e56a2eafd8adc43ca695e18ec1163960e6b4deab099113087f2ff64e0d1fef05` (the workplan note itself excluded). No product-runtime source file changed in that narrow repair.

Focused and affected evidence was run with the user's requested 16-worker xdist allocation (`pytest -n 16 --dist=load`) wherever the owner suite supported it:

- G1B real-owner ancestry test plus existing P5 method-owner/Hypothesis coverage: `24 passed`.
- CV/identity/publication owners (`P5B`, `P5C`, `P5H`): `33 passed`.
- P5-G assembled lifecycle, including CV/final plan and materialization ancestry: `3 passed`.
- Affected implementation matrix covering downstream integration, executable configuration, control plane, P5 TRAIN2/EVAL2/CuEq/restart/recovery, P7, replay ownership, target-size cutovers, P5 guards, and P6 compatibility: `554 passed, 17 CUDA-specific skipped`.
- MACE execution and replay/MACE P5 recovery owners: `28 passed`.
- Direct P5 materialization/CV/memory/context owners: `61 passed`.

The real-owner assembled MACE qualification suite passed serially as `5 passed, 1 CUDA-specific skipped`; its isolated 16-worker attempt hit an existing xdist worker/import race involving partially initialized `mdstats.training_data` symbols and did not produce a valid concurrent result. The serial result is retained because the affected concurrent suites passed and no product-runtime import change was authorized for the G1B repair. The existing source-qualification owner also passed against the supplied MACE/ASE archives: `mace-torch==0.3.16`, source compile/top-level import/`mace.cli.run_train` import all passed, no required or optional dependencies were missing, and the qualified MACE source-tree digest was `0a59f3411759db89f7dc37aeb635078ef2d02781ba0b64e74e36ed1e2d646c1f`. The pinned runtime check resolved native `mace.modules.loss.UniversalLoss` with the expected native signature.

The broader exploratory `tests/test_mlff_*.py` 16-worker sweep is not acceptance evidence (`2669 passed, 34 skipped, 126` pre-existing release/documentation/version-drift failures). It also exposed the stale P5-F source-absence oracle because that oracle forbids the legitimate generic `restart_latest` token rather than the actual screening-continuation owner.

Serena and Semgrep execution remained unavailable because their configured analyzer/cache locations were read-only; bounded source/AST checks passed instead. Hypothesis executed as part of the owner suite. G13 was assessed but not closed: real LTA inputs exist in external read-only locations, while the available prior campaign predates this repair, lacks current-candidate identity/writable run evidence, and rejected its checkpoints. No current-candidate bounded pilot, required three-fold CV, or production-scale GPU qualification was claimed.

### Independent Integration & Verification Review R3 — 2026-09-14 — **NO-PASS; G13 EXCLUDED**

Review subject: assembled branch head `c5fc4e09a2e83c879f07d0ca3e3c611975f78d32`, current D1/D2, canonical D3, current P5/P7/DATA8/CLI D4 specifications, replay preparation/materialization, MACE dependency seam, P5 currentness/restart/publication, real-owner tests, generated config/example, and user guidance.

**Serious Challenge:** none to D1/D2 or D3. The frozen scientific method and architecture remain coherent. The defect below is a D4 replay-transport/currentness violation of already-accepted binary-mask semantics.

**Blocking executable finding:**

1. `replay.py` single-source TRUE_DFT rendering and legacy true-label rematerialization, and `replay_pseudolabel.py` pseudo rendering, copy the source `Atoms` frame and replace labels but do not remove/canonicalize inherited `config_weight`, `config_energy_weight`, `config_forces_weight`, or `config_stress_weight`. Native pinned-MACE `UniversalLoss` ignores general `config_weight` but consumes the three per-property weights. An external replay file can therefore inject non-binary scientific weighting into restored foundation P5 while the method identity still claims the accepted fixed functional. Existing replay artifact/view identity authenticates bytes/labels/membership but does not make those inherited values canonical method masks. This is a genuine D4 blocker.

**Additional integration defects/drifts:**

2. `tests/test_mlff_target_size_p5f_structure.py` forbids the literal `restart_latest` across post-selection source even though authenticated P5 continuation legitimately uses `--restart_latest`. The oracle must be narrowed to screening-continuation ownership; product restart must not be removed or renamed merely to pass the test.
3. `docs/guides/mlff_campaign_cli_user_guide.md`, generated `_config_template` comments, and `campaign.toml.example` still contain prose saying `[objective]` applies to post-selection CV/final production alike. Foundation P5 is actually fixed native UniversalLoss 1:10:1 and deliberately ignores P3/P5-scratch `[objective]` / `[weighting]` overrides.
4. `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md` still advertises a stale public command surface and toy generated CV defaults (`K=2`, seed/partition/horizon values) that do not match the actual current parser/config generator. Runtime/default implementation is the accepted side; the spec must be reconciled.
5. `docs/specs/training_data/mlff_p7_post_production_qualification_spec.md` still says the P5 final publication decision binds frozen M3 membership. Current D3 and P5 runtime intentionally remove M3 from P5 plan/publication/currentness ancestry; `AuthenticatedFinalPublication` now binds common-monitor lineage instead. Repair the P7 prose, not the runtime.
6. `docs/specs/training_data/mlff_data8_mace_artifacts_spec.md` contains a broad top-level `atomic_numbers` union statement that can be misread as restored foundation-P5 authority. Restored P5 is explicitly scoped out of the broad DATA8 protocol graph; its real assembled replay-only-species path reconstructs the model from the authenticated foundation checkpoint. Scope the DATA8 statement to the DATA8 consumers it actually owns and state the restored-P5 exception/route without inventing another model-construction owner.

**Verified nonblockers:** common-monitor ownership/routing, fold topology, selected-head residual-E0/transfer, replay-first exposure, no implicit target duplication, single-process foundation execution, EVAL2 final ordering, M3-free product code, P5->P7 read-only publication intake, and replay-only foundation species reconstruction remain aligned. Do not add new registries/wrappers/caches or reintroduce M3/fold-local semantics to address this review.

### G12A — replay-transport and integration reconciliation — **IMPLEMENTED; INDEPENDENT RE-REVIEW PENDING**

G12A is a D4 repair/impact-closure gate under unchanged D1-D3. It must be completed before G13 or final independent implementation Review can close this workplan.

#### G12A.1 — canonicalize foundation-P5 replay transport at existing owners

Required end state at the MACE loader boundary for every current foundation-P5 replay frame:

```text
config_weight         = 1.0
config_energy_weight  = 1.0 iff the rendered current view carries a valid energy label, else 0.0
config_forces_weight  = 1.0 iff the rendered current view carries valid force labels, else 0.0
config_stress_weight  = 1.0 iff the rendered current view carries a valid stress label, else 0.0
```

The three property values are method masks, not user/source weights. They must be exact binary values. No source `config_*_weight` value, no source `config_weight`, no P3 `[weighting]`, and no replay-head scalar may survive as an active foundation-P5 replay weighting layer.

Implement through existing replay owners:

- `mdstats/training_data/replay.py::_render_source_true_label_frame`: before publishing a TRUE_DFT single-source replay frame, remove/overwrite inherited general/property weight metadata and write the canonical neutral/binary fields from the labels actually rendered.
- `mdstats/training_data/replay_pseudolabel.py::_render_pseudo_frame`: perform the same canonicalization after replacing source truth with foundation pseudo labels. Stress mask follows the actual pseudo stress payload; absence remains absence with mask zero and must not fabricate a stress label.
- `mdstats/training_data/replay.py::materialize_true_label_replay_split`: the supported legacy true-label rematerialization path must apply the same rule when it copies split geometry and reattaches independent true labels.
- Any supported legacy split-file route that is still consumed directly rather than rematerialized must establish the same effective semantics before P5 launch. Do **not** rewrite user input in place. Reuse the existing replay inspection/materialization boundary: either route through the already-owned canonical replay transport or fail closed when explicit/direct-file metadata would cause MACE-resolved weights to differ from the required neutral/binary masks. Do not add a P5-only parser/copy/weight wrapper.
- Apply the rule to replay training and replay monitor transports wherever MACE consumes those transport fields. Monitor/evaluation semantics may not be silently reweighted by inherited source metadata either.

Do not change `UniversalLoss`, `post_selection_mace_run_configuration`, global E:F:S, MACE source patching, target exporter weighting, P3 weighted paths, or P5 scratch to compensate for replay transport contamination.

#### G12A.2 — replay-view currentness/schema cutover without expensive scientific recomputation

The renderer change is numerically material for current foundation P5, so stale derived views cannot be accepted under an unchanged logical identity.

- Advance the current single-source TRUE_DFT replay-view schema/receipt identity and foundation-pseudolabel replay-view schema/receipt identity, or an equivalently explicit currentness token, so pre-repair views cannot pass current reuse merely because their old receipt and bytes still self-authenticate.
- Bind the canonical neutral/binary weight-mask transport policy into the current logical view identity/contract. Update `transport_fields`/equivalent representation metadata so the persisted contract reflects the fields MACE actually consumes.
- Historical v1 views may remain readable as history if needed, but they cannot authorize current repaired foundation-P5 execution.
- Preserve unchanged expensive parents: replay source identity, replay geometry split, true-label cache, foundation-prediction cache, pseudo qualification, and source index remain reusable when their own identities still validate. A view-only repair must rematerialize the cheap ExtXYZ view from those parents; it must not rerun foundation prediction or scientifically resplit the corpus.
- Existing current alias publication must converge on the repaired view in the ordinary `prepare` owner. Do not create a second current alias namespace or a P5-side cache registry.

For legacy external split artifacts, their byte/content identity may remain the historical artifact identity. Current P5 admission must additionally establish the repaired transport invariant at the existing resolver/inspection boundary; a historically readable noncanonical artifact is not a current P5 authorization.

#### G12A.3 — repair the stale restart oracle, not restart behavior

In `tests/test_mlff_target_size_p5f_structure.py`:

- remove generic `restart_latest` from the forbidden-marker test for screening-continuation ownership;
- continue to forbid the actual P3 continuation owners/symbols/import edges (`resolve_target_size_candidate_for_resume`, `TargetSizeContinuationRequest`, `continuation_request_from_boundary`, `build_target_size_candidate_trajectory`, `promote_target_size_boundary_snapshot`, or equivalent current screening owners);
- strengthen the structural test with AST/import/call ownership where practical so a renamed screening function cannot pass a pure word blacklist;
- retain/add a positive real-owner restart/currentness test proving P5's own authenticated MACE continuation is allowed only when run plan/materialization/runtime evidence remain current.

No product runtime rename, wrapper, suppression, or removal is authorized solely to satisfy the old oracle.

#### G12A.4 — reconcile current specification/config/guide truth

Update only the owning/stale surfaces; do not change correct runtime to match stale prose.

1. `docs/specs/training_data/mlff_post_selection_p5_spec.md`
   - state explicitly that current foundation-P5 replay transports carry neutral `config_weight=1.0` and binary property-availability masks derived from rendered labels;
   - state that source replay weight metadata has no current P5 scientific authority;
   - describe stale-view/currentness failure at the appropriate D4 boundary;
   - do not alter G1B method-bearing plan/preparation ancestry.
2. `docs/guides/mlff_campaign_cli_user_guide.md`
   - remove the claim that `[objective]` controls foundation-P5 CV/final production;
   - keep `[objective]` scoped to P3 and the separately accepted P5-scratch path;
   - make early generated CV examples match the actual current generator/defaults (`fold_count=3`, `partition_seed=104729`, CV seed `[0]`, default CV horizon 30, and current acceptance/default production values as emitted by the generator).
3. `mdstats/training_data/_campaign_cli_core.py::_config_template` comments and `campaign.toml.example`
   - correct `[objective]` comments to the same ownership scope;
   - do not change numerical defaults that are already correct merely for prose alignment.
4. `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md`
   - list the real current public parser surface, including the downstream `qualification {status,run,activate-locked}` family while preserving its separate post-production lifecycle meaning;
   - replace stale toy generated-CV values with the actual current initialized values;
   - preserve the distinction between training lifecycle and downstream qualification.
5. `docs/specs/training_data/mlff_p7_post_production_qualification_spec.md`
   - remove frozen-M3 ancestry from the P5 final-publication decision description/currentness identity;
   - describe the actual current `common_monitor_record_digest`/accepted P5 publication lineage;
   - retain M3 only where P7 independently uses a separately authorized bounded P3/deployment-parity cohort; do not make that downstream use a P5 publication parent.
6. `docs/specs/training_data/mlff_data8_mace_artifacts_spec.md`
   - scope the top-level target/replay atomic-number-union statement to the broad DATA8 consumers it actually owns;
   - explicitly note that restored foundation P5 is governed by the P5 D4 handoff and reconstructs the executable model from the authenticated foundation checkpoint/head, so a replay-only species need not appear in the target-side P5 top-level config literal to survive model reconstruction;
   - do not create a second P5 model-construction policy.
7. Reinspect the canonical D3 chapters after these corrections. No D3 mutation is expected. If a real D3 contradiction is found, stop and reopen G1A rather than editing D3 merely for wording consistency.
8. Regenerate/check any tracked derived documentation only after canonical Markdown/source comments are reconciled.

#### G12A.5 — required focused and real-owner falsification

Add/adjust evidence so the previous blind spot cannot recur:

1. **Adversarial TRUE_DFT single-source replay:** construct scientifically identical source frames carrying deliberately contaminated `config_weight` and non-binary `config_energy_weight` / `config_forces_weight` / `config_stress_weight`; materialize through the real replay owner and assert current view fields are exactly neutral/binary.
2. **Adversarial pseudolabel replay:** use the real pseudo-view renderer/cache path with contaminated source metadata and assert the rendered pseudo train view has the same canonical masks; prove source truth/weights do not leak into the pseudo view.
3. **Stress availability:** include at least one frame with valid stress and one without stress; assert masks `1` and `0` respectively and prove no missing stress is fabricated merely to make the mask positive.
4. **Legacy split route:** drive the real still-supported legacy replay resolution with contaminated explicit weight metadata. It must either produce the same canonical derived transport through the existing owner or fail closed before MACE; silent direct consumption is a failure.
5. **Pinned MACE numerical oracle:** feed the repaired replay materialization through the real MACE parser/loader and native `UniversalLoss`; assert the batch property weights are exact masks and that varying only irrelevant source weight metadata cannot change the realized loss for otherwise identical rendered labels/geometries.
6. **Currentness:** seed a pre-repair v1 replay-view receipt/bytes and prove current `prepare` does not reuse it as the repaired view. Then prove rematerialization reuses unchanged replay split/true-label/prediction/qualification parents and performs zero new pseudo-label foundation inference.
7. **Restart:** prove the narrowed P5-F structural oracle rejects actual screening-continuation dependencies while legitimate P5 `--restart_latest` recovery still passes real run-plan/materialization/runtime authentication.
8. **P5->P7:** exercise current final publication intake and assert P7 binds common-monitor publication lineage with no P5 M3 parent.
9. **Public/config truth:** test the generated `init` configuration/defaults and, where repository practice supports it, static/current-doc assertions sufficient to prevent reintroduction of the false `[objective]`/CV-default claims.
10. **Unaffected controls:** rerun P3 weighted complete-batch behavior, P5 scratch weighted behavior, target-side foundation-P5 neutral/binary export, replay-only-species assembled reconstruction, and real source-qualified `mace-torch==0.3.16` UniversalLoss realization.

The real semantic owners must execute. A helper that simply rewrites expected values to match production cannot close this gate.

#### G12A.6 — affected regression and evidence applicability

After all executable G12A edits are assembled:

- rerun the focused replay ownership/default/currentness suite;
- rerun real MACE execution semantics and assembled P5 MACE qualification;
- rerun P5 TRAIN2/restart/recovery/currentness and P5-F structural ownership tests;
- rerun CV/final publication/P7 intake integration;
- rerun affected campaign CLI/config tests;
- rerun P3/P5-scratch unaffected controls;
- run the complete bounded affected regression surface and broader suite if impact cannot be bounded confidently.

Record exact final candidate/tree identity, environment/runtime dependency identity, commands, pass/fail/skip counts, and any unavailable checks. The prior R2 G11/G12 results remain reusable only for unchanged claims whose subject/oracle/owner path is demonstrably unaffected. A stale pass cannot close G12A.

Serena/Semgrep are desirable analyzers but not acceptance authorities. If unavailable again, record that limitation and use bounded source/AST/symbol inspection plus the required real-owner runtime evidence; do not claim analyzer-specific coverage.

#### G12A implementation record — 2026-09-14 — **IMPLEMENTED; re-review pending**

Candidate: `HEAD` `2a93c33123e446e98042d151c56b6a1c167f887b` plus the uncommitted implementation/spec/test diff (workplan excluded, new test file included) with SHA-256 `6c16db305ca837e5fa76fccb3d8454e0610942da2bd9d7803f00c7229fcfee49`. Environment: conda `mace`, Python 3.11.15, `mace-torch==0.3.16`, torch 2.13.0+cu126, ASE 3.29.0.

Concretization (reductive; no new owner, parser, registry, cache, or wrapper):

- G12A.1: the three duplicated replay label-rewrite blocks (`_render_source_true_label_frame`, `_render_pseudo_frame`, `materialize_true_label_replay_split`) are consolidated into one `replay.py::_replay_transport_frame`, which strips inherited labels and every `config_weight`/`config_*_weight` and writes `config_weight=1` plus 0/1 masks from the labels actually rendered (pseudo stress mask follows the pseudo payload; absent stress stays absent). Directly consumed legacy split files stay unmodified: the existing `inspect_replay_extxyz` boundary now rejects frames whose MACE-resolved weights (absent key -> 1.0, absent property -> 0.0) differ from those masks, before any P5/MACE use. Split files used only as geometry/order references for true-label rematerialization are compared by geometry identity instead of full label inspection, so MACE `fine_tuning_select` `config_weight=weight_pt` metadata on a reference split is canonicalized rather than falsely rejected.
- G12A.2: true-label and pseudolabel view/receipt schemas advance v1 -> v2, legacy rematerialization provenance v1 -> v2, and the unified transport-artifact receipt v1 -> v2; `transport_fields` now lists the MACE-consumed weight fields and the logical view digest binds `mdstats.replay-transport-weights.neutral-binary-mask.v1`. Stale views rematerialize from unchanged source/split/true-label/prediction/qualification parents; ordinary `prepare` republishes the aliases.
- G12A.3: `test_mlff_target_size_p5f_structure.py` drops the generic `restart_latest` token; screening-continuation absence is now an AST import/name/attribute check over the reference closure of the actual target-size continuation owners (renamed wrappers stay in the closure), with a discriminating self-test and a positive structural check that P5 `--restart_latest` is guarded by `request.start_epoch` sourced only from `_authenticate_post_selection_continuation`. No product restart code changed.
- G12A.4: P5 spec section 9.1 (transport weights), section 17 (view cutover without reinference), failures/counterfactuals 29-31; `[objective]` comments in `_config_template` and `campaign.toml.example` and the guide scoped to P3/P5-scratch; guide and DATA9B3 generated CV/production examples match the generator (`fold_count=3`, `partition_seed=104729`, seeds `[0]`, horizon 30, acceptance 0.030, production seeds `[1]`); DATA9B3 command surface lists `storage` subcommands and `qualification {status,run,activate-locked}` as the separate P7 lifecycle, and its production text drops the stale M3 lineage; P7 section 1a binds `common_monitor_record_digest` and no P5 M3 parent (M3 retained only as a separately authorized downstream cohort); DATA8 atomic-number union scoped to DATA8 job directories with the restored-P5 foundation-checkpoint reconstruction route stated. Canonical D3 reinspected: no contradiction, no D3 edit. Tracked PDFs are regenerated by the repository `docs-build` workflow on push; not regenerated locally.

Evidence (G12A.5/G12A.6), all on the candidate above:

- New `tests/test_mlff_replay_transport_weight_masks.py` (real replay owners; contaminated `config_weight`/energy/forces/stress/virials weights, stressed and stressless frames): TRUE_DFT single-source views, pseudolabel views with source/pseudo stress disagreement and zero reinference on view build, legacy rematerialization with contaminated source and reference splits, v1 legacy provenance non-reuse, direct legacy split files fail closed for PRESELECTED/EXTERNAL_TRUE_LABEL/EXTERNAL_PSEUDOLABEL and paired `true_labels/` candidates, and MACE-resolved-canonical admission: `10 passed`. Against the pre-repair product code the same file gives `9 failed, 1 passed` (the positive-admission control), so the oracle discriminates.
- Pinned MACE oracle in `test_mlff_mace_execution_semantics.py`: real replay views from neutral vs contaminated sources through the real MACE parser/`run_train` loader and native `UniversalLoss` yield identical exact 0/1 batch masks (both stress-mask values exercised) and identical per-batch losses; the same contamination copied directly into a replay file changes the loss (oracle sensitivity): `1 passed`.
- Currentness in `test_mlff_replay_true_dft_default_and_prepare_ownership.py`: pseudo-mode prepare, then seeded self-authenticating v1 view/receipt bytes with contaminated weights for all three views; the post-selection read owner and a second `prepare` rematerialize canonical views, prediction cache disposition `hit`, zero provider calls, unchanged source/true-cache/split/prediction-cache/qualification record digests, aliases on v2 views: `1 passed`.
- Restart: narrowed P5-F structure suite `15 passed`; existing real-owner P5 continuation tests (`test_authenticated_train2_continuation_is_resumed_by_the_real_p5_owner`, persisted-evidence mismatch tests, `test_mlff_target_size_p5_r7_guards.py` argv guard) passed inside the affected run.
- Public/config truth: new generator/example/guide/DATA9B3/P7 agreement test in `test_mlff_target_size_p6_destructive_closure.py` passed.
- Complete affected regression, 119 test files derived from consumers of the replay inspection/rendering, campaign CLI/config, DATA8, online/MLCV monitors, post-selection/P5/P7, real-MACE execution/assembled qualification, and P3/P5-scratch controls, `pytest -n 16 --dist=load`: `2083 passed, 47 failed, 4 skipped` (41 min). The 47 failures are exactly the same node set failing on the stashed pre-repair baseline (release/version/dependency-graph/manual-synchronization specification drift and three pre-existing warning-domain tests); no new failure. Skips: two host-unavailable supplied MACE source/checkpoint mounts and two P7 LAMMPS-callback UNAVAILABLE/BLOCKING checks, all pre-existing.
- Structural: Semgrep (executed this round) found no replay `REF_*` label writer outside `_replay_transport_frame`; the two other hits are target exporters that already emit explicit binary masks.

Not claimed: independent G12A/G1B re-review, G13 pilot or three-fold CV, production-scale GPU qualification. Serena was not used. P5->P7 intake is covered by the existing P7 owner suites plus the product field `common_monitor_record_digest`; no new P7 runtime test was added.

### G12A closure criterion

G12A closes only when:

- no current foundation-P5 replay route can make externally supplied non-neutral/non-binary replay weights active in native UniversalLoss;
- stale derived replay views cannot remain current after the repaired transport semantics;
- unchanged expensive replay scientific caches are preserved/reused rather than gratuitously recomputed;
- legitimate P5 restart remains intact while screening-continuation ownership remains unreachable;
- current P5/P7/CLI/DATA8 specification and user/config prose match actual accepted behavior; and
- focused, real-owner, affected-regression evidence passes on the exact repaired candidate.

Only after G12A closure does the plan proceed to G13 and the final independent implementation Review.

## 11. Stage E — bounded scientific pilot then full CV

### G13 — pilot and full CV

Before full CV, record a true pre-update foundation baseline and initial restored checkpoints on representative real LTA data. Record:

- common-target-monitor target RMSE;
- TRUE_DFT replay RMSE/degradation;
- resolved loss/dimensional-threshold/exposure identity;
- selected-head residual E0 identity;
- composition-transfer result;
- corpus counts/order; and
- exact common monitor identity.

Do not relax gates. Immediate material replay degradation comparable to the prior failure regime reopens D1/D2 rather than triggering another compensating D4 patch.

After pilot PASS, run required three-fold affected qualification and independent Protocol 6.3 Review. Production-scale GPU qualification remains deferred to one final complete-package user-side qualification pass.

## 12. D3/D4 documentation and impact closure

Before implementation closeout, reconcile only materially affected current surfaces:

- current D3 architecture sources, with no semantic edit unless a real D3 defect is independently established;
- current P5 D4 spec and spec index;
- online/common-monitor and MLCV monitor docs;
- atomic-reference/fitted-preparation docs;
- adaptive-stop/checkpoint docs;
- final-publication and P7 qualification docs/history;
- DATA8 MACE transport/model-construction prose where its scope overlaps the restored P5 seam;
- CLI/config specs, generated template comments, shipped example, and user guide including replay default, retired fields, objective ownership, qualification command surface, and actual CV defaults;
- public exports for advanced/replaced schema families; and
- semantic history of weighted-stress/fold-local/M3-P5/head-scalar/from-scratch-E0/target-first/whole-P3-policy replacement plus this replay-transport mask/currentness correction when it is material to future interpretation.

Generated documentation is derived output and must be regenerated from canonical sources, but `docs/arch_manuals/mlff_training_data_architecture.md` itself is canonical D3 authority and is not a generated aggregate.

## 13. Explicit non-goals

- redesign target-size ordering/membership/reducer;
- change P3 loss merely to match P5;
- change P5 scratch without separate authority;
- change replay geometry split;
- change replay true/pseudo label membership merely to canonicalize transport weights;
- rerun expensive pseudo-label foundation inference when only a derived ExtXYZ replay view is stale;
- relax target/replay gates;
- add a corpus-order knob;
- add three Huber-delta knobs;
- custom trainer/loss/sampler/E0 solver;
- second replay weight policy/parser/materializer owned by P5;
- second P5 protocol identity/monitor registry;
- remove/rename legitimate P5 restart to satisfy a stale structural oracle;
- semantic migration that makes old noncanonical P5/replay records current;
- blanket invalidation of unchanged P1/P2/P3 or replay source/split/prediction evidence; or
- iterative production-scale GPU qualification before final release.

## 14. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- native UniversalLoss cannot express accepted foundation objective;
- nontrivial P5 configuration or property weighting is actually scientifically required rather than inherited transport contamination;
- accepted replay-first native exposure is scientifically unacceptable;
- dimensional Huber semantics cannot be preserved;
- intended data cannot provide exact protected label-usable common monitor under accepted method;
- composition-level E0 transfer rule is scientifically inadequate rather than merely unimplemented;
- a distinct final-seed ranking cohort is scientifically required;
- P3/P5 cannot legitimately use different accepted loss/exposure methods; or
- correctly restored TRUE_DFT replay still produces material forgetting inconsistent with accepted gates.

Reopen D3 if accepted method still requires competing durable owners, `TrainingProtocolIdentity` and `PostSelectionMethodIdentity` cannot be cleanly scoped without dual P5 authority, common-monitor/transfer lineage cannot be represented acyclically, or the replay transport invariant cannot be realized through the existing replay ownership graph without adding a genuinely new durable owner.

Local implementation, transport, currentness, stale-test, or documentation defects under coherent D1-D3 remain D4 repairs.

## 15. Closeout

Close this workplan only after:

1. accepted D1/D2 remain reviewed/ratified;
2. G1/G1A/G1B remain valid or are reopened if authority changes;
3. restored P5 has one method authority/current materialization path;
4. P5 identity/preparation no longer binds whole P3 policy or inert foundation configuration weights;
5. every sibling CV/final plan binds the same exact common monitor + valid P1 separation evidence;
6. foundation residual/transfer evidence is authenticated from real monitor/consumer composition ancestry;
7. P5 final production/publication has no M3 selection/currentness ancestry;
8. every current foundation-P5 replay route realizes neutral general weight plus exact binary local property masks, with no inherited source weighting capable of changing UniversalLoss;
9. repaired replay-view currentness rejects stale noncanonical views while preserving unchanged source/split/prediction/qualification evidence;
10. legitimate authenticated P5 restart remains intact and P3 screening-continuation ownership remains unreachable;
11. D4 code/config/public API/tests/specifications/guides realize the frozen contract with no inert current fields, stale contradictory defaults/prose, or parallel owners;
12. G11 falsification, G12 real-owner assembled qualification, and G12A integration repair evidence pass on the exact final candidate;
13. bounded scientific pilot and required three-fold affected qualification pass;
14. independent Protocol 6.3 implementation Review passes;
15. affected documentation/history/dependency impacts are reconciled;
16. closeout learning assessment is performed; and
17. final production-scale GPU qualification remains deferred until the complete release package is ready for the user's final machine test.

Current repair/closure order:

```text
G12A replay transport/currentness repair
  -> stale P5-F oracle repair
  -> current spec/config/guide/P7/DATA8 reconciliation
  -> exact-candidate focused + real-owner + affected regression
  -> independent integration/G1B re-review
  -> G13 bounded pilot
  -> required three-fold affected qualification
  -> final independent Protocol 6.3 implementation Review
  -> documentation/history/dependency/learning closeout
```

Production-scale GPU qualification remains deferred to the final complete release package and the user's final machine-side qualification pass.

Until those conditions hold, the workplan remains **active**.
