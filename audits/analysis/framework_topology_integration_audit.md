# Na-LTA framework-topology integration audit

## Version 0.15.0 orientation repair

The Na-LTA fixture uses the symmetric T-O-T rule and therefore preserves its
48-vertex, 96-edge scientific topology. Digests changed because mapping and
topology canonical schemas advanced to version 2. The mapping digest is
`a38c678e9702d3ea0008d3f5fe60056aa2c5c86007c8f9749b9931c59bac7496`.

## Fixture

- Source: `tests/data/Na_LTA_relaxed.POSCAR`
- Total atoms: 168
- Composition ordering: Si24 Al24 O96 Na24
- Projection: Si/Al as `VERTEX`, O as `LINKER`, Na as `SPECTATOR`
- Accepted path rule: exact T-O-T (`oxygen_bridge`)

## Framework-only source connectivity

- Active source atoms: 144
- Atomic T-O edges: 192
- Projected vertices: 48
- Projected edges: 96
- Si vertices: 24
- Al vertices: 24
- Projected components: 1
- Vertex degree set: [4]
- Linker framework-degree set: [2]
- Unused linkers: 0
- Parallel vertex pairs: 0
- Self-image edges: 0
- Validation passed: True
- Graph digest: `a11779ac721754899e847216877051f717377ed63c81e9935a78c7f46c87d42c`
- Mapping-aware digest: `11d0b594ba1564d14ede796e86b5a73901f91d5c2e31ab031b5b202ce96a4af4`

## Broader connectivity with Na-O contacts

- Active source atoms: 168
- Source atomic edges: 302
- Ignored spectator/excluded source edges: 110
- Projected vertices: 48
- Projected edges: 96
- Graph digest: `a11779ac721754899e847216877051f717377ed63c81e9935a78c7f46c87d42c`
- Mapping-aware digest: `11d0b594ba1564d14ede796e86b5a73901f91d5c2e31ab031b5b202ce96a4af4`

## Invariance result

- Framework graph digests equal: True
- Mapping-aware digests equal: True
- Source connectivity digests differ: True

The broader atomic graph changes only source provenance and projection diagnostics.
It does not change the projected framework identity.
