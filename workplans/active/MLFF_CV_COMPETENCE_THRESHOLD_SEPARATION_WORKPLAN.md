---
kind: abstraction-concretization-change-plan
protocol_version: 6.3.0
status: proposed
branch: fix/mlff-cv-competence-threshold-separation
baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
highest_affected_domain: D1
review_state: amended-after-second-cross-domain-review
---

# MLFF CV Competence Threshold Separation Workplan

## 0. Review disposition and scope

Second independent workplan review is **PASS after amendment**. The requested change remains a narrow foundation-P5 authority reconciliation: post-selection cross-validation (CV) should test whether the frozen foundation-adaptation method reaches a clearly competent regime consistently under held-out validation, without forcing every disposable fold model through the late, slow-convergence regime required for fresh production checkpoint quality.

The current foundation-model post-selection path (`naive_fine_tuning` and `multihead_replay`) uses one target-force root-mean-square error (RMSE) ceiling, nominally `0.030 eV/angstrom`, in both CV checkpoint admissibility and fresh-production checkpoint admissibility. Current code also embeds the digest of that target-bearing checkpoint-admissibility policy into `PostSelectionMethodIdentity`, so the equality is represented as shared method identity rather than role policy.

The stakeholder recalls prior learning-curve behavior in which target-force error falls rapidly initially and then slows markedly through roughly the `40-20 meV/angstrom` range. The existing `30 meV/angstrom` production criterion was chosen inside that slow-convergence regime. This recollection is the stakeholder-authorized calibration premise for this cycle; it is **not** represented here as a newly recovered or independently verified repository evidence artifact. If current applicable evidence contradicts it, the contradiction reopens D1/D2.

For the current foundation-adaptation policy, the cycle-scoped target values are:

```text
foundation CV checkpoint competence ceiling = 0.045 eV/angstrom = 45 meV/angstrom
foundation CV default held-out force-RMSE ceiling = 0.045 eV/angstrom = 45 meV/angstrom
foundation production checkpoint quality ceiling = 0.030 eV/angstrom = 30 meV/angstrom
```

The production value is a checkpoint/model-control criterion on the protected common target monitor. It is not final external adequacy, locked-test qualification, or release qualification. Those downstream roles remain separate.

This change is specific to restored **foundation adaptation**. P5 `scratch` has a separately accepted method and keeps its pre-change threshold/default semantics. The current default scratch target checkpoint and target-force outer-CV ceiling remain `0.030 eV/angstrom` unless separately and explicitly governed otherwise.

## 1. Outcome and authority

### Protected stakeholder outcome

Remove the accidental production-threshold coupling that makes foundation CV pay the late-convergence cost of the production criterion. Foundation CV should be able to use a shorter **fixed** horizon when that horizon is sufficient for every required fold/seed to enter the competent regime, while fresh production retains the stricter `30 meV/angstrom` checkpoint criterion and downstream release qualification remains unchanged.

This cycle enables economical shorter-horizon CV configurations. It does not claim that changing a threshold alone reduces runtime, does not add threshold-driven early stopping, and does not choose a new universal default CV horizon without evidence.

### Highest affected semantic domain

**D1 scientific formulation.** Current D1 says post-selection CV asks whether the complete frozen foundation-adaptation method “performs acceptably” on held-out evidence and says fresh production uses the same shared foundation-adaptation/checkpoint method validated by CV. That wording is insufficient once the target checkpoint ceiling is intentionally role-specific.

The narrow D1 correction is:

- the **shared foundation-adaptation method** is what CV validates;
- CV competence and production checkpoint quality are distinct role-policy claims over that shared method;
- for this cycle, CV consistency means **every required fold/seed independently reaches the CV competence predicate and passes its held-out predicate**; low cross-fold dispersion is useful diagnostic evidence but is not itself a hard acceptance estimand in this change; and
- neither CV nor the common monitor becomes downstream release qualification.

D2 owns exact predicate, units, boundary and numerical-equivalence semantics. D3 owns the identity/ownership graph that separates the shared method from role policy. D4 owns exact schemas, resolvers, configuration defaults, persistence/currentness, recovery and runtime realization.

### Accepted baseline and current owners

Accepted project baseline: `8553ebe9ed86b24dfe910c9e43acc6230d3ece90` (`main`, merged post-selection restoration).

Current normative and executable owners include:

- D1: `docs/methods/mlff_scientific_method.md`
- D2: `docs/methods/mlff_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data_architecture.md` and `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- D4 foundation-P5 contract: `docs/specs/training_data/mlff_post_selection_p5_spec.md`
- method/role policy resolution: `mdstats/training_data/post_selection_identity.py`
- generic TRAIN2 checkpoint policy: `mdstats/training_data/train2_policy.py`
- EVAL2 plan/candidate evidence: `mdstats/training_data/eval2.py`
- CV plan/run ancestry: `mdstats/training_data/post_selection_cv_plan.py`
- CV fold/campaign acceptance: `mdstats/training_data/post_selection_cv_acceptance.py`
- final-production plan/run ancestry: `mdstats/training_data/post_selection_production.py`
- real CV/final orchestration and recovery: `mdstats/training_data/campaign_post_selection_runtime.py`

The current D1/D2 front matter still describes the just-merged restoration as “pending repository integration”. Because those files are directly amended by this cycle, their authority-state metadata must be reconciled to the integrated baseline rather than copied forward stale.

### Proposed authority and human state

Stakeholder direction authorizes drafting this proposed authority:

- foundation CV competence is distinct from production checkpoint quality;
- current foundation-CV checkpoint competence is `45 meV/angstrom` target-force RMSE;
- current default foundation held-out target-force acceptance is `45 meV/angstrom`;
- current foundation-production checkpoint quality remains `30 meV/angstrom`;
- role target ceilings are not shared `PostSelectionMethodIdentity` fields;
- replay-retention and other genuinely shared method/admissibility constraints remain shared; and
- P5 scratch remains unchanged.

D1/D2 edits remain proposed until independent falsification/review and required stakeholder ratification of the assembled authority revision are complete.

## 2. Governing contract

### Invariants

1. **Foundation-only threshold revision.** `45 meV/angstrom` applies to `naive_fine_tuning` and `multihead_replay` CV, not globally to P5 scratch or generic TRAIN2/EVAL2.
2. **Production criterion unchanged.** Fresh foundation production retains the `30 meV/angstrom` target-force checkpoint/model-control ceiling.
3. **CV competence role-specific.** Foundation CV checkpoint target competence is `45 meV/angstrom`; the default held-out target-force-RMSE acceptance ceiling is also `45 meV/angstrom`.
4. **Consistency has a bounded meaning.** In this cycle, CV consistency is conjunctive success of every required fold/seed against the competence/held-out predicates. Mean performance cannot rescue a failure. Cross-fold dispersion remains diagnostic-only.
5. **Evidence roles stay separate.** The common-monitor predicate and held-out-fold predicate are different evaluations on different evidence. Equal numeric ceilings do not permit substitution or leakage.
6. **All required folds/seeds remain mandatory.** Missing, failed, or rejected required positions are not discarded to create a favorable aggregate.
7. **Replay retention remains shared and unchanged.** Replay-degradation budget, authenticated TRUE_DFT requirement, and zero replay ranking credit do not change or become role-duplicated.
8. **Physical/integrity gates remain shared and unchanged.** Finite-metric, identity, composition-transfer, provenance and other current hard failures remain hard failures.
9. **Held-out labels remain evaluation-only.** They may not supply gradients, fit E0/preprocessing, select checkpoints, construct the common monitor, or otherwise influence training/model control.
10. **Common-monitor membership/method unchanged.** One protected campaign-common exact monitor remains external to all folds and shared by foundation CV and fresh production.
11. **TRAIN2 remains fixed-budget.** No performance-driven termination or threshold early stop is introduced.
12. **CV horizon remains independently controllable.** Existing selected/design CV horizon controls remain the mechanism for a shorter test. No new optimizer schedule or automatic stopping rule is introduced.
13. **Frozen target selection remains upstream.** This threshold-role cutover does not alter `N`, `T_selected`, target order, P1/P2/P3 evidence or the operator-frozen `(N, CV horizon, production horizon)` design. It invalidates only dependent P5 state whose role/method ancestry changes.
14. **Role thresholds are authenticated before work.** The effective target ceiling must be resolved into durable role-policy ancestry before checkpoint evaluation. An unpersisted runtime `if role == ...` switch is insufficient authority.
15. **Shared method identity excludes role-only target ceilings after cutover.** The shared method continues to bind foundation method, optimizer/loss/exposure/preparation, checkpoint-selection semantics and genuinely shared replay/physical/integrity constraints, but not CV-only or production-only target ceilings.
16. **One-time identity cutover is explicit.** Removing the over-broad target-bearing admissibility digest from the shared method representation may require a new `PostSelectionMethodIdentity` schema/generation and may therefore stale existing P5 CV/final descendants once. That is a fail-closed representation/currentness cutover, not a scientific relaxation of production semantics.
17. **Steady-state invalidation is minimal after cutover.** Once the new ownership graph is current, changing only the foundation-CV target ceiling moves CV policy/evidence, not shared method or production policy. Changing only production target ceiling moves production policy, not shared method or otherwise applicable CV evidence. Changing a genuinely shared replay/physical/method gate moves shared method and stales both roles.
18. **Effective checkpoint-admissibility identity is role-bound.** EVAL2 checkpoint classification must be performed under an effective policy that combines the shared gates with the current role target ceiling, and the exact effective policy digest must be bound by EVAL2 plan/evidence ancestry and authenticated on recovery.
19. **Do not reinterpret completed checkpoint evidence under another role policy.** Recovery re-authenticates the policy that classified the candidate; it does not rerun a numeric comparison against a newly resolved ceiling and call old evidence current.
20. **No hidden 30-meV CV fallback.** A healthy foundation-CV checkpoint at `42 meV/angstrom` must not fail because a production-only `30 meV/angstrom` ceiling remains consulted on the CV path.
21. **No global-threshold collateral change.** Non-foundation consumers of `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, generic `CheckpointAdmissibilityPolicy`, P3, or other TRAIN2/EVAL2 paths retain accepted behavior unless a direct dependency is demonstrated and separately reconciled.
22. **Metric units cannot be aliased.** `[post_selection.cv].acceptance_maximum` is dimensioned by `acceptance_metric`; a supported energy/quantile/species metric threshold cannot be reused as the target-force checkpoint ceiling.
23. **Historical/current state fails closed.** Old shared-30 method/policy identities may remain readable as history, but cannot authorize new current role-separated work through silent translation or a compatibility wrapper.
24. **No silent configuration rewrite.** Existing explicit `acceptance_maximum = 0.030` remains explicit `0.030`; generated/current defaults may change to `0.045` for foundation CV and operators may explicitly adopt them. Currentness follows the resulting policy identities.
25. **Downstream qualification remains separate.** Neither the `45` CV threshold nor `30` production monitor threshold is promoted into external/locked/release adequacy.

### Cycle-scoped decisions

```text
foundation CV checkpoint target-force competence ceiling = 0.045 eV/angstrom
foundation CV default outer metric                        = target_force_rmse_ev_per_angstrom
foundation CV default outer acceptance ceiling            = 0.045 eV/angstrom
foundation production checkpoint target ceiling           = 0.030 eV/angstrom
P5 scratch default checkpoint/outer target-force behavior = unchanged (currently 0.030 eV/angstrom defaults)
CV aggregation                                             = all_required_folds_and_variants
CV dispersion policy                                      = diagnostic_only
TRAIN2 termination                                         = fixed budget
```

These values are current cycle policy, not universal constants for all training modes.

### Delegated D3/D4 space

Use the smallest coherent representation. Prefer narrowing the current over-broad owner over adding wrappers, shadow policy registries, duplicate acceptance engines, synchronized target thresholds or compatibility shims.

The generic `CheckpointAdmissibilityPolicy` execution type may remain if cleanly instantiated per role. The shared method may bind a projection/digest of only genuinely shared checkpoint constraints rather than the target-bearing full effective policy. The exact class layout is delegated.

Existing plan ancestry should be reused where sufficient: `PostSelectionCvPlan`/CV run plans already bind CV policy identity; final plans/runs already bind final-production policy identity; EVAL2 plans already contain an `admissibility_policy_digest`. Do **not** add redundant role fields to checkpoint records merely to duplicate ancestry already authenticated at the real plan/evidence owner. Advance a schema only when its serialized payload or meaning actually changes.

### Non-goals

This work does not:

- change scratch thresholds/method;
- relax the `30 meV/angstrom` foundation-production target criterion;
- change the common monitor membership, sampler or size;
- change fold construction/count/seed/aggregation/purge semantics;
- promote dispersion into a hard gate;
- change UniversalLoss, exposure, replay source/split, E0/transfer or optimizer semantics;
- change P1/P2/P3 target-size semantics;
- add threshold-driven early stopping;
- select a new universal CV epoch default;
- treat the common monitor as release qualification;
- retrofit old passes/failures as current by threshold monotonicity alone; or
- globally redesign generic TRAIN2/EVAL2 when role-specific P5 rewiring suffices.

## 3. Abstraction handoff, identity and affected surface

### D1 -> D2 handoff

D2 must preserve these scientific semantics:

- foundation CV validates the shared adaptation method under role-specific competence policy, not production-level late-convergence quality;
- current CV consistency is operationally `all required fold/seed positions satisfy the current CV predicates`, not `dispersion < new hard threshold`;
- fresh production uses the same shared adaptation method but a stricter role-specific checkpoint target criterion;
- shared monitor and held-out evidence remain separate; and
- downstream release qualification remains distinct.

The `45 meV/angstrom` value is a stakeholder-authorized calibration choice based on recalled fast-to-slow convergence behavior. Do not fabricate a repository “study” or quantitative confidence interval. If applicable repository evidence contradicts the premise, reopen D1/D2 rather than widening a threshold downstream.

### D2 -> D3 ownership handoff

The intended semantic graph is:

```text
PostSelectionMethodIdentity
  owns: shared foundation adaptation method
        shared optimizer/loss/exposure/preparation
        shared checkpoint-selection semantics
        shared replay/physical/integrity constraint semantics
        common-monitor method identity
  excludes: CV-only and production-only target-force ceilings

CvValidationPolicyIdentity
  owns: CV geometry, budget, seeds, aggregation/dispersion policy
        effective foundation-CV checkpoint target-force competence ceiling
        outer held-out acceptance metric/threshold

FinalProductionPolicyIdentity
  owns: production horizon, seeds, publication policy
        effective foundation-production target-force checkpoint ceiling

role policy + shared constraint semantics
  -> effective CheckpointAdmissibilityPolicy (or equivalent one-owner realization)
  -> EVAL2 evaluation plan binds exact effective admissibility-policy digest
  -> checkpoint candidate classification/evidence
```

Equivalent decomposition is allowed if the same authority/invalidation graph is reconstructable without duplicated truth.

Current code violates this target graph because `resolve_post_selection_method_policies()` builds one target-bearing `CheckpointAdmissibilityPolicy` from global `[acceptance]`, and `resolve_post_selection_method_identity()` binds that full policy digest into shared method identity. Runtime then uses `context.method_policies.checkpoint_admissibility` for both roles. The repair must remove that coupling at the owner, not override it at one call site.

### One-time cutover versus steady-state invalidation

Do not conflate these two cases:

1. **This migration:** if `PostSelectionMethodIdentity` changes schema/field meaning to stop binding the role target ceiling, pre-cutover P5 descendants may become stale even though the production threshold is still numerically `0.030`. That broad one-time currentness consequence is acceptable and should preserve reusable upstream/source/cache/common-monitor evidence whose own identities are unchanged.
2. **After migration:** a future CV-only target-ceiling edit must not move shared method identity or production policy; a future production-only ceiling edit must not move shared method/CV policy. This is the steady-state ownership property the cutover exists to establish.

Do not invent compatibility translation merely to preserve old P5 authorization across the identity cutover. If historical reading already exists, keep it historical; current authorization must use current identities.

### Acceptance-metric dimensionality

Outer CV acceptance currently supports multiple metrics. Therefore:

- checkpoint competence remains specifically target-force RMSE;
- default foundation outer acceptance is target-force RMSE at `0.045 eV/angstrom`;
- an alternate outer metric keeps its own units and threshold;
- a non-force outer `acceptance_maximum` cannot become the checkpoint target-force ceiling; and
- the effective checkpoint ceiling must be reconstructable independently of the outer metric whenever the outer metric is not target-force RMSE.

No second user-visible knob is required merely for symmetry. A fixed current CV-role policy value is acceptable if it is identity-bound. If a configurable checkpoint ceiling is introduced, place it on the existing CV role-policy surface and bind it there.

### Foundation versus scratch

Current P5 specification explicitly separates restored foundation adaptation from scratch. The present `CvValidationPolicyIdentity` resolver is mode-agnostic, so simply changing its default from `0.030` to `0.045` would also change scratch. Gate C/D must make resolution method-aware (or equivalently compose method + role policy) without creating a second policy resolver.

A default scratch result at `42 meV/angstrom` must still fail the pre-change target criterion unless scratch has an independent explicit accepted configuration that says otherwise.

### Materially dependent descendants

Review and update, where actually implicated:

- `docs/methods/mlff_scientific_method.md`
- `docs/methods/mlff_numerical_algorithmic_method.md`
- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- `docs/specs/training_data/mlff_post_selection_p5_spec.md`
- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/post_selection_cv_plan.py` only if role-policy payload/ancestry changes require it
- `mdstats/training_data/post_selection_production.py` only if role-policy payload/ancestry changes require it
- `mdstats/training_data/campaign_post_selection_runtime.py`
- `mdstats/training_data/post_selection_cv_acceptance.py`
- `mdstats/training_data/eval2.py`/EVAL2 construction or recovery only as needed to bind/authenticate the existing effective-admissibility digest seam
- `mdstats/training_data/train2_policy.py` only if clean policy composition cannot be achieved without changing the generic type
- relevant currentness/recovery/store paths that compare method, role-policy or EVAL2 ancestry
- `campaign.toml.example`
- generated `init` template in `mdstats/training_data/_campaign_cli_core.py`
- configuration validation/default resolution
- `docs/guides/mlff_campaign_cli_user_guide.md`
- operator-visible manifests/logs/status where threshold provenance is shown
- affected identity, no-admissible, recovery, CLI-generation and assembled CV->production tests.

This list is a lower bound, not a mandate to churn every listed file.

### Unaffected siblings/evidence

Preserve:

- P1/P2 neutral evidence, relations and orders;
- P3 target-size screening and reducer semantics;
- frozen selected target membership/design;
- common-monitor selection/membership/separation evidence if its own identity is unchanged;
- CV fold membership/purge geometry;
- replay source/split/caches and replay metric definition;
- foundation checkpoint/head identity;
- residual-E0/transfer method;
- UniversalLoss/exposure/optimizer semantics;
- production horizon semantics;
- P5 scratch method/threshold semantics;
- generic TRAIN2/EVAL2 consumers not directly dependent on this P5 role split; and
- still-valid immutable source/cache/evidence products whose owning identity did not move.

## 4. Historical Applicability Set

This cycle touches mature P5 identity/currentness and recent restoration history, so project engineering memory is active.

```yaml
pem_basis:
  accepted_project_state: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-002
    disposition: APPLICABLE
    reason: Recovery/currentness must not admit historical policy/checkpoint state as current authorization after the identity cutover.
  - id: SP-001
    disposition: APPLICABLE
    reason: Repair the over-broad owner by reduction/rewiring rather than adding a synchronized second threshold path.
  - id: SP-002
    disposition: APPLICABLE
    reason: Method/policy/effective-admissibility identity boundaries and stale CV/final authorization must fail closed.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve unaffected immutable P1/P2/P3/replay/source/common-monitor evidence rather than globally rebuilding it.
  - id: SP-004
    disposition: APPLICABLE
    reason: Acceptance must exercise the real CV -> EVAL2 classification -> held-out verdict -> production authorization path.
```

**PEM basis health:** `REVIEW_REQUIRED` as metadata provenance, not as a blocker to the bounded lessons above. The project-selected accepted publication at `4eabe2...` still self-declares an older `b65fa3b...` basis and the then-live NT-001 state. Later commit `b5d101d8f73d3efd63ef4e70b3913e7d281406ce` reconciled that basis on a branch-local candidate overlay and its repair subsequently closed PASS, but this workplan does not self-promote that later file state into accepted PEM. Therefore the HAS uses only materially verified family lessons also supported by direct repository history, and absence of another lesson is not inferred from the partial/stale metadata. Gate E must refresh this disposition if project-governed PEM acceptance advances before closeout.

The immediately preceding post-selection restoration is also read directly as bounded historical evidence. It preserved target/replay thresholds because threshold revision was outside that cycle; this does **not** establish that CV and production target ceilings must be identical. Retired CV specifications may support the robustness rationale but do not govern current D1/D2.

## 5. Evidence and falsification

### Reverse-semantic verification question

From persisted current identities/plans/evidence and executable behavior, without this workplan, can an independent reviewer reconstruct:

```text
shared foundation adaptation method: same CV and production method
foundation CV checkpoint competence: 45 meV/angstrom target-force RMSE
foundation CV default held-out force-RMSE pass: 45 meV/angstrom
foundation production checkpoint quality: 30 meV/angstrom target-force RMSE
scratch default target behavior: unchanged (30 meV/angstrom defaults)
CV consistency: every required fold/seed passes; dispersion diagnostic only
shared replay/physical/integrity gates: unchanged
EVAL2 candidate classification: bound to exact role-effective admissibility digest
TRAIN2 termination: fixed budget
release qualification: downstream and unchanged
```

If not, the concretization is inadequate.

### Required falsification cases

At minimum:

1. **Foundation CV intermediate checkpoint:** all other gates pass and target-monitor RMSE `~0.042` -> checkpoint admissible under foundation CV.
2. **Foundation CV intermediate held-out:** frozen representative held-out target-force RMSE `~0.042` -> pass under default foundation CV.
3. **CV upper boundary:** `0.045` passes `<=`; representable just-above fails at the correct role owner.
4. **Production preservation:** foundation production target-monitor RMSE `~0.042` -> inadmissible under `0.030` production policy.
5. **Production boundary:** `0.030` passes; representable just-above fails.
6. **Scratch preservation:** default scratch `~0.042` does not begin passing because foundation CV changed.
7. **Evidence-role separation:** equal numeric CV ceilings do not let held-out labels select checkpoints or monitor evidence replace held-out evaluation.
8. **Replay/physical independence:** relaxing foundation-CV target competence does not relax replay degradation, TRUE_DFT requirement, physical/integrity gates or replay ranking semantics.
9. **No-admissible outcome:** all candidates above `0.045` or failing another mandatory gate produce the existing no-admissible fold rejection with no held-out evaluation; replay/physical failures are not rescued by target relaxation.
10. **All-fold/seed semantics:** one required failure rejects the CV campaign even if mean error is below `0.045`; dispersion remains diagnostic-only.
11. **Metric-dimensionality guard:** choose a supported non-target-force outer metric and prove its threshold is not consumed as target-force checkpoint competence.
12. **Frozen-selection preservation:** the threshold cutover does not mutate/recompute P1/P2/P3 or the frozen selected `(N, CV horizon, production horizon)` binding.
13. **One-time method-identity cutover:** a pre-cutover P5 shared-method identity containing target-bearing admissibility ancestry does not authorize current descendants; current schema/generation is fail-closed.
14. **Post-cutover CV-only identity change:** perturb only the foundation-CV checkpoint ceiling and prove CV policy/evidence moves while shared method and production policy do not.
15. **Post-cutover production-only identity change:** perturb only production target ceiling and prove production policy moves while shared method and applicable CV method evidence do not.
16. **Shared-gate identity change:** perturb replay degradation or another genuinely shared method/admissibility gate and prove shared method plus dependent CV/production ancestry move.
17. **Effective EVAL2 policy binding:** CV and production EVAL2 plans bind different effective admissibility-policy digests when their target ceilings differ, while binding the same shared method identity.
18. **Recovery policy authentication:** completed candidate evidence classified under one effective admissibility digest cannot be reused/current under another digest by simply recomparing stored numeric metrics.
19. **No redundant evidence authority:** if EVAL2 plan ancestry already proves effective policy, checkpoint-record schema is not expanded merely to duplicate that policy unless an actual recovery gap requires it.
20. **Historical state:** old readable method/policy/CV records cannot silently authorize current work; no compatibility wrapper reinterprets shared-30 state.
21. **Configuration defaults:** newly generated foundation campaign resolves default outer CV `0.045` and production target `0.030`; scratch defaults remain pre-change; generated and example configs agree.
22. **Explicit config preservation:** existing explicit `[post_selection.cv].acceptance_maximum = 0.030` remains `0.030`; it is not silently rewritten to the new default.
23. **No early-stop leak:** training consumes configured CV fixed horizon rather than stopping when `0.045` is first crossed.
24. **Real-path integration:** exercise `cross-validate` -> persisted CV verdict -> `train-production`, authenticating shared method, CV policy, production policy and effective EVAL2 admissibility ancestry at the real owners.
25. **Current documentation/specification:** current D1/D2/D3/D4 text no longer claims one identical target ceiling is part of the shared checkpoint method while role policy says otherwise.

### Calibration adequacy premise

The `45 meV/angstrom` choice is accepted for this cycle from the stakeholder-provided historical learning-curve recollection: rapid initial convergence, then pronounced slowdown across roughly `40-20 meV/angstrom`, with `30 meV/angstrom` selected as a production criterion inside that slow region. `45 meV/angstrom` is intentionally just above the slow-convergence regime.

No new calibration campaign is required simply to implement this already-directed narrow change. Reopen D1/D2 if applicable current evidence shows healthy foundation folds commonly plateau above `45`, shows no such convergence knee, or shows the remembered curve belongs only to scratch/different training semantics.

### Strongest Challenge

Attempt to falsify the split by determining whether:

1. any current workflow uses foundation CV's old `30 meV/angstrom` gate as the **only** quantitative final-product/release accuracy assurance;
2. current docs/code conflate the `30 meV/angstrom` production common-monitor gate with locked/downstream qualification; or
3. the target ceiling is scientifically part of the shared training method rather than role-specific evidence policy.

If any is established, stop the local split and reopen D1. Do not compensate in D3/D4.

## 6. Concretization sequence

### Gate A — D1 authority reconciliation

Narrowly amend `docs/methods/mlff_scientific_method.md`:

- distinguish shared foundation-adaptation method from CV competence policy and production checkpoint-quality policy;
- define current CV consistency as all-required-fold/seed competence plus held-out success, with dispersion diagnostic-only;
- establish `45 meV/angstrom` as current foundation CV competence/default target-force held-out threshold and retain `30 meV/angstrom` fresh-production target checkpoint quality;
- preserve common-monitor/held-out separation, leakage prohibitions, replay semantics and downstream qualification;
- explicitly preserve scratch as separately governed;
- revise “same shared checkpoint method” prose so it means shared monitor/selection/evaluation semantics, not an identical role target ceiling; and
- reconcile stale post-restoration integration metadata.

Keep the calibration provenance honest: stakeholder-authorized historical observation, not fabricated recovered evidence.

Run independent D1 Challenge/Review and required stakeholder ratification before treating the revision as accepted-current D1.

### Gate B — D2 numerical-method reconciliation

After D1 acceptance, narrowly amend `docs/methods/mlff_numerical_algorithmic_method.md`:

- define the foundation CV checkpoint target-force predicate at `<=0.045 eV/angstrom`;
- define current default held-out target-force acceptance at `<=0.045 eV/angstrom`;
- retain foundation production checkpoint target-force predicate at `<=0.030 eV/angstrom`;
- preserve strict evidence-role separation and all-fold/all-seed aggregation;
- keep dispersion diagnostic-only;
- preserve fixed-budget training;
- define dimensional separation for alternate outer metrics; and
- keep scratch unaffected.

Revise “same checkpoint method” language so CV/final share the checkpoint-selection/evaluation method and common monitor while consuming different role-specific target-ceiling policies.

Run independent D2 review with boundary, unit, mode, role-policy and stale-evidence counterexamples.

### Gate C — D3 ownership/currentness cutover

Reconstruct all current identity consumers before editing. Required end state:

- shared `PostSelectionMethodIdentity` no longer binds a role-specific target ceiling;
- it still binds the genuine shared method and shared replay/physical/integrity semantics;
- `CvValidationPolicyIdentity` carries/reconstructs the effective foundation-CV checkpoint target ceiling in addition to outer acceptance policy;
- `FinalProductionPolicyIdentity` carries/reconstructs the effective production target ceiling;
- role policy is available before work and deterministically produces the effective checkpoint-admissibility policy;
- EVAL2 evaluation ancestry binds the exact effective admissibility-policy digest;
- recovery reauthenticates that digest rather than reinterpreting old candidate records;
- scratch and generic TRAIN2/EVAL2 retain accepted behavior; and
- current P1/P2/P3/frozen-selection/common-monitor evidence is preserved where its own identity did not change.

Treat the migration and steady state separately. Advance `PostSelectionMethodIdentity` schema/generation if needed to remove the old full target-bearing digest. That one-time change may stale old P5 CV/final evidence. After cutover, role-only target changes must no longer move shared method identity.

Advance `CvValidationPolicyIdentity`/`FinalProductionPolicyIdentity` schema only if their serialized semantics/payload change, which is likely when role target ceilings become identity-bearing. Do not advance `PostSelectionCvPlan`, `FinalProductionPlan`, EVAL2 or checkpoint-record schemas merely because an ancestor digest value changes; advance them only if their own representation/meaning changes.

Prefer existing ancestry seams. CV/final run plans already bind their role-policy digests; EVAL2 already owns an `admissibility_policy_digest`. Rewire those real owners rather than adding a second role-policy field to every descendant.

Review configuration ownership. Do not globally change `[acceptance].maximum_target_force_rmse_ev_per_angstrom` to `0.045`: it has scratch/generic consumers. Production may continue resolving its `0.030` value from that existing owner if faithful. Foundation CV needs an identity-bearing effective `0.045` role value; introduce a new user-visible field only if the existing CV policy surface cannot express this without ambiguity.

### Gate D — D4 implementation and affected regression

Implement the minimum Gate-C concretization.

Generated/example foundation defaults must expose outer CV acceptance:

```toml
[post_selection.cv]
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045
```

That is only the outer held-out default. The foundation-CV **checkpoint** target-force competence must independently resolve to the authenticated CV-role `0.045` policy, and foundation production must resolve to authenticated `0.030` production policy.

Make default resolution mode-aware without duplicating policy resolvers: foundation default outer CV becomes `0.045`; scratch retains its current default. Existing explicit values remain explicit. Alternate outer metrics remain dimensionally separate from checkpoint target force.

Update the hand-maintained example, generated `init` text, parser/default/currentness logic and user guide together. Reconcile P5 D4 spec, runtime role-policy composition, EVAL2 effective-admissibility ancestry, recovery, logs/manifests and affected tests.

Do not add early stopping or change the default CV horizon to manufacture a speedup. GPU qualification remains deferred to the final complete release package under standing project policy.

### Gate E — assembled independent review and impact closure

Independently review the assembled D1-D4 candidate. Verify:

- foundation/scratch isolation;
- D1/D2 role meaning and exact units;
- one-time identity cutover versus steady-state minimal invalidation;
- role-effective EVAL2 admissibility provenance and recovery;
- no stale-policy reinterpretation;
- frozen target-selection/common-monitor preservation;
- no replay/physical/integrity weakening;
- no P3/generic TRAIN2 collateral change;
- fixed-budget behavior;
- generated/config/doc convergence; and
- real CV -> production authorization.

Refresh the PEM/HAS basis-health disposition if project-governed accepted memory advances. Perform closeout learning assessment but mutate PEM only if admission criteria are met. Archive this workplan only after independent review PASS and required authority acceptance.

## 7. Reopen, simplification and human triggers

Reopen D1 if:

- CV is actually final-product/release qualification;
- the `45 meV/angstrom` calibration premise is contradicted or inapplicable to current foundation adaptation;
- target ceiling is scientifically part of the shared method rather than role evidence policy; or
- the change alters a broader scientific conclusion.

Reopen D2 if:

- role target predicates cannot be specified without unit/metric ambiguity;
- shorter fixed-horizon CV plus the competence predicate introduces an unrecognized estimator/selection bias;
- a mode-independent target criterion is required by accepted science; or
- role policy changes the checkpoint-selection algorithm rather than only admissibility threshold.

Reopen D3 before adding machinery if:

- clean ownership seems to require a wrapper, shadow registry, duplicate evaluator or synchronized thresholds;
- fail-closed currentness cannot be achieved through existing method/role/EVAL2 ancestry;
- the implementation would require global generic TRAIN2/scratch changes; or
- the proposed representation cannot distinguish one-time cutover invalidation from post-cutover role-only invalidation.

Human ratification is required for the material D1/D2 revision before final acceptance. No active Serious Challenge remains in the reviewed workplan; the Challenge targets above remain mandatory during Gates A/B/E.

## 8. Impact, compatibility and history

Record the semantic evolution succinctly:

- the 2026-09-14 restoration preserved target/replay thresholds because threshold revision was outside its scope;
- subsequent review identified that target ceiling ownership was too broad and coupled foundation CV to production late convergence;
- foundation CV competence/default held-out target-force acceptance becomes `45 meV/angstrom`;
- foundation production target checkpoint quality remains `30 meV/angstrom`;
- scratch remains unchanged;
- CV consistency remains all-required-fold/seed success with diagnostic dispersion; and
- the separation permits deliberately shorter fixed-horizon foundation CV without weakening production or release qualification.

Do not rewrite retired specifications as though they always contained this split.

Compatibility/currentness distinction:

- pre-cutover shared-method identity may become historical because its representation incorrectly included the role target ceiling;
- this one-time cutover may stale old P5 CV/final descendants while preserving unaffected upstream/source/cache/common-monitor evidence;
- a prior `30` pass is not automatically current under `45` merely because it is numerically stronger on one metric;
- a prior `30-45` failure is not retroactively relabeled as pass; and
- after cutover, future role-only threshold edits obey the minimal steady-state invalidation graph.

No new threshold-equivalence migration layer is authorized.

## 9. Acceptance and handoff

The workplan may close only when:

- D1 clearly separates shared foundation method, CV competence, production checkpoint quality and downstream qualification;
- D1 states the bounded consistency claim and keeps dispersion diagnostic-only;
- D2 owns/reconstructs the exact `45`/`45`/`30 meV/angstrom` foundation predicates with correct units;
- calibration provenance is represented honestly as stakeholder-authorized historical observation unless stronger evidence is actually recovered;
- scratch remains unchanged;
- independent D1/D2 review and required stakeholder ratification are complete;
- the shared method no longer owns role target ceilings in the **post-cutover** representation;
- the one-time method-identity/schema cutover and its stale-evidence consequence are explicit and tested;
- post-cutover CV-only and production-only threshold edits have minimal exact invalidation;
- genuinely shared replay/physical/integrity changes still move shared method identity;
- foundation CV checkpoint competence resolves to `45 meV/angstrom`;
- default foundation held-out target-force acceptance resolves to `45 meV/angstrom`;
- foundation production checkpoint quality remains `30 meV/angstrom`;
- alternate outer metrics cannot alias target-force checkpoint competence;
- EVAL2 candidate classification binds the exact role-effective admissibility-policy digest and recovery reauthenticates it;
- old candidate evidence is not reinterpreted under a new role threshold;
- P1/P2/P3/frozen selected design and unaffected common-monitor/replay/source evidence are preserved;
- new generated config, example config and user guide agree while explicit old config is not silently rewritten;
- TRAIN2 remains fixed-budget;
- all required folds/seeds, leakage, replay and physical/integrity constraints remain unchanged;
- real-path regression includes `30 < RMSE <= 45` foundation CV pass, production fail, scratch preservation, unit/dimensionality, one-time cutover, steady-state invalidation and recovery cases;
- assembled `cross-validate` -> persisted acceptance -> `train-production` passes under authenticated role policies; and
- PEM basis-health/closeout obligations and affected documentation/history are reconciled.

A hidden shared `30 meV/angstrom` CV gate, global `45` scratch change, runtime-only unbound role switch, missing effective-EVAL2 policy provenance, metric-unit aliasing, stale-schema reinterpretation, silent old-evidence reclassification, contradiction between one-time and steady-state invalidation, production-threshold relaxation, downstream qualification weakening, or unreviewed final-qualification dependence is a blocking **No-Pass**.
