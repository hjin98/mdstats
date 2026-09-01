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

Scientific graph evidence is persisted as content-addressed authenticated NPY sidecars with a small JSON manifest. Native persistence v2 packs all family witness offsets, witness candidates, candidate offsets, and candidate witnesses into four shared read-only NPY mappings; each family is an authenticated canonical slice of those roots and retains its unchanged scientific array references/content digest. Open family-array mappings therefore remain O(1) in family count. The forward-only MVSEL2/REPAIR2 projection opens only the two candidate-oriented packed roots. Domain obligation/correlation arrays remain independently authenticated because their cardinality scales with label domains rather than feature families. The manifest binds TARGET-DATA2B, TARGET-DATA2A, FEAS1, family, frame-domain, policy, obligation, unit, dtype/shape, and SHA-256 identities. Future heaps, marginal-gain vectors, covered masks, and scratch arrays are reconstructible caches and are not part of MVIDX1 authority. Restart reuse requires unchanged upstream digests and exact forward/inverse sparse consistency.

Legacy native persistence v1 stored four NPY members per family and can exhaust `RLIMIT_NOFILE` at production family counts despite bounded RAM. Because MVIDX1 is reconstructible, a v1 pointer is rejected before sidecar walking; the campaign rebuilds it from authenticated NEIGHBOR1 without recomputing target geometry, then writes v2 under the unchanged MVIDX1 scientific digest.

Native restart validation preserves those identities while bounding execution footprint. On a validation miss, each large adjacency array is checked in one chunked sequential pass combining value-SHA, range, and strict within-row ordering/uniqueness checks. A completed-validation receipt may be stored in the campaign's trusted local receipt database, keyed by the authenticated manifest plus each sidecar's resolved path, device, inode, size, modification time, and change time. An exact receipt hit maps arrays without walking their data; any changed identity falls back to full validation and fails closed on integrity or scientific-invariant mismatch. Receipts, progress reporting, and memory-map advice are execution-only.

Restore supports retain, discard, and automatic file-cache policies.  Full
validation uses sequential mapping advice where supported.  The automatic policy
may release already-validated clean mapped pages when the authenticated logical
payload is large relative to currently available memory; this changes only
reclaimable file-cache residency.  It must not copy adjacency payloads into the
Python heap, mutate persisted arrays, or change subsequent query results.

## Acceptance

Qualification requires: worker/block-invariant graph digests and exact forward/inverse agreement; deterministic geometric rebuild equivalence; exact covered-mass, marginal-gain, and extent/stratum/correlation obligations; packed native round-trip and tamper rejection; one-pass validation, receipt-hit/stat invalidation, and bounded cache-policy/progress behavior; O(1) family-array mappings for full and forward-only restore under constrained `RLIMIT_NOFILE`; early legacy-v1 rebuild routing; unchanged selectors/defaults; and regression-clean TARGET-DATA2B/C/D behavior.
