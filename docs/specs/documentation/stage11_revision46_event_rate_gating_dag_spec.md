---
title: "Stage 11 Revision 46 Event, Rate, Gating, and DAG Consistency"
author: "mdstats"
date: "2026-07-27"
version: "0.20.16a0"
status: "superseded by revision 47"
---

# Purpose

This historical contract is superseded by
`stage11_revision47_provenance_kinetic_pmf_dag_spec.md`.

This specification prevents recurrence of event/path/rate over-gating, late gating-model
selection, thermodynamic-branch serialization, omitted PMF/E8a/manual-model branches,
and phrase-only dependency tests.

# Required dependency contracts

- `FinalTransitionEventCertificate` may create an `ObservedEventEdge` without an E6b path
  or a THERMO3B saddle.
- E6b creates optional `PathResolvedEdge` geometry. THERMO3B creates optional
  `TransitionStateAnnotatedEdge` evidence.
- E7 is an event network first. Path and saddle records enrich but do not define whether
  an event edge exists.
- E9A owns pre-rate event-process and state-model adequacy and may fit non-promoted
  diagnostic models.
- G0 occurs after E9A and before F0. Gating augmentation creates a new signed model
  generation and a bounded replay, not an in-generation graph cycle.
- F0 empirical rates depend on final events, event exposure, E9A, and an accepted G0 state
  model. E6b and THERMO3B are forbidden required dependencies.
- E9B validates the fitted F0 model before propagation.
- F1 barrier-derived rates require THERMO3B but do not require F0.
- Detailed balance is a conditional F0/THERMO4B product requiring an independent
  equilibrium population certificate and compatible measure.
- THERMO4A branches from basin thermodynamics and held-out thermodynamic validation; it
  does not require THERMO3A.
- THERMO3A branches from SAMP2, converged corridor numerics, and THERMO0.
- PMF is an optional branch with explicit STAT2/STAT3/E3B/grid/support dependencies.
- E8a is a milestone dossier with ENS, STAT, GR, SAMP, and scope sub-dossiers. Optional
  PMF/thermodynamic/path/rate evidence does not gate earlier milestones.
- M1/M2 are explicitly represented as a supplied-model branch outside discovered-site
  selection.

# Evidence partition contract

The only normative crossfit vocabulary is:

```text
discovery
model_selection
basin_validation
corridor_validation
thermodynamic_validation
optional_final_refit
```

No generic `final_validation_blocks` partition may own all evidence channels.

# Transition thermodynamic ownership

- THERMO3A owns `StaticTransitionRegionThermodynamics`.
- THERMO3B owns `TransitionStateValidationCertificate`.
- `SaddleThermodynamicCertificate` is promoted only as a source-bound composition of the
  exact THERMO3A and THERMO3B products.

# Machine-readable DAG

`docs/arch_manuals/stage11_dependency_graph.json` is normative. Tests must verify:

- acyclicity of required dependencies;
- presence of PMF, E8a milestone, and M1/M2 nodes;
- G0 precedes F0;
- F0 is not required to depend on E6b/THERMO3A/THERMO3B/F1;
- THERMO4A is not required to depend on THERMO3A;
- E7 requires E6 but treats E6b/THERMO3B as optional enrichments;
- obsolete partition vocabulary and release chronology are absent from the normative
  manual.
