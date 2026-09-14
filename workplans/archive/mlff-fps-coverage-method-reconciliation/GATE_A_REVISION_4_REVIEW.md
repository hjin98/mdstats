# Gate A Revision 4 D1/D2 review

Date: 2026-09-13
Reviewed candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 4
Candidate head reviewed: `1a169789c3ab0e5bb0773dd47f8179da6878b8b7`
Accepted project basis: `e8d04144f55c72d799ffcd3fe40c75e47078a66d`
Protocol: SSDP 6.3
Disposition: **NO PASS FOR PROMOTION**

> Independence note: this review was requested in the same conversational lineage that authored Revision 4. A NO-PASS finding is valid challenge evidence, but this record does not claim to satisfy the eventual separate-context independent-PASS requirement.

## 1. What Revision 4 successfully repairs

Revision 4 materially closes the main Revision-3 authority defects.

- The branch now actually descends from the accepted D1/D2 baseline.
- Neutral-condition retention is hard split feasibility.
- Structural redundancy is recomputed against the current retained set and constrained to exact globally minimum condition-depletion completions; the Revision-3 mutually redundant-component counterexample is therefore addressed.
- Material/profile-specific raw pair rules and declared atom groups are excluded from baseline membership evidence.
- The low-level local-structure policy, element-only aggregation, exact generated feature names, shear coordinate convention, and semantic family map are substantially more precise.
- Evaluation uses a genuine realized Fisher-Yates probability design over distinct M3 occurrences rather than a deterministic geometry hash incorrectly described as SRSWOR.
- Winner/tie semantics remain canonical scalar binary64 rather than relying on a generic fuzzy score tolerance.
- The full reviewed parent workplan has been restored and branch ancestry reconciled to accepted main.

The following blockers are new or remain after those repairs.

## 2. Blocking findings

### R4-B1 — the transform is undefined for all-missing coordinates and family dimension is ambiguous

Section 2.3 defines quantiles, `M=max_i |x_i|`, IQR, and maximum median deviation over **observed** values, but it never defines the case `n_observed=0`.

This is not merely pathological. Raw strain coordinates can be absent for an unresolved reference/strain domain, and local angular/orientational coordinates can be missing for every frame when the required neighbor support does not exist. The target-order aggregation explicitly permits a frame coordinate to be missing when no valid local value remains.

The same section says that if any source value is missing, a binary missingness coordinate is appended. Section 2.4 then normalizes by `sqrt(d_f)` where `d_f` counts active numerical and missingness coordinates, but neither of these is specified sufficiently:

- Is an all-missing numerical coordinate omitted, zero-filled, or counted as an active zero coordinate?
- Is an all-one missingness indicator active even though it carries no pairwise information?
- Is a binary missingness coordinate used as raw 0/1, robust-scaled, centered, or otherwise transformed?
- Does a numerically unresolved zero coordinate count in `d_f` and thereby dilute every informative coordinate in that family?

Different answers change distances, split membership, medoids, and FPS order while satisfying the current prose.

**Required repair:** define the exact zero-observation/partial-missing/constant cases and the exact active-dimension rule. A sound minimal rule would normally omit constant/non-discriminating coordinates from `d_f`, persist their missing/unresolved status as evidence, and explicitly define the numerical treatment of a varying missingness indicator; the owning D2 proposal must decide rather than leaving this to D4.

### R4-B2 — `sqrt(u)*max_abs` is still an unratified resolution threshold, not a derived finite-precision bound

Revision 4 moved the numerical ambiguity from winner ties into transform conditioning, but the chosen threshold is not derived from the current provider's forward-error/conditioning semantics.

An independent scalar reference check used

```text
x = [1, 1+1e-9, 1+2e-9, 1+3e-9]
u = 2^-53
rho = sqrt(u)*max(|x|)
```

The 1e-9 increment is about **4.5 million binary64 ulps at 1.0**, yet Revision 4 produces approximately

```text
IQR   = 1.5e-9
s_dev = 1.5e-9
rho   = 1.0537e-8
```

and classifies the coordinate as numerically unresolved. The rule therefore suppresses variations vastly larger than representation roundoff. Its stated rationale assumes perturbations of order `u*M`, but the accepted local-structure features are computed through minimum-image geometry, switches, reductions, radial/angular/orientational transforms, and aggregation; their forward error is not established as `u*M` either.

Positive unit-rescaling invariance does not supply the missing error model.

**Required repair:** either derive coordinate-resolution bounds from the numerical provider/operation conditioning and use those bounds, or explicitly promote a physically/scientifically meaningful minimum-resolution policy through D1/D2 with evidence. Do not describe `sqrt(u)` as finite-precision necessity merely because it suppresses an unstable scale. Real-feature sensitivity/precision evidence is required before acceptance.

### R4-B3 — SRSWOR estimator uncertainty is not reconciled with the actual funnel decision rule

Revision 4 correctly defines M1/M2 as random finite-population prefixes and exposes a ratio-estimator standard error, but declares that uncertainty diagnostic only. The accepted reducer, however, irreversibly eliminates candidates at early boundaries using those realized prefix metrics and a practical-equivalence tolerance `epsilon`.

Therefore a candidate can be eliminated solely because one SRSWOR realization reverses the M3 ordering or moves an observed difference across `epsilon`; later larger rungs cannot recover an eliminated candidate. The final target-size recommendation is consequently a random variable induced by the evaluation permutation, not merely a noisy reported metric.

Revision 4 does not define:

- an acceptable probability/risk of early-rung misranking;
- an adequacy relationship between sampling uncertainty and `epsilon`;
- a seed/randomization robustness criterion; or
- a D1 limitation saying that the funnel deliberately accepts an uncontrolled realization-specific elimination risk.

The current `SE(r_m)` diagnostic by itself does not preserve the scientific meaning of the funnel.

**Required repair:** D1 must explicitly adjudicate stochastic screening risk. D2 must then define a compatible adequacy route—for example evidence/bounds showing rung sampling uncertainty is sufficiently small relative to decision margins in the intended regime, or an uncertainty-aware decision rule if the reducer is intentionally reopened. A deterministic/balanced evaluation design remains an alternative if the project does not want the recommendation to depend on a fresh probability draw.

### R4-B4 — discrete identity/reduction semantics remain incomplete

Revision 4 says fixed-width integer fields use their stated representation, but `source_frame_index` in `kappa` has no stated width/sign encoding. Two conforming readers can therefore hash different byte strings.

Likewise `H_mean` changes split membership but its canonical reduction order is not stated. The scalar-reference section freezes squared-distance accumulation order, not the member ordering and summation/division semantics for `mean_{x in g} q_x`. The same concern applies to any membership-owning aggregate that is not already bound to an immutable provider numerical contract.

The low-level local-structure feature formulas currently live in the analysis specification/implementation. Revision 4 freezes parameter values and names but does not bind an immutable analysis numerical-contract identity into the target-order method strongly enough to prevent a same-name provider semantic change from silently changing `d_U/d_P`.

**Required repair:** freeze the exact `kappa` integer encoding (for example unsigned 64-bit big-endian if that is the intended domain), canonicalize every membership-owning reduction such as `H_mean`, and bind the exact accepted local-structure numerical contract/version/provider identity used by target ordering. A D2 reader should not need to infer material numerical semantics from whichever implementation currently exports the same feature names.

### R4-B5 — Gate A evidence/coordination is incomplete, and some evidence is staged at the wrong gate

The candidate itself requires pre-promotion falsification that has not been realized: real-family equal-mass sensitivity/ablation, complete provider/coordinate-lineage evidence, optimized/reference discrete equivalence, input/UID/column metamorphic evidence, and representative CPU/RAM evidence. `GATE_A_REVISION_4_BOUNDED_FALSIFICATION_RECORD.md` explicitly marks these unavailable. A required unavailable realization is not a pass.

The parent workplan also requires, before Gate A closes, a true capability-transfer map containing immutable historical source identity, current authority disposition, replacement mechanism, oracle/acceptance route, and omission rationale for both the early DATA7 and later MVSEL/MVQUAL lineages. Revision 4 contains only a compact disposition summary; the required lossless transfer map is still absent.

At the same time, Revision 4's Section 6 over-stages some D3/D4 conformance checks as D1/D2 pre-promotion blockers—particularly persistence restart/no-redraw behavior, old-generation admission through current storage/currentness, and real `prepare -> publish -> consume` integration. Behavioral D3/D4 is explicitly blocked until Gate A closes, so requiring the final D3/D4 realization to exist before Gate A can pass creates a circular gate.

**Required repair:** separate evidence by semantic owner:

- Gate A: D1/D2 mathematical/reference/prototype evidence, real-feature sensitivity, numerical/provider lineage, stochastic decision adequacy, and algorithmic CPU/RAM feasibility sufficient to establish the proposed method is coherent and realizable;
- Gates B-E: D3/D4 persistence/restart, production currentness, old-generation rejection, optimized implementation equivalence, prepare/publish/consume integration, and affected regression.

Do not weaken final evidence obligations; move them to their correct downstream gates.

## 3. Additional gap — D1/D2 scope wording

D1 says the raw baseline covers “universal cell/strain geometry,” while D2 also includes `mass_density_g_cm3`, which depends on atomic masses/composition as well as cell volume. This is order-changing evidence and is not literally a geometry/strain observable. Either D1 should explicitly authorize this composition-derived physical coordinate or D2 should remove it. This is straightforward to close but should not be left as an implicit scope expansion.

## 4. Evidence disposition

The Revision-4 author-side fixtures remain useful and applicable to the narrow propositions they exercise:

- the Revision-3 mutual-redundancy counterexample is closed by retained-set rescoring;
- hard neutral-condition infeasibility behavior is coherent on bounded enumeration;
- Fisher-Yates construction is exact for the stated unbiased-bit assumption;
- the variable-atom-count fixture correctly demonstrates that the finite-prefix ratio estimator is not exactly unbiased and full M3 recovers the exact estimand;
- static inspection supports excluding declared/profile groups from the target-order provider.

They do **not** close R4-B1 through R4-B5. The independent `sqrt(u)` counterexample above directly challenges the current conditioning claim.

## 5. Promotion decision

**NO PASS. Do not promote Revision 4 into permanent D1/D2 and do not start behavior-changing D3/D4 implementation.**

The next repair should remain narrow:

1. fully define missing/all-missing/constant coordinate and family-dimension semantics;
2. replace or rigorously justify the `sqrt(u)` conditioning floor;
3. reconcile evaluation-sampling uncertainty with the reducer's irreversible early decisions and `epsilon`;
4. close the remaining exact identity/reduction/provider-contract details;
5. complete the historical capability-transfer map;
6. restage D3/D4 conformance evidence to Gates B-E while retaining the D1/D2 evidence genuinely needed for Gate A.

Revision 4's retained-set split, hard condition support, neutral element-only structural substrate, exact Fisher-Yates construction, one-order topology, hard/soft separation, no-foundation membership rule, and fail-closed ancestry intent should be preserved unless one of the repairs above directly requires reopening them.