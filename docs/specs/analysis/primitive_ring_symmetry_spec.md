---
title: "Primitive-Ring Symmetry Index Specification"
subtitle: "Stage 7R: Compact Catalog-Bound Derived Ring Action"
author: "mdstats"
date: "2026-07-18"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.82in
fontsize: 10pt
colorlinks: true
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
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose and boundary

`primitive_ring_symmetry.py` stores the exact action of one
`PeriodicNetSymmetry` on one `PrimitiveRingCatalog`. It is a derived index, not a
field of the core net-symmetry result.

Runtime/API target:

```text
mdstats 0.19.19a0
```

The ownership chain is

```text
PeriodicNetView
    -> PeriodicNetSymmetry
PrimitiveRingCatalog
    -> PrimitiveRingIndex
        + PeriodicNetSymmetry
        -> PrimitiveRingSymmetryIndex
```

This split prevents a net automorphism group from depending on a particular ring
search bound and binds every ring orbit explicitly to the exact catalog that
supplied it.

# Motivation

A periodic-net automorphism group is defined by the decorated graph view. A
primitive-ring action additionally depends on:

- which ring family was enumerated;
- the minimum and maximum search sizes;
- resource-completeness metadata; and
- the exact ring-catalog digest.

Persisting ring data inside `PeriodicNetSymmetry` merged two scientific sources,
repeated complete `PrimitiveRingKey` payloads for every operation, and allowed a
ring action to be restored without recording the exact catalog provenance.

# Mathematical action

For normalized operation

$$
g(i,\mathbf n)=
\left(\pi_g(i),A_g\mathbf n+\boldsymbol\tau_i^g\right),
$$

and canonical zero-shift ring representative $R_k$, the derived action records

$$
g(R_k)=T_{\mathbf s_{gk}}R_{p_g(k)},
$$

plus one cycle parameterization

$$
(c_{gk},\epsilon_{gk}),
\qquad \epsilon_{gk}\in\{-1,+1\}.
$$

`p_g(k)` is stored as an integer ring position, not as a repeated full key.

Normalized representatives compose with cocycle

$$
\widehat g\widehat h
=T_{\mathbf c(g,h)}\widehat{gh}.
$$

Therefore exact placement composition requires

$$
\mathbf s_{gh,k}
=
A_g\mathbf s_{h,k}
+
\mathbf s_{g,p_h(k)}
-
\mathbf c(g,h).
$$

The builder verifies this identity for every operation pair and every stored
ring. It also verifies composition of cycle orientation and start position.

# Public API

```python
@dataclass(frozen=True, slots=True)
class RingSymmetryImage:
    target_ring_position: int
    target_image_shift: LatticeShift
    parameterization: CycleParameterization
```

```python
@dataclass(frozen=True, slots=True)
class PrimitiveRingSymmetryIndex:
    periodic_net_symmetry_digest: str
    periodic_net_view_digest: str
    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    complete_for_ring_sizes_up_to: int
    source_search_completed_without_resource_truncation: bool
    ring_keys: tuple[PrimitiveRingKey, ...]
    action_table: tuple[tuple[RingSymmetryImage, ...], ...]
    ring_orbits: tuple[tuple[int, ...], ...]
    ring_stabilizers: tuple[tuple[int, ...], ...]
    digest: str
```

Builder:

```python
build_primitive_ring_symmetry_index(
    view: PeriodicNetView,
    symmetry: PeriodicNetSymmetry,
    ring_index: PrimitiveRingIndex,
    *,
    max_composition_checks: int = 5_000_000,
) -> PrimitiveRingSymmetryIndex
```

Convenience methods include:

```python
ring_position(ring_key)
ring_key(position)
ring_image(operation_index, ring_key)
target_ring_key(image)
map_placement(symmetry, operation_index, placement)
```

# Source invariants

Construction requires:

1. `symmetry.periodic_net_view_digest == view.digest`;
2. matching topology graph digests;
3. the same framework edge-orbit set in the view and ring catalog;
4. one exact action row per symmetry operation;
5. one exact image per catalog ring; and
6. a complete group-action homomorphism under the stored translation cocycle.

The index stores the catalog completeness bound but does not reinterpret it. Ring
orbits are complete only for the supplied catalog.

# Compact persistence

Schema:

```text
mdstats.primitive-ring-symmetry.v1
```

Complete ring keys appear once. Table cells carry only:

```text
target ring position
three-integer image shift
start position
orientation
```

For the Na-LTA gate, this reduces the ring-action JSON from repeated full-key
records to approximately 1 MB while preserving all 96-by-82 exact images.

# Serialization

`from_dict()` requires all three source objects:

```python
PrimitiveRingSymmetryIndex.from_dict(
    payload,
    view=view,
    symmetry=symmetry,
    ring_index=ring_index,
)
```

The method rebuilds and revalidates the complete action table. A payload cannot
be transferred to another symmetry group or another primitive-ring catalog even
when the topology graph is the same.

# Edge cases

- empty ring catalog: supported as an empty finite domain only if the action table
  shape is consistent;
- ring catalog with different edge set: rejected;
- different view policy on the same topology: rejected by view digest;
- catalog with same keys but different provenance: rejected by catalog digest;
- nonsymmorphic operation: image shifts are composed with the exact cocycle;
- translated input placement: mapped by $A_g\mathbf t+\mathbf s_{gk}$;
- resource limit exceeded during homomorphism validation: no partial index is
  returned.

# Focused tests

- identity, rotation, and reflection actions;
- ring orbit and stabilizer partitions;
- parallel-edge and occurrence orientation handling;
- source-bound serialization;
- wrong-group and wrong-catalog rejection;
- exact translated-placement action; and
- all 82 Na-LTA rings under the 96-operation group.

# References

[1] S. J. Chung, Th. Hahn, and W. E. Klee, *Acta Cryst. A* **40**, 42-50
(1984), doi:10.1107/S0108767384000088.

[2] O. Delgado-Friedrichs and M. O'Keeffe, *Acta Cryst. A* **59**, 351-360
(2003), doi:10.1107/S0108767303012017.
