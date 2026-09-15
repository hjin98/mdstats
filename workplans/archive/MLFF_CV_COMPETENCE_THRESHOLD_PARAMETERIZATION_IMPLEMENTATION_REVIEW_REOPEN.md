---
kind: independent-implementation-final-review
protocol_version: 6.3.0
status: pass
branch: fix/mlff-cv-competence-threshold-separation
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
prior_review_commit: 77c2ba997856f701e09ce40afed20df79f88db0c
repaired_implementation_commit: a0f477ef2a3a60660b98b357078a2944e3628126
reviewed_candidate_commit: 48a99a77a59232edc71b29a3f9a932ddec141778
review_disposition: PASS
highest_open_owner: none
---

# MLFF configurable-threshold implementation — final independent review

## 0. Disposition

**PASS.** No Serious Challenge remains. Accepted D1/D2 semantics, D3 ownership, D4 specification, executable behavior, canonical representation, affected regression, and lifecycle closure are mutually consistent.

The final repair preserves the accepted architecture: `PostSelectionMethodIdentity` owns only shared checkpoint constraints; `CvValidationPolicyIdentity` owns foundation `tau_cv` and `theta_cv`; `FinalProductionPolicyIdentity` owns `tau_prod`; and the existing `post_selection_checkpoint_admissibility(...)` path composes the authenticated role ceiling with shared constraints. No P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, threshold registry, synchronized production alias, compatibility translator, wrapper, or second checkpoint engine was introduced.

## 1. Prior blocker closure

### B1 — canonical authority/lifecycle representation: PASS

The configurable-threshold semantics are consolidated into the broad canonical owners:

- D1: `docs/methods/mlff_scientific_method.md` §10.3/§11;
- D2: `docs/methods/mlff_numerical_algorithmic_method.md` §17.1/§23.7;
- D3: `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- D4: `docs/specs/training_data/mlff_post_selection_p5_spec.md` §12.1.

The former threshold-delta authority files were incorporated and removed. The canonical owners state that `tau_cv`, `theta_cv`, and `tau_prod` are independently configurable policy parameters with generated defaults `45 / 45 / 30 meV/angstrom`, not immutable scientific constants.

### B2 — fail-closed threshold typing: PASS

The existing `_finite_positive_threshold(...)` owner rejects booleans and non-numeric values before conversion, then rejects non-finite/nonpositive numerics. `_configured_maximum_target_force_rmse(...)` preserves the raw `[acceptance]` value until the owning policy identity validates its original type.

Focused tests exercise real TOML for all three public thresholds and cover booleans, quoted numerics, invalid strings, nonpositive values, `nan`, `inf`, and valid positive integer/float values.

A structural semgrep pass additionally found no remaining threshold-configuration path that converts a configured value with `float()` before validation.

### B3 — exact role currentness: PASS

The assembled `cross-validate -> persisted CV acceptance -> train-production` oracle now changes only `tau_cv` while holding `theta_cv`, shared method inputs, and production policy fixed. It proves that the CV policy/run lineage changes, old CV acceptance becomes stale for production authorization, shared method and production policy stay current, and rerunning at tightened `tau_cv=0.040` rejects a `0.042` candidate. A separate `theta_cv`-only edit preserves the dimensional/ownership distinction.

## 2. Executed acceptance evidence

Execution record supplied for the repaired candidate:

- focused threshold suite: **47 fast tests passed**;
- assembled end-to-end threshold suite: **2 slow tests passed**;
- affected regression: **112 files**, `-n 16`: **1740 passed, 93 failed, 2 skipped**;
- all 93 failures are `*_specification.py` documentation-sync tests, and the same test ids fail on the unmodified comparison state with identical messages; therefore **0 candidate-attributable regression failures**;
- structural semgrep: **pass**, no remaining pre-validation `float()` coercion of threshold configuration values;
- `git diff --check`: **clean**.

The extensive executable import/execution surface subsumes a separate syntax-only compile check for the changed Python path; no syntax/import defect is observed in the changed owner or its affected consumers.

The successful documentation-PDF workflow for `a0f477ef` remains applicable; generated tracked PDFs are current at `48a99a77`.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains intentionally deferred to the final complete-release package and is not a blocker for this CPU/control-plane repair.

## 3. Final conformance findings

PASS findings:

- foundation thresholds are independently configurable with defaults `0.045 / 0.045 / 0.030`;
- explicit default and omission resolve identical policy identity;
- alternate CV outer metrics never donate their threshold to `tau_cv`;
- role-only edits move only their owning role lineage and material dependents;
- shared replay/physical/integrity edits remain shared-method changes;
- stored evidence is never re-thresholded into current evidence under a changed policy;
- fixed training horizons remain fixed; no threshold early stopping was introduced;
- scratch remains separately governed and rejects the foundation-only CV checkpoint knob;
- generated config, shipped example, guide, CLI spec, P5 spec, D1/D2 papers, and D3 architecture agree on the same ownership/default semantics; and
- no repair introduced duplicate threshold/protocol/checkpoint machinery.

## 4. PEM/HAS and closeout learning

Accepted PEM basis remains `4eabe2ae9783c7ff92f3a1093c37502a01380812`. The bounded repair does not warrant a new PEM family or application episode. Existing applicable lessons remain satisfied:

- FF-002 — exact role-policy ancestry/currentness is fail-closed;
- SP-001 — repair altered/reused the real owner instead of adding synchronized machinery;
- SP-002 — strict typed threshold validation protects authenticated policy identity;
- SP-003 — independent upstream/source/replay/common-monitor identities remain preserved;
- SP-004 — real-owner assembled CV-to-production authorization is explicitly exercised.

No `PROJECT-ENGINEERING-MEMORY.md` mutation is required.

## 5. Closeout

The threshold-separation/parameterization cycle is **CLOSED / PASS**. Archive this review with the parent workplans and retain the closeout/history records as historical evidence. Reopen only for genuinely new contradictory evidence, a semantic policy change, or a regression in the governed currentness/configuration behavior.