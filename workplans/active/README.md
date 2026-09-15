# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Current active MLFF work

The MLFF CV competence threshold separation/parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` remains **reopened / NO-PASS**, but the three prior implementation-review blockers are now closed statically on repaired candidate `48a99a77a59232edc71b29a3f9a932ddec141778` (`a0f477ef2a3a60660b98b357078a2944e3628126` before CI PDF regeneration).

Current review contract:

`MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_IMPLEMENTATION_REVIEW_REOPEN.md`

The accepted design is unchanged and not challenged: all three foundation post-selection thresholds are independently configurable role-policy parameters, with generated/current defaults `45 / 45 / 30 meV/angstrom` for CV checkpoint competence / default held-out target-force acceptance / fresh-production checkpoint quality.

Current canonical owners are consolidated:

- D1: `docs/methods/mlff_scientific_method.md` §10.3/§11;
- D2: `docs/methods/mlff_numerical_algorithmic_method.md` §17.1/§23.7;
- D3: `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- D4: `docs/specs/training_data/mlff_post_selection_p5_spec.md` §12.1.

The temporary threshold-delta authority files were incorporated and removed; no parallel current threshold authority remains. The existing architecture is preserved: `PostSelectionMethodIdentity` owns shared constraints, `CvValidationPolicyIdentity` owns CV checkpoint + outer policy, `FinalProductionPolicyIdentity` owns production policy, and one existing `post_selection_checkpoint_admissibility(...)` path composes the effective run policy.

Static re-review closes:

1. **Canonical/lifecycle representation drift:** D1/D2 are accepted/current and parameterized; history/provenance routes are reconciled; broad canonical D3/D4 own the threshold semantics.
2. **Fail-closed threshold typing:** the existing threshold validator rejects booleans/strings before conversion, production passes its raw configured value to the policy identity, and real-TOML counterexamples cover all three threshold knobs.
3. **Confounded assembled currentness oracle:** the slow real-owner path now changes only `tau_cv` while holding `theta_cv`, shared method and production policy fixed, proves prior CV acceptance stale, reruns CV under the tightened ceiling, and separately tests `theta_cv`-only invalidation.

One blocker remains:

**Fresh executable evidence for the repaired candidate is unavailable.** The older recorded 25/2/96 and 19-test/transitive-regression realizations predate the strict validator and repaired assembled oracle. The repository-hosted workflow after `a0f477ef` is the successful documentation-PDF build only; no current focused/affected test realization is recoverable. Protocol 6.3 requires the focused threshold suite, affected regression, compile/static checks and real assembled path to execute against the repaired candidate before PASS.

Production-scale GPU/CuEq/LAMMPS/MLIAP release qualification remains deferred to the final complete-release package and is not an intermediate gate for this cycle.

The previously archived closeout `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md` remains historical evidence of an attempted closure and is superseded for current lifecycle state until the active review returns PASS.

Completed/superseded workplans belong under `workplans/archive/`.
