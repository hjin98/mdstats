# TARGET-SIZE-V5-CLOSE1 — Final v5 Conformance Closure

**Status:** active  
**Design state:** frozen after final independent software-design review on 2026-08-22  
**Current authority:**
- `docs/specs/training_data/mlff_target_subset_size_study_spec.md`
- `docs/specs/training_data/mlff_data_stage_plan_spec.md`
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- `docs/arch_manuals/mlff_training_data_dependency_graph.json`

**Lineage only:**
- `workplans/archive/TARGET_SIZE_V5_WORKPLAN.md`
- `workplans/archive/TARGET_SIZE_V5_POST_REVIEW_FIX1.md`

**Target branch/base:** current provided `feat/target-size-v5-redesign` source snapshot; archive contains no Git metadata.

## Objective

Close the remaining implementation/documentation gaps found by the final v5 architecture review without changing the accepted target-size topology.

The current architecture remains:

```text
required final + CV gradient-training domains
  -> domain-local MVSEL2
  -> domain-local REPAIR2 R_d
  -> monotone MVQUAL2
  -> common qualified size population Q
  -> paired-seed TRAIN2 study
       epoch 3 -> epoch 10 -> epoch 30
  -> immutable selected N
  -> every target-size-controlled training domain consumes R_d[:N]
  -> held-out CV / EVAL / VERIFY
```

This is a conformance/closure round, not another redesign.

The mandatory correction is to make a real candidate-specific TRAIN2/EVAL2 numerical or scientific failure become authenticated target-size failure evidence and, when it leaves too few comparable candidates, the typed terminal result:

```text
insufficient_comparable_candidates
```

rather than an unstructured campaign failure.

The same round must reconcile replay-monitor wording/edges in the architecture documentation, strengthen one cheap derived-identity invariant, and remove or explicitly quarantine dead coarse-size-study API residue if it is proven unused.

## Diagnosis

The study reducer already implements `insufficient_comparable_candidates`, but the production controller cannot currently supply realistic failure evidence:

1. TRAIN2 execution failures are collected by the campaign training stage and terminate that stage generically.
2. `_available_successful_executions()` filters failed runs out before target-size EVAL2.
3. `_eval2_target_size_endpoint_evidence()` requires a successful execution and exact endpoint and otherwise raises `CampaignCliError`.
4. Successful endpoint evidence is always emitted with `numerical_valid=True`.
5. `TargetSizeTrainingEvidence` structurally requires a complete finite endpoint even when `numerical_valid=False`, so it cannot truthfully represent a trajectory that fails before the 3/10/30 boundary or a target evaluation that produces non-finite predictions.

The defect is therefore an evidence-model/controller integration gap. It is not a failure of the fixed-eight size architecture, paired-seed funnel, REPAIR2/MVQUAL2 ownership, or continuation design.

## Invariants

The following contracts are frozen through this workplan.

### Scientific and selection invariants

- Candidate universe remains exactly `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`.
- `MVQUAL2` remains the sole hard size-eligibility authority.
- Every required training domain continues to use exactly its local `R_d[:N]` membership.
- The study funnel remains `q -> min(q,4) -> 2 -> 1` at epochs `3 -> 10 -> 30` for comparable candidates.
- Candidate comparisons remain paired over the exact ordered training-seed set owned by the sole enabled training method.
- Practical-equivalence widths remain configurable, digest-bound scientific policy.
- Replay/model-quality/physical/deployment criteria do not become target-size hard gates or tie-breakers.
- `16384` remains the fixed ceiling; no rescue or generated target size is permitted.
- A selected target size remains immutable before held-out validation begins.

### Failure-semantics invariants

- Only positively identified **candidate-specific numerical/scientific invalidity** may become target-size trajectory-failure evidence.
- Input, schema, lineage, missing-file, configuration, programming, launch, timeout, interruption, OOM/resource, and infrastructure failures remain ordinary fail-closed execution/campaign errors unless a separate existing authority already classifies them otherwise.
- Do not classify scientific failure by fuzzy stderr keyword matching.
- A failed candidate/seed must remain bound to the exact study policy, run, candidate data, stage, and available execution/evaluation provenance.
- A failed candidate cannot be silently replaced by another seed or retrained from a different parent.

### Continuation invariants

- Successful epoch-3/10/30 evidence retains the current strict complete-endpoint contract.
- Epoch 10 authenticates exact epoch-3 checkpoint/optimizer/RNG ancestry.
- Epoch 30 authenticates exact epoch-10 ancestry.
- Failure handling must not create a synthetic successful endpoint, score, checkpoint, optimizer state, RNG state, or target-evaluation digest that never existed.

### Resource invariants

- No additional product-scale dataset, descriptor, MVIDX, selector, or REPAIR2 copy per rung or seed.
- Failure evidence is metadata-scale and content-addressed.
- No extra model inference is required merely to classify an already-observed failure.
- Existing sparse/progressive MVQUAL2 and TRAIN2 scheduling behavior remains unchanged.

## Design decisions

### D1 — Keep successful endpoint evidence strict

Do **not** expand `TargetSizeTrainingEvidence` into a partially nullable record that means both “completed endpoint” and “failed attempt.” Its current strong endpoint invariants are valuable for continuation authentication.

Refactor the target-size evidence model into two semantically distinct records:

```text
TargetSizeTrainingEvidence
    = successful, complete, finite 3/10/30 endpoint

TargetSizeTrajectoryFailureEvidence
    = authenticated candidate/seed failure while attempting one required fidelity stage
```

The failure record must be narrow. At minimum it binds:

- stage / required fidelity boundary;
- target size;
- optimizer seed;
- failure phase (`train` or `target_evaluation`);
- stable machine-readable failure code;
- concise authenticated failure reason(s);
- target-size-study policy digest;
- training-run digest;
- candidate-data digest;
- training-policy and schedule identity where applicable;
- execution-record / attempt-record identity for TRAIN2 failures;
- checkpoint and target-role/evaluation identity when failure occurs during EVAL2 and those artifacts exist;
- authenticated partial progress identity when available, without pretending the required endpoint completed.

Successful and failure records for the same `(size, seed, stage)` are mutually exclusive.

### D2 — Use explicit owning-layer numerical classification

Do not infer numerical failure from arbitrary child-process text.

Introduce a narrow machine-recognizable numerical/scientific failure path at the owners that can prove the condition:

1. **TRAIN2 runtime:** validate finite live training state at durable boundaries before publishing continuation authority. Non-finite model/EMA state (and any other explicitly qualified TRAIN2 numerical invariant) emits a stable mdstats numerical-failure marker/code and must not persist a valid endpoint companion/summary for that boundary.
2. **EVAL2 target evaluation:** non-finite model predictions/target metric construction use a dedicated numerical-evaluation exception or equivalent typed signal. Ordinary `TrainingDataInputError` remains too broad and must not be swallowed as scientific failure.
3. **Campaign execution:** recognize only the explicit mdstats numerical marker/classification and preserve it in immutable execution-attempt provenance. Existing deterministic input/schema classifications remain distinct.

A generic non-zero exit, timeout, launch failure, CUDA OOM, missing checkpoint, malformed artifact, digest mismatch, or unexpected exception is not target-size scientific-failure evidence.

### D3 — Stage reduction consumes a complete outcome population

For each authorized stage, the reducer must receive exactly one outcome per expected `(candidate size, seed)`:

```text
successful endpoint evidence
OR
trajectory-failure evidence
```

The union of success and failure keys must equal the exact policy-ordered expected population with no duplicate, missing, substituted, or reordered identities.

Only complete paired successful candidates are rankable. If fewer candidates remain than required for the next transition, persist:

```text
outcome = insufficient_comparable_candidates
comparison_failure_stage = <coarse|short|final>
comparison_failures = authenticated (size, seed, reasons...)
```

If enough complete candidates remain, continue the existing deterministic equivalence-aware ranking unchanged.

### D4 — Hard-cut derived target-size evidence schema if needed

If the evidence-model cleanup requires schema/version advancement, perform a hard cut for **derived target-size study state only**. Do not invent a translation layer for structurally ambiguous old invalid-evidence records.

Current valid upstream FEAS1/MVIDX1/MVSEL2/REPAIR2/MVQUAL2 authority remains reusable when its own identities authenticate. A stale/incompatible target-size study is rebuilt from those authorities.

### D5 — Replay is protocol/diagnostic identity, not ranking evidence

The target-size metric remains target-only. Replay semantics/monitor identity may be bound because candidates share the same training protocol and replay diagnostics may exist, but replay score/retention is not consumed as target-size eligibility, ranking, or tie-break evidence.

Documentation and dependency edges must state this distinction explicitly.

## Scope

### Required code scope

- `mdstats/training_data/target_size_study.py`
- `mdstats/training_data/train2_runtime.py`
- `mdstats/training_data/critical_precision_cli.py` only as needed for an explicit machine-readable numerical-failure signal
- `mdstats/training_data/campaign_execution.py` only as needed to persist that explicit classification
- `mdstats/training_data/eval2.py` for a narrow numerical-evaluation signal
- `mdstats/training_data/_campaign_cli_core.py`
- package exports only if a new public/internal record type requires them

### Required tests

- `tests/test_mlff_target_size_study_v5.py`
- target-size campaign-path tests in `tests/test_mlff_campaign_cli.py` or a focused new target-size campaign test module
- `tests/test_mlff_data9b2_execution_aggregation_freeze.py` if execution classification changes
- `tests/test_mlff_eval2.py` for EVAL2 numerical classification
- `tests/test_mlff_target_size_v5_topology.py` only for supplementary forbidden-path guards

### Required documentation scope

- `docs/specs/training_data/mlff_target_subset_size_study_spec.md`
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- `docs/arch_manuals/mlff_training_data_dependency_graph.json`
- generated consolidated architecture manual/PDF if repository policy requires rebuilding it after source-fragment changes

### Conditional cleanup scope

- `mdstats/training_data/eval2.py::build_eval2_coarse_size_study_target_role`
- corresponding exports/tests and unused `_eval2_target_role_for_run(... coarse ...)` arguments

Delete these only after proving there is no current production/specification/API requirement. If public compatibility still materially matters, retain them outside the v5 authority path with explicit legacy/non-v5 status rather than pretending they are current target-size architecture.

## Gates

### G0 — Freeze the failure-evidence contract

**Goal:** establish one unambiguous representation and classification boundary before controller changes.

**Work:**

- Define `TargetSizeTrajectoryFailureEvidence` and its serialization/semantic invariants.
- Decide the minimal stable failure codes required for this round; keep the taxonomy narrow.
- Make successful `TargetSizeTrainingEvidence` unequivocally represent a complete finite endpoint. Remove or prohibit synthetic invalid-endpoint construction under the new schema.
- Define exact stage-batch identity rules over success + failure outcomes.
- Define restart behavior for old derived target-size study/evidence schemas.

**Acceptance:**

- An early TRAIN2 failure can be represented without a fake epoch endpoint, fake force score, fake checkpoint, or fake evaluation digest.
- An EVAL2 non-finite prediction can be represented while retaining the real successful training/checkpoint identity.
- Generic input/lineage/programming/infrastructure failure cannot instantiate the scientific failure record.

### G1 — Implement owning-layer numerical/scientific failure evidence

**Goal:** produce authenticated failure provenance only where the software can positively establish numerical invalidity.

**Work:**

- Add finite-state validation at the TRAIN2 runtime durability boundary before a continuation endpoint is published.
- Emit a stable explicit mdstats numerical-failure code/marker on qualified TRAIN2 numerical invalidity.
- Preserve that classification in `TrainingRunAttemptRecord` / `TrainingRunExecutionRecord` without conflating it with deterministic input/schema failures.
- Introduce a narrow EVAL2 numerical-evaluation signal for non-finite energy/force/stress or derived target metric values.
- Ensure ordinary EVAL2 input/role/artifact/lineage exceptions remain exceptions.

**Acceptance:**

- A controlled non-finite TRAIN2 state is persisted as an authenticated failed execution classification, not a successful endpoint.
- A controlled non-finite EVAL2 prediction is distinguishable from a malformed role, missing artifact, digest mismatch, or programming error.
- No fuzzy log-message heuristic is required.

### G2 — Wire the real target-size campaign path into typed terminal state

**Goal:** make the live `train -> evaluate -> study transition` path realize the normative v5 failure semantics.

**Work:**

- During an active target-size fidelity stage, distinguish a classified candidate-specific numerical TRAIN2 failure from ordinary campaign failure.
- Do not allow one classified candidate failure to terminate the entire training stage before the required stage population can be reduced; continue/finish independent authorized candidates subject to existing scheduler safety rules.
- Preserve ordinary stop-on-error behavior for unclassified failures.
- Replace the “successful executions only” assumption for target-size endpoint reduction with exact resolution of each expected `(size, seed)` to either:
  - successful execution + endpoint evaluation, or
  - authenticated trajectory-failure evidence.
- Convert only the narrow EVAL2 numerical signal to failure evidence; propagate all other exceptions.
- Update `attach_epoch_3_evidence`, `attach_epoch_10_evidence`, and `attach_epoch_30_evidence` (or one consolidated owning function) so exact population validation spans success + failure outcomes.
- Preserve current ranking, equivalence, continuation, ceiling, and survivor cardinalities for the successful population.

**Acceptance:**

- Real campaign path: one numerical candidate/seed failure is recorded and the stage continues when enough candidates remain.
- Real campaign path: too few complete paired candidates yields persisted `insufficient_comparable_candidates` with exact failed stage and authenticated `(size, seed, reason)` evidence.
- Real campaign path: generic failed execution still fails closed as a campaign error.
- No downstream held-out evidence is created before terminal target-size outcome.

### G3 — Identity hardening and architecture reconciliation

**Goal:** finish low-cost conformance cleanup without adding another authority.

**Work:**

- Recompute/validate `candidate_data_digest` from its canonical candidate inputs during target-size plan semantic validation, rather than validating only digest syntax and relying exclusively on outer campaign restart reconstruction.
- Clarify the target-size specification/manual so replay semantics are protocol/diagnostic identity but replay metrics do not rank, qualify, reject, or tie-break sizes.
- Remove `COMMON_REPLAY_MONITOR -> SIZE_STUDY_EPOCH3` with edge type `consumes` from `mlff_training_data_dependency_graph.json`; retain replay identity at `FROZEN_TRAINING_PROTOCOL` or another semantically correct identity edge.
- Correct matching prose in `50_target_multiview.md` and `80_ownership_and_decisions.md`.
- Inspect the coarse-size-study EVAL2 API/arguments. Delete them if proven dead and compatibility-neutral; otherwise explicitly mark them non-v5/legacy and keep them out of current dependency documentation.

**Acceptance:**

- A forged derived `candidate_data_digest` cannot survive `TargetSizeStudyPlan` semantic validation even before campaign-store reconstruction.
- No current architecture text or graph claims replay-monitor scores are consumed by target-size ranking.
- No unqualified second coarse-size-study authority remains reachable from current v5 production orchestration.

### G4 — Direct regression, restart, and closeout

**Goal:** prove the corrected semantics through the real owning path and close the v5 architecture.

**Mandatory tests:**

1. successful all-valid target-size stage remains byte/decision equivalent to current behavior;
2. TRAIN2 non-finite candidate failure -> authenticated trajectory-failure evidence;
3. EVAL2 non-finite target prediction -> authenticated trajectory-failure evidence;
4. one failed seed makes that candidate non-comparable under the paired-seed contract;
5. enough remaining candidates -> normal survivor/finalist progression;
6. too few comparable candidates at epoch 3 -> typed terminal state;
7. too few comparable candidates at epoch 10 -> typed terminal state;
8. too few comparable finalists at epoch 30 -> typed terminal state;
9. typed terminal state survives serialization/restart with identical failure provenance;
10. forged failure code, run digest, candidate digest, stage, seed, or execution/evaluation provenance fails semantic validation;
11. generic non-zero exit does **not** become scientific target-size failure evidence;
12. timeout/interruption/OOM/launch/input/schema/lineage failure does **not** become scientific target-size failure evidence;
13. successful 3 -> 10 -> 30 exact checkpoint/optimizer/RNG continuation remains unchanged;
14. domain-local final/CV `R_d[:N]` membership remains unchanged;
15. fixed-ceiling nonconvergence remains unchanged and never invokes rescue;
16. replay diagnostic changes cannot change target-size ranking under fixed target evidence;
17. architecture dependency-graph validation passes after replay-edge correction;
18. focused target-size, TRAIN2 execution, EVAL2, and architecture tests pass with the supplied dependency bundle.

Prefer direct product-path fixtures over source-string inspection. Retain source/topology guards only for forbidden dependency reintroduction.

**Gate acceptance:**

- Focused tests pass.
- Target-size study round-trip/restart tests pass.
- No regression in existing TRAIN2 execution/restart tests.
- No active v5 route through legacy ladder/migration/rescue machinery.
- Architecture/specification and implementation describe the same current behavior.

## Performance and resource constraints

This closure should be computationally neutral in normal successful campaigns.

- Finite-state validation must be fused with state already cloned/visited at TRAIN2 persistence where possible; do not add a second full checkpoint serialization or model inference pass.
- Failure records remain small metadata objects.
- Do not retain large stderr/stdout content in scientific records; bind existing immutable log digests/attempt identities instead.
- Do not alter training concurrency, seed cardinality, candidate cardinality, MVQUAL2 backend, DATA7 materialization, or checkpoint persistence frequency.
- No GPU qualification is required for this local semantic closure; final consolidated GPU qualification remains deferred to the final release package.

## Non-goals

This workplan does not authorize:

- target sizes outside the fixed eight;
- rescue/adaptive target-size generation;
- held-out CV feedback into target-size selection;
- replay-retention or physical/deployment gates inside the target-size ranking;
- a broad global execution-error taxonomy;
- treating OOM/resource exhaustion as scientific numerical invalidity;
- fuzzy stderr parsing as scientific evidence;
- migration of ambiguous old target-size failure records into the new schema;
- changes to the 3/10/30 fidelity schedule, paired-seed authority, equivalence widths, or 16384 ceiling;
- unrelated campaign cleanup.

## Genuine redesign triggers

Return to software design only if implementation demonstrates one of the following:

1. a candidate-specific numerical failure cannot be positively distinguished from infrastructure/programming failure without invasive MACE changes that materially compromise maintainability or portability;
2. preserving exact paired-seed comparison after a candidate failure requires changing the current scientific pairing policy rather than merely marking the candidate non-comparable;
3. a truthful failure record requires product-scale duplicated state or materially changes TRAIN2 persistence cost;
4. downstream scientific requirements actually require replay or held-out evidence to control target-size choice;
5. the fixed-eight/3-10-30 architecture itself becomes invalid.

Ordinary schema advancement, controller refactoring, test fixture work, or documentation correction is not a redesign trigger.

## Closeout

When all gates pass:

1. update the target-size specification and architecture fragments to the accepted current structure;
2. rebuild the consolidated MLFF architecture manual and dependency graph outputs required by repository documentation policy;
3. record the implementation chronology in the next MLFF architecture revision/history entry;
4. store focused qualification evidence in the normal audit/qualification location if the repository's release process requires it;
5. move this plan from `workplans/active/` to `workplans/archive/`;
6. declare Target Size v5 architecturally clean only after the direct campaign-path numerical-failure regression passes.

## Completion criterion

The closure is complete when the mechanically demonstrated production behavior is:

```text
MVQUAL2-qualified fixed sizes
  -> exact paired TRAIN2 stage population
       each (size, seed) = successful endpoint OR authenticated scientific failure
  -> compare only complete paired successful candidates
  -> enough comparable candidates: continue normal 3/10/30 funnel
     otherwise: insufficient_comparable_candidates
  -> selected N remains immutable
  -> held-out validation begins only afterward
```

with no fabricated endpoint evidence, no swallowed input/lineage/programming failure, no replay ranking authority, no rescue topology, and no second target-membership selector.
