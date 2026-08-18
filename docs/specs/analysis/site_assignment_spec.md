---
title: "mdstats legacy/manual Stage 11E-M2 trajectory site-assignment specification"
author: "mdstats"
date: "2026-07-24 (documentation reclassification only)"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.85in
fontsize: 10pt
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \setlist{nosep}
---

# Scope

Legacy/manual Stage 11E-M2 maps persistent Stage-11E-M1 geometric site hypotheses onto mobile-ion
trajectory coordinates using the instantaneous Stage-11B/11C2 tile and ring
frames. The result is descriptive geometric evidence. It does not certify a
metastable free-energy basin, a barrier, or a Markov model.

The public entry point is:

```python
assign_trajectory_sites(
    collection,
    frame_tiling_geometry,
    frame_ring_geometry,
    site_topology,
    site_network,
    assignment_profile,
    *,
    species=None,
    atom_indices=None,
    options=None,
    resources=None,
)
```

The analysis requires a trajectory and one explicit assignment profile bound to
the Stage-11E-M1 topology profile. This implemented supplied-model branch is not
the new data-driven Stage 11E2 deterministic-attractor stage. Public module names
and release behavior are unchanged by this documentation reclassification.

# Source identity and frame alignment

The implementation shall reject inputs unless:

- the frame-ring catalog is bound to the supplied frame-tiling catalog;
- both frame catalogs use the same selected collection-frame sequence;
- the Stage-11E-M1 topology is bound to the same reference tile and ring catalogs;
- the structural network is bound to the supplied site topology;
- the selected atoms all match the declared target species; and
- the selected frames are strictly increasing trajectory frames.

No frame, ring, site, or ion identity is re-enumerated.

# Explicit basin rules

A `SiteAssignmentRule` selects states by an exact state key or by a conjunction
of state kind, optional landscape regime, and optional interface label. Every
Stage-11E1 state must match exactly one rule.

For a ring-local point state with expected local coordinate
$(z_0,u_0,v_0)$ and instantaneous ion coordinate $(z,u,v)$, define

$$
S^2 = \left(\frac{z-z_0}{a_z}\right)^2
    + \frac{(u-u_0)^2+(v-v_0)^2}{a_\perp^2}.
$$

For a cage-interior state, use the isotropic score

$$
S = \frac{\lVert\Delta\mathbf r\rVert}{a_\perp}.
$$

For an annular state of radius $\rho_0$,

$$
S^2 = \left(\frac{z}{a_z}\right)^2
    + \left(\frac{\rho-\rho_0}{a_\perp}\right)^2,
\qquad
\theta=\operatorname{atan2}(v,u).
$$

The core basin is $S\le1$. The explicit transition shell is

$$
1<S\le\gamma,
$$

where `transition_multiplier = gamma > 1`.

There is no automatic nearest-state fallback.

# Assignment outcomes

For each selected ion and frame:

1. exactly one core candidate gives `assigned`, or `annular_assigned` for an
   annular state;
2. two or more core candidates give `ambiguous`;
3. no core candidate but one or more transition-shell candidates gives
   `transition_region`;
4. no accepted or transition candidate gives `unassigned`; and
5. if no state geometry can be realized in the frame, the outcome is
   `frame_unresolved`.

Candidate diagnostics are deterministically ordered by core membership,
transition membership, score, state index, and image shift. The result retains
only a configured finite number of leading diagnostics.

# Periodic image convention

For every candidate, the general-cell minimum-image operation is applied to the
raw site-to-ion Cartesian displacement. If

$$
\Delta\mathbf r_{\mathrm{MIC}}
=\Delta\mathbf r_{\mathrm{raw}}+\mathbf mH,
$$

then the closest site image is labelled by

$$
\mathbf s=-\mathbf m.
$$

An observed accepted transition from $(i,\mathbf s_i)$ to
$(j,\mathbf s_j)$ carries

$$
\lambda_{ij}^{\mathrm{obs}}=\mathbf s_j-\mathbf s_i.
$$

A structural network match requires the source state, target state, and
periodic translation to agree exactly with a Stage-11E1 candidate edge.
Multiple matching multigraph edges are retained. Events with no matching edge
are reported explicitly as off-network observations.

# Temporal statistics

Each ion receives a dense frame-state sequence. Physical state IDs occupy
`0..n_physical_states-1`; four deterministic auxiliary IDs represent:

- ambiguous;
- transition region;
- unassigned; and
- frame unresolved.

The complete sequence is passed to
`compute_state_transition_statistics()`. Physical occupancy arrays and accepted
state-to-state events are also reported separately. A boundary involving an
auxiliary state is not converted into a direct physical transition across the
gap.

A change in periodic image label is an observed event even when the physical
state index is unchanged.

# Immutability, resources, and replay

All arrays are defensive read-only copies and all nested metadata are immutable.
Resource preflight bounds frames, selected ions, states, candidate evaluations,
and retained diagnostics before assignment begins.

Canonical serialization is source-bound. `from_dict()` reruns the calculation
with the supplied sources and rejects any noncanonical or tampered payload.

# Deferred boundaries

Stage 11E2 does not provide:

- energetic basin certification;
- probabilistic soft assignment;
- hidden-state inference or temporal smoothing;
- transition-state or rate estimation;
- censoring-corrected survival analysis;
- many-ion occupancy constraints; or
- automatic basin-width inference from ring order or ionic radius.
