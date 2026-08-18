# Stage 11 architecture revision 13 audit

Date: 2026-07-24  
Package source version: `0.19.91a0`  
Scope: planning and documentation only

## Audit objective

Resolve the remaining estimator, topology, symmetry, moving-boundary, and finite-time transition contracts identified after revision 12 without changing production source code or tests.

## Corrections applied

1. **Kernel metric and reference-cell covariance**
   - Added immutable Gaussian covariance and coordinate-measure provenance.
   - Defined Cartesian-isotropic, fractional-isotropic, and explicit-covariance policies.
   - Required covariance transformation under equivalent fixed affine coordinate changes.
   - Added a reference-cell sensitivity check to the Na-LTA pilot.

2. **Triclinic periodized Gaussian**
   - Defined the normalized lattice image sum on the registered torus.
   - Added image-truncation and omitted-mass bounds.
   - Prohibited minimum-image substitution without a small-bandwidth certificate.
   - Defined fractional-grid volume quadrature.

3. **Ring harmonic measures**
   - Restricted the exact cyclic-index DFT to equal atom weights.
   - Added separately named boundary-measure angular moments.
   - Separated cyclic, physical-angle, and Nyquist gauge semantics.

4. **Density ridges and periodic topology**
   - Added a Hessian/eigenspace criterion for one-dimensional density ridges.
   - Added intrinsic-dimension and eigengap uncertainty.
   - Defined one canonical periodic cell complex for critical points, ridges, saddles, plateaus, and basins.
   - Added primary citations for nonparametric density ridges and cell-complex Morse theory.

5. **Numerical certification**
   - Separated field-error certification from topology-stability certification.
   - Treats unevaluated sparse blocks as unknown rather than zero.
   - Requires refinement around critical features and periodic seams.

6. **Symmetry identity**
   - Statistical state instances remain authoritative network nodes.
   - Added optional validated structural symmetry orbits with multiplicity, stabilizer, missing-member, and symmetry-breaking provenance.
   - Disabled default symmetry augmentation and pooling.

7. **Moving boundaries**
   - Added static and dynamic memberships, comoving ion displacement, boundary displacement, and boundary-induced crossing diagnostics.
   - Requires the frozen-basin counterfactual when a dynamic assignment model is used.

8. **Finite-resolution first-hit transitions**
   - Defined the target as the first subsequently resolved core.
   - Added resolved, bracketed, multiple-target, ambiguous, and gap-interrupted statuses.
   - Requires lattice translation from continuous registered unwrapped paths and image bookkeeping.

9. **PMF temperature**
   - Every PMF owns one declared thermodynamic temperature and reweighting provenance.
   - Nonstationary temperature segments cannot produce an unlabeled averaged-temperature PMF.

10. **Implementation order**
    - Core C0 affine registration precedes Stage 11C3 registered-view integration.
    - Added Stage C0A3 for registered structural embeddings and frame reconstruction.

## Consistency checks

- Markdown fenced blocks and display-math delimiters are balanced.
- All cited reference identifiers are defined; references S11-34 and S11-35 are added.
- Density and matched-force equations now use the same covariance-aware periodic-kernel notation.
- The bandwidth ladder is represented as covariance scales on one fixed metric shape or as an explicit covariance ladder.
- Stage deliverables, persistent data objects, validation fixtures, and deferred boundaries reflect the revised contracts.

## Source-tree impact

- Production Python source: unchanged.
- Tests: unchanged.
- Documentation changed:
  - Stage 11 architecture manual and PDF;
  - root README, changelog, and architecture index;
  - this audit.

## Implementation readiness

Stage C0A1 remains the next implementation stage. Revision 13 also makes the later Stage 11E1 and 11E2 specifications safe to write without silently changing the KDE operator or the topology of the learned site catalog.
