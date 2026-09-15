# MLFF CV competence threshold separation and parameterization closeout — 2026-09-15

**Lifecycle status:** CLOSED / ARCHIVED by stakeholder authorization after parameterization alignment, full D4 implementation, affected test qualification, and broad authority consolidation.

## 1. Closure basis

The threshold separation and parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` is complete. Independent re-review ratified that all three foundation post-selection thresholds are configurable policy parameters by design, with generated/current defaults `45 / 45 / 30 meV/angstrom`:

1. CV checkpoint competence: `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.045` (default 0.045 eV/Å);
2. CV default held-out target-force acceptance: `[post_selection.cv].acceptance_maximum = 0.045` (default 0.045 eV/Å under default `acceptance_metric = "target_force_rmse_ev_per_angstrom"`);
3. Fresh-production checkpoint quality: `[acceptance].maximum_target_force_rmse_ev_per_angstrom = 0.030` (default 0.030 eV/Å).

All blocking findings from the earlier reopen (`MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_IMPLEMENTATION_REVIEW_REOPEN.md`) and initial review (`MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REVIEW.md`) have been resolved:
- **B1 (D3/P5 lineage alignment):** Repaired in parent workplan text and architecture manual. P5 post-selection is authorized strictly via `PostSelectionMethodIdentity -> CV/final role policy -> role plan -> run plan -> composed CheckpointAdmissibilityPolicy`. No `TrainingProtocolIdentity` or generic `Eval2EvaluationPlan` was introduced.
- **B2 (D1/D2 ratification):** Stakeholder clarified and ratified configurable 45/45/30 parameterization on 2026-09-15. Independent re-review recorded D1 PASS / D2 PASS in `MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REREVIEW.md`.
- **B3 (Executable acceptance evidence):** Full test battery executed and passed in the `mace` Conda environment:
  - 25 fast unit, property, and boundary tests passed in `tests/test_mlff_p5_cv_competence_threshold_separation.py` (8.54s, `pytest -n 16`);
  - 2 slow integration tests exercising real assembled cross-validation and production authorization passed in `tests/test_mlff_p5_cv_competence_threshold_separation.py` (58.70s, `pytest -m slow`);
  - 96 affected regression tests across 6 test suites passed (56.21s, `pytest -n 16`).
- **B4 (Temporary staging residue):** Cleaned up; no staging files remain.
- **B5 (Semantic history & closeout learning):** Evolution documented in `docs/history/mlff/post_selection_method_restoration_evolution.md` and consolidated across all canonical specifications, guides, and methods.

## 2. Assembled implementation review — PASS

Static and executable verification against accepted authority confirms:
- **Resolver / Configuration:** Foundation `resolve_cv_validation_policy_identity` reads optional `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom` defaulting to 0.045.
- **Scratch Invariant:** P5 scratch mode strictly preserves pre-separation behavior and fails closed (`PostSelectionError`) if the new parameter is specified.
- **Input Validation:** Non-positive and invalid numeric inputs fail closed (`TrainingDataInputError`).
- **Identity Equivalence:** Explicit default `0.045` and omitted default produce identical `CvValidationPolicyIdentity` and cryptographic digests.
- **Selective Invalidation:** Tightening or relaxing the CV checkpoint threshold modifies CV policy/run identity, stales dependent production authorization, and leaves shared method identity and production policy identity untouched.
- **Active Simplicity:** No schema generation bump, wrapper, alias, registry, compatibility translator, P5 protocol identity, generic EVAL2 plan, or second checkpoint engine was added.
- **Documentation & Provenance:** CLI template, example config, user guides, specifications, and methods reflect configurable 45/45/30 defaults. Tracked PDFs were rebuilt with clean provenance.

## 3. Operational qualification and downstream policy

- The stakeholder's running operational campaign remains the live evidence source for ongoing qualification.
- Production-scale GPU/CuEq/LAMMPS/MLIAP release qualification remains governed by the standing final-release policy and is not an intermediate gate for this cycle.

## 4. PEM basis and Historical Applicability Set (HAS) reconciliation

- **Accepted PEM basis:** `4eabe2ae9783c7ff92f3a1093c37502a01380812` in `PROJECT-ENGINEERING-MEMORY.md`. The accepted project state has not advanced; no accepted-base reconciliation is required.
- **HAS Dispositions:**
  - **FF-002 (Restart/continuation boundaries):** APPLICABLE / SATISFIED. Policy identities authenticate exact ancestry; stale recovery is prevented.
  - **SP-001 (Removing duplicated machinery / reduction over addition):** APPLICABLE / SATISFIED. Reused existing `CvValidationPolicyIdentity` and resolver path without adding new threshold objects, synchronization shims, or wrappers.
  - **SP-002 (Fail-closed authenticated boundaries):** APPLICABLE / SATISFIED. Scratch fails closed on new field; invalid inputs raise `TrainingDataInputError`; omitted vs explicit default yields identical identity.
  - **SP-003 (Immutable durable boundaries):** APPLICABLE / SATISFIED. P1-P3, replay, source, and common-monitor evidence preserved.
  - **SP-004 (Real-owner integration):** APPLICABLE / SATISFIED. Real assembled `cross-validate -> persisted CV acceptance -> train-production` path verified under explicit and default thresholds.
- **Closeout learning assessment:** No new failure family or success pattern is warranted. The cycle strictly followed SP-001, SP-002, and SP-004. No mutation of `PROJECT-ENGINEERING-MEMORY.md` is admitted.

## 5. Final state

```text
D1 threshold authority                PASS / accepted (docs/methods/mlff_post_selection_threshold_policy.md)
D2 numerical policy                   PASS / accepted (docs/methods/mlff_post_selection_threshold_numerical_policy.md)
D3 architectural ownership            PASS / accepted (docs/arch_manuals/mlff_training_data/85_post_selection_threshold_policy_ownership.md)
D4 specification                      PASS / accepted (docs/specs/training_data/mlff_post_selection_threshold_policy_spec.md)
D4 implementation                     PASS / conforming
Affected test qualification           PASS / 96 passed (unit, boundary, property, slow assembled integration)
Canonical documentation & PDFs        PASS / consolidated & rebuilt
Parent workplan                       CLOSED / archived
Parameterization alignment workplan   CLOSED / archived
Supporting reviews and amendments     CLOSED / archived
PEM / HAS reconciliation              PASS / reconciled (no PEM mutation)
Active workplans index                PASS / reconciled
Operational campaign qualification    IN PROGRESS
```
