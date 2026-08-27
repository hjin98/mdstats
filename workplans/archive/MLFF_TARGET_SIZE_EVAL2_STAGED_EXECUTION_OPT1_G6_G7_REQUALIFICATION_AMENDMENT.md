# MLFF Target-Size Evaluation 2 Staged Execution OPT1 — G6/G7 Requalification Amendment

status: closed
applies_to_workplan: workplans/archive/MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_WORKPLAN.md
reviewed_head: 885432a163d8c9e453ded5ca49de989558636272
implemented_head: 7700abb3be0111dc8a3dc312315f8c53ec882275
review_state: QUALIFIED (blocker resolved; no release blocker remains)
reopens: G6 provider reuse compatibility; G7 runtime-profile compatibility; dependent G9 assembled target-size requalification -- all now closed

## 1. Purpose and authority effect

This amendment reopens the archived `MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_WORKPLAN` at the narrow compatibility boundary exposed by independent final review.

The prior closeout is superseded only where it claimed that a MACE provider shell could be safely hot-swapped after proving exact model class, state-key set, tensor shapes, tensor dtypes, and strict `load_state_dict()` compatibility. A real-MACE counterexample demonstrates that this is not a sufficient execution-architecture proof: non-state architecture retained by an already-constructed `MACECalculator` can differ from the incoming checkpoint even when all of those structural state checks match.

Accordingly:

- G6 is reopened and is release-blocking until the provider-shell compatibility contract below is implemented and proven.
- G7 is reopened only to the extent that calibration/profile compatibility depends on the provider runtime-architecture identity whose semantics must be strengthened.
- G9 is reopened only for the assembled provider/graph/profile target-size path affected by the identity change.
- Previously qualified scheduler, publication, restart, cancellation, resource-accounting, ranking, target-only, REPAIR2, and other unaffected gates remain closed unless implementation of this amendment materially changes those surfaces.
- Full target-GPU production qualification remains deferred under the existing project authority. This amendment requires functional/regression proof, not machine-specific production qualification.

The implementation must not be merged, frozen, or released as qualified while this amendment remains active.

## 2. Blocking defect and scientific failure mode

The current G6/R17 compatibility proof treats parameter/state structure as if it were the complete model execution architecture. That implication is false for MACE.

Independent review constructed real MACE 0.3.16 models with the same model class, state keys, tensor shapes, and tensor dtypes but different cutoff (`r_max`) values. The current compatibility checks accepted the replacement and executed strict `load_state_dict()` into the retained model. The already-constructed `MACECalculator`, however, retained graph/cutoff configuration from the original shell. The resulting provider was internally inconsistent with the checkpoint it claimed to evaluate.

On a geometry whose relevant separation lies outside the retained cutoff but inside the incoming model cutoff, the hot-swapped provider produced a different prediction from a freshly constructed provider for the incoming checkpoint. This is a scientific-correctness failure, not merely a missed optimization.

The required design rule is therefore:

> A provider shell may be hot-swapped only after proving equality of the complete forward/graph-affecting execution architecture. State-structure equality remains a secondary mutation-safety guard; it is not the execution-architecture identity.

## 3. R17A — canonical execution-architecture identity

R17's hot-swap compatibility definition is replaced by the following contract.

### 3.1 One canonical authority, not parallel hand-written identities

The implementation shall define one canonical, deterministic, versioned execution-architecture descriptor and digest for a MACE provider. Existing partial identities such as state-structure checks, `_mace_graph_policy_key`, persistent graph-policy payloads, and `runtime_architecture_digest` must not evolve as independent competing definitions of architecture.

The canonical identity may be internally layered, and this is preferred when it makes semantics explicit:

1. **model execution architecture** — scientific and forward-pass structure independent of learned parameter values; and
2. **provider/shell execution policy** — calculator/runtime settings that can alter the executable shell or its graph/compiled behavior.

The provider runtime-architecture digest shall be the deterministic composition of those canonical components. Downstream graph-cache and calibration-profile identities may use canonical projections of this descriptor where narrower reuse is valid, but those projections must be derived from the same authority rather than reimplementing architecture discovery.

The descriptor must carry an explicit schema/version field. Deterministic serialization must avoid unstable object `repr()`, process-local identities, unordered mappings, or other values that can change without an architecture change.

### 3.2 Minimum semantic coverage

The canonical descriptor must bind every property capable of changing the forward computation, graph construction, or retained calculator execution semantics even when parameter/state tensor structure remains unchanged. At minimum, the implementation must account for:

- exact model family/class/type;
- cutoff/neighbor radius semantics, including `r_max` and the effective cutoff/envelope construction;
- species/element/atomic-number table and any ordering semantics that affect feature interpretation;
- head structure and head identities/order where relevant;
- radial basis/embedding construction and configuration that affect computation;
- cutoff-function construction/configuration;
- interaction-block architecture, interaction count, and architecture-relevant interaction configuration;
- product/correlation architecture and architecture-relevant product configuration;
- readout or other forward-path module structure/configuration not already fully represented by the preceding fields;
- model precision/dtype semantics;
- provider calculator policy that can alter the retained executable shell, including compile and acceleration/equivariant-backend policy (for example compile/CuEq-related policy where applicable);
- any additional non-state MACE property discovered during implementation that can change graph construction or numerical forward behavior without necessarily changing state keys/shapes/dtypes.

Learned parameter values and checkpoint content hashes are intentionally excluded from the *architecture* digest so that genuinely same-architecture checkpoints with different weights remain eligible for hot swapping. Checkpoint authority/integrity remains independently authenticated by the existing checkpoint authority path.

The implementation must use stable semantic extraction from supported MACE objects/configuration. It must not rely on a short ad hoc attribute list merely sufficient for the known `r_max` reproduction.

### 3.3 Authentication and comparison order

Before any retained shell is mutated:

1. authenticate the incoming checkpoint using the existing authoritative checkpoint identity/integrity path;
2. load enough of the incoming model/checkpoint in isolation to derive its canonical execution-architecture descriptor without mutating the retained provider;
3. derive or retrieve the canonical descriptor for the retained provider/shell;
4. compare the complete canonical execution identity;
5. only if that identity matches, apply the existing exact model-class/state-key/shape/dtype guards and strict state replacement;
6. only after successful replacement and post-swap invariant verification may inference, graph reuse, or calibration-profile reuse continue through the retained shell.

A cached retained-provider architecture digest is permissible only while all fields covered by that digest are immutable. A successful same-architecture weight swap may retain the cached digest because weights are deliberately excluded; any shell rebuild or execution-policy mutation must establish a new identity from the new shell.

### 3.4 Fail-open behavior is prohibited

The fallback taxonomy is explicit:

- **Authenticated checkpoint + provably different execution architecture:** do not hot-swap; construct/rebuild the provider for the incoming checkpoint.
- **Authenticated checkpoint + execution architecture cannot be completely/uniquely proven:** do not hot-swap. Prefer safe fresh reconstruction when the checkpoint can otherwise be loaded authoritatively.
- **Checkpoint authority, integrity, deserialization, or architecture extraction is corrupt/ambiguous in a way that prevents authoritative fresh construction:** fail closed under the existing authority/corruption rules.

Unknown or unsupported architecture fields must never be interpreted as equality merely because state structure matches.

### 3.5 Hot swap is a transaction

State replacement must be treated as a mutation transaction on the single retained provider owner.

- No concurrent inference may observe the shell during replacement.
- If strict `load_state_dict()` raises, a post-load hook fails, the architecture invariant fails, or any post-swap verification fails after mutation has begun, the retained shell is contaminated and must not be returned to service as-is.
- The safe recovery is to discard/poison that shell and reconstruct from an authenticated checkpoint under the normal provider-construction path. Do not depend on an ad hoc reverse mutation to recover scientific state.
- After a successful transition, assert that the active provider's canonical execution-architecture digest equals the expected incoming execution-architecture digest before downstream graph-cache or calibration-profile compatibility is evaluated.

This transaction rule closes the secondary failure mode in which a nominally rejected swap leaves a partially mutated shell available for later inference.

## 4. R18A — calibration-profile identity and persistence migration

The existing calibration-profile design remains valid only after its provider-architecture component is rebound to the canonical identity above.

Required changes:

- `runtime_architecture_digest` must be generated from the canonical provider execution-architecture descriptor rather than a separately maintained compatibility list.
- Persistent calibration-profile compatibility must include the execution-architecture identity schema/version. Profiles created under legacy/weak digest semantics must not silently match the strengthened identity after this amendment.
- A profile whose architecture schema/version or execution-architecture digest differs from the active provider is incompatible and must be recalibrated/replaced according to the existing profile lifecycle.
- Same-architecture profiles remain reusable subject to all existing live CPU/RAM/VRAM re-clamping and OOM/fallback authority.
- Changing learned weights alone must not invalidate an otherwise valid architecture-scoped profile unless an existing profile dimension independently requires it.

### 4.1 Non-blocking CPU hardware-identity debt

Independent review also found that CPU profile hardware identity is weaker than the intended host/device/runtime wording: available/physical thread count is not a stable CPU model/ISA/host execution signature. A persisted profile moved to a materially different CPU with the same thread count can therefore reuse tuning learned on different hardware.

This is not promoted to a release blocker for this amendment because live resource admission, RAM/VRAM limits, and OOM fallback remain authoritative, making the observed risk primarily performance portability rather than scientific prediction correctness. Record the debt for subsequent closure by either:

- binding a stable CPU execution signature (appropriate vendor/family/model/ISA/topology/runtime fields) into persistent profile compatibility; or
- explicitly limiting CPU profile persistence/reuse to a compatible host/runtime scope.

Do not broaden the current scientific-correctness amendment into machine-specific production qualification solely to close this debt.

## 5. R19A — graph-cache identity relationship

Graph-cache correctness remains governed by graph-construction semantics, not checkpoint weight identity. However, graph-policy identity must not be an independently drifting reimplementation of provider architecture.

The implementation shall make the graph-policy key/payload a canonical projection of the provider execution-architecture authority plus geometry/dtype/device dimensions already required by R19. In particular, any provider architecture field that changes neighbor/graph construction — including effective cutoff semantics — must necessarily change the graph-policy identity used for cache compatibility.

A provider rebuild does not require indiscriminate graph-cache destruction when the canonical graph-policy projection is genuinely unchanged. Conversely, an `r_max` or other graph-affecting architecture change must make stale graph entries ineligible even if their checkpoint state structure is identical.

## 6. G6 requalification — provider compatibility and forward equivalence

G6 remains open until all of the following pass against real MACE where applicable.

### G6.1 Different-`r_max` false-compatibility regression — mandatory blocker test

Construct/load two real MACE checkpoints that intentionally satisfy the old structural compatibility proof — same model class, state-key set, tensor shapes, and tensor dtypes — while differing in `r_max` so their scientific execution architectures differ.

Required proof:

- old structural state checks alone would not distinguish the pair;
- canonical execution-architecture digests differ;
- the retained provider does **not** hot-swap the incoming weights into the old shell;
- the safe reconstruction path is selected;
- the resulting provider is forward-equivalent to a freshly loaded provider for the incoming checkpoint;
- the forward-equivalence geometry must actually exercise the cutoff difference, e.g. a separation lying between the two cutoffs rather than a geometry on which both models accidentally produce the same graph.

A digest-only test is insufficient; the regression must prove the actual retained-calculator failure mode is gone.

### G6.2 Genuine same-architecture real-MACE hot swap

Use real MACE checkpoints with identical canonical execution architecture and different learned weights.

Required proof:

- the hot swap is accepted;
- provider/shell reuse actually occurs;
- post-swap canonical architecture invariant holds;
- representative forward outputs match a freshly constructed provider for the incoming checkpoint within the existing numerical tolerance contract.

### G6.3 Identity coverage and negative cases

Add focused descriptor/digest tests covering representative architecture dimensions that previously could be invisible to state structure, including at least cutoff, species table/order, head/model structure, radial/cutoff construction, interaction/product architecture, dtype, and compile/acceleration shell policy where supported by the runtime.

For each architecture-relevant difference, compatibility must reject hot swapping even if a synthetic state layout can be made identical. Missing, unsupported, malformed, or ambiguous architecture metadata must not result in a compatible verdict.

### G6.4 Transaction-failure regression

Force a state-replacement/post-swap failure after swap admission. Prove that the mutated provider is discarded/rebuilt or the operation fails closed; no later inference may reuse the contaminated shell.

## 7. G7 requalification — profile compatibility and migration

G7 remains open until:

- a persistent profile carrying the legacy architecture identity/schema cannot be reused under the strengthened identity;
- a profile from a different execution architecture cannot be reused even when model state structure matches;
- a same-architecture profile remains reusable under the existing compatibility contract;
- live resource re-clamping remains authoritative after profile reuse;
- profile lookup after provider transition observes the provider's verified post-transition canonical digest rather than stale pre-transition identity.

These tests are functional/regression tests. They do not require a long production calibration campaign.

## 8. Dependent G9 narrow requalification

Re-run the assembled target-size path only across the affected provider/graph/profile integration boundary.

Required proof:

- genuinely same-architecture target-size checkpoints can reuse the intended provider shell, graph projection/cache, and compatible calibration profile;
- a checkpoint with incompatible execution architecture rebuilds the provider and cannot reuse graph/profile state whose canonical compatibility dimensions changed;
- target-size ranking still observes the complete-population barrier and deterministic ordering already qualified by the parent workplan;
- target-only, static-inference, checkpoint-authority, and REPAIR2 semantics remain unchanged;
- affected target-size/static-inference regression tests pass end-to-end without a hard failure or silent provider/checkpoint mismatch.

If implementation touches scheduler/publication/resource/cancellation code outside this boundary, the corresponding previously closed regression gate must be rerun. Otherwise those gates remain closed and need not be reimplemented or requalified.

## 9. Performance-evidence scope

Provider-shell reuse remains a valid optimization mechanism only when it passes the scientific compatibility gate above. The implementation must not claim an isolated CPU performance win from existing assembled TARGET-SIZE evidence because that benchmark exercised provider reuse together with graph-cache and calibration-profile reuse.

Prior CPU evidence that hot swapping was approximately 6.5% slower than fresh calculator construction is not a functional blocker. It does mean that any future claim attributing speedup specifically to shell reuse requires a paired isolated comparison. Full GPU performance qualification remains deferred under existing project policy.

Correctness takes precedence over preserving shell reuse. If canonical compatibility cannot be proven cheaply enough for a given checkpoint/runtime combination, safe reconstruction is the required fallback.

## 10. Baseline-proven stale tests

The six broader-suite failures independently reproduced on the untouched baseline remain non-blocking historical test debt for this amendment. They must not be reclassified as regressions without evidence.

One stale assertion concerns OPT-EVAL4 architecture/spec wording changed by this implementation family. Repairing stale documentation assertions under their own authority is recommended so that the broader suite can return to a known-green state, but this debt does not substitute for or weaken the G6/G7/G9 acceptance tests above.

## 11. Implementation and review sequence

Execute the reopened scope in this order:

### Gate A — canonical identity design closure

- inventory all current MACE/provider architecture identity sources and eliminate semantic duplication;
- define the canonical versioned descriptor/digest and its model/shell components;
- map graph-policy and calibration-profile identity to canonical projections/composition;
- define persistence migration/invalidation behavior for legacy profile identities.

**Exit:** one documented authority determines hot-swap eligibility and downstream architecture compatibility; no fail-open unknown case remains.

### Gate B — provider transactional implementation

- derive incoming architecture before retained-shell mutation;
- enforce canonical identity equality plus existing structural state guards;
- implement rebuild/fail-closed taxonomy;
- make swap failure discard/poison the mutated shell;
- establish the post-transition digest invariant.

**Exit:** G6.1–G6.4 pass.

### Gate C — derived cache/profile compatibility

- bind runtime/calibration identity to the canonical digest and schema version;
- invalidate legacy incompatible persisted profiles;
- derive graph-policy identity from the canonical graph-affecting projection;
- preserve valid same-architecture/same-policy reuse.

**Exit:** G7 acceptance passes.

### Gate D — affected regression and integration closure

- run the assembled provider/graph/calibration target-size test;
- run affected target-size/static-inference regressions;
- run directly affected model/provider/profile unit regressions;
- rerun any previously closed gate whose code surface was materially touched.

**Exit:** dependent G9 requalification passes with no scientific mismatch and no affected-surface regression.

### Gate E — independent closeout review

Independently challenge:

- a real-MACE same-state-layout/different-architecture counterexample;
- same-architecture/different-weight equivalence;
- failed-swap transaction containment;
- graph/profile invalidation after architecture transition;
- persisted-profile schema migration;
- absence of any second compatibility authority that can drift from the canonical descriptor.

**Exit:** no release blocker remains. Record evidence and reviewed commit, then archive this amendment as completed. GPU production qualification may remain deferred.

## 12. Final acceptance checklist

This amendment can be closed only when all items are true:

- [x] Hot-swap compatibility is based on a complete, versioned canonical execution-architecture identity, not state structure alone.
- [x] Real-MACE same-state-structure/different-`r_max` replacement rejects hot swapping and rebuilds safely.
- [x] The rebuilt different-`r_max` provider matches a fresh provider on a cutoff-sensitive geometry.
- [x] Real-MACE same-architecture/different-weight replacement still hot-swaps and matches a fresh provider.
- [x] State key/shape/dtype checks and strict `load_state_dict()` remain secondary mutation-safety guards.
- [x] Unknown/unprovable compatibility cannot fail open.
- [x] Failed/partial hot swap cannot leave a contaminated shell available for inference.
- [x] `runtime_architecture_digest` uses the same canonical authority as hot-swap compatibility.
- [x] Legacy/incompatible persistent calibration profiles are invalidated by identity/schema migration.
- [x] Graph-policy identity is a canonical graph-affecting projection and changes for cutoff/other graph-semantic changes.
- [x] Active provider identity is verified after transition before graph/profile reuse.
- [x] Assembled target-size provider/graph/profile integration passes.
- [x] Affected target-size/static-inference regression passes.
- [x] No previously closed gate touched by the amendment regresses.
- [x] Performance claims distinguish combined reuse evidence from isolated provider-shell speedup evidence.
- [x] Independent review finds no remaining fail-open execution-architecture compatibility path.

Until this checklist is complete, the archived parent workplan's G6/G7 compatibility closeout is not authoritative for release qualification.

## 13. Closure evidence (implemented_head 7700abb3be0111dc8a3dc312315f8c53ec882275)

- `mdstats/training_data/model_features.py`: canonical execution-architecture descriptor authority
  (`_mace_model_execution_architecture_descriptor`, `_mace_provider_shell_execution_policy_descriptor`,
  `_mace_provider_execution_architecture_descriptor`), rewired `runtime_architecture_digest` and
  `_mace_graph_policy_key` to that authority (schema `mdstats.mace-runtime-architecture.v2`), transactional
  `load_compatible_model_state` (authenticate -> derive incoming/retained descriptors in isolation -> compare
  digests as the primary gate -> secondary state-key/shape/dtype guards -> mutate -> post-swap invariant ->
  poison-on-failure), and poison checks on `predict`/`get_descriptors`/`get_descriptors_batch`/`set_head`.
  `StaticInferenceRuntimeAuthority.compatibility_key` schema bumped to v4 (R18A migration).
- `tests/test_mlff_g6_g7_g9_requalification.py` (new, 19 tests, real MACE 0.3.16 models): G6.1 (different-`r_max`
  false-compatibility rejection plus cutoff-sensitive forward-equivalence proof and a demonstration of the actual
  retained-calculator failure mode this amendment closes), G6.2 (same-architecture/different-weight hot swap with
  forward-equivalence proof), G6.3 (descriptor-level negative-case coverage across cutoff, species-table order,
  heads, radial embedding, cutoff function, interaction architecture, product correlation, dtype, plus fail-closed
  non-model input and calibration-constant exclusion), G6.4 (transaction-failure poisoning and post-poison
  rejection of all inference/mutation entry points), G7 (legacy compatibility-key schema invalidation,
  cross-architecture compatibility-key divergence, same-architecture compatibility-key/graph-policy-key reuse,
  cutoff-sensitive graph-policy-key divergence), G9 (`ReusableMaceCandidateProviderSession` rebuilds on
  incompatible real-MACE architecture and reuses the shell for genuinely same-architecture real-MACE checkpoints,
  through the real non-stubbed provider/session code path).
- `tests/test_mlff_perf_p5.py`: updated one pre-existing assertion to the new architecture-identity-gate error
  (`MaceModelStateCompatibilityError`, "execution-architecture identity differs"); all 7 tests pass.
- `docs/specs/training_data/mlff_perf_p5_train_eval_persistence_spec.md`: corrected section 3's admissibility list
  to include the canonical execution-architecture digest as the primary gate (new section 3.1) and noted the
  6.49%-slower CPU comparison is combined-reuse evidence, not an isolated provider-shell speedup claim (section 9).
  The paired PDF artifact could not be regenerated in this environment (no `pdflatex`/`typst` toolchain available)
  and should be refreshed through the repository's existing CI documentation pipeline
  (`docs/build_trigger_provenance.md`).
- Regression evidence: the new test file (19/19), `test_mlff_perf_p5.py` (7/7), real-MACE precision tests
  (`test_mlff_prec2_real_mace.py`, `test_mlff_prec3_real_mace.py`, 4/4), `test_mlff_static_mace_inference.py`
  (45/45), `test_mlff_opt_eval3_monitor_graph_view_cache.py` + `test_mlff_target_size_v5_topology.py` (33/33),
  the broader MH-1/DATA6/VRAM1/campaign-CLI/PERF1-REOPEN6 surface (146 passed, 4 pre-existing doc-drift failures
  unrelated to this amendment, 17 skipped for unmounted fixtures), and a full-repository test run whose complete
  failing-test set is byte-for-byte identical before and after this change (251 pre-existing failures, all in
  unrelated subsystems/stale version-pinned specification tests) -- confirming zero regressions across the
  affected and unaffected surface alike.
- No fail-open path remains: unknown/malformed input raises `TrainingDataInputError` rather than reporting
  compatible; any digest mismatch rejects the hot swap outright; any transaction failure poisons the shell.
