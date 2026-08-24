# TARGET-DATA2B-FEAS1-NEIGHBOR1-OUT-OF-CORE-MEM1 — bound aggregate forward-CSR RAM

**Status:** active
**Current authority:** `docs/specs/training_data/mlff_neighbor1_exact_neighborhood_spec.md`, `docs/specs/training_data/mlff_parcore1_deterministic_work_queue_spec.md`
**Target branch/base:** `fix/feas1-neighbor-memory-fd-bounds` from uploaded `mdstats-feat-target-size-v5-redesign (6)`

## Objective

Remove the production FEAS1/NEIGHBOR1 failure in which completed forward-CSR families accumulate as resident NumPy arrays until their aggregate size exhausts the stage RAM budget. Preserve exact FEAS1 reductions, NEIGHBOR1 identities/digests, MVIDX reuse semantics, canonical ordering, and PAR90 CPU authority. Final forward CSR shall be file-backed for campaign execution, with only bounded finalization scratch charged to PARCORE1 RAM admission.

## Invariants

- FEAS1 report content and FP64 reduction order are unchanged.
- NEIGHBOR1 `uint64` offsets, `uint32` candidate indices, row ordering, family/domain/store digests, and persistence schemas are unchanged.
- MVIDX cache-hit geometry reuse remains exact; no second geometry sweep is introduced.
- PARCORE1 remains fail-closed for anonymous execution RAM. Temporary reservation contention is backpressure, while an intrinsically oversized reservation remains an error.
- Campaign final CSR storage may exceed the RAM budget because it is disk-backed; bounded copy/finalization scratch may not.
- Completed-family file mappings MUST NOT scale open file descriptors with family count; build and persisted restore shall use O(1) shared CSR mappings.
- The runtime 90%-CPU budget and single-level cKDTree parallelism are unchanged.

## Scope

Included: `work_queue.py`, exact-neighborhood stream/builders, FEAS1 global scheduler, native NEIGHBOR1 persistence, campaign FEAS1 staging/handoff, MVIDX1 native persistence/restore descriptor scaling, focused tests, and the owning NEIGHBOR1/PARCORE1/MVIDX1 specifications.

Excluded: target-size-v5 scientific selection policy, 3/10/30 halving, MVIDX/MVSEL scientific algorithms, GPU qualification, and unrelated storage formats.

## Gates

### G0 — Reproduce and freeze the resource contract

**Goal:** encode the observed failure mode as a deterministic small-budget regression.

**Work:**

- Add queue coverage for temporary persistent-reservation contention and improved diagnostics.
- Add a FEAS1 fixture where every active profile/block fits the RAM budget but aggregate completed forward CSR exceeds it.

**Acceptance:** historical output-retention behavior would fail the aggregate fixture; the new path completes with unchanged scientific output.

### G1 — File-backed NEIGHBOR1 finalization

**Goal:** prevent aggregate forward-CSR bytes from becoming anonymous resident output state.

**Work:**

- Allow `ExactNeighborhoodCSRStream` to finalize into NPY-backed memmaps under an optional build directory.
- Copy raw streamed candidate edges into the final NPY payload in bounded chunks; offsets are written directly to NPY memmap.
- Charge only bounded finalization scratch to PARCORE1 and defer finalization when that scratch cannot yet be reserved.
- Keep the direct API compatible when no out-of-core directory is supplied.

**Acceptance:** exact family/store digests match the in-memory/direct path; large final arrays remain file-backed.

### G2 — Native persistence handoff

**Goal:** avoid recopying whole NPY-backed arrays when campaign persistence can adopt them by same-filesystem hardlink.

**Work:**

- Reuse the accepted MVIDX whole-NPY-memmap hardlink pattern in the NEIGHBOR1 native writer.
- Build campaign FEAS1 forward CSR under the campaign external-record directory, persist it, reload the durable native store, then remove transient build paths.
- Emit explicit disk-storage telemetry and fail clearly if finalization cannot allocate required disk space.

**Acceptance:** campaign-restored arrays are read-only native-store memmaps and no transient build path remains after successful handoff.

### G3 — Qualification and authority reconciliation

**Goal:** prove equivalence and record the corrected current contract.

**Work:**

- Run PARCORE1, FEAS1, NEIGHBOR1, native-persistence, and MVIDX cache-hit focused tests with the supplied dependency bundle.
- Update NEIGHBOR1/PARCORE1 specifications to state out-of-core final CSR and reservation-backpressure semantics.

**Acceptance:** focused regressions pass; no scientific schema/digest change is required; no GPU claim is made.


### G4 — File-descriptor scaling closeout

**Goal:** remove the second production ceiling exposed after CSR payloads became file-backed.

**Work:**

- Detach and close each completed family mmap immediately after FEAS1/NEIGHBOR1 finalization.
- Compact staged families into two shared mappings: one packed `uint64` offsets array and one packed `uint32` candidates array.
- Emit native persistence v2 using those two packed arrays and canonical per-family slices; retain v1 read compatibility without reusing v1 records as v2 writes.
- Add a constrained-`RLIMIT_NOFILE` regression spanning FEAS1 build, native persistence, and reload.

**Acceptance:** a 96-family fixture completes under a low descriptor ceiling where the preceding out-of-core patch deterministically fails with `EMFILE`; restored scientific/store digests remain unchanged and open mapped-file descriptors remain bounded independently of family count.

### G5 — MVIDX1 native file-descriptor scaling closeout

**Goal:** remove the per-family mmap descriptor ceiling from full MVIDX1 restart and forward-only MVSEL2/REPAIR2 restore.

**Work:**

- Advance reconstructible MVIDX1 native persistence to packed v2 storage with four shared family-array roots: witness offsets, witness candidates, candidate offsets, and candidate witnesses.
- Represent each family as authenticated canonical slices of those roots while preserving every existing per-family scientific array reference and content digest.
- Make full restore map four family roots independent of family count; make forward-only restore map only the two candidate-oriented roots.
- Reject legacy v1 per-family pointers before sidecar validation so production restart rebuilds MVIDX1 from the persisted NEIGHBOR1 authority instead of walking ~100 GiB and eventually failing with `EMFILE`.
- Preserve receipt-hit behavior, cache advice, tamper rejection, and exact MVIDX1/MVSEL2 scientific identity.
- Add a constrained-`RLIMIT_NOFILE` 96-family regression covering full and forward-only native restore.

**Acceptance:** full and forward-only restore remain digest-exact under a low descriptor ceiling; family-array mapped descriptors are O(1) in family count; legacy v1 cache state fails fast into the existing reconstructible-cache rebuild path; no target-size or selector semantics change.

## Closeout

When all gates pass, archive this workplan only after the implementation is accepted; retain it active in the implementation patch so review can trace the transition.

## Implementation result

All implementation gates are complete in this candidate and await acceptance. The aggregate-memory regression uses 266 exact families under a 70,000-byte explicit stage RAM budget: the untouched uploaded baseline fails from PARCORE1 memory admission after retained final CSR accumulates, while this implementation completes with 70,224 bytes of final CSR payload because the payload is file-backed and only bounded finalization scratch is admitted. Focused PARCORE1, FEAS1, NEIGHBOR1 native-persistence, and MVIDX cache-consumer tests pass with the supplied dependency bundle (ASE source used directly from the bundle). Follow-up G4 is also complete: the preceding candidate deterministically reproduces `EMFILE` under the constrained descriptor regression, while this candidate completes FEAS1 build and packed native reload with bounded descriptor use. NEIGHBOR1 native persistence is advanced to v2 packed-array storage with v1 read compatibility. G5 closes the analogous MVIDX1 restart defect: native persistence v2 packs four family-array roots, full/forward restore use O(1) family mappings, and legacy per-family MVIDX1 pointers are rejected before expensive validation so the existing campaign restart path rebuilds this reconstructible cache from NEIGHBOR1. No GPU qualification was attempted or claimed.
