# Part IV-B - Target-training-order architecture

## Purpose and authority

This chapter is the canonical D3 owner for the software architecture that realizes the accepted current `TargetTrainingOrder` / `pi_train` method.

Its upstream scoped method owners are:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`;
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

Those scoped papers supersede conflicting target-order statements in the general MLFF method papers while leaving unrelated MLFF method authority unchanged. This chapter owns component/state/interface ownership, dependency direction, persistence/restart, resource topology, currentness integration, and the D3-to-D4 boundary. It does not redefine D1/D2 numerical semantics.

## Current architecture

The one current target-order chain is:

```text
resolved target-size policy
        |
        v
U_size -> exact P_train + M3
        |
        v
prepare selector inputs on exact P_train
        |
        v
sole fitted TargetCoverageReference
        |
        +-----------------------------+
        |                             |
        |                    current P2 explicit support policy
        |                             |
        |     accepted automatic condition/event/profile/correlation/extent evidence
        |                             |
        +-------------+---------------+
                      |
                      v
       one canonical membership-obligation authority
          [L(o), A(o), k(o), applicability, provenance]
                      |
                      +-------------------------------+
                      |                               |
                      v                               |
      one shared exact NEIGHBOR1 construction         |
                      |                               |
              +-------+-------+                       |
              |               |                       |
              v               v                       |
        FEAS1 reduction    authenticated               |
        /capacity report   NEIGHBOR1 store             |
                              |                        |
                              v                        |
                         MVIDX1 adoption <-------------+
                              |
                              v
                    MVSEL2 / MVSTATE2
                              |
                      configured REPAIR2
                              |
                    exact state reconstruction
                              |
                              v
                    complete TargetTrainingOrder
                              |
                +-------------+-------------+
                |                           |
                v                           v
        exact T_N prefixes            independent MVQUAL
                                from TargetCoverageReference
                                + canonical obligation definitions
                                (+ MVIDX only as exact cross-check)
                |                           |
                +-------------+-------------+
                              |
                              v
                     current P2 projection
                              |
                              v
                   unchanged P3/CV/production
```

The architecture has one `P_train`, one complete `pi_train`, and exact nested `T_N = pi_train[:N]`. Historical label-domain/fold selector fan-out, fixed `128..16384` target-size authority, per-size membership selectors, UID/condition-round-robin suffix completion, and alternate MVSEL generations are not current architecture.

## Durable ownership

1. `prepare` is the only live-input/build/publication orchestration owner for selector construction.
2. Current prepared-generation storage plus `CampaignStore` is the sole completed-generation publication/currentness/adoption architecture.
3. P2 owns the configured target-size policy, exact `P_train/M3` split, explicit hard-support inputs, and the public order/qualification projection.
4. `TargetCoverageReference` is the sole selector-specific fitted numerical product. DATA6/DATA7 may supply authenticated raw/lineage/provider inputs but do not own a competing fitted selector reference.
5. The canonical membership-obligation authority is constructed once from accepted automatic evidence plus current explicit P2 requirements. It binds canonical locus, exact `P_train` incidence, effective minimum, applicability/provider identity, and source provenance. FEAS1, MVIDX, MVSEL2, REPAIR2, and MVQUAL may consume or represent it but may not redefine it.
6. NEIGHBOR1 owns one exact candidate-witness neighborhood relation/build product for a selector generation.
7. MVIDX owns exact sparse forward/inverse representation of NEIGHBOR1 plus canonical-obligation incidence and current correlation-unit codes. It is representation, not a second semantic owner.
8. MVSEL2/REPAIR2 own construction of the one complete target-training order. They do not own candidate-size policy or target-size model-outcome ranking.
9. MVQUAL owns independent configured-prefix membership admissibility evidence only. It does not rank target sizes and may not trust selector/repair counters as its sole oracle.
10. P3 training/evaluation/reducer, `pi_eval/M1/M2/M3`, post-selection CV/replay, and production remain unchanged downstream owners.

## Shared FEAS1/NEIGHBOR1 boundary

The normal prepared path performs the exact neighborhood geometry once. The shared construction exposes both the FEAS1 reduction/capacity product and one authenticated NEIGHBOR1 store. MVIDX adopts/inverts that store when lineage matches rather than querying the same exact geometry again.

A NEIGHBOR1 rebuild is allowed only when the required authenticated relation is absent, corrupt, incompatible, or intentionally invalidated as reconstructible state. Obligation-policy changes do not by themselves change NEIGHBOR scientific identity when its true reference/geometry parents remain unchanged; FEAS obligation-capacity reduction and MVIDX obligation incidence are separate consumers of the canonical obligation authority.

FEAS1 is fail-closed diagnostic/capacity architecture. It cannot mutate target sizes, thresholds, obligation minima, or create rescue candidates.

## Selector, repair, and qualification integration

The product architecture retains one scalar/full-forward exact oracle and one optimized certified-lazy production realization of the same D2 selector. Native/vector kernels are execution primitives only and cannot acquire ordering authority.

At configured shells, REPAIR2 may alter only the active shell under accepted D2 semantics. After an accepted repair swap, every prefix-dependent continuation cache/frontier/checkpoint/history object whose ancestry precedes the repaired prefix is invalid for scientific continuation. Exact selector state is reconstructed from authenticated primitive sparse authority and the repaired prefix before continuation.

After the final configured shell, the same optimized exact selector continues until all of `P_train` is ordered. There is no alternate or UID suffix.

MVQUAL independently recomputes configured-prefix coverage/extents and canonical-obligation satisfaction from immutable primitive definitions. MVIDX may be an exact secondary cross-check only.

## Prepared-generation identity and cutover

The completed target-order generation binds every scientific parent that can change the order or qualification, including the exact split/`P_train`, selector-input/provider identities, `TargetCoverageReference`, canonical obligations, scientific NEIGHBOR/MVIDX identity, MVSEL2 method version, configured repair-shell policy/repair ancestry, complete final order, and MVQUAL evidence.

Execution-only worker widths, queue timing, cache residence, mmap paths, scratch locations, and native preflight timing do not enter scientific identity.

A restored multi-view order uses a new semantically versioned target-order policy/schema identity. Existing `candidate_independent_priority.v1` generations are stale/reconstructible under that cutover and rebuild through normal `prepare` ownership. Old ranks are not migrated, and no compatibility selector or hidden fallback may remain current after cutover.

## Pre-adoption restart ownership

Expensive selector continuation produced before a completed prepared generation is adopted belongs to the existing `prepare` / prepared-storage lifecycle as reconstructible build-cache/checkpoint state. It is not a `CampaignStore` generation, public order, or second currentness mechanism.

Reusable checkpoint/history state requires a deterministic prospective build identity that covers the scientific parents relevant to the checkpoint level, content/schema integrity, exact prefix identity, and repair ancestry. Mutable scratch is attempt-owned. Concurrent attempts may target the same prospective build identity but may not share mutable scratch or cross-adopt another attempt's unfinished state.

Reusable checkpoint publication is crash-safe and authenticated. File/path existence alone is never validity evidence. Stale, corrupt, incompatible, or foreign-attempt state is discarded or reconstructed exactly from primitive authority. Rank journals/history remain bounded; pre-repair continuation history becomes diagnostic-only after repair divergence. Downstream selection/CV/production never discover or consume pre-adoption selector state.

The final prepared manifest references only completed authenticated prepared products. `CampaignStore` remains the sole owner that makes a completed generation current. Cleanup remains under existing prepared/storage ownership and may remove only attempt/build-owned or unreachable reconstructible state after protected references are checked. No selector-specific currentness database or GC is introduced.

## Resource and persistence architecture

NEIGHBOR1/MVIDX preserve the mature sparse/OOC capability envelope or an equal-or-stronger exact representation:

- file-backed/OOC construction for large sparse payloads;
- bounded anonymous working/finalization memory;
- packed/shared durable roots with mapped file-descriptor count O(1) in family count;
- forward-only restore where selector consumers do not need witness-oriented roots;
- early rejection/rebuild of obsolete reconstructible per-family persistence;
- explicit disk/scratch/write-amplification and descriptor/inode admission where material;
- transactional publication so ENOSPC/write interruption cannot expose partial accepted selector artifacts;
- attempt-owned cleanup that cannot delete protected/current/restartable products.

CPU lanes come from the current stage/resource owner. The mature deterministic bounded queue and qualified native candidate-row backend may be restored beneath that owner, but scientific commit/reduction order remains canonical. If the native/OpenMP backend is retained, clean source/editable/wheel install and installed-package native/reference exact-equivalence qualification are part of D4 acceptance.

The current target-order path does not require a GPU. Production-scale GPU qualification for the overall MLFF release remains deferred to the final release package on the stakeholder machine.

## Downstream integration

A normal `prepare` invocation builds or reuses the selector products and publishes the compact P2/public definition required by downstream commands. Manual `select-target-size N` loads the prepared P2 order/qualification evidence it needs and must not map NEIGHBOR/MVIDX or restore selector checkpoints. Automatic diagnostic selection consumes the same prepared P2 definition and performs only its P3 screen/reducer work. Post-selection CV/replay/production consume frozen memberships and never reconstruct target-order science.

Target-size candidate outcome, M3, CV, replay, production, and qualification evidence have no reverse edge into target-order membership.

## D4 acceptance boundary

D4 may choose exact class/module names, serialization fields, checkpoint file layout, worker implementation, and policy-token spelling, provided the ownership/dependency relations above remain true.

Implementation acceptance must falsify at least:

- one shared normal-path neighborhood construction rather than FEAS/MVIDX duplicate geometry;
- canonical-obligation alias/max-min and strengthened-minimum behavior;
- direct/reference adjacency and coverage equality;
- full-forward versus optimized rank equality at every bounded fixture rank;
- repair trace, lower-prefix immutability, post-repair cold reconstruction, and complete suffix behavior;
- independent MVQUAL equality/monotonicity;
- old-generation staleness and fresh-process no-scientific-rebuild behavior;
- concurrent-attempt isolation and authenticated checkpoint rejection/recovery;
- bounded journal replay;
- OOC RAM/disk failure and constrained-FD behavior;
- native/reference installed-package equivalence where native execution is retained;
- representative current-scale wall/RSS/I/O, edges/rank, lazy-refresh, repair-reconstruction, suffix, and restart cost.

A material performance defect first requires proving that the accepted optimized execution closure is active. Performance pressure cannot weaken D1/D2 membership semantics.

## Reopen conditions

Reopen D3 if implementation evidence shows that simultaneous accepted ownership/currentness/restart/resource constraints cannot be realized without a materially different component or persistence topology, or if representative current-envelope scaling requires a different architecture. Reopen D2/D1 only for an actual numerical/scientific contradiction rather than implementation inconvenience.
