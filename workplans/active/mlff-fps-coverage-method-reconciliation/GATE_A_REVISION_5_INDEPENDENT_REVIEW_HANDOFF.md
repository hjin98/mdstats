# Gate A Revision 5 — independent D1/D2 review handoff

Date: 2026-09-14
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Candidate family: Revision 5
Lifecycle: review handoff; **not acceptance evidence and not D1/D2 authority**

## 1. Review subject

Review the assembled Revision-5 Gate-A method, not merely one file or the latest diff. The minimum subject is:

- `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`;
- `GATE_A_REVISION_5_D1_METHOD_AMENDMENT.md`;
- `GATE_A_REVISION_5_D2_METHOD_AMENDMENT.md`;
- `GATE_A_REVISION_5_CAPABILITY_TRANSFER_MAP.md`;
- `GATE_A_REVISION_5_WORKPLAN_RECONCILIATION.md`;
- all applicable Gate-A evidence records for the exact reviewed commit;
- accepted D1/D2 baseline at `e8d04144f55c72d799ffcd3fe40c75e47078a66d`;
- accepted PEM basis `4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md` with the parent workplan HAS.

Do not inherit the author-side conclusion that Revision 4 blockers are closed. Reconstruct the governing D1 question, the D2 method, the historical transfer, and evidence applicability independently.

## 2. Review disposition rule

Gate A may receive **PASS FOR HUMAN RATIFICATION** only if all required Gate-A D1/D2 evidence is available, applicable, and sufficient and no material D1/D2 Challenge/blocker remains.

Use **NO PASS** if any required realization is unavailable, if resource feasibility is not demonstrated, if the amendment overlays cannot be applied losslessly to permanent D1/D2, if a counterexample changes the intended target-size scientific meaning, or if the exact D2 method is ambiguous/unreconstructible.

Do not require future D3/D4 persistence/integration behavior to exist before Gate A; those obligations remain staged to Gates B-E. Conversely, do not waive a D1/D2 check merely because it could eventually be tested through D4.

Human ratification is not part of the independent review itself. A PASS means only that the exact reviewed proposal is ready for the designated human decision.

## 3. Required D1 Challenge pass

Attempt to falsify at least:

1. **Independent-variable integrity.** Can two candidates at different `N` differ in anything other than exact extension of one frozen `pi_train` plus the already accepted N-dependent optimizer normalization/exposure semantics?
2. **Training-support priority.** Can exact M3 allocation extinguish an eligible neutral condition or split an inherited protected component?
3. **Coverage interpretation.** Does any proposed coverage diagnostic silently claim model accuracy, deployment adequacy, or statistical independence?
4. **Metric scope.** Can material/profile-specific coordinates, mass density, foundation predictions, label-derived difficulty, candidate outcomes, replay/CV state, or downstream evidence influence split or `pi_train`?
5. **Evaluation estimand.** Can diagnostic `M1/M2` randomization influence ranking/elimination/recommendation despite the exact-full-`M3` rule?
6. **Residual-reserve limitation.** Is the proposal explicit that `M3` is a development/model-selection reserve selected while prioritizing training support and is not claimed to be an unbiased estimator of a broader physical population?
7. **Operator claim boundary.** Is the supported conclusion limited to comparative short-horizon exact-`M3` target-force behavior over the configured candidate ladder and frozen training method?

A material ambiguity that permits a scientifically different descendant is a D1 blocker even if one intended implementation is sensible.

## 4. Required D2 reference/falsification pass

### 4.1 Exact split solver

Implement or independently derive a bounded direct exhaustive reference over protected-component subsets. Compare against the proposed exact dynamic-programming/reference recurrence for:

- hard-feasible exact cardinality;
- condition-capacity constraints;
- exact rational `J*`;
- multiple globally optimal reserve subsets;
- no-feasible-subset cases;
- completion-admissibility at multiple retained-set steps.

Use exact rational arithmetic for the governing depletion objective. A floating optimization result is not by itself a reference oracle.

Construct at least one counterexample where a component is hard-feasible locally but cannot participate in any `J*` completion; it must be rejected by completion admissibility.

### 4.2 Retained-set redundancy

Exercise the known mutual-redundancy pattern where two components appear redundant relative to each other. Verify that after removing the first, the second is rescored against the new retained set and cannot rely on stale reciprocal coverage.

Check canonical `H_mean` ordering/reduction semantics and exact-score tie behavior.

### 4.3 Metric transform

Independently verify:

- all missing -> inactive numeric + inactive all-one missing indicator;
- fully observed constant -> inactive;
- partial missing + constant observed values -> missing indicator only;
- partial missing + varying values -> numeric + missing indicator;
- collapsed IQR with a real rare excursion -> max-deviation fallback;
- finite nonzero small variation -> active, with no generic `sqrt(u)` suppression;
- all-inactive family -> zero contribution without diluting other families.

### 4.4 Provider and aggregation lineage

Audit the bound local-structure numerical contract at the immutable accepted specification/blob. Confirm that every target-order local feature family/coordinate exists with the asserted semantics and that material/profile extensions are excluded from baseline membership.

Verify canonical element aggregation with an independently simple scalar implementation, including type-7 quantiles and missing masks.

### 4.5 Order construction

Independently verify:

- condition medoid calculation;
- condition-local FPS against a simple scalar maximin reference;
- exact integer proportional deficit scheduling;
- deterministic condition-ID and `kappa` ties;
- exact `pi_train` permutation and `T_N=pi_train[:N]` for every configured size;
- `N_min >= number of represented P_train conditions`.

### 4.6 Metamorphics

Where their preconditions hold, test:

- source/input traversal reorder invariance;
- non-semantic `frame_uid` spelling change invariance outside genuine governing ties;
- serialized feature-column permutation invariance after canonical semantic naming;
- diagnostic `pi_eval` realization change leaves full-`M3` reducer input and recommendation unchanged for frozen predictions.

Do not assert an invariance where source occurrence identity or another semantically governing field genuinely changed.

## 5. Real-feature sensitivity and precision evidence

The equal-active-family weighting is a proposed no-prior baseline, not a theorem. On representative current target-order data, challenge it by reporting at least:

- baseline `pi_train`/configured-prefix memberships and coverage summaries;
- one-family-at-a-time ablation;
- bounded family reweight perturbations sufficient to reveal whether small plausible changes catastrophically reorder configured prefixes;
- provider/aggregation precision perturbation or independently justified higher-precision/reference recomputation on representative coordinates where feasible;
- observed membership/rank changes, not only aggregate distance correlations.

There is no predetermined percentage threshold to manufacture a pass. The reviewer must assess whether the baseline is numerically/scientifically stable enough for the intended target-size experiment or whether D1/D2 needs a different accepted weighting/uncertainty treatment.

## 6. Representative CPU/RAM feasibility evidence

The exact split/completion reference semantics are mandatory; no approximate fallback is admissible for Gate-A closure.

Use representative supported current target-order populations and report at minimum:

- total frames `|U_size|`;
- protected-component count and component-size distribution;
- represented neutral-condition count;
- `m3`, `N_max`, and configured `K=max(candidate_sizes)`;
- active target-order coordinate dimension;
- exact-solver memoized/explored state count and any exact pruning used;
- wall time and peak CPU RAM for descriptor/aggregation preparation;
- wall time and peak RAM for `J*` plus completion-admissibility solving;
- wall time and peak RAM for retained-set scoring;
- wall time and peak RAM for K-bounded FPS/order construction.

Wall time is evidence, not an arbitrary acceptance constant. The acceptance question is whether the exact proposed method is operationally feasible for the supported regime with reasonable bounded CPU/RAM resources. If not, reopen D2 rather than weaken semantics.

Long GPU qualification is intentionally out of scope unless this evidence unexpectedly introduces GPU-dependent numerical semantics.

## 7. Capability-transfer audit

For every row in `GATE_A_REVISION_5_CAPABILITY_TRANSFER_MAP.md`, verify:

- the historical source actually contains the stated capability/mechanism;
- current disposition is consistent with accepted/project-proposed authority;
- the replacement mechanism preserves the stated capability where preservation is claimed;
- retired constants/topologies are not smuggled back through a new name;
- acceptance/oracle routes are sufficient for the preserved capability.

Pay particular attention to early DATA7 representative/FPS/environment queues, later MV coverage/qualification semantics, V7 one-order simplification, and the retirement of changing `M1/M2/M3` decision populations.

## 8. Amendment-overlay losslessness

Apply the D1 and D2 overlays conceptually to the accepted permanent papers and check that:

- every materially contradicted old target-order statement is replaced;
- unaffected scientific/numerical method sections remain preserved;
- no old D2 statement still grants empty-evidence/UID-order baseline semantics;
- no old section still states that `M1/M2/M3` are automatic decision populations;
- old `O(C*m3)` split complexity is removed for the repaired exact solver;
- Section-21 falsification and Section-22 reproducibility are updated consistently;
- reconstruction provenance is retained and the later reconciliation is added rather than falsely backdated.

A missing permanent-paper delta is a promotion blocker even if the combined candidate text contains the intended semantics.

## 9. Review output

Record:

- exact reviewed commit SHA;
- evidence realizations and their subject/input/environment identities;
- PASS/NO-PASS disposition;
- any Serious Challenge before ordinary findings;
- each blocker with owning D1/D2 layer and specific repair requirement;
- evidence judged still applicable from earlier revisions and why;
- evidence rejected/stale/inapplicable and why;
- whether the exact bundle is ready for human ratification.

Do not mutate permanent D1/D2 or authorize behavioral D3/D4 in the review record itself.
