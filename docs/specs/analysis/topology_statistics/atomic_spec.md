---
title: "Atomic Connectivity Statistics Specification"
subtitle: "Normative TS1+TS3 API for Pair Counts, Degree Statistics, Contact Occupancy, Exact Timelines, and Contact Episodes in mdstats"
author: "mdstats"
date: "2026-07-14 (TS3 integration revision)"
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
mdstats/analysis/topology_statistics/atomic.py
```

and its public re-export surface through

```python
mdstats.analysis.topology_statistics
mdstats.analysis
mdstats
```

for topology-statistics Stage TS1. The implementation is introduced in
`mdstats 0.17.0a1`; exact TS3 temporal integration is added in `0.17.0a3`. TS4 consumes the completed atomic result unchanged in `0.17.0a4` for exact cross-layer alignment.

TS1 consumes one completed `AtomicConnectivityResult` and derives descriptive
statistics without rebuilding neighbors, modifying connectivity, smoothing state
assignments, or reclassifying graph identity.

The governing boundary is

$$
\boxed{
\text{atomic connectivity defines contacts; TS1 only summarizes them}
}.
$$

The initial implementation provides:

- exact per-frame species-pair contact counts;
- exact discrete contact-count probability mass functions;
- total atomic-edge counts;
- catalog-state occupancy and Shannon diversity;
- gauge-invariant contact occupancy;
- degree statistics by species and atom;
- trajectory-only aggregate additions and removals;
- immutable, schema-versioned result objects;
- deterministic SHA-256 result digests;
- optional exact TS3 state timelines and contact episodes for trajectories.

Exact transition timelines, dwell intervals, return lags, and gauge-invariant
contact episodes are supplied by the TS3 temporal layer. Survival functions,
correlation functions, probabilities, and rates remain deferred.

# Motivation

An `AtomicConnectivityResult` contains complete graph states and frame-to-state
assignments, but it is not itself a compact statistical report. A trajectory may
contain thousands of frames, dozens of recurring contact states, and only a small
number of chemically relevant descriptor changes.

TS1 answers questions such as:

- How many Si-O, Al-O, or Na-O contacts occur in each frame?
- Is a contact count invariant or distributed over several integer values?
- Which atomic contacts are permanent or intermittent?
- Which species show variable graph degree?
- How many unique connectivity states occur, and how populated are they?
- How many contact additions and removals occur across adjacent trajectory frames?
- Are apparent changes caused only by periodic gauge labels rather than contact
  identity?

For the validated 300 K Na-LTA trajectory, TS1 should report:

```text
Si-O contacts: 96 in every frame
Al-O contacts: 96 in every frame
Na-O contacts: distributed from 110 through 121
atomic connectivity states: 72
trajectory state changes: 71 frame boundaries
Na-O additions/removals: 40 / 31
```

These quantities validate the atomic layer before framework, ring, site, or cage
interpretation is applied.

# Responsibility boundaries

## Owned by `atomic.py`

The module owns:

- species-pair contact counts derived from catalog states;
- exact count distributions and scalar summaries;
- total-edge statistics;
- state occupancy and entropy through TS0 primitives;
- degree statistics grouped by atomic species;
- contact occupancy under gauge-invariant atom-pair identity;
- aggregate trajectory additions and removals;
- self-contained source-scope provenance;
- TS1 serialization and result digest validation.

## Not owned by `atomic.py`

The module must not:

- calculate geometric neighbors;
- choose connectivity cutoffs;
- form, break, retain, or smooth connectivity edges;
- project atomic paths into framework edges;
- classify topology classes;
- enumerate primitive rings;
- classify adsorption sites or cage occupancy;
- infer that a Na-O contact event is a site-to-site hop;
- assign physical time when no time axis is supplied;
- treat stored ensemble order as a trajectory;
- estimate independent-sample uncertainties from correlated trajectory frames.

# Module layout and import policy

The implementation resides at

```text
mdstats/analysis/topology_statistics/atomic.py
```

and depends on:

```text
atomic_connectivity.py
semantics.py
topology_statistics/_common.py
```

It does not depend on framework topology, ring analysis, plotting, or file readers.

The primary public entry point is

```python
compute_atomic_connectivity_statistics(...)
```

Users normally import TS1 objects from

```python
from mdstats import compute_atomic_connectivity_statistics
```

The source module may also be imported directly when type-local organization is
useful.

# Public constants

```python
CANONICAL_ATOMIC_TOPOLOGY_STATISTICS_SCHEMA = (
    "mdstats.topology-statistics.atomic.v2"
)
```

TS1 uses the shared digest algorithm

```python
TOPOLOGY_STATISTICS_DIGEST_ALGORITHM = "sha256"
```

and accepts only source connectivity states using

```python
CANONICAL_CONNECTIVITY_SCHEMA = "mdstats.atomic-connectivity.v1"
```

Schema versions are part of scientific provenance. A schema mismatch is rejected
rather than silently interpreted.

# Terminology and mathematical conventions

## Atomic connectivity state

For catalog state $s$, let

$$
G_s=(V,E_s)
$$

be the canonical periodic atomic graph. The active atom population $V$ is fixed by
`ResolvedConnectivityScope`.

For analyzed result position $f$, the catalog assignment is

$$
z_f\in\{0,\ldots,S-1\},
$$

so the frame graph is

$$
G_f=G_{z_f}.
$$

TS1 evaluates graph descriptors once for each unique state $s$ and expands only
compact descriptor arrays through $z_f$.

## Species-pair contact count

For an unordered species pair $A-B$, define

$$
N_{AB}(f)
=
\left|
\left\{
(i,j)\in E_f:
\{Z_i,Z_j\}=\{A,B\}
\right\}
\right|.
$$

The exact empirical probability mass function is

$$
p_{AB}(n)
=
\frac{1}{F}
\sum_{f=1}^{F}
\mathbf 1[N_{AB}(f)=n].
$$

No arbitrary histogram width is introduced.

## Total edge count

The total atomic-edge count in frame $f$ is

$$
N_E(f)=|E_f|.
$$

Its exact distribution is derived in the same way as a species-pair count.

## Degree statistics

For atom $i$ in frame $f$,

$$
d_i(f)=\deg_{G_f}(i).
$$

For species $A$, TS1 reports the atom-frame degree distribution

$$
p_A(k)
=
\frac{1}{F N_A}
\sum_{f=1}^{F}
\sum_{i:Z_i=A}
\mathbf 1[d_i(f)=k].
$$

It also reports the per-frame species mean

$$
\bar d_A(f)
=
\frac{1}{N_A}
\sum_{i:Z_i=A}d_i(f),
$$

and per-atom population mean and standard deviation over frames.

## State occupancy and diversity

For state $s$, the frame occupancy is

$$
p_s
=
\frac{1}{F}
\sum_{f=1}^{F}\mathbf 1[z_f=s].
$$

The Shannon state entropy is

$$
H=-\sum_{s:p_s>0}p_s\ln p_s,
$$

with effective state count

$$
N_{\mathrm{eff}}=e^H.
$$

These are descriptive diversity measures, not thermodynamic entropies.

## Gauge-invariant contact identity

`AtomicEdgeKey` includes a periodic image shift, but periodic graph states may use
different normalized gauges. Under a vertex-image gauge transformation,

$$
\mathbf m_{ij}'
=
\mathbf m_{ij}+\mathbf g_j-\mathbf g_i,
$$

while the physical atom contact $(i,j)$ is unchanged.

The first atomic-connectivity schema forbids parallel edges between one atom pair.
Therefore persistent contact occupancy and cross-state addition/removal statistics
use

$$
C_{ij}=\{i,j\}
$$

as the gauge-invariant contact identity. Image-shift changes alone do not create a
new contact event.

This choice matches `AtomicConnectivityResult.compare_states()` and the source
catalog transition semantics.

## Aggregate trajectory changes

For adjacent trajectory frames,

$$
C_f^+=C_f\setminus C_{f-1},
$$

$$
C_f^-=C_{f-1}\setminus C_f,
$$

where $C_f$ is the set of gauge-invariant atom contacts.

TS1 aggregates:

$$
N_+=\sum_f|C_f^+|,
\qquad
N_-=\sum_f|C_f^-|,
$$

and total churn

$$
\chi=N_++N_-.
$$

The aggregate remains a compact summary; the integrated TS3 result owns the exact event timeline.

# Input contract

## Source type

The public function accepts exactly one

```python
AtomicConnectivityResult
```

from `compute_atomic_connectivity(...)` or a schema-valid deserialization.

The input must contain:

- one nonempty analyzed frame selection;
- one nonempty state tuple;
- dense valid `frame_state_ids`;
- one persistent resolved atom scope;
- states aligned to that scope;
- valid `metadata["frame_semantics"]`;
- source state schema `mdstats.atomic-connectivity.v1`.

## Atom identity constraints

All source states must use the same:

- active atom indices;
- active atomic numbers;
- atom ordering;
- periodic-dimensionality convention.

The implementation validates state alignment against `resolved_scope` before
computing statistics.

## Frame semantics

The input metadata must identify either

```python
FrameSemantics.TRAJECTORY
FrameSemantics.ENSEMBLE
```

For trajectories, frame indices, optional steps, and optional times must be
strictly increasing.

For ensembles, TS0 axis rules reject:

- simulation steps;
- physical times;
- time units;
- temporal visit counts;
- transition aggregates.

## Optional time metadata

The source catalog preserves frame indices and frame IDs but not necessarily
simulation steps or physical times. The caller may supply:

```python
steps: ArrayLike | None
times: ArrayLike | None
time_unit: str | None
```

Constraints:

- arrays must be one-dimensional and match the analyzed frame count;
- trajectory steps and times must be strictly increasing;
- `time_unit` requires `times`;
- ensembles reject all temporal metadata;
- no physical time is guessed.

# Public options

## `AtomicStatisticsOptions`

```python
@dataclass(frozen=True, slots=True)
class AtomicStatisticsOptions:
    species_pairs: tuple[tuple[int, int], ...] | None = None
    include_degree_statistics: bool = True
    include_contact_occupancies: bool = True
    include_transition_statistics: bool = True
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES
```

### `species_pairs`

`None` selects every unordered species pair observed in at least one source state.

An explicit tuple restricts output to those pairs. An explicitly requested pair
may have zero observed contacts, in which case TS1 returns

$$
p_{AB}(0)=1.
$$

Both species must exist in the resolved active scope. Duplicate canonical pairs
are rejected.

For symbol-based construction, use

```python
AtomicStatisticsOptions.from_species_pairs(
    [("Si", "O"), ("Al", "O"), ("Na", "O")]
)
```

### Optional large outputs

`include_degree_statistics=False` omits per-species degree results.

`include_contact_occupancies=False` omits contact-resolved occupancy records.

`include_transition_statistics=False` omits trajectory aggregate edge-change
statistics.

These options bound memory use for very large reactive catalogs.

### TS3 temporal options

```python
include_temporal_statistics: bool = True
include_contact_episodes: bool = True
temporal_options: TemporalStatisticsOptions = TemporalStatisticsOptions()
```

Detailed temporal output is created only for trajectory input. Setting
`include_temporal_statistics=False` suppresses both the state timeline and contact
episodes. Setting `include_contact_episodes=False` retains exact state residence
and transition statistics while omitting the potentially large contact-episode
table.

### Quantiles

Quantiles must be finite, strictly increasing, and span exactly 0 to 1.

The default is inherited from TS0:

```python
DEFAULT_QUANTILES = (0.0, 0.25, 0.5, 0.75, 1.0)
```

# Data structures

## `AtomicContactKey`

```python
@dataclass(frozen=True, order=True, slots=True)
class AtomicContactKey:
    atom_i: int
    atom_j: int
```

This is the persistent, gauge-invariant contact identity used by TS1.

Invariants:

- atom indices are nonnegative integers;
- `atom_i < atom_j` after canonicalization;
- self-contacts are invalid;
- periodic image shift is intentionally absent.

The omission of image shift is not information loss in TS1's first schema because
parallel atomic edges are forbidden by the source connectivity schema.

## `AtomicContactOccupancy`

```python
@dataclass(frozen=True, slots=True)
class AtomicContactOccupancy:
    contact: AtomicContactKey
    frame_count: int
    probability: float
```

For contact $c$,

$$
p_c
=
\frac{1}{F}
\sum_f\mathbf 1[c\in C_f].
$$

Invariants:

- `0 <= frame_count <= F` in the enclosing result;
- `probability = frame_count / F`;
- `0 <= probability <= 1`.

## `AtomicPairContactStatistics`

```python
@dataclass(frozen=True, slots=True)
class AtomicPairContactStatistics:
    species_pair: tuple[int, int]
    state_contact_counts: NDArray[np.int64]
    contact_count_series: ScalarSeries
    contact_count_distribution: DiscreteCountDistribution
    contact_occupancies: tuple[AtomicContactOccupancy, ...] | None
    contact_occupancy_summary: ScalarSummary | None
```

The occupancy records use `AtomicContactKey` and are therefore gauge invariant.

The result contains:

- one count per unique source state;
- the expanded per-frame or per-sample series;
- its exact integer PMF;
- optional contact-resolved occupancies;
- an optional scalar summary over occupancy probabilities.

If the selected species pair has no observed contacts:

- `state_contact_counts` are zero;
- the count PMF is a delta function at zero;
- `contact_occupancies == ()` when occupancy output is enabled;
- `contact_occupancy_summary is None`.

Properties provide chemical symbols and a compact label. The canonical species
pair itself remains an unordered atomic-number identity.

## `AtomicSpeciesDegreeStatistics`

```python
@dataclass(frozen=True, slots=True)
class AtomicSpeciesDegreeStatistics:
    atomic_number: int
    atom_indices: NDArray[np.int64]
    degree_distribution: DiscreteCountDistribution
    mean_degree_series: ScalarSeries
    per_atom_mean_degree: NDArray[np.float64]
    per_atom_population_standard_deviation: NDArray[np.float64]
```

The degree distribution samples every atom of the selected species in every
analyzed frame, while avoiding explicit frame-by-atom expansion internally.

The result includes all active atoms of one species exactly once and is sorted by
atomic number in the enclosing result.

## `AtomicPairTransitionCount`

```python
@dataclass(frozen=True, slots=True)
class AtomicPairTransitionCount:
    species_pair: tuple[int, int]
    additions: int
    removals: int
```

Derived properties are

```python
churn = additions + removals
net_change = additions - removals
```

Counts are aggregate trajectory quantities. They do not identify exact event
frames; the integrated TS3 result provides that timeline.

## `AtomicTransitionAggregateStatistics`

```python
@dataclass(frozen=True, slots=True)
class AtomicTransitionAggregateStatistics:
    n_frame_boundaries: int
    n_changed_boundaries: int
    total_added_edges: int
    total_removed_edges: int
    pair_counts: tuple[AtomicPairTransitionCount, ...]
    affected_atom_indices: NDArray[np.int64]
    affected_atom_event_counts: NDArray[np.int64]
```

`affected_atom_event_counts` counts changed frame boundaries involving each atom,
not the number of individual incident edge operations.

The object exists only for trajectories when transition statistics are enabled.
For an ensemble it is always `None`.

## `AtomicTemporalStatistics`

```python
@dataclass(frozen=True, slots=True)
class AtomicTemporalStatistics:
    state_statistics: StateTransitionStatistics
    contact_keys: tuple[AtomicContactKey, ...]
    contact_episodes: EntityPresenceStatistics | None
```

`contact_keys[e]` gives the gauge-invariant atomic contact represented by dense
entity ID `e` in `contact_episodes`. Contact episodes use atom-pair identity and
must not split when a state-local periodic image shift changes.

The convenience method

```python
contact_episode_statistics(contact: AtomicContactKey)
```

returns all episodes for one observed contact.

## `AtomicConnectivityStatistics`

```python
@dataclass(frozen=True, slots=True)
class AtomicConnectivityStatistics:
    axis: FrameAxis
    catalog_occupancy: CatalogOccupancyStatistics
    active_atom_indices: NDArray[np.int64]
    active_atomic_numbers: NDArray[np.int64]
    total_edge_series: ScalarSeries
    total_edge_distribution: DiscreteCountDistribution
    pair_statistics: tuple[AtomicPairContactStatistics, ...]
    degree_statistics: tuple[AtomicSpeciesDegreeStatistics, ...] | None
    transition_statistics: AtomicTransitionAggregateStatistics | None
    temporal_statistics: AtomicTemporalStatistics | None
    options: AtomicStatisticsOptions
    source_definition_kind: str
    source_connectivity_schema: str
    source_state_digests: tuple[str, ...]
    metadata: Mapping[str, Any]
    canonical_schema_version: str
    digest_algorithm: str
    digest: str
```

This is the primary TS1 result.

### Convenience properties and queries

```python
result.n_frames
result.n_states
result.pair("Na", "O")
result.species_degree("Na")
result.to_dict()
AtomicConnectivityStatistics.from_dict(payload)
```

`pair(...)` accepts chemical symbols or atomic numbers and treats the pair as
unordered.

`species_degree(...)` raises `KeyError` when degree statistics were disabled or
the species is absent.

### Immutability

All arrays are defensive, read-only copies. Metadata is JSON-normalized and
wrapped in a read-only mapping. Nested result tuples are immutable.

# Public function

## `compute_atomic_connectivity_statistics`

```python
def compute_atomic_connectivity_statistics(
    catalog: AtomicConnectivityResult,
    *,
    steps: ArrayLike | None = None,
    times: ArrayLike | None = None,
    time_unit: str | None = None,
    options: AtomicStatisticsOptions | None = None,
) -> AtomicConnectivityStatistics:
    ...
```

### Input constraints

- `catalog` must be an `AtomicConnectivityResult`;
- all states must align with the resolved atom scope;
- source state schemas must be supported;
- metadata must contain valid frame semantics;
- optional steps and times must align with analyzed result positions;
- explicit requested species must exist in the active scope;
- options must be an `AtomicStatisticsOptions` instance.

### Output

The result is one immutable `AtomicConnectivityStatistics` object containing
collection-wide distributions, frame-aligned series, optional large outputs, and
source provenance.

# Algorithm

## High-level pseudocode

```text
validate catalog, semantics, options, and state alignment
build immutable FrameAxis
compute state occupancy and Shannon diversity from frame_state_ids

for each unique state:
    count total edges
    count edges by species pair
    read degree array

expand state-level scalar counts through frame_state_ids
build exact PMFs and scalar series

if contact occupancy enabled:
    for each source state:
        weight each gauge-invariant atom pair by state frame count

if degree statistics enabled:
    accumulate weighted integer degree frequencies by species
    compute per-frame species mean degree
    compute per-atom weighted mean and population deviation

if trajectory aggregate changes enabled:
    compare gauge-invariant contact sets across adjacent assignments
    aggregate additions, removals, species pairs, and affected atoms

assemble immutable result
compute deterministic payload digest
```

## Catalog-compressed evaluation

Let:

- $F$ be the analyzed frame count;
- $S$ be the number of unique connectivity states;
- $E_s$ be the edge count of state $s$;
- $N$ be the active atom count;
- $P$ be the selected species-pair count.

State descriptor construction scales approximately as

$$
O\!\left(\sum_{s=1}^{S}|E_s|+SN\right).
$$

Scalar frame expansion scales as

$$
O(FP).
$$

Trajectory aggregate transitions scale as

$$
O\!\left(\sum_{f=2}^{F}
|C_{z_f}\triangle C_{z_{f-1}}|
\right)
$$

when set differences are used.

The implementation does not rebuild $F$ graph objects and does not expand the full
$F\times N$ degree matrix. Weighted state frequencies are used for degree PMFs and
per-atom moments.

## Weighted exact degree distribution

For species $A$, state $s$ has frame weight $w_s$. If $n_{s,A}(k)$ is the number
of atoms of species $A$ with degree $k$ in state $s$, then

$$
F_A(k)
=
\sum_s w_s n_{s,A}(k).
$$

The exact PMF is

$$
p_A(k)
=
\frac{F_A(k)}{F N_A}.
$$

Quantiles are computed as if the weighted integer sample were expanded, without
materializing that expansion.

# Trajectory and ensemble semantics

## Trajectory

A trajectory permits:

- state visit counts;
- optional simulation steps;
- optional physical times;
- adjacent-frame aggregate additions and removals;
- affected-atom boundary counts.

TS1 does not yet provide:

- exact transition timestamps;
- dwell intervals;
- return times;
- contact episode lifetimes;
- rates.

These are implemented by TS3 except survival and correlation analysis, which remain deferred.

## Ensemble

An ensemble permits:

- contact-count PMFs;
- total-edge PMFs;
- state occupancy probabilities;
- entropy and effective state count;
- degree distributions;
- contact occupancies across samples.

An ensemble does not permit:

- visit counts;
- steps or physical times;
- aggregate adjacent-sample transitions;
- event, dwell, or lifetime interpretation.

The stored sample order is not treated as time.

# Contact language and scientific interpretation

The module uses the neutral term **contact** for atomic edges because connectivity
models may represent:

- radial coordination contacts;
- hysteretic contacts;
- reference-retained contacts;
- explicit bonds;
- externally supplied graph relations.

A Na-O contact addition or removal does not automatically prove a cation site hop.
A site hop requires later ring-site, cage, or other spatial assignment.

The result retains `source_definition_kind` and source catalog metadata so reports
can state how contacts were defined.

# Serialization contract

The top-level payload uses

```text
schema_version: mdstats.topology-statistics.atomic.v2
object_type: AtomicConnectivityStatistics
digest_algorithm: sha256
```

Nested TS0 objects retain their own common schema wrappers. TS1-specific nested
objects are serialized as explicit dictionaries inside the top-level TS1 payload.

The top-level digest is calculated from canonical compact JSON excluding the
stored digest field itself.

Deserialization validates:

- schema version;
- object type;
- source schema;
- array and tuple invariants;
- state and frame alignment;
- pair-series expansion;
- occupancy probabilities;
- degree-species partitions;
- metadata finiteness;
- the stored SHA-256 digest.

A modified payload with an unchanged digest is rejected.

# Provenance

The result preserves:

- source connectivity definition kind;
- source connectivity schema;
- one source digest per unique state;
- active atom indices and atomic numbers;
- frame semantics;
- source catalog consistency category;
- caller-selected options;
- source catalog metadata;
- TS1 schema and digest algorithm.

The statistics digest identifies the complete statistical payload, not the source
catalog alone.

# Edge cases and warnings

## No observed edges for a requested pair

An explicit pair with no observed contacts is valid. TS1 reports a zero count in
every frame and no contact occupancy records.

## No edges anywhere

An explicit empty graph is valid when the source catalog permits it. Total edge
and pair distributions may be delta functions at zero. Degree distributions are
then delta functions at zero.

## Uniform catalogs

A uniform catalog has:

$$
H=0,
\qquad
N_{\mathrm{eff}}=1.
$$

Every state-level descriptor expands to a constant frame series.

## Per-frame source mode

`ConnectivityConsistency.PER_FRAME` is accepted. TS1 still computes occupancies
and state descriptors, but each source state may be observed exactly once.

## Periodic gauge changes

A change in `AtomicEdgeKey.image_shift` for the same atom pair is not counted as a
contact formation or removal. TS1 uses `AtomicContactKey` for cross-state identity.

## Large contact unions

Contact-resolved occupancy may be memory intensive for strongly reactive systems.
Use

```python
AtomicStatisticsOptions(include_contact_occupancies=False)
```

when only aggregate pair counts are needed.

## Large active populations

Degree PMFs are accumulated from weighted state histograms rather than full
frame-by-atom expansion. Per-atom mean and deviation arrays still scale as $O(N)$.

## Correlated trajectory frames

Population means and standard deviations describe the observed trajectory frames.
They are not standard errors and do not imply independent sampling.

## Canonical species-pair order

The authoritative pair identity is an unordered canonical pair of atomic numbers.
Human-facing plotting may choose a conventional label order, but serialization and
queries must not depend on display formatting.

# Usage examples

## Basic atomic statistics

```python
from mdstats import compute_atomic_connectivity_statistics

stats = compute_atomic_connectivity_statistics(atomic_result)

print(stats.n_states)
print(stats.catalog_occupancy.effective_state_count)
print(stats.pair("Na", "O").contact_count_distribution.summary.mean)
```

## Physical time supplied by the caller

```python
stats = compute_atomic_connectivity_statistics(
    atomic_result,
    times=np.arange(atomic_result.frame_indices.size) * 0.001,
    time_unit="ps",
)
```

## Restrict species pairs and omit large outputs

```python
options = AtomicStatisticsOptions.from_species_pairs(
    [("Si", "O"), ("Al", "O"), ("Na", "O")],
    include_contact_occupancies=False,
    include_degree_statistics=False,
)

stats = compute_atomic_connectivity_statistics(
    atomic_result,
    options=options,
)
```

## Exact Na-LTA contact distribution

For the validated 2,000-frame 300 K trajectory, TS1 produces:

| Pair | Support | Mean | Population SD |
|---|---:|---:|---:|
| Si-O | 96 | 96.0000 | 0.0000 |
| Al-O | 96 | 96.0000 | 0.0000 |
| Na-O | 110--121 | 115.8735 | 2.8563 |

The exact Na-O frequencies are:

| Contact count | Frame frequency |
|---:|---:|
| 110 | 51 |
| 111 | 69 |
| 112 | 218 |
| 113 | 204 |
| 114 | 83 |
| 115 | 179 |
| 116 | 220 |
| 117 | 431 |
| 118 | 169 |
| 119 | 122 |
| 120 | 178 |
| 121 | 76 |

The source contains 72 unique connectivity states. TS1 reports 71 changed
trajectory boundaries with 40 gauge-invariant contact additions and 31 removals,
all belonging to the Na-O species pair.

# Testing requirements

The TS1 focused test suite must cover at least:

1. constant species-pair contact counts;
2. variable exact contact-count PMFs;
3. total-edge PMFs;
4. explicit zero-contact pair requests;
5. contact occupancy probabilities;
6. species degree distributions;
7. per-atom degree means and population deviations;
8. state occupancy and recurrence;
9. Shannon entropy and effective state count;
10. trajectory aggregate additions and removals;
11. simultaneous additions and removals;
12. affected-atom boundary counts;
13. ensemble rejection of temporal interpretation;
14. optional output suppression;
15. custom quantiles;
16. unknown species rejection;
17. immutable arrays;
18. serialization round-trip;
19. digest tampering rejection;
20. periodic-gauge-invariant contact identity;
21. real Na-LTA integration values.

The complete package regression suite must remain unchanged except for the added
TS1 tests.

# TS3 temporal integration

The following are intentionally deferred:

- exact transition event tables;
- transition raster data;
- state dwell intervals;
- state return times;
- contact formation episodes;
- contact lifetime distributions;
- survival functions;
- transition matrices normalized by time;
- autocorrelation and integrated correlation time;
- Markov-state modeling.

Deferral prevents TS1 from mixing static catalog summaries with more demanding
time-domain semantics.

# Accepted TS1 decisions

1. `AtomicConnectivityResult` is the authoritative input.
2. TS1 never rebuilds atomic connectivity.
3. Graph descriptors are evaluated once per unique state.
4. Integer contact counts use exact PMFs.
5. Species-pair identities are unordered and atomic-number canonical.
6. Cross-state contact identity uses atom pairs, not periodic image shifts.
7. Image-shift-only changes do not count as contact events.
8. Contact occupancy is optional because its union may be large.
9. Degree statistics include atom-frame PMFs and per-atom moments.
10. State entropy is descriptive and not thermodynamic.
11. Aggregate edge changes are trajectory-only.
12. Exact event timelines are provided by TS3.
13. Ensemble storage order has no temporal meaning.
14. Physical time is caller supplied and never guessed.
15. Atomic edges are described as contacts unless stronger provenance exists.
16. Contact changes are not automatically site hops.
17. Result arrays and metadata are immutable.
18. Serialization is schema checked and SHA-256 validated.
19. Source state digests and active scope remain visible.
20. Plotting and table export remain outside TS1.

# Final TS1 contract

TS1 converts a completed atomic-connectivity catalog into immutable descriptive
statistics while preserving all scientific boundaries:

```text
AtomicConnectivityResult
        |
        v
validate scope, state schema, and frame semantics
        |
        v
state-compressed pair, edge, and degree descriptors
        |
        +--> exact count distributions
        +--> frame/sample scalar series
        +--> contact occupancies
        +--> catalog diversity
        `--> trajectory aggregate changes
        |
        v
AtomicConnectivityStatistics
```

The module answers what the atomic graph did statistically. It does not decide why
contacts exist, whether the framework changed, or whether an ion hopped between
physical sites.
