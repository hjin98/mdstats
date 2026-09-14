---
kind: abstraction-concretization-change-plan
protocol_version: 6.3.0
status: proposed
branch: fix/mlff-cv-competence-threshold-separation
baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
highest_affected_domain: D1
---

# MLFF CV Competence Threshold Separation Workplan

## Background and terminology

The current post-selection machine-learned force-field (MLFF) method uses the same target-force root-mean-square error (RMSE) ceiling, nominally `0.030 eV/angstrom`, in two roles that now have different scientific purposes:

1. **production-quality acceptance** — the final post-selection model is expected to reach the established `30 meV/angstrom` target-force RMSE regime; and
2. **post-selection cross-validation (CV) competence/robustness evidence** — disposable fold models are trained only to test whether the frozen training method works consistently on held-out development evidence.

The stakeholder's prior training-curve study indicates that error falls rapidly at first and then slows markedly through roughly the `40-20 meV/angstrom` regime. The existing `30 meV/angstrom` production threshold intentionally lies inside that slow-convergence region. Requiring every disposable CV fold model to reach the same production-quality threshold therefore spends substantial CV compute on late convergence that is not necessary to answer the narrower CV question.

For this cycle, the proposed CV competence threshold is:

```text
T_CV = 0.045 eV/angstrom = 45 meV/angstrom
```

while the production-quality threshold remains:

```text
T_PRODUCTION = 0.030 eV/angstrom = 30 meV/angstrom
```

This is a narrow semantic separation, not a redesign of post-selection CV, checkpoint monitoring, replay retention, or training termination.

## 1. Outcome and authority

### Protected problem/stakeholder outcome

Make post-selection CV a quicker robustness/competence test without weakening final production-model accuracy requirements. A CV fold should demonstrate that the frozen foundation-adaptation method can reliably reach the clearly competent pre-slow-convergence regime on held-out development evidence. Final production remains responsible for reaching the stricter production-quality regime.

### Highest potentially affected semantic domain

**D1 scientific formulation.** The present D1 wording makes post-selection CV ask whether the frozen method "performs acceptably" on held-out development evidence while the currently restored threshold semantics preserve the same `30 meV/angstrom` target criterion used for production. Separating CV competence from production quality changes the interpretation of what CV evidence is intended to establish.

### Applicable accepted parent abstractions and constraints

Preserve the current accepted post-selection restoration except for the threshold-role coupling explicitly changed here. In particular preserve:

- foundation-adaptation method and objective semantics;
- one campaign-common exact target checkpoint monitor outside every CV fold;
- default three-fold CV geometry and explicit fold-count override;
- required CV seeds and all-required-fold/all-required-seed acceptance;
- held-out-fold exclusion from training and checkpoint selection;
- fresh fold-local fitted training state and fresh model/optimizer state;
- target/replay/physical/integrity checkpoint admissibility structure;
- replay-retention scientific requirement and its current threshold;
- fresh final production using the accepted production method;
- fixed-budget TRAIN2 semantics and prohibition on target/replay performance-driven termination; and
- the existing distinction between CV-specific horizon and final-production horizon.

### Current normative owners

- D1: `docs/methods/mlff_scientific_method.md`
- D2: `docs/methods/mlff_numerical_algorithmic_method.md`
- D3/D4 descendants include the post-selection identity/policy, checkpoint-admissibility policy, CV acceptance evaluator, configuration surface, serialization/provenance, and tests.

### Proposed authority and human-ratification state

Stakeholder direction authorizes drafting the following proposed authority:

- post-selection CV uses a **CV competence target-force RMSE ceiling of `0.045 eV/angstrom`**;
- final production retains the **production target-force RMSE ceiling of `0.030 eV/angstrom`**;
- the two ceilings are semantically distinct and must not be represented as one shared target-accuracy invariant;
- CV remains a robustness/competence test and does not become the final product-accuracy qualification step.

The D1/D2 paper edits remain proposed until the normal independent review/falsification and required stakeholder ratification of the assembled authority revision are complete.

## 2. Governing contract

### Invariants

1. **Production quality is unchanged.** No change may relax the final-production `30 meV/angstrom` target-force RMSE requirement.
2. **CV competence is role-specific.** CV checkpoint target competence and outer held-out fold acceptance use `45 meV/angstrom`, not the production `30 meV/angstrom` ceiling.
3. **All required folds and seeds still pass individually.** Mean fold performance cannot rescue a failed fold; missing folds/seeds are not passes.
4. **Cross-fold dispersion remains diagnostic-only in this cycle.** Do not introduce a new hard dispersion criterion or replace the existing per-fold pass predicate.
5. **Replay retention is unchanged.** This change does not relax, reinterpret, or duplicate the replay-degradation requirement.
6. **Physical/integrity admissibility is unchanged.** Non-finite metrics, identity mismatch, infeasible reference-energy fitting, missing required evidence, or other existing hard failures remain failures.
7. **Held-out folds remain evaluation-only.** A held-out fold may not choose checkpoints, fit preprocessing/reference energies, provide gradients, or otherwise leak backward into fold training.
8. **Common monitor semantics are unchanged.** CV continues to use the accepted campaign-common checkpoint monitor external to all folds.
9. **Fixed-budget training remains fixed-budget.** Do not add target-threshold early stopping or performance-driven termination to make this change appear faster.
10. **CV horizon remains independently controllable.** Existing CV-specific budget/horizon controls may be shortened because the CV competence target no longer requires production-level late convergence. This workplan does not invent a new optimizer schedule or stopping rule.
11. **Method identity must distinguish threshold role correctly.** A CV-only threshold change must invalidate/recompute CV policy/evidence as appropriate without falsely changing production quality semantics; a production-threshold change must remain a production/method change with its proper invalidation surface.
12. **No hidden fallback to the shared 30 meV/angstrom gate.** A fold at, for example, `42 meV/angstrom` that satisfies all other CV checkpoint-admissibility requirements must not be rejected merely because a production-only target ceiling is still consulted on the CV path.

### Cycle-scoped decisions

For this cycle freeze:

```text
CV target competence/checkpoint ceiling = 0.045 eV/angstrom
CV outer held-out target-force RMSE ceiling = 0.045 eV/angstrom
production target/checkpoint ceiling = 0.030 eV/angstrom
CV aggregation = all required folds and variants
CV dispersion policy = diagnostic_only
TRAIN2 termination = fixed budget, no performance-driven early stopping
```

These numerical values are authority for this cycle once the D1/D2 revision is accepted. The software representation is delegated provided it preserves the role separation and identity/invalidation behavior.

### Delegated space

D3/D4 may choose the smallest clean representation for role-specific threshold resolution. Prefer altering or splitting the existing policy ownership over adding wrappers, compatibility shims, duplicated acceptance engines, or another threshold-control subsystem. Existing policy/configuration objects should be reduced or rewired where possible.

### Non-goals

This work does **not**:

- change the `30 meV/angstrom` production target;
- choose a new universal default CV epoch count without supporting evidence;
- add threshold-driven early stopping;
- redesign fold construction, fold count, seed policy, or aggregation;
- promote cross-fold dispersion into a new hard acceptance metric;
- change the common monitor membership or size;
- alter UniversalLoss/foundation-adaptation objective semantics;
- relax replay degradation, physical, provenance, or integrity gates;
- alter target-size selection P1/P2/P3 semantics; or
- revisit training-from-scratch semantics unless a direct shared-policy dependency is discovered and must be disentangled without changing its behavior.

## 3. Adequacy and affected surface

### Upstream meaning the child abstraction must preserve

D2 must make the distinction operationally unambiguous:

- **CV checkpoint competence:** the checkpoint-selection/admissibility process used during a CV fold may accept target-monitor RMSE up to `0.045 eV/angstrom`, subject to all unchanged replay/physical/integrity rules.
- **CV held-out acceptance:** after the representative checkpoint is frozen, the held-out fold target-force RMSE must be `<= 0.045 eV/angstrom`.
- **production checkpoint quality:** final-production checkpoint admissibility retains `<= 0.030 eV/angstrom`.

The `45 meV/angstrom` CV threshold is not claimed to be final model adequacy. It is a competence boundary deliberately placed just above the empirically observed slow-convergence regime so CV can interrogate robustness without requiring every disposable model to pay the production convergence cost.

### Materially dependent descendants

Review and update at least these surfaces, following actual dependency discovery rather than treating this list as exhaustive:

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`;
- `mdstats/training_data/post_selection_identity.py`;
- `mdstats/training_data/train2_policy.py` or the narrower current owner of checkpoint target thresholds;
- `mdstats/training_data/post_selection_cv_acceptance.py`;
- campaign/example configuration and configuration parsing;
- persisted CV/method identities, digests, resume/staleness checks, and human-readable manifests/logs that expose the governed thresholds;
- unit/integration tests covering CV versus production policy resolution and stale-evidence invalidation; and
- current architecture/manual prose only where it duplicates or routes the affected threshold semantics.

### Unaffected siblings/evidence

Preserve without unnecessary churn:

- P1/P2 neutral evidence and ordering;
- P3 target-size screening objective/evaluation semantics;
- common monitor membership selection and exact size;
- CV fold membership and protected-relation logic;
- replay corpus construction and replay metric definition;
- foundation checkpoint/head identity;
- reference-energy fitting method;
- training loss functional;
- production horizon semantics; and
- existing evidence that does not depend on equality of the CV and production target thresholds.

### Historical applicability

The immediately preceding post-selection restoration deliberately preserved target/replay thresholds because threshold semantics were outside that restoration's intended scope. This workplan explicitly reopens only the **target threshold role coupling**. That preservation decision must not be treated as evidence that CV and production thresholds are scientifically required to be identical.

Historical CV specifications that characterize CV as robustness evidence are relevant rationale, but current accepted D1/D2 authority remains the baseline to amend; retired documents do not directly govern the change.

## 4. Evidence and falsification

### Reverse-semantic verification question

Starting from the assembled D4 behavior, can a reviewer reconstruct exactly this result without relying on comments or workplan prose?

```text
CV fold checkpoint/held-out target competence: 45 meV/angstrom
final-production target quality:              30 meV/angstrom
replay/physical/integrity gates:               unchanged
all required CV folds/seeds:                   individually required
termination:                                   fixed budget
```

If not, the concretization is inadequate.

### Required falsification cases

At minimum demonstrate:

1. **CV-only intermediate case:** a CV checkpoint/held-out result with target-force RMSE between `30` and `45 meV/angstrom` can pass the target criterion when all other CV gates pass.
2. **CV boundary failure:** a CV fold above `45 meV/angstrom` fails with the correct reason.
3. **production preservation:** an otherwise identical production checkpoint/result above `30 meV/angstrom` remains inadmissible.
4. **exact boundaries:** equality at `0.045` passes the CV `<=` predicate and equality at `0.030` passes the production `<=` predicate; just-above values fail their respective roles within the existing numerical comparison convention.
5. **replay independence:** relaxing the CV target threshold does not relax replay-degradation acceptance.
6. **all-fold semantics:** one failing CV fold still causes overall CV failure even if the mean is below `45 meV/angstrom`.
7. **identity/invalidation:** changing only the CV threshold changes CV-policy identity/stales prior CV authorization as designed but does not masquerade as a production-quality threshold change; changing production target threshold retains its proper broader identity consequence.
8. **resume/recovery:** resumed CV cannot reuse evidence generated under the old `30 meV/angstrom` CV policy as though it were generated under the new `45 meV/angstrom` policy unless existing compatibility rules explicitly and correctly prove equivalence. Prefer stale/recompute over unsafe reinterpretation.
9. **no early-stop leak:** training still consumes the configured fixed CV horizon rather than stopping when `45 meV/angstrom` is first crossed.

### Empirical adequacy of 45 meV/angstrom

The stakeholder's prior learning-curve observation is the current calibration basis: fast initial convergence followed by marked slowdown around the `40-20 meV/angstrom` region, with `30 meV/angstrom` chosen as a production-quality threshold inside that slow regime. `45 meV/angstrom` is therefore intentionally placed just above the slow-convergence region.

This narrow change does not require inventing a fresh calibration campaign before implementation. If existing repository evidence materially contradicts that premise—for example, accepted fold trajectories commonly plateau above `45 meV/angstrom` despite otherwise healthy training, or the claimed convergence knee is absent—raise the contradiction to D1/D2 rather than silently widening the threshold.

### Strongest Challenge to attempt

Attempt to falsify the claimed role separation by asking whether CV is currently relied upon anywhere as the **only** quantitative final-product accuracy qualification. If a dependent workflow treats CV's `30 meV/angstrom` gate as its sole assurance of production accuracy, weakening that gate without adding/identifying the actual production qualification owner would be unsafe and must reopen D1 before implementation.

Absent such a dependency, the proposed split is coherent: CV establishes method competence/robustness; final production and downstream qualification establish final-model quality.

## 5. Concretization sequence

### Gate A — D1 authority reconciliation

Amend the scientific method paper narrowly:

- distinguish **CV competence/robustness adequacy** from **production-quality adequacy**;
- define `45 meV/angstrom` as the CV target-force competence ceiling;
- preserve `30 meV/angstrom` as the production target-force quality ceiling;
- state that the CV threshold is deliberately positioned before the observed slow-convergence region and is not final-product qualification;
- preserve all-fold/all-seed held-out evidence semantics, common monitor separation, replay requirements, and leakage prohibitions; and
- remove/qualify any statement that still implies target acceptance thresholds are universally identical across CV and production.

Run an independent D1 Challenge/Review. Do not proceed as though the edit were accepted current authority until required stakeholder ratification is recorded.

### Gate B — D2 numerical-method reconciliation

After D1 acceptance, amend D2 so the two numerical predicates are explicit and reconstructable:

```text
CV target monitor/checkpoint competence <= 0.045 eV/angstrom
CV held-out target-force RMSE          <= 0.045 eV/angstrom
production target monitor/checkpoint   <= 0.030 eV/angstrom
```

Preserve fixed-budget TRAIN2 behavior and existing fold/seed aggregation. Define the role-specific policy identity/invalidation consequence without prescribing unnecessary software decomposition.

Run independent D2 Review including boundary-value, role-confusion, and stale-evidence counterexamples.

### Gate C — D3 policy/identity repair

Reconstruct the current policy ownership before editing. Remove the accidental semantic coupling whereby one shared target-force checkpoint ceiling forces CV to satisfy the production target.

Preferred architecture:

- retain genuinely shared checkpoint gates in the common method/policy (finite metrics, replay, physical/integrity constraints, foundation/method identity as applicable);
- resolve the target-force RMSE ceiling from the **execution role** (`CV` versus `production`) or from two clearly owned policies already present in the architecture;
- keep the outer CV held-out threshold in CV policy identity; and
- ensure threshold provenance is visible in manifests/logs and included in the identities that govern reuse/staleness.

Do not add a wrapper around the current `30 meV/angstrom` shared gate. Alter/split the existing authority representation so the implementation directly expresses the accepted D2 distinction.

### Gate D — D4 implementation and affected regression

Implement the minimum code/configuration changes required by Gate C. Update defaults/examples so the normal path resolves:

```toml
[post_selection.cv]
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.045
```

and ensure CV checkpoint admissibility uses the same CV-role `0.045` target ceiling while production retains `0.030` from its production-quality owner.

Do not implement performance-driven early stopping. Do not change the default CV horizon merely to claim runtime improvement. Existing explicit CV horizon controls remain the mechanism for choosing a shorter fixed CV run; a future default-horizon change requires its own evidence if desired.

Run affected unit/integration tests and the falsification cases above. GPU qualification remains deferred to the final release qualification package under the standing project workflow; this workplan must not create an intermediate user GPU-test gate.

### Gate E — assembled review and impact closure

Review the assembled D1-D4 candidate against this workplan and current accepted parent authority. Verify no unrelated post-selection restoration semantics drifted. Reconcile current docs/config examples, stale-evidence behavior, identity/version migrations if required, and archive the workplan only after the branch is genuinely closed.

## 6. Reopen / simplification / human triggers

Reopen D1 if:

- evidence shows CV is materially serving as final-product accuracy qualification rather than competence/robustness evidence;
- `45 meV/angstrom` contradicts available accepted empirical evidence about the convergence regime; or
- changing CV accuracy interpretation alters a downstream scientific conclusion beyond the bounded post-selection validation role.

Reopen D2 if:

- a separate CV checkpoint ceiling and held-out ceiling cannot be defined without numerical ambiguity;
- fixed-horizon CV plus `45 meV/angstrom` creates an unrecognized estimator/selection bias; or
- identity/reuse semantics cannot distinguish evidence produced under the two threshold policies.

Reopen D3 before adding machinery if the clean repair appears to require wrappers, duplicate acceptance engines, or compatibility shims. First test whether existing shared policy ownership is simply too broad and should be narrowed.

Human ratification is required for the material D1/D2 authority mutation before final acceptance. No active Serious Challenge is asserted at plan creation; the explicit Challenge target is whether any dependent workflow relies on the old CV `30 meV/angstrom` gate as final-product qualification.

## 7. Impact and history

Record the semantic evolution succinctly in the current authority/history mechanism used by the repository:

- the earlier restoration preserved the `30 meV/angstrom` threshold because changing it was out of scope;
- subsequent review identified that this preservation coupled two scientifically distinct roles;
- production remains `30 meV/angstrom`;
- CV competence becomes `45 meV/angstrom`, calibrated from the observed fast-to-slow convergence transition; and
- the change enables deliberately shorter fixed-horizon CV configurations without weakening final production accuracy.

Do not rewrite retired historical specifications to pretend they always contained the new threshold. Preserve them as historical evidence and update only current authority plus any derived current documentation that would otherwise misstate the accepted method.

Existing CV acceptance evidence generated under the old policy must be handled according to explicit applicability rules. A prior pass at `30 meV/angstrom` is numerically stronger on the target metric than `45 meV/angstrom`, but policy identity and method changes may still make reuse invalid; do not infer reuse solely from threshold monotonicity. A prior failure between `30` and `45 meV/angstrom` is not automatically current passing evidence unless all other current method/identity requirements are proven applicable.

## 8. Acceptance and handoff

The workplan may close only when all of the following are true:

- D1 explicitly owns and distinguishes CV competence from production quality;
- D1 records `45 meV/angstrom` CV and `30 meV/angstrom` production target-force thresholds;
- D2 concretizes the two role-specific predicates without ambiguity;
- independent D1/D2 review and required human ratification are complete;
- D3/D4 no longer route CV through a production-only `30 meV/angstrom` target gate;
- CV checkpoint competence and outer held-out acceptance both use `45 meV/angstrom`;
- final production still uses `30 meV/angstrom`;
- replay, physical, integrity, all-fold/all-seed, monitor-separation, and leakage constraints remain unchanged;
- TRAIN2 remains fixed-budget with no threshold early stopping;
- identity/staleness/recovery behavior is correct for the changed CV policy;
- affected tests include the `30 < RMSE <= 45 meV/angstrom` role-separation case and production-preservation case;
- no unrelated P1/P2/P3 or post-selection method semantics drifted; and
- required documentation/evidence/history impact closure is complete.

A missing required review, stale identity path, hidden shared `30 meV/angstrom` CV gate, production-threshold relaxation, or unreviewed dependency that uses CV as final-product qualification is a blocking **No-Pass**.
