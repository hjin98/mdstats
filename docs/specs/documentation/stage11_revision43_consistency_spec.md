---
title: "Stage 11 Revision-43 Dependency, Temperature, and Quality Consistency Specification"
version: "0.20.16a0"
date: "2026-07-27"
---

# Purpose

This specification owns the corrections through architecture revision 43.
It is a documentation and planning contract; it does not change existing S0--S4
runtime algorithms or scientific outputs.

# Required corrections

- E0b owns immutable raw availability only; admissibility is attached by signed
  overlays referencing ENS/STAT certificates.
- No untested stationarity assertion may promote PMF or E5 evidence.
- Source energy channels are reconstructed before conservation analysis.
- STAT1 production-regime selection uses fixed source-level observables; held-out
  site-density stability is a later STAT3 refinement.
- Candidate discovery and basin/corridor validation are cross-fitted across disjoint
  complete-system blocks.
- E2 numerical density boundaries are not called validated saddles.
- NVT, NVE, NpT, and biased thermodynamics use distinct potential definitions.
- MBAR requires cross-evaluated reduced potentials or a certified equivalent map.
- Tagged-ion, pooled-orbit, occupation-vector, and joint-state probabilities are
  distinguished explicitly.
- Formal zero-event rate bounds require an E9/11F `RateBoundModel`.
- Source-control architecture is generic, with VASP as a versioned adapter.
- Current normative stage order appears once; descriptive history is maintained in a
  separate appendix.

# Acceptance

The normative manual must contain revision 43, `SimulationRunControls`,
`ProductionRegimeCatalog`, `EvidenceAdmissibilityOverlay`, `11E-STAT3`, the
cross-fitted SAMP sequence, ensemble-specific thermodynamic sections, and the
reduced-potential-matrix requirement. It must not contain an untested-stationarity promotion path, a current
"next implementation boundary" statement, or a source-authoritative ensemble or
temperature claim derived from the legacy pilot label.


# Revision-43 additions

- Ionic temperature is reconstructed from ionic kinetic energy and a signed active
  degree-of-freedom count using equipartition.
- Mean, standard deviation, autocorrelation-aware confidence, and drift are distinct
  reported quantities.
- The VASP adapter extracts numerical MD quality controls and per-step SCF traces from
  `vasprun.xml`.
- The only execution-quality outcomes are `strictly_qualified`, `degraded_quality`, and
  `unqualified`.
- Degraded quality warns and proceeds; only unqualified catastrophic integrity failure
  raises by default.
- Trajectory quality and method-specific thermodynamic admissibility remain separate.
