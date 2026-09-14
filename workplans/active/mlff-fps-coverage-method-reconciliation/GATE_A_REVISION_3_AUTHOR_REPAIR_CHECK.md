# Gate A Revision 3 author repair check

Date: 2026-09-13
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 3
Basis review: `GATE_A_REVISION_2_INDEPENDENT_REVIEW.md`
Status: author-side repair mapping; **not independent acceptance evidence**.

## Closure mapping

### R2-B1 — false SRSWOR semantics

Repaired by removing deterministic hash priority from evaluation membership entirely. Revision 3 requires one actual randomization event after M3 freezes, using exact Fisher-Yates over distinct frame occurrences and independent unbiased random bits. The realized permutation, not a seed-derived hash rule, becomes immutable experiment authority. Exact geometry duplicates participate as distinct occurrences. Restart reuses rather than redraws.

### R2-B2 — condition extinction

Repaired by making retention of at least one P_train frame from every eligible U_size neutral condition a hard exact-split feasibility constraint. Exact M3 cardinality that cannot satisfy this constraint is scientific infeasibility.

### R2-B3 — structural uniqueness lost under equal condition depletion

Repaired with a separate pre-split metric `d_U`, fitted on label-blind U_size geometry/structural evidence under the same metric definition. Protected-component uniqueness is the maximum, over component members, of nearest distance to any frame outside the component. Among hard-feasible splits with equal minimum condition depletion, the exact solver minimizes the sum of removed-component uniqueness. The later P_train order uses a separately refitted `d_P`; no P_train fit flows backward into the split.

### R2-B4 — family mapping ambiguity

Repaired by requiring the universal structural provider to publish an explicit one-to-one `(feature_name, family_id)` table aligned with feature coordinates, with an exact allowed family set. D3/D4 may expose this existing semantic ownership but may not infer a second taxonomy downstream.

### R2-B4 — unsupported fuzzy tie envelope

Repaired by deleting fuzzy tolerance from membership semantics. A canonical scalar binary64 reference fixes quantiles, transforms, coordinate order, multiply/add order, representative scores, FPS scores, and exact binary64 equality ties. Optimized paths must reproduce discrete decisions or fall back to reference comparison.

## Self-challenge / remaining evidence

Revision 3 still requires independent evidence before promotion. In particular:

1. the structural uniqueness objective is additive over removed protected components and is a deliberate secondary objective, not a theorem of globally optimal P_train coverage;
2. equal family mass remains a ratifiable no-prior baseline and needs real-feature sensitivity/ablation;
3. the canonical scalar reference prioritizes reproducibility over backend-specific floating-point freedom; resource evidence must show fallback/reference checks do not create unacceptable preparation cost;
4. the Fisher-Yates design depends on an independently unbiased random-bit source at the one initialization event; qualification must test the algorithm with a controllable reference bit stream and verify restart never redraws;
5. exact constrained split optimization may be more expensive than the old first-feasible subset-sum; representative resource qualification must establish feasibility without weakening the objective.

## Disposition

Revision 3 closes the four Revision-2 authority defects in proposal form and is ready for a fresh independent D1/D2 review plus the explicit falsification suite. It is not self-promoted. D3/D4 behavioral implementation remains blocked.