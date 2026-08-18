---
title: "MLFF-DATA9A7d Optional Profile Extensions and LTA Migration"
author: "mdstats project"
date: "2026-07-30"
version: "0.20.50a0"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{enumitem}
    \setlist{nosep}
    ```
---

# 1. Purpose

MLFF-DATA9A7d completes the ownership inversion begun in DATA9A7a--DATA9A7c.
The generic MLFF core must not assume that a material contains zeolite rings,
cages, adsorption sites, or alkali cations. Those concepts are valuable for LTA,
but they are optional material-profile extensions rather than universal
training-data concepts.

This stage therefore introduces a generic extension envelope for
partition-critical and selection-grade evidence, migrates LTA payloads behind
that envelope, and replaces the remaining cation-specific decision defaults
with profile-declared atom groups or data-derived species sets.

The numerical LTA algorithms are not rewritten. Their scientific ownership
remains in the existing LTA provider modules. DATA9A7d changes how their results
are identified, serialized, and consumed by generic MLFF machinery.

# 2. Normative ownership boundary

The generic MLFF core owns:

- extension identity and activation checks;
- provider and configuration identity;
- stage and parent-bundle lineage;
- immutable serialization and content digests;
- common frame-vector, atomic-environment, and environment-class adapter calls;
- generic atom-group focus policies;
- generic coverage and production-gate evidence.

An extension provider owns:

- the scientific meaning of its payload;
- its numerical algorithms and domain assumptions;
- extension-specific feature names and missing-value semantics;
- extension-specific event and environment-class definitions;
- decoding of its own payload schema.

For the LTA extension, ring, cage, window, site, and crossing semantics remain
owned by `lta_profile.py` and `lta_selection.py`. Generic DATA4--DATA7 code may
consume only the standardized extension interfaces unless it is inside the
explicit compatibility adapter.

# 3. Generic extension record

`ProfileFeatureCatalog` is the canonical optional-extension envelope. It binds:

| Field | Meaning |
|---|---|
| `extension_id` | Stable lowercase extension identifier, such as `lta` |
| `stage` | `partition` or `selection` |
| `provider_identity` | Provider ID, provider version, and configuration digest |
| `frame_catalog_digest` | Exact frame population described by the payload |
| `parent_bundle_digest` | Required DATA4 parent for selection-stage evidence |
| `payload_schema` | Scientific schema owned by the provider |
| `payload` | Immutable provider-owned evidence |
| `content_digest` | Canonical envelope digest |

Partition-stage catalogs cannot depend on a later bundle. Selection-stage
catalogs must bind the exact DATA4 bundle from which they were constructed.
Foreign frame catalogs, parent bundles, providers, stages, and inactive
extensions fail closed.

The material profile remains authoritative. A declared generic profile cannot
carry an LTA catalog. LTA catalogs require the explicit extension chain

```text
porous_network -> zeolite -> lta
```

Historical unprofiled LTA bundles remain readable through compatibility paths,
but new production evidence should always carry explicit profile contracts.

# 4. Standard extension adapters

The core recognizes three optional adapter surfaces:

1. `frame_feature_vector(frame_uid)` returns immutable feature names, numerical
   values, and missing masks for DATA7 fitting.
2. `atomic_environment_descriptors()` returns provider-owned atomic
   environments suitable for generic environment selection.
3. `environment_class_labels(frame_uids)` returns stable labels for coverage
   reporting.

An extension is not required to implement every adapter. Unsupported adapters
must fail explicitly or return an empty collection as documented. Generic code
must not inspect the provider payload directly.

The LTA compatibility adapter supplies all three surfaces while preserving its
existing numerical results.

# 5. DATA4 migration

DATA4 advances to schema v3. Canonical serialization contains
`profile_partition_features` and no LTA-named field. The Python object retains
`lta_partition_features` only as a compatibility view derived from the active
`lta` extension.

Full-resolution event evidence records generic profile-feature catalog digests.
The historical `lta_feature_catalog_digest` remains a compatibility alias in the
event record so v1 evidence can be restored exactly. New generic event logic
uses extension catalogs and does not branch on LTA payload internals.

DATA4-v1 and DATA4-v2 records and caches remain readable. Transition-era bundles
that changed only their schema marker while retaining additive fields are also
accepted only when their exact raw canonical digest verifies.

# 6. DATA6 migration

DATA6 advances to schema v4. Canonical serialization contains
`profile_selection_features`. The old `lta_selection_features` attribute is a
compatibility view only.

The default policy no longer turns on LTA feature construction. LTA selection
features are built only when:

- the material profile activates the LTA extension and an LTA partition catalog
  exists; or
- a historical unprofiled DATA4 bundle explicitly carries LTA evidence and the
  compatibility policy requests it.

The generic DATA7 metric block is named `profile_extensions`. The historical
`lta_frame` block remains readable as an alias. Feature columns are supplied by
the extension adapter and remain namespaced, for example `lta:ring_crossing`.

# 7. Generic focus groups and species handling

The generic core shall not define `(Li, Na, K)` as the important species. A
material profile may mark atom groups with roles such as:

```text
mlff_focus
training_focus
validation_focus
```

`focus_atom_group_ids()` returns those groups. `focus_atomic_numbers()` resolves
static group selectors against the current atomic-number sequence. If no focus
group exists, the fallback is every species present in the authorized domain,
not a predefined chemistry list.

This policy controls:

- species-resolved raw and learned descriptor summaries;
- difficulty ranking;
- atomic-environment selection priorities;
- optional group-aware training objectives;
- optional focus-group checkpoint constraints.

The runtime retains `cation_atomic_numbers`,
`species_aware_force_objective`, and
`maximum_cation_force_rmse_ev_per_angstrom` only as deprecated aliases for v1
records. No cation semantics are inferred from them.

# 8. Generic independence and production qualification

`structural_realization_id` replaces `cation_ordering_id` as the generic
independence axis. Examples include chemical ordering, defect realization,
interface registry, amorphous realization, molecular conformer, and porous-site
occupation. The v1 cation-ordering field and grade remain readable aliases.

Production qualification now reports
`profile_extension_coverage_materialized`. If no feature-bearing extension is
required, this condition passes vacuously. If LTA is declared, a verified LTA
partition extension must be present. The historical
`site_coverage_materialized` constructor field is retained only for v1 Python
compatibility and is not emitted by canonical v2 evidence.

# 9. Compatibility rules

The following compatibility guarantees are required:

- DATA4-v1/v2 and DATA6-v1/v2/v3 load without fabricated new evidence;
- LTA numerical payloads round-trip exactly through the extension envelope;
- historical objective, checkpoint, and partition records preserve their
  digests;
- deprecated Python properties expose old names without changing canonical v2
  serialization;
- generic profiles never serialize LTA fields or import LTA algorithms on the
  normal no-extension path;
- explicit LTA profiles preserve existing numerical fixtures.

Compatibility aliases must not appear in newly written canonical evidence
unless they are required to verify a historical nested record.

# 10. Failure semantics

The stage must reject:

- a profile feature whose extension is not activated;
- a partition catalog placed in DATA6 or a selection catalog placed in DATA4;
- a selection catalog bound to the wrong DATA4 digest;
- duplicate extension/provider identities;
- LTA evidence under a generic profile;
- group-aware objectives without declared focus groups or species;
- focus-force checkpoint thresholds without a declared focus domain;
- tampered provider payloads or envelope digests.

# 11. Focused test plan

The release gate covers:

1. LTA partition and selection payload wrapping and exact restoration.
2. Canonical DATA4/DATA6 serialization without LTA-named fields.
3. Explicit-extension rejection under a generic profile.
4. Common frame-vector and environment adapters.
5. Non-alkali focus-group resolution, including chloride.
6. Generic per-species feature columns derived from authorized data.
7. v1 objective, checkpoint, partition, DATA4, DATA6, and production-record
   compatibility.
8. Generic production extension-coverage evidence.
9. Existing DATA4--DATA7, LTA, phase-profile, selection, and architecture tests.
10. Source-tree/wheel registry parity and installed-wheel smoke.

# 12. Deferred work

DATA9A7d does not implement a new porous or zeolite scientific algorithm. It
only places existing LTA semantics behind the correct extension boundary.
DATA9A7e will qualify generic crystal, amorphous, liquid, interface, and LTA
workflows end to end. DATA9A8 will define profile-aware physical-observable
comparison policies.
