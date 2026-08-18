---
title: "Stage 11E6 Final Hysteretic Segmentation and Residence Statistics"
version: "0.20.6a0"
date: "2026-07-25"
status: implemented
owner: "mdstats.analysis.density.final_segmentation"
---

# Purpose and boundary

Stage 11E6 converts the source-bound Stage-11E4 provisional spatial labels and,
when selected, the Stage-11E5b framework-conditioned moving regions into final
hysteretic state histories. The stage publishes residence intervals, passage
outcomes, censoring, occupancy bounds, and threshold/stride sensitivity. It does
not construct registered transition paths, barriers, rates, a PMF, or a kinetic
network; those remain Stage 11E6b and later.

The scientific input hierarchy is fixed:

1. Stage 11E0b owns compact ion samples, represented-time weights, atom identity,
   segment identity, and registration provenance.
2. Stage 11E4 owns immutable raw core, basin, transition, background, unknown,
   unresolved, and overlap labels.
3. Stage 11E5 owns the validated frozen state catalog.
4. Stage 11E5b may provide selected framework-conditioned moving cores/basins,
   static/dynamic counterfactual membership, overlap conflicts, and
   boundary-induced crossing evidence.

No Stage-11E6 result may alter any upstream state identity or raw spatial label.

# Borrowed background and package-specific construction

Core-set state definitions and core-entry/basin-retention hysteresis follow the
metastability and Markov-state-model background summarized by Prinz et al.
[S11-10] and the approximation analysis of Sarich, Noe, and Schuette [S11-29].
The package does not claim these ideas as original.

The following are package-specific constructions:

- exact source-signature binding across E0b, E4, E5, and optional E5b;
- immutable unsupported, unresolved, and assignment-conflict classes;
- simultaneous frozen, selected-moving, and agreement-only membership policies;
- explicit boundary-induced passage policy;
- represented-time occupancy lower/upper bounds under unresolved membership;
- a joint threshold/stride stability certificate that is separate from the raw
  segmentation and from later rate validation.

# Final membership contract

For compact sample index $n$, Stage 11E6 stores

$$
  (c_n, s_n, r_n),
$$

where $c_n$ is the final membership class, $s_n$ is a persistent state ID or
$-1$, and $r_n\in\{0,1,2\}$ denotes outside, basin, or core membership.

The classes are:

- evidence excluded;
- outside a supported state region;
- basin;
- core;
- unsupported/unknown;
- numerically unresolved;
- assignment conflict.

A state ID exists if and only if the sample is uniquely assigned to one basin or
core. Nearest-center filling is prohibited.

## Membership policies

`frozen_e4` uses the immutable E4 core/basin assignment.

`selected_geometry` uses the E5b selected moving regions while preserving E4
excluded, unknown, and unresolved samples.

`require_static_dynamic_agreement` accepts a state only when frozen and selected
moving memberships agree exactly; disagreement becomes an assignment conflict.

# Core-basin hysteresis

A final residence begins only after at least $m_{\mathrm{in}}$ consecutive core
samples for one state. Once entered, the state is retained through its core and
basin. A departure is confirmed only after at least $m_{\mathrm{out}}$
consecutive samples outside that state basin, unless a qualified core of another
state is encountered first.

A shorter departure followed by return is retained inside the residence and
reported as a retained excursion. After a confirmed exit, the next qualified
core determines the passage outcome:

- different state with no gap/conflict: resolved transition;
- same state within the recrossing window: recrossing;
- same state later: return excursion;
- unsupported or unresolved samples: unresolved gap;
- assignment conflict: conflict-interrupted passage;
- no subsequent core before the segment ends: right-censored exit.

Trajectory segment boundaries always reset hysteresis. Independent ensembles
retain spatial membership but publish no temporal intervals.

# Moving-boundary policy

E5b boundary-induced evidence is retained per sample and propagated to every
passage that intersects it. The declared policy is one of:

- `record`: retain a resolved transition while marking it boundary-induced;
- `mark_unresolved`: retain the passage but do not count it as a resolved
  transition;
- `exclude_event`: retain the diagnostic record but exclude it from transition
  statistics.

The event record always preserves the physical distinction; a boundary-swept
crossing is never silently relabeled ion-driven.

# Residence and passage records

Each residence stores:

- persistent state, atom, and segment identity;
- exact compact sample indices;
- represented time;
- core, basin, and retained-excursion time components;
- left and right censoring.

Each passage stores:

- source and optional target state;
- exact compact path-bracket sample indices;
- represented time;
- outcome;
- unknown, conflict, and boundary-induced flags;
- whether it contributes to the resolved transition count.

Full registered coordinates and periodic translations along the passage are not
copied here; Stage 11E6b reconstructs them from source-bound sample indices.

# Occupancy and residence statistics

For state $i$ and frame $t$, let $N_i(t)$ be the number of ions finally assigned
to state $i$, and let $A(t)$ be the number of ambiguous ions. With represented
frame weight $w_t$, the ion-time and mean-occupancy bounds are

$$
  T_i = \sum_t w_t N_i(t),
$$

$$
  \bar N_i^{\mathrm{L}}
  = \frac{\sum_t w_t N_i(t)}{\sum_t w_t},
  \qquad
  \bar N_i^{\mathrm{U}}
  = \frac{\sum_t w_t [N_i(t)+A(t)]}{\sum_t w_t}.
$$

Vacancy bounds use definite vacancy, $N_i=0$ and $A=0$, and possible vacancy,
$N_i=0$. Multiple-occupancy bounds analogously use $N_i>1$ and
$N_i+A>1$.

Residence summaries report counts, uncensored counts, resolved departures,
total ion-time, and mean/median uncensored residence time. No exponential,
Markovian, or rate-law assumption is introduced.

# Stability certificate

The final segmentation is rerun over a declared set of
$(m_{\mathrm{in}},m_{\mathrm{out}})$ pairs and frame strides. Every run retains
its residence count, resolved-transition count, and state occupancy vector.
Relative transition-count change and absolute occupancy change are measured
against the baseline.

The catalog status is:

- `stable` when event support is adequate and all declared changes remain within
  tolerance;
- `unstable` when a declared threshold or stride exceeds tolerance;
- `insufficient_events` when too few resolved transitions exist;
- `ensemble_unavailable` for independent ensembles.

This certificate is required before final event statistics are used downstream,
but it is not a rate-validation certificate.

# Resource and serialization contracts

All sample, state, residence, passage, sensitivity-run, and output-byte limits are
checked transactionally. Results are immutable, strict-JSON serializable,
source-bound, deterministically ordered, and SHA-256 signed. Deserialization
recomputes every signature and rejects tampering.

# Acceptance tests

The focused gate includes:

- a resolved two-state jump;
- a retained short excursion;
- unsupported-gap rejection;
- segment-reset and ensemble semantics;
- threshold/stride stability;
- moving-membership source requirements;
- occupancy and censoring invariants;
- serialization, tamper rejection, resources, and public API.

# References

[S11-10] Prinz, J.-H., Wu, H., Sarich, M., Keller, B., Senne, M., Held, M.,
Chodera, J. D., Schuette, C., and Noe, F. (2011). *Markov Models of Molecular
Kinetics: Generation and Validation*. Journal of Chemical Physics, 134, 174105.
DOI: 10.1063/1.3565032.

[S11-29] Sarich, M., Noe, F., and Schuette, C. (2010). *On the Approximation
Quality of Markov State Models*. Multiscale Modeling and Simulation, 8,
1154-1177. DOI: 10.1137/090764049.
