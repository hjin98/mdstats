---
kind: independent-D3-review-reopen
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R3
protocol_version: 6.3.0
reviewed_candidate_commit: e24aef905fc09ccfc6c9d148b839bada28310200
reviewed_contract: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF.md
verdict: NO-PASS
serious_challenge: false
r1_authority_reopened: false
r2_reopened: false
d4_authorized: false
---

# Independent Protocol-6.3 D3 review — R3 reopen

## 1. Verdict

**NO-PASS.** The proposed R3 architecture is directionally consistent with the accepted scoped D1/D2 method and preserves the major current owners, but four material D3 defects remain before D4 implementation can be authorized.

There is **no Serious Challenge** to accepted R1 D1/D2 authority. The defects are downstream architecture/integration defects: shared-computation ownership, canonical obligation dependency flow, pre-adoption restart ownership, and canonical D3 authority promotion.

R1 remains **PASS / ACCEPTED / COMPLETE**. R2 remains **PASS / CLOSED**. Product source must remain unchanged until a repaired R3 receives fresh independent D3 review and the accepted D3 is promoted into the canonical Architecture Manual.

## 2. Review basis

Reviewed independently against:

- accepted D1: `docs/methods/mlff_target_training_order_scientific_method.md`;
- accepted D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`;
- composed workplan Revisions 5, 6, 7, and 8;
- closed R2 dependency/provenance map;
- current D3 Architecture Manual under `docs/arch_manuals/mlff_training_data/` plus `docs/arch_manuals/mlff_training_data_architecture.md`;
- current prepare/prepared-generation owners at accepted basis `e72090e21cec5311ce87745b03603f8783cd15a7`;
- mature recovery carrier `3937881ef00222e80845aa81f5471d89a4a7736c`;
- accepted PEM basis `hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md` with accepted project-state basis `e72090e...`.

The review does not inherit the authoring conclusion of the R3 handoff.

## 3. What passed

The following architecture choices are sound and should be retained during repair:

1. exactly one current `P_train`, one complete `TargetTrainingOrder`, and exact nested `T_N=pi_train[:N]`;
2. `prepare` remains the only live-input/build/publication orchestration path;
3. CampaignStore/prepared-generation ownership remains the only completed-generation currentness/adoption authority;
4. `TargetCoverageReference` is the sole selector-specific fitted numerical owner;
5. MVSEL2/REPAIR2 construct the order while P2 remains the public target-size policy/projection owner;
6. MVQUAL remains membership admissibility only and cannot rank target sizes;
7. current P3, `pi_eval/M1/M2/M3`, post-selection CV, replay, and production remain unchanged downstream owners;
8. old UID-capable prepared generations are stale/reconstructible under a new method identity rather than migrated;
9. OOC sparse storage, O(1)-in-family-count mapped descriptors, certified-lazy MVSEL2, native row scoring, current resource scope, repair invalidation, and complete-order suffix are correctly recognized as required capability transfer rather than optional optimization;
10. final production-scale GPU qualification remains deferred to the final release package.

## 4. Blocking finding D3-B1 — FEAS1/NEIGHBOR1/MVIDX1 dependency graph loses the mature shared-neighborhood owner

### Evidence

R3 currently draws two independent branches from `TargetCoverageReference`:

```text
TargetCoverageReference -> FEAS1
TargetCoverageReference -> NEIGHBOR1 -> MVIDX1
```

and its D4 sequence places `TargetCoverageReference + FEAS1` before `NEIGHBOR1/MVIDX1`.

That is not the mature recovered execution topology. At recovery snapshot `3937881...`, `target_coverage_exact_neighborhood.py` explicitly defines NEIGHBOR1 as the **shared exact TARGET-DATA2B/C neighborhood engine**. More decisively, `target_coverage_feasibility.py::build_target_coverage_feasibility_artifacts(...)` builds FEAS1 **and** the exact NEIGHBOR1 forward-CSR artifact in the same exact pass and returns:

```text
(TargetCoverageFeasibilityReport, TargetCoverageExactNeighborhoodStore)
```

MVIDX then adopts that authenticated exact neighborhood store instead of recomputing geometry when lineage matches. Revision 7 requires this reuse; Revision 8 preserves the final packed/OOC lineage.

### Why blocking

If the proposed D3 graph is implemented literally, FEAS1 can construct its own exact neighborhoods and MVIDX can construct NEIGHBOR1 again. That preserves science but duplicates the dominant geometry work, loses the accepted capability-transfer invariant, and creates two construction paths for one exact sparse relation. This is an architectural ownership/performance defect, not a D4 micro-optimization.

### Required repair

R3 shall define **one shared NEIGHBOR1 scientific relation/build product** for the selector generation. The architecture may realize it as the mature integrated FEAS1+NEIGHBOR1 builder or an exact-equivalent current owner, but the dependency must be unambiguous:

```text
TargetCoverageReference
        |
        v
one exact NEIGHBOR1 construction
        |\
        | +--> FEAS1 reduction/diagnostics
        |
        +----> MVIDX1 adoption/inversion/indexing
```

or an equivalent integrated build whose output exposes both FEAS1 and the one authenticated NEIGHBOR1 store. MVIDX cache miss may build NEIGHBOR1 only when that exact shared artifact is genuinely absent; the normal prepared path must not query the same geometry twice.

The D4 sequence must be changed accordingly: coverage reference -> canonical obligations -> **shared FEAS1/NEIGHBOR1 artifact construction** -> MVIDX adoption.

## 5. Blocking finding D3-B2 — canonical hard-obligation authority is not an explicit FEAS1 parent

### Evidence

Accepted D2 requires FEAS1 to operate over the same canonical obligation authority used by MVIDX/MVSEL2/REPAIR2/MVQUAL and to establish support-capacity infeasibility before selection.

R3 Section 4.2 correctly defines current canonical-locus composition, but ends by making MVIDX the incidence/count realization. R3 Section 4.3 then describes FEAS1 without routing that canonical obligation product into it, and the architecture diagram does not show the obligation authority at all.

The recovered FEAS1 hard lower-bound code is historical-topology-specific: it derives old strata, correlation intervals, and extent obligations. It cannot simply be copied and still account for current explicit P2 hard-support obligations, especially strengthened minima `k>1` and the accepted same-locus `max(k)` composition.

### Why blocking

Without an explicit shared parent, D4 has two bad choices:

1. duplicate canonical-obligation projection inside FEAS1, creating a second semantic owner; or
2. let FEAS1 ignore some current explicit/canonical minima, violating accepted D2 feasibility semantics.

Either breaks the one-authority rule.

### Required repair

R3 shall define one prepare-derived **canonical membership-obligation authority** (exact type/name remains D4-owned) after exact `P_train` and the required TargetCoverageReference-derived extent semantics are known. It must bind at least:

```text
canonical locus L(o)
exact P_train incidence A(o)
effective minimum k(o)
applicability/provider identity
source-alias/minimum provenance
governing P2 policy identity
```

Dependency must be explicit:

```text
current P2 explicit requirements + automatic accepted evidence + TargetCoverageReference extent semantics
 -> one canonical obligation authority
 -> FEAS1 support/capacity
 -> MVIDX sparse representation
 -> MVSEL2 / REPAIR2
 -> independent MVQUAL definition/count recomputation
 -> current P2 qualification projection
```

MVIDX owns an exact sparse representation of this authority, not the semantic definition itself. MVQUAL may consume the canonical definitions/identity but must independently recompute the selected-prefix evidence required by D2 rather than trusting selector counters.

## 6. Blocking finding D3-B3 — pre-adoption selector restart state lacks a durable owner/discovery contract

### Evidence

R3 requires MVSTATE2-equivalent checkpoint/restart and authenticated rank history, and it correctly states that CampaignStore owns only completed prepared-generation currentness. However it does not define who owns or how `prepare` safely discovers/reuses **expensive selector continuation produced before final prepared-generation adoption**.

The current prepared-generation owner publishes complete immutable components before CampaignStore CAS adoption. Before that adoption there is intentionally no current generation. A long MVSEL/NEIGHBOR/MVIDX preparation therefore needs a subordinate recovery contract that cannot be inferred from final-currentness semantics alone.

### Why blocking

Restart ownership is D3. Leaving this unspecified permits D4 to invent any of the failure modes Protocol 6.3 is meant to prevent: pathname-as-authority scratch reuse, a selector-specific mutable currentness registry, cross-attempt state adoption, or an unbounded journal. This is directly within PEM FF-002 and the Revision-7/8 restart-capability obligation.

### Required repair

R3 shall assign pre-adoption continuation to the existing **prepare/prepared-storage owner as reconstructible build-cache/checkpoint state**, not as a second current generation. The D3 contract must require:

- a deterministic prospective selector-build identity derived from exact scientific parents/policies;
- content/integrity authentication of MVSTATE/rank-history/checkpoint state before reuse;
- attempt/build ownership sufficient to prevent concurrent writers from cross-adopting mutable scratch;
- atomic checkpoint publication or an equivalent crash-safe boundary;
- stale/corrupt/incompatible checkpoint -> discard/rebuild or exact primitive reconstruction, never reinterpretation;
- bounded journal/history replay and retention;
- no downstream command discovers or consumes pre-adoption selector state;
- final prepared manifest references only completed authenticated final products; CampaignStore remains the sole completed-generation currentness owner;
- cleanup removes only build/attempt-owned state proven unreachable from protected prepared generations.

Do not add a selector-specific campaign-currentness database or compatibility router. Prefer content-addressed/digest-bound subordinate cache/checkpoint state under the existing prepared-storage lifecycle.

## 7. Blocking finding D3-B4 — canonical current D3 authority would remain contradictory when D4 is authorized

### Evidence

R3 says D4 becomes authorized after R3 PASS/acceptance, but the canonical current D3 Architecture Manual still describes the pre-restoration topology. Material examples include:

- `docs/arch_manuals/mlff_training_data_architecture.md` still names only the general D1/D2 papers in its authority chain and describes candidate-independent pre-order fitted evidence followed directly by one target-size generation containing `pi_train`;
- `30_statistical_design.md` allows DATA6/DATA7-style fitted transforms/metrics as pre-order fitted owners consumed by the order owner, while accepted R1 makes `TargetCoverageReference` the sole selector-specific fitted numerical owner and historical DATA7 fitted metric ownership non-current;
- `60_execution_performance.md` still states that the neutral statistical substrate supplies both canonical orders, which is false for restored `pi_train`;
- `80_ownership_and_decisions.md` still assigns pre-order fitted selection evidence to the DATA6/DATA7 family and does not name the restored coverage/NEIGHBOR/MVIDX/MVSEL/REPAIR/MVQUAL ownership chain.

Revision 5 currently defers D3 documentation reconciliation to R9, after executable restoration has begun.

### Why blocking

Under Protocol 6.3, a proposed workplan contract cannot silently outrank contradictory **current normative D3 architecture** while D4 implements against it. That would invert `D3 -> D4` authority and leave two recoverable architecture stories during implementation.

### Required repair

The repaired R3 must make canonical D3 promotion a **D3 gate action before D4 product mutation**, not an R9-only closeout chore.

After the repaired R3 passes independent re-review, promote the accepted design into the canonical D3 owners at minimum:

- `docs/arch_manuals/mlff_training_data_architecture.md`;
- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md`;
- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`.

Remove or reconcile stale target-order passages rather than adding a permanent amendment overlay. The canonical D3 must explicitly recognize the scoped accepted D1/D2 target-order papers. Only after that promotion is D4 implementation authorized.

R9 still owns final D4/spec/help/history/generated-document reconciliation, but not delayed establishment of the D3 architecture that D4 is supposed to concretize.

## 8. HAS / project-memory disposition

Using the Revision-8 PEM basis:

| ID | D3-review disposition | Reason |
| --- | --- | --- |
| SP-001 | APPLICABLE | repair must consolidate under existing prepare/P2/store owners, not add selector wrappers/currentness owners |
| SP-002 | APPLICABLE | reference/sparse/order/repair/qualification/checkpoint boundaries are identity-sensitive and fail closed |
| SP-003 | APPLICABLE | expensive selector products and continuation require immutable/content-authenticated reuse |
| SP-004 | APPLICABLE | final acceptance must exercise real prepare -> publish/adopt -> restart -> downstream consumption |
| FF-001 | NOT_APPLICABLE to the current target-size selector path | current P3 target-size candidate protocol authenticates replay/foundation mode as `none`; accepted D1/D2 foundation-residual families remain conditional/dormant unless a future target-size protocol explicitly activates a foundation provider |
| FF-002 | APPLICABLE | pre-adoption MVSTATE/history and post-repair continuation are material restart boundaries; D3-B3 closes the owner gap |
| FF-003 | NOT_APPLICABLE | repaired design stays under existing prepared/storage mutation ownership and creates no destructive selector GC |
| FF-004 | NOT_APPLICABLE to the current target-size selector path | current target-size selector does not require an accelerator-backed foundation provider; if a future accepted target-size method activates one, resource facts remain with its real provider/process owner and this disposition must be refreshed |
| FF-005 | APPLICABLE | downstream commands must consume the prepared P2 projection and never reconstruct selector science |

The current code evidence for FF-001/FF-004 applicability is `mdstats/training_data/target_size_execution/candidate.py` at `e72090e...`, which requires the target-size trajectory replay/foundation identity to be mode `none`. The conditional D1/D2 provider rule remains preserved for future accepted modes; it is not activated by the current target-size architecture.

No new PEM family or occurrence is warranted by this design review; these are candidate-plan defects caught before implementation, not accepted-code failure episodes.

## 9. Nonblocking clarifications to preserve during repair

These are not independent blockers once D3-B1..B4 are repaired:

1. Native/OpenMP retention still carries Revision-6 clean-build/install/package qualification. R3 should cross-reference it explicitly in its D4 acceptance list so the implementation handoff is snapshot-complete.
2. Manual `select-target-size N` should remain able to load the compact P2 experiment definition/order/qualification without mapping MVIDX/NEIGHBOR or restoring selector checkpoints.
3. Large TargetCoverage/NEIGHBOR/MVIDX arrays should remain typed/file-backed subordinate prepared artifacts rather than being forced into whole-object JSON merely because the current small prepared-component set is JSON-serialized.
4. Final production-scale GPU qualification remains deferred, but CPU/reference/native exactness and representative current-scale prepare performance are required before closeout.

## 10. Re-review acceptance criteria

A repaired R3 may PASS only when all of the following are explicit in the candidate itself:

1. one exact NEIGHBOR1 build is shared by FEAS1 and MVIDX on the normal prepared path;
2. one canonical obligation authority is an explicit parent of FEAS1, MVIDX, MVSEL2/REPAIR2, and independent MVQUAL semantics;
3. pre-adoption MVSTATE/history/checkpoint ownership, identity, concurrency, retention, and failure/recovery behavior are defined beneath existing prepare/prepared-storage ownership;
4. canonical D3 Architecture Manual promotion is required and sequenced before D4 mutation;
5. the repaired graph preserves one `P_train`, one order, current P2/public projection, current CampaignStore currentness, and unchanged P3/CV/replay/production;
6. Revision-5/6/7/8 performance, storage, packaging, oracle, and complete-order obligations remain binding without an unreviewed hybrid;
7. no new wrapper, alternate selector, selector currentness store, or semantic migration path is introduced.

After repair, perform a fresh independent D3 review. Do not treat this NO-PASS review as approval of the repaired text.