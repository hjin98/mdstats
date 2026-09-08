---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-IMPLEMENTATION-REVIEW-R2-POSITION-INTEGRITY
parent_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-IMPLEMENTATION-REVIEW-R2
root_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
created_date: 2026-09-05
branch: plan/mlff-storage-io-reset-r37-review-closure
reviewed_head: 57f8f408d1693f18a891e4209de6af8a62c03a20
reviewed_executable_head: 84868eccd5dec74f07d4aa1917037d57e032249d
verdict: NO-PASS / IMPLEMENTATION-REOPENED
scope: final residual qualification component-position schema integrity at the public observation boundary
precedence: this amendment closes the two blockers recorded by IMPLEMENTATION_REVIEW_R2 except for the narrower position-locator integrity defect stated here. Every non-conflicting root, integration, P4-P7, Storage R38, prior-review, and R2 invariant remains binding.
---

# MLFF assembled integration - R2 residual position-integrity review

## 0. Verdict

**NO-PASS / IMPLEMENTATION-REOPENED.**

The R2 repair at executable candidate `84868eccd5dec74f07d4aa1917037d57e032249d` closes the two named blockers from the preceding review in their main form:

- `qualification status` now derives target revision, selected binding, and every P7 pointer digest from the shared `campaign_owner_snapshot` read transaction;
- plan, component evidence, locked activation, release index, and terminal record are loaded through typed content-addressed owners before their fields are interpreted;
- attempt identity comes from the authenticated qualification plan rather than being guessed from the selected binding;
- the combined probabilistic P5/P7 race was replaced with deterministic one-owner transaction races;
- exact-candidate closure evidence is recorded: the required named closure selection is `690 passed, 0 failed, 0 skipped`, and the affected `-k "mlff or storage or campaign"` comparison has identical baseline/candidate failure sets with the persistent failures mapped outside this integration acceptance surface.

Those gains are retained. No scientific, target-size, P5, P7, prepared-generation, CampaignStore, or Storage-R38 architecture is reopened.

Independent source review nevertheless found one narrower defect inside the newly shared mutable component-position reader. It is directly within the prior R2 requirement that malformed or schema-inconsistent position state must degrade to an unreadable/blocked diagnostic instead of becoming semantic truth.

---

## 1. Blocking finding - current locator schema can fall through as unauthenticated legacy/direct payload

`qualification.runtime.read_component_position()` currently parses the mutable locator and then performs:

```python
if not payload.get("position_object"):
    return payload
```

The current publication owner, however, always writes a locator with schema `mdstats.qualification-component-position-locator.v1` and with both `position_object` and `position_object_digest`. Therefore `position_object` is mandatory for the current locator schema.

A parseable corruption can delete only `position_object` (and, if desired, its digest) while leaving the current schema plus `component`, `binding_digest`, `component_input_digest`, and `evidence_digest`. The reader then treats that malformed current locator as the legacy/direct representation and returns it without schema/shape authentication.

`qualification.observation._component_states()` subsequently follows the returned `evidence_digest`; the evidence object itself is content-authenticated, but the malformed mutable locator has still selected which authentic evidence object is reported. The observer checks the loaded evidence's component and qualification binding, but that does not make a current-schema locator with a missing mandatory object reference valid.

This matters because component state is operator-visible control-plane information. The Frozen observation invariant is not merely "the final evidence object parses": mutable coordination bytes that choose the evidence must themselves satisfy the accepted representation contract, or status must say unreadable. R2 explicitly required malformed/schema-inconsistent position bytes to degrade to a blocked diagnostic.

The new acceptance test that corrupts `position_object_digest` is useful but does not exercise this bypass: it leaves `position_object` present, so the verifying branch runs. The missing-mandatory-field path remains untested.

### Required repair - tighten the existing reader; do not add an authority

1. Keep `read_component_position()` as the single shared reader used by both `QualificationSession.completed_component()` and observation.
2. Make the representation distinction explicit:
   - if `schema == "mdstats.qualification-component-position-locator.v1"`, require the complete current locator contract, including `component`, `binding_digest`, `component_input_digest`, `evidence_digest`, `position_object`, and `position_object_digest`; missing/wrongly typed fields are `QualificationLineageError`;
   - require the locator's component/binding/input/evidence claims to agree with the authenticated immutable position object it names before returning that object;
   - if a pre-locator direct representation is still intentionally supported, recognize it by an explicit historical shape/schema rule and validate its required fields. Do **not** treat an arbitrary JSON object lacking `position_object` as historical compatibility state.
3. `qualification.observation._component_states()` must continue to degrade `QualificationLineageError` to `unreadable_position` + blocked detail. Do not reconstruct inputs, open a `QualificationSession`, or add a new position registry/CAS/currentness authority.
4. Do not remove historical compatibility unless current package authority permits it; the preferred repair is a typed discriminator between valid legacy-direct state and malformed current-locator state.

### Required acceptance

Add focused real-owner/public-command regressions on the exact repaired candidate:

- current `locator.v1` with `position_object` removed -> `unreadable_position`, blocked, no mutation;
- current `locator.v1` with `position_object_digest` removed -> unreadable/blocked;
- current locator whose declared component/binding/input/evidence fields disagree with its authenticated immutable position object -> unreadable/blocked;
- if legacy-direct state remains supported, one positive test proves the exact accepted legacy shape still reads through both the session owner and `qualification status`; malformed near-misses fail closed;
- rerun `test_mlff_qualification_status_observation.py`, the campaign observation coherence suite, P7 qualification acceptance, and assembled lifecycle; then rerun the affected regression selection or provide bounded regression evidence sufficient under the parent test doctrine for this one-reader change.

The existing deterministic concurrency evidence and the 690-test exact-candidate closure evidence may be reused where the new reader-only repair cannot invalidate them, but every test that exercises `read_component_position()` or qualification observation must run on the final executable candidate.

---

## 2. Non-blocking conclusions preserved

The following are **PASS / remain closed** and must not be reopened to repair this defect:

- coherent `campaign_owner_snapshot` use by both public status paths;
- typed authentication of content-addressed P7 plan/component/locked/release/terminal objects;
- deterministic single-owner publication/status race tests;
- create-or-verify prepared/frame publication;
- ordinary `prepare` source-change detection, terminal idempotence, and stale-writer CAS;
- P3 prediction-evidence v2 without redundant `M == batch_size` semantics;
- bounded P7 conservative PES and full locked lifecycle;
- owner-driven storage and the legitimate empty prepared/frame archive plan;
- the earlier exact-boundary no-checkpoint-yet versus corrupt-continuation invariant.

No second cache, refcount database, checkpoint registry, lifecycle authority, position registry, batch policy, or storage mutation path is justified.

## 3. Closure criterion

This amendment may close when the shared component-position reader rejects malformed current locators instead of reinterpreting them as legacy/direct payload, any intentionally supported legacy form has an explicit validated discriminator, the focused qualification-observation regressions pass on the exact executable candidate, and no previously closed R2 behavior regresses.
