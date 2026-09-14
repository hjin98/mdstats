# Gate A Revision 5 author repair check

Date: 2026-09-13
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 5
Basis review: `GATE_A_REVISION_4_REVIEW.md`
Status: author-side repair mapping; **not independent acceptance evidence**.

## R4-B1 — all-missing/constant/active-dimension semantics

Closed in proposal form. Revision 5 defines four materially distinct states instead of letting D4 infer them:

- no observations -> numerical coordinate inactive; all-one missingness indicator inactive;
- observed constant value -> numerical coordinate inactive;
- partial missingness -> raw 0/1 missingness indicator active only when both states occur;
- nonconstant observed numerical values -> active robust-scaled coordinate.

Only active numerical coordinates and varying missingness indicators count in `d_f`. An inactive coordinate or all-inactive family cannot dilute another informative dimension/family. `d_U` and `d_P` fit these states independently on their own domains.

## R4-B2 — unjustified `sqrt(u)` resolution threshold

Closed by removal, not by inventing another threshold. Revision 5 uses exact nonzero binary64 IQR, then exact nonzero maximum deviation, otherwise constant/inactive. The target-order layer treats the bound provider's binary64 values as evidence; it does not silently promote binary64 epsilon into a scientific resolution policy.

If a coordinate-specific provider uncertainty/resolution bound becomes accepted later, importing it into membership is a new metric identity and D2 decision.

## R4-B3 — random evaluation prefixes could irreversibly steer the funnel

Closed by simplification. Exact full M3 is now the sole automatic model-selection population at every configured training-fidelity boundary. The existing funnel and practical-equivalence policy compare same-estimand, same-population EVAL2 metrics at every boundary.

M1/M2 remain SRSWOR diagnostics only and cannot rank, eliminate, qualify, tie-break, recommend, or freeze. This eliminates evaluation-permutation decision risk instead of adding a confidence wrapper or another decision threshold.

## R4-B4 — incomplete identity/reduction/provider semantics

Closed in proposal form by:

- advancing occurrence key to `mdstats.target-order-scientific-occurrence-key.v3`;
- encoding `source_frame_index` as unsigned 64-bit big-endian with fail-closed bounds;
- canonicalizing protected-component-key serialization;
- defining `H_mean` member order, left-to-right binary64 accumulation, and final division;
- defining canonical frame-level element aggregation for mean/std/extrema/type-7 quantiles;
- binding the target-order local-structure numerical contract to the accepted analysis owner/schema/version/specification blob, not only feature names.

## R4-B5 — capability-transfer and evidence-stage defects

Closed structurally:

- `GATE_A_REVISION_5_CAPABILITY_TRANSFER_MAP.md` supplies the required early-DATA7 and later MVSEL/MVQUAL capability transfer with immutable source routes, disposition, replacement, oracle route, and omission rationale;
- Gate A now requires D1/D2 method evidence only;
- persistence/currentness, old-generation rejection, production optimized equivalence, restart, real `prepare -> publish -> consume`, and affected implementation regression remain mandatory but are explicitly staged to Gates B-E after D1/D2 acceptance.

No evidence obligation was deleted merely to obtain a pass.

## Additional D1/D2 scope gap

Closed by deleting `mass_density_g_cm3` from the target-order membership metric. The raw block now means what D1 says: cell geometry plus strain. Composition support remains expressed by neutral conditions and element-resolved local-structure summaries.

## Preserved successful Revision-4 decisions

Revision 5 intentionally preserves:

- hard neutral-condition retention;
- protected components;
- exact global minimum condition-depletion objective;
- dynamically recomputed retained-set structural redundancy under exact completion admissibility;
- material-neutral element-only local structure;
- no material-specific raw pair rules or declared/profile groups;
- exact medoid-seeded condition-local FPS and proportional condition interleaving;
- one exact `pi_train` and exact target prefixes;
- scalar binary64 membership reference with no fuzzy score-tie tolerance;
- no foundation/difficulty/candidate-outcome membership leakage;
- no revived legacy selector topology.

## Remaining Gate-A evidence, not authority defects

The candidate is not self-proven. A genuinely separate review context must still independently challenge at least:

1. real-feature equal-family sensitivity/ablation;
2. precision sensitivity of the bound provider/aggregation/transform on representative features;
3. exact split/completion and retained-set reference cases;
4. bounded CPU/RAM feasibility of the exact D2 method;
5. method-level identity/input-order metamorphics feasible before D3/D4 implementation; and
6. completeness/correctness of the capability-transfer map.

## Disposition

Revision 5 is ready for a **separate-context independent D1/D2 review**. It is not promoted. Human ratification remains pending, and behavior-changing D3/D4 remains blocked.