# Stage 11 architecture revision 12 audit

Date: 2026-07-24  
Package source version: `0.19.91a0`  
Scope: planning and documentation only

## Audit objective

Resolve the remaining implementation-contract issues identified after revision 11 without changing production source code or tests.

## Corrections applied

1. **Composed reference-material registration**
   - Cell mapping and translation registration are orthogonal policy components.
   - The normative map is
     \[
     \mathbf q_{i,t}=(\mathbf x_{i,t}-\mathbf c_t)H_t^{-1}H_{\mathrm{ref}}+\mathbf c_{\mathrm{ref}}.
     \]
   - Source and registered center coordinate conventions are explicit.

2. **Reference-cell provenance and initial scope**
   - Added immutable `ReferenceCellDefinition`.
   - Initial choices are explicit matrix or selected source frame.
   - Initial `reference_material` support is fully periodic, full-rank 3D only.

3. **Force semantics**
   - Geometric force-transform status is separate from PMF-force admissibility.
   - Variable-cell reference-material force covectors remain PMF-inadmissible until the required thermodynamic measure is derived.

4. **Segment-aware time weighting**
   - Frame weights cannot cross restarts, missing intervals, ensemble or thermostat changes, topology-regime boundaries, or independent trajectories.

5. **Topology-regime segmentation**
   - Added regime identities, compatibility masks, connectivity-flicker masks, and structural-phase status.
   - Initial discovery requires one compatible topology regime.

6. **Periodic local charts**
   - Boundary-crossing isolated modes use minimum-image lifted coordinates.
   - Annular states require a certified intrinsic chart.
   - Unsupported general manifolds fail closed.

7. **Extended-attractor cores**
   - Isolated modes use maximum-to-saddle depth.
   - Extended attractors use local ridge-normal depth.
   - Weak angular corrugation cannot arbitrarily fragment one annular core.

8. **Ring-harmonic coordinate validity**
   - Radial spectra retain center kind, coordinates, and uncertainty.
   - Actual-angle spectra fail closed when projected angular coordinates are singular.

9. **Historical stage naming**
   - Implemented supplied-model specifications are labeled legacy/manual Stage 11E-M1 and 11E-M2.
   - Modules, APIs, and release behavior are unchanged.

## Consistency checks

- The architecture sequence now assigns C0 reference-cell and force-admissibility contracts before consumer migration.
- The sample catalog owns segment weights and topology regimes before density estimation.
- Attractor-local charts and type-specific cores precede local force fitting.
- Physical bond geometry remains separate from registered site-association geometry.
- Exact ordered ring coordinates remain authoritative over harmonic summaries.
- The manual branch and new data-driven Stage 11E1/E2 names are no longer ambiguous in maintained specifications.

## Source-tree impact

- Production Python source: unchanged.
- Tests: unchanged.
- Documentation changed:
  - Stage 11 architecture manual and PDF;
  - Stage 11E-M1 supplied site-topology specification and PDF;
  - Stage 11E-M2 supplied assignment specification and PDF;
  - root README, changelog, and architecture index;
  - this audit.

## Implementation readiness

Stage C0A1 is ready to enter specification and implementation. The revision establishes the normative requirements that Stage C0A1/C0A2 must satisfy; it does not implement them.
