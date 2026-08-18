---
title: "Part II - Registered Statistical Site Discovery and Kinetic-Network Architecture"
subtitle: "Species-Dependent Evidence, Ensemble Certification, Sampling Confidence, Thermodynamics, Paths, and Deferred Kinetics"
author: "mdstats"
date: "2026-07-27 (architecture revision 57; Stage 11E-GR3 fixed-kernel scientific grid refinement implemented)"
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
    \definecolor{codegray}{RGB}{247,247,247}
    \setlist{nosep}
---

# Purpose and current status

This manual is **Part II** of the Stage 11 architecture. The species-independent
framework, primitive-ring, natural-tiling, tile/cage/window, serrated ring-boundary,
and framework-semantic layers are owned by
`framework_ring_architecture.{md,pdf}` (**Part I**). Part II begins at registered
trajectory evidence. It consumes Part I identities but never recreates or
mutates them.

Architecture revision 57 is the controlling normative contract. The ensemble and quality plan first consolidated in architecture revision 48 remains preserved and is now partially implemented. It preserves the
revision-47 typed dependency and thermodynamic-provenance contract and marks Stage
11E-ENS0 source-control/named-energy reconstruction, 11E-ENS1 control/ensemble certification, 11E-STAT0 ionic-temperature/integrity/quality evaluation, 11E-STAT1 source-observable production-regime identification, 11E-STAT2 ensemble-specific admissibility, 11E-SAMP0 complete-system cross-fit sampling, 11E-GR0 common grid geometry and numerical diagnostics, 11E-GR1 common budgeted planning and deterministic grid ladders, 11E-GR2 plotting adaptation and visual-policy preservation, and 11E-GR3 fixed-kernel scientific grid refinement as implemented. GR4 and all later
GR/SAMP/STAT/THERMO migration stages remain subject to their own specifications and
acceptance tests. It preserves the
event/path/saddle separation and additionally requires source-bound provenance on every
thermodynamic result, treats independent cross-checking as optional verification rather
than a prerequisite for a source-qualified estimate, splits density-derived and
force-integrated PMFs, introduces an independent kinetic fit/validation partition and a
predeclared rate-candidate edge universe, assigns final candidate freezing to GR4, and
replaces the two-field DAG with typed dependency edges and source-identity constraints.

Release chronology, previous architecture revisions, and package-specific implementation
history are maintained only in `stage11_site_kinetics_status_history.{md,pdf}`. They are
descriptive and cannot override this manual, the machine-readable stage DAG, or a signed
scientific acceptance certificate.

Stage 11 connects a certified periodic framework topology to observed mobile-ion
states and, only after validation, to a kinetic model. The revised architecture
adopts one controlling principle:

$$
\boxed{
\begin{gathered}
\text{normalized source trajectory}
\rightarrow
\text{analysis-specific frame registration}
\rightarrow
\text{trajectory evidence}\\
\rightarrow
\text{statistical sites}
\rightarrow
\text{structural interpretation}
\rightarrow
\text{kinetics}
\end{gathered}
}
$$

The framework geometry must not prescribe the physical site catalog. It supplies
stable identities, ring and cage coordinates, periodic translations, and local
geometric descriptors. A new cross-cutting spatial-frame-registration layer
supplies the analysis coordinate system without altering the immutable physical
source trajectory. The mobile-ion trajectory then determines where
species-specific basins occur and whether they are spatially and temporally
metastable.

The following completion list describes the **baseline compatibility behavior** at the
time of this contract. It does not imply complete revision-52 compliance. ENS0, ENS1, STAT0, STAT1, STAT2, and SAMP0 are
implemented; later SAMP certificates, GR migration, revised force products, event-network
branching, typed provenance, kinetic cross-fitting, and downstream thermodynamic records
remain migration work until their own implementation and acceptance tests pass.

The baseline compatibility state contains the structural stack through
Stage 11D, the first three cross-cutting coordinate-registration foundations,
and the atom-resolved structural ring-boundary layer:

- certified natural tiling;
- exact reference tile and window geometry;
- compatible-frame tile geometry;
- persistent T/O ring geometry;
- compatible-frame ring centers, normals, side frames, and breathing descriptors;
- generic tile and ring-interface semantics;
- an explicit LTA semantic profile;
- Stage C0A1 source-field semantics, periodic lattice-basis validation,
  optional explicit unimodular reconciliation, reference-cell definitions, and
  separate geometric/PMF force-admissibility contracts;
- Stage C0A2 immutable fit/analysis metrics, certified triclinic closest-image
  geometry, affine registration, matched periodic framework translation,
  temporal branch lifting, registered coordinate products, and covector-correct
  force transformation;
- Stage 11C3 persistent T/O atom chemistry, exact cyclic structural sequences,
  unweighted cyclic spectra, boundary-measure angular moments, rank-safe
  physical-angle fits, dihedral gauges, and fail-closed LTA oxygen aliases; and
- Stage C0A3 source-bound physical/registered structural views, certified
  transformed periodic atom images, reconstructed registered orthonormal ring
  frames, and optional registered tile, cage, face, and window embeddings.
- Stage C0B source-bound compatibility adapters for displacement, velocity,
  atomic density, framework density, trajectories, and framework plotting, with
  centralized scientific drift ownership and exact legacy regression semantics.
- Stage 11E0a analysis-owned scientific density protocols, zero-copy field
  adapters, canonical atomic/framework preparation facades, and disjoint
  scientific-versus-rendering resource policies, while retaining the current
  numerical fields as explicit compatibility-owned objects.
- Stage 11E0b compact registered species sample catalogs with raw availability and
  geometry masks, segment-aware represented-time weights, topology regimes, lazy
  structural annotations, and optional shared-domain multi-trajectory registration
  groups. Scientific force, ensemble, stationarity, and PMF admissibility are later
  overlay products under the revision-49 migration contract.
- Stage 11E-ENS0 immutable source-bundle identity, explicit/effective VASP control
  reconstruction, non-authoritative user-label diagnostics, exact named frame-energy
  channels, companion-file classification, numerical MD controls, per-step SCF traces,
  strict serialization, and VASP reader metadata integration. Ensemble interpretation
  is Stage 11E-ENS1.
- Stage 11E-ENS1 signed control-inferred dynamics, ensemble, propagator, thermostat,
  barostat, cell-control, bias, constraint, force-provider, initial-velocity, and
  continuation certificates, with missing companion evidence retained as unresolved.
- Stage 11E-STAT0 source-bound equipartition ionic temperature, autocorrelation-aware
  confidence and drift statistics, NVE energy-conservation diagnostics, explicit hard
  integrity versus soft quality checks, and the exact `strictly_qualified`,
  `degraded_quality`, and `unqualified` execution verdicts. Degraded sources continue
  with one warning; only catastrophic integrity failure rejects by default.
- Stage 11E1 source-bound periodic species-density estimation with explicit
  physical/reference-material measures, covariance and analysis-metric
  separation, normalized triclinic Gaussian lattice sums, bounded image
  truncation, density/score/metric-gradient/Hessian fields, local support,
  dense/block realizations, bandwidth ladders, and complete-system block
  uncertainty.
- Stage 11E2 deterministic isolated modes, derivative-supported extended
  ridges, unresolved flat components, support-restricted periodic basin
  ownership, numerically supported density-boundary and saddle candidates, local periodic charts, provisional cores,
  covariance-scale lineage, explicit scale ambiguity, and separate topology
  refinement certificates.
- legacy Stage 11E3 combined local mechanical fits and PMF-oriented force fields;
  the current contract maps mechanical center/stiffness/curvature quantities to E3A and requires
  thermodynamic mean-force, density-score residual, and PMF claims to be recomputed under
  E3B/PMF ensemble, partition, measure, kernel, and support contracts.
- Stage 11E4 immutable raw core/basin/transition/background/unknown
  memberships, segment-aware core visits and preliminary residences, explicit
  jump/excursion/unresolved/censored passages, local decorrelation estimates,
  stride sensitivity, recrossing diagnostics, and separate temporal-support and
  evidence-pattern statuses.
- Stage 11E5 frozen joint-evidence catalogs with orthogonal spatial, temporal,
  force, force-score, stationarity, geometry, curvature, and validation statuses;
  fail-closed registered structural associations; legacy block provenance mapped to
  `EvidenceCrossfitPartition`; conservative symmetry exchangeability; and an explicit
  frozen-versus-refit boundary.
- Stage 11E5a exact state-conditioned physical M--O/M--T sample matrices,
  persistent atom/image identities, direct local ion coordinates, centered-
  reference and geometry-forward diagnostics, exact cyclic and boundary-measure
  spectra, rank-safe actual-angle fits, phase-locking evidence, occupancy-
  conditioned mixtures, and conservative structural classes.
- Stage 11E5b optional one-pass framework-only affine center refinement,
  frozen discovery assignments, model-selection and held-out basin/corridor gates, translated
  nested cores/basins, joint static/dynamic membership, comoving and boundary
  displacement diagnostics, exclusive overlap conflicts, and occupancy bounds.
- Stage 11E6 final core-entry/basin-retention hysteresis, explicit residence,
  excursion, transition, recrossing, gap, conflict, and censoring intervals,
  represented-time residence and occupancy statistics, and threshold/stride
  stability certification.
- Stage 11E6b exact observed registered paths with periodic translations,
  cadence and first-hit resolution, optional structural/force evidence,
  compatible cross-run path ensembles, and diagnostic collective-event context.
- Stage 11E7 an observed periodic network on validated state instances, exact
  structural-versus-observed edge comparison, separate complex/orbit/class
  summaries, compact source-anchor transfer models, and fail-closed held-out or
  external transfer application records.

The explicit manual or transferred-model branch has permanent labels:

| Legacy label in pre-revision documents | Current label | Ownership |
|---|---|---|
| former manual-model `11E1` | `11E-M1` | explicit ring/site model construction |
| former manual-model `11E2` | `11E-M2` | application and assignment of a supplied model |

The legacy labels appear only in this migration table. Normative prose uses `11E-M1`
and `11E-M2`; `11E1` and `11E2` exclusively mean density estimation and numerical
feature discovery.

Stage 11F rate-law work is postponed until the revised Stage 11E discovery,
ensemble, stationarity, sampling-confidence, thermodynamic, and kinetic-adequacy
gates are complete.


Detailed implementation history and release-by-release pilot status are maintained in
`stage11_site_kinetics_status_history.{md,pdf}`. That appendix is descriptive, not
normative. This manual and `stage11_dependency_graph.json` contain the authoritative
current contracts and stage order.

# Authoritative architectural decisions

## Structural identity remains species-independent

The following identities are fixed by the certified framework and natural tiling:

- framework vertex and edge identities;
- primitive-ring keys and ring order;
- natural-tile keys and face signatures;
- the two oriented ring--tile incidences of each window;
- periodic translation labels;
- reference and compatible-frame ring geometry; and
- generic or profile-specific semantic labels.

Changing the mobile species, temperature, loading, force model, clustering
method, or bandwidth must not change these structural identities.

## The atom-resolved ring boundary is authoritative

A ring is not represented scientifically by a circle, ellipse, or smooth aperture
alone. The authoritative object is the persistent ordered sequence of framework
T atoms, bridging oxygen atoms, periodic images, chemical environments, and
instantaneous coordinates. Area, ellipticity, aperture, and harmonic coefficients
are derived summaries.

A geometrically centered ion need not see equivalent ring atoms. In LTA, the
single 6-ring contains alternating O(2) and O(3) sites. Experimental refinements
report three shorter and three longer M--O contacts for centered Na and Ag, and
an analogous three-plus-three pattern for the principal K site [S11-32, S11-33].
The architecture therefore distinguishes geometric centering from coordination
isotropy.

Conventional crystallographic aliases such as O(1), O(2), and O(3) are attached
only by an explicit validated framework profile. Generic ring analysis uses
persistent atom identities and local chemical/topological signatures. A profile
must not force an alias when the input ordering, symmetry, chemistry, or origin
convention is incompatible.

The species-independent structural boundary and species-dependent ion
coordination are separate owners. Stage 11C3 records only framework geometry and
chemistry. Stage 11E5a records M--O/M--T distances and coordination harmonics
after a statistical state has been associated with structural objects.


## No universal canonical frame

`AtomisticFrameCollection` remains the normalized physical source truth. It is
never rewritten into one permanently drift-free or strain-free trajectory. A
pair-distance analysis, a material-frame density, a laboratory-frame current,
and a rotating-frame visualization do not require the same coordinates.

The package therefore defines **spatial frame registration** as an explicit,
analysis-specific view. "Frame canonicalization" is the architectural role; the
public API should emphasize registration because no single canonical frame is
physically correct for all observables.

Every analysis declares its requirements. The registration layer resolves one
policy, records the framewise transforms, and rejects incompatible requests.

## Physical site identity is learned from data

For species $M$, a physical site is not created by ring order, cage type, ionic
radius, or a manually selected offset. It is a trajectory-supported metastable
region. Position and temporal evidence can establish a spatially reproducible,
temporally metastable site. Admissible force evidence raises the certification to
force-validated or fully validated status.

The full evidence channels are:

1. a reproducible local maximum of the species position density;
2. a mechanically restoring local force field with stable local curvature;
3. repeated temporal residence beyond the local vibration timescale; and
4. reproducibility across trajectory blocks, ions, and moderate estimator changes.

A low-population site may still be real. Population and temporal persistence are
reported separately.

## Basin, pathway, and kinetic claims are separate

One trajectory can support different levels of claim. Two reproducible residence
regions may establish two candidate basins. One accepted core-to-core passage
establishes one observed connection. A transition-path ensemble, directional
rate, or Markov model requires substantially more repeated evidence.

The package therefore reports the following separately:

- existence and geometry of each basin;
- spatial and temporal evidence for metastability;
- each observed successful or failed passage;
- whether a transition-path ensemble is resolved;
- whether directional rates are identifiable; and
- whether a Markov, semi-Markov, or gated kinetic model is supported.

A single observed jump is never promoted automatically to a representative
minimum-free-energy path or a rate estimate.

## Position, force, and temporal evidence remain inspectable

The first implementation must not fuse all evidence into one opaque score.
Position-only density, force-only reconstruction, and temporal segmentation are
separate results with shared provenance. Their agreement is a validation result.
Their disagreement is scientifically meaningful and must remain visible.

## Calculation controls, not user labels, define the ensemble

Free-form source labels such as VASP `SYSTEM`, POSCAR comments, filenames,
directory names, or user-provided run descriptions are retained as comments only.
They never define the ensemble, thermostat, barostat, target temperature, bias,
constraint, or production interval. `SimulationControlCertificate` reconstructs the
**control-inferred dynamics mode** from explicit/effective controls and source-format
semantics only. Observed time-series diagnostics never redefine that mode; they produce a
separate `RealizedEnsembleConsistency` and contribute to trajectory quality and
method-specific thermodynamic admissibility.

For VASP, the first implementation must distinguish the compact explicitly supplied
`<incar>` section from the complete effective `<parameters>` section and resolve at
least `IBRION`, `MDALGO`, `SMASS`, `ISIF`, `ANDERSEN_PROB`, `LANGEVIN_GAMMA`,
`LANGEVIN_GAMMA_L`, `PMASS`, `NHC_NCHAINS`, `NHC_PERIOD`, CSVR controls,
multiple-thermostat controls, bias mode, and constraint provenance. The decision
table follows the official VASP ensemble and MD-control documentation
[S11-38--S11-42]. Unknown or internally inconsistent controls fail closed only for claims that require a resolved dynamics mode. Descriptive structural analysis may continue when hard trajectory-integrity checks pass.

A user comment may disagree with the inferred controls without changing the
certificate. Such a disagreement is recorded explicitly as
`user_label_conflicts_with_controls`.

## Canonical reduced landscapes are PMFs, not microscopic potential-energy surfaces

For a coarse coordinate $\mathbf q$, the equilibrium one-body probability density
for species $M$ defines the potential of mean force

$$
A_M(\mathbf q)
=
-k_{\mathrm B}T\ln p_M(\mathbf q)+C.
$$

The remaining framework and mobile-ion coordinates have been integrated out.
The result is therefore a free-energy landscape conditional on the selected
ensemble, composition, loading, temperature, and coordinate definition. It must
not be labeled the microscopic potential-energy surface.

## PMF interpretation is ensemble-specific

The canonical identity

$$
A_T(\mathbf q)=-k_{\mathrm B}T\ln p_T(\mathbf q)+C
$$

requires a stationary canonical distribution or a justified reweighted equivalent.
A stationary microcanonical trajectory instead defines an energy-shell conditional
distribution. It may support a microcanonical occupancy landscape directly and may
approximate a canonical subsystem PMF only under an explicit finite-bath or ensemble-
equivalence policy. NVE, NVT, NpT, biased, constrained, and mixed-thermostat data
therefore have different admissibility contracts.

The package must keep these products distinct:

```text
position_density
microcanonical_occupancy_distribution
canonical_probability_density
canonical_PMF
reweighted_PMF
force_integrated_PMF
```

No stage silently converts an NVE density into a canonical PMF by inserting a mean
kinetic temperature.

## No scientific claim outside sampled support

Density, force, PMF, and basin results are valid only where sampling support is
adequate. Sparse interpolation may connect sampled values numerically, but it
must not create a physical site or barrier in an unsampled region.

Every field result must retain a support mask, local sample count or effective
sample size, and uncertainty diagnostic.

## Every MD-derived catalog is sampling-scoped and partial

A finite trajectory can certify only features supported on its observed timescale,
temperature, composition, loading, and sampling protocol. Even a long machine-
learned-force-field trajectory cannot prove that all higher-barrier basins and
saddles have been found. The default catalog-level claim is therefore
`observed_partial_catalog`, never `complete_site_network`.

Numerical maxima, ridges, basin boundaries, and saddle cells are candidates. A
physical feature is reported only after effective independent sample counts,
independent blocks or replicas, bootstrap recurrence, uncertainty, and held-out
support pass a declared policy. Transition frames from one crossing remain one
independent event regardless of how many stored frames resolve that crossing.

Unsupported features are rejected or retained as ambiguous. Absence of an event is
reported as raw event/exposure/censoring evidence. A rate bound is produced only
under a signed Stage 11F0 `RateBoundModel`, never as an automatic SAMP result.

## Manual site models remain optional

The existing manual profile branch is retained as an explicit alternative:

```text
manual or transferred site model
    -> explicit geometric basins
    -> framewise assignment
    -> observed statistics
```

Its output must state that site locations and basin definitions were supplied,
not discovered. Manual and learned catalogs may be compared or matched, but
must never be silently merged.

# Part I structural dependency contract

Part II requires a certified Part I structural product set. The minimum contract
contains:

- immutable framework vertex/edge identities and periodic translations;
- source-bound primitive-ring keys and ordered atom-resolved T/O boundaries;
- certified natural-tile, face, window, cage, and adjacency identities when
  available;
- reference and compatible-frame ring geometry with centers, normals, side
  frames, planarity, breathing, and serrated-boundary descriptors;
- framework semantic labels and explicit profile provenance; and
- digests that prove every registered structural view derives from the same
  framework/topology catalog.

Part II may use these products to interpret a statistical state. It must not:

- replace an ordered oxygen polygon by a circle or ellipse;
- convert a ring side, cage, or window directly into a physical site;
- infer a transition from structural adjacency alone;
- merge states solely because they share a structural label; or
- modify Part I identity in response to species, temperature, loading,
  bandwidth, or clustering choices.

Detailed structural mathematics, implementation stages 11A-D, and the remaining
general-topology roadmap are normative only in Part I.

# Stage C0 - Spatial frame registration and coordinate canonicalization

Stage C0 is a cross-cutting prerequisite placed after source normalization and
before analysis-specific coordinate preparation:

```text
raw I/O
    -> unit, atom-order, box-origin, and periodic-unwrapping normalization
    -> immutable AtomisticFrameCollection
    -> Stage C0 spatial frame registration
    -> analysis-specific registered view
    -> scientific analysis or plotting
```

Source normalization and frame registration are distinct. Normalization records
what the source trajectory physically contains. Registration chooses how one
analysis observes that trajectory.

## Affine registration contract

Use the package row-vector convention. Let

$$
\mathbf x_{i,t}=\mathbf f_{i,t}H_t
$$

be an origin-relative Cartesian coordinate in the normalized source collection.
A framewise affine registration is

$$
\boxed{
\mathbf q_{i,t}=\mathbf x_{i,t}M_t+\mathbf b_t
}
$$

with registered cell

$$
\boxed{
G_t=H_tM_t.
}
$$

Positions and cells must always be transformed together. A periodic analysis may
use a fixed periodic domain only when the resolved $G_t$ is constant within the
declared tolerance.

For a reference group with continuously gauged center $\mathbf c_t$, choose

$$
\mathbf b_t
=
\mathbf c_{\mathrm{ref}}-\mathbf c_tM_t,
$$

so that

$$
\mathbf q_{i,t}
=
(\mathbf x_{i,t}-\mathbf c_t)M_t+\mathbf c_{\mathrm{ref}}.
$$

Reference centers may be centers of geometry, centers of mass, persistent
anchors, or explicitly supplied trajectories. Their atom identities and periodic
gauges are part of the registration signature. The framewise center $\mathbf c_t$
is always represented as a continuously unwrapped, origin-relative Cartesian row
vector in the source frame before application of $M_t$. The target
$\mathbf c_{\mathrm{ref}}$ is a Cartesian row vector in the registered domain.
A fractional reference-center input is converted through its declared source or
reference cell before the affine map is assembled; the coordinate convention is
never inferred implicitly.

## Periodic lattice-basis gauge and registered products

The reference-material map assumes that the reported lattice basis has a
continuous identity. Cells related by

$$
H_t'=U_tH_t,
\qquad
U_t\in GL(3,\mathbb Z),
$$

describe the same lattice under a different integer basis. Stage C0 therefore
checks cell handedness, determinant sign, periodic-axis consistency, and basis
continuity before constructing $M_t$.

The first implementation may reject a basis change instead of solving the full
lattice-matching problem, but it must never interpret a silent basis relabeling
as physical strain or rotation. Later implementations may reconcile admissible
unimodular changes and retain the integer gauge $U_t$ in provenance.

Every registration result exposes four distinct products:

```text
registered_unwrapped_cartesian
registered_wrapped_fractional
registered_image_shifts
registered_cell
```

Unwrapped coordinates preserve continuous framework centers and ion paths.
Wrapped fractional coordinates define periodic density samples. Image shifts
preserve lattice translations of observed hopping events. Wrapping is performed
only after registration and never discards the unwrapped path or image labels.

The source collection also records, where known:

```text
position_frame
velocity_frame
force_frame
box_origin_frame
```

Unknown source-frame semantics prevent exact transformed-velocity or PMF claims.

## Reference-cell selection and initial periodic scope

Every reference-material registration owns an immutable
`ReferenceCellDefinition`. The first implementation supports only:

```text
explicit_matrix
    a caller-supplied full-rank reference cell

selected_source_frame
    the gauge-validated cell of one declared source frame
```

The result records the source kind, selected frame when applicable, basis gauge,
periodic axes, handedness, cell digest, and tolerances. A reference structure or a
gauge-reconciled weighted mean cell may be added later, but a mean is not formed
until basis continuity, common handedness, and compatible periodic axes have been
proved.

The first `reference_material` implementation supports fully periodic, full-rank
three-dimensional cells only. Partial periodicity, singular embedding cells, and
changes in periodic-axis identity fail closed until a dedicated mixed
periodic/nonperiodic specification exists. Identity and translation-only
registration may still be used by analyses whose own contracts support partial
periodicity.

## Registration policies

The first implementation supports three authoritative policies.

### `physical`

$$
M_t=I,
\qquad
\mathbf b_t=\mathbf 0,
\qquad
G_t=H_t.
$$

This is the normalized physical trajectory. It is the default for pair distances,
coordination, bond geometry, topology reconstruction, and laboratory-frame
transport.

### `translation_registered`

$$
M_t=I,
\qquad
\mathbf b_t=\mathbf c_{\mathrm{ref}}-\mathbf c_t.
$$

This removes uniform drift while retaining the instantaneous physical cell,
shape, orientation, and metric. It is appropriate for fixed-cell density and
framework-relative trajectories when only translational drift is artificial.

### `reference_material`

For an invertible, fully periodic cell,

$$
M_t=H_t^{-1}H_{\mathrm{ref}},
\qquad
G_t=H_{\mathrm{ref}}.
$$

Cell mapping and translation registration are orthogonal policy components. With
a continuously gauged framework center, the composed map is

$$
\boxed{
\mathbf q_{i,t}
=
(\mathbf x_{i,t}-\mathbf c_t)
H_t^{-1}H_{\mathrm{ref}}
+\mathbf c_{\mathrm{ref}}
}.
$$

Equivalently, if $\mathbf c_t^{(\mathrm{frac})}=\mathbf c_tH_t^{-1}$,

$$
\mathbf q_{i,t}
=
(\mathbf f_{i,t}-\mathbf c_t^{(\mathrm{frac})})H_{\mathrm{ref}}
+\mathbf c_{\mathrm{ref}}.
$$

When `translation_mode="none"`, $\mathbf c_t=\mathbf0$ and
$\mathbf c_{\mathrm{ref}}=\mathbf0$, recovering
$\mathbf q_{i,t}=\mathbf f_{i,t}H_{\mathrm{ref}}$. The default variable-cell
site-discovery policy uses reference-material cell mapping together with a
framework translation gauge, not the translation-free shorthand.

This maps every frame to one fixed periodic reference torus and removes affine
cell rotation, isotropic breathing, anisotropic stretch, and shear while also
removing only the explicitly selected uniform reference-group translation. It
preserves fractional/material internal motion. It is not used for physical RDFs
or bond-length distributions.

### Periodic reference-translation gauge

A framework center is not formed by averaging arbitrarily wrapped atom positions.
After the declared cell map has placed frame $t$ in the registered domain, let
$\widetilde{\mathbf q}_{j,t}$ denote the pre-translation coordinates of the
persistent reference atoms and let $\mathbf q_{j,\mathrm{ref}}$ denote their
reference coordinates. The translation gauge is the torus displacement

$$
\boldsymbol\tau_t
=
\operatorname*{argmin}_{\boldsymbol\tau\in\mathbb T_G^3}
\sum_{j\in\mathcal R}w_j
\left\|
\operatorname{MIC}_{G,R}
\left(
\widetilde{\mathbf q}_{j,t}
-
\mathbf q_{j,\mathrm{ref}}
-
\boldsymbol\tau
\right)
\right\|_R^2,
$$

where $\mathcal R$ is a constant persistent reference set, $w_j$ gives the COG,
COM, or caller-declared weighting, and $R$ is a positive-definite
`RegistrationFitMetric`. The affine translation is
$\mathbf b_t=-\boldsymbol\tau_t$ up to the declared reference-origin convention.
The solver retains the selected torus branch, residual RMS and maximum, branch
separation, and ambiguity status. A branch is rejected when competing translations
are indistinguishable within tolerance or the residuals show that one uniform
translation is inadequate.

The registration metric has its own coordinate frame, units, transformation law,
and digest. Under $\mathbf q'=\mathbf qA$, the same fitting geometry transforms as

$$
R'=A^{-1}RA^{-\mathsf T}.
$$

Its default is ordinary Euclidean distance in the registered Cartesian domain. It is not inherited from the downstream `AnalysisGeometryMetric`; an
anisotropic transport or basin metric must not change the fitted framework origin.
A caller may deliberately equate the two metrics only through an explicit policy.

This `ReferenceTranslationGauge` is invariant to a common relabeling of periodic
images. It also prevents a deforming cell from converting arbitrary per-atom image
offsets into fictitious Cartesian drift. COG and COM are weighting policies for
the matched-displacement problem, not independent wrapped-coordinate averages.

### Temporally continuous translation-branch lift

The torus solution is defined only modulo the registered lattice:

$$
\boldsymbol\tau_t^{(\mathrm{lift})}
=
\boldsymbol\tau_t+\mathbf n_tG,
\qquad
\mathbf n_t\in\mathbb Z^3.
$$

For every continuous trajectory segment, Stage C0 chooses the integer sequence
$\mathbf n_t$ jointly or sequentially using temporal continuity, matched-framework
residuals, and a declared branch-separation tolerance. The result retains:

```text
torus translation per frame
temporally lifted translation per frame
integer lattice-branch sequence
continuity residual and competing-branch separation
branch ambiguity and segment reset points
```

A branch jump is never selected only because wrapped positions are unchanged. An
ambiguous lift fails closed for registered unwrapped trajectories, finite-difference
velocities, and transition lattice translations. Independent ensemble frames have
no invented temporal lift; each receives only its torus representative and ambiguity
status. Restart, missing-frame, topology-regime, and declared discontinuity boundaries
reset the lift.

Later policies may remove only the rotational part of cell motion, only isotropic
breathing, or perform a nonperiodic rigid-body Procrustes fit. They require
separate specifications and are not part of the first Stage C0 implementation.

## Positions, displacements, forces, and velocities

Different physical fields transform differently.

For a same-frame geometric displacement,

$$
\Delta\mathbf q=\Delta\mathbf xM_t.
$$

Work invariance requires the force covector transformation

$$
\boxed{
\mathbf F_q=\mathbf F_xM_t^{-\mathsf T}
}
$$

for an externally defined affine map. Treating force as an ordinary displacement
vector is incorrect for a nonorthogonal transformation.

For a time-dependent transform,

$$
\mathbf q=\mathbf xM+\mathbf b,
$$

the exact registered velocity is

$$
\boxed{
\dot{\mathbf q}
=
\dot{\mathbf x}M
+
\mathbf x\dot M
+
\dot{\mathbf b}.
}
$$

Translation-only drift subtraction is exact when $M_t=I$. A rotating or deforming
frame requires $\dot M_t$ and its convective term. VACF and current analyses must
not inherit a position-registration policy silently.

## Externally defined and structure-fitted maps

The result distinguishes externally defined affine maps from transforms fitted to
instantaneous structure.

Examples of externally defined maps are the instantaneous-cell to reference-cell
map and a user-supplied rigid transform. Their position and force rules are
explicit.

Examples of structure-fitted maps are framework Procrustes rotation, dynamic ring
frames, and cage-local frames. They are valid geometric coordinates. However, a
naively rotated mobile-ion force is not automatically the exact generalized mean
force after the fitted framework degrees of freedom are marginalized.

Every transformed force carries a geometric transformation status:

```text
exact_external_affine_covector
exact_translation_relative_to_disjoint_reference_group
diagnostic_structure_fitted_projection
generalized_force_unavailable
```

This status answers only whether the vector or covector transformation is
geometrically valid. A separate PMF-force status records whether the transformed
force is admissible as a thermodynamic conditional mean force:

```text
pmf_force_admissible
pmf_force_inadmissible_variable_cell_measure
pmf_force_inadmissible_structure_fitted_map
pmf_force_inadmissible_untracked_bias_or_constraint
pmf_force_provenance_unknown
```

`exact_translation_relative_to_disjoint_reference_group` additionally requires
that translation is the sole fitted transform, the mobile atom is excluded from a
constant reference group, and no untracked constraint, bias, thermostat, or
stochastic force contributes. Geometric exactness never upgrades PMF
admissibility automatically.

The first force-supported site-discovery implementation permits
`LocalMechanicalForceRefinement` for fixed-cell physical or translation-registered
coordinates when geometric transformation and conservative-force provenance pass.
`ThermodynamicMeanForceCertificate` additionally requires a canonical/reweighted
measure or separately implemented microcanonical/subsystem theory. Reference-material
positions under a variable cell remain valid for density discovery, but their
transformed forces are thermodynamically inadmissible until the ensemble measure,
Jacobian, and cell-fluctuation terms are derived. Dynamic ring-frame forces remain
diagnostic until their generalized-force measure is derived.

## Analysis requirement profiles

The registration service provides one implementation but no universal default.

| Analysis | Default spatial policy |
|---|---|
| RDF, coordination, physical pair distances | `physical` |
| Bond angles and neighbor topology | `physical` plus topology gauge |
| Laboratory MSD | `physical`, optional translation drift |
| Material-frame MSD under variable cell | `reference_material` |
| VACF | native velocity frame; optional exact translation subtraction |
| Charge current and conductivity | native laboratory frame unless explicitly redefined |
| Atomic density, fixed cell | `translation_registered` |
| Atomic density, variable cell | `reference_material` |
| Data-driven site discovery | `translation_registered` for fixed cell; `reference_material` for variable cell |
| Tile and ring geometry | physical topology gauge plus local structural frames |
| Interactive plotting | consume the registration chosen by the scientific field |

The service rejects physically inconsistent requests, including a
reference-affine RDF without an explicit strain-normalized-distance contract, a
rotating-frame VACF without transform derivatives, or periodic KDE after an
arbitrary rotation that does not yield one fixed registered cell.

## Registration result and diagnostics

A provisional public interface is

```python
registration = prepare_frame_registration(
    collection,
    policy=FrameRegistrationPolicy(
        cell_mode="reference_affine",
        translation_mode="center_of_geometry",
        reference_atom_indices=framework_indices,
        reference_frame=0,
        periodic_domain="fixed_reference_cell",
    ),
)
```

The immutable result retains:

```text
source normalization and source digest
reference frame and reference atoms
translation, cell, and rotation modes
framewise M_t and b_t
source and registered cells
centers and periodic gauges
reference-translation branch, residual, and ambiguity diagnostics
analysis geometry metric and certified MIC semantics
determinant and condition number
cell deformation diagnostics
fit RMS and maximum residual when fitted
geometric force-transform and PMF-force admissibility semantics
velocity transformation semantics
reference-cell definition and periodic-scope compatibility
per-frame status and failure reason
```

It fails closed for singular cells, empty references, unresolved periodic gauges,
rank-deficient rigid fits, incompatible fixed-domain requests, and unavailable
transform derivatives for exact velocity output.

## Multi-trajectory registration groups

Pooling independent trajectories requires one explicit `FrameRegistrationGroup`.
It verifies common framework topology and atom correspondence, periodic axes,
lattice-basis gauge, chemistry and loading, reference cell, origin convention,
and registration semantics. Each member retains its own transform series and
signature, but all registered samples inhabit one declared periodic domain.
Independent runs are never pooled by matching filenames or approximate cell
lengths alone.

## Registered structural geometry view

Site discovery and ring interpretation may use different coordinate measures.
The Stage C0 service therefore provides a source-bound
`RegisteredStructuralGeometryView` for persistent T/O atoms, tile and cage
centers, ring centers, and their periodic images.

The same framewise affine map used for mobile-ion positions is applied to the
structural atom coordinates. Under a non-rigid affine map, the registered ring
center, normal, and local basis are reconstructed from the transformed T/O
coordinates. The implementation must not obtain a registered orthonormal frame
by merely multiplying the physical frame axes by $M_t$.

Both representations remain available:

```text
physical_structural_geometry
    actual Cartesian bond lengths, apertures, and M-O/M-T coordination

registered_structural_embedding
    site association, density-space displacement, and registered classification
```

A discovered density attractor and its candidate ring or cage are compared only
inside one declared registered view. Physical distances and chemical
coordination are then evaluated in the physical structural geometry with the
same persistent atom and frame identities.

The registered view records the registration signature, source structural
digest, transformed atom images, reconstructed local frames, and any failure of
periodic or orientation continuity.

## Initial Stage C0 implementation boundary

The first Stage C0 implementation provides:

1. identity/physical registration;
2. center-of-geometry and center-of-mass translation registration;
3. full reference-cell affine registration composed with an optional explicit
   translation gauge;
4. explicit-matrix or selected-frame reference-cell definitions;
5. registered positions, cells, displacements, geometric force covectors, and
   structural views;
6. separate geometric-force and PMF-force admissibility statuses;
7. immutable signatures, diagnostics, and round-trip checks;
8. compatibility adapters for current MSD and atomic-density behavior.

Reference-material registration is initially restricted to fully periodic,
full-rank three-dimensional cells.

It does not initially implement arbitrary framework Procrustes rotation,
rotation-only cell correction, isotropic-breathing-only correction, or exact
rotating/deforming-frame velocities.

# Discovery coordinate policy and evidence catalog

## Default site-discovery coordinates

The initial site-discovery coordinate must inhabit one fixed periodic domain.
For a fixed cell, use framework translation registration without an arbitrary
global Procrustes rotation. For a variable cell, use the composed `reference_material` cell map and
framework-translation gauge in $H_{\mathrm{ref}}$ for position-density discovery. Variable-cell force
PMF certification remains disabled until the ensemble measure, Jacobian, and
cell-fluctuation weighting are specified in a dedicated force-coordinate
contract.

An arbitrary frame-dependent rigid rotation changes the periodic lattice to
$Q_t^{\mathsf T}H_t$ and cannot be combined into one periodic KDE unless the cell
is transformed consistently and the resulting domain is explicitly reconciled.
The previous global rigid-alignment proposal is therefore not the default
periodic discovery coordinate.

After global sites are discovered, Stage 11C ring and cage frames provide local
coordinates for interpretation. Full orthonormal $(u,v,z)$ coordinates preserve
the mobile-ion volume measure for a fixed structural identity. Reduced polar
coordinates such as $(z,\rho,\theta)$ require the corresponding Jacobian and are
not the initial discovery measure.

## Evidence masks and admissibility overlays

The immutable E0b catalog owns raw availability and geometry masks only:

```text
raw_position_available_mask
raw_force_available_mask
raw_time_available_mask
registration_valid_mask
structural_geometry_mask
topology_compatible_mask
connectivity_flicker_mask
```

Scientific admissibility is attached later through an immutable
`EvidenceAdmissibilityOverlay` that references the E0b signature and the exact
`SimulationControlCertificate`, `ProductionRegimeCatalog`, and
`PmfAdmissibilityCertificate` used to construct it:

```text
position_analysis_mask
force_analysis_mask
joint_position_force_mask
temporal_analysis_mask
canonical_pmf_mask
microcanonical_analysis_mask
reweighted_analysis_mask
```

E0b does not infer equilibrium, stationarity, production windows, PMF temperature,
or thermostat/constraint admissibility. An unresolved certificate produces an
unresolved overlay; it never causes an assumption to be embedded in the raw catalog.
Density-force consistency uses the exact joint admissible subset, kernel metric,
covariance scale, weights, and coordinate transformation recorded by the overlay.

## Topology-regime segmentation

The sample catalog separates changes in framework connectivity from ordinary
ring breathing and cutoff flicker. Every frame carries:

```text
topology_regime_id
topology_compatible_mask
connectivity_flicker_mask
structural_phase_status
```

The initial data-driven site catalog requires one compatible framework-topology
regime. Frames with unresolved transient connectivity may remain available for
position-only analyses only when the selected topology regime and registration
remain unambiguous; genuinely distinct structural phases are never pooled into
one density or PMF. Later workflows may build separate site catalogs per regime.

## Source trajectory bundle identity

Every source-derived record is bound to one immutable `SourceTrajectoryBundleIdentity`.
The identity covers the normalized primary trajectory bytes, coordinate payload, atom
identity/order, frame/time axis, companion-control manifest, source-program/version, and
any restart lineage that is included in the analysis. `SOURCE_BYTES` and
`SOURCE_COORDINATES` are views of this one bundle, not independent roots.

ENS0 and C0 each retain the same bundle signature. Combining controls from one run with
coordinates from another is a hard source-integrity failure even when atom counts and
cell dimensions happen to match. Derived records carry both their immediate parent
signatures and the shared bundle identity so that source mixing is machine-detectable.

## Source-control reconstruction and ensemble certificate

The source-general architecture is owned by:

```text
SimulationControlBundleManifest
SimulationRunControls
SimulationControlCertificate
RealizedEnsembleConsistency
EnsembleInferencePolicy
```

A source adapter, such as `VaspRunControls`, implements `SimulationRunControls` and
records a versioned control-semantics identifier. Inference is therefore reproducible
against the source program and version rather than against an unversioned decision
table.

`SimulationControlBundleManifest` records every relevant primary or companion input
with one of:

```text
present_and_bound
known_absent
not_applicable
not_provided
required_missing
```

Absence proves nonuse only when source semantics make the file or tag optional and the
bound primary controls explicitly disable the corresponding feature. Otherwise the
result remains `not_provided` or `required_missing`; missing `ICONST`, `REPORT`, hills,
or bias metadata is never silently interpreted as proof that constraints or bias were
absent.

For VASP the reconstruction owns:

```text
explicit_incar_controls
effective_parameter_controls
user_comment
program_and_version
control_semantics_version
control_source_precedence
ensemble_decision_trace
thermostat_certificate
barostat_certificate
bias_and_constraint_certificate
initial_velocity_provenance
continuation_provenance
numerical_md_quality_controls
per_step_electronic_convergence_trace
```

The VASP adapter must parse both the explicitly supplied `<incar>` values and the
complete effective `<parameters>` values from `vasprun.xml`, preserving source
precedence and original tag names. It must also parse per-ionic-step electronic-step
counts and convergence outcomes wherever the XML contains them. The initial numerical
MD quality-control record includes at least:

```text
POTIM
NSW_and_present_ionic_step_count
output_cadence
EDIFF
NELM
NELMIN
ALGO_or_IALGO
PREC
LREAL
ROPT
ENCUT
ISYM
per_step_SCF_iteration_count
per_step_SCF_convergence_status
position_cell_force_energy_completeness
restart_and_initial_velocity_provenance
```

These controls do not redefine the ensemble. They explain expected numerical quality
and provide evidence for later conservation and integrity verdicts. The parser retains
unknown or source-version-specific values rather than forcing them into an unsupported
category. The official VASP output and control documentation establishes that
`vasprun.xml` contains effective calculation parameters and that timestep, SCF
convergence, and force-evaluation settings are relevant to MD stability and NVE energy
conservation [S11-39, S11-40, S11-50--S11-54].

The initial resolver covers at least `MDALGO`, `SMASS`, `ISIF`,
`ANDERSEN_PROB`, `LANGEVIN_GAMMA`, `LANGEVIN_GAMMA_L`, `PMASS`,
`NHC_NCHAINS`, `NHC_PERIOD`, CSVR controls, multiple-thermostat controls,
and source-bound bias/constraint controls. The VASP rules are taken from the official
control documentation [S11-38--S11-42].

The source-level decision uses canonical diagnostic status plus a domain outcome:

```text
diagnostic_status = resolved | unresolved | insufficient | rejected |
                    unavailable | not_applicable
ensemble_outcome  = NVE | NVT | NpT | NpH | driven | mixed_or_partial |
                    unsupported_variant | inconsistent_controls
```

`SYSTEM`, filenames, directory names, and user descriptions are retained only as
comments and conflict diagnostics.

## Energy reconstruction, conservation, stationarity, and production regimes

Exact source-level energy reconstruction precedes conservation analysis. A
`FrameEnergyCatalog` records every named electronic, ionic kinetic, thermostat,
barostat, lattice, bias, constraint, and reported-total channel with source name,
units, completeness, and the source-specific conserved-quantity identity. A generic
`energy` field is never sufficient.

### Ionic-temperature reconstruction

Ionic temperature is reconstructed from the source-bound ionic kinetic energy using the
equipartition theorem:

$$
T_t=\frac{2K_{\mathrm{ion}}(t)}{f_{\mathrm{ion}}k_{\mathrm B}},
$$

where $f_{\mathrm{ion}}$ is the active quadratic ionic velocity degree-of-freedom
count for that source. The definition remains simple and explicit: fixed coordinates,
affirmatively known holonomic constraints, and an affirmatively removed center-of-mass
mode reduce $f_{\mathrm{ion}}$; no degree of freedom is removed merely because the
trajectory happens to have small momentum. Variable-cell kinetic terms remain separate
from ionic kinetic temperature. VASP's documented periodic-system example uses
$f_{\mathrm{ion}}=3N-3$ when center-of-mass translation is excluded; the adapter must
reconstruct rather than assume that convention [S11-55].

A signed `IonicTemperatureDefinition` records the kinetic-energy channel, masses,
active-coordinate mask, constraint evidence, center-of-mass convention, and resulting
$f_{\mathrm{ion}}$. A signed `IonicTemperatureStatistics` records at least:

```text
frame_temperature_series
represented_time_weighted_mean
represented_time_weighted_standard_deviation
minimum_and_maximum
integrated_autocorrelation_time
effective_sample_count
block_means
mean_standard_error_and_confidence_interval
drift_slope_and_confidence_interval
stationarity_outcome
target_temperature_comparison_if_applicable
```

The standard deviation describes physical temperature fluctuation; confidence in the
mean is computed from complete-system block or autocorrelation-aware uncertainty and is
never obtained by treating adjacent frames as independent. For NVT/NpT the statistics
may be compared with an authoritative target temperature. For NVE/NpH there is no
active temperature target; the code evaluates temporal stability of the reconstructed
temperature instead of demanding equality to a historical label.

### Three-level trajectory-quality verdict

Trajectory quality is aggregated from two disjoint classes of checks:

```text
hard_integrity_checks
soft_numerical_quality_checks
```

The signed `TrajectoryQualityVerdict` has exactly three top-level outcomes:

```text
strictly_qualified
degraded_quality
unqualified
```

`strictly_qualified` means every required integrity check passes, the source controls
meet the active policy, the relevant conserved or controlled quantities pass, and no
material numerical-quality issue is detected.

`degraded_quality` means the trajectory remains finite, structurally valid, and
quantitatively usable, but one or more noncatastrophic quality checks fail or remain
marginal. Examples include measurable but bounded NVE energy drift, a manageable
temperature trend, looser-than-preferred SCF convergence, real-space projection or a
timestep that produces detectable integration error, or absence of a channel that is
verdict-critical or required by the requested method. A genuinely optional,
method-irrelevant channel is recorded as `unavailable` and does not degrade the trajectory.
A degraded trajectory proceeds through downstream analysis. The public API
emits one `TrajectoryDegradedQualityWarning`, and every result carries the exact verdict,
failed checks, effect estimates, and uncertainty/provenance flags.

`unqualified` is reserved for catastrophic trajectory-integrity failure, including
nonfinite or divergent energies/forces/positions, singular or inverted cells, broken
atom identity, unexpected internal frame loss or nonmonotonic time, missing mandatory
coordinates/cells, physically impossible atomic overlap under a species-aware hard
integrity policy, or runaway displacement/velocity/force behavior. Production
scientific APIs raise `TrajectoryIntegrityError` for this outcome. A diagnostic-only
parse mode may return the failure certificate for inspection, but it cannot silently
continue into scientific analysis.

The aggregation rule is deterministic:

```text
any hard integrity failure -> unqualified
else any soft failure or material warning -> degraded_quality
else -> strictly_qualified
```

The quality verdict controls execution rejection only. It does not replace
ensemble-specific scientific admissibility. For example, a degraded NVE trajectory may
still yield descriptive density and occupancy statistics, while a canonical-PMF method
may independently remain unavailable because the source is not canonical.

The diagnostic stage is governed by persistent `TrajectoryQualityPolicy` and
`ProductionWindowPolicy` records. Their first implementation must contain at least:

```text
primary_observables
physical_time_units
autocorrelation_estimator
minimum_independent_blocks
block_length_rule
drift_normalization
trend_significance_threshold
change_point_method_and_penalty
cell_and_stress_tolerances
energy_conservation_tolerance
ionic_temperature_confidence_level
ionic_temperature_mean_tolerance_if_targeted
ionic_temperature_drift_tolerance
hard_integrity_thresholds
soft_quality_thresholds
warning_emission_policy
unqualified_error_policy
selection_validation_partition
short_trajectory_behavior
```

The default block length is the maximum declared minimum duration and twice the
largest accepted integrated autocorrelation time among the primary source
observables. Acceptance requires at least the policy's minimum number of independent
complete-system blocks; fewer blocks yield `insufficient`, never relaxed thresholds.
Correlated uncertainty and block resampling follow stationary-sequence methods
[S11-36, S11-37, S11-46]. A configured change-point method, initially PELT with a
persisted cost and penalty, records all selected boundaries and uncertainty rather
than presenting a silent visual choice [S11-47].

For observable $x(t)$, drift diagnostics include both the uncertainty-normalized
slope and the observation-span change normalized by the block-scale fluctuation:

$$
Z_{\dot x}=\frac{|\widehat{\dot x}|}{\operatorname{SE}(\widehat{\dot x})},
\qquad
D_x=\frac{|\widehat{\dot x}|T_{\mathrm{obs}}}
{\max(\widehat\sigma_{x,\mathrm{block}},\sigma_{x,\mathrm{floor}})}.
$$

Thresholds are policy values, not hidden constants. NVT, NVE, NpT, NpH, driven, and
biased runs select different primary conserved or controlled quantities. A smooth but
statistically significant NVE drift is not hidden by small detrended residuals.

`11E-STAT1` uses only source-level or predeclared low-complexity observables: energy,
temperature, cell, stress, momentum, framework RMS descriptors, and other diagnostics
whose definitions are fixed before site discovery. It does not use the adaptive E1
site density to select a production interval.

`TrajectoryQualityVerdict` is trajectory-wide or source-segment-wide and records
whether analysis may execute. `ProductionRegimeCatalog` is finer-grained and records
which contiguous portions support particular interpretations. A degraded trajectory
may contain one or more usable production regimes. An unqualified trajectory has no
scientific production regime.

The result is a `ProductionRegimeCatalog`, not one Boolean stationarity label. Each
contiguous regime records:

```text
thermalization_status
stationarity_status
energy_conservation_status
ensemble_consistency_status
production_interval_status
selection_conditioning_status
thermodynamic_admissibility_status
```

Externally proven continuation boundaries are tested preferentially. When the same
trajectory must be used to select and analyze a regime, discovery and validation
blocks or nested resampling are mandatory, and downstream uncertainty is labeled
`selection_conditioned`. Multiple stationary regimes remain separate datasets.

After E1 candidate density exists, optional `11E-STAT3` evaluates held-out
blockwise distribution stability. It may reject or condition a thermodynamic
interpretation, but it cannot retroactively tune the production window using the same
blocks that support the reported occupancy.

## Ensemble-aware statistical-mechanical contract

Every landscape declares a `ThermodynamicPotentialDefinition` and a
`ThermodynamicStateDefinition`. No equation is ensemble-general by default.

For stationary canonical NVT data or a certified reweighted canonical equivalent,
restricted-state probabilities determine Helmholtz free-energy differences:

$$
\Delta A_{ij}=-k_{\mathrm B}T
\ln\frac{P_i/g_i}{P_j/g_j}.
$$

For stationary isothermal-isobaric NpT data, the analogous probability ratio defines
Gibbs free-energy differences $\Delta G_{ij}$; energetic decomposition uses
conditional enthalpy and explicit $pV$ treatment rather than silently reusing an NVT
potential-energy formula.

For stationary microcanonical NVE data at energy shell $E$,

$$
P_i(E)=\frac{\Omega_i(E)}{\sum_j\Omega_j(E)},
\qquad
\Delta S_{ij}(E)=k_{\mathrm B}\ln
\frac{P_i(E)/g_i}{P_j(E)/g_j}.
$$

A canonical subsystem approximation is a separate conditional result requiring a
persisted finite-bath/ensemble-equivalence policy and diagnostics [S11-48]. It is not
obtained by inserting the mean kinetic temperature into the canonical formula.

Biased or constrained ensembles require exact bias/constraint provenance and an
explicit reweighting measure. Raw, corrected, and reweighted energies and weights are
retained separately.

The admissibility result separates diagnostic status from permitted products:

```text
position_density
microcanonical_occupancy_distribution
canonical_probability_density
canonical_Helmholtz_landscape
isothermal_isobaric_Gibbs_landscape
reweighted_landscape
force_integrated_landscape
```

Each product records the selected production regime, ensemble, temperature or energy
shell, standard measure, state definition, multiplicity convention, effective sample
size, and approximation status.

## Force provenance

The label `exact_translation_relative_to_disjoint_reference_group` is valid only
when translation is the sole fitted transformation, the mobile ion is excluded
from the fixed reference group, the reference membership is constant, and the
force source contains no untracked constraint or thermostat contribution. A
structure-fitted rotation, changing reference group, or self-referential center
forces the result to `diagnostic_structure_fitted_projection` or
`generalized_force_unavailable`.


A force-aware sample is admissible only when its provenance is explicit. The
catalog records source format, force unit, model or electronic-structure source,
frame completeness, bias and constraint contributions, thermostat or stochastic
contributions, and the spatial transformation semantics.

Conservative physical forces with a geometrically exact transformation may support
mechanical refinement. Only forces in a thermodynamically admissible coordinate and
ensemble measure may certify a PMF gradient. Unknown, mixed,
variable-cell-measure-incomplete, or diagnostic projected forces remain available as
vectors but cannot elevate a site to thermodynamic-force-validated status. Biased simulations additionally retain:

```text
unbiased_physical_force
known_bias_force_subtracted
density_reweighted_force_unusable
bias_force_unknown
```

Position reweighting alone does not convert the biased force into the unbiased PMF gradient.
A reweighted density may be admissible while its force channel remains unusable. Bias-force
subtraction requires explicit framewise bias-gradient provenance in the same coordinate
measure. The geometric transform status, PMF-force status, and bias-force status are retained
independently in every sample and derived force field.

# Position-density evidence

## Species number density and probability density

Let $\omega_t$ be the represented time interval of frame $t$. For all selected
species atoms present in a position-admissible frame, define

$$
\widehat\rho_M(\mathbf q;\Sigma_h)
=
\frac{1}{\sum_t\omega_t}
\sum_t\omega_t
\sum_{a\in M_t}
K_{G,\Sigma_h}^{\mathrm{per}}(\mathbf q-\mathbf q_{a,t}).
$$

Then

$$
\int_\Omega\widehat\rho_M(\mathbf q;\Sigma_h)\,d\mathbf q
=
\frac{\sum_t\omega_tN_{M,t}}{\sum_t\omega_t}
=
\overline N_M.
$$

The one-particle probability density is

$$
\widehat p_M(\mathbf q;\Sigma_h)
=
\frac{\widehat\rho_M(\mathbf q;\Sigma_h)}{\overline N_M},
\qquad
\int_\Omega\widehat p_M(\mathbf q;\Sigma_h)\,d\mathbf q=1.
$$

Frame weights are not assumed equal when timesteps are nonuniform, trajectories
are concatenated, or frames are subsampled. Weight construction is segment aware.
Each sample retains:

```text
trajectory_segment_id
segment_local_frame_weight
represented_interval_left
represented_interval_right
discontinuity_status
```

The default quadrature uses midpoint intervals only inside one continuous
trajectory segment and half intervals at segment endpoints. A frame never
represents time across a restart gap, rejected interval, ensemble change,
thermostat change, topology-regime boundary, or independent-trajectory boundary.
A position-admissible frame normally contains the complete selected species
population; atom-specific missingness must not silently alter frame weight.

Kernel density estimation follows Rosenblatt and Parzen [S11-18, S11-19]. The
bandwidth is a statistical model parameter, not a numerical grid interval or a rendering
tolerance.

## Kernel metric and reference-cell covariance

A Gaussian KDE owns a symmetric positive-definite covariance $\Sigma_h$ in its declared
coordinate measure:

$$
K_{\Sigma_h}(\boldsymbol\delta)
=
\frac{\exp\!\left[-\tfrac12\boldsymbol\delta\Sigma_h^{-1}
\boldsymbol\delta^{\mathsf T}\right]}
{(2\pi)^{3/2}\sqrt{\det\Sigma_h}}.
$$

The initial policies are:

```text
registered_cartesian_isotropic
    Sigma_h = h^2 I in the registered Cartesian domain

fractional_coordinate_isotropic
    isotropic width h_f in fractional coordinates, equivalent to
    Sigma_h = h_f^2 G^T G in a fixed registered cell G

explicit_covariance
    caller-supplied positive-definite covariance with declared units and frame
```

Under a fixed row-vector coordinate change $\mathbf q'=\mathbf qA$, the same physical
smoothing operator transforms as

$$
\Sigma_h'=A^{\mathsf T}\Sigma_hA.
$$

The kernel metric, covariance, coordinate measure, units, and transformation provenance
are part of the field signature. Selecting a different valid $H_{\mathrm{ref}}$ must not
silently redefine the estimator. The Na-LTA pilot includes a modest reference-cell
sensitivity comparison, such as frame 0 versus a representative production frame, with
the covariance transformed consistently when the same physical smoothing is intended.

## Analysis geometry metric and certified periodic distance

The smoothing covariance does not by itself define the geometry used for minimum-image
lifting, gradient flow, ridges, basins, path comparison, or catalog correspondence. Every
registered analysis owns a separate immutable positive-definite metric $P$:

$$
\|\boldsymbol\delta\|_P^2
=
\boldsymbol\delta P\boldsymbol\delta^{\mathsf T}.
$$

Under a fixed row-vector coordinate change $\mathbf q'=\mathbf qA$, the same geometry
transforms as

$$
P'=A^{-1}PA^{-\mathsf T}.
$$

The initial policy `registered_cartesian_euclidean` uses $P=I$ in the declared registered
Cartesian domain. An explicit metric is permitted when its units, coordinate frame, and
transformation provenance are supplied. The same $P$ governs:

```text
periodic closest-image distance and local-chart lifting
density metric-gradient or mean-shift flow
Hessian orthogonality and ridge normal spaces
basin and saddle construction
attractor correspondence and path-shape distance
periodic comparison clustering
```

Three metric-bearing objects remain distinct:

```text
RegistrationFitMetric
    fits framework alignment and translation residuals

AnalysisGeometryMetric
    defines MIC, local charts, gradient flow, ridges, basins, and path geometry

KernelMetricDefinition
    defines statistical smoothing covariance
```

They may be derived from one declared physical convention, but none is silently
substituted for another.

All differential topology is evaluated in a metric-orthonormal chart. Choose a
fixed factor $L$ with $P=LL^{\mathsf T}$ and local row coordinate
$\mathbf y=\mathbf qL$. Gradients, Hessian eigenvalues, ridge normal spaces, and
steepest-ascent flow appearing below refer to this $\mathbf y$ chart, or to an
algebraically equivalent metric-aware operator. This prevents a nonorthogonal
change of registered coordinates from changing the scientific basin topology.

For a triclinic cell, `MIC_{G,P}` means the closest lattice-vector solution

$$
\operatorname{MIC}_{G,P}(\boldsymbol\delta)
=
\boldsymbol\delta-\mathbf n_*G,
\qquad
\mathbf n_*
=
\operatorname*{argmin}_{\mathbf n\in\mathbb Z^3}
\|\boldsymbol\delta-\mathbf nG\|_P.
$$

Componentwise fractional rounding is not assumed to solve this problem for a skewed cell.
The backend uses a certified reduced-lattice or bounded integer search and records ties or
near ties. Ambiguous closest images fail closed for local moments, force centers, and event
translations.

The kernel covariance $\Sigma_h$ controls statistical smoothing; $P$ controls geometric
notions of distance and topology. They may be chosen consistently from one physical length
scale, but one is never silently substituted for the other.

## Periodized Gaussian on a triclinic torus

For fixed registered cell $G$, the normalized periodic kernel is

$$
K_{G,\Sigma}^{\mathrm{per}}(\boldsymbol\delta)
=
\sum_{\mathbf n\in\mathbb Z^3}
K_{\Sigma}(\boldsymbol\delta+\mathbf nG),
$$

where $\mathbf n$ is an integer row vector. It integrates to one over one periodic cell.
The direct image sum is the numerical oracle. Image enumeration is performed in lattice
coordinates and is truncated by a declared Mahalanobis-radius or equivalent tail bound;
the omitted-mass bound is retained. A minimum-image Gaussian is not generally identical
to the periodized Gaussian and is permitted only when a conservative small-bandwidth
certificate bounds the neglected images.

For a uniform fractional grid with dimensions $(N_1,N_2,N_3)$, each node or voxel uses
the declared quadrature convention with volume weight

$$
\Delta V=\frac{|\det G|}{N_1N_2N_3}.
$$

Normalization, gradient, and Hessian evaluations use one kernel contract. Dense, adaptive,
and block-sparse backends must agree with the same triclinic image sum within their stated
field-error bounds. The kernel contract records behavior when the covariance scale is not
small compared with the torus injectivity radius; no minimum-image shortcut is inferred.

## Physical and reference-material density measures

A density in the physical policy is measured with respect to the instantaneous
physical Cartesian volume element. Under `reference_material`, the field is
measured with respect to the declared reference-material coordinate $d\mathbf q$
and fixed cell $H_{\mathrm{ref}}$.

These are different scientific objects:

```text
physical_cartesian_density
reference_material_density
```

The reference-material field is appropriate for locating material-coordinate
sites under cell breathing or strain. It must not be described as an
instantaneous physical Cartesian density or PMF without the corresponding
Jacobian and ensemble treatment. The real Na-LTA pilot compares physical or
translation-registered and reference-material results where both are feasible.

A pooled `physical_cartesian_density` initially requires a constant registered
cell. Variable-cell trajectories use `reference_material_density` or produce
separate per-frame physical fields. No single pooled physical Cartesian torus is
implied when the periodic domain changes with time.

## Sampled support and local evidence

For a kernel value $K_n(\mathbf q)$ and sample weight $w_n$, retain the raw local
kernel effective sample size

$$
N_{\mathrm{eff}}^{\mathrm{kernel}}(\mathbf q)
=
\frac{\left[\sum_nw_nK_n(\mathbf q)\right]^2}
     {\sum_n\left[w_nK_n(\mathbf q)\right]^2}.
$$

This quantity is correlation-blind and is not an uncertainty estimate by itself.
Scientific support requires both a minimum local kernel support and
reproducibility across complete-system contiguous time blocks or independent
trajectories. Highly correlated adjacent frames cannot manufacture support.

## Feature-level sampling adequacy and cross-fitting

Local KDE support determines whether a numerical field value can be evaluated; it does
not certify a physical basin or transition state. The architecture tracks:

$$
N_{\mathrm{raw}}\rightarrow N_{\mathrm{eff}}\rightarrow
N_{\mathrm{independent\ visits/events}}\rightarrow
N_{\mathrm{independent\ blocks/replicas}}.
$$

The primary resampling unit is the complete-system time block or an independent
trajectory. Multiple mobile ions in one frame increase spatial coverage but do not
multiply independent energetic or thermodynamic observations.

`SamplingAdequacyPolicy` and `FeatureCorrespondencePolicy` define this candidate-validation
sequence:

1. construct `EvidenceCrossfitPartition` before feature discovery;
2. discover per-realization basin and density-boundary candidates on discovery data;
3. select bandwidth, grid, correspondence, and candidate-complexity policies using only
   discovery/model-selection data;
4. let GR4 freeze one `FrozenCandidateCatalog` and its exact numerical hypothesis;
5. assign held-out basin-validation blocks without refitting;
6. count independent basin residences and basin-to-basin passages without requiring a
   saddle;
7. certify basins;
8. validate density-boundary/corridor candidates using independent corridor-validation
   evidence not used for discovery or selection; and
9. perform any final refit only after validation and retain the pre-refit certificates.

Candidate confidence is represented by orthogonal fields, not one hierarchy:

```text
numerical_support_status
spatial_recurrence_status
temporal_recurrence_status
cross_block_validation_status
cross_replica_status
uncertainty_status
promotion_decision
```

E2 owns per-realization numerical candidates. GR4 alone owns the source-bound
`FrozenCandidateCatalog` evaluated by held-out stages. A later all-data
`FinalRefitCatalog` has a new signature and cannot inherit the frozen catalog's parameter-
validation certificate.

## Matched density and force smoothing

Density-force consistency requires the same periodized kernel definition, covariance
scale, sample weights, and joint frame subset. Define

$$
\widehat p_{\Sigma_h}(\mathbf q)
=
\frac{1}{W}
\sum_nw_nK_{G,\Sigma_h}^{\mathrm{per}}(\mathbf q-\mathbf q_n),
$$

and

$$
\widehat{\mathbf f}_{\Sigma_h}(\mathbf q)
=
\frac{
\sum_nw_nK_{G,\Sigma_h}^{\mathrm{per}}(\mathbf q-\mathbf q_n)\mathbf f_n
}{
\sum_nw_nK_{G,\Sigma_h}^{\mathrm{per}}(\mathbf q-\mathbf q_n)
}.
$$

The finite-sample consistency test compares this matched pair. A density
estimated on all admissible positions remains available for site discovery, but
it is not compared directly with a force field from a smaller subset.

### Density score covector and metric gradient

The coordinate derivative of the log density is the score covector

$$
\mathbf s_q(\mathbf q)=d_q\ln p(\mathbf q).
$$

Under a fixed row-vector coordinate change $\mathbf q'=\mathbf qA$,

$$
\mathbf s_{q'}=\mathbf s_qA^{-\mathsf T}.
$$

It therefore transforms like the force covector. The equilibrium density-force
consistency relation is

$$
\boxed{
\overline{\mathbf F}_q(\mathbf q)
=
k_{\mathrm B}T\,\mathbf s_q(\mathbf q)
}
$$

in one declared coordinate measure. The vector that generates steepest-ascent
flow under analysis metric $P$ is a different object:

$$
\boxed{
\operatorname{grad}_P\ln p
=
\mathbf s_qP^{-1}.
}
$$

`DensityScoreCovector` is used for force comparison, thermodynamic integration,
and covector-valued diagnostics. `MetricGradientVector` is used for gradient flow,
mean shift, ridge normals, and basin construction. A consumer must never compare
force directly with the metric-raised vector unless it first lowers that vector
with the declared metric. Score, metric gradient, derivative realization error,
and coordinate-transform provenance are stored separately. Their shared field
signature records $P$, $\Sigma_h$, registered domain, coordinate measure, and
sample subset so a consumer cannot combine incompatible derivatives.

## Bandwidth ladder and attractor lineage

No single smoothing scale is authoritative. For one fixed positive-definite metric
shape $B$, the default ladder uses

$$
\Sigma_\ell=h_\ell^2B,
\qquad
h_1<h_2<\cdots<h_L.
$$

An explicit covariance ladder is also permitted when every matrix and correspondence is
declared. Each covariance scale produces a deterministic attractor and basin catalog. A
`DensityAttractorLineage` records:

- attractor type and periodic support at every covariance scale;
- parent and child merge or split events;
- basin-overlap score;
- periodic displacement of isolated modes;
- overlap and intrinsic-dimension changes for extended attractors;
- basin probability change;
- split or merge ambiguity; and
- the smoothing-scale survival interval.

A grid index or local-maximum number is never a persistent site identity.
Attractors that exist only over one narrow smoothing interval remain method-dependent
unless independently supported.

### Operational scale-consensus catalog

Downstream force fitting, temporal persistence, and segmentation require one concrete,
versioned catalog. A `ScaleConsensusCatalog` is therefore produced from the full lineage;
no plotting default or visually convenient bandwidth may become authoritative implicitly.
Its `OperationalScaleDecision` retains:

```text
candidate topology-stable scale intervals
selected covariance or consensus construction
selection criterion and independent selection evidence
competing split/merge hypotheses
support and numerical certificates
selection uncertainty and scale_ambiguous status
```

The decision first identifies covariance intervals with stable supported topology, then
rejects intervals without field and topology certification. When several nested split/merge
hypotheses remain plausible, independent `model_selection` temporal persistence and admissible force evidence may
distinguish physical substates from smoothing artifacts. If they do not, the catalog retains
the competing hypotheses and is `scale_ambiguous`; later rate or PMF claims that depend on
one unresolved choice are prohibited. An optional consensus construction may retain only
attractors with stable correspondence over a declared interval, but its basin construction
and uncertainty must be explicit.

When the spatial evidence alone cannot choose, Stage 11E2 emits a
`ScaleHypothesisSet` rather than pretending that one catalog is resolved. Stage 11E3 and
Stage 11E4 then evaluate each retained hypothesis under identical force and temporal
contracts; Stage 11E5 may select one hypothesis only when `model_selection` evidence distinguishes
it, otherwise `scale_ambiguous` persists. The exact catalog or hypothesis set used by each
downstream stage records the lineage digest and operational decision. Re-selecting a scale
creates a new catalog identity rather than mutating the previous one.

## Isolated modes and extended attractors

A statistical site need not be an isolated point maximum. The authoritative
object is a `DensityAttractor` with one of the forms:

```text
isolated_mode
ridge_or_manifold
flat_unresolved_component
```

An annular site is a connected one-dimensional ridge with restoring confinement
normal to the ridge and weak tangential variation. It must not be reduced to an
arbitrary point by plateau tie breaking. Discrete off-center sites remain
separate isolated modes.

For an extended attractor, retain its connected ridge support, intrinsic
dimension, normal confinement, tangential variation, compact geometric
representation, basin probability, and bootstrap stability.

## State-local periodic charts

Wrapped coordinates are suitable for a periodic density field but not directly
for Euclidean moments, local force fits, or compact transfer models. Every
attractor therefore owns an `AttractorLocalChart` bound to the registered-cell
signature. For an isolated mode with periodic anchor $\boldsymbol\mu_i$, samples
are lifted by minimum-image displacement,

$$
\boldsymbol\delta_n
=
\operatorname{MIC}_{G,P}
(\mathbf q_n-\boldsymbol\mu_i),
$$

and covariance, local Hessians, and harmonic fits use
$\boldsymbol\delta_n$, not globally wrapped coordinates. The chart records the
anchor, image convention, lifted samples, validity radius, and any chart-boundary
ambiguity.

An extended attractor may require an intrinsic periodic parameterization or
several overlapping charts. The first implementation supports isolated-mode
charts and an explicitly parameterized annular chart; a general manifold whose
chart cannot be certified remains `manifold_chart_unresolved` and is excluded
from Euclidean force fitting.

## Deterministic attractor and basin construction

The initial authoritative backend is:

```text
periodic KDE field
    -> deterministic periodic-grid extrema and ridge components
    -> canonical plateau-component ownership
    -> discrete steepest-ascent or ridge-attraction labels
    -> support-restricted periodic basin ownership
    -> supported inter-basin saddle densities
    -> attractor lineage across bandwidths
    -> operational scale-consensus catalog
```

### Continuous ridge criterion

In the metric-orthonormal coordinate $\mathbf y=\mathbf qL$, let the smooth
periodized KDE have Hessian eigendecomposition

$$
\nabla_{\mathbf y}^2\widehat p
=
V\Lambda V^{\mathsf T},
\qquad
\lambda_1\ge\lambda_2\ge\lambda_3.
$$

For a one-dimensional ridge in three dimensions, let
$V_{\perp}=[\mathbf v_2,\mathbf v_3]$. A supported point is a ridge candidate when

$$
V_{\perp}^{\mathsf T}\nabla_{\mathbf y}\widehat p=\mathbf0,
\qquad
\lambda_2(\mathbf q)\le-\kappa_{\perp}<0,
$$

with a declared eigengap, support, and derivative-uncertainty requirement. This adapts
density-ridge definitions from the nonparametric ridge literature [S11-34]. If the
normal eigenspace, eigengap, or intrinsic dimension is unresolved, the component remains
`ridge_dimension_unresolved`. A point mode instead satisfies $\nabla_{\mathbf y}\widehat p=0$ with
all three curvatures negative within uncertainty.

A corrugated annulus remains one extended attractor only when its connected ridge survives
bandwidth and grid refinement and the tangential modulation does not meet the declared
persistent-saddle criterion for splitting into separate point states. The exact persistence
and curvature thresholds belong to the Stage 11E2 specification.

### Support-certified periodic cell complex and transition candidates

The production topology is built on one complete periodic cell complex in fractional-
grid coordinates with explicit wrap adjacency. Density, gradient, Hessian,
critical-cell, plateau, ridge, numerical transition-candidate, and basin labels share
that complex. `SupportedPeriodicCellComplex` classifies every cell as:

```text
supported_basin
supported_transition_region
supported_background
unsupported_unknown
numerically_unresolved
```

A face-adjacent merge cell or density bottleneck is a
`density_boundary_candidate`. When field and derivative support also pass, it may be
called a `numerically_supported_saddle_candidate`. Neither name implies an observed
transition event, an equilibrium transition state, a barrier, or an authoritative
kinetic edge.

Unsupported or unevaluated cells are never assigned to a basin and are never treated
as zero-density background. A basin cannot connect through unsupported space.
Disconnected supported components acquire no inferred adjacency or relative
thermodynamic offset. Rendering sparsification is downstream and cannot create
scientific connectivity.

The discrete critical-cell and attachment logic may adapt Forman cell-complex Morse
theory [S11-35]. Mean-shift ascent remains the theoretical mode-seeking reference
[S11-20]. HDBSCAN remains an independent cluster-stability validator using the same
certified periodic metric [S11-21]. None of these numerical backends bypasses SAMP2
event and held-out-corridor validation.

### Field and topology certification

Numerical realization owns two independent certificates:

```text
FieldErrorCertificate
    density, gradient, and Hessian error bounds against the declared operator

TopologyStabilityCertificate
    critical points, ridges, saddles, basin adjacency, and periodic connectivity
    stable under declared refinement and backend comparison
```

A small pointwise field error does not by itself certify topology. Sparse or adaptive
blocks that have not been evaluated are treated as unknown, not as zero. A block may be
excluded from topology only when a conservative upper/derivative bound proves it cannot
contain a supported critical feature or create a basin connection. Refinement concentrates
around extrema, ridges, saddles, basin boundaries, and periodic seams until identities are
stable or explicitly unresolved. Small synthetic fixtures use a dense oracle; production
fields retain the refinement history and both certificates.

## Provisional cores

Each attractor owns a nonparametric basin $B_i$ and a type-specific core
construction. For an isolated mode, let $p_i^{\max}$ be its maximum and
$p_i^{\mathrm{saddle}}$ the highest resolved density connecting it to a
neighboring basin. Define

$$
\chi_i(\mathbf q)
=
\frac{
\log\widehat p(\mathbf q)-\log p_i^{\mathrm{saddle}}
}{
\log p_i^{\max}-\log p_i^{\mathrm{saddle}}
},
$$

and, for declared $0<\tau_c<1$,

$$
C_i(\tau_c)
=
\{\mathbf q\in B_i:\chi_i(\mathbf q)\ge\tau_c\}.
$$

For an extended attractor, one global maximum is not used. Let
$\pi_i(\mathbf q)$ project a supported point to the certified ridge or manifold,
and let $p_i^{\mathrm{ridge}}(\pi_i(\mathbf q))$ be the local ridge density. The
normal-depth coordinate is

$$
\chi_i^{\perp}(\mathbf q)
=
\frac{
\log\widehat p(\mathbf q)-\log p_i^{\mathrm{saddle}}
}{
\log p_i^{\mathrm{ridge}}(\pi_i(\mathbf q))
-\log p_i^{\mathrm{saddle}}
}.
$$

An annular core uses $\chi_i^{\perp}$ together with the certified annular chart
so that weak tangential density modulation does not break one continuous state
into arbitrary core sectors. General manifold cores remain unresolved until a
projection and local ridge-density model are certified.

A core owns one explicit depth source:

```text
interbasin_saddle_depth
supported_boundary_depth
probability_content_core
core_unresolved
```

`interbasin_saddle_depth` is preferred when a neighboring supported basin and resolved
saddle exist. A single attractor or an attractor isolated in its supported component has no
interbasin saddle; it may use a declared supported-boundary depth or a probability-content
core with retained mass fraction and uncertainty. A fallback never invents a neighboring
state or barrier. If the connecting saddle, supported boundary, local chart, projection, or
ridge density is unresolved and no declared fallback passes, the core remains unresolved.
The canonical nonparametric basin and core remain authoritative even when an ellipsoid,
Gaussian, annulus, or other compact transfer model is fitted.

# Mechanical force evidence and thermodynamic mean-force reconstruction

## Two force products with different admissibility

Stage 11 keeps two force-derived products separate.

`LocalMechanicalForceRefinement` uses geometrically admissible conservative physical
forces to test local restoring behavior, center offsets, stiffness, and manifold-normal
confinement. It does not require a canonical PMF and may be available for NVE data.

`ThermodynamicMeanForceCertificate` tests whether a conditional force is the gradient of
a declared canonical or validly reweighted reduced free-energy landscape. It requires the
matching ensemble measure, coordinate Jacobian, temperature/reweighting provenance, and
joint position-force support. Mechanical validity never promotes thermodynamic validity.

## Canonical conditional mean force

For a canonical or validly reweighted-canonical coarse coordinate in the declared
coordinate measure,

$$
\overline{\mathbf F}_{M,q}(\mathbf q)
=
\mathbb E[\mathbf F_M^{(q)}\mid\mathbf q]
=
-d_qA_M(\mathbf q)
=
k_{\mathrm B}T\,d_q\ln p_M(\mathbf q).
$$

This identity is not applied generically to NVE, NpH, unknown, or mixed-thermostat
data. A stationary NVE trajectory may use a separately implemented microcanonical
mean-force formalism or an explicitly certified subsystem-canonical approximation;
otherwise density-force comparison is diagnostic-only. The metric gradient used for
basin flow is obtained only after raising the score with $P^{-1}$ and is not the
covector compared directly with force. Average-force free-energy methods and force
matching provide the theoretical basis [S11-22, S11-23].

## Local mechanical force refinement

For a position-derived point candidate, fit inside its certified local periodic chart
using only SAMP0 discovery/model-selection evidence,

$$
\mathbf f_n
=
\mathbf b_i
-
\boldsymbol\delta_n\mathbf K_i
+
\boldsymbol\epsilon_n,
\qquad
\mathbf K_i=\mathbf K_i^{\mathsf T}.
$$

When $\mathbf K_i$ is nonsingular under the row-vector convention, the force-defined
center offset is

$$
\boldsymbol\delta_i^{(F)}
=
\mathbf b_i\mathbf K_i^{-1}.
$$

The result retains the density anchor, intercept, force-defined center, joint
center/stiffness uncertainty, chart containment, and positive-definiteness probability.
The force center is not reported when $\mathbf K_i$ is singular, poorly conditioned, or
places the center outside the supported chart. A point basin requires locally restoring
curvature within uncertainty; an annular manifold is fitted in certified ridge-normal
coordinates without imposing one global point center.

A held-out mechanical-force evaluation may measure residuals and center agreement but
may not refit parameters. An optional all-data post-validation refit receives a new
signature and does not inherit the original held-out certificate.

The residence covariance diagnostic

$$
\boldsymbol\Sigma_i^{(\mathrm{res})}
=
\operatorname{Cov}
\left[
\boldsymbol\delta\mid\text{provisional residence in }B_i
\right]
$$

is always reported descriptively. The harmonic equipartition relation

$$
\boldsymbol\Sigma_i^{(\mathrm{res})}
\approx
k_{\mathrm B}T\mathbf K_i^{-1}
$$

is evaluated only for canonical/reweighted-canonical data or under an explicitly
accepted subsystem-canonical approximation. Basin truncation, anharmonicity, correlated
many-ion conditioning, and unresolved ensemble measure may invalidate this thermodynamic
comparison without invalidating the mechanical fit or spatial attractor.

## Raw mean-force field

The matched-kernel conditional force field retains local force variance,
effective sample size, support, and time-block uncertainty. Force-assisted
density estimators may reduce variance but cannot create claims in unsampled
regions [S11-28].

## Curl and periodic harmonic components

For an exact equilibrium PMF,

$$
\nabla\times\overline{\mathbf f}=\mathbf0.
$$

On a periodic three-torus, a vector field decomposes schematically as

$$
\mathbf f
=
-\nabla A
+
\nabla\times\mathbf B
+
\mathbf h,
$$

where $\mathbf h$ is a harmonic component. Nonzero curl, nonzero circulation, or
a nonzero harmonic component is a diagnostic of sampling error, nonequilibrium,
coordinate or force mis-specification, or unresolved conditioning.

Helmholtz-Hodge decomposition supplies the mathematical language [S11-26].
Poisson or least-squares integration may expose the closest conservative field
[S11-27], but projection is never automatic.

The full periodic torus and a sampled support subdomain are different mathematical
domains. The full torus has its periodic harmonic directions and circulation cycles.
A support-limited component may also have boundaries, disconnected pieces, or holes,
so its harmonic space and admissible boundary terms depend on the topology of that
subdomain. Curl-free behavior on sampled cells alone does not establish a single-valued
potential when nontrivial circulation remains. Every PMF attempt therefore records:

```text
full_torus_hodge or supported_domain_integrability
domain cell-complex topology and connected component
boundary conditions and excluded unsupported boundary
independent circulation generators and measured circulation
harmonic-space dimension or unresolved status
```

No full-torus conclusion is inferred from a partial support component, and no
supported-domain relative offset is invented across disconnected components.

## Optional support-limited force-PMF reconstruction

This subsection describes the force-integrated estimator only. A density-derived PMF is a
separate estimator and does not require force evidence. Global force-PMF reconstruction is
optional and does not block local site discovery.
It is attempted only when:

- the declared numerical domain and boundary conditions are explicit;
- the sampled support component is connected;
- the field is adequately supported across the integration domain;
- periodic circulation and harmonic diagnostics are reported; and
- disconnected support components are not assigned relative free-energy offsets.

The preferred reconstruction fits a scalar potential directly:

$$
\mathcal L_F(\theta)
=
\sum_nw_n
\left\|
\mathbf f_n^{(q)}+\nabla A_\theta(\mathbf q_n)
\right\|^2
+
\mathcal R(\theta).
$$

Conservativity is guaranteed by construction. Periodic splines or radial basis
functions are initial candidates. Variational reconstruction follows
single-sweep free-energy methods [S11-24]. Gaussian-process gradient
reconstruction is a later uncertainty-aware option [S11-25, S11-31]. Raw and
projected fields, support, boundary conditions, residuals, and additive-constant
conventions remain available together.

# Joint site validation and structural classification

## Orthogonal evidence and classification statuses

Every evidence channel uses the canonical diagnostic registry:

```text
resolved | unresolved | insufficient | rejected | unavailable | not_applicable
```

Each channel also carries a domain outcome rather than embedding that outcome in a
new incompatible status enum:

```text
spatial_diagnostic_status
spatial_outcome                  # candidate | recurrent | method_dependent | absent

temporal_diagnostic_status
temporal_outcome                 # persistent | nonpersistent | censored | unavailable

force_diagnostic_status
force_outcome                    # diagnostic_only | correlated | consistent | inconsistent

stationarity_diagnostic_status
stationarity_outcome             # stationary | nonstationary | selection_conditioned

geometry_diagnostic_status
attractor_geometry               # isolated_point | annular_manifold |
                                 # general_manifold | flat_unresolved

curvature_diagnostic_status
curvature_outcome                # stable | saddle | unstable | unresolved

overall_promotion_decision       # accepted | conditional | blocked | rejected
```

Mappings from ENS/STAT/SAMP results to E5 fields are explicit and immutable. Force
availability may strengthen certification but never deletes accepted position/time
evidence. Position and force from one trajectory are not independent; uncertainty
uses matched complete-system block resamples. A state with accepted spatial and
temporal evidence but unavailable admissible force evidence may receive a conditional
metastable interpretation, not a force-validated one.

## Provisional temporal evidence

Frozen numerical basin candidates may be assigned provisionally before final basin or
saddle certification. Held-out assignments use only the frozen basin regions and do
not require a saddle definition. Core entry and basin retention produce raw dwell
intervals, local decorrelation estimates, censoring, and basin-to-basin passages.
This stage does not publish the final cleaned event catalog.

A passage is recognized when one atom leaves a frozen basin and subsequently enters a
different frozen basin under the declared gap/censoring policy. A validated saddle is
not an input to passage recognition; the resulting independent passages are later
used to validate or reject candidate transition corridors.

The local vibration/decorrelation timescale is explicit. Acceptable estimators include
a site-conditioned coordinate autocorrelation time, site-conditioned VACF decay,
Hessian-derived harmonic timescale, or declared physical minimum. The estimator,
block provenance, and uncertainty are retained, and short trajectories may return
`insufficient`.

## Basin and transition-corridor sampling certificates

Every candidate basin receives a `BasinSamplingCertificate` with raw and effective
sample counts, represented time, independent residences, complete-system blocks,
trajectory/replica coverage, ion-time probability, occupancy, bootstrap recurrence,
held-out support, anchor/shape uncertainty, and grid/bandwidth survival.

Its evidence fields are orthogonal:

```text
numerical_support_status
spatial_recurrence_status
temporal_recurrence_status
cross_block_validation_status
cross_replica_status
uncertainty_status
promotion_decision
rejection_reasons
```

A long single residence can support spatial localization while remaining insufficient
for recurrent metastability.

Every candidate basin pair or corridor receives a
`TransitionCorridorSamplingCertificate` containing independent passage count,
forward/reverse counts, complete-system block and replica support, path-progress
coverage, local field support, candidate recurrence, corridor-location uncertainty,
density-level uncertainty, and event-path agreement.

Terminology is fixed:

```text
density_boundary_candidate
numerically_supported_saddle_candidate
observed_one_off_passage
sampling_supported_transition_corridor
sampling_supported_saddle_candidate
```

`density_level_uncertainty`, `free_energy_barrier_uncertainty`, and
`conditional_energy_uncertainty` are distinct fields. One passage may be retained as
an observation but never validates an equilibrium saddle or rate.

## Partial-catalog and saturation certificate

Every dataset produces a `DiscoveryScopeCertificate` with species, composition,
loading, ensemble, temperature or energy-shell scope, trajectory/replica counts,
physical and effective observation time, cumulative basin/corridor/event discovery,
holdout novelty, and saturation diagnostics. Allowed public claims include:

```text
strongly_unsaturated
still_discovering
apparently_plateauing_at_this_timescale
replicated_partial_catalog
structurally_enumerated_but_dynamically_partial
observed_partial_catalog
```

A plateau means only that no new supported feature appeared over the observed
extension. SAMP3 reports raw event count, at-risk exposure, occupancy exposure,
censoring, and model eligibility. A formal zero-event or low-count rate interval is
owned by Stage 11F0 and requires a signed `RateBoundModel` specifying Poisson or
other event assumptions, stationarity, exposure, censoring, and confidence method
[S11-49].

## Density-force consistency refers to the authoritative force contract

Density-force comparison is governed exclusively by **Canonical conditional mean force**
and Stage 11E3B. It is available only under the exact ensemble, reweighting,
coordinate-measure, Jacobian, transformed-covector, matched-kernel, and joint-support
requirements stated there. Generic NVE data are not upgraded by this cross-reference.

A failed or unavailable thermodynamic mean-force comparison remains explicit and never
deletes a valid E3A mechanical refinement or descriptive density result.

## Major and minor sites

The catalog reports separate rankings by basin probability and temporal
persistence. A low-population, long-lived basin may be a minor metastable site.
A high-density bridge with short visits may be transition support. No fixed
majority-occupancy threshold defines a site.

## Ion-time probability and many-ion occupancy

For a normalized species probability density, the integral over basin $B_i$,

$$
P_i^{\mathrm{ion}}
=
\int_{B_i}\widehat p_M(\mathbf q)\,d\mathbf q,
$$

is the fraction of ion-time samples in that basin. It is not, by itself, the
probability that the structural site is occupied. The mean occupancy is

$$
\langle n_i\rangle
=
\int_{B_i}\widehat\rho_M(\mathbf q)\,d\mathbf q.
$$

Final site statistics separately report ion-time fraction, mean occupancy,
occupancy distribution, vacancy fraction, and multiple-occupancy fraction.
Many-ion correlations are retained at the complete-frame level.

## Structural association and species-dependent coordination

Only after statistical discovery and provisional temporal validation is one
state associated with Stage 11C/11D structural objects. Association is not
restricted to one ring. A cage-interior, interstitial, or transition state may be
influenced by several windows or tiles.

```text
StructuralAssociationSet
    primary association, when identifiable
    secondary ring/cage/tile associations
    geometric and chemical scores
    ambiguity and support
    registered and physical geometry references
```

The registered structural view is used to compare density-space positions. The
physical geometry is used for exact bond distances, apertures, and coordination.
An association remains ambiguous rather than being forced to the nearest ring.

### Statistical-state instances and structural symmetry orbits

Every learned basin is first a distinct `ValidatedStatisticalState` instance. Optional
structural grouping records

```text
StructuralSymmetryOrbit
    orbit identity and member state instances
    ideal multiplicity and observed multiplicity
    stabilizer or site-symmetry provenance
    missing, unresolved, or split members
    Si/Al-order, occupancy, and geometry symmetry-breaking evidence
```

The observed kinetic network always retains state instances as nodes. An orbit-level
summary is created only after framework chemistry, oxygen classes, local occupancy,
density, force, and transition statistics pass an exchangeability test. No symmetry
augmentation of trajectory samples occurs by default; it would hide genuine symmetry
breaking and overstate uncertainty support.

### Exact coordination fingerprint

For one state and one associated structural object, the authoritative
species-dependent record is

$$
\mathbf d_M
=
\left(
d_{M\mathrm O_1},\ldots,d_{M\mathrm O_k},
d_{M\mathrm T_1},\ldots
\right),
$$

with persistent atom identities, oxygen classes, local ion coordinates, and the
complete conditioning context. Stage 11E5a owns this record; Stage 11C3 does not.

Coordination descriptors use the same separation as structural ring analysis:

- an exact unweighted cyclic-index spectrum for ordered discrete M--O sequences;
- boundary-measure angular moments when a continuous angular measure is intended; and
- a rank-safe actual-angle fit for physical angular modulation.

For a hypothetical point with the same normal coordinate and zero in-plane
displacement, compute the exact centered-reference distances $d_j^{(0)}$ and

$$
\Delta d_j=d_j-d_j^{(0)}.
$$

The residual spectra $\Delta D_m$ are diagnostic summaries. They are not an
orthogonal or exact separation of ring corrugation and cation displacement.
Irregular spacing, puckering, large off-centering, and nonlinear distance
geometry can mix harmonics. The authoritative off-center measures remain the
direct local coordinates

$$
(u_M,v_M,z_M),
\qquad
r_\perp=\sqrt{u_M^2+v_M^2},
$$

and the exact ordered distance vector.

### Forward-model check

For one learned registered center or instantaneous geometry-conditioned center,
first map the center back to the physical frame of each sample:

$$
\mathbf x_{\mathrm{site},t}
=
\left(
\mathbf q_{\mathrm{site},t}-\mathbf b_t
\right)M_t^{-1}.
$$

Using the persistent matched image of oxygen $j$, calculate the framewise physical distance

$$
d_{j,t}^{\mathrm{geom}}
=
\left\|
\mathbf x_{\mathrm{site},t}
-
\mathbf x_{\mathrm O_j,t}^{(\mathrm{matched\ image})}
\right\|.
$$

Compare the conditional distribution or conditional mean of these framewise distances with
the observed state-conditioned M--O sequence. Distances are never computed between a
registered site coordinate and a physical oxygen coordinate, and distance from averaged
structures is not substituted for the average of framewise distances. The result separates:

```text
geometrically_explained_off_centering
chemical_or_environment_residual
occupancy_conditioned_residual
unresolved_mixture
```

A large $m=1$ coordination amplitude alone is insufficient to declare an
off-centered site.

### Classification evidence

For each association retain at least:

```text
normal and in-plane site displacement
ordered M-O and M-T distances
structural cyclic and physical-angle spectra
coordination cyclic and physical-angle spectra
off-center residual diagnostics
chemical phase-locking scores
opposite-side partner score
angular multiplicity and annularity scores
ring/cage distance and association confidence
forward-model residual
```

For an S6R, a centered serrated site may satisfy

$$
r_\perp\simeq0,
\qquad
|\Delta D_1|\simeq0,
\qquad
|D_3|>0,
$$

whereas an off-centered serrated site has nonzero direct $r_\perp$, a
long-wavelength modulation compatible with the exact geometry, and a retained
short-wavelength chemical component. An $m=2$ structural component can indicate
elliptical or twofold ring deformation and must not be relabeled as cation
off-centering.

Phase locking is evaluated only when the amplitude and phase are resolved under
the formal structural gauge. Persistent locking may support labels such as
oxygen-directed, gap-directed, or sector-locked. Several persistent angular
modes are separate statistical microstates. Angular circulation with normal and
radial confinement may define `smooth_annular`, `corrugated_annular`, or
`discrete_angular_minima` according to density, force, and temporal evidence.

### Occupancy-conditioned fingerprints

Before pooling all samples from one nominal state, compare the coordination
fingerprint under local occupancy context $\eta$:

$$
p(\mathbf d_M\mid\eta).
$$

When supported by the data, report center shifts, phase changes, covariance
changes, or split subpopulations conditioned on neighboring occupancy. The first
implementation need not build a many-body PMF, but it must detect when one
pooled fingerprint is an unresolved occupancy-conditioned mixture.

Nominally equivalent rings are pooled only after exchangeability tests. Local
Si/Al ordering, oxygen-class splitting, neighboring occupancy, distortion, and
site history may require separate subclasses even when the natural-tiling
interface family is the same. Borderline cases remain `general` or
`classification_ambiguous`.

## EvidenceCrossfitPartition, thermodynamic partitions, and final refit

One signed `EvidenceCrossfitPartition` assigns complete-system blocks or independent
trajectories to structural/statistical roles:

```text
discovery
model_selection
basin_validation
corridor_validation
thermodynamic_estimation
thermodynamic_validation
optional_final_refit
```

`thermodynamic_estimation` owns source-qualified occupancy, conditional-energy, PMF, or
effective-Hamiltonian estimation. `thermodynamic_validation` is reserved for an optional
independent cross-check. If the latter is unavailable, the estimate may still be reported
when its own ensemble, state, sampling, and uncertainty gates pass; it is labeled
`source_qualified_unverified`, not rejected.

| Partition | Permitted ownership |
|---|---|
| `discovery` | E1/E2 per-realization candidate construction and exploratory E3A fitting |
| `model_selection` | bandwidth, grid, candidate complexity, correspondence policy, and E3A hyperparameter selection |
| `basin_validation` | SAMP1 recurrence, occupancy, residence, and E5 basin evidence without refitting |
| `corridor_validation` | SAMP2 preliminary passage/corridor evidence without changing basin or corridor definitions |
| `thermodynamic_estimation` | THERMO1/2/3A, PMF_DENSITY, PMF_FORCE, and source-qualified thermodynamic estimators |
| `thermodynamic_validation` | optional THERMO4A or PMF_CROSSCHECK evidence that does not build the estimator it verifies |
| `optional_final_refit` | post-validation parameter refit with a new signature and no inherited parameter-validation certificate |

Discovery and model-selection evidence may share a signed nested-selection policy only
when the nesting is explicit and uncertainty is propagated. Reuse between thermodynamic
estimation and verification must be labeled `selection_conditioned_verification`; it is
never described as independent.

Candidate identities are frozen by GR4 before held-out assignment. `FrozenCandidateCatalog`
retains the exact numerical hypothesis and candidate set evaluated on validation data.
`FinalRefitCatalog` is a new product and cannot inherit validation evidence for moved
centers, changed boundaries, changed force parameters, or changed state identity.

The protocol reports independence separately for each product:

```text
independent_selection_supported
independent_basin_validation_supported
independent_corridor_validation_supported
independent_thermodynamic_verification_supported
selection_conditioned_verification
independent_verification_unavailable
```

Attractors, basins, ridges, and corridors are matched across bandwidths, grids, bootstrap
replicas, blocks, and independent trajectories through the signed
`FeatureCorrespondencePolicy`. Numeric mode order is never a persistent identity.

## Geometry-conditioned site refinement

After a site has been associated independently with a persistent ring or cage,
its complete assignment region may follow framework geometry. A first model is

$$
\mathbf q_i(t)
=
\mathbf q_{i,0}
+
B_i\left[\boldsymbol\xi_R(t)-\overline{\boldsymbol\xi}_R\right]
+
\boldsymbol\epsilon_t,
$$

where $\boldsymbol\xi_R$ may contain aperture, area, puckering, oxygen-class
radii, rank-safe structural spectra, gauge-defined phase features, and cage
volume from the registered and physical structural views. The fitted
object is not only a moving point. It defines instantaneous nested regions

$$
C_i(t)\subset B_i(t).
$$

The first implementation translates or rigidly transports a fixed basin shape
in the associated local frame. Shape- or covariance-conditioned models are later
extensions. The static nonparametric discovery basin and the optional dynamic
assignment basin remain separately available.

A dynamic boundary can pass over an ion even when the ion barely moves in the local
comoving frame. Every candidate crossing therefore retains

```text
ion displacement in the local comoving frame
center and boundary displacement
static-basin and static-core membership
dynamic-basin and dynamic-core membership
boundary_induced_crossing flag and uncertainty
```

A transition is never interpreted as purely ion-driven when the dynamic and frozen
memberships disagree. The final catalog may use the validated dynamic basin, but it
reports the frozen-basin counterfactual so ring breathing or cage deformation cannot
masquerade silently as hopping.

The fitting protocol is noncircular by default:

1. fit candidate geometry-conditioned models on `discovery` evidence using assignments
   from the frozen static catalog;
2. choose among candidate models on `model_selection` evidence while keeping frozen
   state identity unchanged;
3. freeze the selected dynamic model;
4. evaluate state geometry, occupancy, and assignment stability on `basin_validation`
   evidence and passage/crossing effects on `corridor_validation` evidence;
5. use `thermodynamic_validation` only for separately requested thermodynamic products;
6. report all static/dynamic disagreements, assignment conflicts, and
   boundary-induced crossings; and
7. treat any `optional_final_refit` as a new signed product.

Static and geometry-conditioned models are selected on complete-system
`model_selection` evidence and confirmed independently for each requested held-out
product. The dynamic model is retained only when it reproducibly reduces residual
variance without changing persistent state identity. Mobile-ion
coordinates never redefine the ring frame or chemical boundary used as the
predictor. Any iterative reassignment/refit method is a separately named,
versioned algorithm with declared initialization and convergence criteria; it is
never an implicit refinement step.

Independently transported dynamic regions can overlap even when the static
nonparametric basins are disjoint. Every frame therefore receives one exclusive
`AssignmentConflictStatus`:

```text
unique_core
unique_basin
multiple_core_overlap
multiple_basin_overlap
static_dynamic_conflict
outside_supported_regions
assignment_unresolved
```

One ion is never double-counted in occupancy. Simultaneous membership in multiple
cores is not an exact first hit, and a transition target remains ambiguous until
one unique core is resolved. The result reports overlap volume or sample fraction,
site-specific lower and upper occupancy bounds, and all static/dynamic conflicts.
A dynamic model that produces persistent core overlap or an excessive unresolved
fraction fails the relevant basin- or corridor-validation gate.

## Statistical states, structural complexes, and classes

The kinetic node is a `ValidatedStatisticalState`. Structural reporting may group
several microstates into a `StructuralSiteComplex`, and several complexes may
share one `SiteClass`.

Examples include two opposite wells grouped as one bilateral complex, several
angular minima grouped as one off-center family, or one extended annular state.
Grouping never erases the individual statistical states or their transitions.

Structural classification retains continuous evidence such as normal and radial
displacement, opposite-side partner score, angular multiplicity, annularity,
ring/cage distance, and classification confidence. Borderline cases remain
`general` or `classification_ambiguous`.

# Ensemble-specific basin, corridor, and catalog thermodynamics

Thermodynamic analysis begins only after ensemble, production-regime, sampling, and
state-identity gates are explicit. `ThermodynamicStateDefinition` distinguishes:

```text
tagged_ion_basin_marginal
pooled_symmetry_orbit
site_class_probability
many_ion_occupation_vector
joint_metastable_state
```

It records the state scope, tagged/pooled/joint semantics, multiplicity convention,
standard measure, ensemble, and coordinate Jacobian. Multiplicity correction is used
only when the probability is pooled over equivalent members; applying it to an
already per-state probability is prohibited.

## Provenance-first thermodynamic reporting

Every thermodynamic estimate carries a required `ThermodynamicResultProvenance` record:

```text
estimator_kind
source_trajectory_bundle_signature
source_record_signatures
ensemble_and_target_measure
state_definition_signature
energy_or_force_channel_signature
coordinate_measure_and_Jacobian
estimation_partition_signature
sampling_and_effective_counts
assumptions_and_approximations
uncertainty_method
verification_status
verification_record_signatures
```

A result may be reported as `source_qualified_unverified` when its own estimator-specific
assumptions, sampling, and uncertainty gates pass but no independent channel is available.
Cross-checking is an additional verification step with statuses:

```text
not_requested
unavailable
insufficient
agreed
partially_agreed
disagreed
```

Unavailable verification never erases a valid source-qualified estimate. Disagreement is
retained and prevents promotion to a combined or cross-validated consensus, but both
source estimates remain inspectable with their own provenance. A cross-check may be
mandatory only for a specifically requested `cross_validated` product, never for basic
source-qualified thermodynamic reporting.

## Source energy catalog and thermodynamic channel selection

The source-level `FrameEnergyCatalog` is constructed before STAT0. THERMO0 consumes
that immutable catalog and creates a `ThermodynamicEnergySelection` for the requested
estimand. Raw source energies, bias-corrected energies, reweighting reduced
potentials, conditional potential energies, enthalpies, and extended-system
conserved quantities remain separate.

## NVT and reweighted canonical basin thermodynamics

For validated canonical basin regions $\Omega_i$,

$$
\Delta A_{ij}=-k_{\mathrm B}T
\ln\frac{P_i/g_i}{P_j/g_j}.
$$

A `BasinThermodynamicCertificate` records occupancy and uncertainty, relative
Helmholtz free energy, state/multiplicity definition, complete-system effective block
count, and selection/reweighting provenance. The conditional potential energy

$$
U_i=\left\langle U_{\mathrm{pot}}\mid X\in\Omega_i\right\rangle
$$

is a whole-system conditional mean, not a unique atomic site energy. When both
$\Delta A$ and $\Delta U$ are independently supported,

$$
\Delta S_{ij}=\frac{\Delta U_{ij}-\Delta A_{ij}}{T}
$$

may be reported with propagated uncertainty.

## NpT basin thermodynamics

For a stationary isothermal-isobaric ensemble, probability ratios define relative
Gibbs free energies $\Delta G_{ij}$. Energetic decomposition uses conditional
enthalpy, including the declared pressure-volume term and any required extended-
system convention. NVT notation and potential-energy-only decomposition are not
reused silently.

## NVE basin thermodynamics

For a stationary energy shell, occupancy produces microcanonical state probabilities
and restricted density-of-states or entropy differences, not canonical Helmholtz
free energies. A subsystem-canonical result is separately labeled
`canonical_subsystem_approximation_conditional` and requires a tested
ensemble-equivalence policy [S11-48]. Energy-drifting NVE data may retain descriptive
occupancies and conditional energies while rejecting shell thermodynamics.

## Biased, constrained, and reweighted thermodynamics

A biased result requires bound bias/constraint provenance, an exact target measure,
and configuration weights or cross-evaluated reduced potentials. Raw and corrected
results are both retained. Unavailable companion evidence cannot be interpreted as
zero bias.

## Effective occupancy Hamiltonian

For many-ion systems an optional predictive model may use

$$
E(t)=E_0+\sum_i\epsilon_i n_i(t)
+\frac12\sum_{ij}J_{ij}n_i(t)n_j(t)
+f(\boldsymbol\xi_{\mathrm{framework}}(t))+\varepsilon_t.
$$

`EffectiveHamiltonianPolicy` defines a nested basis hierarchy, symmetry constraints,
regularization, rank/condition thresholds, feature selection using training blocks,
held-out scoring, parameter uncertainty, and sensitivity to framework descriptors.
The framework term may not be chosen using validation blocks. Parameters are
predictive effective coefficients, never a causal or unique DFT atomic-energy
decomposition.

## Transition-region and activation thermodynamics

A mathematical point saddle has zero integrated probability. Thermodynamic analysis
uses a declared finite transition tube, dividing surface, or reaction-coordinate bin.
`SaddleThermodynamicCertificate` records the region measure, independent event
support, probability-density or reweighted support, ensemble-specific activation
potential, conditional energy or enthalpy, uncertainties, recrossing, and committor or
enhanced-sampling provenance.

A `numerically_supported_saddle_candidate` is not a thermodynamic saddle. One-off
passages, unstable density candidates, and unsupported regions cannot produce a
promoted barrier.

## Optional pre-kinetic thermodynamic verification

`ThermodynamicCrossValidationCertificate` is optional and compares noncircular channels
that do not require a fitted kinetic model:

- density/occupancy thermodynamics versus an independently constructed admissible
  force-integrated landscape;
- conditional-energy derivatives across temperature;
- held-out temperature or independent-replica population predictions; and
- WHAM/MBAR estimates when a common target measure and cross-evaluated reduced
  potentials are available.

The certificate records exactly which result was estimated, which independent source was
used for verification, and whether the verification was unavailable, insufficient,
agreed, partially agreed, or disagreed. Absence of a second channel leaves the original
result `source_qualified_unverified`; it does not block reporting.

WHAM or MBAR requires the cross-evaluated matrix $u_k(x_n)$, or an equivalent certified
alchemical/reweighting map, together with overlap diagnostics [S11-43, S11-44]. Native
energies from different species, compositions, or Hamiltonians are insufficient.

Detailed balance, empirical rate bounds, and barrier-rate consistency are not part of
this pre-kinetic certificate. They are owned by Stage 11F0/11F1 and THERMO4B.

# Final temporal residence and transition segmentation

## Raw evidence remains immutable

Every accepted sample retains unsmoothed labels:

```text
site_core_i
site_basin_i
basin_overlap
assignment_conflict_status
transition_support
background
geometry_unresolved
force_unavailable
```

Raw labels are never overwritten by a cleaned event sequence.

## Core-basin hysteresis

For an accepted site $i$, use $C_i\subset B_i$. An ion enters state $i$ only on
reaching $C_i$, remains associated while inside $B_i$, and enters an explicit
transition segment after leaving $B_i$ until another core is reached. This
prevents boundary chatter without nearest-center filling. Core-set and
metastability ideas motivate the separation [S11-29, S11-30].

## Final segmented outputs

The final result contains residence intervals, transition intervals, unresolved
gaps, recrossings, left- and right-censoring, frame-stride sensitivity, static-versus-
dynamic membership, boundary-induced crossing diagnostics, and raw-to-segmented
provenance. The existing
`compute_state_transition_statistics()` backend is reused after segmentation.

Bootstrap and robustness tests use independent trajectories when available, or
contiguous time blocks containing the complete many-ion system. Per-ion
resampling is only a secondary hierarchical diagnostic because ions within one
frame are correlated.

## Observed transition-path ensembles

For a resolved passage, the ion must most recently have occupied source core $C_A$.
The event begins at its final exit from residence basin $B_A$. Its target is the first
subsequently resolved core reached, not a target selected in advance. If $C_C$ is reached
before $C_B$, the event is $A\rightarrow C$.

$$
C_A
\rightarrow
B_A\setminus C_A
\rightarrow
T_A
\rightarrow
B_J\setminus C_J
\rightarrow
C_J,
$$

where $J$ is the first resolved target. A return to $C_A$ before another core is reached
is a failed excursion or recrossing. Unresolved gaps remain unresolved and are not bridged
automatically.

Finite output cadence may prevent an exact first-hit decision. Every event records one of

```text
resolved_first_hit
temporally_bracketed_first_hit
multiple_targets_between_frames
target_ambiguous
gap_interrupted
```

No interpolation is allowed to fabricate a core crossing that is not resolved by the
stored trajectory and declared dynamic-boundary model. Frame-stride sensitivity and the
minimum resolvable event duration are part of the event provenance.

Each `ObservedTransitionEvent` retains:

```text
ion identity
source and target statistical states
start and end frames and times
residence-exit and core-entry boundaries
registered path coordinates
periodic image displacement
ring and cage geometry along the path
available force samples
minimum-density or highest-PMF region encountered
first-hit resolution status and temporal bracket
recrossing, censoring, boundary-induced, and unresolved flags
```

The periodic image displacement

$$
\boldsymbol\lambda_{AB}\in\mathbb Z^3
$$

is part of the event identity. It is derived from the continuous registered unwrapped
path together with registration image bookkeeping, never from wrapped endpoint subtraction
alone. Two events between the same state keys but with different lattice translations are
different periodic-network events.

A `TransitionPathEnsemble` groups comparable successful paths without erasing
physical time. Comparable events must share source and target statistical states,
periodic translation, structural association, compatible unresolved-gap status,
and one validated `RegistrationCompatibilityClass`. The compatibility class proves
that member trajectories share a common registered domain, reference-cell and
lattice gauge, analysis metric, unit convention, and state correspondence while
retaining their distinct source and transform signatures. Identical per-trajectory
registration signatures are not required and would incorrectly prevent independent
runs from contributing to one path ensemble. Any progress-coordinate alignment retains the
original physical time. It reports `single_observed_path`,
`path_ensemble_undersampled`, or `path_ensemble_resolved`. One observed jump
establishes one connection, not a representative pathway, minimum-free-energy
path, directional rate, or detailed balance. Transition-path and core-set ideas
motivate these definitions [S11-8, S11-29, S11-30].

Each path also retains the atom-resolved ring environment along the passage:
ordered M--O distances, oxygen-class contacts, O--O sector crossed,
ring/coordination harmonics, aperture, and puckering. This permits distinct
pathways through chemically inequivalent sectors of the same nominal ring.

Nominally single-ion events are checked for temporal overlap with other mobile-ion
transitions. The event record retains concurrent event identifiers, local
occupancy before/during/after, exchange or swap candidates, and one of
`isolated_single_ion`, `temporally_overlapping`, `candidate_exchange`,
`candidate_concerted`, or `collective_unresolved`. Detection does not yet imply a
many-body kinetic model.

A density shoulder between $A$ and $B$ becomes a third metastable state only if
it has its own reproducible attractor, restoring curvature or equivalent stable
normal confinement, and independent temporal residence. Otherwise it remains
transition support.

## Observed event, path-resolved, and structural networks

Three edge claims remain distinct:

```text
observed_event_edge
path_resolved_edge
transition_state_annotated_edge
```

An `observed_event_edge` is created from a final E6 state-to-state event certificate and
at-risk exposure. It does not require the intermediate geometric path to be resolved.
E6b may enrich that edge with a `path_resolved_edge`; THERMO3B may further attach a
validated transition-state or saddle annotation. Failure of either enrichment never
deletes a valid observed event edge.

The structural/manual candidate network remains separate. Its comparison reports observed
and unobserved structural edges, off-network events, periodic displacement labels, geometry
and occupancy conditioning, unresolved intermediate mechanisms, and path-resolution
status. The structural network never forces observed topology.

# Refactor design

## Dependency direction

The revised dependency graph is:

```text
raw I/O
    -> source normalization and periodic unwrapping
    -> immutable physical AtomisticFrameCollection
    -> Stage C0 spatial frame registration
    -> analysis-specific registered views
        -> pair geometry and topology
        -> displacement and velocity dynamics
        -> scientific density and force fields
        -> site discovery and temporal segmentation
        -> plotting adapters and interactive scenes
```

No scientific analysis module imports Plotly, browser budgets, mesh simplifiers,
or HTML serialization.

## Coordinate-registration ownership

Create a root numerical package, initially compact and later split as needed:

```text
mdstats/coordinates/
    contracts.py
    periodic_gauge.py
    frame_registration.py
    transforms.py
    kinematics.py
    provenance.py
```

The shared owner consolidates the tested translation and reference-cell logic now
spread across `_displacement_common.py`, `_velocity_common.py`,
`framework_dynamics.py`, Stage 11B gauges, and Stage 11C local frames. The local ring and tile modules retain topology-specific gauge construction;
they consume or extend the common transform contracts rather than being replaced
by a generic fit. The registration layer additionally exposes a
`RegisteredStructuralGeometryView` so density-space sites and structural atoms
are never compared in different coordinate systems.

Migration is staged:

1. specify row-vector affine contracts, field transformations, and signatures;
2. implement identity, translation, and reference-cell registration;
3. migrate displacement preparation while preserving numerical regressions;
4. migrate translation-only velocity preparation without adding rotating-frame
   VACF;
5. move density coordinate preparation out of plotting;
6. integrate site-discovery sample catalogs;
7. add advanced rotation/stretch decomposition only after the base contracts are
   validated.

## Incremental scientific-density extraction

The current plotting density code already contains backend-neutral contracts
alongside rendering-specific machinery. Avoid a big-bang move.

### E0a - analysis facade - implemented

Canonical analysis imports and field protocols now wrap the existing scientific
density objects without changing numerical ownership. `mdstats.analysis.density`
provides zero-copy adapters, atomic/framework field bundles, and a scientific-only
resource policy. `mdstats.plotting.density_resource_policy` owns the separate
rendering policy. No rendering class appears in the analysis protocol.

### Density extraction follow-ups D0b-D0d - decomposed into 11E-GR0-GR5

These older density-ownership items are not Stage 11E0b. Stage labels are unique:
Stage 11E0b is the immutable registered raw sample catalog. Revision 44 decomposes the
remaining density move into explicit grid-resolution stages rather than one big-bang
migration:

- `11E-GR0` extracts common cell-metric grid geometry, periodic spread, reciprocal
  resolution, and artificial-broadening diagnostics into analysis ownership;
- `11E-GR1` extracts target-shape, finest-feasible-shape, deterministic nested-grid,
  field-signature reuse, and physical-resolution-first/backend-second planning;
- `11E-GR2` adapts atomic and framework plotting to the common layer while preserving
  plotting's visual smearing and browser/mesh policies;
- `11E-GR3` integrates a fixed-kernel scientific refinement ladder into E1/E2 and
  emits separate field, basin, and corridor convergence certificates;
- `11E-GR4` executes that ladder only on discovery/model-selection blocks and freezes the
  numerical hypothesis before held-out basin or corridor validation; and
- `11E-GR5` completes D0b-D0d by moving the remaining numerical owners, making plotting
  consume analysis-owned producers, and removing compatibility ownership only after
  dense, sparse, scientific, and visual regressions pass.

Scientific memory/work limits and rendering/mesh/browser budgets remain disjoint.
Compatibility imports remain until `11E-GR5`; no stage may force a coordinated rewrite
of scientific numerics, sparse execution, meshing, browser admission, and public APIs in
one release.

The intended package layout is:

```text
mdstats/analysis/density/
    contracts.py
    kernel.py
    sparse_reference.py
    block_sparse.py
    planning.py
    diagnostics.py
    hdr.py

mdstats/analysis/site_samples.py
mdstats/analysis/site_density.py
mdstats/analysis/site_modes.py
mdstats/analysis/site_force.py
mdstats/analysis/site_validation.py
mdstats/analysis/site_segmentation.py
mdstats/analysis/observed_site_network.py
```

## Statistical bandwidth, grid realization, and partial numerical refactor

The KDE covariance $\Sigma_h$ - or scalar scale $h$ on one fixed metric shape - the
analysis grid interval $\Delta$, and the rendering mesh tolerance are distinct:

$$
\Sigma_h\neq\Delta\neq\text{mesh tolerance}.
$$

A direct normalized triclinic image sum is the numerical oracle. `KernelMetricDefinition`
and `PeriodicKernelDefinition` fix the coordinate measure, covariance, image truncation,
and quadrature. Dense and block-sparse realizations must preserve that operator. The same
certified scientific field drives attractor discovery, basin integration, uncertainty
diagnostics, and optional rendering.

### Existing atomic-density machinery is the common numerical oracle

The tested atomic-density implementation already owns mature backend-neutral algorithms
for:

- grid-shape construction from target Cartesian interval in an oblique periodic cell;
- realized Cartesian grid intervals and logical node/voxel counts;
- periodic Frechet means and periodic item-spread diagnostics;
- reciprocal-resolution diagnostics;
- cloud-in-cell assignment covariance;
- discrete Gaussian-stencil and combined artificial broadening;
- target-shape and finest-feasible-shape search under scientific voxel/work budgets;
- physical-grid selection before dense or local-sparse backend selection; and
- immutable serializable resolution records and deterministic field reuse metadata.

Those algorithms are not intrinsically rendering operations. Their current
`mdstats.plotting` ownership is a compatibility state. Revision 44 therefore chooses a
**partial refactor**: move the common mathematics into `mdstats.analysis.density`, retain
old plotting imports through adapters, and keep plotting-specific and Stage-11-specific
policies separate.

### Plotting and scientific refinement remain separate policies

Atomic-density plotting may retain its visual default

$$
\sigma=c\,\max_i\Delta_i,
$$

and may refine grid spacing and visual Gaussian width together when artificial smearing
would dominate the rendered cloud. It selects one production grid and may display the
finest feasible budget-limited result with a warning.

Stage 11 scientific convergence must instead hold the kernel hypothesis fixed:

$$
\Sigma_h=\text{constant},\qquad
\Delta^{(0)}>\Delta^{(1)}>\Delta^{(2)}>\cdots .
$$

Changing $\Sigma_h$ and $\Delta$ together would confound physical smoothing-scale
uncertainty with numerical discretization error. Stage 11 therefore uses plotting's
common geometry, broadening, resource, and backend machinery. Stage 11 never uses
plotting's adaptive bandwidth selection or one-grid acceptance policy.

### Scientific resolution and convergence certificates

One combined topology verdict is insufficient. The scientific refinement result owns
three orthogonal certificates:

```text
DensityFieldResolutionCertificate
BasinGridConvergenceCertificate
CorridorGridConvergenceCertificate
```

`DensityFieldResolutionCertificate` records exact grid shapes, realized intervals,
fixed kernel covariance and signature, $\Delta/\sigma$ or reciprocal metrics, CIC and
stencil broadening, normalization residuals, backend, scientific resource limits, and
budget limitation.

`BasinGridConvergenceCertificate` records candidate correspondence, attractor-count
stability, anchor displacement, basin overlap, integrated probability changes,
split/merge and unmatched candidates, and acceptance or unresolved reasons.

`CorridorGridConvergenceCertificate` records density-boundary adjacency, corridor
location and width, bottleneck-density changes, split/merge and correspondence ambiguity,
and whether a stable refinement regime was reached. A valid scientific outcome may be:

```text
field numerics: converged
basins: converged
transition corridors: unresolved
```

Basin convergence never implies corridor convergence. This distinction is mandatory for
the current Na-LTA pilot, whose basin identities are more stable than its numerical
saddle adjacency.

### Budget and sampling rules

The common planner resolves physical grid requirements before selecting dense versus
local-sparse storage. A scientific caller may receive a budget-limited ladder, but if the
requested convergence criterion is not reached the status is
`unresolved_due_to_resolution_budget`; the finest affordable field is not promoted as
authoritative merely because it can be rendered.

The grid ladder is selected and executed only within SAMP0 discovery/model-selection evidence.
Candidates are frozen before held-out assignment. An optional all-data final refit is a
new signed product and does not inherit held-out parameter-certification evidence.
Grid convergence concerns discretization of one fixed statistical hypothesis; SAMP1/SAMP2
independently determine whether basins and corridors have adequate trajectory support.

## Position-force sample catalog

The global sample catalog remains compact and does not eagerly materialize every
ion-frame-ring descriptor. It retains species, atom and frame identities,
registered positions, force evidence, evidence masks, weights, source and
registration signatures, and stationarity provenance.

Structural annotations are lazy views created after a statistical candidate is
associated with a fixed ring or tile identity. This preserves global discovery
before semantic interpretation and avoids an $N_{\mathrm{ion}}N_{\mathrm{frame}}N_{\mathrm{ring}}$
materialization.

## Existing manual-model branch

`ring_site.py`, `site_kinetic_network.py`, and `site_assignment.py` remain an
explicit manual or transferred-model branch. Current public names may remain
through the pre-release series, but documentation must state that their site
locations and basin widths are supplied rather than discovered.

## Interactive analysis scene

The interactive scene consumes registered scientific fields and validated site
results. It may overlay the framework, tiles, rings, density, attractor lineages,
basin/core surfaces, mean-force vectors, residence segments, and semantic labels.
The scene is diagnostic; every scientific result remains usable without
rendering.

# Revision-47 authoritative typed dependency graph

The machine-readable companion `stage11_dependency_graph.json` is normative. Revision 47
introduced the typed-edge graph retained by architecture revision 51 rather than treating execution order, promotion gates, optional
enrichment, and verification as one relationship. Required acyclicity is evaluated over
`source_identity_requires`, `execution_requires`, and unconditional
`promotion_requires` edges. The edge vocabulary is:

```text
source_identity_requires
execution_requires
promotion_requires
conditional_requires
optional_enrichment
optional_verification
supersedes
replay_triggers
```

A condition-bearing edge records its predicate and product scope. A bounded gating replay
creates a new signed `StateModelGeneration`; it is not a cycle within one generation.

```text
SourceTrajectoryBundleIdentity
    -> SOURCE_BYTES and SOURCE_COORDINATES views of the same source
    -> ENS0 controls/energies and C0 coordinates retain the same bundle signature

ENS0 -> ENS1 -> STAT0 -> STAT1 -> STAT2
C0 + Part I -> E0b-RAW
STAT1 + E0b-RAW -> SAMP0 EvidenceCrossfitPartition

E0a -> GR0 -> GR1 -> GR2
SAMP0 + GR1 -> E1 -> E2 per-realization candidates
E2 + GR1 -> GR3 convergence evidence
GR3 + SAMP0 -> GR4 FrozenCandidateCatalog
GR4 -> STAT3, E3A, E4
STAT2 + STAT3 + E3A -> E3B where canonical/reweighted force thermodynamics are admissible
E4 + GR4 -> SAMP1 -> E5 -> E5a -> optional E5b
E4 + E5 + GR3 -> SAMP2
SAMP1 + SAMP2 -> SAMP3

THERMO0 -> THERMO1 -> optional THERMO2
THERMO1/2 results carry mandatory ThermodynamicResultProvenance.
THERMO4A is optional verification, not a prerequisite for source-qualified reporting.

STAT2 + STAT3 + GR3 + SAMP1 -> PMF_DENSITY
STAT2 + STAT3 + E3B + GR3 + SAMP1 -> PMF_FORCE
PMF_DENSITY + PMF_FORCE -> optional PMF_CROSSCHECK
No force record is required for PMF_DENSITY.

SAMP2 + GR3 + THERMO0 -> THERMO3A
E6 -> optional E6b
E6b + THERMO3A -> optional THERMO3B

E5 + a signed RateCandidateEdgePolicy -> RATE_EDGE_UNIVERSE
SAMP2 and M2 may optionally enrich that universe.
E6 -> E7 observed-event network
E6 + E7 -> KSAMP0 KineticCrossfitPartition
KSAMP0 + E7 -> E9A -> G0
KSAMP0 + RATE_EDGE_UNIVERSE + E6 + E7 + G0 -> F0
F0 + held-out kinetic-model-validation episodes -> E9B
Zero-event bounds attach to RateCandidateEdge records, not only observed edges.

THERMO3B + G0 -> F1
F0 + E9B + optional independent populations -> optional THERMO4B
F0 + E9B + G0 -> G1 -> H -> I

E8b product nodes are independent:
    E8B_BASIN_GEOMETRY from E5/SAMP1/GR3
    E8B_BASIN_THERMO from THERMO1 and optional THERMO2/THERMO4A verification
    E8B_CORRIDOR from SAMP2/GR3
    E8B_TRANSITION_REGION from THERMO3A
    E8B_PATH from E6b
    E8B_TRANSITION_STATE from THERMO3B
    E8B_EVENT_NETWORK from E7
    E8B_KINETIC from F0/E9B and optional G1/F1/THERMO4B

E8a remains a cross-cutting milestone dossier. PMF, thermodynamic verification, paths,
and rates are optional sub-dossiers and do not gate earlier ENS/STAT/GR/SAMP milestones.
```

`QualityDiagnosticBlockPartition`, `EvidenceCrossfitPartition`, and
`KineticCrossfitPartition` are distinct signed objects. Control-inferred dynamics,
realized ensemble consistency, trajectory quality, source-qualified thermodynamic
results, optional verification, and method-specific admissibility remain separate
records.

# Planned persistent data model

The new stages introduce source-general immutable records:

```text
SourceTrajectoryBundleIdentity
SimulationControlBundleManifest
SimulationRunControls
SimulationControlCertificate
RealizedEnsembleConsistency
EnsembleInferencePolicy
VaspRunControls
NumericalMDQualityControls
FrameEnergyCatalog
IonicTemperatureDefinition
IonicTemperatureStatistics
TrajectoryQualityPolicy
TrajectoryQualityVerdict
ProductionWindowPolicy
QualityDiagnosticBlockPartition
ProductionRegimeCatalog
EvidenceCrossfitPartition
KineticCrossfitPartition
PmfAdmissibilityCertificate
EvidenceAdmissibilityOverlay
SamplingAdequacyPolicy
FeatureCorrespondencePolicy
GridConvergenceStoppingPolicy
CommonDensityGridPolicy
ScientificGridRefinementPolicy
DensityFieldResolutionCertificate
BasinGridConvergenceCertificate
CorridorGridConvergenceCertificate
PerRealizationCandidateCatalog
FrozenCandidateCatalog
FinalRefitCatalog
LocalMechanicalForceRefinement
ThermodynamicMeanForceCertificate
BasinSamplingCertificate
TransitionCorridorSamplingCertificate
PreliminaryCorridorSupport
FinalTransitionEventCertificate
RateCandidateEdgePolicy
RateCandidateEdge
RateCandidateEdgeUniverse
ObservedEventEdge
PathResolvedEdge
TransitionStateAnnotatedEdge
ObservedEventNetwork
DiagnosticKineticModel
PreRateKineticAdequacyCertificate
StateModelGeneration
GenerationReplayPlan
GenerationTerminationCertificate
GatingModelSelectionCertificate
EmpiricalRateCertificate
PostFitKineticAdequacyCertificate
BarrierDerivedRateCertificate
FinalGateModelSelectionCertificate
KineticPropagationResult
IntegratedGroundGateDossier
CrossDatasetComparisonCertificate
DiscoveryScopeCertificate
ThermodynamicStateDefinition
ThermodynamicPotentialDefinition
ThermodynamicEnergySelection
ThermodynamicResultProvenance
EffectiveHamiltonianPolicy
BasinThermodynamicCertificate
StaticTransitionRegionThermodynamics
TransitionStateValidationCertificate
SaddleThermodynamicCertificate
DensityPmfCertificate
ForcePmfCertificate
PmfCrossCheckCertificate
ThermodynamicCrossValidationCertificate
KineticThermodynamicConsistencyCertificate
RateBoundModel
```

Every thermodynamic certificate contains `ThermodynamicResultProvenance`. Verification is
an optional linked record; its absence is metadata, not automatic rejection. Every source-
derived record carries `SourceTrajectoryBundleIdentity`. Every model-generation replay
carries parent/child signatures and a bounded termination certificate.

The canonical diagnostic status registry is:

```text
resolved | unresolved | insufficient | rejected | unavailable | not_applicable
```

Promotion decisions are:

```text
accepted | conditional | blocked | rejected
```

Thermodynamic verification statuses are:

```text
not_requested | unavailable | insufficient | agreed | partially_agreed | disagreed
```

Domain outcomes such as `NVE`, `nonstationary`, `spatial_density_only`,
`source_qualified_unverified`, `cross_validated`, or `observed_partial_catalog` are
separate values, not replacements for diagnostic status.

# Revised implementation sequence

This section follows the revision-47 typed dependency graph and its machine-readable companion. Status and historical
release chronology are descriptive metadata; they do not override the acceptance
gates or the authoritative dependency map.

## Part I structural prerequisites - Stages 11A-D implemented

Stages 11A, 11B, 11C1, 11C2, 11C3, and 11D are implemented and owned by
`framework_ring_architecture.{md,pdf}`. Part II records their completion only as
a prerequisite; detailed deliverables and remaining general-topology work are not
duplicated here.

## Stage 11E-M1/11E-M2 - manual and transferred site models - implemented foundation

The existing site-topology/structural-network implementation is documented as
legacy/manual Stage 11E-M1, and the explicit trajectory assignment implementation
as Stage 11E-M2. Their modules and public APIs remain unchanged. Their
specification headers use the E-M names so that historical statements such as
"Stage 11E2 complete" cannot be confused with the new deterministic-attractor
Stage 11E2. Site locations and basins in this branch are supplied explicitly.

## Stage C0A1 - source semantics and periodic lattice gauge - implemented

Deliverables:

- source position, velocity, force, and box-origin frame semantics;
- cell handedness and determinant checks;
- periodic-axis continuity;
- lattice-basis continuity and optional unimodular gauge reconciliation;
- explicit rejection of unsupported basis changes;
- explicit-matrix and selected-source-frame reference-cell definitions;
- full-periodicity/full-rank scope for initial reference-material registration;
- separate geometric-force and PMF-force admissibility contracts.

Acceptance gate:

- a basis relabeling is never interpreted silently as physical strain;
- unknown field semantics block only claims that require them.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.coordinates.contracts` owns normalized source-field semantics,
  force-source provenance, geometric/PMF admissibility, reference-cell
  definitions, deterministic schemas, and immutable digests;
- `mdstats.coordinates.periodic_gauge` owns determinant, condition, handedness,
  periodic-axis, and basis-continuity validation;
- nontrivial unimodular relabelings are rejected by default and reconciled only
  under an explicit option with the integer matrix retained;
- normalized collections now persist source-field semantics, while legacy
  collections remain readable through conservative inference; and
- focused tests cover rejection, reconciliation, partial-claim availability,
  reference-cell scope, and deterministic signatures.

C0A1 itself does not construct `M_t`, `b_t`, registered coordinates, translation
gauges, or transformed forces; those products are supplied by the following C0A2 layer.

## Stage C0A2 - affine registration and coordinate products - implemented

Deliverables:

- affine row-vector contracts with explicit source and registered center semantics;
- physical, periodic matched-displacement translation, and composed
  reference-material-plus-translation policies;
- dedicated `RegistrationFitMetric`, separate immutable `AnalysisGeometryMetric`,
  and certified triclinic closest-image solvers under their declared metrics;
- torus reference-translation solution, segment-continuous `TranslationBranchLift`,
  residual, competing-branch separation, reset, and ambiguity diagnostics;
- registered cells and fixed-domain checks;
- unwrapped Cartesian, wrapped fractional, and image-shift products;
- position, displacement, and force transformations;
- immutable signatures, diagnostics, and round-trip validation.

Acceptance gate:

- $G_t=H_tM_t$ for every valid frame;
- coordinate round trips and force-work invariance pass;
- singular, basis-inconsistent, and incompatible transforms fail closed.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.coordinates.metric_geometry` owns immutable `RegistrationFitMetric`
  and `AnalysisGeometryMetric` contracts and a finite, singular-value-certified
  triclinic closest-image enumeration with explicit tie diagnostics;
- `mdstats.coordinates.registration` owns physical, translation-registered, and
  reference-material affine policies, persistent reference sets and weights,
  matched periodic translation fitting, trajectory-segment branch lifting,
  fixed-domain validation, and registered coordinate products;
- force fields are transformed as affine covectors and validated by work
  invariance, while structure-fitted translation retains conservative geometric
  and PMF admissibility statuses;
- independent ensembles receive no invented temporal branch continuity; and
- focused tests cover skew-cell closest images, exact ties, periodic drift across
  boundaries, variable-cell reference-material maps, segment resets, ensembles,
  unimodular source-basis reconciliation, serialization, and public exports.

Stages 11C3, C0A3, C0B, and 11E0a exist in the baseline runtime. Current normative progression is defined only by the revision-47 typed dependency graph.

## Stage 11C3 - atom-resolved structural ring boundary and harmonics - implemented

Deliverables:

- persistent per-atom T/O boundary records and generic chemical environments;
- optional validated O(1)/O(2)/O(3 aliases for LTA;
- exact ordered structural sequences;
- exact unweighted cyclic-index spectra with correct even-ring Nyquist handling;
- rank-safe actual-angle spectra with explicit weights, rank, condition,
  regularization, and unresolved status;
- separate boundary-measure angular moments and weighted actual-angle fits;
- raw and normalized amplitudes;
- canonical dihedral phase gauges and phase-defined uncertainty;
- per-frame symmetry-breaking and oxygen-class splitting diagnostics;
- explicit radial-center convention and uncertainty;
- angular-coordinate validity and fail-closed singularity diagnostics.

Acceptance gate:

- an alternating S6R recovers the cyclic $m=3$ component exactly;
- an irregularly spaced ring does not force the same sequence into a pure
  physical-angle $m=3$ component;
- underdetermined mode sets fail closed;
- cyclic permutation, reversal, rigid motion, and periodic wrapping follow the
  declared dihedral and geometric transforms;
- phase becomes undefined when amplitude support is insufficient;
- crystallographic aliases fail closed when the framework profile is incompatible.

This stage owns no M--O/M--T fingerprint and no species-dependent site label.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.ring_boundary` owns immutable per-atom T/O boundary records,
  ordered neighboring-T chemistry, generic oxygen-environment signatures, and
  exact-source optional LTA O(1)/O(2)/O(3) alias profiles;
- exact equal-atom DFT descriptors retain the complete real-sequence mode set
  with signed even-ring Nyquist coordinates and explicit dihedral transforms;
- arc-length Voronoi boundary moments and equal-atom/arc-length physical-angle
  fits remain distinct, with rank, condition, regularization, residual, phase
  support, and uncertainty provenance;
- singular projected atoms and non-identifiable mode sets fail closed without
  arbitrary angles or pseudoinverse coefficients;
- framewise outputs retain class splitting, radial symmetry breaking, and
  reference phase/amplitude continuity while exact Cartesian coordinates remain
  authoritative; and
- focused tests cover synthetic serrated rings, dihedral transforms, rank and
  singularity failures, source-bound aliases, serialization, resource preflight,
  rigid rotation, and all 58 LTA reference rings.

Stage C0A3 is implemented below.

## Stage C0A3 - registered structural-view integration - implemented

Deliverables:

- apply the resolved Stage C0 transform to persistent T/O, ring, tile, and cage atoms;
- reconstruct registered orthonormal ring frames from transformed atoms using
  the standard least-squares closest-plane and polygon constructions
  [S11-15, S11-16];
- retain linked physical and registered structural embeddings;
- integration tests coupling Stage 11C3 boundary identities to registered views;
- immutable structural-view signatures and unresolved-frame diagnostics.

Acceptance gate:

- site-space association never mixes registered positions with physical structural coordinates;
- physical bond lengths and apertures remain available unchanged;
- non-rigid affine maps reconstruct, rather than affinely distort, local orthonormal frames.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.registered_structural_view` owns one immutable,
  source-bound integration product joining the collection, C0A2 registration,
  compatible C2 ring geometry, C3 atom-resolved boundaries, and optional
  compatible tiling geometry;
- every ring view exposes separately named physical and registered children, so
  physical distances, apertures, areas, perimeters, planarity, and T--O metrics
  remain unchanged and cannot be confused with registered projected descriptors;
- persistent T/O atom images are transformed by the exact resolved affine map,
  then their registered fractional images are independently certified against
  the registered cell;
- registered ring centers and orthonormal frames are reconstructed from the
  transformed oxygen polygon and persistent cyclic-origin atom; transformed
  physical axes are retained only as a distortion diagnostic;
- optional tile/cage centers, tile-face vertices and reconstructed normals, and
  window centers share the same registration while retaining physical tiling
  measures unchanged;
- trajectory orientation continuity is diagnostic, respects explicit
  registration segment resets, and is not inferred for independent ensembles;
- unresolved geometry, identity mismatch, source mismatch, resource excess,
  serialization tampering, and degenerate transformed polygons fail closed; and
- focused tests cover all 58 LTA ring identities, identity and non-rigid maps,
  periodic registered images, tiling integration, reset semantics, ensembles,
  serialization, resource preflight, and public exports.

Stage C0A3 is complete.

## Stage C0B - consumer migration - implemented

Deliverables:

- displacement preparation migrated with exact regression compatibility;
- translation-only velocity preparation migrated without changing VACF semantics;
- atomic density and framework plotting consume shared registration;
- compatibility adapters for current public options.

Acceptance gate:

- current MSD and density reference results remain unchanged within declared
  tolerance;
- pair geometry remains on the physical policy;
- plotting does not own scientific drift removal.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.coordinates.consumer_adapters` owns immutable, source-bound
  compatibility products for displacement, velocity, and plotting consumers;
- laboratory and reference-material displacement preparation delegates its
  affine map to C0A2 and retains the exact historical optional COG/COM
  zero-centering translation;
- translation-only velocity preparation retains the exact instantaneous
  COG/COM drift used by VACF, spectra, and velocity-derived transport while
  recording its registration-policy provenance separately;
- `framework_dynamics.py` prepares one coordinate view before framework
  averaging, trajectories, atomic density, framework vertex density, or
  framework edge density, and no longer computes a scientific drift vector;
- material, framework-registered, and laboratory plotting modes retain their
  historical numerical coordinates and public options;
- pair geometry is declared physical and is not replaced by display or
  reference-material geometry;
- larger smooth variable-cell changes admitted historically are handled by an
  explicit compatibility continuity envelope, while certifiable unimodular
  basis relabelings remain fail-closed;
- very large historical unwrapped absolute coordinates use an explicit
  floating-point-ULP floor for round-trip certification without changing the
  returned consumer coordinates;
- partial-periodic material plotting remains available so the owning density
  preflight can issue its more specific validation; and
- focused regression tests compare the migrated products against the legacy
  coordinate, velocity, plotting, and atomic-density oracles and verify public
  API compatibility, immutability, and provenance.

Stage 11E0a is complete.

## Stage 11E0a - scientific density facade and ownership boundary - implemented

Deliverables:

- analysis-owned `ScientificDensityField3D` and periodic-node protocols;
- zero-copy adapters and deterministic scientific field bundles;
- canonical atomic and framework density preparation entry points;
- lazy compatibility imports for current numerical option and field classes;
- `ScientificDensityResourcePolicy` containing only field-construction limits;
- plotting-owned `DensityRenderingResourcePolicy` containing only browser/mesh limits;
- explicit temporary numerical-owner and permanent scientific-owner metadata.

Acceptance gate:

- atomic and framework fields match the current numerical oracle exactly;
- adapters retain the exact current field object and storage;
- scientific preparation invokes no mesh extraction or browser admission;
- Plotly and scikit-image remain unnecessary for field construction;
- rendering options are absent from the analysis facade; and
- existing plotting APIs remain compatible.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.protocols` defines the canonical structural field
  protocols, zero-copy compatibility adapter, bundle, immutable ownership
  metadata, and contract signatures;
- `mdstats.analysis.density.resources` defines runtime-resolvable scientific
  limits without mesh faces, Plotly traces, browser payloads, or HTML budgets;
- `mdstats.analysis.density.facade` delegates to the unchanged atomic and
  framework numerical producers and wraps their exact result objects;
- `mdstats.plotting.density_resource_policy` owns the explicitly separate
  rendering policy;
- canonical analysis imports expose current numerical contracts lazily but omit
  all 3-D render-option classes; and
- focused tests compare dense atomic and framework vertex/edge fields against
  the current oracle and guard against optional rendering imports or browser
  admission.

Stage 11E0a is complete. Stage 11E0b is implemented below.

## Stage 11E-ENS0 - source-control bundle and energy-channel reconstruction

Deliverables:

- `SimulationControlBundleManifest`;
- source-general `SimulationRunControls` protocol and versioned VASP adapter;
- explicit-versus-effective control precedence;
- companion-file state classification;
- source-level `FrameEnergyCatalog` with exact channel names and units;
- `NumericalMDQualityControls` reconstructed from explicit and effective
  `vasprun.xml` parameters, including timestep, electronic convergence, precision,
  projection, cutoff, symmetry, and per-step SCF traces;
- user-label conflict diagnostics.

Acceptance gate:

- the Na-LTA fixture resolves the misleading comment as non-authoritative;
- `MDALGO=2`, `SMASS=-3`, and `ISIF=2` enter the decision trace;
- missing companion evidence is classified, not silently treated as absent;
- every conservation input channel is available to STAT0 before STAT0 executes;
- the Na-LTA fixture exposes `POTIM`, `EDIFF`, `PREC`, `LREAL`, `ROPT`, `NELM`,
  present ionic-step count, and per-step electronic-step counts from the XML without
  consulting the `SYSTEM` comment.

Implementation status: complete in `0.20.17a0`. The runtime owners are
`mdstats.io.source_controls`, `mdstats.io.vasp_controls`, and the metadata integration in
`mdstats.io.vasp`. Stages 11E-ENS1 through 11E-STAT2 are now implemented.

## Stage 11E-ENS1 - ensemble, control, and force-provenance certificate

Deliverables:

- `SimulationControlCertificate` with ensemble, propagator, thermostat, barostat,
  driven/bias/constraint, cell, and force-provenance outcomes;
- versioned `EnsembleInferencePolicy` and complete decision trace;
- initial-velocity and continuation provenance;
- explicit unresolved outcomes for unsupported or incomplete source bundles.

Acceptance gate:

- source controls, not comments, determine the outcome;
- thermostat friction is `not_applicable` when the thermostat is disabled;
- bias/constraint nonuse is asserted only from affirmative source evidence;
- inconsistent controls block only ensemble-dependent methods; descriptive analysis may
  continue when STAT0 hard-integrity checks pass.

Implementation status: complete in `0.20.18a0`. Runtime owners are
`mdstats.io.control_certificates`, `mdstats.io.vasp_ensemble`, and ENS1 metadata
integration in `mdstats.io.vasp`. The permanent specification is
`docs/specs/io/vasp_ensemble_certificate_spec.md`.

## Stage 11E-STAT0 - ionic temperature, integrity, conservation, and quality verdict

Deliverables:

- source-bound `IonicTemperatureDefinition` and equipartition-derived per-frame ionic
  temperature;
- weighted mean, standard deviation, autocorrelation-aware confidence interval, block
  stability, and drift statistics in `IonicTemperatureStatistics`;
- ensemble-specific conserved or controlled quantity reconstructed from the ENS0
  `FrameEnergyCatalog`;
- dimensionless drift, slope significance, residual fluctuation, cell, stress,
  momentum, equipartition, SCF quality, frame completeness, collision, and runaway
  diagnostics;
- signed `TrajectoryQualityPolicy` and three-level `TrajectoryQualityVerdict`;
- `TrajectoryDegradedQualityWarning` and `TrajectoryIntegrityError` execution
  contracts;
- `RealizedEnsembleConsistency`, separate from the control-inferred dynamics mode;
- a required/optional diagnostic matrix classifying each channel as
  `hard_integrity_required`, `verdict_critical`, `method_specific`, or `optional`.

Acceptance gate:

- ionic temperature is computed as $2K_{\mathrm{ion}}/(f_{\mathrm{ion}}k_{\mathrm B})$
  from a signed active-DOF definition;
- the time mean, standard deviation, and correlated confidence interval are all
  reported rather than replacing one another;
- NVE, NVT, NpT/NpH, biased, and driven cases use distinct conserved or controlled
  quantities;
- no generic total-energy convention is guessed and smooth drift remains visible after
  detrending;
- `strictly_qualified` proceeds without a quality warning;
- `degraded_quality` proceeds with one warning and immutable downstream flags;
- only `unqualified` blocks scientific execution by default;
- fewer than the required independent blocks may degrade confidence or return an
  `insufficient` diagnostic, but it does not become `unqualified` unless an independent
  hard integrity failure is present.

Implementation status: complete in `0.20.19a0`, with the default NVE drift policy revised in `0.20.20a0` to strict/degraded/hard thresholds of 1 and 26 meV/(atom ps). Runtime owners are `mdstats.io.trajectory_quality`, `mdstats.io.vasp_quality`, and full-source metadata integration in `mdstats.io.vasp`. The permanent specification is `docs/specs/io/trajectory_quality_spec.md`.

## Stage 11E-STAT1 - source-observable production-regime catalog

Deliverables:

- complete-system block construction and uncertainty;
- predeclared energy, temperature, cell, stress, momentum, and framework-observable
  stability tests;
- configured change-point detection and contiguous `ProductionRegimeCatalog`;
- selection-conditioning and external-continuation provenance.

Acceptance gate:

- adaptive E1 site density is not used to select the production window;
- user-declared continuation boundaries are tested rather than trusted;
- insufficient blocks yield `insufficient` and do not by themselves make the source
  catastrophic;
- strictly qualified and degraded-quality trajectories may both contain usable regimes;
- unqualified trajectories cannot create a scientific production regime;
- multiple regimes remain separate.

Implementation status: implemented in `0.20.20a0`. Runtime owners are
`mdstats.io.production_regimes`, `mdstats.io.vasp_stationarity`, and full-source
metadata integration in `mdstats.io.vasp`. The permanent specification is
`docs/specs/io/production_regime_catalog_spec.md`. Stage 11E-STAT2 is implemented in
`0.20.21a0`.

## Stage 11E0b - immutable registered raw sample catalog

Current implementation provides compact frame-major registered species samples,
represented-time weights, topology segments, source and registration signatures,
raw position/force availability, and lazy structural annotations.

Revision-47 contract:

- E0b owns raw availability and geometry masks only;
- it references but does not infer `SimulationControlCertificate`,
  `ProductionRegimeCatalog`, or `PmfAdmissibilityCertificate`;
- later `EvidenceAdmissibilityOverlay` objects select position, force, temporal,
  canonical, microcanonical, or reweighted subsets without mutating E0b;
- no field may encode an untested stationarity assertion as scientific evidence;
- unresolved prerequisite certificates retain descriptive raw evidence but block the
  corresponding scientific interpretation.

Acceptance gate:

- raw-source, registration, atom, frame, topology, and represented-time identities
  replay exactly;
- scientific masks cannot be produced without exact prerequisite signatures;
- user labels cannot alter a mask.

## Stage 11E-STAT2 - preliminary ensemble-specific admissibility

Deliverables:

- `PmfAdmissibilityCertificate` and initial `EvidenceAdmissibilityOverlay`;
- explicit permissions for descriptive density, microcanonical occupancy,
  canonical/NpT/reweighted landscapes, conditional force, and diagnostic-only use;
- temperature, energy-shell, bias/reweighting, and approximation provenance.

Acceptance gate:

- NVE data are not silently converted to a canonical PMF;
- NpT uses Gibbs/enthalpy semantics;
- unresolved stationarity blocks thermodynamic promotion while retaining descriptive
  spatial evidence;
- every permission is policy- and source-bound.

Implementation status: implemented in `0.20.21a0`. Runtime owners are
`mdstats.io.admissibility`, `mdstats.io.vasp_admissibility`, and full-source metadata
integration in `mdstats.io.vasp`. The permanent specification is
`docs/specs/io/ensemble_admissibility_spec.md`. The following runtime stage is Stage
11E-SAMP0.

## Stage 11E-SAMP0 - cross-fitted block and effective-sample foundation

Deliverables:

- `QualityDiagnosticBlockPartition` remains owned by STAT1;
- one `EvidenceCrossfitPartition` contained within an accepted production regime;
- explicit `discovery`, `model_selection`, `basin_validation`,
  `corridor_validation`, `thermodynamic_estimation`, `thermodynamic_validation`, and
  optional `final_refit` domains;
- a signed nested-selection alternative confined to discovery/model-selection data;
- local decorrelation times, complete-system effective sample counts, represented time,
  and block/replica support;
- `SamplingAdequacyPolicy` and an implementation-complete
  `FeatureCorrespondencePolicy`.

The initial correspondence preset `stage11_feature_correspondence_v1` uses the normalized
cost

$$
C_{ab}=w_d(d_{ab}/\sigma_{\min})^2+w_o(1-O_{ab})+w_p|P_a-P_b|/P_{\mathrm{scale}},
$$

with versioned weights, admissible point/ridge type pairs, maximum cost, ambiguity margin,
deterministic tie breaking, and explicit split/merge/unmatched outcomes. Exact preset
values are serialized and never inferred from feature order.

Acceptance gate:

- all mobile ions from one frame remain in one complete-system block;
- model selection cannot inspect held-out validation domains;
- held-out blocks never change bandwidth, grid, candidate count, or correspondence;
- thermodynamic estimation and optional verification are distinguished;
- final all-data refits receive new signatures and do not inherit parameter-validation
  certificates.

Implementation status: implemented in `0.20.22a0`. Runtime owner is
`mdstats.io.sampling_crossfit`; the permanent specification is
`docs/specs/io/sampling_crossfit_spec.md`. The following completed runtime stage is Stage
11E-GR0.

## Stage 11E-GR0 - common grid geometry and numerical diagnostics

Deliverables:

- analysis-owned cell-metric grid-shape and realized-interval functions;
- periodic spread and Frechet-mean diagnostics;
- reciprocal-resolution diagnostics;
- CIC, Gaussian-stencil, and effective artificial-broadening diagnostics;
- analysis-domain density numerical exceptions;
- compatibility aliases preserving the current plotting imports and serialized values.

Acceptance gate:

- exact numerical and serialization parity with the tested atomic-density oracle;
- oblique-cell Euclidean geometry is preserved;
- no Plotly, mesh, browser, or graph-specific policy is imported by the common layer;
- graph-facing exceptions remain adapter behavior rather than common numerical types.

Implementation status: implemented in `0.20.23a0`. Runtime owners are
`mdstats.analysis.density.grid_geometry`, `mdstats.analysis.density.diagnostics`,
`mdstats.analysis.density.stencil_diagnostics`, and
`mdstats.analysis.density.broadening`; the permanent specification is
`common_grid_diagnostics_spec.md` under `docs/specs/analysis/density/`. The
following completed runtime stage is Stage 11E-GR1.

## Stage 11E-GR1 - common budgeted planner and deterministic grid ladder

Deliverables:

- target Cartesian interval to grid-shape planning;
- finest-feasible shape search under scientific limits;
- deterministic nested-grid ladder generation;
- physical-resolution-first and backend-second planning;
- identical-field signature reuse and cache keys;
- explicit budget-limited status without scientific promotion.

Acceptance gate:

- dense and local-sparse plans represent the same logical grid and fixed kernel;
- requested and realized intervals are both retained;
- a ladder that cannot reach its requested finest level remains signed as budget-limited;
- browser and mesh budgets cannot change the scientific grid plan.

Implementation status: implemented in `0.20.24a0`. Runtime owner is
`mdstats.analysis.density.planning`; the permanent specification is
`common_grid_planning_spec.md` under `docs/specs/analysis/density/`. The plotting-private
finest-budgeted shape name is a compatibility adapter only. The following completed runtime stage
is Stage 11E-GR2.

## Stage 11E-GR2 - plotting adaptation and visual-policy preservation

Deliverables:

- atomic and framework plotting adapters over the common GR0/GR1 layer;
- preservation of plotting's automatic visual bandwidth/grid coupling;
- graph-facing error translation and rendering metadata;
- unchanged browser, mesh, and scene-admission behavior.

Acceptance gate:

- atomic/framework density values, default selected grids, warnings, sparse routing,
  meshes, scenes, and public option serialization remain regression-compatible;
- plotting may accept a finest-feasible grid with a visual warning, but that outcome is
  not a scientific convergence certificate;
- the common analysis layer remains independently usable without rendering libraries.

Implementation status: implemented in `0.20.25a0`. Runtime owner is
`mdstats.plotting.density_visual_policy`; the permanent specification is
`plotting_grid_adaptation_spec.md` under `docs/specs/analysis/density/`. Atomic and
framework field producers consume the adapter while retaining their established
visual and rendering contracts. The following completed runtime stage is Stage
11E-GR3.

## Stage 11E1 - discovery-block periodic species-density estimation

Deliverables remain the existing source-bound physical/reference-material density,
periodized triclinic kernel, support, score, Hessian, dense/sparse realization,
bandwidth ladder, and uncertainty products.

Revision-47 requirements:

- density discovery uses only the SAMP0 discovery blocks and an admissibility overlay;
- descriptive position density may run when thermodynamic interpretation is blocked;
- discovery-block identities and policy signatures are mandatory;
- validation blocks are never used to choose bandwidth, grid, or candidate count.

Acceptance gate:

- held-out mass and feature recurrence can be evaluated without refitting;
- canonical, microcanonical, or descriptive labels come from STAT2 rather than E1;
- numerical support is not represented as feature-level sampling confidence;
- the kernel covariance is explicit and remains fixed within each GR3 grid ladder;
- E1 does not call plotting's adaptive Gaussian-to-grid policy.

## Stage 11E2 - per-realization numerical basin and density-boundary candidates

Deliverables remain deterministic point/ridge/flat candidates, support-restricted basin
ownership, local periodic charts, provisional cores, lineage, scale ambiguity, and one
`PerRealizationCandidateCatalog` for each bandwidth/grid realization.

Revision-47 terminology and ownership:

- E2 emits `density_boundary_candidate` and, with derivative support,
  `numerically_supported_saddle_candidate`;
- it does not emit a validated transition saddle, kinetic edge, or final frozen catalog;
- candidates are constructed only from discovery data;
- `FeatureCorrespondencePolicy` defines matching among E2 realizations.

Acceptance gate:

- unsupported space remains unknown;
- each realization is deterministic and serializable;
- no event or barrier claim follows from face adjacency alone;
- final selection and freezing are owned exclusively by GR4.

## Stage 11E-GR3 - Stage 11 fixed-kernel scientific grid refinement

Deliverables:

- `ScientificGridRefinementPolicy` and `GridConvergenceStoppingPolicy`;
- deterministic nested cell-metric grids with fixed kernel covariance;
- `DensityFieldResolutionCertificate`;
- `BasinGridConvergenceCertificate`;
- `CorridorGridConvergenceCertificate`; and
- explicit budget-limited unresolved outcomes.

The stopping policy records the refinement factor or interval ladder, target
$\max_i\Delta_i/\sigma_{\min}$, maximum ladder depth, and the number of consecutive
level pairs required to pass. Basin convergence records tolerances for count,
correspondence ambiguity, anchor displacement relative to kernel scale, basin overlap,
and integrated probability change. Corridor convergence records adjacency equality,
corridor/ridge overlap, bottleneck-location displacement, width/density changes, and
split/merge ambiguity. Defaults may be policy presets, but every resolved certificate
retains their numerical values. The initial `stage11_grid_stopping_v1` preset uses factor-two
interval refinement, $\Delta_{\max}/\sigma_{\min}\le 0.5$, and two consecutive passing
level pairs. Its basin and corridor thresholds and the matching weights of
`stage11_feature_correspondence_v1` are defined exactly in
`scientific_grid_refinement_spec.md`; any change requires a new preset identifier.

At least two consecutive refinement comparisons must pass after the minimum physical
resolution is reached. A single matching level pair is diagnostic only. Basin convergence
does not imply corridor convergence. Hitting the resource or maximum-depth limit before
passing returns `unresolved_due_to_resolution_budget` or
`unresolved_due_to_refinement_limit`.

Acceptance gate:

- plotting's adaptive bandwidth selection does not enter the scientific ladder;
- all levels use one fixed density hypothesis and exact common metric;
- field, basin, and corridor outcomes remain orthogonal;
- unresolved corridor topology cannot block a separately converged basin catalog, but
  it blocks saddle/barrier promotion.

Implementation status: implemented in `0.20.26a0`. Runtime owner is
`mdstats.analysis.density.refinement`; the permanent specification is
`fixed_kernel_grid_refinement_spec.md` under `docs/specs/analysis/density/`.
The implementation records exact `stage11_grid_stopping_v1` policy values,
requests the additional post-gate level required for two consecutive comparisons,
and retains budget-, depth-, metric-, and missing-evidence outcomes as signed
unresolved certificates. Stage 11E-GR4 is the next implementation stage.

## Stage 11E-GR4 - cross-fitted numerical-hypothesis selection and freeze

Deliverables:

- grid, bandwidth, candidate-complexity, and correspondence selection restricted to
  discovery/model-selection evidence;
- one source-bound `FrozenCandidateCatalog` containing the accepted numerical hypothesis,
  exact E2 realization lineage, correspondence policy, and convergence certificates;
- optional all-data `FinalRefitCatalog` with a new signature;
- selection-conditioned uncertainty when nested selection is unavoidable.

Acceptance gate:

- held-out blocks cannot change kernel covariance, grid level, candidate count, candidate
  identities, or feature correspondence;
- all-data refinement does not inherit held-out parameter-certification evidence;
- GR4 numerical convergence and SAMP1/SAMP2 trajectory support remain orthogonal;
- no other stage may claim ownership of the final frozen numerical catalog.

## Stage 11E-STAT3 - held-out distribution-stability refinement

Deliverables:

- distribution and occupancy stability measured on the dedicated
  `thermodynamic_validation` partition or an explicitly signed nested equivalent; this
  verification is optional for source-qualified descriptive/thermodynamic estimators but
  required for a `cross_validated` claim;
- selection-conditioned uncertainty and regime-sensitivity diagnostics;
- a refined `PmfAdmissibilityCertificate` without retuning E1/E2 candidates.

Acceptance gate:

- held-out instability may block occupancy thermodynamics or PMF interpretation while
  preserving descriptive density and basin geometry;
- STAT3 never consumes basin-validation or corridor-validation evidence unless a
  prespecified nested policy proves independence;
- validation results do not alter bandwidth, grid level, candidate identity, or local
  mechanical-force parameters.

## Stage 11E3A/11E3B - mechanical refinement and thermodynamic mean-force estimation

### Stage 11E3A - local mechanical-force refinement

- consumes only discovery/model-selection blocks and geometrically admissible
  conservative physical forces;
- fits `LocalMechanicalForceRefinement` for center offsets, restoring stiffness,
  manifold-normal confinement, and uncertainty;
- remains available for NVE and other noncanonical runs when force provenance is
  geometrically valid;
- makes no PMF, free-energy, or Boltzmann claim.

### Stage 11E3B - thermodynamic mean-force estimation and certification

- evaluates a frozen E3A model and constructs matched-kernel conditional force on the
  `thermodynamic_estimation` partition;
- emits a source-qualified `ThermodynamicMeanForceCertificate` only for canonical,
  validly reweighted, microcanonical-theory, or explicitly accepted subsystem-canonical
  contracts; the result carries mandatory `ThermodynamicResultProvenance`;
- retains curl, circulation, residual, and support diagnostics without projecting them
  away;
- rejects thermodynamic interpretation without deleting the E3A mechanical result.

Acceptance gate:

- no thermodynamic-estimation or verification block refits E3A parameters;
- an optional final all-data refit is separately signed;
- mechanical and thermodynamic statuses remain orthogonal in E5 and downstream records.

Legacy E3 migration is explicit:

| Legacy E3 field | Revision-47 owner | Migration rule |
|---|---|---|
| local center offset, symmetric stiffness, mechanical curvature | E3A | may be replayed only on discovery/model-selection evidence |
| conditional force average on a matched support subset | E3B candidate input | recompute on the signed thermodynamic-validation subset |
| density-score/force residual | E3B | recompute when ensemble, measure, kernel, or subset changes |
| PMF-admissible or equilibrium label | E3B/PMF-DENSITY/PMF-FORCE certificate | never inherited from the legacy record |

A legacy E3 result therefore proves neither E3A nor E3B compliance without the
corresponding replay and certificate.

## Stage 11E4 - provisional assignment and temporal-persistence diagnostics

Deliverables:

- raw core, basin, transition, background, unknown, unresolved, and overlap
  memberships;
- segment-aware core visits and preliminary core-entry/basin-retention intervals;
- explicit jump, return-excursion, unresolved-gap, and right-censored passages;
- local decorrelation-timescale estimates in the E1 analysis metric;
- dwell, censoring, stride, excursion, and recrossing diagnostics;
- independent temporal-support and global evidence-pattern statuses.

Acceptance gate:

- transition/background/unknown samples are not nearest-center filled;
- one jump, repeated hopping, short excursions, and unresolved gaps receive
  distinct evidence statuses;
- source segment boundaries and independent ensembles never acquire invented
  temporal continuity;
- temporal evidence is reported before final site certification.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.temporal_assignment` owns the Stage-11E4 result;
- E0b, E1, E2, and optional E3 signatures are validated before temporal work;
- raw memberships preserve the exact E2 cell classification and provisional-core
  sets, including explicit core overlap and unsupported space;
- only core and basin samples carry an attractor identity; no transition,
  background, unknown, unresolved, overlap, or excluded sample is filled by
  nearest anchor;
- trajectory continuity is restricted to one atom and one E0b segment, while
  independent ensembles retain spatial memberships but no intervals or passages;
- preliminary passages distinguish resolved jumps, same-state return excursions,
  unsupported/unresolved gaps, and right-censored exits;
- local periodic-coordinate autocorrelation uses a Geyer initial-positive-sequence
  truncation and downgrades irregular physical-time stride to a frame-only claim;
- stride sensitivity is evaluated separately from the authoritative full-resolution
  membership table;
- short-excursion and recrossing diagnostics use declared frame and local
  decorrelation thresholds without creating final events; and
- focused tests cover single jumps, repeated hopping, short excursions,
  unsupported gaps, ensembles, stride sensitivity, serialization, resources,
  source binding, and public API contracts.


## Stage 11E-SAMP1 - held-out basin sampling certificates

Deliverables:

- one `BasinSamplingCertificate` per frozen E2 basin candidate;
- held-out recurrence, residence, anchor/shape uncertainty, block/replica coverage,
  and grid/bandwidth survival;
- orthogonal evidence fields and final basin-promotion decision.

Acceptance gate:

- validation blocks are assigned with frozen candidate regions;
- one long correlated residence may support localization but not recurrence;
- accepted basins reproduce on held-out blocks within policy uncertainty.

## Stage 11E5 - joint evidence validation and structural association

Deliverables:

- orthogonal spatial, temporal, force, stationarity, geometry, curvature, and
  overall-certification statuses;
- matched force-to-score-covector consistency, never force-to-unqualified-gradient comparison;
- the exact `EvidenceCrossfitPartition` with separate discovery, model-selection, basin-validation, corridor-validation, thermodynamic-validation, and optional-final-refit independence statuses;
- `StructuralAssociationSet` records using registered structural views;
- statistical-state instances, preliminary structural complexes, and optional symmetry-orbit candidates;
- exchangeability checks before any orbit grouping of nominally equivalent rings;
- no default symmetry augmentation of trajectory samples;
- explicit `ValidatedFrozenCatalog` and optional `FinalRefitCatalog`.

Acceptance gate:

- force-free trajectories can produce spatial/temporal sites but not
  force-validated sites;
- disagreement among evidence channels remains explicit;
- association ambiguity is retained rather than resolved by nearest-ring fallback;
- held-out basin validation never rejects a one-transition trajectory merely because
  early and late blocks occupy different basins; limited data instead produce an
  explicit selection-conditioned or independent-validation-unavailable status.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.evidence_validation` owns the Stage-11E5 result;
- E0b, E1, E2, E4, optional E3, and C0A3 registration/source identities are
  reconciled transactionally before block or association work;
- `ValidatedFrozenCatalog` retains one record per E2 state with orthogonal
  evidence statuses and explicit disagreement diagnostics;
- force evidence is compared only with the E3 density-score covector in the same
  registered measure, never with an unqualified Euclidean gradient;
- structural associations use the E1 analysis metric and certified triclinic
  periodic-image geometry under a declared radius, retain all plausible
  candidates, and prohibit nearest-object fallback;
- discovery, model-selection, basin-validation, corridor-validation,
  thermodynamic-validation, and optional-final-refit partitions retain independent,
  selection-conditioned, unavailable, and insufficient-transfer statuses rather than
  forcing rejection;
- nominal structural-symmetry candidates remain opt-in, require exchangeability
  evidence before orbit acceptance, and never augment observations by default;
- `FinalRefitCatalog` is separately signed and cannot inherit parameter-validation
  evidence for refitted positions, boundaries, or force parameters; and
- focused tests cover force-free and force-validated states, force-score
  disagreement, ambiguous/unresolved association, limited transitions, block
  independence, symmetry exchangeability, refit provenance, serialization,
  resources, source binding, and public API contracts.


## Stage 11E5a - species-dependent coordination fingerprints and classification

Deliverables:

- exact state-conditioned M--O/M--T distance vectors;
- cyclic-index and rank-safe actual-angle coordination spectra;
- direct local off-center coordinates and diagnostic residual spectra;
- gauge-defined oxygen-, gap-, and sector-locking scores;
- exact unweighted cyclic spectra, boundary-measure angular moments, and raw/normalized amplitudes;
- geometry-predicted coordination and unexplained residual;
- occupancy-conditioned fingerprint diagnostics;
- point, bilateral, discrete off-center, smooth/corrugated annular, cage, general,
  and ambiguous structural classes with continuous evidence.

Acceptance gate:

- a centered serrated S6R is not classified as off-center;
- direct off-centering and geometry-predicted distance modulation agree within
  uncertainty for a coherent point state;
- residual spectra are not interpreted as exact component separation;
- phase-dependent labels require resolved amplitude and stable circular phase;
- occupancy-conditioned mixtures remain explicit;
- one state may retain several plausible structural associations.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.coordination_fingerprints` owns the Stage-11E5a result;
- exact physical M--O/M--T sample matrices and persistent atom/image identities
  are authoritative, while mean sequences and all spectra are derived views;
- the centered-reference construction preserves each sample's normal coordinate
  and removes only in-plane displacement;
- equal-index DFTs, boundary-measure angular moments, and rank-safe actual-angle
  fits are stored as three distinct measures;
- direct local coordinates gate off-center labels, so a centered serrated S6R
  remains centered despite a strong short-wavelength harmonic;
- phase-dependent locking and discrete-angular labels require a resolved radial
  amplitude and a stable circular resultant;
- geometry-forward residuals compare average framewise physical distances rather
  than distances to an averaged structure;
- occupancy-conditioned mixtures and multiple plausible structural associations
  remain explicit; and
- focused tests use real ASE 3.29.0 for VASP I/O and triclinic minimum-image
  behavior, and cover classification, harmonics, serialization, resources, and
  public API contracts.


## Stage 11E5b - optional geometry-conditioned site refinement

Deliverables:

- static and framework-descriptor-conditioned center models;
- atom-resolved structural predictors and rank-safe harmonic features;
- separate `model_selection` comparison, `basin_validation` confirmation, and `corridor_validation` crossing checks;
- instantaneous predicted centers and nested cores/basins with persistent global
  state identity;
- static/dynamic memberships, comoving ion displacement, boundary displacement, and
  boundary-induced crossing diagnostics;
- residual covariance before and after conditioning;
- exclusive `AssignmentConflictStatus`, overlap fractions, and occupancy bounds.

Acceptance gate:

- the dynamic model is retained only when model-selection residuals improve and the relevant held-out basin/corridor evidence does not contradict the gain;
- a moving center never uses a frozen basin implicitly;
- dynamic and frozen memberships remain jointly reportable;
- a boundary-swept crossing is not silently labeled ion-driven;
- mobile-ion positions never redefine the structural predictor frame.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.geometry_conditioning` owns the Stage-11E5b result;
- `FrameworkPredictorTable` accepts only framework-derived predictors and rejects
  mobile-ion-dependent tables;
- `FrozenRegionDefinition` binds one persistent state/association to a static
  center and strictly nested core/basin radii;
- discovery assignments remain frozen while a represented-time weighted affine
  center model is fit with rank, condition, residual RMS, and covariance records;
- model-selection and untouched basin/corridor-validation evidence decide whether the
  dynamic model is retained, contradicted, or unsupported;
- moving cores and basins rigidly translate the frozen shape and never reuse a
  frozen basin around a moving center;
- static, candidate-dynamic, and selected memberships are all persistent;
- atom/segment-local crossings retain ion, center, boundary, and comoving
  displacement, including explicit boundary-induced status;
- global assignment conflicts are exclusive and state occupancy is reported as
  lower/upper bounds under overlap; and
- deterministic signatures, strict replay serialization, resource preflight,
  real-ASE regression, permanent specifications, and public exports are tested.


## Stage 11E-SAMP2 - preliminary corridor and saddle-candidate sampling support

Deliverables:

- `PreliminaryCorridorSupport` built from E4 provisional passages not used for
  candidate discovery;
- `TransitionCorridorSamplingCertificate` with independent passage count,
  forward/reverse directions, block/replica support, path-progress coverage, local
  field support, candidate recurrence, and corridor uncertainty;
- explicit `observed_one_off_passage`, `sampling_supported_transition_corridor`, and
  `sampling_supported_saddle_candidate` outcomes.

SAMP2 does not create a validated thermodynamic saddle or final transition event.
E6 may alter event boundaries, censoring, recrossing, and event count. Final evidence
therefore supersedes rather than silently inherits preliminary counts.

Acceptance gate:

- raw transition-frame count never substitutes for independent event count;
- candidate correspondence uses the frozen GR4 policy;
- one event remains one-off evidence;
- promotion to a physical transition saddle is reserved for THERMO3B or an equivalent
  independently specified transition-state test.

## Stage 11E-SAMP3 - partial-catalog scope, novelty, and saturation

Deliverables:

- cumulative basin, corridor, and event discovery curves;
- holdout novelty and unsupported-assignment rates;
- `DiscoveryScopeCertificate` with `observed_partial_catalog` semantics;
- raw event/exposure/censoring outputs and `RateBoundModel` eligibility only.

Acceptance gate:

- no finite trajectory claims complete discovery;
- formal rate intervals remain deferred to Stage 11F0 unless a complete signed
  model certificate exists;
- longer trajectories increase supported evidence rather than only fitted features.

## Stage 11E-THERMO0 - thermodynamic state and channel selection

Deliverables:

- `ThermodynamicStateDefinition` and `ThermodynamicPotentialDefinition`;
- `ThermodynamicEnergySelection` referencing the preexisting `FrameEnergyCatalog`;
- tagged-ion, pooled-orbit, occupation-vector, and joint-state semantics;
- multiplicity and standard-measure convention.

Acceptance gate:

- THERMO0 does not reconstruct source energy channels after STAT0;
- no generic energy or ambiguous state probability is accepted;
- multiplicity correction cannot be applied twice.

## Stage 11E-THERMO1 - ensemble-specific basin thermodynamics

Deliverables:

- NVT/reweighted Helmholtz, NpT Gibbs, or NVE microcanonical occupancy/entropy
  products as permitted by the selected potential definition;
- correlated-data uncertainty and selection-conditioning status;
- descriptive occupancy retained when thermodynamic promotion is blocked.

Acceptance gate:

- canonical formulas are used only for canonical target measures;
- NpT includes pressure-volume/enthalpy semantics;
- NVE canonical approximation requires a separate accepted policy;
- population-derived thermodynamics are never validated against the same population.

## Stage 11E-THERMO2 - conditional energies and identifiable effective Hamiltonians

Deliverables:

- ensemble-appropriate conditional potential energy or enthalpy;
- complete-system block uncertainty and background-control sensitivity;
- optional nested effective occupancy models under `EffectiveHamiltonianPolicy`;
- energy/entropy decomposition where independently identifiable.

Acceptance gate:

- frame energies are not duplicated across ions as independent samples;
- rank, condition, occupancy-variation, symmetry, regularization, and held-out-score
  gates are explicit;
- predictive coefficients are not represented as unique atomic energies.

## Stage 11E-THERMO3A - static finite transition-region thermodynamics

Deliverables:

- a declared finite transition tube, dividing-surface neighborhood, or
  reaction-coordinate bin for each SAMP2-supported candidate;
- static probability density or reweighted support, conditional whole-system energy or
  enthalpy, region measure, and uncertainty;
- `StaticTransitionRegionThermodynamics` with no event-conditioned or committor claim.

Acceptance gate:

- point saddles are never assigned integrated probability;
- unsupported or grid-unstable regions remain unresolved;
- static transition-region evidence cannot promote a transition state or rate.

## Stage 11E6 - final hysteretic segmentation and residence statistics

Deliverables:

- immutable raw labels;
- frozen-catalog core-basin hysteresis;
- residence and transition intervals;
- unresolved-gap, recrossing, excursion, censoring, and moving-boundary policies;
- static-versus-dynamic membership, assignment-conflict, overlap, and boundary-induced crossing records;
- reuse of generic temporal statistics;
- ion-time, mean-occupancy, vacancy, and multiple-occupancy statistics.

Acceptance gate:

- final event statistics are stable over a documented range of thresholds and
  frame strides;
- `FinalTransitionEventCertificate` records final independent event count, censoring,
  recrossing, at-risk exposure, and the exact relationship to superseded E4/SAMP2
  preliminary evidence.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.final_segmentation` owns the Stage-11E6 result;
- immutable E4 raw labels remain authoritative and nearest-center filling is prohibited;
- frozen E4, selected E5b, and static/dynamic-agreement membership policies are explicit;
- qualified core entry and basin-retention hysteresis preserve short excursions and require confirmed exits;
- unsupported gaps, assignment conflicts, boundary-induced passages, recrossings, return excursions, and censoring remain explicit;
- residence records retain exact atom, segment, state, and compact sample identities with represented-time components;
- state summaries report ion-time, uncensored residence durations, occupancy bounds, vacancy bounds, and multiple-occupancy bounds without a rate-law assumption;
- declared threshold/stride perturbations produce an independent stability certificate; and
- deterministic signatures, strict replay serialization, resource preflight, permanent specifications, public exports, and real-ASE validation are tested.


## Stage 11E6b - observed transition-path ensembles

Deliverables:

- first-subsequently-resolved-core passages;
- resolved, bracketed, multiple-target, ambiguous, and gap-interrupted first-hit statuses;
- failed excursions and recrossings;
- full registered paths and periodic translations;
- `RegistrationCompatibilityClass` for pooling paths from independent registered trajectories;
- geometry, exact ring-sector coordination, harmonics, and force evidence along paths;
- single-path, undersampled-ensemble, and resolved-ensemble statuses;
- optional path clustering only when event support is adequate;
- concurrent-event and local occupancy context without forcing a many-body model.

Acceptance gate:

- one jump produces one observed connection but no inferred rate or
  representative pathway;
- repeated paths retain physical time, unwrapped image bookkeeping, and periodic identity;
- output cadence limitations remain explicit rather than interpolated away;
- an intermediate density shoulder is not promoted to a site without independent
  spatial and temporal evidence.

Baseline compatibility requirements (implemented; release chronology is in the status appendix):

- `mdstats.analysis.density.transition_paths` owns the Stage-11E6b result;
- every event is reconstructed from exact E6 compact sample brackets and retains
  registered Cartesian positions, wrapped fractional positions, integer image
  shifts, physical times where available, represented-time weights, and force
  availability without interpolation;
- resolved, cadence-bracketed, target-ambiguous, gap-interrupted, failed,
  recrossing, and censored first-hit outcomes remain explicit;
- periodic translation is validated as the endpoint image-shift difference and
  is part of the path-ensemble identity;
- optional sample-bound ring, sector, ordered coordination, harmonic, aperture,
  puckering, occupancy, density, PMF, and transformed-force evidence is retained
  without changing the E6 state catalog;
- `RegistrationCompatibilityClass` permits pooling distinct independent
  registrations only under a common registration group or identical
  registration, unit convention, and explicit state correspondence;
- path ensembles distinguish single observations, undersampled collections, and
  resolved support; optional diagnostic clustering is admitted only above a
  declared event count and preserves original time;
- overlapping events retain local occupancy context and isolated, overlapping,
  candidate-exchange, candidate-concerted, or unresolved collective status
  without creating a many-body model; and
- deterministic signatures, strict replay serialization, resource preflight,
  permanent specifications, public exports, and real-ASE validation are tested.

The optional PMF-DENSITY, PMF-FORCE, and PMF-CROSSCHECK branches may proceed only under their own ensemble, support, and integrability gates. Current implementation priority is defined only by the revision-47 typed dependency graph.

## Stage 11E-THERMO3B - event/path-conditioned transition-state validation

Deliverables:

- transition-region statistics recomputed from final E6 events and E6b path ensembles;
- recrossing, directional support, path-conditioned energy/enthalpy, dividing-surface
  behavior, and committor or enhanced-sampling provenance where available;
- `TransitionStateValidationCertificate`;
- promoted `SaddleThermodynamicCertificate` is a composition of the exact
  `StaticTransitionRegionThermodynamics` from THERMO3A and the THERMO3B validation
  certificate, and exists only when all required gates pass.

Acceptance gate:

- preliminary SAMP2 counts are not treated as final events;
- repeated passages alone do not prove a thermodynamic saddle;
- one-off or undersampled paths remain observations without barrier/rate promotion;
- `validated_transition_saddle` is a THERMO3B outcome, never an E2 or SAMP2 outcome.

## Stage 11E7 - observed event network with optional geometric annotations

Deliverables:

- `ObservedEventNetwork` whose nodes are validated state instances;
- `ObservedEventEdge` from final E6 directional events, at-risk exposure, censoring,
  and periodic endpoint translation where identifiable;
- optional `PathResolvedEdge` enrichment from E6b;
- optional `TransitionStateAnnotatedEdge` enrichment from THERMO3B;
- structural-versus-observed edge comparison without graph completion;
- separate state-instance, structural-complex, symmetry-orbit, and semantic-class
  summaries;
- compact source-anchor transfer models and fail-closed held-out/external assignment.

Acceptance gate:

- an event-supported edge does not require a resolved intermediate path or saddle;
- cadence-limited or geometry-unresolved paths remain event edges with explicit missing
  annotations;
- structural candidates never create observed edges;
- off-network events and failed transfer remain explicit; and
- rates, state merging, symmetry augmentation, and model refitting remain absent.

Baseline compatibility mapping:

- the existing observed-network implementation currently creates edges from successful
  E6b path ensembles;
- revision-47 migration must add E6-event-supported edges without changing legacy
  path-resolved edge serialization;
- existing path edges map to `PathResolvedEdge`; they do not define the complete event
  network after migration.

## Stage 11E-GR5 - density numerical-ownership closeout

Deliverables:

- remaining field contracts, source provenance, periodized kernels, normalization,
  support masks, HDR integration, dense/local-sparse producers, and scientific planning
  moved to `mdstats.analysis.density` where not already migrated;
- plotting consumes only analysis-owned field protocols and producers;
- compatibility imports and adapters retained for one deprecation interval, then removed
  only after public-API approval;
- D0b-D0d marked complete.

Acceptance gate:

- dense, local-sparse, scientific-field, atomic/framework plotting, mesh, scene, and
  package-wide regression boundaries pass;
- numerical fields and signatures remain equal across compatibility and new import paths;
- no analysis module imports graph, browser, mesh, or HTML policy;
- removal of old numerical ownership is an engineering cleanup and cannot alter existing
  scientific certificates.

## Stage 11E-PMF-DENSITY - optional density-derived PMF

Entry dependencies:

- STAT2 canonical/reweighted density-PMF admissibility;
- STAT3 distribution stability;
- converged field numerics and SAMP1-supported basins;
- explicit coordinate measure, Jacobian, support topology, temperature, and reweighting
  provenance.

Deliverables:

- `DensityPmfCertificate` with $A(q)=-k_{\mathrm B}T\ln p(q)+C$ on declared supported
  components;
- component offsets, uncertainty, minima, and candidate bottlenecks only where supported;
- mandatory `ThermodynamicResultProvenance`.

Force data are not required. The result may be `source_qualified_unverified`.

## Stage 11E-PMF-FORCE - optional force-integrated PMF

Entry dependencies:

- STAT2/STAT3 force-PMF admissibility;
- E3B matched-kernel thermodynamic mean-force evidence;
- converged field numerics and SAMP1-supported basins;
- coordinate-measure, Jacobian, curl, circulation, harmonic-component, topology, and
  boundary-condition policy.

Deliverables:

- `ForcePmfCertificate` with raw mean-force, curl, circulation, harmonic diagnostics,
  integrability status, scalar reconstruction, and provenance.

## Stage 11E-PMF-CROSSCHECK - optional independent PMF verification

When both PMF estimators exist on compatible coordinates and support,
`PmfCrossCheckCertificate` compares them without rebuilding either estimator. Agreement
raises confidence; unavailability leaves either source-qualified PMF reportable;
disagreement preserves both estimates and blocks only a combined cross-validated PMF.

None of the PMF stages blocks local site discovery, temporal segmentation, or observed
transition paths.

## Stage 11E8a - Na-LTA NVE continuation integration dossier

E8a is a cross-cutting source-bound acceptance dossier. It is updated at each migration
milestone and is not ordered after GR5 or the optional PMF branches.

Milestone products:

```text
E8a-ENS    source controls, user-label conflict, ensemble and force provenance
E8a-STAT   ionic temperature, integrity, energy conservation, quality, production regimes
E8a-GR     fixed-kernel field/basin/corridor numerical convergence
E8a-SAMP   held-out basin sampling confidence and preliminary corridor support
E8a-SCOPE  novelty, saturation, and observed-partial-catalog scope
E8a-PMF-DENSITY   optional density-derived PMF sub-dossier
E8a-PMF-FORCE     optional force-integrated PMF sub-dossier
E8a-PMF-CROSSCHECK optional verification when both estimators exist
E8a-THERMO optional and present only when thermodynamic gates pass
E8a-PATH   optional and present only when final events/path gates pass
E8a-RATE   optional and present only when kinetic gates pass
```

The current real-source fixture is a fixed-cell Na-LTA continuation trajectory. Its
historical user comment contains "300 K NVT", but that label is non-authoritative.
ENS0/ENS1 must reconstruct the controls and numerical MD settings. STAT0--3 must
determine equipartition temperature, the three-level trajectory-quality verdict,
production regimes, and permitted thermodynamic interpretations. The observed smooth NVE
energy drift is expected to produce `degraded_quality`, not catastrophic rejection,
provided all hard integrity checks pass.

The existing S0--S4 software path remains an engineering-complete exploratory baseline:
24 numerical basin identities are persistent across the tested pilot bandwidth/grid
realizations, but they are not yet SAMP1-certified on held-out blocks. Saddle adjacency,
PMF-force admissibility, and inter-basin transition evidence remain unresolved or
unsupported. The dossier remains `scientifically_partial`.

Milestone acceptance requirements:

- `E8a-ENS`: resolve `MDALGO=2`, `SMASS=-3`, and `ISIF=2`; record the misleading
  comment only as `user_label_conflicts_with_controls`; reconstruct exact energy and
  numerical-control channels;
- `E8a-STAT`: classify integrity, NVE conservation, production regimes, and quality
  without untested stationarity assertions;
- `E8a-GR`: replace pilot-only hard-coded grid pairs with the GR3 fixed-kernel ladder,
  report field/basin/corridor convergence separately, and leave budget-limited
  unconverged corridors unresolved;
- `E8a-SAMP`: apply the signed crossfit partition and held-out basin/corridor confidence;
- `E8a-SCOPE`: label every result as a condition- and timescale-scoped partial catalog;
- no milestone requires optional PMF, GR5 ownership closeout, a validated saddle, or a
  rate unless that specific sub-dossier is requested.

Detailed S0--S4 release history and package-test evidence remain in the non-normative
status appendix.

## Stage 11E-THERMO4A - optional product-scoped thermodynamic verification

Deliverables:

- one optional `ThermodynamicCrossValidationCertificate` per requested product class;
- exact estimator provenance and independent verification-source provenance;
- optional occupancy/PMF, temperature-derivative, replica/held-out-temperature, or
  WHAM/MBAR checks when admissible.

Acceptance gate:

- THERMO1/2 source-qualified results do not require THERMO4A to be reported;
- every result states whether verification was not requested, unavailable, insufficient,
  agreed, partially agreed, or disagreed;
- a `cross_validated` claim requires genuinely independent or explicitly nested evidence;
- native energies from different Hamiltonians are never pooled as MBAR input;
- detailed balance and barrier-rate agreement are absent from this stage.

## Stage 11E8b - cross-dataset comparison by product class

Every product retains its observation timescale, `observed_partial_catalog` scope, source
bundle identity, and estimator provenance. Equal ring semantics do not imply equal
statistical-state identity.

Product-specific nodes and gates:

- `E8B_BASIN_GEOMETRY`: E5/E5a, SAMP1, SAMP3, and converged basin numerics;
- `E8B_BASIN_THERMO`: THERMO1 and compatible state/ensemble definitions; THERMO2 and
  THERMO4A are optional energy-decomposition and verification annotations;
- `E8B_CORRIDOR`: SAMP2 plus converged corridor numerics;
- `E8B_TRANSITION_REGION`: THERMO3A;
- `E8B_PATH`: E6b only;
- `E8B_TRANSITION_STATE`: THERMO3B;
- `E8B_EVENT_NETWORK`: E7 with compatible state semantics;
- `E8B_KINETIC`: F0/E9B, with optional G1/F1/THERMO4B annotations.

Direct WHAM/MBAR pooling additionally requires a common target measure and
cross-evaluated reduced potentials. Failure of a later product gate never blocks an
earlier comparison class.

## Stage 11E7A - rate-candidate edge universe and exposure support

Deliverables:

- one signed `RateCandidateEdgePolicy` defining the edge universe before event counting;
- `RateCandidateEdgeUniverse` containing source-bound `RateCandidateEdge` records;
- candidate sources may include structurally admissible all-pairs rules, M2 supplied
  edges, or SAMP2-supported corridors, each labeled separately;
- state-at-risk exposure and censoring eligibility even when zero events occur;
- multiplicity, symmetry pooling, and multiple-testing policy.

Acceptance gate:

- an observed event creates or annotates an `ObservedEventEdge`, but zero-event candidates
  remain representable;
- no candidate edge is interpreted as an observed transition or saddle;
- rate bounds are calculated only for policy-declared candidates with valid exposure.

## Stage 11E-KSAMP0 - kinetic fit and validation partition

Deliverables:

- one `KineticCrossfitPartition` created after final E6 event episodes are frozen;
- explicit `kinetic_model_selection`, `kinetic_model_fit`, and `kinetic_model_validation` episodes;
- split boundaries respect complete residence/event episodes where possible;
- intervals crossing a split are censored according to a signed boundary policy;
- trajectory- or replica-level splitting is preferred when sufficient data exist.

Acceptance gate:

- E9A and G0 consume selection evidence only;
- F0 consumes kinetic-model-fit events and exposure only;
- E9B consumes untouched kinetic-model-validation events/exposure only;
- when independent kinetic validation is impossible, the outcome is
  `independent_kinetic_validation_unavailable`, not in-sample promotion.

## Stage 11E9A - pre-rate event-process and state-model adequacy

Deliverables:

- dwell-time survival, censoring, recrossing, threshold, and stride diagnostics;
- event-count and at-risk-exposure sufficiency;
- diagnostic waiting-time, discrete-lag, and continuous-time models that are explicitly
  non-promoted and used only for adequacy testing;
- lag-time and Chapman--Kolmogorov diagnostics where data permit;
- one pre-rate state-model outcome:

```text
current_state_model_supported
discrete_lag_model_required
semi_markov_required
gate_state_augmentation_required
sampling_insufficient
```

Acceptance gate:

- E9A uses only `kinetic_model_selection` episodes and may fit diagnostic models but
  does not publish production rates or rate bounds;
- a gating-required outcome routes to G0 before F0;
- sampling insufficiency remains explicit and cannot be repaired by regularization.

## Stage 11G0 - gating diagnosis and state-model selection

Deliverables:

- identify no-gate, fast-gate, slow-gate, comparable-timescale, or unsupported regimes;
- define candidate gate observables from validated framework breathing, aperture,
  occupancy, or other descriptors;
- determine whether averaging, explicit augmented states, semi-Markov memory, or a
  nonstationary model is required;
- `GatingModelSelectionCertificate` for the accepted state-model generation.

Acceptance gate:

- if no augmentation is required, issue an explicit no-op accepted certificate;
- if augmentation is required, it must improve selection-stage adequacy without
  inspecting `kinetic_model_validation` episodes;
- augmentation creates a signed `StateModelGeneration`, `GenerationReplayPlan`, and
  `GenerationTerminationCertificate`, and repeats bounded assignment,
  segmentation, E7 construction, and E9A validation with new signatures;
- the iteration count is policy-bounded; failure to converge blocks promoted rates rather
  than creating a cycle or silently retaining ungated rates.

## Stage 11F0 - empirical rates and rate bounds

Deliverables:

- directional final-event counts, at-risk state exposure, censoring, and uncertainty on
  `kinetic_model_fit` episodes;
- the owning `RateBoundModel` with event-process, stationarity, exposure, multiplicity,
  candidate-edge, and confidence assumptions;
- empirical directional rates where identifiable;
- zero- or low-event upper bounds on declared `RateCandidateEdge` records;
- conditional detailed-balance residuals only when an independent equilibrium population
  certificate and compatible thermodynamic measure exist.

Acceptance gate:

- requires E6 final events, E7 observed-event records, E7A candidate-edge universe, E9A
  support, KSAMP0, and an accepted G0 state model;
- E6b paths and THERMO3B saddles are not required;
- zero-event bounds require valid at-risk exposure and the signed candidate-edge policy;
- absent equilibrium admissibility suppresses detailed-balance output but does not delete
  otherwise valid empirical rates;
- insufficient fit events produce `sampling_insufficient`, not regularized certainty.

## Stage 11E9B - post-fit kinetic-model validation

Deliverables:

- held-out likelihood or survival prediction on untouched `kinetic_model_validation` episodes;
- lag-time, implied-timescale, Chapman--Kolmogorov, residual, and censoring checks where
  identifiable;
- model-selection uncertainty and one outcome:

```text
promoted_model_supported
semi_markov_revision_required
gating_revision_required
independent_kinetic_validation_unavailable
sampling_insufficient
rejected
```

Acceptance gate:

- E9B cannot reuse F0 fit episodes as independent validation;
- only `promoted_model_supported` permits Stage 11H propagation as a validated model;
- unavailable independent validation may permit a clearly labeled exploratory rate result,
  but not a held-out-validated kinetic claim;
- a revision-required outcome starts a new signed model generation under the bounded
  replay policy.

## Stage 11F1 - barrier-derived and transition-state rate laws

Deliverables:

- ensemble-appropriate activation potentials from THERMO3B or dedicated enhanced
  sampling;
- prefactor and transmission provenance;
- descriptor-, temperature-, and gate-conditioned barrier-derived rate laws with
  uncertainty;
- no barrier inferred from a numerical density boundary alone.

Acceptance gate:

- requires THERMO3B and the accepted G0 state model, but not F0;
- every rate term is bound to state, path, thermodynamic, and provenance certificates;
- empirical F0 and barrier-derived F1 rates remain separate until THERMO4B.

## Stage 11E-THERMO4B - kinetic-thermodynamic consistency

Deliverables:

- product-scoped `KineticThermodynamicConsistencyCertificate`;
- detailed-balance consistency when F0 and independent equilibrium populations exist;
- barrier-versus-empirical-rate comparison only when both F0 and F1 exist;
- temperature dependence and transmission-factor diagnostics where identifiable.

Acceptance gate:

- requires E9B support for any promoted F0 kinetic claim;
- missing F1 suppresses only the barrier-comparison subproduct;
- disagreement is retained and blocks promotion to a unified model;
- no circular comparison reuses the same fitted quantity as its own validation target.

## Stage 11G1 - gate-conditioned rate comparison and final model selection

Deliverables:

- compare ungated, averaged-gate, augmented-state, semi-Markov, and nonstationary models
  that survived G0/E9B;
- gate-conditioned empirical and optional barrier-derived rates with uncertainty;
- final model-selection certificate for propagation.

Acceptance gate:

- unsupported gating remains absent rather than being imposed by framework semantics;
- the selected model improves held-out prediction and preserves state/provenance identity;
- G1 never retroactively changes the F0/E9B source generation.

## Stage 11H - kinetic propagation and first-passage statistics

Deliverables:

- propagators or kinetic Monte Carlo only for an E9B-supported and G1-finalized model;
- mean first-passage times, survival probabilities, fluxes, and uncertainty;
- optional transition-path-theory observables where the model and sampling support them.

Acceptance gate:

- numerical propagation reproduces source-model invariants and held-out observables;
- uncertainty includes state, event, rate, gating, and model-selection components.

## Stage 11I - integrated scientific ground gate

Deliverables:

- one source-bound dossier linking structural identities, registered coordinates,
  sampling certificates, thermodynamics, final events, kinetic adequacy, rates, gating,
  and propagated observables;
- explicit supported, conditional, unresolved, and rejected claims;
- no complete-site or complete-pathway claim from finite MD sampling.

Acceptance gate:

- every promoted result is traceable to its exact source, policy, partition, and upstream
  certificate;
- failure of any high-level gate preserves all valid lower-level products.

# Validation strategy

## Stage C0 algebra and transformation tests

Required synthetic trajectories include uniform translation, integer periodic
wrapping, moving box origin, rigid cell rotation, isotropic breathing,
anisotropic stretch, shear, combined affine deformation, and residual nonaffine
motion.

For every valid frame,

$$
G_t=H_tM_t,
$$

coordinate round trips must close, and force work must satisfy

$$
\mathbf F_x\cdot d\mathbf x
=
\mathbf F_q\cdot d\mathbf q.
$$

Consumer regressions cover laboratory/reference MSD, COG/COM drift,
translation-only VACF preparation, framework-registered density, and plotting.
Additional C0 tests require:

- core affine registration followed by separate registered-structural-view integration;
- composed reference-material plus framework-translation registration;
- explicit-matrix and selected-frame reference-cell provenance;
- rejection of partial-periodic reference-material requests;
- independent geometric-force and PMF-force statuses;
- variable-cell transformed forces remaining PMF-inadmissible despite geometric
  work invariance;
- translation-fit invariance under changes to the downstream analysis metric;
- segment-continuous translation branch lifting across periodic crossings; and
- fail-closed branch ambiguity at restart or undersampled discontinuities.

## Synthetic site landscapes

Controlled cases include isolated harmonic wells, anisotropic wells, double
wells, saddles, annular manifolds, unequal populations, periodic-boundary modes,
background transition support, and disconnected sampled components. Temporal
fixtures include repeated $A\leftrightarrow B$ hopping, one irreversible-looking
$A\rightarrow B$ event, short failed excursions, rapid recrossings, a true
metastable intermediate, and a nonmetastable transition shoulder.

Tests require kernel-metric covariance, triclinic image-sum normalization, affine
covariance of both the density score covector and metric gradient, density-ridge
criteria, periodic cell-complex topology, field/topology certificates, attractor lineage,
saddle densities, type-specific provisional cores, local periodic charts, local force
curvature, temporal persistence, transition-path extraction, and evidence statuses to recover the declared
structure without forcing every point into a site. Boundary-crossing wells must
have compact lifted covariance, and a weakly corrugated annulus must retain one
continuous core rather than only its highest angular sectors.
Model selection must use `model_selection` evidence and leave basin-, corridor-, and thermodynamic-validation evidence untouched.
Overlapping dynamic regions must produce exclusive conflict statuses and occupancy bounds.
One observed jump must never produce a rate or a resolved path ensemble. Compatible paths
from independent runs may pool despite distinct member registration signatures. Coarse output
cadence must produce bracketed or ambiguous first-hit status rather than a fabricated exact
path.

## Statistical robustness

Primary uncertainty units are independent trajectories or contiguous time blocks
containing the complete many-ion system. Tests include bandwidth ladders, separate
the full discovery/model-selection/basin-validation/corridor-validation/thermodynamic-validation partition where sampling permits,
leave-one-residence-episode-out checks, nested block resampling when independent
validation is unavailable, frame-stride changes, segment-aware quadrature,
topology-regime splitting, reference-cell/covariance sensitivity, density-backend
field and topology certification, force-subset matching, and HDBSCAN comparison.
Per-ion resampling is a secondary hierarchical diagnostic. A single-transition
trajectory may return `selection_conditioned_validation` or
`independent_validation_unavailable` rather than a false rejection.

## Coordinate and structural interpretation

Rigid translation, periodic wrapping, and declared cell deformation corrections
must not broaden a registered site artificially. Physical pair-distance analyses
must retain real cell breathing. Ring/cage annotations must remain downstream of
global statistical discovery.

## Atom-resolved ring and coordination tests

Required structural cases include:

- a regular ring and an alternating-radius S6R;
- a puckered and chemically split S6R;
- exact even-ring Nyquist handling in cyclic-index spectra;
- an irregular-angle ring whose alternating sequence is not forced into a pure
  physical-angle Nyquist component;
- rank, condition, and unresolved checks for actual-angle fits;
- exact unweighted cyclic spectra versus boundary-measure angular moments;
- raw versus normalized amplitudes;
- dihedral shift/reversal transforms and undefined-phase behavior;
- rigid rotation, periodic wrapping, and compatible-frame deformation; and
- registered structural views under rigid and non-rigid affine maps.

Required species-conditioned cases include:

- centered three-short/three-long coordination;
- superposed direct $m=1$ off-centering and short-wavelength serration;
- elliptic structural deformation without false off-center classification;
- exact geometry forward prediction of M--O distances;
- a residual coordination pattern not explained by geometry alone;
- phase locking to oxygen atoms, O--O gaps, or T--O--T sectors;
- weakly corrugated annuli and discrete angular states;
- multi-ring/cage and ambiguous structural associations;
- symmetry-equivalent state instances with true, broken, and occupancy-conditioned exchangeability;
- occupancy-conditioned center or phase splitting; and
- transition paths through inequivalent ring sectors.

Persistent identities must survive cyclic permutation, orientation reversal,
registration, and source replay. A phase-dependent label is rejected when its
amplitude or phase is unresolved.

## Ensemble, energy, and production-regime validation

Tests cover comment/control conflicts, versioned VASP control semantics, companion-file
states, thermostat-disabled NVE, NVT/NpT/driven variants, exact energy-channel
mapping, controlled/conserved quantities, correlated block lengths, insufficient
block outcomes, dimensionless drift, PELT boundary replay, multiple regimes,
selection-conditioned uncertainty, and NVE/NVT/NpT/biased thermodynamic permissions.
The Na-LTA continuation fixture must resolve fixed-cell NVE without using `SYSTEM`.

## Sampling-confidence and cross-fitting validation

Tests freeze candidates on discovery blocks and validate them on disjoint complete-
system blocks. They cover correlated long residences, multiple ions sharing one
frame, one-off passages, forward/reverse events, corridor validation independent of
saddle-required assignment, bootstrap feature correspondence, grid/bandwidth
survival, holdout novelty, unsaturated accumulation curves, and partial-catalog
reporting.

## Shared grid-refinement and ownership validation

Tests replay the present atomic-density oracle and the extracted common layer over
orthogonal and strongly triclinic cells, fixed and interval-derived grids, dense and
local-sparse backends, periodic spread edge cases, reciprocal-resolution thresholds,
CIC/stencil broadening, budgeted finest-shape search, serialization, and graph-facing
compatibility errors. Stage 11 tests hold kernel covariance fixed while refining the grid,
cover basin convergence with unresolved corridor topology, split/merge correspondence,
budget-limited ladders, identical-field reuse, and discovery/model-selection versus held-out
partition isolation. Existing atomic/framework plotting outputs must remain unchanged.

## Thermodynamic validation

Tests require every thermodynamic product to retain `ThermodynamicResultProvenance`, cover
source-qualified estimates with unavailable verification, compatible and incompatible
PMF density/force cross-checks, disagreement retention, and prohibition of silent source
or energy-channel mixing. Tests also cover tagged-ion versus pooled versus joint-state
definitions, multiplicity,
NVT Helmholtz, NpT Gibbs/enthalpy, NVE entropy and conditional canonical
approximation, bias/reweighting separation, complete-system energy resampling,
effective-Hamiltonian rank and held-out prediction, finite transition-region measures,
noncircular checks, reduced-potential-matrix requirements, MBAR overlap failure, and
rate-model deferral.

## Kinetic cross-fitting and zero-event rate validation

Tests freeze complete residence/event episodes before constructing
`KineticCrossfitPartition`, keep model-selection, fit, and validation episodes disjoint,
apply signed censoring at split boundaries, and reject in-sample E9B promotion. Synthetic
fixtures include observed edges, declared zero-event `RateCandidateEdge` records with
positive exposure, multiplicity-aware candidate universes, and multiple-testing policy.
Model-generation replay tests require parent/child signatures, bounded termination, and no
in-generation cycle.

## Real trajectory audit

The Na-LTA pilot reports accepted-frame fractions for every evidence mask,
registration diagnostics, topology and ring mapping, stationarity, attractor lineage,
basin/core probabilities, dwell support, force provenance, density-force
consistency, declared PMF temperature where admissible, moving-boundary diagnostics,
first-hit resolution, symmetry-orbit evidence, orthogonal site-evidence statuses,
unresolved fractions, and computational cost.
No universal LTA site model is released from synthetic fixtures alone.

# Deferred boundaries

The first data-driven implementation does not claim:

- arbitrary structure-fitted global rotation for periodic KDE;
- exact rotating/deforming-frame VACF or current;
- exact generalized forces for dynamic ring coordinates;
- reference-material registration for partial-periodic systems;
- general-manifold local charts or cores without a certified intrinsic model;
- a minimum-image Gaussian substituted for the periodized kernel without a bound;
- scientific grid convergence inferred from plotting's bandwidth-to-grid coupling;
- scientific promotion of the finest affordable grid when convergence was not reached;
- basin convergence treated as proof of transition-corridor convergence;
- grid convergence substituted for independent sampling-confidence certification;
- topology inferred from rendering meshes or uncertified sparse omissions;
- default symmetry augmentation or orbit pooling without exchangeability evidence;
- a universal site model transferable across species or temperatures;
- exact many-ion free energies at finite loading;
- automatic discovery of unsampled basins;
- a complete site or saddle catalog from any finite MD trajectory;
- ensemble inference from `SYSTEM`, filenames, directory labels, or user comments;
- canonical PMF interpretation of NVE data without an explicit approximation policy;
- equilibrium certification from thermostat settings alone;
- independent sample support inferred from raw frame count alone;
- a validated saddle from one crossing or from density adjacency alone;
- unique atomic site energies from framewise total energies;
- Boltzmann self-validation using the same occupancy data used to infer free energy;
- rejection of a source-qualified thermodynamic estimate solely because an independent
  cross-check is unavailable;
- thermodynamic results without exact estimator/source/channel/ensemble/partition
  provenance;
- unbiased PMFs from biased trajectories without reweighting;
- variable-cell force PMFs before the coordinate measure is specified;
- automatic treatment of thermostat or stochastic force contributions;
- exact cooperative multi-ion transition states;
- forced crystallographic O(1)/O(2)/O(3 labels without a validated profile;
- replacement of exact ring geometry by a circle, ellipse, or truncated harmonic model;
- a representative transition pathway from one observed jump;
- a minimum-free-energy path without supported PMF coverage;
- promoted Markovian kinetics before E9A pre-rate diagnostics, G0 state-model selection, and E9B post-fit validation pass;
- automatic rate-law selection; or
- barriers outside sampled or independently computed regions.

Conditional landscapes

$$
A_M(\mathbf q\mid\eta,\boldsymbol\xi_R)
$$

for local occupancy $\eta$ and framework descriptors $\boldsymbol\xi_R$ remain a
later extension after the one-body marginal architecture is validated.

# Borrowed theories and original constructions

## Borrowed or adapted foundations

The following methods are borrowed or adapted and must be cited in specifications
and source comments when implemented:

- natural tilings and zeolite natural-tile semantics [S11-13, S11-14];
- least-squares planes and orthogonal Procrustes alignment [S11-15, S11-17];
- kernel density estimation and mode estimation [S11-18, S11-19];
- mean-shift density-gradient mode seeking [S11-20];
- nonparametric density-ridge definitions [S11-34];
- discrete Morse theory on cell complexes as a basis for critical-cell bookkeeping [S11-35];
- hierarchical density clustering as an independent validator [S11-21];
- conditional mean force and average-force free-energy reconstruction [S11-22];
- force matching as a conditional mean-force estimator [S11-23];
- variational PMF reconstruction and Gaussian-process reconstruction from
  umbrella or gradient/force evidence [S11-24, S11-25, S11-31];
- Helmholtz-Hodge decomposition and Poisson integration [S11-26, S11-27];
- force-assisted reduced-variance density estimation [S11-28];
- metastable/core-set and Markov-state validation [S11-29, S11-30, S11-10];
- VASP source-control and ensemble semantics [S11-38--S11-42];
- correlated-data blocking, moving-block bootstrap, and effective-sample analysis [S11-36, S11-37, S11-46];
- persisted change-point detection for production-regime candidates [S11-47];
- explicit canonical/microcanonical ensemble-equivalence conditions [S11-48];
- exact low-count Poisson confidence intervals when a RateBoundModel is accepted [S11-49];
- WHAM and MBAR multistate free-energy estimation [S11-43, S11-44];
- restricted-ensemble/free-energy relations and thermodynamic derivatives [S11-45];
- transition-path ensemble and reactive-network concepts [S11-8]; and
- experimental LTA oxygen-class, centered S6R coordination, split-site, and
  off-center structural evidence [S11-32, S11-33].

Later kinetic work retains the existing citations for Eyring, Vineyard, Kramers,
Gillespie, TPT, milestoning, NEB, and umbrella sampling [S11-1--S11-12].

## Current mdstats architectural constructions

The following are project-specific design choices:

- the immutable source collection is separated from analysis-specific spatial
  registration;
- no universal drift-, rotation-, or strain-corrected trajectory is created;
- positions, cells, displacements, forces, and velocities follow distinct
  transform contracts;
- natural tiling and ring geometry interpret learned sites but do not create them;
- exact ordered chemical ring boundaries remain authoritative over circle, ellipse,
  or harmonic summaries;
- cyclic-index and rank-safe physical-angle spectra provide complementary
  structural and coordination descriptors;
- exact local displacement and ordered distances remain authoritative, while
  off-center residual harmonics remain diagnostic;
- position, force, temporal, stationarity, geometry, and curvature statuses
  remain orthogonal immutable results;
- manual site profiles are an optional branch rather than the default discovery
  path;
- statistical kernel covariance, analysis grid, and rendering resolution are distinct;
- field accuracy and topology stability are independently certified;
- one shared frame-registration signature and nested evidence catalog bind all
  discovery channels;
- raw and conservative force fields are retained together;
- curl, circulation, and periodic harmonic components are explicit diagnostics;
- nonparametric basins remain canonical even when compact models are fitted;
- site classes are conclusions from learned landscapes;
- source controls, not user labels, own ensemble inference;
- thermalization, stationarity, conservation, and PMF admissibility are separate
  certificates;
- numerical field support, basin support, event support, and catalog scope are
  distinct claims;
- every finite-trajectory catalog is partial and condition-scoped;
- occupancy free energy, conditional potential energy, entropy, and barrier free
  energy are separate quantities;
- population-derived thermodynamics require independent, noncircular validation;
- raw frame labels, segmented residences, and full transition paths are separate
  products;
- one observed connection, a resolved path ensemble, and an identifiable rate are
  separate claims;
- statistical-state instances, optional symmetry orbits, structural site complexes, and
  semantic classes are distinct identities;
- moving-boundary and first-hit resolution diagnostics remain explicit; and
- structural and observed transition networks remain distinct.

# References

[S11-1] Eyring, H. (1935). *The Activated Complex in Chemical Reactions*.
Journal of Chemical Physics, 3, 107-115. DOI:
[10.1063/1.1749604](https://doi.org/10.1063/1.1749604).

[S11-2] Vineyard, G. H. (1957). *Frequency Factors and Isotope Effects in
Solid State Rate Processes*. Journal of Physics and Chemistry of Solids, 3,
121-127. DOI:
[10.1016/0022-3697(57)90059-8](https://doi.org/10.1016/0022-3697(57)90059-8).

[S11-3] Kramers, H. A. (1940). *Brownian Motion in a Field of Force and the
Diffusion Model of Chemical Reactions*. Physica, 7, 284-304. DOI:
[10.1016/S0031-8914(40)90098-2](https://doi.org/10.1016/S0031-8914(40)90098-2).

[S11-4] Haenggi, P., Talkner, P., and Borkovec, M. (1990). *Reaction-Rate
Theory: Fifty Years after Kramers*. Reviews of Modern Physics, 62, 251-341.
DOI: [10.1103/RevModPhys.62.251](https://doi.org/10.1103/RevModPhys.62.251).

[S11-5] Zwanzig, R. (1992). *Dynamical Disorder: Passage through a Fluctuating
Bottleneck*. Journal of Chemical Physics, 97, 3587-3589. DOI:
[10.1063/1.462993](https://doi.org/10.1063/1.462993).

[S11-6] Gillespie, D. T. (1977). *Exact Stochastic Simulation of Coupled
Chemical Reactions*. Journal of Physical Chemistry, 81, 2340-2361. DOI:
[10.1021/j100540a008](https://doi.org/10.1021/j100540a008).

[S11-7] Fichthorn, K. A., and Weinberg, W. H. (1991). *Theoretical Foundations
of Dynamical Monte Carlo Simulations*. Journal of Chemical Physics, 95,
1090-1096. DOI: [10.1063/1.461138](https://doi.org/10.1063/1.461138).

[S11-8] Metzner, P., Schuette, C., and Vanden-Eijnden, E. (2009). *Transition
Path Theory for Markov Jump Processes*. Multiscale Modeling and Simulation, 7,
1192-1219. DOI: [10.1137/070699500](https://doi.org/10.1137/070699500).

[S11-9] Faradjian, A. K., and Elber, R. (2004). *Computing Time Scales from
Reaction Coordinates by Milestoning*. Journal of Chemical Physics, 120,
10880-10889. DOI: [10.1063/1.1738640](https://doi.org/10.1063/1.1738640).

[S11-10] Prinz, J.-H., Wu, H., Sarich, M., Keller, B., Senne, M., Held, M.,
Chodera, J. D., Schuette, C., and Noe, F. (2011). *Markov Models of Molecular
Kinetics: Generation and Validation*. Journal of Chemical Physics, 134, 174105.
DOI: [10.1063/1.3565032](https://doi.org/10.1063/1.3565032).

[S11-11] Henkelman, G., Uberuaga, B. P., and Jonsson, H. (2000). *A Climbing
Image Nudged Elastic Band Method for Finding Saddle Points and Minimum Energy
Paths*. Journal of Chemical Physics, 113, 9901-9904. DOI:
[10.1063/1.1329672](https://doi.org/10.1063/1.1329672).

[S11-12] Torrie, G. M., and Valleau, J. P. (1977). *Nonphysical Sampling
Distributions in Monte Carlo Free-Energy Estimation: Umbrella Sampling*.
Journal of Computational Physics, 23, 187-199. DOI:
[10.1016/0021-9991(77)90121-8](https://doi.org/10.1016/0021-9991(77)90121-8).

[S11-13] Blatov, V. A., Delgado-Friedrichs, O., O'Keeffe, M., and Proserpio,
D. M. (2007). *Three-Periodic Nets and Tilings: Natural Tilings for Nets*.
Acta Crystallographica Section A, 63, 418-425. DOI:
[10.1107/S0108767307038287](https://doi.org/10.1107/S0108767307038287).

[S11-14] Anurova, N. A., Blatov, V. A., Ilyushin, G. D., and Proserpio, D. M.
(2010). *Natural Tilings for Zeolite-Type Frameworks*. Journal of Physical
Chemistry C, 114, 10160-10170. DOI:
[10.1021/jp1030027](https://doi.org/10.1021/jp1030027).

[S11-15] Pearson, K. (1901). *On Lines and Planes of Closest Fit to Systems of
Points in Space*. Philosophical Magazine, Series 6, 2(11), 559-572. DOI:
[10.1080/14786440109462720](https://doi.org/10.1080/14786440109462720).

[S11-16] O'Rourke, J. (1998). *Computational Geometry in C*, 2nd edition.
Cambridge University Press.

[S11-17] Schoenemann, P. H. (1966). *A Generalized Solution of the Orthogonal
Procrustes Problem*. Psychometrika, 31, 1-10. DOI:
[10.1007/BF02289451](https://doi.org/10.1007/BF02289451).

[S11-18] Rosenblatt, M. (1956). *Remarks on Some Nonparametric Estimates of a
Density Function*. Annals of Mathematical Statistics, 27, 832-837. DOI:
[10.1214/aoms/1177728190](https://doi.org/10.1214/aoms/1177728190).

[S11-19] Parzen, E. (1962). *On Estimation of a Probability Density Function
and Mode*. Annals of Mathematical Statistics, 33, 1065-1076. DOI:
[10.1214/aoms/1177704472](https://doi.org/10.1214/aoms/1177704472).

[S11-20] Fukunaga, K., and Hostetler, L. D. (1975). *The Estimation of the
Gradient of a Density Function, with Applications in Pattern Recognition*.
IEEE Transactions on Information Theory, 21, 32-40. DOI:
[10.1109/TIT.1975.1055330](https://doi.org/10.1109/TIT.1975.1055330).

[S11-21] Campello, R. J. G. B., Moulavi, D., and Sander, J. (2013).
*Density-Based Clustering Based on Hierarchical Density Estimates*. In PAKDD
2013, Lecture Notes in Computer Science 7819, 160-172. DOI:
[10.1007/978-3-642-37456-2_14](https://doi.org/10.1007/978-3-642-37456-2_14).

[S11-22] Darve, E., and Pohorille, A. (2001). *Calculating Free Energies Using
Average Force*. Journal of Chemical Physics, 115, 9169-9183. DOI:
[10.1063/1.1410978](https://doi.org/10.1063/1.1410978).

[S11-23] Noid, W. G., Chu, J.-W., Ayton, G. S., Krishna, V., Izvekov, S.,
Voth, G. A., Das, A., and Andersen, H. C. (2008). *The Multiscale
Coarse-Graining Method. I. A Rigorous Bridge between Atomistic and
Coarse-Grained Models*. Journal of Chemical Physics, 128, 244114. DOI:
[10.1063/1.2938860](https://doi.org/10.1063/1.2938860).

[S11-24] Maragliano, L., and Vanden-Eijnden, E. (2008). *Single-Sweep Methods
for Free Energy Calculations*. Journal of Chemical Physics, 128, 184110. DOI:
[10.1063/1.2907241](https://doi.org/10.1063/1.2907241).

[S11-25] Stecher, T., Bernstein, N., and Csanyi, G. (2014). *Free Energy
Surface Reconstruction from Umbrella Samples Using Gaussian Process
Regression*. Journal of Chemical Theory and Computation, 10, 4079-4097. DOI:
[10.1021/ct500438v](https://doi.org/10.1021/ct500438v).

[S11-26] Bhatia, H., Norgard, G., Pascucci, V., and Bremer, P.-T. (2013).
*The Helmholtz-Hodge Decomposition - A Survey*. IEEE Transactions on
Visualization and Computer Graphics, 19, 1386-1404. DOI:
[10.1109/TVCG.2012.316](https://doi.org/10.1109/TVCG.2012.316).

[S11-27] Henin, J. (2021). *Fast and Accurate Multidimensional Free Energy
Integration*. Journal of Chemical Theory and Computation, 17, 6789-6798. DOI:
[10.1021/acs.jctc.1c00593](https://doi.org/10.1021/acs.jctc.1c00593).

[S11-28] Rotenberg, B. (2020). *Use the Force! Reduced Variance Estimators for
Densities, Radial Distribution Functions, and Local Mobilities in Molecular
Simulations*. Journal of Chemical Physics, 153, 150902. DOI:
[10.1063/5.0029113](https://doi.org/10.1063/5.0029113).

[S11-29] Sarich, M., Noe, F., and Schuette, C. (2010). *On the Approximation
Quality of Markov State Models*. Multiscale Modeling and Simulation, 8,
1154-1177. DOI:
[10.1137/090764049](https://doi.org/10.1137/090764049).

[S11-30] Guarnera, E., and Vanden-Eijnden, E. (2016). *Optimized Markov State
Models for Metastable Systems*. Journal of Chemical Physics, 145, 024102. DOI:
[10.1063/1.4954769](https://doi.org/10.1063/1.4954769).


[S11-31] Stecher, T., and Bernstein, N. (2016). *Exploration, Sampling, and
Reconstruction of Free Energy Surfaces with Gaussian Process Regression*.
Journal of Chemical Theory and Computation, 12, 4796-4807. DOI:
[10.1021/acs.jctc.6b00553](https://doi.org/10.1021/acs.jctc.6b00553).

[S11-32] Carey, T., Tang, C. C., Hriljac, J. A., and Anderson, P. A. (2014).
*Chemical Control of Thermal Expansion in Cation-Exchanged Zeolite A*.
Chemistry of Materials, 26, 1561-1566. DOI:
[10.1021/cm403312q](https://doi.org/10.1021/cm403312q).

[S11-33] Pluth, J. J., and Smith, J. V. (1979). *Crystal Structure of
Dehydrated Potassium-Exchanged Zeolite A. Absence of Supposed
Zero-Coordinated Potassium. Refinement of Si,Al-Ordered Superstructure*.
Journal of Physical Chemistry, 83, 741-749.

[S11-34] Genovese, C. R., Perone-Pacifico, M., Verdinelli, I., and Wasserman,
L. (2014). *Nonparametric Ridge Estimation*. Annals of Statistics, 42,
1511-1545. DOI:
[10.1214/14-AOS1218](https://doi.org/10.1214/14-AOS1218).

[S11-35] Forman, R. (1998). *Morse Theory for Cell Complexes*. Advances in
Mathematics, 134, 90-145. DOI:
[10.1006/aima.1997.1650](https://doi.org/10.1006/aima.1997.1650).


[S11-36] Flyvbjerg, H., and Petersen, H. G. (1989). *Error Estimates on
Averages of Correlated Data*. Journal of Chemical Physics, 91, 461-466. DOI:
[10.1063/1.457480](https://doi.org/10.1063/1.457480).


[S11-37] Geyer, C. J. (1992). *Practical Markov Chain Monte Carlo*.
Statistical Science, 7, 473-483. DOI:
[10.1214/ss/1177011137](https://doi.org/10.1214/ss/1177011137).

[S11-38] VASP Wiki. *MDALGO*. Official VASP documentation.
[https://vasp.at/wiki/MDALGO](https://vasp.at/wiki/MDALGO).

[S11-39] VASP Wiki. *Molecular-dynamics calculations*. Official VASP
documentation. [https://vasp.at/wiki/Molecular-dynamics_calculations](https://vasp.at/wiki/Molecular-dynamics_calculations).

[S11-40] VASP Wiki. *NVE ensemble*. Official VASP documentation.
[https://vasp.at/wiki/NVE_ensemble](https://vasp.at/wiki/NVE_ensemble).

[S11-41] VASP Wiki. *SMASS*. Official VASP documentation.
[https://vasp.at/wiki/SMASS](https://vasp.at/wiki/SMASS).

[S11-42] VASP Wiki. *OSZICAR*. Official VASP documentation.
[https://vasp.at/wiki/OSZICAR](https://vasp.at/wiki/OSZICAR).

[S11-43] Kumar, S., Rosenberg, J. M., Bouzida, D., Swendsen, R. H., and
Kollman, P. A. (1992). *The Weighted Histogram Analysis Method for Free-Energy
Calculations on Biomolecules. I. The Method*. Journal of Computational
Chemistry, 13, 1011-1021. DOI:
[10.1002/jcc.540130812](https://doi.org/10.1002/jcc.540130812).

[S11-44] Shirts, M. R., and Chodera, J. D. (2008). *Statistically Optimal
Analysis of Samples from Multiple Equilibrium States*. Journal of Chemical
Physics, 129, 124105. DOI:
[10.1063/1.2978177](https://doi.org/10.1063/1.2978177).

[S11-45] Kirkwood, J. G. (1935). *Statistical Mechanics of Fluid Mixtures*.
Journal of Chemical Physics, 3, 300-313. DOI:
[10.1063/1.1749657](https://doi.org/10.1063/1.1749657).

[S11-46] Kunsch, H. R. (1989). *The Jackknife and the Bootstrap for General
Stationary Observations*. Annals of Statistics, 17, 1217-1241. DOI:
[10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).

[S11-47] Killick, R., Fearnhead, P., and Eckley, I. A. (2012). *Optimal
Detection of Changepoints with a Linear Computational Cost*. Journal of the
American Statistical Association, 107, 1590-1598. DOI:
[10.1080/01621459.2012.737745](https://doi.org/10.1080/01621459.2012.737745).

[S11-48] Touchette, H. (2015). *Equivalence and Nonequivalence of Ensembles:
Thermodynamic, Macrostate, and Measure Levels*. Journal of Statistical Physics,
159, 987-1016. DOI:
[10.1007/s10955-015-1212-2](https://doi.org/10.1007/s10955-015-1212-2).

[S11-49] Garwood, F. (1936). *Fiducial Limits for the Poisson Distribution*.
Biometrika, 28, 437-442.


[S11-50] VASP Wiki. *vasprun.xml*. Official VASP output-format documentation.
[https://vasp.at/wiki/Vasprun.xml](https://vasp.at/wiki/Vasprun.xml).

[S11-51] VASP Wiki. *POTIM*. Official VASP timestep documentation.
[https://vasp.at/wiki/POTIM](https://vasp.at/wiki/POTIM).

[S11-52] VASP Wiki. *EDIFF*. Official VASP electronic-convergence documentation.
[https://vasp.at/wiki/EDIFF](https://vasp.at/wiki/EDIFF).

[S11-53] VASP Wiki. *PREC*. Official VASP precision-control documentation.
[https://vasp.at/wiki/PREC](https://vasp.at/wiki/PREC).

[S11-54] VASP Wiki. *LREAL*. Official VASP real-space projection documentation.
[https://vasp.at/wiki/LREAL](https://vasp.at/wiki/LREAL).

[S11-55] VASP Wiki. *CSVR thermostat*. Official VASP kinetic-energy and
degree-of-freedom documentation.
[https://vasp.at/wiki/CSVR_thermostat](https://vasp.at/wiki/CSVR_thermostat).

