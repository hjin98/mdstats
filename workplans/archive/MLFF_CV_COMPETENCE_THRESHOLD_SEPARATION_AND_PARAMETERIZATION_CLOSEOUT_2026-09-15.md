# MLFF CV competence threshold separation and parameterization closeout — 2026-09-15

**Lifecycle status:** CLOSED / PASS / ARCHIVED after configurable-threshold authority alignment, D4 implementation, final independent re-review, affected regression, canonical consolidation, and closeout-learning/HAS reconciliation.

## 1. Final accepted state

Foundation post-selection adaptation has three independently configurable role-policy thresholds:

1. `tau_cv`: `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom`, generated default `0.045 eV/angstrom`;
2. `theta_cv`: `[post_selection.cv].acceptance_maximum`, generated default `0.045` under the default target-force outer metric, with units following `acceptance_metric`;
3. `tau_prod`: `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, generated default `0.030 eV/angstrom`.

These values are policy parameters, not immutable scientific constants. The accepted scientific/numerical invariants are role separation, exact evidence populations, all-required-fold/seed conjunction, fixed-budget training, dimensional separation of `theta_cv`, and selective currentness/invalidation.

Current canonical owners are:

- D1: `docs/methods/mlff_scientific_method.md` §10.3/§11;
- D2: `docs/methods/mlff_numerical_algorithmic_method.md` §17.1/§23.7;
- D3: `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- D4: `docs/specs/training_data/mlff_post_selection_p5_spec.md` §12.1.

The temporary threshold-delta authority files used during the cycle were incorporated into those broad owners and removed; Git history retains them as historical provenance.

## 2. Final independent review disposition

**PASS.** No Serious Challenge remains.

The accepted implementation shape is:

```text
PostSelectionMethodIdentity(shared checkpoint constraints only)
  + CvValidationPolicyIdentity(tau_cv + theta_cv)
  + FinalProductionPolicyIdentity(tau_prod)
  -> role plan / run plan
  -> authenticate exact method + role-policy ancestry
  -> one effective CheckpointAdmissibilityPolicy
  -> CV acceptance or production evidence
```

No P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, threshold registry, synchronized production alias, compatibility translator, wrapper, per-checkpoint role field, or second checkpoint engine was introduced.

Strict configuration typing is fail-closed: all three threshold surfaces accept only finite positive TOML integer/float values; booleans, strings/quoted numerics, non-finite values, and nonpositive values are rejected before identity/execution. Production preserves the raw configured value until the owning policy identity validates it.

The assembled currentness oracle changes `tau_cv` alone while holding `theta_cv`, shared method inputs, and production policy fixed; it proves the old CV plan/acceptance becomes stale, shared method and production policy remain current, and dependent production authorization is refused until CV is rerun under the new policy.

## 3. Executed acceptance evidence

Final repaired-candidate execution record:

- focused threshold tests: **47 fast passed**;
- assembled threshold end-to-end tests: **2 slow passed**;
- affected regression: **112 files** at `-n 16`: **1740 passed, 93 failed, 2 skipped**;
- all 93 failures are `*_specification.py` documentation-sync tests; the same test ids fail on the unmodified comparison state with identical messages, so there are **0 candidate-attributable regression failures**;
- structural semgrep check: **pass**, no remaining threshold config value is converted with `float()` before validation;
- `git diff --check`: **clean**;
- documentation-PDF workflow after the repair: **success**, with tracked generated PDFs current.

The affected execution surface imports and exercises the changed owner and its transitive consumers; no separate syntax-only compile gate remains material after this broader executable realization.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains intentionally deferred to the final complete-release package and is not an intermediate blocker.

## 4. Preserved behavior

Final review confirms:

- generated/default foundation behavior is `45 / 45 / 30 meV/angstrom`;
- explicit default and omission produce identical role-policy identity;
- an alternate outer metric never donates its threshold to `tau_cv`;
- `tau_cv`/`theta_cv` edits move CV lineage and stale dependent production authorization without moving shared method or production policy;
- `tau_prod` edits move production lineage only;
- genuinely shared replay/physical/integrity constraint edits move the shared method and both dependent roles;
- stored classifications are never re-thresholded into current evidence;
- training horizons remain fixed and thresholds do not early-stop training;
- scratch keeps pre-separation behavior and rejects the foundation-only CV checkpoint field; and
- generated config, shipped example, guide, CLI spec, P5 spec, D1/D2 papers, and D3 architecture agree.

## 5. PEM basis / HAS / closeout learning

Accepted PEM basis remains `4eabe2ae9783c7ff92f3a1093c37502a01380812`.

Applicable lessons remain satisfied:

- FF-002 — authenticated role-policy/run ancestry prevents stale reuse;
- SP-001 — repair reused and simplified existing owners rather than adding synchronization machinery;
- SP-002 — strict fail-closed typing/currentness protects semantic identity;
- SP-003 — independent source/replay/common-monitor durable boundaries remain preserved;
- SP-004 — real-owner `cross-validate -> persisted CV acceptance -> train-production` integration is explicitly exercised.

The bounded repair does not constitute a new independent failure-family or success-pattern episode. No `PROJECT-ENGINEERING-MEMORY.md` mutation is required.

## 6. Final state

```text
D1 threshold authority                PASS / accepted-current
D2 numerical policy                   PASS / accepted-current
D3 architectural ownership            PASS / accepted-current
D4 specification                      PASS / current
D4 implementation                     PASS / conforming
Focused threshold qualification       PASS / 47 fast + 2 slow
Affected regression                   PASS / 0 candidate-attributable failures
Structural threshold coercion check   PASS
Git diff structural check             PASS / clean
Canonical documentation & PDFs        PASS / consolidated & rebuilt
Parent workplans/reviews               CLOSED / archived
PEM / HAS reconciliation              PASS / no PEM mutation
Operational GPU/release qualification DEFERRED to final release package
```

The CV competence threshold separation/parameterization cycle is closed.