---
kind: implementation-workplan
workplan_id: DOC-MVQUAL-MEM1-PERF1
protocol_version: 5.1.0
status: M0_READY
analysis_base_ref: main@9fdc649289cbf65fe825af8adf958e10bd6dd1ac
predecessor_workplan: DOC-REPAIR2-PERF1
review_status: FINAL_REVIEW_HARDENED
---

# DOC-MVQUAL-MEM1-PERF1 — bounded exact MVQUAL and conditional progressive optimization

## Objective

Make TARGET-DATA2C-MVQUAL1 complete reliably at the full product ladder, including target size 16,384, without changing scientific policy, output schemas, numerical authority, or content digests for identical inputs. Remove the present memory-amplifying sparse telemetry path first; only after product-scale memory safety is established should additional wall-time optimization be considered.

The implementation sequence is deliberately:

```text
strict bounded CSR
    -> exact independent-rung MEM1
    -> product memory qualification
    -> measure remaining wall time
    -> reuse existing progressive TARGET-DATA2B scorer if justified
    -> incremental sparse telemetry only if still justified by measurement
```

PERF1 is therefore conditional. A successful bounded implementation that makes full MVQUAL comfortably practical is an acceptable endpoint even if no progressive sparse state is introduced.

## Opening evidence and root cause

The current production MVQUAL owner is `mdstats/training_data/target_multi_view_qualification.py`.

For one `(domain, selector, target_size)` job it currently performs:

1. independent TARGET-DATA2B scoring through `score_target_subset_coverage()`;
2. MVIDX telemetry through `_selector_telemetry_indices()`;
3. a second MVIDX covered-mask traversal through `indexed_family_covered_mask()` to cross-check independent coverage mass;
4. hard-obligation counting and final same-N comparison.

The sparse telemetry path gathers all selected candidate-to-witness rows for a family at once. `csr_gather_rows()` materializes edge-sized prefix/base/position arrays; `_selector_telemetry_indices()` then materializes gathered witnesses, an `int64` witness view, witness multiplicity, and for unique-owner telemetry an edge-sized `np.repeat(selected, lengths)` owner array. At full product scale, selected-edge cardinality can be very large even though the final telemetry is small.

The current admission estimate is not a trustworthy peak-live-memory model. It uses average selected edges and a coarse per-edge term, while the implementation can hold several edge-sized arrays simultaneously. It also sums family costs even though scientific scoring/telemetry traverse families sequentially.

This is an allocation/data-movement design defect, not primarily a worker-count problem.

## Scientific and architectural envelope

Preserve exactly:

- TARGET-DATA2C-MVQUAL1 as the scientific qualification owner in `target_multi_view_qualification.py`;
- TARGET-DATA2B as the independent coverage/scoring authority;
- MVIDX as secondary exact telemetry plus an independent sparse covered-mass cross-check;
- current policy/schema/version constants and serialized fields;
- current same-N comparison semantics, tolerances, hard-obligation rules, extent rules, N95 logic, learning-control selection and outcome classification;
- current canonical domain, rung, selector, family, stratum and UID ordering;
- current `float64` scientific reductions and comparison tolerances;
- deterministic scientific outputs independent of worker count, chunk size and completion order;
- current direct API behavior when no explicit campaign resource scope is supplied;
- no approximation, sampling, stochastic pruning, approximate nearest-neighbor search, reduced family set, weakened cross-check or skipped scientific validation.

Execution-only chunk sizes, memory estimates, worker admission and profiling telemetry must not enter scientific content digests.

### Authority/version rule

M0-M5 are execution-only. They must not change:

- `TARGET_MULTI_VIEW_QUALIFICATION_*` schemas/version;
- `TargetMultiViewQualificationPolicy.policy_digest` for identical policy;
- any report/plan content digest for identical inputs;
- persistence keys or scientific lineage;
- TARGET-DATA2B coverage semantics;
- MVIDX scientific content.

Do not update a golden digest to bless an implementation-induced numerical change. Any unexpected scientific-output change fails the gate unless separately reviewed as a scientific redesign.

## Reviewed design constraints

### 1. Existing CSR batching is not a strict memory bound

`iter_csr_gather_batches()` batches only at complete-row boundaries and explicitly permits a single row to exceed `max_edges`. MEM1 therefore requires a stricter execution primitive capable of splitting inside one CSR row.

For every emitted chunk, including a pathological single row:

\[
E_{chunk} \le E_{max}.
\]

The strict stream must preserve canonical selected-row order and canonical within-row edge order. It must expose enough owner information to attribute unique witnesses without materializing an edge-sized owner vector for the entire selected set.

### 2. Freeze floating-point reduction order

Chunking may change integer accumulation order because integer multiplicity is exact, but it must not change scientific floating-point association.

For one family, stream selected edges only to build exact integer state. After all chunks are consumed, derive full witness masks and perform all weight reductions in canonical witness-array order using the same `float64` NumPy reductions as the current implementation.

Do not accumulate covered/uncovered/unique mass chunk-by-chunk.

### 3. Multiplicity width

Witness multiplicity satisfies

\[
m_w \le N_{selected}.
\]

MVQUAL1 v1 freezes the capacity ceiling at 16,384, so signed `int32` multiplicity is safe. Retain `int32` unless the policy ceiling is ever revised beyond its representable range; fail closed if an execution request violates the invariant.

### 4. Unique-owner telemetry

`zero_unique_candidate_fraction` means a selected candidate owns at least one witness whose final selected multiplicity is exactly one in any required family.

A bounded implementation may use two edge passes per family:

1. stream selected edges to build final witness multiplicity;
2. stream selected edges again and mark the current selected candidate as a unique owner when any of its edges points to a final `multiplicity == 1` witness.

This preserves exact semantics while bounding edge scratch. No full `np.repeat(selected, lengths)` array is permitted.

### 5. Reuse one bounded sparse mask for the MVIDX mass cross-check

After pass 1, `covered = multiplicity > 0` is exactly the same set represented by `indexed_family_covered_mask()` for the same selected candidates. Use this exact mask to compute the MVIDX covered mass and compare it to the independent TARGET-DATA2B report.

This removes the current second full selected-edge gather without weakening validation: the independent authority remains TARGET-DATA2B, while MVIDX still independently establishes the sparse coverage predicate from its adjacency.

### 6. Peak-live-memory model

The scheduler estimate must model job phases and lifetimes rather than total dataset size:

\[
M_{job,peak}=M_{persistent}+\max(M_{direct},M_{sparse},M_{crosscheck/hard}).
\]

Shared immutable reference/MVIDX arrays are thread-shared and must not be multiplied by worker count as if copied per worker. Job-local result objects, selected-index arrays, per-family witness state, strict-stream scratch and direct scorer scratch must be included when simultaneously live.

The estimate is an admission contract, not scientific authority. Derive its sparse terms from the implemented bounded kernel rather than from the old unbounded gather.

### 7. PARCORE1 ownership

Do not redesign `DeterministicWorkQueue` preemptively. MVQUAL should adapt its task estimates, producer/drain behavior or stage reservation using existing PARCORE1 mechanisms first. Modify the queue only if focused evidence proves the queue itself prevents correct admission or causes material memory retention after the MVQUAL-local fix.

### 8. Existing progressive direct scorer

`score_target_nested_subsets_coverage()` already owns exact progressive TARGET-DATA2B scoring for nested subsets. If PERF1 is needed, regroup MVQUAL work by `(domain, selector)` and reuse that semantic owner instead of implementing a second progressive coverage engine.

The existing scorer validates exact nesting and returns unchanged TARGET-DATA2B reports.

### 9. Progressive sparse telemetry is a separate conditional optimization

Unique ownership is non-monotone under added selected candidates: witness multiplicity may transition `0 -> 1 -> 2`, causing ownership to appear and later disappear. A correct incremental sparse state would need multiplicity plus sole-owner/per-candidate unique-witness bookkeeping and exact canonical per-rung reductions.

Do not implement this machinery unless P0 measurement shows sparse rescanning remains a dominant material cost after M5 and P1.

## Target product envelope

The primary product case currently has:

- one label domain with 36,408 candidates;
- 165 required coverage families;
- 9,505,021,522 MVIDX forward candidate-to-witness edges;
- fixed target-size ladder through 16,384;
- authenticated native/file-backed MVIDX state;
- workstation-class CPU execution where full campaign RAM is finite and swap must be avoided.

The implementation must scale with selected-edge work while keeping **temporary edge memory bounded by configured chunk size**, rather than proportional to all selected edges in a family.

## Gate M0 — freeze executable contracts and feasible baseline

### Implementation

Add focused tests/benchmark fixtures that freeze the current scalar/reference behavior before replacing the product kernel.

Retain `_selector_telemetry_reference()` as an intentionally independent slow oracle. Do not refactor it to share the optimized implementation.

Capture cases covering:

- multiple families;
- overlapping witnesses;
- uncovered witnesses;
- witnesses with multiplicity 1 and >1;
- selected candidates with and without unique ownership;
- correlation-unit diversity;
- run/condition provenance;
- hard obligations;
- feasible same-N plan construction;
- exact scientific plan/content digests for fixed fixture input where stable repository fixtures already provide them.

### Acceptance

M0 passes when current `main` behavior is executable on bounded fixtures and the tests establish exact expected scalar/vector behavior without modifying production science.

## Gate M1 — strict canonical CSR edge stream

### Implementation

Extend `_sparse_vector_kernels.py` with one minimal strict-stream primitive. Prefer a generic CSR execution helper rather than an MVQUAL-specific duplicate because strict bounded CSR traversal is a data-layout responsibility already owned by this module.

The helper must:

- accept offsets, indices, selected rows and `max_edges`;
- emit nonempty chunks in canonical row/edge order;
- never emit more than `max_edges` edges;
- split inside an oversized row when necessary;
- identify the owner selected-row position or equivalent owner information for each emitted edge/chunk without constructing full-set edge owners;
- avoid edge-sized Python objects;
- validate obvious shape/range contract violations fail closed.

### Tests

Require exact reconstruction against canonical `csr_gather_rows()` for small/moderate fixtures and an adversarial CSR where one row alone exceeds the limit several times.

Test empty rows, repeated selected-row ordering where disallowed by caller contract, first/last rows and `max_edges=1`.

### Acceptance

Every emitted chunk satisfies `edge_count <= max_edges`, concatenated indices/owners are exactly canonical, and existing sparse-vector tests remain green.

## Gate M2 — bounded exact MVQUAL sparse telemetry

### Implementation

Replace `_selector_telemetry_indices()` family-local unbounded gather with bounded passes using M1.

For each sparse family:

1. allocate `int32` multiplicity of `witness_count`;
2. first strict edge pass increments multiplicity exactly;
3. derive `covered`, `unique_witness` and canonical `float64` uncovered/unique/reference mass reductions;
4. compute the MVIDX covered mass from `covered` and cross-check against the independent TARGET-DATA2B family report in the same job;
5. second strict edge pass identifies selected candidates that own at least one final unique witness;
6. release family-local state before moving to the next family.

Refactor `_mvqual_score_job()` only enough to avoid the redundant `indexed_family_covered_mask()` traversal. Keep hard-obligation counting unchanged unless a local reuse is trivially exact and independently tested.

Expose the strict edge limit as execution-only internal/configurable input with a conservative default. It must not enter scientific digests.

### Exactness requirements

For identical inputs, require exact equality of:

- telemetry integer fields;
- telemetry floating fields;
- direct/MVIDX coverage cross-check result;
- family/stratum comparison fields;
- same-N decisions;
- plan outcome;
- serialized scientific content digest.

### Acceptance

M2 passes focused scalar-oracle, old-vector-reference and adversarial tests. No family-local allocation scales with all selected edges except the underlying read-only MVIDX mapping itself.

## Gate M3 — phase-aware memory admission and telemetry

### Implementation

Replace `_estimate_mvqual_score_memory_bytes()` with a conservative peak-live estimate matched to the new implementation.

Separate at least:

- job-persistent selected/provenance/result working state;
- direct TARGET-DATA2B scoring scratch;
- maximum one-family sparse witness state;
- strict-stream scratch from `max_edges`;
- hard-obligation/correlation counting scratch.

Do not sum mutually exclusive family scratch across all families.

Add execution-only MVQUAL telemetry sufficient to observe:

- configured strict `max_edges`;
- total streamed edges;
- maximum emitted chunk edges;
- maximum encountered selected CSR-row length;
- per-job/per-phase wall time where practical;
- estimated job peak bytes;
- PARCORE1 allocated/max-busy workers, peak-accounted bytes and memory backpressure;
- process RSS/fault/I/O counters in a benchmark wrapper rather than scientific authority.

If the campaign already owns a resource scope, preserve it. Direct API calls without a scope remain independent of transient host free-memory state.

### Acceptance

Focused tests show worker admission decreases under deliberately tight RAM budgets and still makes progress; estimates do not falsely reject a small bounded job because total graph bytes are counted as per-worker scratch.

## Gate M4 — semantic/determinism qualification

Run targeted tests under multiple execution settings:

- strict edge limits including 1, small values and normal default;
- scoring workers 1 and >1;
- completion-order perturbation where existing test seams allow it;
- nested and nonnested scientific inputs unchanged from current authority behavior.

Compare the optimized path to `_selector_telemetry_reference()` and to the current direct TARGET-DATA2B scorer on bounded fixtures.

### Acceptance

All scientific reports/plans/digests are identical across chunk sizes and worker counts. No tolerance widening is allowed to make this pass.

## Gate M5 — product bounded-memory meter

### Runner

Add the smallest reusable benchmark that invokes the **real production MVQUAL builder** from the persisted campaign authorities. Do not run full `prepare` merely to reach this stage, and do not reconstruct a second MVQUAL algorithm in the benchmark.

The runner should report:

- source commit;
- authority input digests;
- candidate/family/forward-edge counts;
- requested/effective workers;
- RAM budget and estimated per-job peak;
- strict edge limit and observed max chunk/row;
- wall/user/system CPU;
- RSS before/peak/after where available;
- minor/major faults and filesystem I/O;
- PARCORE1 memory/backpressure telemetry;
- completed rung sizes and final scientific plan digest/outcome.

Use a bounded wall-time and no generated product-scale scratch beyond normal authority reads and the small JSON benchmark result.

### Product acceptance

M5 passes when the full 16,384 qualification completes with:

- no OOM and no OS swap attributable to MVQUAL;
- all configured scientific cross-checks passing;
- repeated execution producing the same final scientific content digest;
- strict chunk bound observed on product data;
- peak RSS leaving meaningful workstation headroom rather than approaching physical-memory exhaustion.

If M5 requires the user's local campaign database or target-scale files unavailable to the connected execution environment, stop after committing the runner and provide the shortest exact command. Do not fabricate product evidence.

## Gate P0 — profile/stop decision

Using M5 evidence, attribute remaining wall time among:

- independent TARGET-DATA2B direct scoring;
- sparse MVIDX telemetry;
- sparse mass cross-check;
- hard obligations/provenance;
- queue/resource waiting;
- page faults/I/O.

### Stop rule

If total product MVQUAL is comfortably practical (design target approximately <= 5 minutes on the established workstation, absent abnormal cold-cache I/O), stop PERF1. MEM1 is accepted without additional progressive state.

If wall time remains material, optimize only the measured dominant component.

## Gate P1 — conditional progressive direct TARGET-DATA2B scoring

If direct scoring is material, regroup independent jobs from `(domain, selector, rung)` to `(domain, selector)` and call existing `score_target_nested_subsets_coverage()` once per nested rung sequence.

Do not duplicate its progressive family state.

The MV selector may contain materializable sizes not shared with legacy. Build each selector's canonical nested size sequence exactly from its authoritative rungs, then map returned reports back to the unchanged MVQUAL comparison logic.

If the supplied sequence is not nested, fail closed or use the historical independent scorer rather than redefining nesting.

### Acceptance

Per-rung TARGET-DATA2B reports and final MVQUAL plan digest are exactly identical to independent scoring on representative fixtures. Product wall time must improve materially enough to justify the regrouping.

## Gate P2 — conditional progressive sparse telemetry

Implement only if P0/P1 evidence still shows repeated sparse rescanning dominates.

A proposed state must first prove an exact transition model for:

- witness multiplicity;
- sole owner while multiplicity is one;
- per-selected-candidate unique-witness count;
- `0 -> 1` and `1 -> 2` witness transitions;
- newly selected candidates;
- correlation-unit/run/condition counts;
- canonical per-rung float reductions.

No incremental sparse authority may replace the bounded M2 implementation as the independent oracle. P2 must compare every rung against M2.

### Acceptance

Exact rung-by-rung telemetry and plan digest equality, plus material measured product speedup. Otherwise delete/revert P2 and retain simpler MEM1/P1.

## Gate P3 — final product performance acceptance

Repeat the product meter under comparable cache/resource conditions.

Acceptance requires:

- identical scientific authority digest to M5/reference;
- no swap/OOM;
- bounded RSS and scratch;
- materially improved end-to-end wall time relative to the immediately preceding accepted implementation;
- no added persistent product-scale graph or generated scratch;
- no unjustified compatibility/duplicate execution path.

## Focused regression set

At minimum maintain/run tests covering:

- sparse vector kernels;
- MVIDX indexed coverage helpers;
- MVQUAL telemetry scalar/reference parity;
- MVQUAL plan construction and serialization;
- parallel MVQUAL determinism/resource admission;
- REPAIR2/MVSEL2 integration tests that depend on shared sparse helpers if those helpers change.

Run targeted tests before any broader suite.

## Non-goals

This workplan does not authorize:

- changing coverage threshold, deficit rules, learning-control policy or capacity ceiling;
- replacing TARGET-DATA2B with MVIDX as scientific authority;
- changing REPAIR2/MVSEL2 science;
- rebuilding MVIDX or changing its persistence schema;
- GPU acceleration;
- approximate coverage or telemetry;
- process-pool duplication of large scientific state;
- broad PARCORE1 redesign without evidence;
- a second progressive direct coverage implementation;
- automatic full-campaign qualification that can recreate prior 100+ GiB scratch behavior.

## True redesign triggers

Stop and return to design review if any of the following occurs:

1. exact bounded telemetry cannot reproduce scalar/current outputs without scientific change;
2. per-family witness state itself is too large for the product RAM envelope;
3. strict edge streaming causes prohibitive I/O/refault amplification that cannot be solved by reasonable chunk sizing/locality;
4. direct TARGET-DATA2B scoring, rather than sparse telemetry, is shown to require a different algorithm than the existing progressive scorer;
5. PARCORE1's ownership/lifetime model is proven incapable of safe admission for this stage;
6. product qualification needs a persistent second graph or other multi-GiB execution artifact;
7. any optimization requires changing scientific floating reduction order or tolerances.

## Completion and documentation

This workplan is temporary transition coordination. Permanent architecture/specification documents change only if the accepted implementation changes a durable software contract; pure execution optimization should not create a permanent scientific documentation delta.

On acceptance, retain benchmark/qualification evidence in the appropriate benchmark/audit location, move any material chronology needed for history, and archive this workplan according to repository policy.
