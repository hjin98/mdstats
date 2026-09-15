---
kind: independent-implementation-review-reopen
protocol_version: 6.3.0
status: reopened
branch: fix/mlff-cv-competence-threshold-separation
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
implementation_commit: 00d8b20659ee63830eab6d1b3400287af3caaa55
reviewed_candidate_commit: c632521f6aace258d68406afa1cc9f4c4290c9ac
parent_handoff: workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_ALIGNMENT.md
supersedes_closeout_for_current_state: workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md
review_disposition: NO-PASS
highest_open_owner: D1-representation-and-D4
---

# MLFF configurable-threshold implementation — independent review reopen

## 0. Disposition

Independent assembled re-review is **NO-PASS**. No Serious Challenge is raised against the accepted D1/D2 configurable-threshold semantics, and no D3 architecture defect is found in the implemented role-policy split. The implemented resolver correctly reuses `CvValidationPolicyIdentity` for the foundation CV checkpoint threshold and preserves the existing production/shared-method ownership graph; that shape should be preserved.

Closure was premature. Three blocking defects remain in canonical authority representation, public configuration validation, and the required real-owner currentness oracle. The archived closeout remains historical evidence of the attempted closure but does not govern current state until these findings are repaired and independently re-reviewed PASS.

## 1. B1 — canonical authority/lifecycle consolidation is incomplete

The branch claims that broad canonical documentation was consolidated and that D1/D2/D3/D4 are closed, but current canonical authority still says otherwise.

### D1 drift

`docs/methods/mlff_scientific_method.md` still declares the threshold revision **proposed**, pending independent D1 review and stakeholder ratification, even though the independent re-review passed and the stakeholder explicitly ratified all three configurable thresholds on 2026-09-15. Its body repeats that proposed state.

The same paper also retains fixed-default wording where the accepted invariant is now parameterized. In particular:

- “reaching 45 meV/angstrom does not stop a run” must refer to reaching the configured `tau_cv` rather than promote the default into the invariant;
- “CV competence at 45 ... never authorizes a production checkpoint above 30” must instead state that CV acceptance never substitutes for or overrides the configured `tau_prod`; and
- the D1->D2 handoff still labels the threshold separation proposed and hard-codes 45/45/30 as predicates rather than configurable parameters with those defaults.

Its revision provenance also still describes the threshold separation as proposed and routes to the former active workplan path.

### D2 drift

`docs/methods/mlff_numerical_algorithmic_method.md` likewise still declares the role-predicate revision **proposed**, pending D2 review and stakeholder ratification. Sections 17.1 and 23.7 remain explicitly tagged “(proposed)”, D2->D3 handoff item 9 still calls the accepted role thresholds proposed, and revision provenance still points to `workplans/active/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_ALIGNMENT.md`, which is archived.

The default-value numerical oracles are valid as default-policy tests, but they must not be worded as universal fixed-threshold oracles after acceptance of parameterization.

### D4/lifecycle drift

`docs/specs/training_data/mlff_post_selection_threshold_policy_spec.md` still says `implementation reconciliation required` although implementation reconciliation is claimed complete. The archived parent workplan frontmatter says closed while its opening body still says the assembled implementation review is NO-PASS/reopened and that the active index advertises that state.

These contradictions violate the one-current-owner/lossless-representation requirement and make the current lifecycle state unrecoverable without knowing which file to ignore.

**Repair:** consolidate the accepted configurable-threshold semantics into the broad canonical D1/D2/D4 documents and lifecycle prose. Mark D1/D2 accepted/ratified, parameterize normative sentences while retaining 45/45/30 strictly as defaults/calibration, repair provenance/routes to archived records, update the D4 threshold specification to implemented/current status, and reconcile archived coordination prose where it is presented as current disposition. Do not create another semantic owner. If the dedicated threshold-delta documents remain, make their relation to the broad canonical owners unambiguously subordinate or incorporated rather than parallel current authority.

No new D1/D2 scientific review is required if this repair is representational only and preserves the already accepted semantics.

## 2. B2 — threshold configuration accepts booleans and quoted numerics contrary to the public contract

The canonical CLI specification requires finite real configuration fields to reject booleans and strings before identity/execution. The existing threshold validator instead calls `float(value)` and therefore accepts values such as `true -> 1.0` and `"0.040" -> 0.04`.

This affects the three configurable threshold surfaces:

- `tau_cv`, through `CvValidationPolicyIdentity.__post_init__`;
- `theta_cv`, through the same validator; and
- `tau_prod`, where `_configured_maximum_target_force_rmse(...)` first calls `float(...)`, erasing the original TOML type before `FinalProductionPolicyIdentity` validates it.

The focused negative test covers nonpositive/nonfinite values and one nonnumeric string, but does not cover boolean or quoted-numeric counterexamples. The public contract is therefore stronger than the actual parser/resolver behavior.

**Repair by altering the existing validation path:**

1. make the existing finite-positive threshold validator reject booleans and non-numeric types before conversion/canonicalization;
2. pass the raw `[acceptance].maximum_target_force_rmse_ev_per_angstrom` value through that strict owner rather than coercing it with `float(...)` first;
3. preserve accepted integer/float finite-positive values and current defaults;
4. add real-TOML `_load_config` counterexamples for each of the three threshold knobs covering `true`, a quoted numeric such as `"0.040"`, and an invalid string; and
5. run affected regression for other callers of the shared validator/coercion path rather than adding a threshold-specific parallel parser.

Do not add a schema, wrapper, alias, registry, or compatibility translator for this repair.

## 3. B3 — assembled `tau_cv` currentness evidence is confounded by a simultaneous `theta_cv` edit

The handoff requires real `cross-validate -> persisted acceptance -> train-production` evidence that a **CV checkpoint-only** threshold edit moves CV policy/run identity, stales dependent production authorization, and leaves shared method and production policy unchanged.

The current slow test first sets `acceptance_maximum = 0.04`. Its subsequent “CV checkpoint-ceiling edit” replaces that line with `checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.040`. That operation changes two CV policy fields at once: it adds/tightens `tau_cv` and simultaneously removes the explicit `theta_cv=0.04`, restoring `theta_cv` to its default `0.045`. The resulting stale-CV refusal therefore does not discriminate checkpoint-only invalidation.

The focused identity test correctly isolates `tau_cv`, and the later CV rerun correctly shows that `0.042` is rejected under `tau_cv=0.040`; those are useful evidence but do not close the required assembled real-owner currentness claim.

**Repair:** in the assembled harness, change only `tau_cv` while holding `theta_cv`, shared method inputs, and production policy fixed. Assert from the rebuilt real context that method digest and production-policy digest remain unchanged, old CV acceptance/plan is stale under the new CV policy, and a rerun under the new `tau_cv` produces the expected acceptance/rejection and downstream production authorization state.

## 4. Evidence assessment

The closeout records 25 focused fast tests, two slow assembled tests, and 96 affected regression tests as passing. Those realizations remain historical evidence for the candidate and support the many conforming behaviors they actually discriminate. The documentation-PDF workflow for implementation commit `00d8b206...` also completed successfully and produced head `c632521...`.

They do not close B1, B2, or B3: B1 is contradicted directly by current canonical files; B2 has concrete untested public-input counterexamples; and B3's relevant assembled oracle changes two policy dimensions simultaneously. No production-scale GPU qualification is required for this cycle under the standing final-release policy.

## 5. Preserved PASS findings

Unless repair evidence falsifies them, preserve these implementation choices:

- foundation CV resolves optional `[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom` through the existing CV policy owner with default `0.045`;
- the outer threshold remains independently owned by `acceptance_maximum` and the production threshold by `[acceptance].maximum_target_force_rmse_ev_per_angstrom`;
- scratch rejects the foundation-only CV checkpoint field and otherwise keeps pre-separation behavior;
- role-only threshold changes do not enter `PostSelectionMethodIdentity`;
- `post_selection_checkpoint_admissibility(...)` remains the one composition path for shared constraints plus the authenticated role ceiling;
- explicit default and omitted default produce the same resolved CV identity;
- no schema bump, threshold registry, synchronized production alias, P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, or second checkpoint engine was introduced; and
- the 45/45/30 generated defaults and selective role-policy ownership remain correct.

## 6. Re-review acceptance

Return PASS and re-close/archive only when all of the following are true:

- canonical D1/D2/D4 and lifecycle/provenance representations agree that the configurable-threshold policy is accepted and implemented;
- fixed-default wording is replaced by parameterized invariants wherever it currently overstates 45/45/30 as immutable behavior, while default-policy examples/oracles remain explicit;
- all three public threshold knobs reject boolean and string TOML values and accept only the supported finite-positive numeric domain;
- a real assembled checkpoint-only `tau_cv` edit independently demonstrates exact selective invalidation/currentness;
- focused plus affected regression executes against the repaired candidate with no candidate-attributable failure;
- documentation generation remains consistent after canonical repairs;
- no repair introduces duplicate threshold/protocol/checkpoint machinery; and
- closeout/HAS/PEM state is reconciled only after this independent re-review passes.

Until then the threshold-parameterization cycle is **reopened / NO-PASS**.
