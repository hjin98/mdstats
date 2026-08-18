# MLFF Scaling Audit, Revision 2

Date: 2026-08-05  
Package: `mdstats 0.20.63a0`  
Scope: `mdstats.training_data`, campaign CLI, DATA2–DATA9B preparation, model sweep, selection, materialization, evaluation, and restart paths.

## Executive result

The interrupted-run stall was traced to an omitted quadratic property in the DATA6 model-sweep checkpoint:

```python
return tuple(
    uid for uid in self.requested_frame_uids
    if uid not in set(self.completed_frame_uids)
)
```

`set(self.completed_frame_uids)` was reconstructed once for every requested frame.  For `N` requested frames and `C = O(N)` completed frames, the property cost was `O(N C) = O(N^2)`.  It was called by restart/progress/finalization logic, so an interrupted 36,759-frame campaign could appear to hang before useful work resumed.

The checkpoint now constructs immutable completed/pending indexes once in `__post_init__`.  Construction is `O(N)` and each subsequent `pending_frame_uids` query is `O(1)`.

A full branch-wide scan then identified and corrected the additional scaling defects below.  After these changes, no unbounded all-frame `O(N^2)` or worse computation remains in the normal production DATA2–DATA8 path when atom count, fold count, profile count, and maximum selection ladder are fixed.

## Corrected poor-scaling paths

| Area | Former behavior | Former cost | Replacement | New cost |
|---|---|---:|---|---:|
| DATA6 interrupted resume | Rebuilt `set(completed)` inside the per-requested-frame membership test | `O(N^2)` | Cache completed and pending UID tuples/sets once | `O(N)` construction, `O(1)` query |
| Local campaign scheduler | `list.pop(0)` shifted all remaining jobs for every launch | `O(J^2)` | `collections.deque.popleft()` | `O(J)` |
| Label-domain grouping | Compared each source fingerprint with every member of every existing group | worst-case `O(S^2 P)` | Compatibility-key buckets plus aggregate PAW-conflict bitsets, preserving earliest-compatible-group semantics | approximately `O(S P)` |
| Strained reference discovery | Every strained source reparsed/compared every potential reference | `O(R^2)` plus repeated metadata work | One normalized identity/composition index | `O(R + matches)` |
| Reference-cell constancy | Rescanned a reference trajectory for every strained sibling | `O(S N_ref)` | Evaluate constancy once per run | `O(N_ref + S)` |
| Event-to-interval association | Rebuilt frame sets and compared every event with every interval | up to `O(I E F)` | Frame UID → event-ordinal index | `O(actual event memberships)` |
| Temporal purging/leakage audits | Regrouped/sorted all units and scanned all units for every fold/query | repeated `O(F U log U)` and `O(F U)` | Reusable run-local temporal index | one `O(U log U)` build plus `O(anchor × radius)` queries |
| Label/domain/catalog lookup | Reconstructed dictionaries or linearly scanned domains/units/frames per lookup | multiplicative `O(DN)`/`O(UN)` patterns | Immutable keyed indexes on catalog construction | `O(N)` construction, average `O(1)` lookup |
| DATA6 model-evidence domains | Scanned all candidate frames independently for each domain | `O(DN)` orchestration | One frame-membership/index pass | `O(N + memberships)` |
| Duplicate restart detection | Cartesian product of first/final duplicate-run sets | `O(R^2)` | Set-union predicate | `O(R)` |
| Species support | Reconstructed species sets from every frame | `O(NA)` Python work | One atomic-number scan per trajectory run | `O(RA)` |
| DATA7 selected-neighbor coverage | Rebuilt each full `K_l × K_l` pair matrix at every ladder level | `O(sum K_l^2 d)` | Incrementally extend one `K_max × K_max` matrix | `O(K_max^2 d)` |
| DATA7 representative prefix | Full lexicographic sort of every condition group to retain at most `K` rows | `O(N log N)` | Exact partitioned prefix plus deterministic tie handling | expected `O(N + K log K)` |
| DATA7 FPS | Recomputed all candidate-to-all-selected distances and built a complete ordering | effective `O(N^3 d)` | Incremental nearest-distance update, bounded to `K_max` | `O(N K_max d)` |
| DATA7 feature assembly | Per-frame arrays followed by `vstack`, then block outputs followed by `column_stack` | linear but 2–3× peak-memory amplification | Preallocated matrices, direct columnar extraction, write blocks directly to final matrix | `O(Nd)` with bounded extra memory |
| Atomic-reference fit | Built Python row lists before converting to arrays | linear object amplification | Preallocated count/target arrays | `O(NE)` with lower constants |
| Checkpoint evaluation metrics | Retained and concatenated all force/stress error arrays | `O(total components)` memory plus final copy | Streaming sums of squared errors and counts | `O(groups)` memory |
| Cryptographic verification | Independently reread unchanged large files in many modules and once per checkpoint | repeated full-file I/O | Process-local cache keyed by resolved path, device, inode, size, mtime, and ctime; post-hash stat verification | one full read per unchanged file identity |
| Content digests | Rebuilt large nested payloads and recursively sorted keys repeatedly | repeated linear/log-linear object work | Cached scientific digests and single canonical mapping order | one computation per immutable record |

## Quantitative microbenchmarks

The benchmark is deterministic and measures bookkeeping/selection kernels, not MACE inference.

### Interrupted DATA6 pending-frame query

| Frames | Former | Current | Speedup |
|---:|---:|---:|---:|
| 500 | 0.00124 s | 0.0000144 s | 86× |
| 4,000 | 0.100 s | 0.000114 s | 882× |
| 8,000 | 0.326 s | 0.000245 s | 1,330× |
| 16,000 | 1.69 s | 0.000603 s | 2,804× |

The former curve is quadratic.  Extrapolation explains the severe restart/finalization delay at 36,759 requested frames.

### Local pending-job queue

| Jobs | `list.pop(0)` | `deque.popleft()` | Speedup |
|---:|---:|---:|---:|
| 1,000 | 0.000084 s | 0.000038 s | 2.2× |
| 4,000 | 0.000800 s | 0.000160 s | 5.0× |
| 16,000 | 0.0129 s | 0.000634 s | 20.4× |

### DATA7 bounded operations

- Exact 512-of-36,759 centroid-prefix selection: 0.0194 s → 0.00444 s, 4.37×.
- Incremental selected-neighbor matrix at `K_max=512`: 0.00195 s → 0.00112 s, 1.73×.
- Earlier bounded FPS benchmark: 36,759 candidates, 24 dimensions, 512 selected in approximately 0.5 s.

## Static and call-path audit method

The audit combined:

1. call-path inspection from campaign CLI through DATA2–DATA9B;
2. AST screening for nested loops, comprehensions inside loops, repeated container construction, front-removal queues, repeated sorting, pairwise matrices, and linear catalog lookup;
3. targeted searches for `.index`, `pop(0)`, `in set(...)`, `vstack`, `column_stack`, `X @ X.T`, and local SHA-256 implementations;
4. exact numerical/prefix-equivalence tests for selection and structural paths;
5. deterministic synthetic scaling benchmarks;
6. focused campaign, persistence, restart, and production-materialization regression tests.

## Remaining scaling terms

The following costs remain intentionally or because they are bounded by small dimensions:

- **Universal structural geometry:** `O(N A^2)` for exact all-pair periodic features.  It is linear in frame count and quadratic in atoms per frame.  A sparse cutoff would change the frozen scientific feature definition unless introduced as a new declared policy.
- **MACE inference:** graph construction and message passing scale with atoms/edges and model depth.  DATA6 uses batching, adaptive memory limits, and a combined descriptor/prediction forward where compatible.
- **Bounded selection:** `O(N K d)` with `K` normally 512.  This is linear in candidate frames for fixed ladder size.
- **Selected-neighbor coverage:** `O(K^2 d)`, bounded by the maximum ladder rather than all frames.
- **PCA/randomized projection:** approximately `O(N p k)` for fixed input/output dimensions; multiple full memory-bandwidth passes remain but no all-frame quadratic matrix is formed.
- **Exact robust quantiles:** compiled per-column selection/sorting may be `O(N log N)` internally.  It is performed once per fitted domain and does not repeat per frame.
- **Cross-validation:** work is proportional to the declared fold count.  Fold count is a policy dimension rather than an emergent frame-count square.
- **Verification matrix:** committee × structures × temperatures is an explicitly requested Cartesian product.
- **Dense event evidence:** storage and processing are `O(E)` in the number of emitted events/protected memberships.

## Remaining architectural opportunities

These are worthwhile constant-factor or peak-memory improvements, but they are not omitted frame-count quadratic defects:

1. Store large DATA7 PCA centers/scales/projections as NumPy members rather than nested JSON float objects.
2. Replace the monolithic DATA7 ZIP with a checksummed directory artifact when memory mapping across DATA8 domains is more important than single-file atomicity.
3. Make large JSONL record catalogs lazy/indexed when optional per-atom environment materialization is enabled.
4. Fuse value and missing-indicator randomized-PCA passes to improve memory locality.
5. Batch DATA9 checkpoint evaluation through the native MACE graph path rather than ASE configuration-by-configuration calls.
6. Add a chunked selected-neighbor fallback if users raise `K` into the many-thousands range.

## Conclusion

The interrupted run exposed a genuine omitted `O(N^2)` checkpoint property.  That defect and every other unbounded quadratic-or-worse production path found by the renewed audit have been removed.  With fixed system size and policy dimensions, the campaign now scales approximately linearly with frame count; remaining apparent nonlinear slowdowns should primarily indicate memory pressure, filesystem behavior, or growth in atoms, folds, selected ladder size, events, or training jobs rather than a hidden all-frame pairwise algorithm.
