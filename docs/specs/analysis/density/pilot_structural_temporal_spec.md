---
title: "Stage 11E8a-S3 Structural Mapping and Temporal-Support Preparation"
subtitle: "Source-bound Na-LTA serrated-ring association and full-trajectory provisional assignment"
author: "mdstats"
date: "2026-07-26"
version: "0.20.13a0"
status: "implemented"
---

# 1. Scope

Stage 11E8a-S3 extends the source-bound S2 spatial pilot with two products:

1. a structural association between the central exploratory Na-density
   attractors and the packaged persistent Na-LTA primitive-ring catalog; and
2. a Stage 11E4 provisional temporal assignment over the complete 1,500-frame
   represented-time sample catalog.

S3 does not declare the S2 central bandwidth or saddle topology authoritative.
It does not certify final states, final hysteretic events, transition paths,
rates, or a global PMF. Structural and temporal results remain provisional when
the upstream S2 scale or grid certificate is unresolved.

The implementation owner is:

```text
mdstats.analysis.density.pilot_structural_temporal
```

# 2. Public operation

```python
prepare_na_lta_300k_structural_temporal_pilot(
    collection,
    trajectory_path,
    *,
    options=None,
    s2_options=None,
    s1_options=None,
    density_resources=None,
    attractor_options=None,
    attractor_resources=None,
    temporal_resources=None,
    audit_policy=None,
    metadata=None,
)
```

The operation executes the complete S0--S2 source, registration, quadrature,
density, attractor, lineage, refinement, and reference-cell contracts before
constructing S3 evidence. Every output remains bound to the exact raw trajectory
digest, selected framework-registration signature, central density signature,
and central attractor-catalog signature.

# 3. Packaged structural sources

S3 packages and validates:

```text
mdstats/data/na_lta_framework_topology.json
mdstats/data/na_lta_primitive_ring_catalog.json
```

The framework topology is the persistent T--O net used by the Stage 11 ring
pipeline. The primitive-ring catalog contains 82 no-shortcut primitive rings
complete through ring size eight:

```text
36 four-rings
40 six-rings
 6 eight-rings
```

These are graph-theoretic primitive rings. S3 does not silently relabel every
ring as a chemically unique adsorption site, crystallographic window, or cage.
Those semantic classifications require separate evidence.

The topology and primitive-ring digests must match their packaged records.
S3 also verifies that the normalized trajectory uses the expected framework
index layout and that every replayed mean T--O bond lies inside the declared
physical compatibility interval. The default interval is 1.20--2.20 Å.

# 4. Mean registered ring geometry

Ring geometry is evaluated in the selected S1 registered cell from the mean
registered framework coordinates. For each primitive ring, S3 expands the
ordered alternating T--O atomic walk and retains the ordered oxygen vertices.

Periodic ring polygons are reconstructed locally. Starting from the first
oxygen vertex, each next oxygen is unwrapped relative to the previous one by the
triclinic Cartesian minimum-image displacement. This local construction avoids
false multi-cell stretching that can arise from applying lifted graph-image
labels directly as Cartesian polygon coordinates.

For each ring S3 stores:

- ring and oxygen-atom identities;
- periodic center in fractional and Cartesian coordinates;
- fitted plane normal and orthonormal in-plane basis;
- the actual ordered oxygen polygon in plane coordinates;
- minimum, mean, and maximum oxygen radius; and
- plane-fit RMS residual.

The default maximum ring-planarity RMS is 0.50 Å. Exceeding it fails closed.

# 5. Serrated-polygon association

The irregular oxygen boundary is normative. S3 must not replace the ring by a
perfect circle or ellipse.

For each attractor anchor and each ring, S3 computes the minimum-image anchor
relative to the ring center and reports:

- center distance;
- signed plane distance and side sign;
- whether the projected anchor lies inside the ordered oxygen polygon;
- signed clearance to the nearest polygon edge;
- radial position relative to the actual serrated boundary along the projected
  center-to-anchor ray; and
- a combined association distance formed from plane distance and any
  outside-polygon distance.

The radial quantity is

```text
projected center-to-anchor radius / serrated polygon ray-intersection radius
```

and is not an ellipse-normalized radius. The nearest declared number of
candidates is retained; the default is three.

An association is `unique` only when the best candidate is within the declared
maximum association distance and exceeds the runner-up by the declared minimum
margin. The default limits are 2.75 Å and 0.12 Å. Otherwise the status is
`ambiguous`, `outside_limit`, or `unresolved`.

The structural catalog metadata explicitly records:

```text
serrated_polygon_mapping = true
circle_or_ellipse_substitution = false
```

# 6. Exact spatial-partition transfer

The S1/S2 density catalog retains all registered coordinates but assigns
positive statistical weight only to deterministic representative frames. That
catalog is appropriate for density discovery, but it cannot by itself certify
contiguous trajectory support.

S3 therefore applies the central E2 spatial partition to the full S0 E0b Na
sample catalog only through the Stage 11E4 exact-transfer contract. Transfer is
permitted only when the discovery and assignment catalogs have identical:

- source-contract and registration signatures;
- topology-assignment signature;
- selected species and atom indices;
- frame indices and frame identifiers;
- sample atom indices;
- registered Cartesian coordinates;
- registered wrapped fractional coordinates; and
- registered image shifts.

Only represented-time weights may differ. Any coordinate, atom, frame,
registration, topology, or ordering mismatch fails closed. Successful transfer
is recorded with both catalog signatures and
`partition_transfer_identity = exact_registered_coordinate_identity`.

# 7. Provisional temporal diagnostics

After exact partition transfer, S3 executes the existing Stage 11E4 operation on
the full frame-major sample catalog. It retains raw membership classes, core
visits, preliminary residences, preliminary passages, local decorrelation
estimates, stride diagnostics, censoring, and unresolved gaps.

The result remains provisional:

- no nearest-center fill is introduced;
- no unsupported gap is bridged;
- return excursions are distinct from jumps;
- right-censored exits remain censored evidence; and
- Stage 11E6 final hysteresis and Stage 11E6b path reconstruction are not
  executed by S3.

# 8. Dossier semantics

S3 replaces the `structural_mapping` and `temporal_support` evidence records.
A unique ring association or persistent temporal pattern is `resolved` only
when the upstream S2 scale consensus and grid-topology certificate are also
authoritative. Otherwise the record is `partial`, even if every individual
attractor association is unique or the full-trajectory temporal result is
persistent.

This distinction prevents local geometric clarity from being misreported as a
converged state model.

After S3, the expected missing required evidence is:

```text
force_density_agreement
transition_paths
```

The dossier therefore remains `blocked_missing_required_evidence`. Stage
11E8b remains prohibited.

# 9. Determinism and failure rules

- Options and every structural record are signed by canonical JSON SHA-256.
- Packaged topology and primitive-ring digests are replayed exactly.
- Ring order, oxygen order, candidate order, and attractor order are
  deterministic.
- Nonfinite geometry, incompatible framework bonds, excessive planarity,
  source mismatch, or partition-transfer mismatch fails closed.
- A unique structural mapping does not override unresolved S2 scale or saddle
  topology.
- A persistent provisional temporal pattern does not publish final events or
  rates.

# 10. Required validation

Focused tests cover:

- signed S3 option and catalog serialization;
- public root and analysis exports;
- exact packaged topology and 82-ring reconstruction;
- 36/40/6 four-/six-/eight-ring counts;
- actual serrated-polygon metadata and no circle/ellipse substitution;
- deterministic locally unwrapped periodic polygons;
- framework-bond and planarity gates;
- unique, ambiguous, and out-of-limit candidate logic;
- exact coordinate-identical partition transfer and mismatch rejection;
- full represented-time temporal sample count;
- dossier missing-evidence reduction; and
- real ASE-backed Na-LTA replay.
