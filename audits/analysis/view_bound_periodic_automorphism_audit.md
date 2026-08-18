# View-Bound Periodic Automorphism Validation Audit

Date: 2026-07-18  
Version: `0.19.15a0`  
Architecture: revision 22

## Scope

This gate upgrades the exact Stage-5 P2 action prototype so that every accepted
periodic multigraph automorphism belongs to one immutable `PeriodicNetView` and
preserves its deterministic signature policy.

It does not discover automorphisms, normalize representatives modulo a common
translation, construct a group, serialize symmetry results, or compute orbits and
stabilizers.

## Implemented contracts

- `ValidatedPeriodicAutomorphism.periodic_net_view_digest` source ownership;
- builder validation against `PeriodicNetView` rather than `PrimitiveRingIndex`;
- exact vertex-signature preservation;
- exact edge-signature preservation;
- explicit multiedge permutation/orientation;
- exact quotient-edge endpoint and image-shift incidence;
- integer unimodular lattice action;
- active-PBC-subspace preservation for partially periodic inputs;
- view-bound physical edge-instance mapping;
- stable `FrameworkEdgeKey` conversion between net-view edge positions and
  primitive-ring catalog edge indices;
- view-bound `RingOccurrenceMap` provenance; and
- exact retained P2 cyclic/reversed occurrence alignment.

## Scientific invariants

- Symmetry belongs to `Aut(PeriodicNetView)`, not to bare topology connectivity.
- An action validated under one view cannot be reused under another view of the
  same topology.
- Equal signatures permit exchange but never merge vertices or parallel edges.
- `PeriodicEdgeImage.target_edge_index` is a position in the owning view edge
  sequence.
- `PrimitiveRingStep.edge_index` remains local to the ring catalog; the two dense
  domains are bridged only through `FrameworkEdgeKey`.
- Primitive-ring enumeration, keys, digests, and physical support are unchanged.

## Algorithmic provenance

Periodic quotient-edge labels follow Chung, Hahn, and Klee (1984), DOI
`10.1107/S0108767384000088`. The exact combinatorial periodic-net automorphism
viewpoint follows Delgado-Friedrichs and O'Keeffe (2003), DOI
`10.1107/S0108767303012017`.

View-signature ownership, active-PBC-subspace validation, source-safe edge-domain
bridging, and exact occurrence-level ring adaptation are mdstats-specific.

## Validation

Direct periodic-ring-action tests:

```text
13 passed
```

Focused Stage-4/5/net-view regression gate:

```text
88 passed
```

Coverage includes:

- identity/common-translation and unimodular lattice actions;
- cyclic rotation and reversed ring orientation;
- explicit parallel-edge exchange;
- invalid edge incidence;
- graph and view-digest mismatch rejection;
- Si/Al exchange accepted in the unlabeled T-net view but rejected in the
  chemically decorated view;
- O/S parallel-edge exchange accepted in the unlabeled view but rejected in the
  chemically decorated view;
- partial-PBC lattice-mixing rejection; and
- all 82 Na-LTA primitive-ring orbits and 432 ordered ring-step occurrences.

## Gate decision

**PASS.**

The next symmetry gate is automatic exact discovery plus deterministic
representative gauge and group closure. Those should build on the present
view-bound validator rather than duplicate its incidence/signature checks.
