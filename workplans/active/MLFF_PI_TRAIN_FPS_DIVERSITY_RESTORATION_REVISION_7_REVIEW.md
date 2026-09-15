# Revision-7 independent workplan review — PASS

Date: 2026-09-15
Canonical plan under review: immutable Revision 5 + immutable Revision 6 + Revision 7
Disposition: **PASS AS WORKPLAN**

## 1. Review question

Does the composed workplan now restore not only the latest mature MVSEL2 scientific selection/repair/qualification semantics, but also the current-compatible bounded-memory, restart, optimization and deterministic parallel execution capabilities that made the pre-P6 path production-usable, while keeping rejected experiments and obsolete target-size topology out?

## 2. Reopen result

The prior Revision-6 PASS was correctly reopened.

Revision 6 required correctness/reference/native packaging evidence but allowed an implementation to omit historically accepted optimized/parallel machinery if an exact fallback remained. That was insufficient for the stakeholder's restoration objective and for faithful mature-capability transfer.

Revision 7 closes that defect by making the accepted performance capabilities mandatory preservation targets unless an equal-or-stronger current owner already supplies them or a concrete current incompatibility is established.

## 3. Historical performance lineage — PASS

The review independently recovered the relevant mature lineage and found it materially consistent with Revision 7:

- `DOC-MVSEL2_forward_lazy_selector` replaced eager inverse propagation with exact forward state, certified lazy Phase B, MVSTATE2 and REPAIR2, with a major production-scaling gate;
- `DOC-MVSEL2-V5-REDESIGN1` retained Python scientific authority while moving only independent family-row scoring to a bitwise-qualified private C/OpenMP primitive; its real-MVIDX preflight selected parallel execution only when measured speedup justified it;
- `DOC-REPAIR2-PERF1` identified repeated state-invariant proposal work as the bottleneck and optimized that before adding parallelism;
- `DOC-MVQUAL-MEM1-PERF1` accepted bounded sparse and progressive nested-rung MVQUAL while explicitly rejecting a theoretically attractive direct-prepass variant that worsened the product critical path;
- `PAR90_FULL_PARALLELIZATION_WORKPLAN` established one affinity/cgroup-aware campaign CPU budget, explicit native/OpenMP accounting, full-budget MVSEL2, deterministic REPAIR proposal parallelism and removal of fixed worker ceilings;
- `TARGET_SIZE_V5_PERFORMANCE_PRESERVATION_WORKPLAN` restored MVSTATE2-to-REPAIR2 pre-divergence checkpoint reuse and one campaign resource authority;
- `DOC-MVSEL2_HARDEN1_V3` retained real product-path qualification and explicitly retired qualification-only reconstruction/harness machinery.

P6 implementation evidence independently confirms that the selector generation deletion removed the native kernel, sparse kernels, work queue, TargetCoverage/MVIDX machinery, optimized MVSEL2 kernels/runtimes, repair checkpoint runtime and MVQUAL runtime in the same destructive cutover. There is no evidence that those accepted performance capabilities failed and thereby justified their semantic omission.

## 4. Current common-owner reconciliation — PASS

Current main still retains `SystemResourceSnapshot` / `StageResourceScope`, including affinity/cgroup-aware capacity, RAM budget and explicit native/OpenMP width. It no longer contains `work_queue.py`.

Revision 7 therefore chooses the minimum coherent architecture:

```text
current resource owner
 + restored deterministic bounded work-queue capability
 + restored selector-specific optimized kernels/pipelines
```

rather than reinstating a competing historical resource planner or creating a new scheduler.

The package-wide native extension registry also survives P6 but currently contains no extension and explicitly documents that MVSEL2 was removed. Revision 7 correctly routes `_mvsel2_native` restoration through this existing registry instead of one-off build machinery.

## 5. Parallel-boundary correctness — PASS

Revision 7 keeps authoritative mutation/reduction boundaries explicit:

- TargetCoverage/FEAS: independent family/block work may parallelize; canonical scientific reduction remains deterministic;
- MVIDX: exact independent family/block query/inversion work may parallelize; scientific sparse content/order remains canonical;
- MVSEL2 Phase A: read-only family/candidate scoring may vectorize/native-parallelize, while staged lexicographic filtering and accepted rank mutation remain canonical;
- MVSEL2 Phase B: independent candidate-row scoring may use native/OpenMP, while lazy certification, canonical family accumulation, contender/tie logic and mutation remain serial scientific authority;
- REPAIR2: immutable proposal scoring may run concurrently after state-invariant factorization; canonical proposal assembly, winner comparison and accepted mutation remain serial;
- MVQUAL: independent family/rung work may execute concurrently; persisted scientific records and reductions remain canonical.

This architecture preserves D2 while making parallelism D3/D4 execution machinery rather than a second numerical authority.

## 6. Resource-budget / oversubscription closure — PASS

Revision 7 preserves one runtime budget:

```text
B_cpu = max(1, floor(cpu_fraction * N_available))
```

with current configuration owning `cpu_fraction` and `0.90` remaining the historical/default production value.

Explicit stage widths are caps inside that budget. Python/tree/BLAS/native/OpenMP/PyTorch nesting is represented by the existing `StageResourceScope`; broad outer work normally uses inner native width one, while an MVSEL native kernel may consume the native width directly as the sole active parallel layer.

The plan explicitly rejects the historical execution defects that PAR90 removed: fixed 4/8/16/28 capacity ceilings, unrelated reuse of cKDTree worker policy and sibling pools each independently claiming 90% of the host.

## 7. MVSEL2 final production generation — PASS

Revision 7 does not stop at the scalar reference selector. It requires:

- one fresh/resumed production rank loop;
- locality-oriented Phase-A implementation;
- cached-witness Phase-B implementation;
- certified lazy frontier and memory-bounded family-major rebase;
- bitwise-qualified private native/OpenMP row scorer where current packaging/platform permits it;
- dynamic real-MVIDX preflight and exact Python/NumPy fallback;
- MVSTATE2 plus authenticated rank-history resume.

It also explicitly keeps the failed Python candidate-thread PAR1 path and G4c/G4d mmap release/refault policies retired.

The historical V5 evidence is material: 8-worker real-MVIDX preflight measured 2.59x primitive speedup, and the accepted product continuation reached 16,384 at 37.996 ranks/s with complete MVSEL2 stage acceptance around 10 minutes. Revision 7 appropriately uses this as bounded historical comparator evidence rather than blindly declaring it a hardware-independent SLA.

## 8. REPAIR2 final execution generation — PASS

Revision 7 correctly preserves the optimization ordering learned historically:

1. remove repeated state-invariant proposal-frontier work;
2. keep the factorized context execution-only and invalidate it at authoritative mutation;
3. parallelize independent immutable proposal evaluation through the shared queue;
4. keep canonical serial winner/mutation authority;
5. reuse authenticated MVSTATE2 before repair divergence only, without skipping the active shell;
6. stop restoring pure-selector checkpoints after the first accepted repair swap.

This avoids the common mistake of trying to solve an algorithmic amplification defect by merely adding threads.

## 9. MVQUAL final execution generation — PASS

Revision 7 restores the accepted bounded exact path and the accepted progressive nested-prefix optimization:

- bounded canonical CSR streaming;
- exact witness-state ownership/multiplicity;
- canonical full-witness FP64 reductions at every rung;
- progressive processing of only newly added rows for nested ladders;
- deterministic family/rung concurrency under one resource budget;
- exact bounded fallback for nonnested/incompatible groups.

It explicitly keeps the rejected P1 direct TargetCoverage prepass retired, preserving the evidence-backed lesson that reducing isolated work can lengthen the total critical path.

## 10. MVIDX / coverage preparation — PASS

The plan now requires exact optimized coverage/FEAS/NEIGHBOR/MVIDX restoration, including authenticated cache/reuse, deterministic sparse inversion, OOC/file-backed arrays, bounded queues/backpressure and actual RAM admission rather than a fixed lane count.

This composes correctly with Revision 6's independent TargetCoverageReference and direct MVIDX adjacency oracles, preventing optimized construction and downstream consumers from sharing an undetected common-mode error.

## 11. Determinism and failure-path evidence — PASS

The required matrix varies worker width, budget endpoint, batch/chunk size, file-backed reload, queue completion order/depth, native/reference backend, cache state and restart state while holding scientific input fixed.

The expected equality surface spans reference, MVIDX, FEAS, complete MVSEL order, REPAIR swap trace/order, MVQUAL result and current P2/prepared identities.

Revision 7 also adds worker-failure, cancellation, partial OOC build, native-qualification failure, stale-CAS build, restart and resource-teardown cases. Parallel execution therefore cannot manufacture partially current scientific state.

## 12. Performance evidence strength — PASS

The workplan correctly separates:

- immutable historical evidence demonstrating the mature path's capability;
- current representative-scale evidence required for the rebound pipeline;
- exact semantic/reference equivalence;
- hardware-dependent effective-width tuning.

Historical timings are comparators/priors, not portable SLAs. A large unexplained regression on a comparable workload is nevertheless a blocker requiring recovery of missing mature optimization or a measured D3/D4 redesign; it cannot be dismissed because a serial reference is scientifically correct.

Qualification is routed through the real current prepare/product path rather than resurrecting the later-retired qualification-only reconstruction harness.

## 13. Source-closure completeness — PASS WITH IMPLEMENTATION OBLIGATION

Revision 7's R2 list is expressly a minimum list inside a requirement to recover the **complete optimization dependency closure**. Therefore additionally discovered recovery-snapshot surfaces such as `_target_multi_view_scoring`, `mvsel2_v5_runtime` or late hardening helpers are automatically in scope when the import/call/dependency census shows that they participate in a required capability.

This is not an open plan gap: R2 already forbids treating the enumerated filename list as exhaustive and requires blob-level classification of the complete closure. The final source census must make these dispositions explicit before implementation proceeds past R2.

## 14. Challenge pass

No remaining plan-level Serious Challenge was found.

No incompatibility was found among:

- exact restored multi-view science;
- one current `P_train` and one `TargetTrainingOrder`;
- current configurable candidate ladder;
- current P2/EVAL2/P5 ownership;
- restored exact optimized/parallel selector chain;
- current prepared-generation/CampaignStore currentness;
- current storage/resource owners;
- deterministic/restart equivalence;
- final-release-only GPU qualification.

The product's current UID-capable method remains under the existing Serious Challenge; this workplan PASS does not ratify the proposed D1/D2 restoration or claim implementation acceptance.

## 15. Final disposition

**PASS AS WORKPLAN.**

Revision 7 closes the performance-capability transfer defect that reopened Revision 6. The plan now requires restoration/rebinding of the final accepted current-compatible optimization and deterministic parallelization machinery surrounding TargetCoverage/FEAS, NEIGHBOR/MVIDX, MVSEL2/MVSTATE2, REPAIR2 and MVQUAL, while explicitly excluding historically rejected execution experiments and obsolete target-size topology.

Implementation must still begin at R1 D1/D2 reconstruction/independent falsification/human ratification, then perform the R2 exact semantic + performance dependency census before restoring production code.