---
title: "Stage 11 Revision 45 Dependency, Force, and Transition Consistency"
author: "mdstats"
date: "2026-07-27"
version: "0.20.16a0"
status: "normative planning contract"
---

# Purpose

This specification prevents recurrence of the revision-44 stage-order, ensemble-force,
cross-fitting, and transition-promotion contradictions.

# Required contracts

- The authoritative dependency graph is revision 45 and is a DAG with product-specific gates.
- Control-inferred dynamics, realized trajectory consistency, and thermodynamic admissibility are separate records.
- E3A mechanical refinement is distinct from E3B canonical thermodynamic mean-force validation.
- Canonical force-density and harmonic equipartition identities are not applied generally to NVE.
- `EvidenceCrossfitPartition` contains discovery, model selection, basin validation,
  corridor validation, thermodynamic validation, and optional final-refit domains.
- SAMP2 stops at preliminary corridor and saddle-candidate support.
- E6 owns `FinalTransitionEventCertificate`.
- THERMO3A owns static finite-region thermodynamics; THERMO3B owns event/path-conditioned
  transition-state validation and any `validated_transition_saddle` promotion.
- THERMO4A precedes E8b thermodynamic comparison; THERMO4B follows empirical/barrier rates.
- Stage 11F0 owns `RateBoundModel`; Stages 11G--11I have explicit roadmap deliverables.
- Historical implementation bullets belong to the status appendix, not the normative manual.
