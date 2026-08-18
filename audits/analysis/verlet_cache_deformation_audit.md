# S3 Deformation-Aware Verlet Cache Mathematical Validity Audit

## Release

```text
Package: mdstats
Version: 0.14.0a3
Stage: S3 - deformation-aware Verlet candidate reuse
```

## Implemented source boundary

- `mdstats/analysis/_verlet_cache.py` owns request schemas, immutable rebuild references, active species-pair metadata, fixed/deforming-cell validity, exact current-frame reevaluation, and statistics.
- `mdstats/analysis/_cell_list.py` remains the exact candidate-list rebuild backend.
- `mdstats/analysis/_neighbors.py` remains the dense oracle and stateless facade.
- Scientific hysteresis and reference-bond state remain outside the candidate cache.

## Accepted validity bound

For rebuild cell $H_0$ and current cell $H_t$,

$$
F_t=H_0^{-1}H_t.
$$

For active species pair $(A,B)$, the implementation evaluates

$$
M_{AB}(t)
=
\sigma_{\min}(F_t)(r_{AB}+r_{\mathrm{skin}})
-r_{AB}
-u_A^{\max}(t)
-u_B^{\max}(t).
$$

The nonaffine displacement is

$$
\mathbf u_i(t)
=
[\mathbf s_i(t)-\mathbf s_i(t_0)]H_t,
$$

using the continuous fractional trajectory coordinates stored by
`AtomisticFrameCollection`.

Reuse is accepted only when

$$
M_{AB}(t)>\varepsilon
$$

for every active pair. Equality rebuilds.

## Proof review

1. Every omitted pair satisfies $\lVert\mathbf x_0\rVert\ge r_{AB}+r_{\mathrm{skin}}$ at the rebuild frame.
2. The affine map gives $\lVert\mathbf x_0F_t\rVert\ge\sigma_{\min}(F_t)\lVert\mathbf x_0\rVert$.
3. Endpoint nonaffine motion can reduce pair separation by at most $u_A^{\max}+u_B^{\max}$.
4. Therefore a positive margin prevents an omitted pair from entering the physical cutoff.
5. The implementation reserves the numerical tolerance $\varepsilon$ and rebuilds at equality.

The proof is pair-type conservative and independent of the current minimum-image branch. Current MIC vectors and image shifts are recalculated after validity is established.

## Species-pair audit

- Disjoint requests use the canonical species Cartesian product.
- Identical requests use unordered species pairs that can be formed by two distinct atoms.
- A singleton species does not create a same-species pair type.
- Species maxima are evaluated over the exact union of request centers and candidates.
- The immutable cache stores sorted canonical pair identities and matching physical thresholds.

## Cell validation audit

- Reference and current cells are checked for finite shape and nonsingularity.
- Singular values are computed explicitly.
- The 2-norm condition number must not exceed `max_cell_condition_number`.
- The default limit is $10^{12}$.
- An over-conditioned cell raises `InvalidCellGeometryError`; no reuse claim is made.
- A rigid rotation has $\sigma_{\min}=1$ and does not consume affine margin.

## Ensemble audit

Independent ensembles do not provide continuous fractional coordinates.

- If the cell is unchanged, the stage S2 reference-relative MIC displacement bound is used.
- If the cell changes, the cache rebuilds with reason `fractional_unwrapping_unavailable`.

No temporal unwrap is inferred from independently wrapped samples.

## Rebuild provenance

The S3 implementation distinguishes:

```text
initial_build
cell_changed
displacement_limit
cell_deformation_limit
nonaffine_displacement_limit
fractional_unwrapping_unavailable
nonfinite_deformation_margin
```

Successful reason counts sum exactly to successful rebuilds.

## Focused acceptance matrix

The focused suite verifies cached/dense/fresh-cell-list equality for:

- isotropic expansion;
- isotropic compression with positive margin;
- compression crossing the affine limit;
- orthorhombic strain;
- volume-preserving shear;
- combined shear and nonaffine thermal motion;
- rigid cell rotation;
- nonaffine threshold crossing;
- mobile singleton species versus an immobile framework;
- periodic boundary crossing during deformation;
- an omitted pair just outside the list radius driven near the exact margin;
- randomized triclinic variable-cell paths;
- changed-cell independent-ensemble fallback without inferred unwrapping;
- explicit ill-conditioned-cell rejection.

## Regression result

```text
Python compileall:  passed
Ruff:               passed
Focused cache tests: 25 passed
Complete regression: 272 passed
Expected warnings:   24
```

## Result

The S3 acceptance gate passed. Within the documented unique-image regime and fixed-population collection contract, deformation-aware reuse is conservative by construction and produces the same scientific neighbor lists as fresh dense and fresh exact cell-list evaluation on every tested frame.
