---
geometry: margin=0.52in
fontsize: 9pt
---

# TARGET-DATA2C-MVIDX1 exact sparse coverage-index specification

**Release:** `mdstats 0.20.201a0`  
**Architecture revision:** `68`  
**Dependency-graph schema:** `50`  
**Status:** implemented index substrate; TARGET-DATA2C v4 selection remains executable and unchanged.

## Authority

MVIDX1 consumes the frozen TARGET-DATA2B reference, TARGET-DATA2A role freeze, and TARGET-DATA2B-FEAS1 record. For every **required** TARGET-DATA2B family it constructs exact witness-to-candidate and candidate-to-witness sparse adjacency under the unchanged scaled-RMS/local-radius coverage metric. Neighbor elements are reduced to sorted unique candidate-frame identities, so one candidate covers a witness iff the existing TARGET-DATA2B scorer can cover that witness through at least one family element from that frame.

Production arrays use little-endian `uint32` candidate/witness indices and `uint64` offsets. Dense persistent all-pairs distance matrices and persistent Python-object neighbor graphs are forbidden. Query worker count and query block size are execution-only and excluded from scientific identity.

## Hard-obligation substrate

The domain index separately freezes bidirectional obligation adjacency for required lower/upper extent witnesses, TARGET-DATA2B strata (with their required flag/minimum), and every TARGET-DATA2A development correlation interval. Candidate correlation-unit codes and sorted unit identities are persisted explicitly. This substrate does not decide the later lexicographic selector objective; it only makes exact obligation/marginal queries available to MVSEL1/REPAIR1.

## Persistence and restart

Scientific graph evidence is persisted as content-addressed authenticated NPY sidecars with a small JSON manifest. The manifest binds TARGET-DATA2B, TARGET-DATA2A, FEAS1, family, frame-domain, policy, obligation, unit, dtype/shape, and SHA-256 identities. Future heaps, marginal-gain vectors, covered masks, and scratch arrays are reconstructible caches and are not part of MVIDX1 authority. Restart reuse requires unchanged upstream digests and exact forward/inverse sparse consistency.

## Acceptance

Qualification requires: worker/block-invariant graph digests; exact forward/inverse agreement; geometric rebuild equivalence on deterministic fixtures/production-style coverage data; exact covered-mass and marginal-gain agreement with TARGET-DATA2B; exact extent/stratum/correlation obligation indexing; native persistence round-trip and checksum tamper rejection; no selector/default change; and regression-clean TARGET-DATA2B/C/D behavior.

**Next gate:** `TARGET-DATA2C-MVSEL1`.
