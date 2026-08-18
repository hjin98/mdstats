---
title: "Collective Charge Current and Current-Correlation Specification"
subtitle: "C0 Contract Closure and C1 Ordered Collective Correlations"
author: "mdstats"
date: "2026-07-22"
geometry: margin=0.9in
fontsize: 10pt
toc: true
toc-depth: 2
numbersections: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{fvextra}
    \usepackage{hyperref}
    \DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,breakanywhere,commandchars=\\\{\}}
---

# Purpose and status

This document specifies roadmap stages **C0** and **C1** for
`mdstats 0.19.85a0`:

- C0 closes the package-level charge, neutrality, grouping, correlation-order,
  volume-provenance, and immutability contracts.
- C1 implements collective charge-current construction and positive-lag total
  and ordered group-current correlations.

The implementation resides in
`mdstats.analysis.current_correlation`. Conductivity integration, explicit plateau estimation, and the
Nernst-Einstein comparison are implemented by the separate C2 module
`mdstats.analysis.ionic_conductivity` in `mdstats 0.19.86a0`.

The equilibrium current-correlation framework follows the Green-Kubo linear
response relation [1, 2]. FFT evaluation reuses the package's existing
positive-lag linear-correlation machinery, which is an implementation of the
Wiener-Khinchin correlation identity [3, 4]. Charge resolution, exact group
partitioning, fixed/variable-cell provenance, public result schemas, backend
selection, and fail-closed validation are `mdstats` design decisions.

# Physical definitions

For per-atom charges $q_i$ in units of the elementary charge $e$ and Cartesian
velocities $\mathbf v_i(t)$ in Angstrom/ps, the microscopic charge current is

$$
\mathbf J_q(t)=\sum_i q_i\mathbf v_i(t).
$$

Its stored units are

$$
e\,\mathrm{Angstrom}/\mathrm{ps}.
$$

For an exact partition of the current-carrying atoms into named groups $a$,

$$
\mathbf J_q(t)=\sum_a\mathbf J_a(t).
$$

The positive-lag ordered cross correlation is

$$
C_{ab}(\tau)
=
\left\langle
\mathbf J_a(t_0)\cdot\mathbf J_b(t_0+\tau)
\right\rangle_{t_0}.
$$

At positive lag, $C_{ab}$ and $C_{ba}$ are distinct estimators and are stored
separately. No implicit symmetrization is performed.

# C0 resolved contract

## Charge input

`compute_charge_current()` accepts exactly one charge source:

1. `charges`: one finite real value per canonical atom; or
2. `species_charges`: a mapping from exact chemical symbols to finite charge
   values.

Integer-key charge mappings are rejected because an integer could denote an
atom index or an atomic number. A species mapping must contain every element
present in the collection exactly once and must not contain unknown or unused
symbols. Resolved charges are stored as an immutable per-atom array in canonical
atom order.

Atoms with exactly zero resolved charge do not contribute to the current and
are excluded from `current_atom_indices`. At least one current-carrying atom is
required.

## Neutrality

The first release requires a neutral system:

$$
\left|\sum_i q_i\right|\le\varepsilon_Q,
$$

where `neutrality_tolerance_e` is finite and nonnegative. A non-neutral override
is deliberately absent. This prevents an unqualified drift correction from
changing the total charge current by
$Q_{\mathrm{tot}}\mathbf v_{\mathrm{drift}}$.

## Drift removal

Velocity validation and drift construction reuse `_velocity_common.py`.
`drift_mode`, `drift_species`, and `drift_atom_indices` therefore have the same
meaning and strict validation as VACF and direct velocity-spectrum analysis.
The exact drift-reference atom population is retained in the shared
`DynamicsInputSignature`.

For a neutral system, subtracting one common framewise drift velocity leaves the
total current invariant analytically. Individual charged-group currents can
change, so the selected drift convention remains part of the result provenance.

## Exact group partition

`species_groups` is optional. When supplied, it is an insertion-ordered mapping
from a nonempty unique group name to a `SpeciesSelection`.

Each group selection is intersected with `current_atom_indices`; zero-charge
atoms are ignored. The resulting nonempty groups must be pairwise disjoint and
must cover every current-carrying atom exactly once. Consequently,

$$
\mathbf J_q(t)=\sum_a\mathbf J_a(t)
$$

is a validated result invariant. Partial, overlapping, or diagnostic groupings
belong to a future separately named API.

## Cell and volume provenance

`ChargeCurrentResult` stores:

- the complete instantaneous volume series;
- the three periodic-axis flags;
- whether the full cell matrix is fixed across all frames; and
- the fixed volume when the cell is fixed.

A trajectory with constant determinant but changing cell matrix is classified
as variable-cell. C1 does not reject variable cells because current correlation
itself requires no volume. C2 conductivity integration will reject them in its
first release.

# Public APIs

## Charge-current construction

```python
def compute_charge_current(
    collection: AtomisticFrameCollection,
    *,
    charges: ArrayLike | None = None,
    species_charges: Mapping[str, float] | None = None,
    species_groups: Mapping[str, SpeciesSelection] | None = None,
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    neutrality_tolerance_e: float = 1.0e-12,
) -> ChargeCurrentResult:
    ...
```

The function requires a uniformly sampled trajectory with complete Cartesian
velocities. It performs no time correlation, SI conversion, conductivity
integration, smoothing, or plateau selection.

## Current correlation

```python
def compute_current_correlation(
    current: ChargeCurrentResult,
    *,
    max_lag: int | None = None,
    origin_stride: int = 1,
    lag_stride: int = 1,
    compute_tensor: bool = True,
    backend: Literal["auto", "direct", "fft"] = "auto",
) -> CurrentCorrelationResult:
    ...
```

`max_lag` defaults to half the trajectory length. Lag zero is always retained.
`origin_stride != 1` requires the direct backend. `lag_stride` changes only the
stored lags, not the physical sample spacing. C1 correlates the raw resolved
current. It does not subtract a time-mean current, detrend, smooth, or symmetrize
the data; drift removal must be requested during charge-current construction.

# Result schemas

## `ChargeCurrentResult`

The immutable result stores:

```text
times_ps                   (T,)
total_current              (T, 3)
group_names                tuple[str, ...]
group_currents             (T, G, 3) or None
charges_e                  (N,)
current_atom_indices       (M,)
group_atom_indices         mapping[str, (M_g,)]
total_charge_e             scalar
sample_spacing_ps          scalar
pbc                        (3,)
cell_volumes_a3            (T,)
cell_mode                  "fixed" or "variable"
fixed_volume_a3            scalar or None
signature                  DynamicsInputSignature
metadata                   recursively immutable mapping
```

The constructor validates finite values, shapes, exact current-carrying atom
identity, neutrality, exact group partition, exact group-current sum, fixed-cell
volume consistency, and signature consistency.

## `CurrentCorrelationResult`

The immutable result stores:

```text
lag_steps                  (L,)
lag_times                  (L,)
scalar                     (L,)
components                 (L, 3)
tensor                     (L, 3, 3) or None
group_names                tuple[str, ...]
group_scalar               (L, G, G) or None
group_tensor               (L, G, G, 3, 3) or None
n_origins                  (L,)
backend                    "direct" or "fft"
charges_e                  (N,)
current_atom_indices       (M,)
group_atom_indices         immutable mapping
pbc                        (3,)
cell_volumes_a3            (T,)
cell_mode                  "fixed" or "variable"
fixed_volume_a3            scalar or None
signature                  DynamicsInputSignature
metadata                   recursively immutable mapping
```

The scalar and Cartesian identities are

$$
C_{\mathrm{tot}}(t)=\sum_\alpha C_{\alpha\alpha}(t),
$$

and, when groups exist,

$$
C_{\mathrm{tot}}(t)=\sum_{a,b}C_{ab}(t).
$$

If tensors are retained, `components` equals the total tensor diagonal and each
`group_scalar[:,a,b]` equals the trace of
`group_tensor[:,a,b,:,:]`.

# Direct estimator

For lag $k$ and valid origins
$t_0=0,s,2s,\ldots<T-k-1$, the direct estimator computes

$$
C_{\alpha\beta}(k)
=
\frac{1}{N_k}
\sum_{t_0}
J_\alpha(t_0)J_\beta(t_0+k).
$$

Group tensors replace the two total currents with $\mathbf J_a$ and
$\mathbf J_b$. The origin count is

$$
N_k=\left\lfloor\frac{T-1-k}{s}\right\rfloor+1.
$$

# FFT estimator

For `origin_stride == 1`, C1 forms zero-padded linear cross spectra

$$
\widehat C_{xy}=\widehat x^{\,*}\widehat y
$$

and inverts them through `_fft.positive_lag_correlation_from_spectrum`.
Division by the exact pair count $T-k$ occurs before lag subsampling. Group
pairs are inverted one ordered pair at a time so temporary memory does not scale
as $G^2\times 3\times3\times N_\omega$.

The FFT and direct estimators must agree within floating-point tolerance and use
the same tensor orientation: the first Cartesian index belongs to the origin
current and the second to the lagged current.

# Backend selection

`backend="auto"` compares conservative direct and FFT work estimates. It keeps
the direct estimator for short trajectories and whenever `origin_stride != 1`.
The selected backend and both work estimates are stored in metadata.

# Units

Current units are

```text
e*Angstrom/ps
```

Current-correlation units are

```text
e^2*Angstrom^2/ps^2
```

C1 does not convert the elementary charge, Angstrom, or picosecond to SI units.
That conversion belongs exclusively to C2 conductivity integration.

# Failure policy

The public functions fail closed for:

- missing or multiple charge sources;
- non-finite, wrong-shaped, ambiguous, incomplete, or extra charge mappings;
- a system with no nonzero charges;
- non-neutral total charge outside tolerance;
- invalid drift selections;
- empty, overlapping, or incomplete current groups;
- nonuniform time sampling or missing velocities;
- invalid lag, stride, boolean, or backend inputs;
- FFT requests with non-unit origin stride;
- malformed result construction;
- non-finite current or correlation values; and
- any violation of total/group or tensor/trace identities.

# Required tests

C0-C1 acceptance requires tests for:

1. exact per-atom array and species-map charge agreement;
2. missing, duplicate-source, incomplete, extra, integer-key, and non-finite
   charge rejection;
3. neutrality-tolerance acceptance and non-neutral rejection;
4. neutral rigid translation giving zero total current;
5. explicit paired-charge algebra;
6. exact group-current sum;
7. overlap, omission, and empty-group rejection;
8. fixed-cell and constant-volume variable-cell classification;
9. drift-reference signature preservation;
10. direct/FFT agreement for total and group tensors;
11. ordered positive-lag group correlations with $C_{ab}\ne C_{ba}$;
12. exact total/group-pair sum and tensor-trace identities;
13. zero-current behavior and constant nonzero-current preservation;
14. strict integer and boolean validation;
15. backend and origin-stride policy;
16. deep array, mapping, and nested-metadata immutability;
17. public exports; and
18. regression compatibility with the existing VACF/dynamics branch.

# Implemented C2 boundary

`mdstats 0.19.86a0` consumes `CurrentCorrelationResult` in the separate
`ionic_conductivity.py` module. C2 enforces full three-dimensional periodicity
and fixed full-cell-matrix provenance, performs cumulative Green-Kubo
quadrature with exact SI conversion, retains ordered group-pair contributions,
selects only explicit conductivity plateau intervals, and compares against
compatible full-3D species diffusion estimates. The C0-C1 result schemas remain
the authoritative charge, partition, cell, and trajectory provenance source.

# References

[1] M. S. Green, "Markoff Random Processes and the Statistical Mechanics of
Time-Dependent Phenomena. II. Irreversible Processes in Fluids," *Journal of
Chemical Physics* **22**, 398-413 (1954). DOI: 10.1063/1.1740082.

[2] R. Kubo, "Statistical-Mechanical Theory of Irreversible Processes. I.
General Theory and Simple Applications to Magnetic and Conduction Problems,"
*Journal of the Physical Society of Japan* **12**, 570-586 (1957). DOI:
10.1143/JPSJ.12.570.

[3] N. Wiener, "Generalized Harmonic Analysis," *Acta Mathematica* **55**,
117-258 (1930). DOI: 10.1007/BF02546511.

[4] A. Khintchine, "Korrelationstheorie der stationaren stochastischen
Prozesse," *Mathematische Annalen* **109**, 604-615 (1934). DOI:
10.1007/BF01449156.
