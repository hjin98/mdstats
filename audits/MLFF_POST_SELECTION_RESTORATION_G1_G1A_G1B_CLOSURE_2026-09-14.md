# MLFF post-selection restoration G1/G1A/G1B closure record — 2026-09-14

**Branch:** `fix/mlff-post-selection-method-restoration`  
**Parent workplan:** `workplans/active/MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_WORKPLAN.md`  
**Protocol:** SSDP 6.3  
**Disposition:** G1 PASS; G1A PASS; G1B PASS; executable implementation may begin subject to the staged dependency order frozen by the parent workplan.

This record is evidence of the pre-implementation closure review. It is not a second implementation authority. Current D1-D4 sources and the parent workplan remain authoritative.

## 1. Governing upstream state

Accepted D1/D2 restoration authority is the current branch pair:

- `docs/methods/mlff_scientific_method.md`
- `docs/methods/mlff_numerical_algorithmic_method.md`

The D1/D2 independent re-review previously passed at `f310b4c15c6b0465b34013d329847abdb208bae2`, and the stakeholder authorized progression into D3/D4 closure.

No new D1/D2 Serious Challenge was found during G1-G1B closure.

## 2. G1 authority/API/evidence census

### Current D3/D4 owners that must be preserved or rewired

| Surface | Classification | G1 disposition |
|---|---|---|
| `PostSelectionMethodIdentity` | current P5 method owner | preserve and advance generation/field projection; remove whole-P3-policy dependency |
| `CvValidationPolicyIdentity` | current P5 CV policy | preserve; retire selected-fold checkpoint-monitor budget and set one default-K owner |
| `FinalProductionPolicyIdentity` | current P5 final policy | preserve; publication policy remains role-specific |
| `PostSelectionFittedPreparation` | current P5 preparation surface but stale shape | replace current foundation mode shape with P5 residual/transfer ancestry; historical weight-bearing foundation shape stays historical |
| `PostSelectionMaterialization` | current P5 executable materialization | preserve as current P5 realization descendant; advance currentness fields/generation as required |
| post-selection CV plan/fold/run-plan owners | current P5 role-plan owners | remove fold-local target checkpoint membership; bind common monitor + P1 separation ancestry |
| final-production plan | current P5 final role-plan owner | remove M3 ancestry; bind same common monitor used by CV |
| final-publication owner | current P5 member-selection owner | remove M3 evaluation/ranking; consume frozen common-monitor representative records |
| MACE adapter seam | sole dependency-facing executor | preserve; make loss/exposure resolution mode-specific rather than global |
| existing atomic-reference fitter | sole E0 solver | preserve; route foundation modes through selected-head residual inputs and add transfer evidence at fitted-preparation owner |
| `OnlineTargetMonitorPolicy` / target-monitor constructor | current monitor capability | preserve deterministic common-monitor capability; advance exact P5 semantics to exact-256/no-fallback/neutral parent |
| MLCV monitor machinery | current replay/diagnostic capability | preserve replay/diagnostic ownership; remove independent target checkpoint sampling |
| P1 neutral protected-relation authority | current cross-role relation owner | preserve and use for monitor-vs-target separation |
| replay owner | current replay source/split/monitor owner | preserve; canonical omission TRUE_DFT, explicit pseudo opt-in, legacy ambiguity fail-closed |
| adaptive-stop/checkpoint owners | current model-control owner | preserve score/admissibility semantics; route target evidence to common `M_mon` only after monitor exists |

### Current upstream/P3 owners explicitly preserved

| Surface | Classification | G1 disposition |
|---|---|---|
| P1/P2/P3 target-size evidence | current independent upstream authority | preserve; no blanket P5 invalidation |
| `TargetSizeCommonTrainingPolicy` | current P3 common-policy owner | preserve for P3; do not bind whole digest into current foundation P5 |
| P3 objective/weighting policy | current P3 owner | preserve; legitimate P3 overrides do not become foundation-P5 method fields |
| M3 membership/evidence | current P3 development evidence | preserve for P3 and separately authorized downstream probe use; retire from P5 plan/checkpoint/publication ancestry |
| P3 complete-batch MACE realization | current P3 execution semantics | preserve; do not change via global loss/drop-last repair |

### Broad/historical compatibility surfaces

| Surface | Classification | G1 disposition |
|---|---|---|
| `TrainingProtocolIdentity` | broad DATA8-era general/historical identity | may remain for separately current non-P5 consumers/history; cannot authorize restored P5 |
| `Data8PreparationBundle` | broad DATA8 fixed-file aggregate | may remain for separately current non-P5 consumers/history; not current P5 materialization path |
| selected-fold checkpoint-monitor schemas | superseded P5 schema | historical/read-only as supported; never current |
| M3-dependent P5 final plan/publication schemas | superseded P5 schema | historical/read-only as supported; never current |
| weight-bearing foundation-P5 fitted preparations | superseded P5 schema | historical/read-only as supported; never current |
| old weighted-stress foundation trajectories/checkpoints | superseded P5 evidence | historical; cannot restart as current |

### Configuration/public surfaces

The census confirms current repair must cover:

- retired target/replay training-head scalar fields;
- canonical replay label-mode default and legacy ambiguity;
- one P5 fold-default resolver (`3`, override `K>=2`);
- fixed foundation-P5 UniversalLoss parameters without inheriting P3 objective/weighting;
- exact common monitor and no short fallback;
- foundation residual-fit mode/head/transfer failure behavior;
- foundation distributed-execution rejection; and
- currentness generation cutovers at the narrowest affected owners.

**G1 result:** PASS. Each material semantic now has one identified current owner and explicit compatibility disposition. No current P5 path requires both `TrainingProtocolIdentity` and `PostSelectionMethodIdentity`.

## 3. G1A D3 reconciliation

Canonical D3 sources reconciled for the restoration:

- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`
- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`

The resulting owner graph is acyclic and singular:

```text
TargetBinding
  + neutral common target-monitor owner
  + P1 cross-role relation authority
  -> PostSelectionMethodIdentity
  -> role policy
  -> role plan
  -> fitted P5 preparation
  -> PostSelectionMaterialization
  -> run/checkpoint/evaluation evidence
  -> CV acceptance / final publication
  -> downstream qualification
```

Key architectural decisions now explicit:

1. `PostSelectionMethodIdentity` is sole current P5 method owner.
2. `TrainingProtocolIdentity` is scoped away from restored P5.
3. foundation P5 does not bind whole P3 common-training policy.
4. MACE adapter remains sole dependency-facing execution seam and resolves by mode.
5. one neutral `OUTER_MONITOR` common monitor is external to selected folds.
6. every CV/final plan binds the same common-monitor record.
7. monitor membership and P1 relation-separation evidence are distinct ordered owners.
8. selected-fold membership is train + held-out outer evaluation + purge only.
9. existing E0 fitter remains sole solver; P5 preparation owns transfer validation.
10. final P5 publication has no M3 selection/currentness dependency.
11. currentness advancement is narrow and preserves independent P3 evidence.
12. top-level `mlff_training_data_architecture.md` is canonical D3 authority alongside the chapter set; it is not treated as a generated aggregate.

**G1A result:** PASS. The accepted D1/D2 method is expressible with one coherent D3 graph; no parallel method/monitor/E0/currentness owner is required.

## 4. G1B D4 handoff freeze

Normative D4 sources reconciled/created:

- `docs/specs/training_data/mlff_post_selection_p5_spec.md` — sole current restored-P5 D4 handoff.
- `docs/specs/training_data/mlff_online_monitor_spec.md` — exact common-target-monitor record semantics.
- `docs/specs/training_data/mlff_data_stage_plan_spec.md` — cross-cutting current-generation ownership/lineage invariants.
- `docs/specs/training_data/mlff_data8_mace_artifacts_spec.md` — narrowed to generic transport/general non-P5 `TrainingProtocolIdentity` scope.
- `docs/specs/training_data/README.md` — current-spec index and authority routing.

The freeze is specific on:

- foundation-P5 method identity and P5 preparation-policy separation from P3;
- replacement foundation fitted-preparation required/forbidden fields;
- selected-head residual-E0 fit and composition-transfer ancestry;
- mode-specific MACE loss/exposure realization;
- canonical TRUE_DFT replay default and legacy ambiguity failure;
- common exact-256 target-monitor policy/record;
- CV fold/plan removal of selected-only checkpoint-monitor membership;
- same-monitor binding across all sibling CV/final plans;
- target/replay score-weight preservation versus training-head-scalar retirement;
- final-production M3 field/ancestry removal;
- exact `single_best_final_seed` ordering contract over frozen common-monitor records;
- currentness/schema generation cutover; and
- fail-closed unsupported historical/current-cross-mode state.

The frozen foundation-preparation contract explicitly forbids retaining old P3 objective/configuration-weight fields as null/default/current digest baggage.

The frozen final-publication contract explicitly forbids replacing accepted target-only representative ordering with raw scalar-RMSE sorting or rerunning target/M3 evaluation.

**G1B result:** PASS. Two independent implementers following the current D4 sources should produce the same externally visible owner fields, failure behavior, currentness semantics, and public/config behavior while retaining freedom on private helper decomposition and exact schema-token strings.

## 5. Staging dependency closure

The pre-implementation stage ordering is now unambiguous:

```text
Stage A
  method/loss/exposure/config/identity cutover
  preserve checkpoint/adaptive-stop score/admissibility semantics
  DO NOT claim current target-monitor routing yet

Stage B
  residual-E0/head/transfer implementation and manufactured falsification
  DO NOT authenticate current foundation preparation/run yet

Stage C
  build/authenticate exact common M_mon
  bind P1 separation evidence
  complete foundation transfer with actual M_mon composition classes
  route checkpoint/adaptive-stop target evidence to M_mon
  cut over CV/final topology and publication ancestry

Stage D
  assembled currentness/runtime/docs/examples/generated-view reconciliation
  Stage D may not redesign frozen G1B method-bearing contracts
```

Thus:

```text
common monitor exists/authenticates
    before current G9 target routing
    and before G4 transfer evidence authorizes a current run
```

No temporary fold/M3 monitor owner or manufactured monitor ancestry is permitted.

## 6. Fresh falsification pass

The assembled pre-code authority was challenged against these failure modes:

1. dual current P5 method identity — rejected by D3/D4 scope;
2. fold-local target checkpoint monitor surviving as current membership — rejected;
3. M3 surviving as P5 plan/publication identity — rejected;
4. whole-P3 common-training-policy digest surviving as P5 identity parent — rejected;
5. inert P3 configuration weights surviving in foundation fitted preparation — rejected;
6. global loss flip altering P3/scratch — rejected by mode-specific seam;
7. manufactured monitor composition authorizing current transfer — rejected by stage/order and exact record ancestry;
8. common-monitor shortfall becoming degraded success — rejected by exact-256 failure contract;
9. relation-clean monitor being obtained by resampling/filtering — rejected by ordered owner contract;
10. selected-only relation projection being sole cross-role proof — rejected;
11. single-best publication silently becoming raw RMSE sort — rejected;
12. final publication rerunning target/M3 evaluation — rejected;
13. Stage D changing frozen method-bearing contract without reopening G1B — rejected;
14. top-level D3 manual being treated as a generated/non-authoritative derivative — corrected;
15. DATA8 blanket prohibition on UniversalLoss remaining current for P5 — removed by narrowing DATA8 itself and installing dedicated P5 spec.

No residual pre-implementation blocker was found.

## 7. Pass / No-Pass

**PASS — G1, G1A, and G1B are closed.**

Executable implementation may now start at Stage A, subject to the parent workplan and current D1-D4 authority. G4 and G9 retain their explicit Stage-C completion dependencies on the authenticated common monitor.

This PASS does not close the parent workplan. Implementation, stage-local affected regression, assembled qualification, bounded scientific pilot, full CV, and final independent Protocol 6.3 review remain open.
