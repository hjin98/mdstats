---
title: "Stage 11E6b Observed Transition-Path Ensembles and Collective-Event Diagnostics"
version: "0.20.7a0"
date: "2026-07-25"
status: implemented
owner: "mdstats.analysis.density.transition_paths"
---

# Purpose and boundary

Stage 11E6b reconstructs observed transition paths from the exact compact sample
indices retained by Stage 11E6. It publishes source-bound registered paths,
periodic translations, first-hit resolution, optional ring-sector and force
evidence, path ensembles, and concurrent-event context. It does not infer a
rate, barrier, minimum-free-energy path, detailed balance relation, global PMF,
or kinetic network.

The fixed input hierarchy is:

1. Stage 11E0b owns registered positions, wrapped fractional coordinates,
   integer image shifts, transformed forces, physical-time provenance, atom
   identity, source segments, and registration-group membership.
2. Stage 11E6 owns final residence and passage intervals under declared
   hysteresis and ambiguity policies.
3. Optional structural evidence supplies exact ring IDs, sectors, ordered
   coordination features, harmonics, aperture, puckering, local occupancy,
   density, or PMF samples without changing the E6 event identity.

No path result may alter an upstream state, residence, passage, raw label, or
sample coordinate.

# Borrowed background and package-specific construction

Transition-path ensembles and reactive trajectories are established background
[S11-8]. Core-set first-hit logic and metastable-state residence definitions are
standard background [S11-29, S11-30].

The following are mdstats-specific constructions:

- reconstruction from immutable E6 compact sample brackets;
- a stored first-hit resolution taxonomy that forbids interpolation;
- event identity including an integer periodic translation;
- a registration-compatibility certificate for pooling independent runs;
- a typed path-evidence table that retains exact ring-sector coordination and
  harmonic values without converting them into a new state;
- deterministic collective-event diagnostics that do not imply a many-body
  kinetic model;
- a strict separation between an observed connection, an undersampled path
  ensemble, and a resolved path ensemble.

# Event reconstruction

For an E6 passage from source state $A$, the path begins with the last retained
sample of the source residence, includes every compact passage sample, and ends
with the first retained sample of the subsequently resolved target residence
when one exists. Duplicate bracket endpoints are removed without reordering.

The stored arrays include:

- compact sample indices;
- source frame indices and frame IDs;
- physical times when the E0b trajectory has a time axis;
- represented-time weights;
- registered Cartesian positions;
- registered wrapped fractional positions;
- integer image shifts;
- transformed force covectors and an authoritative force-availability mask.

No coordinate interpolation or synthetic core crossing is allowed.

## First-hit resolution

Each event stores one of:

```text
resolved_first_hit
temporally_bracketed_first_hit
multiple_targets_between_frames
target_ambiguous
gap_interrupted
failed_excursion
recrossing
right_censored
```

A unique E6 state change with contiguous stored frames is a resolved first hit.
A unique state change whose target bracket spans missing output frames is
`temporally_bracketed_first_hit`. Unsupported evidence becomes
`gap_interrupted`; assignment conflict becomes `target_ambiguous`. Failed
excursions, recrossings, and censoring remain explicit and are not pooled with
successful paths. `multiple_targets_between_frames` is emitted only when the caller supplies an
explicit passage-bound set of more than one admissible target for one output
interval. E6b retains that set, marks the passage unsuccessful for ensemble
pooling, and never invents candidates from nearest states.

The minimum resolvable duration is the smallest positive stored time spacing on
the path, or the smallest positive represented-time weight when no physical
clock is available. Cadence limits remain data, not an interpolation request.

# Periodic path identity

For an event with retained image shifts $\mathbf n_0$ and $\mathbf n_1$, the
periodic translation is

$$
\boldsymbol\lambda_{AB}=\mathbf n_1-\mathbf n_0\in\mathbb Z^3.
$$

The implementation validates this equality directly. Wrapped endpoint
subtraction is never used as a substitute. Two events with the same source and
target states but different $\boldsymbol\lambda_{AB}$ belong to different
periodic-network connections.

# Optional structural and force evidence

`TransitionPathEvidenceTable` is sample-indexed and source-bound. It may retain:

- persistent ring IDs and ring-sector IDs;
- exact ordered M--O, M--T, oxygen-class, or other named coordination features;
- named harmonic amplitudes and phases;
- aperture and puckering;
- local occupancy;
- density and optional PMF values.

Evidence can be complete, partial, or unavailable along a path. Missing rows are
marked by the status and finite placeholder arrays; they are not interpreted as
physical zeros. The most frequent nonnegative ring ID is retained as a
provisional primary structural association, while any competing ring identity
sets `structural_ambiguity=True`.

The event separately retains the minimum supplied density and highest supplied
PMF value. These are observations along the stored path, not a saddle, barrier,
or minimum-free-energy-path claim.

# Registration compatibility

Independent registered trajectories may contribute to one path ensemble only
through `RegistrationCompatibilityClass`. The class binds:

- every member sample-catalog signature;
- each distinct registration signature;
- one shared registration-group signature, unless all members use the identical
  registration;
- each registration-policy signature;
- one represented-time unit convention;
- an explicit member-local to canonical state correspondence when state IDs are
  not already shared.

The upstream registration group certifies one registered cell, periodic axes,
analysis metric, and lattice gauge. Distinct source and transform signatures are
retained rather than erased.

# Path ensembles

Successful paths are grouped only when they share:

- canonical source and target state;
- periodic translation $\boldsymbol\lambda_{AB}$;
- primary structural association, including `None`;
- one registration-compatibility signature;
- no unresolved gap or assignment conflict.

The ensemble status is:

```text
single_observed_path
path_ensemble_undersampled
path_ensemble_resolved
```

The path count threshold is declared in `TransitionPathOptions`. One observed
jump establishes one observed connection but cannot identify a rate,
representative pathway, or detailed-balance partner.

Optional path-shape clustering is disabled by default. When enabled, it is
admitted only above a separate minimum path count. Paths are resampled by
registered arclength solely for comparison; original physical time and every
source coordinate remain authoritative. Deterministic RMSD-connected components
produce diagnostic cluster labels and no kinetic model.

# Concurrent and collective-event context

Events on different ions within the same member and source segment are compared
over a declared frame window. Each event retains concurrent event IDs and
state-occupancy counts immediately before, during, and after its stored frame
interval.

The diagnostic class is one of:

```text
isolated_single_ion
temporally_overlapping
candidate_exchange
candidate_concerted
collective_unresolved
```

Opposite overlapping state changes are candidate exchanges. Same-direction
overlapping successful changes are candidate concerted events. These labels are
screening evidence only and do not create a many-body state or rate law.

# Resource and serialization contracts

Resource preflight covers event count, path samples, ensembles, annotation
values, and estimated serialized bytes before a result is returned. All public
records are immutable, strictly JSON serializable, deterministically ordered,
and SHA-256 signed. Deserialization recomputes nested signatures and rejects
modified path coordinates, image translations, evidence arrays, or ensemble
membership.

# Acceptance tests

The focused gate includes:

- one jump producing one observed connection but no rate or representative path;
- repeated paths retaining physical time and periodic image translations;
- gap-interrupted and failed passages excluded from successful ensembles;
- exact structural, harmonic, density, PMF, and force-evidence retention;
- registration-compatible pooling of independent runs with distinct
  registration signatures;
- concurrent opposite events classified as candidate exchange;
- serialization, tamper rejection, resource preflight, and public exports;
- adjacent E0b--E6, registration, topology, VASP/ASE, documentation, and API
  regressions against real ASE 3.29.0.

# References

[S11-8] Metzner, P., Schuette, C., and Vanden-Eijnden, E. (2009). *Transition
Path Theory for Markov Jump Processes*. Multiscale Modeling and Simulation, 7,
1192-1219. DOI: 10.1137/070699500.

[S11-29] Sarich, M., Noe, F., and Schuette, C. (2010). *On the Approximation
Quality of Markov State Models*. Multiscale Modeling and Simulation, 8,
1154-1177. DOI: 10.1137/090764049.

[S11-30] Guarnera, E., and Vanden-Eijnden, E. (2016). *Optimized Markov State
Models for Metastable Systems*. Journal of Chemical Physics, 145, 024102.
DOI: 10.1063/1.4954708.
