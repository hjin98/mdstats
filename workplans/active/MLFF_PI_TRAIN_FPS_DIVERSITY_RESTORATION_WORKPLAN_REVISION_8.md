---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 8
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
exact_revision_5_basis:
  commit: d06d98c70455714065035bc434bd949d5b71856d
  path: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_5.md
  blob: 4274096c9a7878c27c934a4aa531b22e49324398
exact_revision_6_basis:
  commit: 01c4bbc63283f226060e6e6defe8f468a906dea9
  path: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_6.md
  blob: bca434dd5961eed69fc21f71bdea50ab557f5fa9
exact_revision_7_basis:
  commit: b43a4f36ddf0d809d20a560fba45a6e3dba13cce
  path: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_7.md
  blob: cc46e90885d1cdc43ac6d95ece5fffedf9c53524
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: stakeholder-restoration-direction-recorded-exact-d1-d2-reconciliation-still-required
---

# MLFF `pi_train` latest-path restoration — Revision 8 closure

## 0. Authoritative Revision-8 composition

Revision 8 is the exact composition of immutable Revision 5, immutable Revision 6, immutable Revision 7, and this closure document. Revision 8 has precedence only where it tightens or corrects those earlier artifacts. All otherwise compatible Revision-5/6/7 scientific, numerical, architectural, persistence, currentness, performance, evidence, documentation, PEM/HAS, and human-gate obligations remain binding.

The prior Revision-7 PASS is reopened because another independent Protocol-6.3 challenge pass found seven remaining plan-level defects:

1. the final recovery snapshot already superseded the earlier 1.75x native-activation rule, but Revision 7 still treated 1.75x as the default to preserve unless disproven;
2. current `TargetTrainingOrder` owns a complete permutation of `P_train`, while performance qualification was still expressible as configured-rung-only work;
3. post-REPAIR continuation did not explicitly invalidate every newly restored prefix-dependent selector execution cache/history surface;
4. MVQUAL progressive scheduling did not explicitly preserve serial rung evolution inside one family state;
5. the final accepted NEIGHBOR1/MVIDX out-of-core generation included disk-admission and O(1)-file-descriptor properties that Revision 7 did not make explicit restoration obligations;
6. the Revision-5 PEM/HAS locator named `4eabe2...` as the PEM publication even though the PEM at that commit still described an older accepted base; and
7. the recovery carrier `3937881...` was not explicitly separated from the P5A6 accepted executable provenance it is being used to recover.

Sections 1-7 close those defects. This remains a restoration/rebinding plan, not an authorization to invent a new selector or target-size architecture.

---

## 1. Recovery provenance and final native-preflight semantics

### 1.1 Recovery carrier versus accepted executable provenance

The accessible coherent recovery carrier remains:

```text
hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c
```

P6 itself records its accepted P5A6 entry implementation as:

```text
commit 1670275487d29bbcde4c59efafdef9d1f8b0ced7
tree   17e2c5609974712bda1efd3375f09f42da830f68
```

Revision 8 therefore forbids treating the phrase "recovery snapshot" as proof that every restored blob is automatically the accepted P5A6 executable realization. R2 shall bind every restored semantic/performance source surface to one of:

```text
P5A6-byte/content-equivalent executable source carried at 3937881...
OR
later accepted same-semantic execution optimization carried at 3937881...
OR
historical reference/evidence only
OR
explicitly rejected/superseded machinery
```

Where the exact P5A6 commit/tree is no longer directly resolvable through the active repository interface, the recovered 393 blob identity plus immutable P6 entry-baseline records and accepted historical execution evidence are the provenance route. Any material ambiguity remains `REVIEW_REQUIRED`; do not create a hybrid by silently selecting whichever historical file is easiest to restore.

### 1.2 Correct final native worker-preflight baseline

The exact final recovery-snapshot `mvsel2_native_preflight.py` owns the mature baseline execution policy:

```text
minimum_parallel_speedup = 1.05
economical_tolerance     = 0.05
worker probes            = 1, powers of two below budget, exact budget endpoint
```

The meter warms and scores deterministic real-MVIDX rows, requires bitwise FP64 equality across worker counts, and chooses the smallest parallel width whose elapsed time lies within the economical tolerance of the measured best; if best parallel speedup is below the threshold it selects one worker.

Therefore Revision 7 Section 7.5 is corrected:

- historical **1.75x** is evidence from the earlier V5 native redesign, not the final recovered runtime default;
- restore the final 1.05 / 0.05/logarithmic-plus-endpoint policy as the default current concretization unless a current representative measurement justifies a same-semantics D4 retune;
- any retune must be explicit, measured, execution-only, and independently prove unchanged order/FP64 semantics; it may not arise merely from confusing an earlier benchmark gate with the final runtime policy;
- meter results, thresholds, selected width, and timing remain outside scientific identity.

This closes a concrete historical-generation drift rather than adding new policy.

---

## 2. Complete-`P_train` optimized full-order closure

Current `TargetTrainingOrder` requires one exact permutation of all `P_train`. Historical production timing through 16,384 is not sufficient evidence for a current order when `|P_train| > Nmax_current`.

Revision 5's full-order semantics remain authoritative and are strengthened operationally:

1. run restored MVSEL2 + configured REPAIR2 through every current configured shell;
2. after the final configured repair, reconstruct an exact forward state from the final repaired prefix and authenticated primitive inputs;
3. invalidate all incompatible pure-selector continuation state as Section 3 requires;
4. continue the **same optimized exact MVSEL2 engine** from that repaired prefix until `selected_count == |P_train|`;
5. no UID suffix, historical-Nmax stop, scalar-only suffix, alternate continuation selector, or unqualified fallback may appear after the last configured target-size rung;
6. MVQUAL remains a configured-rung qualification owner and is not extended artificially over the non-candidate suffix.

### 2.1 Full-order performance evidence

Representative assembled qualification must measure the complete preparation order to `|P_train|`, not stop timing at `Nmax_current`. Report separately:

```text
configured-prefix MVSEL/REPAIR wall and edge work
post-final-repair reconstruction cost
suffix ranks and suffix wall time
suffix evaluated edges/rank and effective backend width
complete-order wall/RSS/I/O
full-order checkpoint/restart cost
```

At least one interruption/resume fixture shall occur strictly beyond `Nmax_current` when `|P_train| > Nmax_current`. Resumed and uninterrupted complete orders must be identical.

If the suffix exposes a new scaling bottleneck, first verify that the accepted optimized engine and caches are active. A material current-envelope defect may reopen D3/D4 performance design, but it cannot be hidden by truncating the order or switching to UID completion.

---

## 3. Post-REPAIR cache, frontier, history, and journal invalidation

Revision 5 already invalidates stale pre-repair forward state and lazy frontier after a swap. Revision 7 restores additional execution caches/history that must obey the same semantic boundary.

After the first accepted REPAIR2 swap at a configured shell, the following pure-selector state derived from the pre-swap prefix is stale for scientific continuation:

- witness-term execution caches whose generation/prefix ancestry precedes the repaired prefix;
- lazy heap/frontier entries and exact-generation arrays;
- native candidate-score batches or preflight state whose validity assumes the old prefix state;
- MVSTATE2 checkpoint state authenticating the pure-selector prefix;
- rank-history/journal state if it is used as continuation/authentication rather than historical diagnostic evidence;
- any reconstructed plan-history cache that assumes the pre-repair selected order.

Required behavior:

1. rebuild compact forward state from primitive sparse authority and the exact repaired prefix;
2. verify multiplicity, coverage, obligation and correlation invariants;
3. rebuild witness-term/lazy/native execution caches from that state rather than patching pre-swap caches;
4. begin any suffix continuation journal/checkpoint under identity that binds the repaired-prefix/repair-plan identity;
5. pre-repair rank history may remain immutable historical diagnostic evidence, but cannot authorize post-repair continuation;
6. after a zero-swap REPAIR2 result, unchanged pure-selector state/history may remain usable if its exact prefix identity still matches.

Required differential falsification:

```text
warm pure-selector caches/history
 -> accepted repair swap
 -> continuation to suffix
```

must produce the identical complete order as a cold primitive replay/reconstruction from the repaired prefix. A deliberately stale pre-repair cache/journal presented after divergence must fail closed or be discarded/rebuilt; it may never be silently consumed.

---

## 4. MVQUAL progressive-state concurrency DAG

Revision 7 Section 9.3 is narrowed to match the accepted P2/P3 execution semantics.

For one exact nested `(group, family)` progressive state:

```text
rung 1 -> rung 2 -> ... -> rung k
```

is a serial state evolution. Witness multiplicity, sole-owner identity, unique-count state, and newly-added-row deltas for a family are carried forward in canonical rung order and shall not be concurrently mutated by per-rung tasks.

Permitted concurrency is across independent state owners:

- distinct families within the same group;
- distinct groups when they share no mutable progressive state and the aggregate stage resource budget admits them;
- bounded-reference/fallback jobs only where they do not mutate one shared progressive state.

Scientific reduction remains canonical family/rung order after arbitrary task completion. Worker count cannot alter the progressive/fallback classification, coverage masses, owner predicates, qualification, or digest.

Do not "restore parallel rung scoring" by splitting one progressive family state into racing per-rung futures. The accepted optimization gains work reduction by carrying state across rungs; preserving that dependency is part of the capability transfer.

---

## 5. Final NEIGHBOR1/MVIDX OOC, disk, and file-descriptor closure

Revision 7's generic file-backed/OOC language is strengthened to the final accepted execution generation recovered in `TARGET_DATA2B_FEAS1_NEIGHBOR1_OUT_OF_CORE_MEM1`.

### 5.1 Aggregate RAM versus durable file-backed output

Final NEIGHBOR1/MVIDX sparse payload may exceed the stage RAM budget only because durable/finalized payload is file-backed. Anonymous/transient working memory and finalization scratch remain resource-admitted and bounded.

Completed family payloads shall not accumulate as anonymous NumPy arrays until aggregate CSR exceeds RAM.

### 5.2 O(1)-in-family-count mapped-file descriptors

Restore or equivalently preserve the accepted descriptor-scaling property:

- NEIGHBOR1 final storage uses packed shared roots/slices rather than one live mapping/file descriptor per family;
- MVIDX full restore uses a bounded number of shared packed roots independent of family count;
- forward-only MVSEL2/REPAIR2 restore maps only the candidate-oriented roots needed by those consumers;
- mapped file-descriptor count is O(1) in family count.

A constrained `RLIMIT_NOFILE` regression with many families is mandatory. Scientific/store digests and sparse arrays must remain exact.

### 5.3 Legacy reconstructible cache rejection

A historical per-family MVIDX persistence layout that would require large sidecar walking and can hit descriptor limits shall be rejected early as an incompatible reconstructible cache and rebuilt from authenticated NEIGHBOR1 authority. Do not spend product-scale I/O validating an obsolete cache shape only to fail late.

This is cache invalidation/rebuild, not semantic migration of retired target-size authority.

### 5.4 Disk/scratch admission and crash-safe handoff

Before a potentially large OOC build/finalization, the current storage/resource owner must account for:

- expected final durable sparse bytes;
- temporary/finalization scratch and copy/write amplification;
- currently available/quota-constrained storage when discoverable;
- file/inode/descriptor constraints where material;
- concurrent writer/adoption ownership.

Required behavior/evidence:

- insufficient disk or simulated `ENOSPC`/write failure fails before or during build without publishing a partial accepted selector artifact;
- disk footprint and scratch telemetry are visible enough to diagnose admission;
- same-filesystem adoption/hardlink or equivalent copy avoidance may be reused only when current storage ownership and integrity semantics permit it;
- successful handoff leaves no stale transient build tree that remains current by pathname accident;
- interrupted/concurrent build publication cannot make a partial object reachable from an adopted prepared generation;
- cleanup removes only attempt-owned temporary state after proving no protected generation references it.

The existing prepared-generation/CampaignStore currentness owner remains the only adoption authority; no selector-specific storage GC is introduced.

---

## 6. Correct Protocol-6.3 PEM/HAS basis

Revision 5's substantive HAS dispositions remain useful, but its `accepted_pem` locator is corrected.

At project state `4eabe2ae9783c7ff92f3a1093c37502a01380812`, the PEM file itself still described the older accepted base and an unresolved candidate notice. The descendant PEM publication that explicitly advanced the accepted memory basis to `4eabe2...` and retired that notice is:

```text
hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
```

The current workplan basis/main is `e72090e...`; the branch adds only workplan/review artifacts and has no PEM candidate overlay. The session-local HAS is therefore refreshed as:

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: mature selector restoration must return capability to real current owners rather than recreate parallel old/new owner stacks
  - id: SP-002
    disposition: APPLICABLE
    reason: coverage/MVIDX/MVSTATE/repair/qualification/prepared identities are corruption- and lineage-sensitive fail-closed boundaries
  - id: SP-003
    disposition: APPLICABLE
    reason: expensive selector/reference/sparse products require immutable authenticated reuse and bounded restart rather than recomputation from live inputs
  - id: SP-004
    disposition: APPLICABLE
    reason: real prepare/publication/restart/downstream consumer boundaries and representative-scale qualification are necessary to expose integration/performance defects
  - id: FF-001
    disposition: REVIEW_REQUIRED
    reason: applicable only if R1 retains model/foundation-derived selector evidence; then model/provider realization must remain under one authenticated owner
  - id: FF-002
    disposition: APPLICABLE
    reason: MVSTATE2, rank history, OOC partial builds and post-repair continuation directly exercise authenticated restart boundaries
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: selector restoration must stay beneath existing prepared/storage mutation ownership and introduces no second destructive cleanup owner
  - id: FF-004
    disposition: REVIEW_REQUIRED
    reason: becomes applicable if R1 retains accelerator-backed selector providers; resource facts then remain owned by the real provider/process boundary
  - id: FF-005
    disposition: APPLICABLE
    reason: downstream select/CV/production must consume the immutable prepared selector result and never reconstruct preparation-owned science
```

The PEM remains intentionally `PARTIAL`; it does not establish absence of pre-August-20 selector/performance lessons. The direct historical intake already required by Revision 5/7 remains mandatory and now expressly includes the final NEIGHBOR1/MVIDX OOC/FD lineage and final native-preflight source.

If the accepted project state or PEM publication materially advances before integration/closeout, refresh the affected HAS interval instead of closing against this frozen review basis.

---

## 7. Gate, falsification, and pass-criteria amendments

### 7.1 R2 additions

Before executable restoration, R2 must additionally close:

- recovery-carrier/P5A6 blob provenance from Section 1.1;
- final native-preflight `1.05` / `0.05` policy disposition;
- final NEIGHBOR1/MVIDX packed-OOC/descriptor lineage;
- progressive MVQUAL state-concurrency ownership;
- all prefix-dependent selector cache/history invalidation surfaces.

### 7.2 R4 additions

NEIGHBOR1/MVIDX acceptance now includes:

- aggregate file-backed CSR larger than a bounded RAM fixture;
- bounded finalization scratch;
- O(1)-in-family-count mapped descriptors under constrained `RLIMIT_NOFILE`;
- legacy per-family cache early rejection/rebuild;
- disk admission/telemetry and simulated write/ENOSPC interruption;
- concurrent/partial publication cannot reach prepared adoption.

### 7.3 R5/R6 additions

MVSEL2/REPAIR acceptance now includes:

- exact final native-preflight baseline or explicitly requalified current same-semantics retune;
- cache/frontier/journal invalidation after repair divergence;
- cold repaired-prefix replay versus warm-pre-repair-cache divergence fixture;
- optimized suffix continuation to full `|P_train|`;
- suffix restart strictly beyond `Nmax_current` where possible.

### 7.4 R7 additions

MVQUAL acceptance must prove:

- serial rung evolution within each progressive family state;
- deterministic concurrency only across independent state owners;
- progressive and bounded fallback equality under worker/completion-order variation;
- no per-rung racing mutation of one progressive family state.

### 7.5 R9 assembled performance closure

Final current-scale evidence must cover the entire `prepare` critical path through a complete `TargetTrainingOrder`, including configured rung work, final repaired-prefix reconstruction, suffix-to-`P_train` exhaustion, publication, fresh-process reload, and downstream no-rebuild routing.

Also record peak mapped file descriptors and final/scratch disk footprint for selector sparse artifacts, in addition to Revision-7 CPU/RAM/I/O metrics.

### 7.6 Additional falsification cases

Add to the composed Revision-5/6/7 set:

21. final native preflight at 393 defaults to 1.05/0.05 semantics; earlier 1.75 evidence cannot silently override it;
22. a current representative order with `|P_train| > Nmax_current` is optimized and deterministic through the last frame;
23. interruption/resume beyond `Nmax_current` yields the exact uninterrupted complete order;
24. a deliberately warm pre-repair witness cache/lazy frontier/rank journal is rejected or rebuilt after an accepted repair swap;
25. zero-swap repair preserves valid pure-selector continuation without unnecessary semantic invalidation;
26. progressive MVQUAL gives identical results when family task completion is perturbed, while rungs within one family remain serial;
27. an attempted concurrent per-rung progressive-state mutation is structurally absent or explicitly rejected;
28. many-family NEIGHBOR1/MVIDX restore passes under constrained `RLIMIT_NOFILE` with bounded mapped roots;
29. legacy per-family MVIDX cache is rejected before expensive full sidecar validation and rebuilt from authenticated NEIGHBOR1;
30. simulated insufficient disk/write interruption leaves no adopted partial sparse artifact and cleanup preserves protected generations.

### 7.7 Additional pass criteria

Append to Revision-7 criteria:

43. recovery-carrier blobs have an explicit P5A6/final-accepted provenance disposition; no unreviewed cross-generation hybrid is restored;
44. native worker preflight restores the final 393 baseline policy (`1.05`, `0.05`, logarithmic-plus-budget endpoint) or a separately measured same-semantics current retune with explicit evidence;
45. the optimized MVSEL engine constructs the complete `TargetTrainingOrder` through `|P_train|`, including the post-final-repair suffix, with no UID/scalar-only/historical-Nmax completion path;
46. full-order suffix restart/recovery is authenticated and exact;
47. every prefix-dependent selector cache/frontier/checkpoint/history/journal is invalidated or rebuilt correctly after repair divergence, while zero-swap state remains reusable when identity-valid;
48. MVQUAL progressive state evolves rungs serially within each family and parallelizes only independent state owners;
49. NEIGHBOR1/MVIDX OOC restoration preserves bounded anonymous RAM, O(1)-in-family-count mapped file descriptors, packed shared storage roots or an equal-or-stronger current representation, and fast incompatible-cache rebuild semantics;
50. OOC disk/scratch admission, write-failure handling and transactional publication prevent partial selector state from becoming current;
51. PEM/HAS closure uses the exact accepted project state/current PEM publication defined in Section 6 and is refreshed if that basis advances materially;
52. representative assembled performance evidence covers the complete current preparation/order/publication/reload path rather than configured-rung-only timing.

---

## 8. Revision-8 implementation start instruction

Implementation still begins at **R1 D1/D2 reconstruction/falsification/human ratification**, followed by R2 exact semantic + performance + provenance dependency recovery.

Do not begin by bulk-copying the 393 tree. R2 first identifies the final accepted source generation for every capability, including final native-preflight and OOC/FD hardening. Then restore/rebind only the smallest coherent dependency closure beneath current owners.

The current UID-capable target-order method remains under **SERIOUS CHALLENGE** until accepted D1/D2 restoration and complete executable qualification close. Revision-8 workplan review may pass the plan; it does not self-ratify the restored method or implementation.