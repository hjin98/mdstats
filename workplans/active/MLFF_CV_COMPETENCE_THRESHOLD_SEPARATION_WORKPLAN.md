---
kind: abstraction-concretization-change-plan
protocol_version: 6.3.0
status: proposed
branch: fix/mlff-cv-competence-threshold-separation
baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
highest_affected_domain: D1
review_state: amended-after-cross-domain-review
---

# MLFF CV Competence Threshold Separation Workplan

## Background and scope

The current foundation-model post-selection path (`naive_fine_tuning` and `multihead_replay`) uses the same target-force root-mean-square error (RMSE) ceiling, nominally `0.030 eV/angstrom`, for two roles with different purposes:

1. **cross-validation (CV) competence/robustness** — disposable fold models test whether the frozen foundation-adaptation method reaches a clearly competent regime consistently on held-out development evidence; and
2. **fresh-production checkpoint quality** — production representatives are required to satisfy the established stricter target checkpoint/model-control criterion before publication and downstream qualification.

The stakeholder's prior training-curve study indicates rapid initial error reduction followed by markedly slower convergence through roughly the `40-20 meV/angstrom` regime. The existing `30 meV/angstrom` criterion deliberately lies inside that slow-convergence region. Requiring every disposable foundation-CV fold to reach the same criterion spends substantial compute on late convergence that is not necessary to answer the CV robustness question.

For the current foundation-adaptation policy, the cycle-scoped target values are therefore:

```text
T_CV = 0.045 eV/angstrom = 45 meV/angstrom
T_PRODUCTION = 0.030 eV/angstrom = 30 meV/angstrom
```

The `30 meV/angstrom` production value is a checkpoint/model-control quality criterion on the protected common target monitor. It is **not** promoted here into a claim that this monitor is the final external adequacy/locked-test qualification of the released force field. Existing downstream qualification remains distinct.

This workplan is intentionally narrow. The empirical premise above is specific to the currently restored **foundation-adaptation** path. P5 training from scratch has a separately accepted method and is not silently assigned the `45 meV/angstrom` CV criterion by this change.

## 1. Outcome and authority

### Protected stakeholder outcome

Remove the accidental production-threshold coupling that prevents economical fixed-horizon foundation CV. Foundation CV should be able to establish method competence before the slow-convergence production regime, while fresh production retains the stricter target checkpoint criterion and downstream release qualification remains unchanged.

This cycle **enables** deliberately shorter fixed-horizon CV configurations. It does not claim a runtime reduction merely from changing a threshold, and it does not choose a new universal default CV horizon without evidence.

### Highest affected semantic domain

**D1 scientific formulation.** Current D1 asks whether the complete frozen foundation-adaptation method "performs acceptably" on held-out development evidence but does not distinguish CV competence from production checkpoint quality strongly enough to prevent the two thresholds from being coupled downstream.

The D1 change is semantic but narrow:

- CV establishes foundation-adaptation **competence/robustness** on held-out development evidence;
- fresh production uses a stricter **production checkpoint/model-control quality** criterion; and
- neither role is redefined as downstream locked/release qualification.

D2 owns the exact numerical predicate/equivalence semantics needed to concretize that distinction. D3 owns where shared method identity ends and role-policy identity begins. D4 owns exact schemas, configuration keys/defaults, resolvers, serialization and runtime realization.

### Accepted baseline and current owners

Baseline accepted project state: `8553ebe9ed86b24dfe910c9e43acc6230d3ece90` (`main`, merged post-selection restoration).

Current normative owners:

- D1: `docs/methods/mlff_scientific_method.md`
- D2: `docs/methods/mlff_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data_architecture.md` and `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- D4 current foundation-P5 contract: `docs/specs/training_data/mlff_post_selection_p5_spec.md`
- executable identity/policy owner: `mdstats/training_data/post_selection_identity.py`
- generic TRAIN2/EVAL2 checkpoint policy/evaluator: `mdstats/training_data/train2_policy.py` and its consumers
- outer CV acceptance owner: `mdstats/training_data/post_selection_cv_acceptance.py`

The current D1/D2 front matter still describes the just-merged restoration as "pending repository integration". Because these files are directly amended in this cycle, their authority-state metadata must be reconciled to the actual integrated baseline rather than copied forward stale.

### Proposed authority and human state

Stakeholder direction authorizes drafting the following proposed authority:

- foundation-adaptation CV competence is distinct from production checkpoint quality;
- the current foundation-CV competence target is `45 meV/angstrom`;
- the current fresh-production target checkpoint criterion remains `30 meV/angstrom`;
- CV and production target ceilings are role-policy semantics, not one shared target-accuracy field of `PostSelectionMethodIdentity`;
- replay retention and other genuinely shared checkpoint constraints remain shared method semantics; and
- P5 scratch remains on its separately accepted threshold behavior unless separately reopened.

The D1/D2 authority edits remain proposed until independent falsification/review and required stakeholder ratification are complete.

## 2. Governing contract

### Invariants

1. **Foundation-only threshold revision.** The `45 meV/angstrom` CV criterion applies to `naive_fine_tuning` and `multihead_replay`. P5 scratch must retain its accepted behavior unless separately reopened with evidence.
2. **Production target quality is unchanged.** Fresh foundation production retains `30 meV/angstrom` as its target checkpoint/model-control ceiling.
3. **CV competence is role-specific.** Foundation CV target-monitor checkpoint competence and the current default held-out target-force-RMSE acceptance use `45 meV/angstrom`.
4. **Same number does not collapse evidence roles.** The common-monitor predicate and held-out-fold predicate remain distinct evaluations on distinct evidence. Sharing `45 meV/angstrom` does not permit monitor/held-out evidence substitution or leakage.
5. **All required folds and seeds still pass individually.** Mean performance cannot rescue a failed or missing required fold/seed.
6. **Cross-fold dispersion remains diagnostic-only.** This cycle does not add a hard dispersion gate.
7. **Replay retention is unchanged and remains shared.** The replay-degradation budget, authenticated TRUE_DFT requirement, and zero replay ranking credit are not relaxed, role-split, or duplicated.
8. **Physical/integrity admissibility is unchanged and remains shared.** Finite-metric, identity, transfer-feasibility, physical-gate, provenance and other existing hard failures remain hard failures.
9. **Held-out folds remain evaluation-only.** Held-out labels may not select checkpoints, fit E0/preprocessing, supply gradients, construct the common monitor, or feed backward into training/model control.
10. **Common-monitor semantics are unchanged.** The accepted campaign-common exact target monitor remains external to every fold and is shared by foundation CV and fresh production.
11. **Fixed-budget TRAIN2 remains fixed-budget.** No target-threshold early stopping or performance-driven termination is introduced.
12. **CV horizon remains independently controllable.** Existing CV horizon/budget controls may be shortened deliberately. This cycle does not create a new optimizer schedule or automatic stop rule.
13. **Role thresholds are bound before work.** A target ceiling may not be selected only by an unpersisted runtime branch such as `if role == ...`. The applicable ceiling must be part of authenticated role-policy ancestry before checkpoint/evaluation evidence is produced.
14. **Shared method identity excludes role-only target ceilings.** `PostSelectionMethodIdentity` must continue to bind genuinely shared replay/physical/integrity/method constraints, but a CV-only or production-only target ceiling must not make the shared method appear scientifically different.
15. **Role-policy invalidation is minimal and exact.** Changing only the foundation-CV target ceiling must move CV policy/evidence without changing production policy or the shared method. Changing only the production target ceiling must move production policy without staling otherwise applicable CV evidence or the shared method. Changing a genuinely shared replay/physical/method gate must still move the shared method and stale dependent CV/production evidence.
16. **No hidden 30-meV CV fallback.** A healthy foundation-CV candidate at, for example, `42 meV/angstrom` must not be rejected merely because a production-only `30 meV/angstrom` ceiling remains consulted somewhere on the CV path.
17. **No global-threshold collateral change.** Existing non-foundation consumers of `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, generic `CheckpointAdmissibilityPolicy`, or related TRAIN2/EVAL2 infrastructure must not change behavior merely because foundation CV is repaired.
18. **Metric units cannot be aliased.** `[post_selection.cv].acceptance_maximum` is dimensioned by `acceptance_metric`. If a supported outer acceptance metric other than target force RMSE is selected, its numeric threshold must not be reused as a target-force checkpoint ceiling.
19. **Historical/current state fails closed.** Old policy/identity records may remain readable as history, but an old shared-30-meV identity may not silently authorize the new role-separated current method/policies.
20. **No silent configuration migration.** An existing campaign that explicitly records `acceptance_maximum = 0.030` is not silently rewritten to `0.045`. New/current foundation defaults may change, and an operator may explicitly adopt the new policy; currentness then follows identity rules.

### Cycle-scoped decisions

For the current foundation-adaptation cycle freeze:

```text
foundation CV checkpoint target-force competence ceiling = 0.045 eV/angstrom
foundation CV default outer metric                        = target_force_rmse_ev_per_angstrom
foundation CV default outer acceptance ceiling            = 0.045 eV/angstrom
foundation production checkpoint target ceiling           = 0.030 eV/angstrom
CV aggregation                                              = all required folds and variants
CV dispersion policy                                        = diagnostic_only
TRAIN2 termination                                           = fixed budget
```

The workplan does not promote these values into a universal theorem for all training modes. The current D1/D2 authority must define the role distinction; exact current numeric defaults/predicates are recorded at the appropriate numerical/specification/configuration owner and remain changeable only through that owner's accepted process.

### Delegated space

D3/D4 may choose the smallest clean representation that satisfies the invariants. Prefer narrowing/splitting existing ownership over adding wrappers, compatibility shims, duplicate acceptance engines, shadow policy registries, or a second threshold subsystem.

A valid architecture may retain the generic `CheckpointAdmissibilityPolicy` execution type, but the **identity projection** must no longer force one role-specific target ceiling into the shared foundation method. Conversely, the repair may refactor the existing policy type if that is the simplest way to leave shared replay/physical/integrity constraints at the shared owner. Exact class/function names are delegated.

### Non-goals

This work does **not**:

- change P5 scratch CV or production thresholds;
- change the `30 meV/angstrom` foundation production checkpoint criterion;
- claim the common monitor is final locked/release qualification;
- choose a new universal default CV epoch count;
- add threshold-driven early stopping;
- redesign fold construction, fold count, seed policy, aggregation, monitor membership or monitor size;
- promote cross-fold dispersion into a hard criterion;
- alter UniversalLoss/foundation objective/exposure semantics;
- relax replay, physical, provenance or integrity gates;
- alter target-size P1/P2/P3 semantics;
- reinterpret old CV failures/passes as current without explicit compatibility authority; or
- globally redesign generic TRAIN2/EVAL2 policy classes unless direct dependency analysis proves that reduction is the smallest safe repair.

## 3. Adequacy, identity and affected surface

### D1 -> D2 handoff

D2 must preserve this scientific distinction without changing evidence roles:

- foundation CV asks whether the complete frozen method can reach a competent regime consistently under fixed-budget fold training and then perform acceptably on held-out development evidence;
- production checkpoint control applies a stricter target criterion to fresh production representatives; and
- downstream qualification remains responsible for release/external adequacy beyond this checkpoint-control evidence.

The `45 meV/angstrom` calibration premise is the observed fast-to-slow convergence transition described above. If repository evidence materially contradicts that premise, D1/D2 must be reopened; D4 may not widen the threshold to make tests pass.

### D2 -> D3 handoff

D3 must represent the following ownership split:

```text
PostSelectionMethodIdentity
  owns: foundation method, optimizer/exposure/loss/preparation identity,
        shared replay-retention gate, shared physical/integrity requirements,
        common-monitor method identity
  does not own: CV-only or production-only target-force ceiling

CvValidationPolicyIdentity
  owns: CV geometry/budget/seeds/aggregation,
        foundation-CV checkpoint target competence policy,
        outer held-out acceptance metric/threshold

FinalProductionPolicyIdentity
  owns: production horizon/seeds/publication policy,
        foundation-production checkpoint target-quality policy
```

Equivalent decomposition is allowed if the same ownership/invalidation graph is reconstructable and no duplicate authority is introduced.

The current implementation embeds `CheckpointAdmissibilityPolicy.policy_digest` in `PostSelectionMethodIdentity`; that policy currently contains `maximum_target_force_rmse_ev_per_angstrom`. The repair must therefore perform an actual identity-ownership cutover, not merely pass a different threshold to one runtime call while leaving the old shared digest authoritative.

If the serialized payload/meaning of `PostSelectionMethodIdentity`, `CvValidationPolicyIdentity`, `FinalProductionPolicyIdentity`, or a bound checkpoint-policy record changes materially, advance the corresponding schema/version token and define fail-closed currentness. Reusing the same schema for a different ownership meaning is nonconforming.

### Acceptance-metric dimensionality

Current outer CV acceptance supports multiple metric names, including target-force RMSE, species/worst-stratum force metrics, force-error quantiles, and energy MAE. Therefore:

- the **foundation checkpoint competence ceiling is specifically target-force RMSE**;
- the default outer foundation-CV acceptance remains target-force RMSE at `0.045 eV/angstrom`;
- if an explicitly supported non-force-RMSE outer metric is selected, its `acceptance_maximum` remains metric-specific and cannot become the checkpoint target-force ceiling by numeric reuse; and
- D3/D4 must either bind a distinct role-specific checkpoint target-force field/policy or prove that reuse occurs only when `acceptance_metric == "target_force_rmse_ev_per_angstrom"` with correct units.

Do not add a user-visible second knob merely for symmetry if a fixed/current role-policy constant or existing owner can carry the value cleanly. But do not create unit ambiguity to avoid one justified field.

### Foundation versus scratch

`docs/specs/training_data/mlff_post_selection_p5_spec.md` explicitly scopes the restored foundation requirements to `naive_fine_tuning` and `multihead_replay`, while P5 scratch retains its separately accepted contract. The current mode-agnostic CV policy/configuration surface therefore cannot simply be changed globally to `0.045` without a mode-aware resolution rule or equivalent policy split.

A scratch campaign/result at `42 meV/angstrom` must not start passing solely because this foundation-CV change landed.

### Materially dependent descendants

Review the actual dependency graph and update at least these directly implicated surfaces where applicable:

- `docs/methods/mlff_scientific_method.md`
- `docs/methods/mlff_numerical_algorithmic_method.md`
- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`
- `docs/specs/training_data/mlff_post_selection_p5_spec.md`
- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/train2_policy.py` only if the clean owner split genuinely requires changing the generic policy type
- `mdstats/training_data/post_selection_cv_acceptance.py`
- CV/final plan, runtime, recovery/currentness code that binds or compares method/policy/checkpoint-admissibility digests
- `campaign.toml.example`
- generated `init`/campaign-template text in `mdstats/training_data/_campaign_cli_core.py`
- configuration parsing/validation and any schema/default owner
- `docs/guides/mlff_campaign_cli_user_guide.md`
- persisted manifests/logs/status output that expose or authenticate the thresholds
- tests covering identity, CV no-admissible outcome, role policy, resume/currentness, CLI generation and assembled CV -> production authorization.

This list is a lower bound, not permission to ignore a discovered consumer.

### Unaffected siblings/evidence

Preserve without churn:

- P1/P2 neutral evidence, protected relations and ordering;
- P3 target-size screening objective/evaluation semantics;
- common monitor membership algorithm and exact size;
- CV fold membership/purge logic;
- replay source/split/corpus construction and replay metric definition;
- foundation checkpoint/head identity;
- residual-E0 fitting and transfer semantics;
- foundation UniversalLoss/exposure semantics;
- production horizon semantics;
- P5 scratch method/threshold semantics;
- generic TRAIN2/EVAL2 consumers not proven dependent on this foundation role split; and
- still-applicable source/cache/evidence products whose owning identity did not change.

## 4. Historical Applicability Set

This change touches mature P5 identity/currentness machinery and depends on recent restoration history, so project engineering memory is active.

```yaml
pem_basis:
  accepted_project_state: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-002
    disposition: APPLICABLE
    reason: CV/recovery/currentness must not treat historical policy/checkpoint state as current authorization after the identity cutover.
  - id: SP-001
    disposition: APPLICABLE
    reason: The defect is over-broad shared ownership; repair by narrowing the real owner rather than adding a wrapper or synchronized second threshold path.
  - id: SP-002
    disposition: APPLICABLE
    reason: Method/policy/schema boundaries and stale CV authorization must fail closed rather than reinterpret plausible old state.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve unaffected immutable P1/P2/P3/replay/source evidence and invalidate only descendants whose policy ancestry changed.
  - id: SP-004
    disposition: APPLICABLE
    reason: Acceptance must exercise the real CV -> checkpoint -> held-out -> production authorization path; helper-only threshold tests are insufficient.
```

The accepted PEM has partial historical coverage and is reconciled only through its declared basis; absence of another relevant lesson is not proven. The recent post-selection restoration workplan/audit is therefore also reviewed directly as bounded historical evidence. Refresh the HAS if accepted project memory or governing branch authority materially advances before closeout.

The preceding restoration explicitly preserved target/replay thresholds because threshold revision was outside its scope. That historical preservation is **not** evidence that CV and production target ceilings must be identical. Retired CV specifications may support rationale about robustness, but current accepted D1/D2 remains the authority to amend.

## 5. Evidence and falsification

### Reverse-semantic verification question

Starting from assembled persisted policy/method identities and real D4 behavior, can a reviewer reconstruct all of the following without relying on comments or this workplan?

```text
foundation CV checkpoint target competence: 45 meV/angstrom
foundation CV default held-out target-force pass: 45 meV/angstrom
foundation production checkpoint target quality: 30 meV/angstrom
P5 scratch threshold semantics: unchanged
shared replay/physical/integrity gates: unchanged
all required CV folds/seeds: individually required
termination: fixed budget
release qualification: downstream and unchanged
```

If not, the concretization is inadequate.

### Required falsification cases

At minimum demonstrate:

1. **Foundation CV intermediate case:** with all other gates passing, a foundation-CV checkpoint target RMSE of about `0.042 eV/angstrom` is admissible and a held-out target-force RMSE of about `0.042 eV/angstrom` passes under the current default foundation-CV policy.
2. **Foundation CV boundary failure:** a foundation-CV checkpoint or default held-out target-force result above `0.045 eV/angstrom` fails at the correct owner/reason.
3. **Production preservation:** an otherwise healthy foundation-production checkpoint at about `0.042 eV/angstrom` remains inadmissible under the `0.030 eV/angstrom` production target policy.
4. **Scratch preservation:** the same `0.042 eV/angstrom` case does not become accepted merely by using P5 scratch; scratch remains on its pre-change policy unless separately configured/authorized under its own current contract.
5. **Exact boundaries:** equality at the relevant ceiling passes `<=`; a representable just-above value fails under the existing floating-point comparison convention.
6. **Evidence-role separation:** monitor and held-out metrics may have the same numeric ceiling but are persisted/evaluated independently; held-out labels never influence checkpoint choice.
7. **Replay independence:** changing foundation CV target threshold does not alter replay admissibility, TRUE_DFT requirement, replay ranking credit, or physical/integrity gates.
8. **No-admissible outcome:** a fold with candidates only above `45 meV/angstrom` or failing another hard gate remains `no_admissible_representative` with no held-out evaluation; widening the target ceiling cannot rescue replay/physical failures.
9. **All-fold semantics:** one failing required fold/seed still rejects the CV campaign even when the mean is below `45 meV/angstrom`.
10. **Metric-dimensionality guard:** select a supported non-target-force outer acceptance metric and prove its `acceptance_maximum` is not consumed as a target-force checkpoint ceiling.
11. **CV-only identity change:** changing only the foundation-CV target ceiling changes CV policy/currentness but leaves the shared method identity and final-production policy identity unchanged.
12. **Production-only identity change:** changing only the production target ceiling changes final-production policy/currentness but leaves shared method identity and already applicable CV method evidence unchanged.
13. **Shared-gate identity change:** changing replay degradation or another genuinely shared checkpoint/method gate still changes the shared method identity and invalidates dependent CV/production authorization.
14. **Schema/currentness cutover:** old current-generation identities/policy records with the shared target ceiling do not deserialize/revalidate as new current authority under unchanged schema semantics. Historical readability, if retained, cannot authorize current work.
15. **Resume/recovery:** resumed CV/production cannot reuse run/checkpoint/acceptance evidence whose role-policy identity does not match current policy. Recovery authenticates stored classification; it does not reinterpret old evidence under a new threshold.
16. **Configuration default:** newly generated foundation-adaptation campaign configuration resolves the current `45 meV/angstrom` CV default and `30 meV/angstrom` production default. Existing explicit `0.030` CV configuration is not silently rewritten.
17. **No early-stop leak:** CV still consumes the configured fixed horizon rather than terminating when `45 meV/angstrom` is first crossed.
18. **Real-path integration:** exercise the current `cross-validate` -> persisted CV acceptance -> `train-production` authorization boundary so role-policy digests and threshold provenance are verified at the actual owners, not only helper calls.

### Empirical adequacy premise

The current calibration basis is stakeholder-observed learning-curve behavior: rapid early convergence followed by strong slowdown through approximately `40-20 meV/angstrom`, with `30 meV/angstrom` intentionally selected as a production checkpoint criterion inside that slow regime. `45 meV/angstrom` is selected just above that regime for foundation CV competence.

A new calibration campaign is not required merely to implement the already-directed narrow policy change. But if current repository evidence materially contradicts the premise — for example, healthy foundation folds routinely plateau above `45 meV/angstrom`, the convergence knee is absent, or scratch is the only source of the remembered curve — raise that contradiction to D1/D2 before implementation.

### Strongest Challenge

Attempt to falsify the proposed split in two directions:

1. determine whether any current downstream workflow treats foundation CV's `30 meV/angstrom` result as its **only** final-product/release accuracy assurance; and
2. determine whether the `30 meV/angstrom` common-monitor production gate is being conflated in current documentation/code with locked/downstream qualification.

If either is true, do not weaken or relabel evidence locally. Reopen D1 and identify the actual final-adequacy owner first.

## 6. Concretization sequence

### Gate A — D1 authority reconciliation

Amend `docs/methods/mlff_scientific_method.md` narrowly:

- state that foundation post-selection CV tests method competence/robustness rather than requiring production-level late convergence;
- distinguish that from the stricter fresh-production checkpoint/model-control quality criterion;
- preserve held-out evidence semantics, all-required-fold acceptance, common-monitor separation, replay requirements and downstream qualification separation;
- explicitly retain P5 scratch as separately governed;
- remove/qualify wording that implies one universal target threshold must govern foundation CV and production; and
- correct stale post-restoration integration metadata while editing the current authority.

D1 need not become the duplicate canonical owner of every numeric software default. It must make the scientific role distinction unambiguous enough that D2/D3 cannot legally recouple the thresholds.

Run independent D1 Challenge/Review. Do not promote the revision to accepted-current authority until required stakeholder ratification is recorded.

### Gate B — D2 numerical-method reconciliation

After D1 acceptance, amend `docs/methods/mlff_numerical_algorithmic_method.md` only as far as needed to make the role-specific numerical predicates reconstructable:

- foundation CV checkpoint competence is a target-force-RMSE predicate distinct from production;
- current cycle/default foundation CV target-force competence is `0.045 eV/angstrom`;
- current default held-out target-force-RMSE acceptance is `0.045 eV/angstrom`;
- foundation production target checkpoint criterion remains `0.030 eV/angstrom`;
- same-valued CV monitor/held-out predicates remain separate evidence evaluations;
- non-force outer acceptance metrics retain their own units and may not supply the checkpoint target-force ceiling;
- fixed-budget training and all-fold/all-seed aggregation remain unchanged; and
- scratch remains unaffected.

If D2 deliberately treats the exact numeric values as cycle/configuration policy rather than durable algorithm law, state that delegation explicitly rather than duplicating authority across D2 and configuration prose.

Run independent D2 review including threshold-boundary, metric-unit, mode-confusion, identity and stale-evidence counterexamples.

### Gate C — D3 ownership and identity cutover

Reconstruct the current identities and all consumers before editing. Current code binds a `CheckpointAdmissibilityPolicy` digest containing the target ceiling into `PostSelectionMethodIdentity`, while `CvValidationPolicyIdentity` already owns outer acceptance and `FinalProductionPolicyIdentity` currently lacks a target ceiling. This is the coupling to remove.

Required D3 end state:

- one shared foundation method identity continues to bind method-bearing and genuinely shared replay/physical/integrity admissibility semantics;
- foundation CV target competence is bound by CV role policy before any fold checkpoint evidence exists;
- foundation production target quality is bound by final-production role policy before any final checkpoint evidence exists;
- CV and final production still bind the same shared `PostSelectionMethodIdentity` when only role thresholds differ;
- scratch and non-P5/generic TRAIN2 consumers keep their accepted behavior;
- policy/schema generation advances wherever serialized semantics changed; and
- old shared-threshold state is historical/stale rather than translated through a compatibility wrapper.

Prefer moving/narrowing an over-broad field/digest at its owner. Do not create a second method identity, second checkpoint evaluator, role-switch wrapper over the old shared `30 meV/angstrom` gate, or synchronized duplicate thresholds.

Review configuration ownership at this gate. In particular, do not blindly repurpose global `[acceptance].maximum_target_force_rmse_ev_per_angstrom` if it has scratch/P3/non-P5 consumers. A new role-specific field is justified only if the current owners cannot express the distinction without ambiguity; if introduced, it belongs to an existing role-policy surface and must be identity-bound.

Update current D3 architecture/ownership prose only where needed to state that role-specific target ceilings are policy descendants, not shared method fields.

### Gate D — D4 implementation and affected regression

Implement the smallest accepted Gate-C concretization.

For the default foundation path, generated/example configuration should expose the current outer-CV default:

```toml
[post_selection.cv]
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045
```

This line alone is **not** the complete repair: the foundation CV checkpoint target-force gate must also resolve to `0.045` from authenticated CV-role policy, and production must resolve to `0.030` from authenticated production-role policy. If an alternative outer metric is configured, preserve dimensional separation as specified above.

Update both hand-maintained and generated public configuration surfaces (`campaign.toml.example` and `_campaign_cli_core.py`) plus the user guide so `init` output, example text and runtime resolution agree. Do not silently rewrite existing explicit campaign values.

Reconcile `mlff_post_selection_p5_spec.md`, role-policy schemas/serialization, currentness/recovery, threshold provenance in logs/manifests, and all affected unit/integration tests. Retain historical readers only where they are already justified; historical readability must not authorize current execution.

Do not change the default CV horizon merely to claim speedup. Existing explicit CV-horizon controls remain the mechanism for running a shorter fixed-budget CV after this threshold coupling is removed.

GPU qualification remains deferred to the final release qualification package under standing project policy; this narrow change creates no intermediate user GPU gate.

### Gate E — assembled independent review and impact closure

Review the assembled D1-D4 candidate against this workplan and current accepted parent authority. Verify:

- foundation/scratch mode isolation;
- method-versus-role identity ownership and exact invalidation;
- schema/currentness behavior;
- metric dimensionality;
- real CV -> production authorization flow;
- no replay/physical/integrity weakening;
- no target-size/P3 drift;
- no early-stop leak; and
- no documentation/config generator divergence.

Reconcile only affected current documentation, semantic history, stale-evidence behavior and PEM closeout assessment. Archive the workplan only after independent review PASS and required authority acceptance are complete.

## 7. Reopen, simplification and human triggers

Reopen D1 if:

- foundation CV is actually relied upon as final-product/release qualification;
- `45 meV/angstrom` contradicts applicable empirical evidence;
- the remembered learning curve is not applicable to current foundation adaptation; or
- the change materially alters a scientific claim beyond bounded post-selection validation.

Reopen D2 if:

- checkpoint competence and held-out acceptance cannot be defined without metric/unit ambiguity;
- fixed-horizon CV plus the new competence criterion introduces an unrecognized numerical/selection bias;
- the role split changes estimator/selection behavior beyond threshold admissibility; or
- a mode-independent numerical criterion is actually required by accepted science.

Reopen D3 before adding machinery if:

- clean identity ownership appears to require a wrapper, shadow policy registry, duplicate checkpoint engine or synchronized threshold state;
- schema/currentness cannot be made fail-closed with existing identity structure; or
- a generic TRAIN2/P5-scratch consumer would be changed by the proposed refactor.

Prefer narrowing the over-broad shared owner or projecting the genuine shared subset before introducing a new durable abstraction.

Human ratification is required for the material D1/D2 authority revision before final acceptance. No active Serious Challenge is asserted after this workplan review; the explicit Challenge targets are final-qualification dependence, empirical applicability of `45 meV/angstrom`, and mode-scope leakage.

## 8. Impact, compatibility and history

Record the semantic evolution succinctly:

- the 2026-09-14 post-selection restoration preserved target/replay thresholds because changing them was out of scope;
- later review identified that the shared target ceiling coupled two distinct foundation roles;
- foundation production retains `30 meV/angstrom` target checkpoint quality;
- foundation CV competence/default held-out target-force acceptance becomes `45 meV/angstrom`;
- scratch remains unchanged; and
- the separation permits deliberately shorter fixed-horizon foundation CV without weakening production checkpoint quality or downstream release qualification.

Do not rewrite retired specifications to pretend they always contained this split.

Existing CV evidence under the old policy is not automatically current merely because `30 <= 45`. A prior `30 meV/angstrom` pass is numerically stronger on that one target metric, but current authorization also depends on exact method/policy/schema ancestry. No new historical-equivalence/migration mechanism is part of this cycle. Preserve old records as historical/readable where current compatibility already allows it, and require current evidence when the new policy identity demands it.

Likewise, a prior failure between `30` and `45 meV/angstrom` is not retroactively relabeled as a current pass without re-establishing the complete current policy/evidence lineage.

Perform closeout learning assessment after accepted implementation. Update PEM only if this cycle materially changes an existing lesson or meets admission criteria; ordinary chronology remains in Git/workplan history.

## 9. Acceptance and handoff

The workplan may close only when all of the following are true:

- D1 unambiguously distinguishes foundation-CV competence, production checkpoint quality and downstream release qualification;
- P5 scratch remains separately governed and unchanged;
- D2/configuration ownership of the current `45`/`30 meV/angstrom` predicates is unambiguous and non-duplicated;
- independent D1/D2 review and required stakeholder ratification are complete;
- shared `PostSelectionMethodIdentity` no longer changes merely because the CV/production target ceilings differ;
- genuinely shared replay/physical/integrity gates remain method-bound and still invalidate both roles when changed;
- foundation CV checkpoint competence resolves to `45 meV/angstrom` under the current policy;
- default foundation held-out target-force-RMSE acceptance resolves to `45 meV/angstrom`;
- foundation production checkpoint target quality remains `30 meV/angstrom`;
- alternative outer metrics cannot be misused as a target-force threshold;
- role-policy/schema/currentness/resume behavior is fail-closed and exact;
- new/generated configuration, example configuration and user guidance agree;
- existing explicit `0.030` CV configuration is not silently rewritten;
- TRAIN2 remains fixed-budget with no threshold early stopping;
- all required folds/seeds, monitor separation, replay and leakage constraints remain unchanged;
- affected regression includes intermediate `30 < RMSE <= 45` foundation CV pass, production fail, scratch-preservation, metric-dimensionality and identity-invalidation cases;
- assembled real-path CV -> production authorization passes; and
- no unrelated P1/P2/P3, P5-scratch or post-selection restoration semantics drifted.

A hidden shared `30 meV/angstrom` foundation-CV gate, a global `45 meV/angstrom` scratch change, a runtime-only unbound role switch, metric-unit aliasing, stale-schema reinterpretation, production-threshold relaxation, downstream qualification weakening, or unreviewed dependence on CV as final-product qualification is a blocking **No-Pass**.
