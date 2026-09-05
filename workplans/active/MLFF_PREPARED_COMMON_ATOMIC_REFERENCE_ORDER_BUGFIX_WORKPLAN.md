# MLFF Prepared Common Atomic-Reference Ordering Bug-Fix Workplan

## Status

**PASS / implementation-ready.**

This workplan addresses a blocking deserialization defect in prepared target-size common atomic-reference state. It is a bounded repair under the existing MLFF storage/currentness and target-size architecture. It does **not** reopen the scientific target-size design, atomic-reference fitting policy, prepared-generation ownership model, content-addressed storage model, or configured fidelity ladder.

## 1. Problem statement

`select-target-size` can fail while loading an otherwise valid prepared generation with:

```text
TrainingDataInputError: Common atomic-reference fitted values must align with the element order.
```

wrapped as:

```text
PreparedGenerationError: Prepared component 'common' failed its owner validation: Common atomic-reference fitted values must align with the element order.
```

The failure occurs in `CommonAtomicReferenceFit.from_dict()` during prepared-generation loading before target-size screening can proceed.

### Confirmed root cause

The current owner contract contains an ordering mismatch between canonical serialization and deserialization:

- `CommonAtomicReferenceFit.__post_init__()` requires `reference_energies_ev` to be ordered exactly according to increasing numeric `element_order`.
- `CommonAtomicReferenceFit._payload()` serializes references as a mapping keyed by string atomic number.
- Prepared-generation `_encode()` uses `json.dumps(..., sort_keys=True)` for deterministic canonical bytes.
- JSON object keys are therefore sorted lexicographically.
- `CommonAtomicReferenceFit.from_dict()` currently reconstructs `reference_energies_ev` by iterating `payload["reference_energies_ev"].items()`.
- For mixed-width atomic numbers such as `(8, 13, 14)`, canonical JSON key order becomes `"13", "14", "8"`, so the reconstructed tuple becomes `(13, 14, 8)` while `element_order` remains `(8, 13, 14)`.
- The owner validation correctly rejects that semantic misalignment.

This is a persistence/deserialization contract bug. It is **not** evidence of a failed atomic-reference fit, stale scientific state, target-size fidelity drift, candidate-specific E0 behavior, or an invalid prepared-generation ownership model.

## 2. Governing architecture and invariants

The repair must preserve the following accepted authority:

1. `prepare` remains the only owner that constructs and publishes the expensive shared P1 -> P3 common scientific substrate.
2. Downstream commands load the exact prepared generation already bound by `CampaignStore`; they must not silently rebuild, refit, or regenerate preparation-owned state.
3. `CampaignStore` remains the sole currentness authority.
4. Prepared objects remain immutable and content-addressed.
5. Canonical deterministic serialized bytes remain part of prepared-object identity.
6. Common atomic-reference fitted values remain shared preparation authority across target-size candidates.
7. Target-size screening/fidelity boundaries and ranking policy are unchanged.
8. Existing owner validation that fitted values align with canonical `element_order` remains semantically correct and must not be weakened.
9. Existing valid prepared artifacts should remain loadable without migration, rewrite, or re-publication when their stored key/value content is semantically complete and digest-valid.

The repair must prefer alteration of the faulty reader over adding wrappers, duplicate representations, compatibility layers, or new persistence machinery.

## 3. Gate A — repair `CommonAtomicReferenceFit.from_dict()`

### Owner

`mdstats/training_data/target_size_execution/common.py`

### Required change

Change `CommonAtomicReferenceFit.from_dict()` so that persisted fitted-reference mappings are reconstructed by semantic key identity and explicit `element_order`, not by serialized mapping iteration order.

The implementation must:

1. Parse and validate `element_order` first.
2. Require `reference_energies_ev` to be a mapping.
3. Normalize each persisted reference key to its numeric atomic number.
4. Validate that the normalized key set matches `element_order` exactly.
5. Reconstruct the internal tuple in `element_order` order, semantically equivalent to:

```python
reference_energies_ev = tuple(
    (z, reference_by_z[z])
    for z in element_order
)
```

6. Pass the reconstructed tuple through the existing owner constructor/validation path.
7. Preserve existing content-digest validation after reconstruction.

### Prohibited repairs

Do **not**:

- remove `sort_keys=True` from prepared-generation canonical JSON serialization;
- weaken or remove `CommonAtomicReferenceFit.__post_init__()` alignment validation;
- reorder `element_order` to follow persisted JSON object iteration order;
- change atomic-reference fitting mathematics;
- refit atomic references during `select-target-size`;
- regenerate prepared common state merely because key iteration order changed;
- create a second serialized representation or compatibility wrapper;
- bump schema solely for this defect when the existing wire representation already contains all required semantic information.

## 4. Gate B — strict malformed-payload handling

The repaired deserializer must remain strict. It must distinguish valid reordered mappings from genuinely malformed persisted state.

Reject at least the following cases with owner-appropriate serialization/input errors:

- missing atomic-number reference keys;
- extra atomic-number reference keys;
- malformed/non-integral atomic-number keys;
- duplicate semantic atomic-number keys created by normalization, if the input mapping form can represent such a collision;
- non-mapping `reference_energies_ev` payloads;
- non-finite fitted values through existing validation;
- invalid, duplicate, non-positive, or non-increasing `element_order` through existing validation;
- content-digest mismatch.

The reader may normalize representation order, but it must never silently repair missing, extra, contradictory, or corrupt scientific state.

## 5. Persistence compatibility policy

Existing valid prepared artifacts should remain usable after this fix.

Required behavior:

1. Preserve existing canonical serialization bytes and digest rules.
2. Do not rewrite an existing prepared object merely to load it.
3. Do not require a schema migration for valid artifacts written under the current schema.
4. Do not require the user to rerun `prepare` solely for this ordering defect.
5. If an artifact independently fails byte digest, manifest digest, key-set, schema, or other integrity checks after the reader repair, surface that as a separate genuine corruption/compatibility failure rather than masking it.

## 6. Gate C — owner-level regression tests

Add focused regression coverage for `CommonAtomicReferenceFit`.

### Critical roundtrip regression

A plain `from_dict(to_dict())` test is insufficient because an in-memory Python mapping preserves insertion order and can mask this bug.

The mandatory regression must exercise the actual canonicalization boundary:

```text
to_dict()
  -> json.dumps(..., sort_keys=True)
  -> json.loads(...)
  -> CommonAtomicReferenceFit.from_dict()
```

Use an element set whose numeric and lexical orders differ, for example `(8, 13, 14)`, with distinct fitted values.

Assert that:

- deserialization succeeds;
- `element_order` remains `(8, 13, 14)`;
- each atomic number retains its correct distinct fitted value;
- internal `reference_energies_ev` order follows `element_order`;
- content digest validation still succeeds.

### Additional owner regressions

Cover:

- deliberately scrambled mapping iteration order with correct key set;
- missing key;
- extra key;
- malformed key;
- key-normalization collision when representable;
- non-mapping payload;
- non-finite fitted value;
- existing digest mismatch behavior.

Tests must prove that order-only differences are accepted while semantic corruption remains rejected.

## 7. Gate D — prepared-generation integration regression

Exercise the real prepared-generation persistence path rather than only the owner type in isolation.

Required flow:

```text
prepared component serialization
  -> canonical JSON encoding
  -> immutable prepared object publication
  -> JSON load
  -> load_prepared_generation_components()
  -> TargetSizeCommonPreparation.from_dict()
  -> CommonAtomicReferenceFit.from_dict()
```

Use mixed-width atomic numbers such as `(8, 13, 14)`.

Assert that:

- publication succeeds;
- subsequent load succeeds;
- loaded common atomic-reference semantics are identical to the published owner state;
- content/object digest validation succeeds;
- loading does not rewrite or republish the object;
- `CampaignStore` currentness ownership is unchanged.

## 8. Gate E — target-size runtime regression

Exercise the failure path that exposed the bug:

```text
command_select_target_size
  -> execute_current_select_target_size
  -> build_screen_context
  -> load_prepared_target_size_generation
```

The regression should use a lightweight prepared fixture and must assert that execution advances beyond prepared common-state loading.

Also assert that:

- no atomic-reference refit is triggered;
- no prepared-generation rebuild/regeneration is triggered;
- configured target-size fidelity boundaries remain unchanged;
- candidate ranking receives the already prepared common authority;
- no candidate-specific atomic-reference fitting is introduced.

This is a functional regression, not a long production qualification run.

## 9. Gate F — bounded sibling audit

Inspect the prepared-generation and target-size persistence/deserialization surface for the same structural defect pattern:

1. semantic data serialized as a mapping;
2. canonical JSON key sorting changes representation order;
3. deserializer reconstructs ordered semantics using `.items()` / `.values()` iteration;
4. an explicit semantic order exists elsewhere in the payload or owner contract;
5. downstream validation requires that semantic order.

If an identical defect is found, repair it under the same keyed-data principle and add corresponding focused regression coverage.

Do not broaden this gate into a general serialization redesign. Do not change unrelated mapping iteration where ordering is intentionally irrelevant.

## 10. Gate G — regression and integration closure

Run all directly and semantically affected regression tests, including at minimum:

- `CommonAtomicReferenceFit` owner tests;
- target-size common/preparation tests;
- prepared-generation persistence/load tests;
- target-size runtime/CLI tests covering `select-target-size` startup and screen-context construction;
- any sibling owner tests changed under the bounded audit;
- repository integration regressions covering the modified persistence path.

All new and modified code must be covered by regression tests. Existing modules whose behavior is affected by the repair must also be re-exercised.

Do not substitute full production qualification for functional regression. Long real-data runs, performance characterization, resource measurements, and GPU qualification remain deferred to the final release qualification stage under existing project policy.

## 11. Acceptance criteria

Implementation may close only when all of the following are true:

- [ ] Canonically serialized prepared common atomic-reference state with lexical/numeric key-order disagreement loads successfully.
- [ ] `reference_energies_ev` is reconstructed strictly according to explicit numeric `element_order`.
- [ ] Distinct fitted values remain bound to the correct atomic numbers.
- [ ] Missing/extra/malformed/contradictory persisted reference state is still rejected.
- [ ] Existing alignment validation remains intact.
- [ ] Canonical JSON serialization and prepared-object identity rules remain intact.
- [ ] Existing valid prepared artifacts require no rewrite, migration, or rerun of `prepare` solely for this defect.
- [ ] Prepared-generation integration roundtrip passes.
- [ ] `select-target-size` advances beyond `build_screen_context` using already prepared common authority.
- [ ] No refit, regeneration, candidate-specific E0 logic, or fidelity-policy change is introduced.
- [ ] Bounded sibling audit is complete and any identical defect is repaired under the same principle.
- [ ] All affected regression and integration tests pass.
- [ ] No heavy production/GPU qualification is required for closure of this bug-fix implementation.

## 12. Closure rule

**PASS** only if the failure is removed by repairing the owner deserialization contract while preserving prepared-generation identity, currentness ownership, common atomic-reference semantics, and target-size scientific architecture.

**NO-PASS / reopen** if implementation instead weakens validation, changes serialization identity, rebuilds/refits downstream, introduces a parallel compatibility mechanism, requires unnecessary artifact migration, changes target-size scientific behavior, or leaves the canonical JSON roundtrip/runtime regression failing.
