---
kind: abstraction-concretization-change-plan
protocol_version: 6.3.0
status: proposed
branch: fix/mlff-cv-competence-threshold-separation
baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
highest_affected_domain: D1
review_state: final-review-pass-after-amendment
---

# MLFF CV Competence Threshold Separation Workplan

## 0. Final review disposition and scope

Final independent workplan review is **PASS after amendment**. No active Serious Challenge remains in the workplan itself. The final review closed two remaining concretization/lifecycle gaps:

1. the role-effective checkpoint-admissibility policy must be bound consistently by the per-run `TrainingProtocolIdentity` as well as by EVAL2; EVAL2-only provenance would permit a hidden stale target ceiling in TRAIN2 protocol ancestry; and
2. the active-workplan index must advertise this plan rather than continuing to state that no active MLFF post-selection workplan exists.

The requested change remains narrow. Foundation post-selection cross-validation (CV) should determine whether the frozen foundation-adaptation method reaches a clearly competent regime consistently on held-out development evidence without forcing every disposable fold model through the late slow-convergence regime required for fresh-production checkpoint quality.

The current foundation path (`naive_fine_tuning` and `multihead_replay`) uses one target-force RMSE ceiling, nominally `0.030 eV/angstrom`, for both CV checkpoint admissibility and final-production checkpoint admissibility. The target-bearing `CheckpointAdmissibilityPolicy` digest is also embedded in `PostSelectionMethodIdentity`, so a role-specific quality criterion is represented as shared method identity.

The stakeholder recalls prior learning curves with rapid initial target-force error reduction followed by markedly slower convergence through roughly the `40-20 meV/angstrom` regime. The existing `30 meV/angstrom` production criterion intentionally lies inside that slow regime. This recollection is the stakeholder-authorized calibration premise for this cycle; it is **not** represented as newly recovered repository evidence. Applicable contradictory evidence reopens D1/D2.

Cycle-scoped target values are:

```text
foundation CV checkpoint competence ceiling       = 0.045 eV/angstrom = 45 meV/angstrom
foundation CV default held-out force-RMSE ceiling = 0.045 eV/angstrom = 45 meV/angstrom
foundation production checkpoint quality ceiling  = 0.030 eV/angstrom = 30 meV/angstrom
```

The `30 meV/angstrom` production value is checkpoint/model-control evidence on the protected common target monitor. It is not final external adequacy, a locked test, or release qualification. Those downstream roles remain separate.

This change is specific to restored **foundation adaptation**. P5 `scratch` remains separately governed and retains its pre-change target-threshold/default semantics, currently `0.030 eV/angstrom`, unless separately reopened.

## 1. Outcome and authority

### Protected stakeholder outcome

Remove the accidental production-threshold coupling that makes foundation CV pay the late-convergence cost of the production criterion. Foundation CV may use a deliberately shorter **fixed** horizon when that horizon is sufficient for all required fold/seed positions to reach the competent regime. Fresh production retains the stricter `30 meV/angstrom` target checkpoint criterion and downstream release qualification remains unchanged.

This cycle does not claim that a threshold edit alone reduces runtime, does not introduce threshold-driven early stopping, and does not choose a new universal CV epoch default without evidence.

### Earliest affected semantic domain

**D1 scientific formulation.** Current D1 says post-selection CV asks whether the complete frozen foundation-adaptation method performs acceptably on held-out evidence and that final production uses the same shared foundation-adaptation/checkpoint method validated by CV. Once the target checkpoint ceiling intentionally differs by role, that wording is too broad.

The D1 correction is:

- CV validates the **shared foundation-adaptation method** under a CV competence policy;
- CV competence and fresh-production checkpoint quality are distinct role-policy claims over that shared method;
- for this cycle, CV consistency means every required fold/seed independently reaches the CV checkpoint-competence predicate and passes its held-out predicate; cross-fold dispersion remains diagnostic-only; and
- neither CV nor the common monitor becomes downstream release qualification.

D2 owns exact numerical predicates, units, boundaries and equivalence semantics. D3 owns the identity/ownership graph and persistence/currentness boundaries. D4 owns exact schemas, resolvers, configuration defaults, protocol/evaluation construction, recovery and runtime realization.

### Accepted baseline and current owners

Accepted project baseline remains `8553ebe9ed86b24dfe910c9e43acc6230d3ece90` on `main`.

Current relevant owners include:

- D1: `docs/methods/mlff_scientific_method.md`
- D2: `docs/methods/mlff_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data_architecture.md` and `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- D4 foundation-P5 contract: `docs/specs/training_data/mlff_post_selection_p5_spec.md`
- campaign/CLI configuration contract: `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md`
- method/role policy resolution: `mdstats/training_data/post_selection_identity.py`
- generic checkpoint policy: `mdstats/training_data/train2_policy.py`
- per-run TRAIN2 protocol identity: `mdstats/training_data/protocol.py`
- TRAIN2 runtime realization: `mdstats/training_data/train2_runtime.py` and post-selection protocol/runtime construction
- EVAL2 plan/candidate evidence: `mdstats/training_data/eval2.py`
- CV plan/run ancestry: `mdstats/training_data/post_selection_cv_plan.py`
- CV fold/campaign acceptance: `mdstats/training_data/post_selection_cv_acceptance.py`
- final-production plan/run ancestry: `mdstats/training_data/post_selection_production.py`
- real CV/final orchestration and recovery: `mdstats/training_data/campaign_post_selection_runtime.py`

Current D1/D2 front matter still describes the just-merged restoration as pending repository integration. Because those files are directly amended in this cycle, reconcile that stale authority-state metadata to the integrated baseline rather than copying it forward.

### Proposed authority and human state

Stakeholder direction authorizes drafting the following proposed authority:

- foundation CV competence is distinct from production checkpoint quality;
- current foundation-CV checkpoint competence is `45 meV/angstrom` target-force RMSE;
- current default foundation held-out target-force acceptance is `45 meV/angstrom`;
- current foundation-production checkpoint quality remains `30 meV/angstrom`;
- role target ceilings are not shared `PostSelectionMethodIdentity` fields;
- replay retention and other genuinely shared method/admissibility constraints remain shared; and
- P5 scratch remains unchanged.

D1/D2 edits remain proposed until independent falsification/review and required stakeholder ratification of the assembled authority revision are complete.

## 2. Governing contract

### Invariants

1. **Foundation-only threshold revision.** `45 meV/angstrom` applies to `naive_fine_tuning` and `multihead_replay` CV, not globally to scratch or generic TRAIN2/EVAL2.
2. **Production target criterion unchanged.** Fresh foundation production retains `30 meV/angstrom` target-force checkpoint/model-control quality.
3. **CV competence is role-specific.** Foundation CV checkpoint target competence is `45 meV/angstrom`; default held-out target-force-RMSE acceptance is also `45 meV/angstrom`.
4. **Consistency is conjunctive.** Every required fold/seed must pass its own competence and held-out predicates. Mean performance cannot rescue a failure. Cross-fold dispersion remains diagnostic-only.
5. **Evidence roles remain distinct.** Common-monitor and held-out predicates are different evaluations on different evidence. Equal numeric ceilings never permit substitution or leakage.
6. **All required folds/seeds remain mandatory.** Missing, failed or rejected required positions are not discarded.
7. **Replay retention remains shared and unchanged.** Replay-degradation budget, authenticated TRUE_DFT evidence and zero replay ranking credit are unchanged and are not role-duplicated.
8. **Other hard gates remain shared and unchanged.** Finite-metric, identity, composition-transfer, provenance, physical/integrity and other current failures remain hard failures.
9. **Held-out labels remain evaluation-only.** They cannot supply gradients, fit E0/preprocessing, select checkpoints, construct the common monitor or influence model control.
10. **Common-monitor semantics remain unchanged.** One protected campaign-common exact monitor remains external to every fold and is reused by foundation CV and fresh production.
11. **TRAIN2 remains fixed-budget.** No performance-driven termination or threshold early stopping is introduced.
12. **CV horizon remains independently controllable.** Existing frozen/design CV horizon controls remain the mechanism for shortening CV. No new optimizer schedule or automatic stopping rule is introduced.
13. **Frozen target selection remains upstream.** This threshold cutover does not alter `N`, `T_selected`, target order, P1/P2/P3 evidence or the frozen `(N, CV horizon, production horizon)` design.
14. **Role thresholds are authenticated before work.** The effective target ceiling must be resolved into durable role-policy ancestry before training/checkpoint evaluation. A runtime-only `if role == ...` switch is insufficient authority.
15. **Shared method identity excludes role-only target ceilings after cutover.** It continues to bind foundation method, optimizer/loss/exposure/preparation, checkpoint-selection semantics and genuinely shared replay/physical/integrity constraints.
16. **One-time identity cutover is explicit.** Removing the old target-bearing admissibility digest from the shared method may require a new `PostSelectionMethodIdentity` schema/generation and may stale existing P5 CV/final descendants once. That is a fail-closed representation cutover, not a relaxation of production semantics.
17. **Steady-state invalidation is minimal after cutover.** A CV-only target-ceiling change moves CV policy/evidence, not the shared method or production policy. A production-only ceiling change moves production policy, not the shared method or otherwise applicable CV evidence. A genuinely shared replay/physical/method change moves shared method identity and stales both roles.
18. **One role-effective checkpoint policy governs a run.** Shared gates plus the current role target ceiling resolve to one effective `CheckpointAdmissibilityPolicy` (or equivalent one-owner policy) before run construction.
19. **TRAIN2 protocol ancestry binds that effective policy.** The per-run `TrainingProtocolIdentity` must serialize/bind the exact effective checkpoint-admissibility policy used by the run. Foundation CV and production may therefore have different per-run training-protocol digests while sharing one `PostSelectionMethodIdentity`.
20. **EVAL2 ancestry binds the same effective policy.** The EVAL2 evaluation plan/evidence must bind the exact effective admissibility-policy digest used by its corresponding TRAIN2 protocol. For one run, the TRAIN2-embedded policy digest and EVAL2 `admissibility_policy_digest` must agree exactly.
21. **Recovery never reinterprets completed evidence.** Recovery reauthenticates role policy, TRAIN2 protocol identity, EVAL2 plan and candidate evidence. It does not recompute a stored numeric metric against a newly resolved ceiling and call old evidence current.
22. **No hidden 30-meV CV fallback.** A healthy foundation-CV checkpoint at `42 meV/angstrom` cannot fail because a production-only `30 meV/angstrom` ceiling survives in method, TRAIN2 or EVAL2 ancestry.
23. **No global-threshold collateral change.** Non-foundation consumers of `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, generic checkpoint policy, P3 or historical/generic TRAIN2/EVAL2 retain accepted behavior unless direct dependency analysis independently requires reconciliation. Do not globally rewrite that key to `0.045`.
24. **Metric units cannot be aliased.** `[post_selection.cv].acceptance_maximum` is dimensioned by `acceptance_metric`; an energy/quantile/species threshold cannot become the target-force checkpoint ceiling.
25. **Historical/current state fails closed.** Old shared-30 method/policy/protocol records may remain readable as history but cannot authorize new role-separated work by silent translation or compatibility wrapper.
26. **No silent configuration rewrite.** Existing explicit `acceptance_maximum = 0.030` remains explicit `0.030`. New/current foundation defaults may expose `0.045`; operators may explicitly adopt the new policy and currentness follows identity rules.
27. **Downstream qualification remains separate.** Neither `45` CV nor `30` production-monitor criteria become external/locked/release adequacy.

### Cycle-scoped decisions

```text
foundation CV checkpoint target-force competence ceiling = 0.045 eV/angstrom
foundation CV default outer metric                        = target_force_rmse_ev_per_angstrom
foundation CV default outer acceptance ceiling            = 0.045 eV/angstrom
foundation production checkpoint target ceiling           = 0.030 eV/angstrom
P5 scratch default checkpoint/outer target behavior       = unchanged (currently 0.030 eV/angstrom)
CV aggregation                                             = all_required_folds_and_variants
CV dispersion policy                                      = diagnostic_only
TRAIN2 termination                                         = fixed budget
```

These are current cycle policies, not universal constants for all training modes.

### Delegated D3/D4 space

Use the smallest coherent representation. Prefer narrowing the current over-broad owner over adding wrappers, shadow registries, duplicate checkpoint engines, synchronized thresholds or compatibility shims.

The generic `CheckpointAdmissibilityPolicy` may remain if instantiated cleanly per role. The shared method may bind a projection/digest of only genuinely shared checkpoint constraints rather than the full target-bearing effective policy. Exact class/helper layout remains delegated.

Reuse current ancestry seams. CV/final run plans already bind role-policy digests; `TrainingProtocolIdentity` already embeds the concrete checkpoint-admissibility policy; EVAL2 already carries `admissibility_policy_digest`. These should be made coherent rather than supplemented with duplicate role fields on every checkpoint record. Advance a schema only when that object's serialized payload or meaning actually changes.

### Non-goals

This cycle does not:

- change scratch thresholds/method;
- relax the `30 meV/angstrom` foundation-production target criterion;
- change common-monitor membership, sampler or cardinality;
- change fold construction/count/seed/aggregation/purge semantics;
- promote dispersion into a hard gate;
- change UniversalLoss, exposure, replay source/split, E0/transfer or optimizer semantics;
- change P1/P2/P3 target-size semantics;
- add threshold-driven early stopping;
- select a new universal CV epoch default;
- treat the common monitor as release qualification;
- reinterpret historical pass/fail outcomes solely by threshold monotonicity; or
- globally redesign generic TRAIN2/EVAL2 when P5 role-specific rewiring suffices.

## 3. Abstraction handoff, identity and affected surface

### D1 -> D2 handoff

D2 must preserve:

- foundation CV validates the shared adaptation method under role-specific competence policy, not production-level late-convergence quality;
- current CV consistency is all required fold/seed positions satisfying current predicates, not a new hard dispersion threshold;
- fresh production uses the same shared adaptation method but a stricter role-specific target checkpoint criterion;
- common-monitor and held-out evidence remain separate; and
- downstream release qualification remains distinct.

The `45 meV/angstrom` choice is a stakeholder-authorized calibration based on recalled fast-to-slow convergence behavior. Do not fabricate a repository study or confidence interval. Applicable contradictory evidence reopens D1/D2 rather than causing downstream threshold widening.

### D2 -> D3 ownership handoff

The intended semantic graph is:

```text
PostSelectionMethodIdentity
  owns shared foundation adaptation method
  owns shared optimizer/loss/exposure/preparation
  owns shared checkpoint-selection semantics
  owns shared replay/physical/integrity constraint semantics
  excludes CV-only and production-only target-force ceilings

CvValidationPolicyIdentity
  owns CV geometry/budget/seeds/aggregation/dispersion
  owns/reconstructs foundation-CV checkpoint target competence
  owns outer held-out metric/threshold

FinalProductionPolicyIdentity
  owns production horizon/seeds/publication policy
  owns/reconstructs foundation-production target checkpoint quality

shared constraints + role target policy
  -> one effective CheckpointAdmissibilityPolicy
  -> per-run TrainingProtocolIdentity binds that full effective policy
  -> TRAIN2 runtime/checkpoint trajectory
  -> EVAL2 evaluation plan binds the same effective policy digest
  -> candidate classification/evidence
```

Equivalent decomposition is allowed only if the same ownership/invalidation graph is reconstructable without duplicated truth.

Current code violates this target graph because `resolve_post_selection_method_policies()` constructs one target-bearing policy from global `[acceptance]`, `resolve_post_selection_method_identity()` binds that full digest as shared method identity, `TrainingProtocolIdentity` serializes the full policy, and current runtime reaches the same method-level policy for both CV and production. The repair must remove coupling at the owner and then propagate one role-effective policy consistently through protocol construction and EVAL2.

### One-time cutover versus steady-state invalidation

Do not conflate:

1. **This migration:** a `PostSelectionMethodIdentity` schema/field-meaning change may stale old P5 descendants even when production still uses `0.030`. Preserve unaffected upstream/source/cache/common-monitor evidence whose own identities remain valid.
2. **Post-cutover steady state:** future role-only threshold edits must not move shared method identity or the opposite role policy.

Do not invent compatibility translation solely to preserve old P5 authorization across the cutover.

### Acceptance-metric dimensionality

Outer CV acceptance supports multiple metrics. Checkpoint competence remains specifically target-force RMSE. Default foundation outer acceptance is target-force RMSE at `0.045`; alternate outer metrics keep their own units/thresholds and never supply the checkpoint target-force ceiling. The effective checkpoint ceiling must be reconstructable independently whenever the outer metric is not target-force RMSE.

A second user-visible knob is not required merely for symmetry. A fixed current role-policy value is acceptable if identity-bound. If a configurable checkpoint ceiling is needed, place it on the existing role-policy surface rather than creating a second threshold subsystem.

### Foundation versus scratch

The current CV resolver is mode-agnostic, so simply changing its default from `0.030` to `0.045` would change scratch. Gate C/D must make effective resolution method-aware, or equivalently compose shared method + role policy, without creating duplicate policy resolvers. A default scratch result at `42 meV/angstrom` must still fail its pre-change criterion.

### Materially dependent descendants

Review/update where actually implicated:

- `docs/methods/mlff_scientific_method.md`
- `docs/methods/mlff_numerical_algorithmic_method.md`
- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- `docs/specs/training_data/mlff_post_selection_p5_spec.md`
- `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md`
- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/protocol.py`
- `mdstats/training_data/post_selection_cv_plan.py` only if its own role-policy payload/meaning changes
- `mdstats/training_data/post_selection_production.py` only if its own role-policy payload/meaning changes
- `mdstats/training_data/campaign_post_selection_runtime.py`
- `mdstats/training_data/post_selection_execution.py` and/or the canonical TRAIN2 protocol construction path
- `mdstats/training_data/train2_runtime.py` only where protocol-policy authentication requires it
- `mdstats/training_data/post_selection_cv_acceptance.py`
- `mdstats/training_data/eval2.py`/EVAL2 construction/recovery only as needed to bind/authenticate the existing effective-admissibility seam
- `mdstats/training_data/train2_policy.py` only if clean composition cannot be achieved without changing the generic type
- currentness/recovery/store paths that compare method, role-policy, training-protocol or EVAL2 ancestry
- `campaign.toml.example`
- generated `init` template in `mdstats/training_data/_campaign_cli_core.py`
- configuration validation/default resolution
- `docs/guides/mlff_campaign_cli_user_guide.md`
- `workplans/active/README.md` for current branch-local lifecycle discoverability
- operator-visible manifests/logs/status where threshold provenance is shown
- affected identity, protocol, no-admissible, recovery, CLI/spec-generation and assembled CV->production tests.

This is a lower bound, not a mandate to churn every listed file.

### Unaffected siblings/evidence

Preserve P1/P2 neutral evidence/relations/orders; P3 screen/reducer semantics; frozen selected target membership/design; common-monitor selection/membership/separation when its identity is unchanged; CV fold/purge geometry; replay source/split/caches/metric definition; foundation checkpoint/head; residual-E0/transfer; UniversalLoss/exposure/optimizer semantics; production horizon semantics; P5 scratch semantics; generic TRAIN2/EVAL2 consumers not directly dependent on this role split; and still-valid immutable source/cache/evidence products whose owning identities did not move.

## 4. Historical Applicability Set

Project engineering memory is active because this cycle changes mature P5 identity/currentness machinery.

```yaml
pem_basis:
  accepted_project_state: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-002
    disposition: APPLICABLE
    reason: Recovery/currentness must not admit historical policy/protocol/checkpoint state as current after the cutover.
  - id: SP-001
    disposition: APPLICABLE
    reason: Narrow/rewire the over-broad owner rather than adding synchronized threshold paths.
  - id: SP-002
    disposition: APPLICABLE
    reason: Method/role/protocol/effective-admissibility boundaries must fail closed.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve unaffected immutable P1/P2/P3/replay/source/common-monitor evidence.
  - id: SP-004
    disposition: APPLICABLE
    reason: Acceptance must exercise the real CV -> TRAIN2 protocol -> EVAL2 -> held-out verdict -> production authorization path.
```

**PEM basis health:** `REVIEW_REQUIRED` for metadata provenance, not a blocker to the bounded lessons above. The project-selected publication at `4eabe2...` still self-declares an older `b65fa3b...` basis and the then-live NT-001 state. Later branch-local state at `b5d101d8f73d3efd63ef4e70b3913e7d281406ce` reconciled that basis and the associated repair later closed PASS, but this workplan does not self-promote that candidate state into accepted PEM. Use only materially verified lessons also supported by direct repository history; do not infer absence of another lesson from partial/stale metadata. Refresh the HAS if project-governed accepted memory advances before closeout.

The preceding post-selection restoration preserved target/replay thresholds because threshold revision was outside its scope. That historical constraint is not evidence that CV and production ceilings must be identical. Retired CV specifications may support rationale but do not govern current D1/D2.

## 5. Evidence and falsification

### Reverse-semantic verification question

From persisted identities/plans/protocols/evidence and real executable behavior, without this workplan, can an independent reviewer reconstruct:

```text
shared foundation method: same CV and production method
foundation CV checkpoint competence: 45 meV/angstrom target-force RMSE
foundation CV default held-out force-RMSE pass: 45 meV/angstrom
foundation production checkpoint quality: 30 meV/angstrom target-force RMSE
scratch target behavior: unchanged
CV consistency: every required fold/seed passes; dispersion diagnostic only
shared replay/physical/integrity gates: unchanged
TRAIN2 protocol: binds exact role-effective admissibility policy
EVAL2 plan: binds the same role-effective admissibility-policy digest
termination: fixed budget
release qualification: downstream and unchanged
```

If not, the concretization is inadequate.

### Required falsification cases

At minimum demonstrate:

1. foundation CV checkpoint target RMSE `~0.042` is admissible when all other gates pass;
2. its held-out target-force RMSE `~0.042` passes under default foundation CV;
3. CV equality `0.045` passes and a representable just-above value fails;
4. foundation production target RMSE `~0.042` remains inadmissible under `0.030`;
5. production equality `0.030` passes and a just-above value fails;
6. default scratch `~0.042` does not begin passing because foundation CV changed;
7. common-monitor and held-out evidence remain independent despite equal CV numeric ceilings;
8. replay degradation, TRUE_DFT requirement, physical/integrity gates and replay ranking semantics remain unchanged;
9. all candidates above `0.045` or failing another mandatory gate still produce the existing no-admissible fold rejection with no held-out evaluation;
10. one failing required fold/seed rejects the campaign even if aggregate mean is below `0.045`; dispersion stays diagnostic-only;
11. a supported non-target-force outer metric cannot donate its threshold to target-force checkpoint competence;
12. P1/P2/P3 and frozen `(N, CV horizon, production horizon)` authority are not recomputed by the cutover;
13. pre-cutover shared-method identity cannot authorize current descendants under the new schema/generation;
14. post-cutover CV-only target-ceiling perturbation moves CV policy/evidence but not shared method/production policy;
15. post-cutover production-only ceiling perturbation moves production policy but not shared method/applicable CV method evidence;
16. replay degradation or another truly shared gate still moves shared method identity and dependent CV/production ancestry;
17. CV and production `TrainingProtocolIdentity` records carry their respective effective target ceilings while referencing the same shared post-selection method identity at the parent plan level;
18. for each run, the checkpoint-admissibility digest embedded in `TrainingProtocolIdentity` exactly matches EVAL2 `admissibility_policy_digest`; a mismatch fails closed before candidate evidence is accepted;
19. CV and production EVAL2 plans therefore bind different effective admissibility-policy digests when the role ceilings differ;
20. completed candidate/protocol evidence from one effective admissibility policy cannot be reused under another by merely recomparing stored metrics;
21. no redundant role/evidence authority is added to checkpoint records when existing protocol/EVAL2 ancestry already proves the policy;
22. readable old method/policy/protocol/CV records cannot silently authorize current work;
23. newly generated foundation configuration resolves default outer CV `0.045` and production target `0.030`, while scratch defaults remain pre-change;
24. `campaign.toml.example`, generated `init` text, CLI specification and user guide agree on the public configuration contract;
25. an existing explicit `[post_selection.cv].acceptance_maximum = 0.030` is not silently rewritten;
26. CV still consumes the configured fixed horizon rather than stopping when `0.045` is first crossed;
27. real `cross-validate` -> persisted CV verdict -> `train-production` integration authenticates shared method, role policies, TRAIN2 protocol and EVAL2 policy ancestry at real owners; and
28. current D1/D2/D3/D4 documents no longer claim an identical role target ceiling as part of the shared checkpoint method.

### Calibration adequacy premise

The `45 meV/angstrom` choice is accepted for this cycle from stakeholder-provided historical learning-curve recollection: rapid early convergence, pronounced slowdown across roughly `40-20 meV/angstrom`, with `30 meV/angstrom` chosen as a production criterion inside that slow region. `45 meV/angstrom` is intentionally just above it.

No new calibration campaign is required merely to implement this directed narrow change. Reopen D1/D2 if applicable evidence shows healthy foundation folds routinely plateau above `45`, shows no relevant knee, or shows the remembered curve applies only to scratch/different training semantics.

### Strongest Challenge

Attempt to establish whether:

1. foundation CV's old `30 meV/angstrom` gate is the only quantitative final-product/release assurance;
2. current code/docs conflate the production common-monitor gate with locked/downstream qualification; or
3. target ceiling is scientifically part of the shared training method rather than role-specific evidence policy.

If any is established, stop the local split and reopen D1. Do not compensate in D3/D4.

## 6. Concretization sequence

### Gate A — D1 authority reconciliation

Amend `docs/methods/mlff_scientific_method.md` narrowly:

- separate shared foundation-adaptation method from CV competence and production checkpoint-quality policies;
- define consistency as all-required-fold/seed competence plus held-out success, with dispersion diagnostic-only;
- establish `45 meV/angstrom` as current foundation CV checkpoint/default held-out target-force criterion and retain `30 meV/angstrom` fresh-production checkpoint quality;
- preserve monitor/held-out separation, leakage prohibitions, replay semantics and downstream qualification;
- keep scratch separately governed;
- revise “same shared checkpoint method” prose so it means common monitor/selection/evaluation mechanics, not identical role ceiling; and
- reconcile stale restoration-integration metadata.

Keep calibration provenance explicit as stakeholder-authorized historical observation, not fabricated recovered evidence. Run independent D1 Challenge/Review and required stakeholder ratification before promotion to accepted-current D1.

### Gate B — D2 numerical-method reconciliation

After D1 acceptance, amend `docs/methods/mlff_numerical_algorithmic_method.md` only as needed to make the predicates reconstructable:

- foundation CV checkpoint target-force predicate `<=0.045 eV/angstrom`;
- default held-out target-force predicate `<=0.045 eV/angstrom`;
- foundation production checkpoint predicate `<=0.030 eV/angstrom`;
- distinct monitor/held-out evidence despite equal CV threshold;
- all-fold/all-seed aggregation;
- diagnostic-only dispersion;
- fixed-budget training;
- dimensional separation for alternate outer metrics; and
- unchanged scratch behavior.

Revise “same checkpoint method” language so roles share selection/evaluation mechanics and common monitor while consuming different role target-ceiling policies. Run independent D2 review with boundary, unit, mode, role and stale-evidence counterexamples.

### Gate C — D3 ownership/currentness cutover

Reconstruct all current identity consumers before editing. Required end state:

- shared `PostSelectionMethodIdentity` excludes role target ceilings but retains genuine shared method/replay/physical/integrity semantics;
- `CvValidationPolicyIdentity` owns/reconstructs the foundation-CV checkpoint target ceiling plus outer acceptance policy;
- `FinalProductionPolicyIdentity` owns/reconstructs the production checkpoint target ceiling;
- shared constraints + role policy deterministically produce one effective checkpoint-admissibility policy before run construction;
- the per-run `TrainingProtocolIdentity` binds that exact effective policy;
- the corresponding EVAL2 plan binds the same policy digest;
- protocol/EVAL2 recovery reauthenticates exact policy ancestry instead of reinterpreting old metrics;
- scratch and generic TRAIN2/EVAL2 retain accepted behavior; and
- P1/P2/P3/frozen-selection/common-monitor evidence is preserved where its own identity did not change.

Treat migration and steady state separately. Advance `PostSelectionMethodIdentity` schema/generation if its field meaning changes; that one-time cutover may stale old P5 CV/final descendants. After cutover, role-only threshold changes must not move the shared method.

Advance CV/final role-policy schemas if their serialized payload/meaning changes. Do not advance CV/final plan, `TrainingProtocolIdentity`, EVAL2 or checkpoint-record schemas merely because an ancestor/policy digest value changes; advance them only if their own representation/meaning changes. `TrainingProtocolIdentity` already has a checkpoint-admissibility field and EVAL2 already has an admissibility digest seam, so prefer rewiring those owners over adding another representation.

Do not globally change `[acceptance].maximum_target_force_rmse_ev_per_angstrom` to `0.045`; it has scratch/generic/historical consumers. Foundation CV needs an identity-bound effective `0.045` role value. Foundation production may continue resolving `0.030` from the existing key only if that remains semantically faithful and does not recouple CV; otherwise place the role value on the existing production-policy surface. Add a user-visible field only when needed for unambiguous ownership.

### Gate D — D4 implementation and affected regression

Implement the minimum Gate-C concretization.

Generated/example foundation defaults expose outer CV acceptance:

```toml
[post_selection.cv]
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045
```

That is only the held-out default. Foundation-CV **checkpoint** competence independently resolves to authenticated CV-role `0.045`; foundation production resolves to authenticated `0.030`.

Make default resolution method-aware without duplicate policy resolvers. Existing explicit values remain explicit. Alternate outer metrics remain dimensionally separate.

Update together:

- `campaign.toml.example`;
- generated `init` text;
- `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md`;
- parser/default/currentness behavior;
- user guide;
- P5 D4 spec;
- shared/role policy composition;
- `TrainingProtocolIdentity` construction and any protocol/runtime authentication needed so the exact role-effective policy is embedded;
- EVAL2 plan construction so its admissibility digest exactly matches the protocol's policy for the run;
- recovery/currentness, logs/manifests/status; and
- affected focused, regression and real-path integration tests.

Do not add early stopping or change the default CV horizon merely to claim speedup. GPU qualification remains deferred to the final complete release package under standing project policy.

### Gate E — assembled independent review and impact closure

Review the assembled D1-D4 candidate independently. Verify foundation/scratch isolation; D1/D2 meaning/units; one-time cutover vs steady-state invalidation; role-effective TRAIN2 and EVAL2 policy provenance/agreement/recovery; no stale-policy reinterpretation; frozen target selection/common-monitor preservation; no replay/physical/integrity weakening; no P3/generic TRAIN2 collateral change; fixed-budget behavior; generated/config/spec/guide convergence; and real CV -> production authorization.

Refresh PEM/HAS if accepted memory advances. Perform closeout learning assessment but mutate PEM only if admission criteria are met. Reconcile `workplans/active/README.md` throughout lifecycle and archive this plan only after independent assembled Review PASS and required authority acceptance.

## 7. Reopen, simplification and human triggers

Reopen D1 if CV is actually final-product/release qualification; the `45` calibration is contradicted/inapplicable; target ceiling is scientifically part of the shared method; or the change alters a broader scientific conclusion.

Reopen D2 if role predicates cannot be specified without metric/unit ambiguity; shorter fixed-horizon CV creates an unrecognized estimator/selection bias; a mode-independent target criterion is required; or the role change affects checkpoint-selection algorithm rather than only admissibility.

Reopen D3 before adding machinery if clean ownership appears to require wrappers/shadow registries/duplicate evaluators/synchronized thresholds; fail-closed currentness cannot use existing role/protocol/EVAL2 ancestry; implementation would require global generic TRAIN2/scratch changes; or one-time cutover cannot be distinguished from steady-state role invalidation.

Human ratification is required for the material D1/D2 revision before final acceptance. The Challenge targets in this plan remain mandatory at Gates A/B/E.

## 8. Impact, compatibility and history

Record semantic evolution succinctly:

- the 2026-09-14 restoration preserved target/replay thresholds because threshold revision was outside its scope;
- later review identified that target-ceiling ownership was too broad and coupled foundation CV to production late convergence;
- foundation CV checkpoint/default held-out target-force criterion becomes `45 meV/angstrom`;
- foundation production checkpoint target quality remains `30 meV/angstrom`;
- scratch remains unchanged;
- CV consistency remains all-required-fold/seed success with diagnostic dispersion; and
- the separation permits deliberately shorter fixed-horizon foundation CV without weakening production or release qualification.

Do not rewrite retired specifications as if they always contained this split.

Pre-cutover shared-method identity may become historical because it incorrectly included the role target ceiling. This one-time cutover may stale old P5 CV/final descendants while preserving unaffected upstream/source/cache/common-monitor evidence. A prior `30` pass is not automatically current under `45`; a prior `30-45` failure is not retroactively a pass. After cutover, role-only target edits obey the minimal steady-state invalidation graph. No threshold-equivalence migration layer is authorized.

## 9. Acceptance and handoff

The workplan may close only when:

- D1 separates shared foundation method, CV competence, production checkpoint quality and downstream qualification;
- D1 defines the bounded consistency claim with diagnostic-only dispersion;
- D2 owns/reconstructs exact `45`/`45`/`30 meV/angstrom` foundation predicates with correct units;
- calibration provenance remains honest;
- scratch remains unchanged;
- independent D1/D2 review and required stakeholder ratification are complete;
- post-cutover shared method no longer owns role target ceilings;
- one-time identity cutover/currentness consequences are explicit and tested;
- post-cutover role-only threshold changes have minimal exact invalidation;
- shared replay/physical/integrity changes still move shared method identity;
- foundation CV checkpoint and default held-out target-force criteria resolve to `45`;
- foundation production checkpoint quality remains `30`;
- alternate outer metrics cannot alias checkpoint target force;
- each run's `TrainingProtocolIdentity` binds the exact role-effective checkpoint-admissibility policy;
- EVAL2 binds the same effective policy digest as its run's training protocol;
- recovery reauthenticates both and does not reinterpret old candidate evidence;
- P1/P2/P3/frozen selected design and unaffected common-monitor/replay/source evidence are preserved;
- generated config, example config, CLI specification and user guide agree while explicit old config is not silently rewritten;
- TRAIN2 remains fixed-budget;
- all required folds/seeds, leakage, replay and physical/integrity constraints remain unchanged;
- real-path regression includes the `30 < RMSE <= 45` foundation CV pass/production fail, scratch preservation, dimensionality, protocol/EVAL2 policy agreement, one-time cutover, steady-state invalidation and recovery cases;
- assembled `cross-validate` -> persisted acceptance -> `train-production` passes under authenticated role policies/protocols;
- active-workplan lifecycle/index and affected documentation/history are reconciled; and
- PEM basis-health/closeout obligations are reconciled.

A hidden shared `30 meV/angstrom` CV gate; global `45` scratch change; runtime-only role switch; missing role-effective TRAIN2 or EVAL2 policy provenance; disagreement between TRAIN2 and EVAL2 policy digests; metric-unit aliasing; stale-schema reinterpretation; silent old-evidence reclassification; contradiction between one-time and steady-state invalidation; production-threshold relaxation; downstream qualification weakening; or unreviewed final-qualification dependence is a blocking **No-Pass**.
