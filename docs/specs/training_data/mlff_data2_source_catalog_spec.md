---
title: "MLFF-DATA2 Source, Label-Domain, and Atomic-Reference Specification"
subtitle: "mdstats 0.20.30a0"
date: "2026-07-28"
geometry: margin=0.78in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{xcolor}
    \usepackage{hyperref}
    \hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue}
    ```
---

# 1. Purpose

MLFF-DATA2 creates the first immutable dataset-level catalog in the mdstats
training-data branch. It converts manifest-declared `vasprun.xml` sources into
source records that answer four questions before any frame is selected:

1. What source bytes and composition produced the trajectory?
2. Which named VASP energy channel is the intended training energy?
3. Which calculations share one compatible electronic-structure label domain?
4. Are elemental atomic-reference corrections structurally identifiable from
   the available composition count vectors?

DATA2 does not assign frame eligibility, train/validation/test roles, strain,
or configuration fingerprints. Those belong to later gates.

# 2. Runtime boundary

DATA2 owns:

- JSON/YAML dataset manifests and deterministic source discovery;
- immutable source occurrence records;
- composition reconstructed from `atominfo`, never from path names;
- existing mdstats VASP control and ensemble certificates;
- explicit `VaspEnergyLabelPolicy` and `SelectedEnergyChannel` records;
- decomposed electronic-structure fingerprints;
- deterministic `LabelDomainCatalog` construction;
- source-level quality and production-regime references when requested;
- per-label-domain `AtomicReferenceIdentifiabilityCatalog` construction, containing one structural `AtomicReferenceIdentifiabilityReport` per resolved label domain.

DATA2 does not own:

- per-frame `frame_uid` or geometry fingerprints;
- DFT-label eligibility or duplicate-frame decisions;
- reference-cell resolution or strain tensors;
- structural feature extraction;
- fitted atomic reference energies;
- MACE files, replay data, or training execution.

# 3. Reused mdstats evidence

For each VASP source, DATA2 reuses:

```python
read_vasp_run_controls(...)
certify_vasp_simulation_controls(...)
```

The returned source identity binds source bytes, atom order, coordinate payload,
frame axis, and explicitly supplied companion files. Ensemble classification is
therefore based on VASP controls rather than a directory name or observed cell
fluctuation.

Full trajectory quality and production-regime assessment are optional through
`SourceTrajectoryAssessmentMode`:

```text
controls_only
full_if_available
full_required
```

`controls_only` is the deterministic low-cost default. `full_if_available`
records a transparent unavailable/failed state rather than pretending the
assessment ran. `full_required` propagates failures.

# 4. Manifest contract

## 4.1 Records

```python
TrainingDataRunSpec
TrainingDataManifest
```

A run specification contains only source location and declarations that cannot
be recovered reliably from one XML file:

```text
run_id
vasprun locator
companion-file locators
reference group
replica id
reference run id
scientific assertions
```

Assertions are not source facts. Later stages must verify them.

## 4.2 Discovery

```python
discover_vasp_manifest(root, dataset_id=..., system_profile=...)
```

Discovery:

1. finds matching `vasprun.xml` files in sorted relative-path order;
2. derives deterministic run identifiers from relative parent paths;
3. records no temperature, composition, ensemble, or strain claim from names;
4. emits a manifest note stating that scientific conditions remain unasserted.

The same root tree produces the same manifest digest.

## 4.3 Serialization

Every public policy and record has:

```text
schema
policy_version or manifest_version
content_digest or policy_digest
from_dict(...)
to_dict(...)
```

Digests are SHA-256 hashes of canonical JSON. They detect modification but are
not authenticated digital signatures.

# 5. Source composition

`SourceComposition` is reconstructed from the ordered atom-symbol list in
`atominfo`.

It records:

```text
element counts
atom count
deterministic reduced formula
```

No composition is inferred from `SYSTEM`, file names, or folder names. The
composition atom count must agree with the existing
`SourceTrajectoryBundleIdentity.atom_count` when that count is available.

# 6. Named VASP energy policy

## 6.1 Motivation

`vasprun.xml` contains multiple energy channels, including electronic free
energy (`e_fr_energy`), energy without entropy, and extrapolated zero-smearing
energy. VASP documents that forces and stress are consistent with the free
energy, not the extrapolated zero-smearing energy. Consequently, an MLFF energy
label must be selected explicitly rather than through a generic `energy` alias
[1,2].

## 6.2 Policy

The default is:

```python
VaspEnergyLabelPolicy(
    channel="e_fr_energy",
    require_complete=True,
    derivative_consistency="electronic_free_energy",
    output_key="REF_energy",
    normalization="total_per_cell",
)
```

Selection fails when:

- the channel is absent;
- completeness is required but one or more frames are missing;
- the channel semantic role differs from the declared derivative surface.

`SelectedEnergyChannel` records:

```text
source-control-bundle digest
energy-catalog digest
policy digest
source channel and semantic role
units and source path
frame/present counts
completeness fraction
output key and normalization
value-payload digest
```

The record identifies the values without duplicating the complete energy
series.

# 7. Electronic-structure fingerprint

`ElectronicStructureFingerprint` is deliberately decomposed.

## 7.1 `TheoryIdentity`

Contains:

- exchange-correlation identifiers;
- DFT+U controls;
- PAW dataset descriptions by element;
- spin formalism;
- dispersion controls;
- hybrid-functional controls;
- resolution state and missing-evidence notes.

PAW mappings are compared only on overlapping elements. A Li-only and Na-only
source may share one label domain when their common theory controls agree and
neither source contradicts the other. If two sources both contain O but use
different O PAW datasets, they are incompatible.

## 7.2 `EnergyReferenceIdentity`

Contains:

- selected channel and semantic role;
- units and normalization;
- `ISMEAR` and `SIGMA` evidence;
- entropy/free-energy convention;
- resolution state.

Different free-energy or normalization conventions form separate domains.

## 7.3 `DerivativeConvention`

The DATA2 normalized derivative contract is:

```text
forces: eV/angstrom, negative energy gradient
stress: Cauchy stress, eV/angstrom^3, tensile-positive
representation: symmetric Cartesian 3 x 3
off-diagonal terms: tensor shear, no engineering factor
```

DATA8 must still verify the stress convention against the locked MACE adapter.

## 7.4 `NumericalQualityProfile`

Contains numerical settings and traces that may change label quality without
necessarily changing the theory:

```text
ENCUT
k-point count and payload digest
EDIFF
NELM/NELMIN
ALGO/IALGO
PREC
LREAL
LASPH
ISYM
SCF-limit fraction
```

## 7.5 `SoftwareProvenance`

Contains VASP version/subversion, mdstats parser version, and control-semantics
version. Software differences are provenance or quality warnings by default,
not automatic theory changes.

# 8. Label compatibility and domains

`LabelCompatibilityPolicy` produces one of:

```text
compatible
compatible_with_quality_flag
separate_label_domain
unresolved
```

The default rules are:

1. unresolved required theory or energy-reference evidence -> `unresolved`;
2. incompatible theory or overlapping PAW mapping -> `separate_label_domain`;
3. different energy reference -> `separate_label_domain`;
4. different derivative convention -> `separate_label_domain`;
5. numerical or software differences -> `compatible_with_quality_flag`;
6. otherwise -> `compatible`.

## 8.1 Domain construction

`build_label_domain_catalog(...)` processes sources in sorted source-id order.
A source joins the first existing group with which it is compatible with every
member. This complete-link rule prevents a transitive bridge from merging two
sources that directly conflict.

Each `LabelDomain` records:

```text
domain id
aggregate core-label digest
source ids
source fingerprint digests
numerical-quality variants
software-provenance variants
quality flags
```

Unresolved sources receive no target-domain assignment unless an explicit
later policy resolves them.

The first MACE adapter enforces one target label domain per initial MACE bundle. Different target domains produce different bundles. MACE supports
multi-head datasets, but DATA2 intentionally keeps the first target contract
narrow and auditable [3].

# 9. Structural atomic-reference identifiability

MACE decomposes total energy into elemental baseline terms and an interaction
energy. Estimating elemental corrections requires solving a linear system whose
design matrix contains element counts [4,5]. DATA2 audits only the structure of that matrix. The audit is performed separately for every resolved label domain; incompatible DFT domains are never combined into one count matrix.

Given source compositions $c=1,\ldots,m$ and elements $Z=1,\ldots,p$,

$$
A_{cZ}=N_Z(c).
$$

Compute the singular-value decomposition

$$
A = U\Sigma V^T.
$$

The numerical rank is

$$
r = \#\{\sigma_i > \epsilon\max(\sigma_1,1)\},
$$

where the relative tolerance is policy-controlled.

`AtomicReferenceIdentifiabilityCatalog` binds the active policy and one `AtomicReferenceIdentifiabilityReport` per resolved label domain. Each report records:

```text
source row ids
element order
integer count matrix
rank and singular values
condition number when full column rank
null-space dimension
identifiable row-space combinations
null-space basis
policy outcome
transfer limitations
```

**No energy values enter the structural rank audit.** No target-minus-foundation
residual, fitted E0 value, or held-out label is inspected in DATA2.

Outcomes are:

```text
identified
rank_deficient_but_fixed_domain_usable
rejected
```

A rank-deficient fixed-stoichiometry domain may proceed to later fold-local
fitting, but individual elemental corrections are non-unique. The report states
that the result is not transferable to changed Si/Al ratio, defect count,
cation count, salt phase, or interface.

Actual E0 fitting belongs to DATA7 and is repeated separately for every fold and
for final training. MACE documentation and releases describe least-squares
atomic-reference estimation and warn about reference-energy problems during
training [4-6].

# 10. Source catalog algorithm

`build_training_data_source_catalog(...)` performs:

```text
for each manifest run in sorted run-id order:
    resolve source and explicit companion paths
    reconstruct immutable VASP source-control bundle
    certify ensemble
    select named energy channel
    parse composition, PAW descriptors, and k-point payload
    construct decomposed electronic-structure fingerprint
    optionally run quality and production assessments

construct complete-link label domains
fail closed on unresolved domains when policy requires
assign domain ids to immutable source records
construct one count-matrix atomic-reference audit per resolved label domain
serialize TrainingDataSourceCatalog
```

The catalog records source-level facts only. DATA3 creates frame occurrences,
geometry/label fingerprints, duplicate detection, eligibility, temperatures,
reference cells, and strain.

# 11. Determinism and failure behavior

DATA2 fails explicitly for:

- missing source files;
- malformed XML;
- empty or inconsistent atom lists;
- absent/incomplete required energy channels;
- semantic mismatch between energy and derivative surface;
- conflicting overlapping PAW datasets;
- unresolved label domains under fail-closed policy;
- malformed digests or modified serialized payloads;
- invalid atomic count vectors.

The following are recorded rather than silently guessed:

- missing XC or smearing evidence;
- optional full-trajectory assessment unavailable;
- numerical-quality variants inside one domain;
- rank-deficient atomic-reference design;
- path-derived scientific conditions not verified.

# 12. Public API

```python
from mdstats import (
    TrainingDataManifest,
    TrainingDataRunSpec,
    discover_vasp_manifest,
    VaspEnergyLabelPolicy,
    SelectedEnergyChannel,
    select_vasp_energy_channel,
    LabelCompatibilityPolicy,
    compare_label_fingerprints,
    build_label_domain_catalog,
    AtomicReferenceIdentifiabilityCatalog,
    AtomicReferenceIdentifiabilityPolicy,
    AtomicReferenceIdentifiabilityReport,
    analyze_atomic_reference_identifiability,
    SourceAuditPolicy,
    TrainingDataSource,
    TrainingDataSourceCatalog,
    build_training_data_source_catalog,
)
```

# 13. Focused gate

DATA2 is accepted when tests establish:

- deterministic discovery and manifest replay;
- no scientific inference from paths;
- named energy selection and failure on absent/incomplete channels;
- compatible numerical variants group together;
- theory/reference conflicts separate domains;
- unresolved domains fail closed by default;
- disjoint element sets may share one compatible theory domain;
- overlapping PAW conflicts cannot share a domain;
- E0 rank/null-space results match analytic fixtures;
- all public records round-trip and reject modified payloads;
- DATA1 and existing VASP-control/ensemble tests remain passing;
- wheel import and source-package integrity pass.

# References

[1] VASP Wiki, “vasprun.xml.” The XML energy fields include
`e_fr_energy` as free energy and stress in kbar.
<https://vasp.at/wiki/Vasprun.xml>

[2] VASP Wiki, “Smearing technique.” Forces and stress are consistent with the
free energy rather than the extrapolated zero-smearing energy.
<https://vasp.at/wiki/Smearing_technique>

[3] ACEsuit, “Multihead Training for MACE.”
<https://mace-docs.readthedocs.io/en/latest/guide/multihead_training.html>

[4] ACEsuit, “Training MACE models.” Atomic reference energies and least-squares
estimation are part of the training interface.
<https://mace-docs.readthedocs.io/en/latest/guide/training.html>

[5] ACEsuit, MACE source and release history, version 0.3.16 baseline.
<https://github.com/ACEsuit/mace/releases/tag/v0.3.16>

[6] ACEsuit, “Troubleshooting and Q&A Guide.” Energy-reference mismatch is a
common cause of large initial energy error.
<https://mace-docs.readthedocs.io/en/latest/guide/troubleshooting.html>
