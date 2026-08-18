---
title: "Stage 11E7 Observed Periodic Network and Transferred-Model Validation"
version: "0.20.8a0"
date: "2026-07-25"
status: implemented
owner: "mdstats.analysis.density.observed_network"
---

# Purpose and boundary

Stage 11E7 composes the frozen Stage-11E5 statistical-state catalog with the
observed Stage-11E6b transition-path catalog. It publishes an observed periodic
network, compares that network with declared structural candidate edges, retains
site-complex, validated symmetry-orbit, and semantic-class summaries, constructs
compact transferred state models, and evaluates those models on untouched
final-validation or external-transfer domains.

The stage does **not** estimate rates, merge state instances, infer an
unobserved connection, augment samples by symmetry, refit the discovery model,
or create a many-body kinetic model. The optional global-PMF branch remains
separate.

# Identity hierarchy

The following identities remain distinct:

1. a statistical-state instance `(member_index, local_state_id)`;
2. a canonical state used only for compatible cross-run correspondence;
3. a structural site complex;
4. a validated symmetry orbit;
5. a semantic class; and
6. a compact transferred model.

A summary may reference several state instances, but no summary replaces those
instances. Symmetry-orbit membership never duplicates samples.

# Observed periodic network

An observed edge is created only from successful E6b path ensembles. Its key is

$$
(A,B,\boldsymbol\lambda),\qquad \boldsymbol\lambda\in\mathbb Z^3,
$$

where `A` and `B` are canonical source and target states and
$\boldsymbol{\lambda}$ is the certified endpoint image-shift difference retained
by E6b. Connections with different translations remain distinct.

Each edge retains:

- contributing path-ensemble and event IDs;
- observed event count;
- path-ensemble support statuses;
- mean and standard deviation of the minimum resolvable path duration;
- retained structural IDs; and
- one structural-comparison status.

No rate, branching probability, detailed-balance relation, or representative
mechanism is inferred.

# Structural-versus-observed comparison

Declared structural candidates are compared by exact source, target, and
periodic translation. The comparison classes are:

```text
observed_and_structural
observed_off_structural_network
structural_unobserved
structural_comparison_unavailable
```

A structural edge cannot create an observed edge. Conversely, an observed edge
outside the declared structural graph remains valid trajectory evidence and is
reported explicitly. Structural candidates absent from the trajectory are
retained as unobserved rather than deleted.

# Compact transferred state models

For every canonical state, E7 retains all contributing state-instance anchors.
A circular fractional-coordinate mean is recorded componentwise,

$$
\bar q_k=\frac{1}{2\pi}\arg\left[\frac{1}{N}
\sum_{j=1}^{N}\exp(2\pi i q_{jk})\right],
$$

with resultant concentration

$$
R_k=\left|\frac{1}{N}\sum_{j=1}^{N}\exp(2\pi i q_{jk})\right|.
$$

The exact instance anchors remain authoritative during transfer assignment.
Low concentration yields `periodic_anchor_ambiguous`; a one-instance model is
marked `single_instance`. The model also retains occupancy and basin-probability
summaries, structural identities, and semantic classes. It contains no rate or
free-energy parameter.

# Transfer domain

Every application declares immutable domain metadata:

- final-validation or external-transfer role;
- species, composition, and optional temperature;
- registered coordinate frame and units;
- registration or registration-group identity;
- a symmetric positive-definite analysis metric; and
- external-source provenance when applicable.

Registration mismatch is a result (`domain_mismatch`), not an implicit
coordinate conversion.

# Assignment and validation

For a target point `q`, the distance to state `s` is the smallest certified
triclinic-torus distance to any retained state-instance anchor:

$$
d_s(q)=\min_{a\in s}\min_{n\in\mathbb Z^3}
\sqrt{(q-a-n)^\mathsf T G(q-a-n)}.
$$

The C0A2 certified closest-image routine is used. Assignment is fail-closed:

- no state is assigned beyond the declared radius;
- close first and second candidates remain ambiguous;
- no anchor is refitted during application; and
- off-network target transitions remain explicit.

When reference labels exist, the mismatch fraction is evaluated only on
reference-labeled samples. Outcomes are:

```text
reproduced_within_uncertainty
partial_reproduction
off_network_events
failed_transfer
domain_mismatch
reference_unavailable
insufficient_evidence
```

An application result may be attached to the immutable model catalog without
changing the model-basis signature.

# Resource and serialization contracts

Resource preflight covers state instances, observed and structural edges,
transfer samples, and application count. Public records are immutable, strictly
JSON serializable, deterministically ordered, and SHA-256 signed. Deserialization
recomputes nested signatures and rejects modified nodes, edges, anchors, domain
metadata, assignments, or transfer outcomes.

# Borrowed background and package-specific construction

Periodic directed graphs, held-out validation, and external transfer tests are
standard background. Core-state and reactive-network concepts follow the
existing Stage-11 references, especially [S11-8], [S11-29], and [S11-30].

The following are mdstats-specific:

- preservation of state-instance, complex, orbit, class, and compact-model
  identities in one catalog;
- exact periodic-translation edge identity inherited from E6b;
- fail-closed structural-versus-observed comparison;
- circular anchor summaries while retaining all source anchors;
- source-bound model-basis signatures independent of attached applications; and
- explicit off-network and failed-transfer outcomes without model mutation.

# Acceptance tests

The focused gate requires:

- state instances, complexes, semantic classes, and compact models remain
  distinct;
- structural candidates never create observed edges;
- observed off-structural and structural-unobserved edges remain explicit;
- untouched validation reproduces the selected catalog within tolerance;
- ambiguous and out-of-radius samples remain unresolved;
- off-network external events and failed transfer remain explicit;
- domain mismatch fails closed;
- serialization, tamper rejection, resource preflight, and public exports pass;
- adjacent E5-E6b, registration, topology, ASE/VASP, documentation, and API
  regressions pass with real ASE 3.29.0.

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
