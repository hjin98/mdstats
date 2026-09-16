# Revision-8 independent workplan review — PASS

Date: 2026-09-15  
Canonical candidate under review: immutable Revision 5 + Revision 6 + Revision 7 + Revision 8  
Disposition: **PASS AS WORKPLAN**

## 1. Review question

Does the composed workplan now provide a snapshot-complete and internally coherent contract for restoring the latest mature `pi_train` multi-view selection path beneath the current one-`P_train` / P2 / prepared-generation architecture, including the final accepted optimization, parallelism, out-of-core, restart, full-order and evidence-lifecycle capabilities, without reviving rejected historical topology or silently selecting an earlier performance generation?

## 2. Governing-current-state check — PASS

Current `main` remains:

```text
e72090e21cec5311ce87745b03603f8783cd15a7
```

which is the workplan basis. No intervening accepted-main drift invalidates the ownership/currentness analysis.

The current `TargetTrainingOrder` remains a nonempty exact permutation owner and `candidate_membership(N)` is its exact prefix. Therefore full-order materialization through `|P_train|`, not only through the largest configured target-size rung, is a real current contract rather than an optional performance extension.

## 3. Recovery-generation provenance — PASS

Revision 8 correctly separates:

- the accessible coherent recovery carrier `3937881ef00222e80845aa81f5471d89a4a7736c`;
- the P6-recorded accepted P5A6 entry implementation identity `1670275487d29bbcde4c59efafdef9d1f8b0ced7` / tree `17e2c5609974712bda1efd3375f09f42da830f68`;
- later same-semantic accepted performance optimizations present in the recovery carrier;
- historical/reference-only and rejected generations.

R2 now requires a blob-level disposition instead of assuming every file at the recovery carrier has identical provenance. This prevents an accidental cross-generation hybrid while still permitting the latest mature accepted optimization to be reused.

## 4. Final native-preflight generation — PASS

The prior Revision-7 wording was materially stale: it privileged the earlier V5 1.75x activation threshold unless implementation later disproved it.

The exact final recovery-snapshot `mvsel2_native_preflight.py` instead defaults to:

```text
minimum_parallel_speedup = 1.05
economical_tolerance     = 0.05
```

with logarithmic worker probes plus the exact budget endpoint, deterministic real-MVIDX sampling, bitwise FP64 parity checks, and selection of the smallest width within the economical tolerance of the best measured parallel result.

Revision 8 now freezes this as the recovered baseline concretization while still allowing an explicitly measured same-semantics D4 retune. Earlier 1.75x evidence remains historical performance evidence, not a competing current default.

## 5. Complete-order performance closure — PASS

Revision 5 already defined the scientific full-order suffix correctly: after the final configured repair, rebuild state from the repaired prefix and continue the same MVSEL phase logic to `P_train` exhaustion.

Revision 8 closes the missing operational half:

- the optimized production engine, not a UID/scalar-only suffix, must run through the last `P_train` frame;
- configured-rung work and post-repair suffix work are measured separately;
- representative acceptance measures the complete order and full prepare critical path;
- when `|P_train| > Nmax_current`, at least one restart/resume acceptance point lies in the suffix beyond the configured ladder;
- MVQUAL remains configured-rung qualification and is not spuriously extended over a non-candidate suffix.

This aligns current full-permutation ownership with restored performance capability.

## 6. Post-REPAIR continuation state — PASS

Revision 8 explicitly extends Revision-5 post-repair invalidation to every performance state introduced by Revision 7:

- witness-term cache;
- lazy frontier/heap/exact-generation state;
- native candidate-score/preflight state when prefix-dependent;
- pure-selector MVSTATE checkpoint;
- rank-history/journal state when used for continuation authority;
- reconstructed plan-history caches tied to the old prefix.

After a repair swap, state and execution caches are rebuilt from the repaired prefix and primitive sparse authority; any new suffix journal/checkpoint binds repaired-prefix/repair-plan identity. A zero-swap repair does not force needless invalidation when exact prefix identity is unchanged.

The required warm-pre-repair-cache versus cold-repaired-prefix differential test is a discriminating oracle for this boundary.

## 7. MVQUAL progressive concurrency — PASS

The final recovered `mvqual_p2_runtime.py` carries witness multiplicity/sole-owner/unique-count state forward rung-by-rung within one family and parallelizes independent families.

Revision 8 now freezes that dependency DAG:

```text
within one progressive family: rung 1 -> rung 2 -> ... serially
across independent families/groups: bounded concurrency permitted
```

Canonical scientific reduction remains ordered after arbitrary task completion. This removes the Revision-7 ambiguity that could otherwise have been implemented as racing per-rung mutation of one progressive state.

## 8. NEIGHBOR1/MVIDX final OOC generation — PASS

Revision 8 recovers the performance/hardening generation that Revision 7 only summarized generically:

- aggregate finalized sparse payload can exceed RAM only because it is file-backed;
- finalization scratch remains bounded/admitted;
- packed shared sparse roots keep mapped file descriptors O(1) in family count;
- forward-only consumers map only needed candidate-oriented roots;
- constrained-`RLIMIT_NOFILE` acceptance protects the many-family path;
- obsolete per-family reconstructible MVIDX layouts fail early into rebuild rather than performing a huge sidecar walk and failing late;
- disk/scratch admission, write/ENOSPC failure and transactional handoff are explicit;
- concurrent/interrupted attempts cannot publish or adopt partial authority.

This is compatible with the existing prepared-generation/storage owner and introduces no selector-specific GC or second currentness owner.

## 9. PEM/HAS reproducibility — PASS

Revision 5's old locator was misleading because the PEM file at `4eabe2...` still described an earlier accepted base and an unresolved candidate notice.

The semantic PEM publication that advanced accepted memory basis to `4eabe2...` is:

```text
b5d101d8f73d3efd63ef4e70b3913e7d281406ce
```

and current accepted `main@e72090e...` carries exactly the same PEM blob (`67e3130d3703d9fc26ed0afe94fa2506a176e9ce`). The current workplan branch does not modify PEM.

Revision 8 therefore uses:

```yaml
accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
accepted_pem: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
candidate_overlay_semantic_candidate: NONE
```

while preserving the PEM's explicit `PARTIAL` coverage and supplementing it with direct selector/performance historical intake. This is a reproducible basis rather than an assertion that PEM covers the entire later project interval.

## 10. Resource/performance ownership — PASS

The composed plan still has one campaign CPU/nested-parallelism owner (`SystemResourceSnapshot` / `StageResourceScope`) and one restored shared bounded queue capability. Parallelism remains execution machinery subordinate to exact D2 ordering/reduction:

- family/block work for coverage/FEAS;
- independent sparse inversion/build work for MVIDX;
- independent candidate-row native/OpenMP scoring for MVSEL while selection/mutation stays canonical;
- immutable REPAIR proposal work after state-invariant factorization with serial winner/mutation;
- independent MVQUAL family/group state while progressive rungs stay serial within a family.

No stage is allowed to recreate fixed host-specific worker ceilings or an independent whole-machine scheduler.

## 11. Storage/currentness/restart ownership — PASS

The composed plan keeps completed scientific state under one immutable prepared generation and current CampaignStore/CAS adoption boundary. MVSTATE/journals, OOC build directories, native-meter state, caches and queue telemetry remain subordinate/reconstructible execution state.

The strengthened failure matrix now covers worker failure, cancellation, partial OOC writes, insufficient disk, stale CAS attempts, cache corruption, restart and descriptor pressure without permitting partial authority publication.

## 12. Evidence adequacy — PASS

The final evidence surface now distinguishes:

- independent bounded TargetCoverage and direct-neighborhood oracles;
- exact numerical/tolerance boundary fixtures;
- reference versus optimized selector/repair/MVQUAL equivalence;
- execution-degree determinism across workers/backends/chunks/queues/cache/restart;
- full-order suffix continuation and restart;
- real storage/OOC/FD/resource behavior;
- current representative complete-prepare performance;
- historical performance as comparator evidence rather than portable SLA;
- clean installed native-package qualification.

Historical expected outputs must retain independent/immutable provenance; candidate-self-generated goldens still cannot close equivalence.

## 13. Remaining historical mechanisms — no blocker

Revision 8 does not require blind restoration of every old file. The R2 capability/source census remains the proper place to decide `RESTORE_UNCHANGED`, `RESTORE_REBIND`, `MERGE_INTO_CURRENT_OWNER`, `REFERENCE_ONLY` or `DROP` for the complete dependency closure.

Known rejected paths remain explicitly outside current restoration: eager MVSEL1 inverse propagation, Python candidate-thread selector parallelism, G4c/G4d refault-regressive page release, MVQUAL P1 direct prepass, obsolete per-domain/currentness topology, fixed worker ceilings, approximate selection and GPU selector authority.

## 14. Challenge pass

No remaining plan-level Serious Challenge or blocking contradiction was found among:

- current D1/D2 amendment sequencing and human ratification;
- exact current `P_train` / P2 ownership;
- current configurable candidate ladder;
- complete `TargetTrainingOrder` ownership;
- restored multi-view selection/repair/qualification semantics;
- final optimized/parallel/OOC execution lineage;
- post-repair and full-suffix restart semantics;
- current prepared-generation/CampaignStore currentness;
- storage/resource/build/package ownership;
- deterministic execution equivalence;
- final-release-only production GPU qualification.

The current UID-capable product method itself remains under the already-recorded Serious Challenge until R1 D1/D2 restoration is independently accepted and human-ratified. Passing this workplan does not accept that future method or its implementation.

## 15. Final disposition

**PASS AS WORKPLAN.**

Revision 8 closes the remaining gaps found in the Revision-7 restoration contract. Implementation remains blocked on R1 exact D1/D2 reconstruction/falsification/human ratification, followed by R2 semantic + performance + provenance dependency recovery. Only then should D4 restoration begin.