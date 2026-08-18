---
title: "mdstats Thermomechanical and Energetic Validation Architecture"
subtitle: "Equation of state, elasticity, thermodynamics, viscosity, phonons, surfaces, interfaces, defects, and migration barriers"
author: "mdstats project"
date: "2026-07-30 (revision: reference states, phonons, hulls, and transport ownership)"
geometry: margin=0.78in
toc: true
toc-depth: 3
numbersections: true
fontsize: 10.5pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{longtable}
  - |-
    \usepackage{microtype}
  - |-
    \usepackage{xurl}
---

# Purpose and ownership

This manual defines the architecture for **thermomechanical and energetic
validation** in `mdstats`. It owns analyses in which the primary scientific
objects are energies, enthalpies, stresses, strains, volumes, force constants,
free-energy derivatives, surfaces, interfaces, defects, or transition paths.

The branch is independent of the MLFF training-data branch. A machine-learned
force-field workflow may call these analyses through the standardized observable
API, pair reference and candidate results, and apply a separately declared
comparison policy. It must not reimplement the theory or numerical algorithms.

This manual does not transfer ownership of existing analyses:

- RDF, coordination, neighbor angles, and generic connectivity remain in the
  structural-observables architecture;
- graph-state statistics remain in the topology-statistics architecture;
- MSD, VACF, VDOS, diffusion, van Hove functions, current correlations, and
  ionic conductivity remain in the dynamics and transport architecture;
- ring, cage, pore-window, and site semantics remain optional framework/porous
  extensions.

The initial release of this manual is architectural. Unless a section is marked
implemented, the corresponding runtime analysis is **planned**.

# Governing principles

1. **Reference state is part of the result.** Energy differences are meaningless
   without composition, chemical potentials, charge state, strain state,
   boundary conditions, and relaxation constraints.
2. **Static and finite-temperature properties are different analyses.** A
   zero-kelvin curvature, an isothermal fluctuation modulus, and an adiabatic
   modulus must never share one unlabeled result field.
3. **Fit policy is immutable evidence.** Strain amplitudes, volume grids,
   polynomial order, weights, excluded points, symmetry assumptions, and
   uncertainty methods are serialized.
4. **The sampled ensemble is explicit.** Fluctuation formulas are valid only in
   their corresponding equilibrium ensemble and after equilibration and
   stationarity checks.
5. **Comparison uses matched protocols.** Reference and candidate values are
   compared only when generated with compatible cells, supercells, k-point or
   boundary conventions, displacement patterns, thermodynamic state, and
   relaxation constraints.
6. **No universal pass threshold is implied.** Analysis modules produce values,
   uncertainties, diagnostics, and validity flags. Project-specific acceptance
   belongs to a separate validation policy.
7. **Expensive workflow generation is separate from result analysis.** The
   architecture may generate strain states, displaced supercells, slabs, defect
   cells, or NEB images, but their identities and calculator executions remain
   explicit workflow records.

# Shared data model

## Configuration and calculation identity

Every thermomechanical or energetic result binds:

- atomic numbers and positions;
- cell and periodic boundary conditions;
- composition and charge state;
- calculator/model identity and digest;
- numerical precision and software versions;
- relaxation constraints and convergence criteria;
- thermodynamic state, when applicable;
- source configuration and parent-child lineage;
- magnetic state, spin constraints, and magnetic initialization when relevant;
- electronic occupation/smearing and electronic-temperature convention;
- long-range electrostatic model, net-charge treatment, dipole correction, and
  electrostatic boundary condition;
- external electric, magnetic, or mechanical fields;
- atomic charge or polarization-model identity when the calculator uses one;
- chemical-potential reference set and admissible region when compositions vary;
- units and stress convention.

A result derived from several calculations additionally stores an ordered
`CalculationSetIdentity` containing the member digests and their physical
coordinates, for example volume, strain component, displacement pattern, defect
state, or reaction-path image.

## Fit and uncertainty records

All fitted analyses use an immutable `FitPolicy` and return a `FitDiagnostic`:

- independent variable and units;
- fit domain and excluded samples;
- model family and order;
- weighting and covariance policy;
- residuals and leverage diagnostics;
- condition number or rank;
- bootstrap or block-bootstrap settings;
- confidence interval convention;
- extrapolation flag.

A fit may be numerically successful yet scientifically invalid. The result must
separate numerical fit status from domain-validity status.

## Static versus trajectory inputs

Static analyses consume one or more independent configurations. Trajectory
analyses consume `AtomisticFrameCollection` objects with explicit ensemble,
time-axis, stress, energy, and volume semantics. Random frames extracted from a
trajectory do not retain time-correlation semantics unless the extraction
preserves an ordered trajectory.

# Equation of state and equilibrium volume

## Theory

An equation of state (EOS) describes energy or pressure as a function of volume
under a declared deformation path. For isotropic scaling at zero temperature,
the equilibrium volume $V_0$ minimizes the relaxed energy $E(V)$, and the bulk
modulus is

$$
B_0 = V_0\left.\frac{\partial^2 E}{\partial V^2}\right|_{V_0}.
$$

The third-order Birch--Murnaghan energy form uses the Eulerian strain

$$
f = \frac{1}{2}\left[\left(\frac{V_0}{V}\right)^{2/3}-1\right]
$$

and may be written

$$
E(V)=E_0+\frac{9V_0B_0}{16}
\left\{
\left[\left(\frac{V_0}{V}\right)^{2/3}-1\right]^3 B'_0
+\left[\left(\frac{V_0}{V}\right)^{2/3}-1\right]^2
\left[6-4\left(\frac{V_0}{V}\right)^{2/3}\right]
\right\}.
$$

This form is a model of a finite strain interval, not a universal law. A local
polynomial, Vinet form, or direct spline may be more appropriate for another
range. The selected form and interval are part of the result identity.

## Calculation protocol

The workflow must declare:

- isotropic or anisotropic deformation path;
- whether fractional coordinates and cell shape are fixed or relaxed;
- volume grid and reference volume;
- pressure correction and residual stress policy;
- electronic or calculator convergence;
- whether all points share the same phase and topology.

At least one point should lie on each side of the minimum. A fit that places
$V_0$ outside the sampled interval is extrapolative and fails the strict domain
gate.

## Planned API

```text
thermomechanical.eos_fit
thermomechanical.equilibrium_state
thermomechanical.bulk_modulus
```

The result stores $E_0$, $V_0$, $B_0$, $B'_0$ when defined, parameter covariance,
residuals, sampled points, and stability/domain diagnostics.

# Elastic constants and mechanical stability

## Small-strain theory

For a reference configuration with strain vector $\boldsymbol\epsilon$ in a
declared Voigt convention,

$$
\frac{E(\boldsymbol\epsilon)}{V_0}
=
\frac{E_0}{V_0}
+\boldsymbol\sigma_0\!:\!\boldsymbol\epsilon
+\frac{1}{2}\boldsymbol\epsilon^\mathsf{T}
\mathbf C\boldsymbol\epsilon
+O(\epsilon^3),
$$

and

$$
\Delta\boldsymbol\sigma = \mathbf C\boldsymbol\epsilon+O(\epsilon^2).
$$

The stiffness tensor $C_{ijkl}$ and compliance tensor $S=C^{-1}$ are different
objects. Engineering shear and tensorial shear conventions differ by factors of
two; the chosen convention must be serialized.

## Static finite-difference methods

Two supported routes are planned:

1. **energy--strain fitting**, which fits energy curvature;
2. **stress--strain fitting**, which fits stress derivatives.

For each independent strain mode the workflow should include positive and
negative amplitudes, test linearity with decreasing amplitude, and report the
sensitivity to fit range. Internal coordinates may be clamped or relaxed; these
produce clamped-ion and relaxed-ion elastic constants and cannot be mixed.

Crystal symmetry may reduce the number of independent constants, but symmetry
must be measured from the reference structure under a tolerance and recorded.
A full unconstrained tensor fit remains available for low-symmetry or disordered
cells.

## Finite-temperature elasticity

Finite-temperature elastic constants may be obtained from controlled stress--
strain simulations or equilibrium fluctuation formulas. Strain-fluctuation and
stress-fluctuation methods require the correct ensemble and long, stationary
trajectories. Their outputs must be labeled isothermal or adiabatic according to
the derivation and ensemble. They are not substitutes for zero-kelvin static
curvatures.

## Mechanical stability

At zero external stress, elastic stability requires positive curvature for all
allowed infinitesimal strains. In matrix form, the properly symmetrized stiffness
must be positive definite. Crystal-class-specific Born criteria may be reported
as a readable decomposition, but the eigenvalue test remains the general check.
Under nonzero external stress, stability uses the stress-corrected elastic
stiffness appropriate to the chosen thermodynamic potential; applying zero-
pressure criteria blindly is prohibited.

## Planned API

```text
thermomechanical.elastic_tensor_static
thermomechanical.elastic_tensor_finite_temperature
thermomechanical.mechanical_stability
thermomechanical.polycrystalline_moduli
```

Polycrystalline Voigt, Reuss, and Hill averages are derived summaries and must
retain the full tensor and averaging convention.

# Thermal expansion, compressibility, and heat capacity

## Thermal expansion

For an equilibrium volume curve,

$$
\alpha_V(T)=\frac{1}{\langle V\rangle_T}
\frac{d\langle V\rangle_T}{dT}.
$$

For anisotropic crystals the linear expansion tensor is obtained from the
temperature derivative of a consistently oriented cell or metric tensor. Cell
rotations must be removed before differentiation. A finite-difference curve over
independently equilibrated temperatures is the default robust route; direct
fluctuation estimators may be added only with their ensemble assumptions.

## Isothermal compressibility

In an equilibrium isothermal-isobaric ensemble,

$$
\kappa_T = \frac{\langle V^2\rangle-\langle V\rangle^2}
{k_B T\langle V\rangle}.
$$

The corresponding bulk modulus is $B_T=1/\kappa_T$. The estimate is sensitive
to barostat dynamics, equilibration, correlation time, and finite trajectory
length. Block analysis and effective sample size are mandatory diagnostics.

## Heat capacities

For a canonical ensemble,

$$
C_V = \frac{\langle E^2\rangle-\langle E\rangle^2}{k_B T^2},
$$

and for an isothermal-isobaric ensemble,

$$
C_P = \frac{\langle H^2\rangle-\langle H\rangle^2}{k_B T^2}.
$$

The energy or enthalpy must be the physical system quantity appropriate to the
ensemble, not an arbitrary thermostat extended Hamiltonian. Classical MD heat
capacities also carry the classical-statistical approximation and do not include
quantum nuclear corrections unless added explicitly. Finite-difference
enthalpy/energy curves are a separate estimator and should be compared where
possible.

## Planned API

```text
thermodynamic.thermal_expansion
thermodynamic.isothermal_compressibility
thermodynamic.heat_capacity_cv
thermodynamic.heat_capacity_cp
```

Each result stores ensemble identity, equilibration interval, block length,
autocorrelation diagnostics, effective sample size, and uncertainty.

# Stress autocorrelation and viscosity

## Ownership boundary

Viscosity is a transport coefficient, but its primary microscopic input is the
stress tensor rather than displacement or charge current. It is therefore owned
by this thermomechanical architecture while sharing common correlation,
integration, plateau, and uncertainty utilities with the dynamics architecture.
No second generic correlation engine should be introduced.

## Green--Kubo theory

For an isotropic equilibrium fluid, a shear-viscosity estimator is

$$
\eta = \frac{V}{k_B T}\int_0^\infty
\langle P_{xy}(0)P_{xy}(t)\rangle\,dt.
$$

Equivalent off-diagonal components and suitable traceless diagonal combinations
may be averaged to reduce variance. The stress must include the kinetic and
virial contributions consistent with the MD engine convention. The trajectory
must be stationary and sufficiently long to resolve a stable running integral.

Bulk viscosity requires the autocorrelation of pressure fluctuations after
subtracting the equilibrium pressure and, depending on formulation, coupling to
energy fluctuations. It is a separate analysis and must not be inferred from
shear viscosity code.

## Numerical policy

The result should include:

- component-resolved stress autocorrelations;
- averaged correlation and running integral;
- explicit integration rule;
- finite-time plateau interval;
- block or replica uncertainty;
- stationarity and long-time-tail diagnostics;
- thermostat/barostat provenance.

A plateau selector may recommend intervals, but the selected interval remains
explicit evidence. A short apparent plateau is not automatically a converged
transport coefficient.

## Planned API

```text
transport.stress_autocorrelation
transport.shear_viscosity
transport.shear_viscosity_plateau
transport.bulk_viscosity
```

# Harmonic phonons and quasiharmonic thermodynamics

## Force constants and dynamical matrix

In the harmonic approximation, displacements $u_{i\alpha}$ generate forces
through

$$
F_{i\alpha}=-\sum_{j\beta}\Phi_{i\alpha,j\beta}u_{j\beta},
$$

where $\Phi$ is the force-constant matrix. The mass-weighted dynamical matrix is

$$
D_{i\alpha,j\beta}(\mathbf q)=
\frac{1}{\sqrt{m_i m_j}}
\sum_{\mathbf R}\Phi_{0i\alpha,\mathbf Rj\beta}
\exp(i\mathbf q\cdot\mathbf R).
$$

Its eigenvalues are $\omega^2(\mathbf q)$. Negative $\omega^2$ is reported as an
imaginary mode and may indicate instability, insufficient relaxation,
finite-size error, or numerical noise.

## Finite-displacement workflow

The planned workflow generates symmetry-reduced displaced supercells, evaluates
forces with a bound calculator/model identity, assembles force constants, and
records:

- primitive and supercell matrices;
- displacement amplitudes and directions;
- symmetry tolerance;
- force-drift removal;
- acoustic sum-rule treatment;
- non-analytical correction policy;
- q-point path or mesh;
- supercell and displacement convergence diagnostics.

Phonon dispersion and harmonic DOS are different from an MD-derived VDOS. The
former is a small-displacement normal-mode calculation; the latter is a
finite-temperature velocity spectrum. Both may be compared, but must retain
separate result types and manuals.


## Harmonic thermodynamic functions

For a set of stable harmonic frequencies $\omega_{\mathbf q s}$, the quantum
vibrational Helmholtz free energy is

$$
F_{\mathrm{vib}}(T)=
\sum_{\mathbf q s}
\left[
\frac{1}{2}\hbar\omega_{\mathbf q s}
+k_B T\ln\left(1-e^{-\hbar\omega_{\mathbf q s}/k_BT}\right)
\right].
$$

The first term is the zero-point energy. The corresponding internal energy and
heat capacity follow from temperature derivatives. A calculation must state
whether it uses the quantum expression or the classical high-temperature limit.
The classical limit omits zero-point energy and gives $k_BT$ per harmonic mode
for the internal energy, but its absolute free energy depends on the chosen
phase-space normalization. Quantum and classical results must never be mixed
without an explicit conversion policy.

## Force-constant invariance and polar corrections

The assembled force constants should satisfy permutation symmetry,

$$
\Phi_{i\alpha,j\beta}=\Phi_{j\beta,i\alpha},
$$

and translational invariance through the acoustic sum rule,

$$
\sum_j \Phi_{i\alpha,j\beta}=0.
$$

For isolated molecules or nonperiodic clusters, rotational invariance is also a
meaningful diagnostic. The result records violations before correction and the
exact projection or enforcement applied. Enforcement is not evidence that the
raw calculation was converged.

Polar crystals may require a non-analytical long-range correction near
$\mathbf q=0$ to reproduce LO--TO splitting. That correction requires Born
effective charges, the high-frequency dielectric tensor, volume, and a declared
boundary convention. A conventional finite-cutoff MLFF does not automatically
contain this nonlocal dipole response. The phonon API must therefore either bind
external non-analytical-correction data or declare the result as short-range
only; it must not silently claim LO--TO accuracy.

## Quasiharmonic approximation

For volumes $V$ and temperature $T$,

$$
F(V,T)=E_0(V)+F_{\mathrm{vib}}(V,T),
$$

with the equilibrium volume obtained by minimizing $F(V,T)+PV$. Quasiharmonic
thermal expansion requires dynamically stable phonons over a converged volume
grid. Strong anharmonicity, diffusion, or phase changes invalidate the method.

## Planned API

```text
vibrational.force_constants
vibrational.phonon_dispersion
vibrational.harmonic_dos
vibrational.quasiharmonic_free_energy
vibrational.quasiharmonic_expansion
```

Interoperation with Phonopy may be provided through an adapter; Phonopy remains
the owner of its own file formats and algorithms.

# Surface energies

## Stoichiometric symmetric slabs

For a symmetric slab with two equivalent surfaces and bulk reference energy per
formula unit,

$$
\gamma = \frac{E_{\mathrm{slab}}-N E_{\mathrm{bulk}}}{2A}.
$$

The factor of two is valid only for two equivalent surfaces. An asymmetric slab
requires separate accounting or a cleavage/termination construction.

## Nonstoichiometric and charged surfaces

The general grand-potential expression is

$$
\gamma = \frac{E_{\mathrm{slab}}-\sum_i N_i\mu_i-q\mu_e+
E_{\mathrm{corr}}}{A_{\mathrm{exposed}}}.
$$

Here $q$ is the net positive charge of the slab relative to the chosen neutral
reference, and $\mu_e$ is the electron chemical potential on the same energy
zero; adding electrons therefore lowers $q$. A different sign convention is
permitted only when stored explicitly with the equation used. Chemical-potential
bounds, charge compensation, dipole corrections, and the chosen exposed area
are part of the result. A classical MLFF generally cannot represent changes in
electronic charge state unless that state is encoded in the model and data; the
analysis must not invent electronic corrections.

## Convergence requirements

- slab thickness;
- vacuum thickness;
- lateral cell size;
- relaxation depth and fixed layers;
- surface termination;
- dipole treatment;
- reference bulk strain and composition;
- finite-temperature averaging when used.

## Planned API

```text
energetic.surface_energy
energetic.cleavage_energy
```

# Interface energy and work of adhesion

## Interface excess energy

For an interface cell of area $A$, an excess interface energy can be written

$$
\gamma_{\mathrm{int}}=
\frac{E_{\mathrm{int}}-E_1^{\mathrm{ref}}-E_2^{\mathrm{ref}}}{n_{\mathrm{int}}A},
$$

where the reference energies must represent the same atom counts and compatible
coherent strain states, and $n_{\mathrm{int}}$ is the number of equivalent
interfaces in the periodic cell. Reference ambiguity is often larger than the
numerical fit error and must be explicit.

## Work of adhesion

For two surfaces and their joined interface under a matched reference,

$$
W_{\mathrm{ad}}=
\frac{E_{1}^{\mathrm{surf}}+E_{2}^{\mathrm{surf}}-E_{12}^{\mathrm{int}}}{A}
=\gamma_1+\gamma_2-\gamma_{12}.
$$

In the total-energy form, $E_{1}^{\mathrm{surf}}$ and
$E_{2}^{\mathrm{surf}}$ are the separated slabs obtained from the same interface
supercell with identical atom counts, in-plane cell, strain allocation, and
surface multiplicities; $E_{12}^{\mathrm{int}}$ is the joined-cell energy. In
the excess-energy form, $\gamma_1$, $\gamma_2$, and $\gamma_{12}$ are already
normalized by their declared exposed-surface or interface multiplicities. The
area $A$ and every multiplicity must be explicit in either representation.

The equality requires consistent strain, area, composition, termination, and
relaxation conventions. A separation curve may provide both the work of
separation and traction--separation response.

## Interface sampling

The workflow records orientation relationship, terminations, lateral registry,
coherent strain allocation, separation, intermixing, and number of interfaces.
For liquid--solid interfaces, a single configuration energy is not a free
energy. Finite-temperature interfacial free energies require a dedicated method
and are deferred.

## Planned API

```text
energetic.interface_excess_energy
energetic.work_of_adhesion
energetic.separation_curve
```

# Defect formation and binding energies

## Neutral defects

For a neutral defect with atom-count changes $n_i$ relative to a bulk reference,

$$
E_f = E_{\mathrm{def}}-E_{\mathrm{bulk}}-\sum_i n_i\mu_i.
$$

The result binds supercell, defect site, relaxation constraints, chemical
potentials, and finite-size convergence. Binding energies are differences among
formation energies under one consistent reference convention.

## Charged defects

The electronic-structure expression includes Fermi-level and electrostatic
terms,

$$
E_f(D^q)=E_{\mathrm{def}}^q-E_{\mathrm{bulk}}
-\sum_i n_i\mu_i
+q(E_F+E_{\mathrm{VBM}}+\Delta V)+E_{\mathrm{corr}}.
$$

These terms belong to an electronic-structure defect workflow. A conventional
charge-neutral MLFF does not by itself provide Fermi levels, band edges, or
charge corrections. The first MLFF validation scope is therefore neutral defects
or fixed-charge models with externally supplied, explicitly identified
corrections.

## Planned API

```text
energetic.defect_formation_energy
energetic.defect_binding_energy
energetic.defect_relaxation_volume
```

# Migration paths and barriers

## Minimum-energy paths

A migration barrier is defined from a converged minimum-energy path (MEP):

$$
E_m = \max_s E(\mathbf R(s))-E(\mathbf R_{\mathrm{initial}}).
$$

The nudged elastic band method optimizes a chain of images using perpendicular
physical forces and tangential spring forces. Climbing-image NEB refines the
highest image toward the saddle point. The analysis must distinguish the path
optimizer from the barrier extractor.

## Path identity and validation

A path record includes:

- initial and final configuration digests;
- atom mapping and periodic image convention;
- interpolation method and number of images;
- spring constants;
- tangent and climbing-image policy;
- force convergence;
- fixed atoms and cell constraints;
- calculator/model identity;
- image energies, forces, and convergence state.

The barrier extractor rejects an unconverged path unless explicitly requested
for diagnostic use. Multiple plausible paths are separate candidates rather
than silently merged.

## Planned API

```text
path.minimum_energy_path
path.migration_barrier
path.transition_state_curvature
```

# Phase, formation, and convex-hull energetics

## Matched phase energies and enthalpies

Relative phase energies require a common composition and compatible calculation
identity. At pressure $P$, static enthalpy is

$$
H=E+PV.
$$

At finite temperature, vibrational or thermodynamic free energies may be added
only when the approximation, reference state, and uncertainty are explicit.
Comparing one relaxed 0 K energy with a finite-temperature free energy is a
protocol mismatch.

## Formation energy

For a structure containing $N_i$ atoms of component $i$, a formation energy per
atom relative to declared reference phases is

$$
\Delta E_f =
\frac{E-\sum_i N_i\mu_i^{\mathrm{ref}}}{\sum_i N_i}.
$$

A per-formula-unit convention is also allowed, but the normalization vector must
be stored. Reference phases, magnetic states, pressure, electronic settings,
and any finite-temperature corrections are part of the result identity.

## Multicomponent convex hull

Each candidate is represented by a normalized composition vector
$\mathbf x=(x_1,\ldots,x_m)$ and a compatible formation energy. The lower convex
envelope in composition--energy space defines stable phases and tie lines (or
higher-dimensional simplices). The energy above the hull is

$$
E_{\mathrm{hull}}(\mathbf x)=
\Delta E_f(\mathbf x)-
\min_{\{\lambda_k\}}
\sum_k \lambda_k\Delta E_{f,k},
$$

subject to $\lambda_k\ge 0$, $\sum_k\lambda_k=1$, and
$\sum_k\lambda_k\mathbf x_k=\mathbf x$. Stable phases have zero energy above
the hull within numerical uncertainty.

The hull result stores:

- component ordering and composition normalization;
- candidate and reference phase identities;
- compatible energy/free-energy convention;
- stable vertices and tie simplices;
- decomposition coefficients for each metastable candidate;
- energy above hull and propagated uncertainty;
- degeneracy/tolerance policy near the hull;
- pressure and temperature when applicable.

Near-hull rankings may be unresolved when uncertainty overlaps the energy above
hull. Such candidates are reported as statistically indistinguishable rather
than deterministically ordered. Pressure-dependent hulls use enthalpy; finite-
temperature hulls use one consistently defined free energy.

## Planned API

```text
energetic.relative_phase_energy
energetic.phase_enthalpy
energetic.formation_energy
energetic.composition_hull
energetic.energy_above_hull
```

# Transport ownership and thermal conductivity

Stress-based viscosity remains in this thermomechanical architecture because the
microscopic observable is the stress tensor and the validity conditions depend
on stress convention, volume, and ensemble. Shared correlation, integration,
blocking, and plateau utilities may be reused from dynamics modules; this does
not create a second generic transport framework. Public transport documentation
should index both displacement/current transport and stress transport.

Thermal conductivity is not owned by the MLFF branch and is not yet implemented
here. A future dynamics/transport architecture must distinguish:

- Green--Kubo heat-current conductivity;
- nonequilibrium imposed-flux methods;
- solid phonon transport and mode-resolved methods;
- convective and conductive contributions in multicomponent liquids;
- heat-current gauge freedom and per-atom-energy ambiguity;
- long-range electrostatic contributions and engine-specific heat fluxes.

No standardized `thermal_conductivity` call should be registered until those
ownership, gauge, and evidence contracts are fixed.

# Standardized observable-call integration

When implemented, each public analysis registers an ID through
`mdstats.analysis.observable_validation`. The registry entry contains:

- owner module and this manual;
- machine-checkable input requirements;
- versioned parameter codec;
- required upstream result bindings;
- result type and API identity.

The MLFF branch may construct matched recipes such as:

```text
reference calculator -> EOS/elastic/phonon result
candidate MLFF        -> same recipe and deformation set
MLFF comparison policy -> differences, uncertainty, pass/degraded/fail
```

The MLFF branch owns the pairing and acceptance policy, not the EOS fit, elastic
regression, force-constant assembly, Green--Kubo integral, surface reference, or
NEB path.

# Implementation sequence

## TE0 - Architecture and common records

Implement calculation-set identities, fit policies, fit diagnostics, uncertainty
records, matched-protocol checks, and standardized API registration scaffolding.
No scientific fit is introduced until these records pass serialization and
tamper tests.

## TE1 - Static EOS and equilibrium state

Implement isotropic deformation generation, energy/pressure ingestion, local
polynomial and Birch--Murnaghan fits, domain diagnostics, uncertainty, and
matched reference/candidate recipes.

## TE2 - Static elasticity and stability

Implement symmetry-aware and unconstrained strain sets, energy--strain and
stress--strain fits, relaxed/clamped internal-coordinate policies, tensor
conversion, eigenvalue stability, and crystal-class readable criteria.

## TE3 - Thermal response

Implement multi-temperature cell curves, thermal-expansion tensors, NPT volume
fluctuation compressibility, energy/enthalpy fluctuation heat capacities, block
uncertainty, and ensemble/stationarity gates.

## TE4 - Stress-correlation viscosity

Reuse common correlation/integration utilities to implement stress correlation,
shear viscosity, plateau evidence, and replica/block uncertainty. Bulk viscosity
is a separate substage after the pressure/energy coupling convention is fixed.

## TE5 - Harmonic phonons

Implement displacement-set generation and identities, force-constant assembly,
sum-rule diagnostics, phonon dispersion/DOS, supercell convergence, and an
optional Phonopy adapter. Quasiharmonic analysis follows only after TE1 and TE5
are qualified.

## TE6 - Surface and interface energetics

Implement slab/interface reference records, area and multiplicity handling,
termination and strain identity, surface energy, interface excess energy, work
of adhesion, and convergence ladders.

## TE7 - Defects and paths

Implement neutral defect formation/binding energies, finite-size ladders, NEB
path identities, path convergence, and migration-barrier extraction. Charged
point-defect electronic corrections remain an explicit external-data extension.

## TE8 - Cross-system qualification

Qualify at least:

1. a cubic crystal EOS and elastic tensor with an analytic or trusted reference;
2. a liquid viscosity synthetic/benchmark trajectory;
3. a harmonic crystal phonon calculation;
4. a converged symmetric surface slab;
5. a coherent interface adhesion calculation;
6. a neutral vacancy and a simple migration path.

Every test must verify source/calculator identity, matched protocols, units,
uncertainty semantics, and fail-closed invalid inputs.

# Failure semantics

The branch distinguishes:

- `invalid_input`: missing fields, inconsistent composition, or malformed units;
- `protocol_mismatch`: reference and candidate calculations are not comparable;
- `underconverged`: grid, supercell, slab, trajectory, or path convergence fails;
- `fit_failure`: rank, condition, residual, or extrapolation gate fails;
- `physically_unstable`: negative curvature, unstable elastic mode, or imaginary
  phonon outside a declared numerical tolerance;
- `insufficient_sampling`: fluctuation/transport uncertainty is unresolved;
- `unsupported_model_physics`: requested electronic charge, magnetic, or
  long-range response is not represented by the calculator/model contract.

A physically unstable result is not a software error. It is a valid scientific
result with a failed stability status.

# Documentation requirements

Every implemented analysis requires:

- theory and equations;
- units and sign conventions;
- input and ensemble requirements;
- numerical method and convergence policy;
- result schema and immutability;
- uncertainty and validity diagnostics;
- synthetic and physical tests;
- standardized API call schema;
- clear ownership and non-responsibilities;
- first-hand or authoritative references.

# References

[1] F. Birch, "Finite Elastic Strain of Cubic Crystals," *Physical Review*
**71**, 809-824 (1947). DOI: 10.1103/PhysRev.71.809.

[2] F. Mouhat and F.-X. Coudert, "Necessary and Sufficient Elastic Stability
Conditions in Various Crystal Systems," *Physical Review B* **90**, 224104
(2014). DOI: 10.1103/PhysRevB.90.224104.

[3] M. Parrinello and A. Rahman, "Strain Fluctuations and Elastic Constants,"
*Journal of Chemical Physics* **76**, 2662-2666 (1982). DOI: 10.1063/1.442722.

[4] M. S. Green, "Markoff Random Processes and the Statistical Mechanics of
Time-Dependent Phenomena. II. Irreversible Processes in Fluids," *Journal of
Chemical Physics* **22**, 398-413 (1954). DOI: 10.1063/1.1740082.

[5] R. Kubo, "Statistical-Mechanical Theory of Irreversible Processes. I,"
*Journal of the Physical Society of Japan* **12**, 570-586 (1957). DOI:
10.1143/JPSJ.12.570.

[6] A. Togo and I. Tanaka, "First Principles Phonon Calculations in Materials
Science," *Scripta Materialia* **108**, 1-5 (2015). DOI:
10.1016/j.scriptamat.2015.07.021.

[7] G. Henkelman, B. P. Uberuaga, and H. Jonsson, "A Climbing Image Nudged
Elastic Band Method for Finding Saddle Points and Minimum Energy Paths,"
*Journal of Chemical Physics* **113**, 9901-9904 (2000). DOI:
10.1063/1.1329672.

[8] M. J. Gillan, "Calculation of the Vacancy Formation Energy in Aluminium,"
*Journal of Physics: Condensed Matter* **1**, 689-711 (1989). DOI:
10.1088/0953-8984/1/4/005.

[9] C. Freysoldt, B. Neugebauer, and J. Van de Walle, "Fully Ab Initio
Finite-Size Corrections for Charged-Defect Supercell Calculations," *Physical
Review Letters* **102**, 016402 (2009). DOI: 10.1103/PhysRevLett.102.016402.

[10] P. Restuccia et al., "High-Throughput First-Principles Prediction of
Interfacial Stability and Adhesion," *ACS Applied Materials & Interfaces*
**15**, 19049-19061 (2023). DOI: 10.1021/acsami.3c00662.
