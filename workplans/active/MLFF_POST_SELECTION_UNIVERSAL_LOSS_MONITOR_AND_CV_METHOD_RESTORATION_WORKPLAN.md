# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — independent Protocol 6.3 implementation Review NO-PASS on 2026-09-14 for code candidate `521bc932ec9b52cc769db32a2561fa4cd1b8eba8` (derived-doc head `f71c5b9af34454940814445fd2e50b97265526d1`); G0/G1/G1A remain CLOSED/PASS; G1B is REOPENED for a D4 ancestry-direction contradiction; Stages A–D are implemented, but candidate-bound G11/G12 evidence, G13 pilot/full CV, and closeout remain open  
**Current authority:** accepted D1/D2 in `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md`; current D3 in `docs/arch_manuals/mlff_training_data_architecture.md` plus canonical chapters; current D4 restored-P5 handoff in `docs/specs/training_data/mlff_post_selection_p5_spec.md`, with G1B narrowly reopened as specified below  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  
**Pre-code closure evidence:** `audits/MLFF_POST_SELECTION_RESTORATION_G1_G1A_G1B_CLOSURE_2026-09-14.md`

## 1. Disposition

The upstream D1/D2 Serious Challenge is resolved for this restoration branch. The repaired D1/D2 pair passed independent falsification at `f310b4c15c6b0465b34013d329847abdb208bae2`, and the stakeholder authorized progression.

G1 authority/API/evidence census and G1A D3 reconciliation remain closed PASS. Independent implementation Review found no D1/D2 Serious Challenge and no D3 architecture contradiction: the accepted D3 dependency direction remains acyclic (`role plan -> fitted P5 preparation -> materialization -> evidence`). G1B is, however, narrowly reopened because the normative D4 P5 specification later states that the CV/final plan itself binds `foundation fitted-preparation ancestry`, which reverses that dependency and would create a plan/preparation cycle if implemented literally. This is a D4 specification defect, not authority for a compensating runtime graph.

Stages A–D are implemented on code candidate `521bc932ec9b52cc769db32a2561fa4cd1b8eba8`. The assembled implementation inspected in Review is otherwise substantially aligned with the restored method: current foundation loss/exposure, common-monitor routing, selected-head residual E0/transfer, currentness, and M3-free publication all route through existing owners rather than parallel machinery. Closure is nevertheless blocked until the narrow G1B repair is reviewed/frozen and candidate-bound G11/G12 plus G13 evidence is produced.

The repair remains deliberately reductive: remove wrong/retired semantics and rewire existing owners. Do not create a custom loss, second sampler, second E0 solver, shadow trainer, parallel method/protocol registry, second currentness system, compatibility wrapper that merely preserves an obsolete current path, or a reverse plan->preparation binding added only to satisfy contradictory wording.

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
general config_weight in P5      neutral transport only; not a P5 loss layer
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

### 3.4 Objective/weight taxonomy

Keep distinct:

1. global energy/force/stress coefficients;
2. general `ConfigurationWeightPolicy` / `config_weight` where a method consumes it;
3. target/replay **training-head scalar** weights, retired for current P5; and
4. checkpoint/adaptive-stop `target_score_weight` / `replay_score_weight`, which remain current.

Foundation UniversalLoss does not consume general `config_weight` as an active P5 scientific layer. The fixed foundation-P5 objective is independent of P3 `[objective]` / `[weighting]` overrides.

### 3.5 Identity/currentness economy

- `PostSelectionMethodIdentity` is sole current P5 method identity.
- `TrainingProtocolIdentity` may remain for separately current non-P5 consumers/history but cannot authorize restored P5.
- `TargetSizeCommonTrainingPolicy` remains a P3 owner; current foundation P5 does not bind its whole digest.
- Exact monitor membership, fold membership, fitted E0 result, transfer result, checkpoints, and metrics are descendants, not pre-work method fields.
- P5-only generation changes do not blanket-stale unchanged P3 evidence.
- True P5 method changes invalidate dependent P5 evidence.

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
    reason: Retired fields, incompatible fit modes, historical schemas, ambiguous replay defaults, and stale run state must fail closed.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve independent immutable P1/P2/P3/selection evidence rather than rebuilding or globally invalidating it.
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

### G1B — D4 handoff freeze — **REOPENED / REVIEW BLOCKER**

Normative restored-P5 handoff: `docs/specs/training_data/mlff_post_selection_p5_spec.md`.

Related current specs/index reconciled:

```text
docs/specs/training_data/mlff_online_monitor_spec.md
docs/specs/training_data/mlff_data_stage_plan_spec.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/specs/training_data/README.md
```

Independent implementation Review found one internal contract contradiction in the normative P5 spec. Section 1 correctly freezes the acyclic chain `role plan -> PostSelectionFittedPreparation -> PostSelectionMaterialization`, matching accepted D3. Sections 11 and 13 nevertheless list `foundation fitted-preparation ancestry where applicable` as a parent that the CV/final plan itself SHALL bind. A plan cannot both own and descend from its fitted preparation without a cycle.

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

Complete G10-G12 after Stages A-C. Later documentation may reconcile examples/generated views/history, but cannot change the frozen G1B method-bearing contract without reopening G1B/upstream owner as applicable.

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
52. D3 source regresses target checkpoint monitor to fold-local membership; and
53. Stage D changes a frozen method-bearing G1B contract without reopening authority.

Each is rejected by a real owner or documented inapplicable with evidence.

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
2. **Candidate-bound G11/G12 evidence is not yet reusable closure evidence.** The workplan's prior status text referred to an uncommitted working-tree run and a 223-test-file regression, while the reviewed implementation is now commit `521bc932...` with a subsequent derived-doc commit. Repository-visible automation on the reviewed branch is documentation generation, not the required focused/affected/real-owner qualification transcript. Existing tests and static review provide strong coverage but do not substitute for an exact-candidate qualification record. Re-run and record G11/G12 plus affected regression against the repaired final candidate, including pinned MACE version/source qualification and unaffected P3/P5-scratch controls. Do not add product machinery to satisfy evidence; exercise the existing owners.
3. **G13 remains intentionally open.** Run the bounded scientific pilot, record the prescribed baseline/restored metrics and exact method/monitor/E0/exposure identities, then run the required three-fold affected qualification. If correctly restored TRUE_DFT replay still shows material forgetting comparable to the prior failure regime, reopen D1/D2 rather than layering another D4 compensation.

**Nonblocking observations:**

- Current code inspection found one P5 method family, one current common-monitor construction owner, one existing atomic-reference solver reused for foundation residual E0, existing EVAL2 ordering reused for final single-best publication, and fail-closed historical/currentness boundaries; no second product owner is justified by this Review.
- The common monitor is deterministically re-resolved per selected context but binds identical content identity/separation ancestry; this is not a semantic blocker while sibling-plan digest equality remains enforced. Do not add a new monitor cache/registry merely to make object construction singular.
- Historical scheduler/resource regression tests removed only where their tested helper was itself retired; real scheduler/process/restart tests and memory-backoff/zero-admission owner tests remain. Do not restore obsolete helper-specific oracles merely for line-count parity.
- Serena/Semgrep-specific execution was unavailable in the remote review environment; structural/symbol/file inspection was performed through the repository connector. This limits analyzer-specific completeness claims but does not relax any qualification gate.

**Repair/closure order:** G1B spec correction + narrow re-review -> candidate-bound G11/G12 and affected regression -> G13 pilot -> required three-fold affected qualification -> independent implementation re-review -> documentation/history/dependency/learning closeout. Production-scale GPU qualification remains deferred to the final complete release package.

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

- current D3 architecture sources;
- current P5 D4 spec and spec index;
- online/common-monitor and MLCV monitor docs;
- atomic-reference/fitted-preparation docs;
- adaptive-stop/checkpoint docs;
- final-publication docs/history;
- CLI/config docs including replay default and retired fields;
- public exports for advanced/replaced schema families; and
- semantic history of weighted-stress/fold-local/M3-P5/head-scalar/from-scratch-E0/target-first/whole-P3-policy replacement.

Generated documentation is derived output and must be regenerated from canonical sources, but `docs/arch_manuals/mlff_training_data_architecture.md` itself is canonical D3 authority and is not a generated aggregate.

## 13. Explicit non-goals

- redesign target-size ordering/membership/reducer;
- change P3 loss merely to match P5;
- change P5 scratch without separate authority;
- change replay geometry split;
- relax target/replay gates;
- add a corpus-order knob;
- add three Huber-delta knobs;
- custom trainer/loss/sampler/E0 solver;
- second P5 protocol identity/monitor registry;
- semantic migration that makes old P5 records current;
- blanket invalidation of unchanged P3 evidence; or
- iterative production-scale GPU qualification before final release.

## 14. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- native UniversalLoss cannot express accepted foundation objective;
- nontrivial P5 configuration weighting is actually scientifically required;
- accepted replay-first native exposure is scientifically unacceptable;
- dimensional Huber semantics cannot be preserved;
- intended data cannot provide exact protected label-usable common monitor under accepted method;
- composition-level E0 transfer rule is scientifically inadequate rather than merely unimplemented;
- a distinct final-seed ranking cohort is scientifically required;
- P3/P5 cannot legitimately use different accepted loss/exposure methods; or
- correctly restored TRUE_DFT replay still produces material forgetting inconsistent with accepted gates.

Reopen D3 if accepted method still requires competing durable owners, `TrainingProtocolIdentity` and `PostSelectionMethodIdentity` cannot be cleanly scoped without dual P5 authority, or common-monitor/transfer lineage cannot be represented acyclically.

Local implementation defects under coherent D1-D3 remain D4 repairs.

## 15. Closeout

Close this workplan only after:

1. accepted D1/D2 remain reviewed/ratified;
2. G1/G1A/G1B remain valid or are reopened if authority changes;
3. restored P5 has one method authority/current materialization path;
4. P5 identity/preparation no longer binds whole P3 policy or inert foundation configuration weights;
5. every sibling CV/final plan binds the same exact common monitor + valid P1 separation evidence;
6. foundation residual/transfer evidence is authenticated from real monitor/consumer composition ancestry;
7. P5 final production/publication has no M3 selection/currentness ancestry;
8. D4 code/config/public API/tests realize the frozen contract with no inert current fields or parallel owners;
9. G11 falsification and G12 real-owner assembled qualification pass;
10. bounded scientific pilot and required three-fold affected qualification pass;
11. independent Protocol 6.3 implementation Review passes;
12. affected documentation/history/dependency impacts are reconciled;
13. closeout learning assessment is performed; and
14. final production-scale GPU qualification remains deferred until the complete release package is ready for the user's final machine test.

Until those conditions hold, the workplan remains **active**.
