---
title: "Topology Statistics Architecture Manual"
subtitle: "High-Level Design Guide for Catalog-Derived Atomic and Framework Graph Statistics in mdstats"
author: "mdstats"
date: "2026-07-30 (revision 5, MLFF caller boundary; TS5 unchanged)"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.85in
fontsize: 10pt
header-includes:
  - |
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \definecolor{codegray}{RGB}{247,247,247}
    \setlist{nosep}
---

# Purpose and status

This manual records the accepted architecture for topology-derived statistical
analysis in `mdstats`. Stages TS0 through TS5 are implemented through
`mdstats 0.17.0a5`: the shared common foundation, atomic-connectivity statistics,
framework-topology statistics, exact trajectory-only temporal statistics,
validated atomic/framework cross-layer alignment, and standard plotting and
machine-readable export.

The statistics layer consumes completed atomic-connectivity and framework-topology
catalogs and converts them into reproducible distributions, per-frame descriptor
series, transition timelines, and cross-layer summaries. It does not construct
neighbors, classify bonds, project framework edges, reconcile topology classes,
or enumerate rings.

This is a **high-level architecture manual**, not a module specification. Its
purpose is to preserve:

1. scientific responsibilities and module boundaries;
2. authoritative inputs and derived outputs;
3. trajectory and ensemble semantics;
4. shared statistical definitions;
5. staged implementation order;
6. accepted design decisions and deferred features.

Detailed dataclass fields, function signatures, validation rules, serialization
schemas, and plotting APIs will be defined in module specifications before each
stage is implemented.

The topology-statistics branch was introduced as an optional Stage 3.5 after atomic
connectivity, framework projection, and topology cataloging are stable. It is not
a prerequisite for primitive-ring enumeration, but it provides a strong validation
and reporting layer before later ring, site, and cage analysis.


# Theoretical background

## A catalog-valued description of structural evolution

The connectivity and topology layers reduce each frame to an exact discrete
state. For frame $f$, let

$$
A_f\in\mathcal A
$$

be an atomic-connectivity state and

$$
T_f\in\mathcal T
$$

be a projected framework-topology class. The finite catalogs $\mathcal A$ and
$\mathcal T$ are defined upstream by canonical graph identity. The statistics
layer observes these labels and graph records; it does not redefine them.

A trajectory is therefore a time-ordered catalog-valued process

$$
(A_0,T_0),(A_1,T_1),\ldots,(A_{F-1},T_{F-1}),
$$

whereas an ensemble is an unordered sample from one or more structural
populations. The same state counts are meaningful in both cases, but temporal
transitions and residence times are meaningful only for the trajectory.

## Empirical measures and graph observables

For a catalog state $s$ with frame count $n_s$, the empirical occupancy is

$$
\hat p_s=\frac{n_s}{F},
\qquad
\sum_s\hat p_s=1.
$$

Any state-level observable $g(s)$ has the empirical frame average

$$
\langle g\rangle_F
=
\sum_s \hat p_s g(s).
$$

This identity is the theoretical basis for catalog compression. If repeated
frames share exactly the same canonical state, expensive graph descriptors need
to be evaluated once per state and then weighted by occupancy. Compression is
mathematically exact for state-determined observables; it is not an approximation
or a clustering step.

Graph observables may be scalar, categorical, or set-valued. Examples include
vertex count, edge count, degree distribution, connected-component count,
cycle-space rank, endpoint chemistry, and the presence of a canonical contact.
The statistics layer must preserve the domain of each observable: an atomic edge
and a projected framework edge are elements of different sample spaces even when
they arise from the same frame.

## State diversity and Shannon entropy

The diversity of catalog occupancy may be summarized by

$$
H_{\mathrm{state}}
=
-\sum_{s:\hat p_s>0}\hat p_s\log \hat p_s,
$$

following Shannon's information measure [1]. This number describes how broadly
the observed frames are distributed over exact states. It is zero for a single
occupied state and is maximal for equal occupancy over a fixed number of states.

It is **not thermodynamic entropy**. It depends on the chosen state definition,
sampling interval, finite trajectory, and catalog resolution. Changing a
connectivity threshold can change $H_{\mathrm{state}}$ even when the underlying
physical trajectory is unchanged.

## Ordered dynamics: transitions and residence intervals

For a trajectory, adjacent stored labels define transition counts

$$
N_{ab}
=
\sum_{f=0}^{F-2}
\mathbf 1[S_f=a,\,S_{f+1}=b].
$$

A row-normalized matrix

$$
\hat P_{ab}
=
\frac{N_{ab}}{\sum_c N_{ac}}
$$

is a descriptive conditional frequency at the chosen sampling interval. It does
not by itself establish that the state sequence is Markovian, stationary, or
sampled finely enough to resolve physical events. A transition can also represent
rapid recrossing, threshold noise, or several unresolved microscopic events.

Residence intervals are maximal contiguous runs of one state. Their durations
must distinguish complete intervals from left- or right-censored intervals at
the trajectory boundaries. The architecture therefore stores exact runs and
transition frames before attempting kinetic models.

## Correlation, persistence, and nonindependent samples

For a scalar frame observable $x_f$, the lag-$k$ empirical autocovariance is

$$
\hat C_x(k)
=
\frac{1}{F-k}
\sum_{f=0}^{F-k-1}
(x_f-\bar x)(x_{f+k}-\bar x).
$$

The correlation/spectral viewpoint follows the general harmonic-analysis lineage
of Wiener and Khintchine [2, 3]. In topology statistics, its main use is to
quantify persistence and decorrelation of catalog-derived observables, not to
construct a vibrational spectrum.

Successive trajectory frames are usually correlated. Consequently, frame counts
are not independent Bernoulli trials, ordinary sample standard errors can be
misleading, and a large number of stored frames does not imply the same number of
independent structural observations. The first-generation statistics therefore
reports descriptive occupancy and exact event structure without silently
claiming independent-sample uncertainty.

## Cross-layer statistics as a deterministic projection

Atomic connectivity contains more detail than projected framework topology. The
catalog mapping can be viewed as a deterministic projection

$$
\pi:\mathcal A\rightarrow\mathcal T,
\qquad T_f=\pi(A_f),
$$

when each atomic state resolves to one framework class under fixed mapping rules.
Many atomic states may share the same projected topology. This explains how
mobile-ion contacts or local bond fluctuations can change repeatedly while the
framework class remains constant.

Cross-layer statistics should therefore ask questions such as

$$
P(T=t\mid A=a),
$$

or classify an atomic transition $a\rightarrow b$ by whether

$$
\pi(a)=\pi(b).
$$

They must not merge the catalogs or compare their state IDs directly.

## What the statistics can and cannot establish

The architecture provides exact descriptive statements about the chosen graph
models:

- which canonical states were observed;
- how frequently they occurred;
- which graph features each state contains;
- when ordered transitions occurred;
- how atomic changes project onto framework changes.

It does not, without additional modeling, establish equilibrium probabilities,
free energies, continuous-time rates, Markovian kinetics, causal mechanisms, or
chemical reaction coordinates. Those are later inferential layers built on top
of the exact catalog and event record.

# Motivation

Atomic and framework catalogs contain complete discrete graph information, but raw
catalog objects are not convenient scientific summaries.

A typical trajectory may contain:

- thousands of frames;
- dozens or hundreds of atomic-connectivity states;
- one or a few projected framework topologies;
- many spectator-contact changes;
- few or no framework-breaking events.

The statistics layer should answer, without repeating graph construction:

- How many contacts of each species pair occur in each frame?
- What is the exact count distribution over the analyzed collection?
- Which edges are permanent, intermittent, newly formed, or removed?
- How many unique atomic states and framework classes occur?
- When do trajectory transitions occur?
- How long does each state or edge persist?
- Which atomic changes alter the projected framework?
- Which graph descriptors are constant, fluctuating, or discontinuous?

For the validated 300 K Na-LTA trajectory, the intended interpretation is:

```text
Na-inclusive atomic connectivity: many discrete states and Na-O contact changes
projected LTA framework topology: one uniform topology and no framework transition
```

This distinction should become a standard, reproducible output rather than a
one-off analysis script.

# Design goals

The topology-statistics architecture should:

- consume `AtomicConnectivityResult` and `TopologyCatalog` as authoritative inputs;
- derive statistics without rebuilding graph states or redefining identity;
- keep atomic-connectivity and framework-topology statistics separate;
- share generic distribution and occupancy machinery where the mathematics is
  identical;
- respect `FrameSemantics.TRAJECTORY` and `FrameSemantics.ENSEMBLE` explicitly;
- provide exact discrete count distributions for integer graph descriptors;
- provide per-frame or per-sample descriptor arrays aligned with catalog frames;
- expose exact trajectory event boundaries and state residence intervals;
- preserve Stage 2 orientation-aware bridge signatures;
- exploit catalog compression by evaluating each unique graph state once;
- keep plotting and file export outside scientific graph interpretation;
- retain schema-versioned provenance and deterministic serialization;
- remain useful before primitive-ring analysis is available;
- support later ring, site, cage, and transport statistics without changing the
  lower catalog contracts.

The central dependency chain is

```text
atomic coordinates and species
            |
            v
atomic connectivity classification
            |
            v
AtomicConnectivityResult
            |\
            | \
            |  +------------------------------+
            |                                 |
            v                                 v
framework projection and reconciliation   atomic statistics
            |                                 |
            v                                 |
TopologyCatalog                              |
            |                                 |
            v                                 |
framework statistics                         |
            |                                 |
            +---------------+-----------------+
                            |
                            v
                  combined cross-layer statistics
                            |
                            v
                   plotting and table export
```

# Governing principles

## Catalog construction is authoritative

The statistics layer must not decide what constitutes an atomic edge or a
framework edge.

Atomic edge identity is defined by the atomic-connectivity layer. Framework edge
identity is defined by canonical Stage 2 `FrameworkEdgeKey` records. Topology-class
identity is defined by `TopologyCatalog`.

The governing rule is

$$
\boxed{
\text{catalog construction defines graph identity; statistics only summarizes it}
}
$$

A statistics function may count, group, expand, correlate, or compare catalog
records. It must not:

- rerun radial neighbor searches;
- apply new connectivity cutoffs;
- smooth graph states silently;
- merge approximately similar states;
- reinterpret spectator contacts as framework edges;
- derive a new topology-class identity.

## Atomic and framework graphs remain distinct

An atomic-connectivity state and a projected framework topology describe different
graphs.

For frame $f$, let

$$
G_f^{\mathrm{A}}=(V^{\mathrm{A}},E_f^{\mathrm{A}})
$$

be the atomic connectivity graph, and

$$
G_f^{\mathrm{F}}=(V^{\mathrm{F}},E_f^{\mathrm{F}})
$$

be the projected framework graph.

Atomic edges may include mobile-ion contacts, terminal species, spectators, or
other interactions that do not survive framework projection. Therefore,

$$
G_f^{\mathrm{A}}\ne G_f^{\mathrm{F}}
$$

and a change in $E_f^{\mathrm{A}}$ does not imply a change in
$E_f^{\mathrm{F}}$.

The result types and state identifiers for the two graph layers must never be
merged into one namespace.

## Static distributions and temporal statistics are different

A frame collection may be a time-ordered trajectory or an unordered ensemble.
Both permit collection-wide distributions, but only trajectories permit temporal
interpretation.

Static or sample statistics include:

- count distributions;
- degree distributions;
- state or class occupancies;
- edge occupancies;
- component-count distributions;
- graph cycle-rank distributions.

Trajectory-only statistics include:

- transition timelines;
- dwell times;
- return times;
- edge formation and breaking episodes;
- autocorrelation and survival functions;
- rates normalized by physical time.

Stored ensemble order must never be treated as a physical sequence.

## Exact integer distributions come before arbitrary histograms

Most primary graph descriptors are integers. For an integer-valued descriptor
$x_f$, the authoritative discrete distribution is

$$
p(n)
=
\frac{1}{F}
\sum_{f=1}^{F}
\mathbf 1[x_f=n].
$$

The result should store exact support values, frequencies, and probabilities.
Plotting may render these as bars, but the analysis layer should not introduce an
arbitrary bin width when exact counts are available.

For example, if every frame contains 96 Si-O edges,

$$
p_{\mathrm{SiO}}(96)=1.
$$

## Statistical summaries do not imply independent sampling

For a trajectory, adjacent frames are usually correlated. Means and empirical
standard deviations remain valid descriptive summaries, but they are not
independent-sample uncertainty estimates.

The initial statistics layer should report descriptive quantities without
silently attaching standard errors or confidence intervals. Correlation-corrected
uncertainty is deferred to a later stage.

## Plotting is presentation, not analysis

Plotting functions should consume immutable statistics results. They must not read
raw catalog edges or recompute scientific descriptors.

This separation ensures that:

- tabular export and plotting use the same values;
- plots remain reproducible;
- scientific definitions can be tested without a graphics backend;
- display changes cannot alter analysis results.

# Proposed package architecture

The analysis implementation should use one coherent subpackage rather than one
monolithic module or many single-purpose files.

```text
mdstats/
|-- analysis/
|   `-- topology_statistics/
|       |-- __init__.py
|       |-- _common.py
|       |-- atomic.py
|       |-- framework.py
|       |-- temporal.py
|       `-- combined.py
`-- plotting/
    `-- topology_statistics.py
```

The matching specification hierarchy should mirror the Python package:

```text
docs/specs/analysis/topology_statistics/
|-- _common_spec.{md,pdf}
|-- atomic_spec.{md,pdf}
|-- framework_spec.{md,pdf}
|-- temporal_spec.{md,pdf}
`-- combined_spec.{md,pdf}

docs/specs/plotting/
`-- topology_statistics_spec.{md,pdf}
```

The architecture manual belongs at

```text
docs/arch_manuals/topology_statistics_architecture.{md,pdf}
```

Public users should normally import from

```python
from mdstats.analysis.topology_statistics import ...
```

rather than depending on internal file layout.

# Common statistical foundation

## Responsibility

`_common.py` owns graph-independent statistical structures and low-level
operations that have the same meaning for atomic and framework catalogs.

It should contain concepts equivalent to:

```text
DiscreteCountDistribution
ScalarSummary
CatalogOccupancyStatistics
StateFrameGroup
TimeAxis
ScalarSeries
```

It should also provide deterministic helpers for:

- exact discrete distributions;
- means, population standard deviations, medians, quantiles, and modes;
- catalog-state occupancies;
- Shannon state entropy;
- expansion of state-level descriptors to frame-level arrays;
- frame and time-axis validation;
- immutable array construction;
- schema-versioned serialization primitives.

It must not know the chemical or graph meaning of one edge.

## Descriptive scalar statistics

For scalar values $x_f$, define

$$
\mu
=
\frac{1}{F}
\sum_{f=1}^{F}x_f,
$$

and the population standard deviation

$$
\sigma
=
\sqrt{
\frac{1}{F}
\sum_{f=1}^{F}(x_f-\mu)^2
}.
$$

The default is population rather than sample standard deviation because the result
summarizes the analyzed collection itself. A later inference layer may add
sample-based estimators when scientifically justified.

## Catalog occupancy

For state or topology-class ID $s$, let $n_s$ be its frame count. The occupancy is

$$
p_s=\frac{n_s}{F}.
$$

The common result should report:

- unique state count;
- frame counts and probabilities;
- first and last occurrence;
- dominant state;
- states observed only once;
- number of disjoint visits for trajectories;
- deterministic state ordering inherited from the catalog.

## State diversity

The Shannon state entropy is

$$
H=-\sum_s p_s\ln p_s.
$$

The effective number of populated states is

$$
N_{\mathrm{eff}}=\exp(H).
$$

This quantity describes catalog-state diversity. It must be labeled
**Shannon state entropy**, not thermodynamic entropy.

For one uniform topology,

$$
H=0,
\qquad
N_{\mathrm{eff}}=1.
$$

# Atomic-connectivity statistics

## Responsibility

`atomic.py` consumes an `AtomicConnectivityResult` and produces statistics whose
meaning depends on canonical atomic contact states.

It owns:

- species-pair edge counts;
- total atomic-edge counts;
- atomic-state occupancy statistics;
- per-species and per-atom degree statistics;
- gauge-invariant atomic-contact occupancy probabilities;
- formation and removal counts by species pair;
- edge churn;
- participating-atom summaries;
- optional contact-episode statistics delegated to the `temporal.py`.

It must not perform framework projection or ring interpretation.

## Species-pair contact counts

For an unordered atomic species pair $A-B$, define

$$
N_{AB}(f)
=
\left|
\left\{
e\in E_f^{\mathrm{A}}:
\operatorname{species}(e)=\{A,B\}
\right\}
\right|.
$$

Species pairs should be stored in a deterministic canonical order. The
orientation of an ordinary undirected atomic edge does not create a separate pair
class.

The result should expose:

- state-level pair counts;
- frame-level pair-count series;
- exact count distributions;
- mean, standard deviation, median, range, quantiles, and mode;
- constant-series diagnostics.

## Atomic degree statistics

For atom $i$ in frame $f$,

$$
d_i(f)=\deg_{G_f^{\mathrm{A}}}(i).
$$

Useful summaries include:

- degree distributions by species;
- mean degree by species per frame;
- per-atom mean and population standard deviation;
- atoms with the largest degree variance;
- minimum and maximum observed degree;
- fraction of atoms retaining one degree across all frames.

Pair counts alone can hide whether fluctuations are distributed across many atoms
or concentrated on a small mobile subset.

## Atomic-contact occupancy

For a gauge-invariant atom-pair contact $c=\{i,j\}$,

$$
p_c
=
\frac{1}{F}
\sum_{f=1}^{F}
\mathbf 1[c\in C_f].
$$

The source atomic edge includes a periodic image shift, but that shift is gauge
dependent across graph states. Because the first connectivity schema forbids
parallel atom-pair edges, TS1 uses the unordered atom pair as persistent contact
identity. Image-shift-only changes do not split occupancy records.

Contact occupancy distinguishes:

- permanent contacts with $p_c=1$;
- intermittent contacts with $0<p_c<1$;
- rare contacts with small occupancy.

Occupancy distributions are groupable by species pair.

## Atomic contact changes

For a trajectory boundary $f-1\rightarrow f$, define gauge-invariant contact sets
$C_f$ and

$$
C_f^{+}=C_f\setminus C_{f-1},
\qquad
C_f^{-}=C_{f-1}\setminus C_f.
$$

TS1 reports aggregate additions, removals, churn, affected atoms, and species-pair
totals. Exact event frames, dwell intervals, and contact episodes are provided by TS3. The statistics layer must not describe every contact change as a
chemical reaction or site-to-site hop.

# Framework-topology statistics

## Responsibility

`framework.py` consumes a `TopologyCatalog` and derives statistics from projected
framework vertices and canonical `FrameworkEdgeKey` records.

It owns:

- topology-class occupancies;
- framework vertex, edge, and component counts;
- degree distributions;
- endpoint-species counts;
- complete bridge-signature counts;
- projected-edge occupancies;
- self-image and parallel-edge statistics;
- graph cycle rank;
- transition effects on vertices and linker atoms;
- optional temporal summaries delegated to the implemented `temporal.py`.

It must not reconstruct atomic connectivity or enumerate primitive rings.

## Basic graph descriptors

For one projected framework topology, report:

- vertex count $V$;
- projected edge count $E$;
- connected-component count $C$;
- isolated-vertex count;
- self-image edge count;
- parallel-edge multiplicity;
- degree distribution.

The graph cycle-space rank is

$$
\beta_1=E-V+C.
$$

This is a graph invariant and a useful defect indicator. It must not be labeled the
number of primitive rings.

## Endpoint-species statistics

Projected edges may be grouped by unordered endpoint species, for example:

```text
Si-Si
Si-Al
Al-Al
```

These counts summarize the retained framework graph but do not identify the
internal linker sequence.

## Orientation-aware bridge signatures

Stage 2 preserves a complete ordered path modulo reversal of the entire path.
Bridge statistics must retain this rule.

For example,

$$
A-\mathrm O-\mathrm S-B
\equiv
B-\mathrm S-\mathrm O-A,
$$

but

$$
A-\mathrm O-\mathrm S-B
\ne
A-\mathrm S-\mathrm O-B.
$$

A framework bridge-signature statistic must therefore use the canonical
whole-path rule identity or equivalent canonical edge decoration. It must not group
edges only by unordered endpoints or independently sort linker species.

## Framework-contact occupancy

For canonical projected edge $e$,

$$
p_e^{\mathrm F}
=
\frac{1}{F}
\sum_{f=1}^{F}
\mathbf 1[e\in E_f^{\mathrm F}].
$$

This identifies persistent framework edges, intermittently missing edges, and new
projected bridges across topology classes.

For a uniform framework catalog, every canonical projected edge should have
occupancy one.

# Temporal statistics

## Responsibility

`temporal.py` owns calculations that require physical frame order. It is shared by
atomic and framework statistics but must reject unordered ensembles.

It should provide reusable operations for:

- exact transition timelines;
- contiguous state residence intervals;
- dwell-frame and dwell-time distributions;
- recurrence and return times;
- state transition matrices;
- edge-presence episodes;
- contact lifetimes;
- cumulative event counts;
- later autocorrelation and survival functions.

## Time-axis contract

A temporal result may use:

1. explicit physical times $t_f$;
2. a fixed frame spacing $\Delta t$;
3. frame indices only.

If physical time is unavailable, the result must not invent one.

A supplied time axis must:

- match the catalog frame count;
- be finite;
- be strictly increasing for trajectories;
- preserve the analyzed frame ordering.

## State residence intervals

For a trajectory state sequence $s_f$, a residence interval is a maximal
contiguous range

$$
[a,b]
$$

such that

$$
s_f=s_a
\quad\text{for all}\quad
f\in[a,b].
$$

The frame length is

$$
L=b-a+1.
$$

If frame times represent sampled instants, physical residence duration requires a
clear convention. The implementation specification must define whether it reports
sample-span duration $t_b-t_a$ or interval duration using frame boundaries. The
choice must be explicit and consistent.

## Transition matrix

For trajectory state IDs, the transition-count matrix is

$$
M_{ij}
=
\sum_{f=1}^{F-1}
\mathbf 1[s_f=i\land s_{f+1}=j].
$$

Self-transitions may be reported separately or excluded from event counts, but the
choice must be explicit.

Transition probabilities or rates are deferred unless adequate sampling and a
valid time basis are available.

## Edge episodes

An edge-presence episode is a maximal contiguous interval during which one
canonical edge remains present. Episode statistics can report:

- formation frame;
- removal frame;
- episode length;
- number of episodes per edge;
- edge survival distributions.

A contact episode is not automatically a reaction lifetime, adsorption residence,
or site residence.

## Lag-domain statistics

Lag statistics are scientifically distinct from absolute time series.

For pair-count fluctuation

$$
\delta N_{AB}(f)
=
N_{AB}(f)-\langle N_{AB}\rangle,
$$

one normalized autocorrelation is

$$
C_{AB}(\ell)
=
\frac{
\langle\delta N_{AB}(f)\delta N_{AB}(f+\ell)\rangle
}{
\langle\delta N_{AB}(f)^2\rangle
}.
$$

If the series variance is zero, normalized autocorrelation is undefined. The
result should report a constant-series condition rather than emitting unexplained
`NaN` values.

Autocorrelation, integrated correlation time, and statistical inefficiency are
deferred from the initial implementation.

# Combined cross-layer statistics

## Responsibility

`combined.py` aligns atomic and framework catalogs and reports how lower-level
atomic changes project into framework changes.

It is a convenience and comparison layer. It invokes the existing TS1 and TS2
branches, validates exact frame and connectivity-state derivation, and derives only
cross-layer contingency and boundary-consequence statistics. It must not duplicate
atomic or framework graph calculations.

## Alignment requirements

Combined analysis requires:

- identical analyzed frame count;
- identical source frame IDs and ordering;
- compatible collection identity;
- compatible atom identity;
- a topology catalog derived from the supplied atomic catalog or an explicitly
  verified equivalent source;
- compatible frame semantics.

A mismatch must raise an error. The implementation must not align catalogs merely
by equal length.

## Atomic-state to framework-class mapping

For atomic state $a$ and framework class $k$, define the frame contingency count

$$
C_{ak}
=
\sum_{f=1}^{F}
\mathbf 1[s_f^{\mathrm A}=a]
\mathbf 1[s_f^{\mathrm F}=k].
$$

This reports how many atomic states project to each framework topology.

Useful summaries include:

- number of atomic states per framework class;
- number of framework classes represented by each atomic state;
- dominant atomic state within each framework class;
- atomic-to-framework compression ratio;
- cross-layer occupancy table.

## Transition projection

For every adjacent trajectory boundary, compare atomic and framework assignments.
The implemented labels are:

```text
stable
atomic_only
framework_only
coupled
```

`atomic_only` means the atomic state changed while the framework class remained
constant. It does not assert that the mechanism was spectator motion. `coupled`
means both layers changed at the same stored-frame boundary. `framework_only` is
retained as a diagnostic but should not occur under exact deterministic reconciled
projection.

Boundary classification is generated only for reconciled trajectories. Ensembles
and per-frame identity modes retain static contingency statistics without temporal
interpretation.

For the 300 K Na-LTA example, the expected summary is conceptually:

```text
many Na-O atomic contact transitions
zero Si-O or Al-O framework-bond changes
one framework topology class
zero framework transitions
```

# Result-model principles

## Immutable, schema-versioned results

Statistics results should be immutable after construction. Numerical arrays should
be read-only where practical.

Every major result should include:

- statistics schema version;
- package version;
- source catalog schema and digest;
- frame semantics;
- analyzed frame IDs;
- time-axis provenance;
- options and requested descriptors;
- completeness or omission flags.

## State-level and frame-level data

The implementation should preserve both:

1. compact state-level descriptors computed once per unique graph;
2. frame-level arrays expanded through catalog assignments.

This avoids recomputation while providing convenient timelines.

## Missing and undefined quantities

Undefined quantities should be represented explicitly.

Examples include:

- no temporal statistics for ensembles;
- no physical time when only frame indices are available;
- undefined normalized autocorrelation for constant series;
- no framework statistics when no `TopologyCatalog` is supplied;
- no transition matrix for a one-frame trajectory.

The result should distinguish **not requested**, **not applicable**, and
**undefined** where the distinction matters.

# Computational model and scaling

## Exploit catalog compression

Let:

- $F$ be the number of analyzed frames;
- $S_A$ the number of unique atomic-connectivity states;
- $S_F$ the number of unique framework topologies;
- $E_s^A$ the atomic-edge count of state $s$;
- $E_k^F$ the framework-edge count of topology $k$.

Graph descriptors should be computed once per unique state:

$$
O\left(
\sum_{s=1}^{S_A}|E_s^A|
+
\sum_{k=1}^{S_F}|E_k^F|
\right).
$$

Expanding $D$ scalar descriptor series to frames costs approximately

$$
O(FD).
$$

This is preferable to reconstructing and recounting every graph independently:

$$
O\left(
\sum_{f=1}^{F}|E_f|
\right).
$$

## Contact occupancy scaling

Exact occupancy of all distinct edges requires processing each unique state's edge
set and weighting by its frame occupancy. If $U$ is the number of distinct edges
across the catalog, memory is approximately

$$
O(U).
$$

For very reactive systems, $U$ may be large. Options should permit disabling
atom-resolved or edge-resolved results while retaining aggregate species-pair
statistics.

## Temporal expansion

Transition timelines can often use catalog segments directly rather than compare
all consecutive edge sets. Edge-level event statistics still require exact edge
set differences at transition boundaries, not every frame.

The architecture should favor:

```text
state descriptor once
frame expansion by integer indexing
transition analysis at segment boundaries
```

# Plotting architecture

`mdstats/plotting/topology_statistics.py` should consume statistics results only.

The initial plotting surface may include:

```python
plot_pair_count_distribution(...)
plot_pair_count_timeseries(...)
plot_catalog_state_occupancy(...)
plot_catalog_state_timeline(...)
plot_transition_raster(...)
plot_transition_matrix(...)
plot_dwell_distribution(...)
plot_contact_occupancy_distribution(...)
plot_graph_descriptor_timeseries(...)
```

Plotting rules should include:

- discrete bars for exact integer count distributions;
- frame index when physical time is unavailable;
- no temporal plots for ensembles unless the x-axis is explicitly labeled sample
  index and no temporal interpretation is made;
- consistent atomic and framework state labels;
- visible distinction between atomic and framework quantities;
- no recomputation of catalog descriptors;
- return of Matplotlib figure and axes objects under existing package conventions.

File export should use statistics objects as the source of truth. CSV and JSON
writers may be methods or helper functions, but they must not create a competing
analysis path.

# Standard analysis workflows

## Nonreactive framework with mobile spectators

```text
trajectory
   |
   v
atomic connectivity catalog
   |-- variable spectator contacts
   `-- stable framework-forming atomic edges
   |
   v
framework topology catalog
   `-- one topology class
   |
   v
topology statistics
   |-- contact-count distributions
   |-- atomic transition timeline
   |-- one framework class
   `-- zero framework transitions
```

This is the expected Na-LTA validation workflow.

## Reactive trajectory

```text
trajectory
   |
   v
atomic state sequence A A A B B C C
   |
   v
framework classes     X X X Y Y Z Z
   |
   v
statistics
   |-- edge changes by species pair
   |-- atomic and framework dwell intervals
   |-- component and cycle-rank changes
   |-- affected vertices and linkers
   `-- cross-layer transition classification
```

The statistics layer reports what changed and when. Ring destruction and creation
remain the responsibility of later primitive-ring analysis.

## Uniform ensemble

```text
unordered samples
   |
   v
one or several atomic states
   |
   v
one framework class
   |
   v
ensemble-safe statistics only
```

Permitted outputs include count distributions, occupancies, degrees, entropy, and
contact occupancy. Transition matrices, dwell times, and rates are not defined.

## Multi-topology ensemble

An ensemble may contain several framework classes. The module reports class
occupancies and descriptor distributions grouped by class, but does not interpret
adjacent stored samples as transitions.

## Atomic-only analysis

When no framework catalog exists, atomic statistics remain valid. The combined
result should omit the framework branch explicitly rather than create an empty
pseudo-catalog.

# Validation strategy

Each stage should include analytical graph fixtures and domain integration tests.

## Common-statistics tests

- exact distribution of a constant integer series;
- multimodal integer distribution;
- deterministic mode ordering;
- population standard deviation;
- entropy of one state;
- entropy of equal state occupancies;
- frame expansion from state-level values;
- immutable output arrays;
- serialization round trip;
- invalid or nonfinite time axes.

## Atomic-statistics tests

- constant Si-O and Al-O edge counts;
- variable Na-O edge counts;
- canonical species-pair ordering;
- total-edge consistency;
- degree distributions by species;
- contact occupancy with permanent and intermittent edges;
- additions, removals, and churn at known boundaries;
- simultaneous multiple-edge events;
- atom participation counts;
- no framework interpretation.

## Framework-statistics tests

- uniform topology with constant descriptors;
- endpoint-species counts;
- complete asymmetric bridge-signature separation;
- whole-path reverse equivalence;
- parallel-edge multiplicity;
- self-image edge counts;
- disconnected graph component counts;
- exact cycle rank $E-V+C$;
- projected-contact occupancy across classes;
- no primitive-ring-count claim.

## Temporal-statistics tests

- exact transition frames;
- maximal contiguous residence intervals;
- recurring sequence $A-B-A$;
- transition-count matrix;
- one-frame and uniform trajectories;
- edge-presence episodes;
- successful time-axis conversion;
- rejection of ensemble temporal analysis;
- constant-series lag diagnostic.

## Combined-statistics tests

- exact atomic/framework frame-index and frame-ID alignment;
- exact frame-to-connectivity-state assignment alignment;
- representative source-digest validation;
- many atomic states mapping to one framework class;
- exact contingency counts and conditional probabilities;
- stable, atomic-only, framework-only, and coupled boundary categories;
- atomic transition without framework transition;
- simultaneous atomic and framework transition;
- ensemble and per-frame temporal omission;
- deterministic contingency matrix;
- cross-layer serialization and digest tampering rejection.

## Domain validation on Na-LTA

The 300 K Na-LTA trajectory should provide a standing integration test with
expected qualitative behavior:

- Si-O and Al-O count distributions are delta functions at the framework bond
  count;
- Na-O contact counts have finite width;
- multiple atomic states occur;
- one framework topology occurs;
- atomic transitions are contact-level changes;
- no projected framework transition occurs;
- every projected T-T edge has occupancy one.

Exact Na-O state counts may depend on the chosen connectivity definition and must
be tied to that definition's provenance.

# Staged implementation plan

The subpackage should be implemented one stable layer at a time.

## Stage TS0: common statistical foundation - implemented

`_common.py` and its specification are implemented in `mdstats 0.17.0a0` and
retained unchanged in `0.17.0a1`.

Primary outcome:

> Immutable exact distributions, scalar summaries, catalog occupancies, entropy,
> frame expansion, time-axis validation, and shared serialization primitives.

Acceptance criteria:

- no dependency on atomic or framework edge semantics;
- exact integer distributions;
- deterministic and immutable results;
- trajectory and ensemble metadata preserved.

## Stage TS1: atomic-connectivity statistics - implemented

`atomic.py` and its specification are implemented in `mdstats 0.17.0a1`.

Primary outcome:

> Species-pair counts, degree statistics, atomic-state occupancies, contact
> occupancies, and aggregate contact-change summaries derived from
> `AtomicConnectivityResult`.

Initial scope:

- exact pair-count distributions;
- total-edge series;
- state occupancy and diversity;
- degree distributions;
- contact occupancy;
- transition additions and removals when trajectory semantics are available.

The implementation uses gauge-invariant atom-pair contact identity across states.
Contact-lifetime survival analysis remains deferred beyond TS3.

## Stage TS2: framework-topology statistics - implemented

Implemented in `mdstats 0.17.0a3` as `framework.py`.

Primary outcome:

> Framework class occupancies, graph descriptors, endpoint and whole-path bridge
> signatures, projected-edge occupancies, and transition-affected structure
> summaries derived from `TopologyCatalog`.

The implemented TS2 layer preserves complete-path reversal equivalence, reports
`E - V + C` only as graph cycle-space rank, and was validated against the uniform
2,000-frame 300 K Na-LTA framework catalog.

The implementation must preserve Stage 2 whole-path orientation equivalence and
must label $\beta_1$ as cycle-space rank rather than primitive-ring count.

## Stage TS3: shared temporal statistics - implemented

Implemented in `mdstats 0.17.0a3` as `temporal.py` and integrated into the atomic
and framework branches.

Primary outcome:

> Exact trajectory transition timelines, residence intervals, transition matrices,
> return lags, and typed atomic-contact/framework-edge episodes with strict
> rejection of unordered ensemble semantics.

The implementation reports sample spans between stored instants, preserves
boundary-censoring flags, and deliberately defers probabilities, rates,
autocorrelation, and censoring-corrected survival estimators.

## Stage TS4: combined cross-layer statistics - implemented

Implemented in `mdstats 0.17.0a4` as `combined.py`.

Primary outcome:

> Exact source alignment, atomic-state/framework-class contingency, catalog
> compression summaries, and classification of reconciled trajectory boundaries
> as stable, atomic-only, framework-only, or coupled.

The implemented layer reproduces the core Na-LTA statement automatically:

```text
72 atomic states -> 1 framework class
71 framework-preserving atomic transitions
0 framework-changing atomic transitions
```

Boundary interpretation is deliberately disabled for ensembles and unreconciled
per-frame identity modes.

## Stage TS5: plotting and export - implemented

Implemented `mdstats/plotting/topology_statistics.py` and
`mdstats/io/topology_statistics.py`.

Primary outcome:

> Standard plots and machine-readable tables generated only from completed
> statistics results.

The implemented initial outputs include:

- pair-count PMFs;
- pair-count time series;
- state/class occupancies;
- state timelines;
- transition rasters;
- graph-descriptor time series;
- JSON summary and CSV tables.

# Edge cases and scientific warnings

## Connectivity edges are model-dependent

A Na-O edge may represent a radial or hysteretic coordination contact rather than a
chemical bond. Statistics must retain connectivity-definition provenance and use
neutral terms such as **contact** unless the input definition supports a stronger
interpretation.

## Atomic transitions are not automatically site hops

Formation or removal of one Na-O contact may occur within one adsorption basin.
Site-to-site hopping requires later ring-site or cage assignment.

## Cycle rank is not primitive-ring count

The graph invariant

$$
\beta_1=E-V+C
$$

is the dimension of the graph cycle space. It does not enumerate removed-edge
shortest-path primitive rings or physical pore windows.

## Ensemble order is not time

Temporal analysis must reject ensembles even when samples are stored in a numbered
sequence. A sample-index plot is permitted only when clearly labeled and not
interpreted dynamically.

## Physical time may be unavailable

Formats such as `XDATCAR` may not contain the frame timestep. The analysis may use
frame indices or a user-supplied time axis, but it must not guess physical time.

## Correlated trajectory samples

Empirical distributions over a trajectory describe observed frame occupancy.
They do not imply independent observations or uncertainty estimates.

## Rare states and one-frame states

A state observed once is a valid catalog state. The statistics layer may label it
rare, but must not remove or merge it unless the authoritative catalog already did
so.

## Very large edge unions

Reactive systems may contain a large number of distinct edges. Edge-resolved
occupancy and episode statistics should be optional to bound memory use.

## Asymmetric bridge order

Framework bridge grouping must use the complete reversal-equivalent path. Sorting
linker species independently would recreate the Stage 2 orientation bug.

## Digest collisions and equality

Digests are compact identifiers and lookup aids. Structured canonical records
remain authoritative for equality. Statistics should not merge states or edges by
digest alone.

## Variable cells and periodic images

The catalogs already define periodic edge identity. Statistics must count canonical
records and must not recompute minimum-image relations from coordinates.

## Missing species or source metadata

Species-resolved results require stable atom species metadata. If a catalog omits
required source metadata, the module should fail clearly or expose only graph-
agnostic quantities.

# Deferred features

The following are compatible with the architecture but intentionally deferred:

- autocorrelation and integrated correlation time;
- statistical inefficiency and effective independent sample size;
- block averaging and correlated confidence intervals;
- transition-rate estimation;
- Markov-state models;
- Bayesian rare-event estimates;
- approximate graph-state clustering;
- graph edit-distance distributions;
- inferred chemical reaction classification;
- atom-resolved event networks;
- survival analysis with censoring corrections;
- persistent tuning profiles for large catalogs;
- primitive-ring count and ring-size statistics;
- ring-site occupancy and site-to-site transitions;
- cage occupancy and cage-to-cage transport;
- automatic report generation with scientific conclusions.

Deferral is deliberate. These features should be added only after the exact static
and event statistics are stable and tested.

# Accepted architectural decisions

The following decisions define the current baseline:

1. Topology statistics consume completed catalogs and never rebuild graph identity.
2. Atomic and framework statistics are separate scientific branches.
3. Shared mathematical utilities live in one private common module.
4. Trajectory-only logic lives in a dedicated temporal module.
5. A thin combined module owns cross-layer alignment and comparison.
6. Plotting consumes statistics results and does not inspect raw catalogs.
7. Exact integer probability mass functions are primary outputs.
8. Population standard deviation summarizes the analyzed collection by default.
9. Descriptive trajectory distributions do not imply independent samples.
10. Ensemble order is never interpreted as time.
11. Physical time is optional and must be supplied or derived from explicit
    metadata.
12. Catalog state and topology-class IDs remain in separate namespaces.
13. Atomic contact changes do not automatically imply framework changes.
14. Species-pair atomic edges are grouped canonically as undirected pairs.
15. Framework bridge signatures preserve complete whole-path reversal equivalence.
16. Cycle-space rank is reported separately from primitive-ring counts.
17. State entropy is labeled Shannon state entropy, not thermodynamic entropy.
18. Graph descriptors are computed once per unique catalog state and expanded to
    frames by integer indexing.
19. Edge-resolved statistics are optional when the distinct-edge union is large.
20. Results are immutable, schema-versioned, and retain source-catalog provenance.
21. Undefined, not-applicable, and not-requested quantities are distinguished.
22. Rare catalog states are reported rather than silently removed.
23. Combined analysis requires exact frame and source alignment.
24. Digests do not replace structured equality.
25. Each implementation stage receives a detailed paired Markdown/PDF
    specification before coding.

# TS4 accepted decisions

1. Combined analysis accepts authoritative catalogs, not precomputed branch results
   alone, so exact source derivation can be validated.
2. Equal frame count is insufficient; frame indices, frame IDs, semantics, and
   connectivity-state assignments must match exactly.
3. TS4 invokes TS1 and TS2 and does not duplicate their graph descriptors.
4. The atomic-state/framework-class contingency matrix is exact and dense in the
   initial implementation.
5. Atomic and framework state IDs remain separate namespaces.
6. Boundary categories are stable, atomic-only, framework-only, and coupled.
7. Atomic-only is a structural projection statement, not a mechanism label.
8. Boundary statistics require reconciled trajectory identity at both layers.
9. Ensembles and per-frame modes receive static contingency statistics only.
10. The compact regime is descriptive and does not replace the full contingency.
11. The atomic-to-framework compression ratio is a catalog-count ratio, not a
    thermodynamic or kinetic measure.
12. TS4 retains complete TS1 and TS2 branches inside one immutable combined result.

# Theoretical references

1. Shannon, C. E. (1948). *A Mathematical Theory of Communication*. Bell
   System Technical Journal, 27, 379-423 and 623-656. DOI:
   [10.1002/j.1538-7305.1948.tb01338.x](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x).
2. Wiener, N. (1930). *Generalized Harmonic Analysis*. Acta Mathematica, 55,
   117-258. DOI:
   [10.1007/BF02546511](https://doi.org/10.1007/BF02546511).
3. Khintchine, A. (1934). *Korrelationstheorie der stationaeren stochastischen
   Prozesse*. Mathematische Annalen, 109, 604-615. DOI:
   [10.1007/BF01449156](https://doi.org/10.1007/BF01449156).

Shannon supplies the information-entropy measure used for catalog diversity.
Wiener and Khintchine supply the correlation/spectral lineage used by later
lag-domain statistics. Catalog compression, exact cross-layer state mapping,
and the separation between descriptive transition counts and kinetic inference
are `mdstats` architectural decisions.

# Context-restoration checklist

Before implementing or revising a topology-statistics component, recover the
following context:

- Is the input an atomic-connectivity catalog or a framework-topology catalog?
- Which catalog schema and connectivity or mapping definition produced it?
- Are the frames a trajectory or an ensemble?
- Is physical time available, supplied, or absent?
- Is the requested quantity static, temporal, or cross-layer?
- Is the descriptor computed per unique state or per frame?
- Does an integer descriptor require an exact PMF rather than a continuous
  histogram?
- Are atomic species pairs or framework bridge signatures being grouped?
- Does bridge grouping preserve whole-path orientation equivalence?
- Is an atomic contact being described more strongly than its connectivity model
  allows?
- Is cycle-space rank being confused with a primitive-ring count?
- Are trajectory samples being treated as independent?
- Are ensemble samples being assigned a false temporal order?
- Are state IDs from atomic and framework catalogs being kept separate?
- Does combined analysis verify exact frame and source alignment?
- Are undefined quantities reported explicitly?
- Is the distinct-edge union small enough for edge-resolved output?
- Are results immutable and fully provenance-bearing?
- Is plotting consuming completed statistics rather than recomputing them?
- Which advanced features remain intentionally deferred?

# Final architecture summary

The proposed topology-statistics architecture is

```text
AtomicConnectivityResult
        |
        v
atomic statistics ---------+
                            |
TopologyCatalog             +--> combined statistics --> plotting and export
        |                   |
        v                   |
framework statistics -------+

trajectory semantics --> shared temporal statistics
ensemble semantics   --> static distributions only
```

The common layer supplies exact statistical machinery. The atomic layer describes
contacts, degrees, and atomic graph states. The framework layer describes projected
edges, bridge signatures, connectivity invariants, and framework classes. The
temporal layer describes ordered events only when time ordering is scientifically
valid. The combined layer states how atomic changes project into framework changes.
The plotting layer presents completed results without changing their meaning.

This separation provides a compact implementation surface while preventing the
most important category errors: mixing atomic contacts with framework bridges,
using ensemble order as time, collapsing asymmetric linker paths, and confusing
graph cycle rank with primitive rings.

# MLFF caller boundary

Topology statistics remain analysis-owned. The MLFF branch may request atomic
connectivity statistics or consume a completed framework/topology result for
validation, but it does not own contact occupancy, degree distributions, state
transitions, residence intervals, entropy, or cross-layer projection.

`mdstats 0.20.44a0` adds standardized call IDs for atomic connectivity and
atomic connectivity statistics. Framework and combined topology statistics
continue to use their direct typed APIs because they require authoritative
framework/topology catalogs. A later standardized port may bind those catalogs
as explicit external dependencies; no duplicate implementation is permitted.

Ring, cage, or site statistics are optional material-profile extensions and are
not defaults for crystalline, amorphous, liquid, or interface MLFF validation.
