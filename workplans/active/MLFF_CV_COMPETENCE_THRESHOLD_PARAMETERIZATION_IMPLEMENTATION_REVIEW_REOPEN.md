---
kind: independent-implementation-review-reopen
protocol_version: 6.3.0
status: reopened
branch: fix/mlff-cv-competence-threshold-separation
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
prior_review_commit: 0fe85e9f67e90a7577edfa2f7a8180f169b553a2
repaired_implementation_commit: a0f477ef2a3a60660b98b357078a2944e3628126
reviewed_candidate_commit: 48a99a77a59232edc71b29a3f9a932ddec141778
parent_handoff: workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_ALIGNMENT.md
supersedes_closeout_for_current_state: workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md
review_disposition: NO-PASS
highest_open_owner: D4-evidence
---

# MLFF configurable-threshold implementation — independent re-review

## 0. Current disposition

Independent re-review of repaired candidate `48a99a77` is **NO-PASS on one remaining evidence gate only**. No Serious Challenge is raised against D1/D2. D3 ownership remains coherent. Static review closes the three prior blockers B1-B3 and finds the repaired D4 shape conforming.

The cycle remains open because the repair changed executable validation semantics in `post_selection_identity.py` and materially strengthened the assembled currentness oracle, but no fresh focused/affected regression realization for repaired implementation commit `a0f477ef` is recoverable from the repository or CI. The only repository-hosted workflow after that commit is the successful documentation-PDF build. Protocol 6.3 does not permit carrying the older pre-repair test realization forward as a PASS for changed executable behavior.

## 1. Prior blocker closure

### B1 — canonical authority/lifecycle representation: CLOSED

The accepted parameterized semantics are now incorporated into the broad canonical owners:

- D1: `docs/methods/mlff_scientific_method.md` §10.3/§11;
- D2: `docs/methods/mlff_numerical_algorithmic_method.md` §17.1/§23.7;
- D3: `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- D4: `docs/specs/training_data/mlff_post_selection_p5_spec.md` §12.1.

D1/D2 identify the revision as accepted/current and stakeholder-ratified, normative statements use configured `tau_cv`, `theta_cv`, and `tau_prod` with 45/45/30 only as generated defaults/calibration, and provenance routes to archived cycle records. The four temporary threshold-delta authority files were incorporated and removed, eliminating parallel current authority. Semantic-history routing was updated accordingly.

Archived review/workplan records may retain candidate-relative historical wording where their opening context makes that historical scope explicit; they are not current authority.

### B2 — fail-closed threshold typing: CLOSED statically

The existing `_finite_positive_threshold(...)` owner now rejects booleans and all non-`int`/`float` values before conversion, then rejects non-finite/nonpositive numeric values. `_configured_maximum_target_force_rmse(...)` returns the raw `[acceptance]` value so `FinalProductionPolicyIdentity` validates its original type rather than a pre-coerced float.

The focused test now drives real TOML through `_load_config` for all three public knobs and includes `true`, quoted numeric `"0.040"`, invalid string, nonpositive, `nan`, and `inf` counterexamples, plus positive integer/float acceptance. No parallel parser or compatibility layer was added.

### B3 — assembled `tau_cv`-only currentness oracle: CLOSED statically

The slow assembled test now performs a true checkpoint-only edit: it changes `tau_cv` while holding `theta_cv`, shared method inputs, and production policy fixed. It asserts:

- shared method digest unchanged;
- production-policy digest unchanged;
- CV policy digest changed only by `tau_cv`;
- `theta_cv` remains unchanged;
- prior accepted CV plan becomes stale and cannot authorize production;
- rerunning CV under tightened `tau_cv=0.040` rejects the 0.042 candidate; and
- rejected current CV does not authorize production.

A separate outer-only edit then changes `theta_cv`, preserving the dimension/ownership distinction.

## 2. Remaining blocker B4 — repaired executable evidence unavailable

The repair modifies executable behavior and executable oracles. The older recorded realization (25 fast + 2 slow + 96 affected tests, and the earlier 19-test/transitive-regression realization) predates this repair and is not admissible confirmation of `a0f477ef`/`48a99a77`.

The current review environment cannot execute the repository test suite because the repository is not mounted locally and outbound Git access is unavailable. GitHub exposes only the successful `Build documentation PDFs` workflow for `a0f477ef`; no current test/check status is present. Therefore required D4 acceptance is **UNAVAILABLE**, not PASS.

Before final re-review, execute and durably record against the repaired candidate at minimum:

```text
pytest -q tests/test_mlff_p5_cv_competence_threshold_separation.py
pytest -q \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r8_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_p5_r11_guards.py \
  tests/test_mlff_target_size_p5d_cv_acceptance.py \
  tests/test_mlff_target_size_p5e_production_and_restart.py \
  tests/test_mlff_target_size_p5g_assembled_integration.py \
  tests/test_mlff_p5_cv_no_admissible_outcome.py \
  tests/test_mlff_campaign_cli.py \
  tests/test_mlff_downstream_integration_closure.py
python -m compileall -q mdstats/training_data
git diff --check 8553ebe9ed86b24dfe910c9e43acc6230d3ece90...HEAD
```

If the maintained transitive affected closure used in the previous realization is broader, rerun that broader closure. PDF-only trailing-space behavior may be assessed consistently with the prior accepted evidence; non-PDF diff-check must pass. GPU/production-scale qualification remains deferred to the final complete-release package and is not required here.

The focused realization must actually execute the new real-TOML boolean/quoted-numeric cases and the repaired `tau_cv`-only assembled path; merely collecting those tests is insufficient.

## 3. Preserved PASS findings

Static re-review preserves these findings:

- all three foundation thresholds are independently configurable, default 45/45/30 meV/angstrom;
- each threshold has exactly one configuration source and existing role-policy owner;
- `PostSelectionMethodIdentity` carries no role target threshold;
- `post_selection_checkpoint_admissibility(...)` remains the one shared-constraints + authenticated-role-ceiling composition path;
- scratch remains separately governed and rejects the foundation-only CV checkpoint knob;
- explicit default and omission resolve identical policy identity;
- role-only changes preserve selective invalidation/currentness;
- no schema bump, threshold registry, synchronized production alias, P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, compatibility translator, wrapper, or second checkpoint engine was introduced;
- canonical D1-D4 authority is consolidated rather than split; and
- the documentation-PDF build for `a0f477ef` succeeded and generated current tracked PDFs at `48a99a77`.

## 4. Non-blocking cleanup

`mdstats/training_data/post_selection_identity.py` still comments that `FOUNDATION_CV_CHECKPOINT_MAXIMUM_TARGET_FORCE_RMSE_EV_PER_ANGSTROM` is a “fixed, identity-bound role value.” The constant is now the **default** for a configurable identity-bound role value. Correcting that comment is recommended before final closeout, but it does not alter executable semantics and is not a PASS blocker.

## 5. PEM/HAS and closeout state

Accepted PEM basis remains `4eabe2ae9783c7ff92f3a1093c37502a01380812`; the branch does not mutate `PROJECT-ENGINEERING-MEMORY.md`. Current HAS remains materially consistent with the prior closeout assessment:

- FF-002: APPLICABLE — exact role-policy ancestry/currentness remains fail-closed;
- SP-001: APPLICABLE — repair alters the existing owner rather than adding synchronized machinery;
- SP-002: APPLICABLE — strict typed threshold validation strengthens the authenticated boundary;
- SP-003: APPLICABLE — independent upstream/source/replay/common-monitor identities remain preserved;
- SP-004: APPLICABLE — the strengthened assembled test targets the real `cross-validate -> persisted CV acceptance -> train-production` path.

No new PEM family/application episode is admitted by this bounded repair. Final closeout/HAS statement should be reconciled only after B4 has executed and this review returns PASS.

## 6. Final re-review acceptance

Return PASS and re-close/archive when:

1. focused + affected regression + compile/static checks above execute against the repaired candidate with no candidate-attributable failure;
2. the new strict-type and `tau_cv`-only assembled counterfactuals are observed passing, not merely present in source;
3. documentation generation remains current;
4. no repair introduces duplicate threshold/protocol/checkpoint machinery; and
5. active lifecycle/closeout state is reconciled after, not before, independent PASS.

Until then the threshold-parameterization cycle remains **reopened / NO-PASS**.
