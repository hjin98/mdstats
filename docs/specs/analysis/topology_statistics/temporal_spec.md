---
title: "Topology Temporal Statistics Specification"
subtitle: "Normative TS3 API for Exact State Timelines, Residence Intervals, Transition Matrices, Return Lags, and Entity-Presence Episodes in mdstats"
author: "mdstats"
date: "2026-07-14 (implemented TS3 revision)"
geometry: margin=0.86in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \usepackage{array}
    \definecolor{codegray}{RGB}{247,247,247}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose and status

This document specifies the implemented module

```text
mdstats/analysis/topology_statistics/temporal.py
```

and its public re-export surface through

```python
mdstats.analysis.topology_statistics
mdstats.analysis
mdstats
```

for topology-statistics Stage TS3. The implementation is introduced in
`mdstats 0.17.0a3`. TS4 reuses the same axis and state assignments in `0.17.0a4` to classify cross-layer boundary consequences.

TS3 consumes an already-defined trajectory frame axis and an authoritative state
assignment. It derives exact temporal organization without reconstructing atomic
connectivity, framework topology, rings, sites, or cages.

The governing boundary is

$$
\boxed{
\text{catalogs define graph identity; TS3 describes ordered occurrences}
}.
$$

The implemented layer provides:

- exact maximal state-residence intervals;
- exact changed-state transition events;
- adjacent-state and changed-state count matrices;
- per-state visits, dwell lengths, recurrence, and return lags;
- cumulative changed-boundary series;
- generic dense-entity presence episodes;
- explicit left- and right-boundary censoring flags;
- typed integration with atomic contacts and projected framework edges;
- immutable, schema-versioned result objects and SHA-256 digests;
- strict rejection of unordered ensemble semantics.

Transition probabilities, kinetic rates, autocorrelation, Markov modeling,
censoring-corrected survival estimation, and statistical uncertainty remain
deferred.

# Motivation

The TS1 and TS2 modules summarize catalog occupancies and aggregate graph changes,
but those summaries do not preserve the exact frame boundary where an event
occurred. Scientific validation and later transport analysis require answers to
questions such as:

- At which stored frame did the state change?
- How long did each state remain continuously occupied?
- Did a state disappear and later recur?
- Which state-to-state changes were observed, and how many times?
- During which intervals was one atomic contact or framework edge present?
- Was an observed episode already active at the beginning or still active at the
  end of the analyzed window?

TS3 standardizes these questions once so atomic and framework statistics do not
implement incompatible notions of residence, transition, or lifetime.

# Scientific responsibility boundaries

## Owned by `temporal.py`

The module owns graph-independent trajectory organization:

- validation that the axis represents a trajectory;
- maximal contiguous residence segmentation;
- exact changed-state event records;
- adjacent-state count matrices;
- changed-state count matrices with a zero diagonal;
- cumulative changed-boundary counts;
- per-state dwell and return summaries;
- generic episodes for dense integer entity IDs;
- sample-span and physical-time-span conventions;
- boundary-censoring flags;
- immutable serialization and stable digests.

## Not owned by `temporal.py`

The module must not:

- infer chemical connectivity;
- choose atomic contact identity;
- choose framework-edge identity;
- project framework paths;
- infer trajectory order from an ensemble;
- calculate transition probabilities or rates;
- call an episode a reaction lifetime, adsorption residence, or site residence;
- enumerate primitive rings;
- perform correlation or Markov analysis.

Atomic TS1 defines gauge-invariant contact keys. Framework TS2 defines canonical
`FrameworkEdgeKey` identity. TS3 receives only dense entity IDs derived from those
authoritative keys.

# Module relationships

```text
FrameAxis + frame-to-state IDs
              |
              v
          temporal.py
      /                       \
     v                         v
state timeline          dense entity episodes
     |                         |
     v                         v
atomic.py                framework.py
contact keys             FrameworkEdgeKey records
```

The generic episode result contains integer entity IDs only. The consuming branch
stores the ordered key tuple that gives those IDs scientific meaning.

# Public schema constants

```python
CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA = (
    "mdstats.topology-statistics.temporal.v1"
)
```

TS3 uses the package-wide topology-statistics digest algorithm:

```text
sha256
```

# Public API summary

```python
@dataclass(frozen=True, slots=True)
class TemporalStatisticsOptions: ...

@dataclass(frozen=True, slots=True)
class StateResidenceInterval: ...

@dataclass(frozen=True, slots=True)
class StateTransitionEvent: ...

@dataclass(frozen=True, slots=True)
class StateResidenceStatistics: ...

@dataclass(frozen=True, slots=True)
class StateTransitionStatistics: ...

@dataclass(frozen=True, slots=True)
class EntityPresenceEpisode: ...

@dataclass(frozen=True, slots=True)
class EntityPresenceStatistics: ...
```

Primary functions:

```python
def compute_state_transition_statistics(
    frame_to_state_id: ArrayLike,
    axis: FrameAxis,
    *,
    n_states: int | None = None,
    options: TemporalStatisticsOptions | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StateTransitionStatistics:
    ...
```

```python
def compute_entity_presence_statistics(
    state_entity_ids: Sequence[Sequence[int] | ArrayLike],
    frame_to_state_id: ArrayLike,
    axis: FrameAxis,
    *,
    n_entities: int | None = None,
    options: TemporalStatisticsOptions | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EntityPresenceStatistics:
    ...
```

# Input contracts

## `FrameAxis`

The supplied axis must satisfy

```python
axis.frame_semantics is FrameSemantics.TRAJECTORY
```

and must already pass the TS0 `FrameAxis` invariants:

- at least one frame;
- unique frame IDs;
- strictly increasing collection frame indices;
- if supplied, strictly increasing simulation steps;
- if supplied, finite strictly increasing physical times;
- a nonempty time unit whenever physical times are present.

An ensemble axis is rejected even when its stored sample order appears smooth.

## State assignments

`frame_to_state_id` must be a nonempty one-dimensional integer array with

$$
0\le s_f < S,
$$

where $S$ is `n_states` or the inferred value

$$
S=1+\max_f s_f.
$$

Its length must equal `axis.n_frames`.

Dense state IDs need not all be observed when `n_states` is supplied explicitly.
Unobserved states receive zero visits and no dwell distribution.

## Entity membership by state

`state_entity_ids[k]` lists the dense entity IDs present in catalog state $k$.
Each state collection must contain nonnegative integers. Duplicate IDs are
removed deterministically.

For $K$ supplied state collections,

$$
0\le s_f<K.
$$

If `n_entities` is supplied, every observed entity ID must satisfy

$$
0\le e<n_{\mathrm{entities}}.
$$

The generic layer does not attach chemical meaning to an entity ID.

# Time and duration convention

Stored trajectory frames are sampled instants, not explicit interval boundaries.
TS3 therefore reports two separate quantities.

For a residence interval covering inclusive result positions $a$ through $b$:

$$
N_{\mathrm{frames}}=b-a+1,
$$

and the sample span is

$$
L_{\mathrm{sample}}=b-a=N_{\mathrm{frames}}-1.
$$

When physical times are available, the physical sample span is

$$
\Delta t=t_b-t_a.
$$

A one-frame interval has

$$
N_{\mathrm{frames}}=1,
\qquad
L_{\mathrm{sample}}=0,
\qquad
\Delta t=0.
$$

TS3 does not extrapolate half-step boundaries or invent an interval duration
beyond the stored instants. This convention is recorded in metadata.

# State residence intervals

For a state sequence $s_f$, a residence interval is a maximal half-open range

$$
[a,b)
$$

such that

$$
s_f=s_a
\quad\text{for every}\quad
f\in\{a,a+1,\ldots,b-1\}.
$$

Maximality requires either $a=0$ or $s_{a-1}\ne s_a$, and either $b=F$ or
$s_b\ne s_{b-1}$.

## `StateResidenceInterval`

Important fields:

```python
interval_id: int
state_id: int
result_position_start: int
result_position_stop: int       # exclusive
collection_frame_index_start: int
collection_frame_index_end: int # inclusive endpoint
frame_id_start: int
frame_id_end: int
n_frames: int
sample_span: int
step_start: int | None
step_end: int | None
step_span: int | None
time_start: float | None
time_end: float | None
time_span: float | None
```

The property

```python
result_position_end
```

returns `result_position_stop - 1`.

Intervals are sorted by result position, assigned dense IDs, and partition the
complete trajectory exactly.

# Transition events and matrices

A changed-state event occurs at boundary $f-1\rightarrow f$ when

$$
s_f\ne s_{f-1}.
$$

## `StateTransitionEvent`

Each event records:

- dense event ID;
- result positions before and after the boundary;
- source and target state IDs;
- collection frame indices;
- external frame IDs;
- optional simulation steps;
- optional physical times.

Self-boundaries are not represented as events.

## Adjacent-state count matrix

TS3 reports the complete adjacent count matrix

$$
A_{ij}
=
\sum_{f=0}^{F-2}
\mathbf 1[s_f=i\land s_{f+1}=j].
$$

Its diagonal contains unchanged adjacent boundaries.

## Changed-state count matrix

TS3 also reports

$$
M_{ij}=
\begin{cases}
A_{ij}, & i\ne j,\\
0, & i=j.
\end{cases}
$$

The total changed-boundary count is

$$
N_{\mathrm{change}}=\sum_{i,j}M_{ij}.
$$

No row normalization is performed. Counts are descriptive; probabilities and
rates require additional sampling assumptions.

# Per-state residence and recurrence

## `StateResidenceStatistics`

For each declared state, TS3 records:

- interval IDs;
- visit count;
- total occupied frame count;
- exact dwell-frame-length distribution;
- physical sample-span summary when times are available;
- return-frame lags;
- return-time lags when times are available.

For consecutive visits $[a_k,b_k]$ and $[a_{k+1},b_{k+1}]$ to the same state, the
return frame lag is defined as

$$
\Delta f_{\mathrm{return},k}=a_{k+1}-b_k.
$$

The physical return lag is

$$
\Delta t_{\mathrm{return},k}=t_{a_{k+1}}-t_{b_k}.
$$

This measures the lag between the last stored sample in one visit and the first
stored sample in the next visit. It is not a first-passage time estimate between
continuous-time boundaries.

# Cumulative changed-boundary series

The per-frame cumulative event count is

$$
C_0=0,
$$

$$
C_f=
\sum_{k=1}^{f}
\mathbf 1[s_k\ne s_{k-1}].
$$

It is stored as an immutable TS0 `ScalarSeries` aligned with the original
`FrameAxis`.

# Generic entity-presence episodes

An entity-presence episode is a maximal interval during which one dense entity ID
is present in every frame's assigned catalog state.

## `EntityPresenceEpisode`

Fields include:

```python
episode_id: int
entity_id: int
result_position_start: int
result_position_stop: int
n_frames: int
sample_span: int
left_censored: bool
right_censored: bool
time_start: float | None
time_end: float | None
time_span: float | None
```

`left_censored=True` means the entity is already present at the first analyzed
frame. `right_censored=True` means it remains present at the last analyzed frame.
The flags describe observation-window boundaries only. TS3 does not estimate a
censoring-corrected survival distribution.

## `EntityPresenceStatistics`

The aggregate object contains:

- all episodes sorted deterministically;
- episode count per entity;
- occupied frame count per entity;
- occupancy probability per entity;
- exact episode-frame-length distribution;
- physical episode sample-span summary when times are available.

The occupancy probability is

$$
p_e=\frac{N_e}{F},
$$

where $N_e$ is the number of frames in which entity $e$ is present.

# Integration with atomic statistics

TS1 now defines

```python
AtomicTemporalStatistics
```

containing:

```python
state_statistics: StateTransitionStatistics
contact_keys: tuple[AtomicContactKey, ...]
contact_episodes: EntityPresenceStatistics | None
```

Atomic contact identity remains gauge invariant:

$$
c=\{\min(i,j),\max(i,j)\}.
$$

State-local periodic image shifts do not define persistent contact identity.

`AtomicStatisticsOptions` adds:

```python
include_temporal_statistics: bool = True
include_contact_episodes: bool = True
temporal_options: TemporalStatisticsOptions
```

For trajectories, `compute_atomic_connectivity_statistics` computes exact state
and optional contact episodes. For ensembles, `temporal_statistics` is `None`.

# Integration with framework statistics

TS2 now defines

```python
FrameworkTemporalStatistics
```

containing:

```python
state_statistics: StateTransitionStatistics
edge_keys: tuple[FrameworkEdgeKey, ...]
edge_episodes: EntityPresenceStatistics | None
```

Framework episode identity uses canonical Stage 2 `FrameworkEdgeKey` records. It
therefore preserves:

- endpoint identities;
- normalized periodic translation;
- ordered linker identities and image offsets;
- complete whole-path rule identity.

`FrameworkStatisticsOptions` adds:

```python
include_temporal_statistics: bool = True
include_edge_episodes: bool = True
temporal_options: TemporalStatisticsOptions
```

For trajectories, `compute_framework_topology_statistics` computes class and
optional projected-edge episodes. For ensembles, `temporal_statistics` is `None`.

# Algorithms

## Residence segmentation

```text
start = 0
for boundary in 1 .. F-1:
    if state[boundary] != state[boundary - 1]:
        emit [start, boundary)
        start = boundary
emit [start, F)
```

This is $O(F)$ in time and $O(R)$ in interval storage, where $R$ is the number of
residence intervals.

## Transition matrices

```text
A = zeros(S, S)
for f in 0 .. F-2:
    A[state[f], state[f+1]] += 1
M = A
set diagonal(M) = 0
```

The cost is

$$
O(F+S^2).
$$

The dense matrix is appropriate for catalog state counts expected in the current
scope. Sparse alternatives may be added later for extremely large state spaces.

## Entity episodes

For each frame, TS3 compares the entity set of the current catalog state with the
previous set:

```text
new entities     = current - previous
removed entities = previous - current
```

New entities open episodes. Removed entities close episodes at the current frame
boundary. Remaining open episodes close at $F$.

The cost is approximately

$$
O\!\left(F+\sum_f |E_{s_f}\triangle E_{s_{f-1}}|\right)
$$

plus output storage. Catalog compression avoids reconstructing entity identity
from coordinates.

# Immutability and serialization

All public TS3 dataclasses are frozen. NumPy arrays are defensively copied and
made read-only.

Serialized objects include:

- schema version;
- object type;
- digest algorithm;
- axis and options;
- interval, event, matrix, and episode records;
- metadata;
- stable digest.

The structured payload defines equality. SHA-256 is a compact integrity and cache
identifier, not a substitute for validating the structured content.

# Edge cases and warnings

## Ensemble input

Direct TS3 computation on an ensemble raises `TopologyStatisticsInputError`.
Stored ensemble order must never be interpreted as time.

## One-frame trajectory

A one-frame trajectory is valid:

- one residence interval;
- zero changed boundaries;
- a zero adjacent matrix;
- zero physical sample span;
- no return lags.

## Uniform trajectory

A uniform trajectory has one residence interval and no changed-state events. Its
adjacent matrix may contain diagonal self-boundary counts.

## Unobserved declared states

An explicitly declared but unobserved state has:

- zero visits;
- zero occupied frames;
- no dwell distribution;
- no return lags.

## Zero-duration stored episodes

One-frame intervals and episodes have physical sample span zero. This does not
assert a physical lifetime of zero; it means the event is resolved at only one
stored instant.

## Boundary censoring

Episodes touching the analysis window are flagged but not corrected. Means of raw
episode spans may be biased when many episodes are censored.

## State identity dependence

Temporal statistics inherit every scientific assumption of the source catalog.
Changing cutoffs, hysteresis, framework mapping, or canonical identity changes the
state sequence and therefore the temporal result.

## Per-frame catalog mode

A trajectory catalog in per-frame mode can be summarized temporally, but every
frame has a distinct public state ID. The resulting transition count may reflect
that storage mode rather than repeated structural classes. Provenance must remain
visible.

# Complexity and memory

For $F$ frames, $S$ states, $R$ state residence intervals, $Q$ entity episodes,
and $K$ entities:

$$
T_{\mathrm{state}}=O(F+S^2),
$$

$$
T_{\mathrm{entity}}=O(F+Q)
$$

up to set-difference costs inherited from state entity memberships.

Storage is approximately

$$
O(F+S^2+R+Q+K).
$$

The main potentially large result is the explicit entity-episode table. Atomic
and framework options therefore allow episode generation to be disabled while
retaining exact state timelines.

# Validation requirements

The TS3 focused test suite must cover:

1. exact maximal residence segmentation;
2. exact changed-state event boundaries;
3. adjacent and changed transition matrices;
4. recurring sequence $A\rightarrow B\rightarrow A$;
5. return-frame and return-time lags;
6. uniform and one-frame trajectories;
7. ensemble rejection;
8. generic entity episode construction;
9. left- and right-censoring flags;
10. atomic contact-episode integration;
11. framework edge-episode integration;
12. optional disabling of detailed temporal outputs;
13. serialization round trips;
14. digest-tampering rejection;
15. custom quantile propagation;
16. read-only result arrays.

# Na-LTA acceptance case

For the validated 2,000-frame 300 K Na-LTA trajectory:

- the atomic state timeline contains 72 residence intervals and 71 changed-state
  boundaries under the selected hysteretic contact definition;
- Si-O and Al-O framework contacts remain invariant;
- Na-O contact episodes may form and end;
- the framework class timeline contains one residence interval and zero changed
  boundaries;
- all 96 projected framework edges form one window-spanning episode each;
- episode results must not be interpreted as ring-site hopping before ring-site
  geometry and assignment exist.

# Deferred features

The following are intentionally outside TS3:

- transition probabilities and rates;
- continuous-time Markov models;
- autocorrelation and integrated correlation times;
- state-lumping or approximate clustering;
- Kaplan-Meier or other censoring-corrected survival estimates;
- statistical uncertainty and block averaging;
- site-residence and cage-residence analysis;
- primitive-ring event statistics;
- hidden-state models;
- event causality or reaction classification.

# Implementation checklist

Before modifying TS3, verify:

- Is the input explicitly a trajectory?
- Does the state assignment align with the `FrameAxis`?
- Are state and entity IDs dense, nonnegative, and within range?
- Is the half-open interval convention preserved?
- Are event boundaries adjacent stored frames?
- Does the adjacent matrix include self-boundaries?
- Does the changed matrix have a zero diagonal?
- Are physical spans reported only when physical times exist?
- Are one-frame spans exactly zero?
- Are atomic contacts gauge invariant?
- Are framework edges canonical Stage 2 keys?
- Are boundary-censoring flags preserved?
- Are probabilities and rates still deferred?
- Do serialization schema and digest checks remain deterministic?

# Final contract

TS3 establishes the shared rule

$$
\boxed{
\text{temporal statistics describe exact stored-frame organization, not hidden continuous-time dynamics}
}.
$$

Atomic and framework branches may attach scientific entity identities to TS3's
dense episode IDs, but neither branch may redefine residence segmentation,
transition boundaries, duration conventions, or ensemble rejection.
