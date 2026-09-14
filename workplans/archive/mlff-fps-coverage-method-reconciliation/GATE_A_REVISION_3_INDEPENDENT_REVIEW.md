# Gate A Revision 3 independent D1/D2 review

Date: 2026-09-13
Reviewed candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 3
Reviewed candidate commit: `51b84b0e2e5b6da998e226ac5d21a4537f269456`
Basis review: `GATE_A_REVISION_2_INDEPENDENT_REVIEW.md`
Protocol: SSDP 6.3
Disposition: **NO PASS FOR PROMOTION**

## 1. Challenge disposition

Revision 3 closes two major Revision-2 defects in proposal form:

- the evaluation ladder is now a genuine realized probability design: exact Fisher-Yates over distinct M3 frame occurrences with independent unbiased bits, persisted and reused on restart; and
- every eligible neutral condition is now hard-preserved in P_train at the split boundary.

The separation of `mu_sel`, `mu_loss`, and `mu_eval`, exact-prefix topology, no-label/foundation leakage, and fail-closed stale-generation semantics also remain sound.

No new SERIOUS CHALLENGE is raised against the accepted current D1/D2 baseline by this review. The proposed replacement itself remains **not promotable**, however, because three D1/D2 defects and two acceptance/lifecycle blockers remain.

## 2. Blocking D1/D2 findings

### R3-B1 — structural redundancy is evaluated component-locally, not against the actual retained P_train

Revision 3 defines, for each protected component `g`,

```text
u_x = min_{y in U_size, y not in g} d_U(x,y)
U_g = max_{x in g} u_x
J_structure = sum_{g assigned to M3} U_g
```

This does **not** establish that a component sent to M3 has a close analogue that remains in P_train. Its nearest analogue may be another component that is also sent to M3.

Minimal counterexample with one neutral condition and four singleton protected components on a one-dimensional accepted metric:

```text
g1 = 0
g2 = 10
g3 = 100
g4 = 100.001
m3 = 2
```

All two-component reserve choices have identical condition depletion. Under the proposed component-local uniqueness:

```text
U_g1 = 10
U_g2 = 10
U_g3 = 0.001   # nearest analogue is g4
U_g4 = 0.001   # nearest analogue is g3
```

so the exact objective chooses `M3={g3,g4}` and leaves `P_train={g1,g2}`. The complete structural mode near 100 is removed from training even though each removed component appeared individually redundant.

This contradicts the D1 statement that structural redundancy means reserve components have close analogues **remaining for training**. The flaw is not solver choice; the objective is separable when the scientific property is joint.

**Required repair:** define the structural split objective as a function of the candidate split itself, using the actual retained set. For example, the owning D1/D2 may choose a lexicographic covering objective such as

```text
R_split(M3) = max_{x in M3} min_{y in P_train(M3)} d_U(x,y)
D_split(M3) = mean_or_sum_{x in M3} min_{y in P_train(M3)} d_U(x,y)
```

with the exact priority between maximum and aggregate loss stated explicitly. Another joint objective is admissible if it preserves the same D1 meaning. A sum of fixed per-component scores computed before the selected reserve is known is not sufficient.

The resource/solver envelope must then be re-evaluated for the actual nonseparable objective rather than assuming additive component costs.

### R3-B2 — the structural feature substrate is still not uniquely material-neutral

Revision 3 says profile/environment extensions are forbidden from baseline membership and calls the universal structural block material-neutral. It requires a `(feature_name, family_id)` mapping, but it does not freeze the **aggregation/group policy** that determines which frame coordinates exist.

The current `UniversalStructuralSelectionPolicy` defaults to:

```text
include_declared_atom_groups = True
include_element_groups = True
```

and the current frame aggregator constructs coordinates explicitly named like:

```text
group:<group_id>:atom_count
group:<group_id>:atom_fraction
group:<group_id>:<local_feature>:<statistic>
```

Declared groups may come from material-profile contracts or external membership providers. The catalog lineage itself binds `material_profile_contracts_digest` and `atom_group_catalog_digest`. Thus the current provider can produce profile-specific frame coordinates while still using one of the eight allowed local-feature family IDs.

Consequently two materially different metrics can satisfy Revision 3 as written: one using only neutral/all-atom or element aggregates, and another importing declared material/profile groups. That changes `d_U`, the split, `d_P`, and every `T_N`.

**Required repair:** D2 must normatively define the target-order structural aggregation policy, not only the local-feature family taxonomy. At minimum it must decide and bind:

- whether `include_declared_atom_groups` is forbidden for baseline membership (the current D1 wording implies yes);
- whether element groups are included;
- which aggregate statistics are included;
- the enabled local-feature family set or the authoritative parameterization rule;
- the exact provider/policy identity that is allowed to influence membership; and
- that material-profile/atom-group authority not explicitly accepted for target ordering cannot enter the target-order descriptor bytes indirectly.

The existing low-level `_feature_family` semantics can be reused; the repair should narrow/rebind the provider rather than introduce a second feature taxonomy.

### R3-B3 — exact scalar reproducibility does not close metric conditioning for near-degenerate scales

Revision 3 correctly removes an unjustified fuzzy **score-tie** tolerance and defines one canonical binary64 reference. That solves discrete reproducibility. It does not solve the different numerical question of whether the robust transform is well conditioned.

The scale rule now falls back only when

```text
Q75 - Q25 == 0.0
```

as an exact binary64 comparison. A coordinate that is scientifically constant but has tiny provider/roundoff jitter can therefore have a very small nonzero interquartile range and be divided by that value. The transform then amplifies numerical jitter to order-one variation, giving that coordinate normal FPS influence despite negligible physical spread.

This is especially relevant to nearly fixed cell angles, symmetry-derived descriptors, or local-structure summaries whose variation can approach provider numerical resolution. Canonical arithmetic makes the amplification deterministic; it does not make it numerically meaningful.

**Required repair:** separate **scale-conditioning semantics** from score-tie semantics. Keep exact scalar reference ordering if desired, but define when a fitted coordinate scale is too poorly resolved to invert. The threshold must derive from accepted provider precision/error semantics, feature resolution, or an independently justified conditioning rule; alternatively use an accepted transform whose conditioning remains bounded without a hard near-zero inversion. Add perturbation/higher-precision evidence showing that provider-level numerical noise cannot materially steer membership.

Do not reintroduce an arbitrary tolerance merely to make implementations agree.

## 3. Acceptance/evidence blocker — Revision 3's own mandatory falsification has not been realized

Section 6 of Revision 3 explicitly requires twelve pre-promotion falsification targets, including Fisher-Yates reference checks, duplicate-occurrence sampling, variable-atom EVAL2 estimation, condition-extinction and unique-mode split counterexamples, exact solver comparison, complete family mapping, scalar reference differential checks, metamorphic invariance, stale-generation negatives, producer-lineage authentication, and representative CPU/resource evidence.

The branch contains only the old Revision-1 bounded fixture plus author repair records. No Revision-3 independent realization artifact or executable evidence was added. The author repair check itself correctly labels these checks outstanding.

The old bounded fixture is stale for Revision 3 because the split objective, metric semantics, and evaluation design all changed materially. It cannot confirm the current candidate.

This review environment could inspect the remote repository but could not execute it; attempts to obtain the repository in the execution container failed because that runtime has no network access. Required executable evidence is therefore **UNAVAILABLE**, not passed.

Promotion remains blocked even if R3-B1 through R3-B3 are repaired textually. A required check that did not execute is not a pass.

## 4. Workflow/representation blocker — the active workplan still describes Revision 1

The active parent workplan has not been reconciled after Revisions 2 and 3. Its Gate A method summary and human-ratification bundle still state, among other obsolete semantics:

- two equal metric blocks;
- the old FP64 tolerance;
- deterministic condition-proportional hash `pi_eval`;
- unchanged split objective apart from UID-independent tie repair; and
- the original Revision-1 independent-review checklist.

Those directly conflict with Revision 3's current proposal: realized Fisher-Yates SRSWOR, hard condition preservation, pre-split `d_U`, lexicographic structural split scoring, semantic-family weighting, and exact scalar membership reference.

Under Protocol 6.3 the active workplan/handoff must remain snapshot-complete enough for review and human adjudication. A human ratification performed against the current workplan could approve the wrong method bundle.

**Required repair:** reconcile the active workplan to Revision 3 (or its successor) before the next acceptance review. Preserve historical review records as history; do not rewrite them into apparent current authority.

The branch is one merge commit behind `main`, but the relevant accepted D1/D2 method-paper blobs are byte-identical to current main, so this ancestry shape is **not** a semantic blocker for this review. Integration should still fast-forward/reconcile accepted project ancestry before downstream implementation.

## 5. Revision-2 blocker status after Revision 3

| Prior finding | Revision 3 disposition |
| --- | --- |
| R2-B1 false SRSWOR | **closed in proposal** by exact Fisher-Yates over distinct occurrences |
| R2-B2 condition extinction | **closed in proposal** by hard per-condition P_train retention |
| R2-B3 structural uniqueness | **reopened/narrowed as R3-B1**: component-local redundancy is not retained-set redundancy |
| R2-B4 family mapping | **partially closed**: local family IDs are explicit, but aggregation/group substrate remains ambiguous/profile-sensitive (R3-B2) |
| R2-B4 fuzzy tie envelope | **score-tie issue closed**, but transform conditioning remains open as R3-B3 |

## 6. Evaluation design assessment

The Revision-3 Fisher-Yates construction is mathematically coherent in proposal form. With independent unbiased bits and rejection sampling, each swap index is uniform and the resulting permutation is uniform over distinct M3 frame occurrences. Persisting the realized permutation rather than regenerating it is consistent with one frozen randomized experimental design.

The component-weighted EVAL2 prefix remains a ratio estimator under frame-cluster SRSWOR; finite-prefix uncertainty is appropriately described as diagnostic rather than exact unbiased inference. However, independent evidence must still establish that the configured early M1/M2 sizes provide useful screening resolution in relevant heterogeneous-error/variable-atom regimes. Shared evaluation membership provides paired comparison but does not eliminate sampling uncertainty in candidate differences.

This is currently an evidence obligation rather than a separate textual blocker.

## 7. Promotion decision

**NO PASS. Do not promote Revision 3 into the permanent D1/D2 method papers.**

The next repair should remain narrow:

1. replace the separable component uniqueness score with a joint retained-P_train structural redundancy/coverage objective;
2. freeze a genuinely material-neutral target-order structural aggregation/provider policy and prevent declared profile groups from entering membership implicitly;
3. add justified scale-conditioning semantics without reviving an arbitrary score-tie tolerance;
4. reconcile the active workplan/human-ratification bundle to the actual candidate; and
5. realize the candidate's complete independent falsification suite, including resource evidence for the repaired joint split solver.

Preserve the strong Revision-3 decisions: hard condition retention, exact protected components, separate `d_U` and `d_P` fit domains, one exact nested `pi_train`, realized Fisher-Yates `pi_eval`, `mu_sel`/`mu_loss`/`mu_eval` separation, candidate-independent membership, no foundation/label leakage, no GPU prerequisite, and fail-closed stale ancestry.

Human ratification remains premature until these blockers are repaired and a fresh independent review passes.