---
kind: implementation-repair-workplan
workplan_id: CODE-MLFF-P5-SINGLE-SOURCE-REPLAY-LINEAGE-ADAPTER-REPAIR
protocol_version: 5.8.0
status: active
created_date: 2026-09-08
baseline_branch: main
baseline_commit: d6f5338b21a792420bf363fc858be8d4a39a5f71
implementation_branch: fix/mlff-p5-single-source-replay-lineage-adapter
scope: bounded P5 implementation nonconformance
primary_owner: mdstats/training_data/campaign_post_selection_runtime.py
parent_authority: workplans/archive/mlff-target-size-v7-packages/P5_POST_SELECTION_CV_FINAL_PRODUCTION.md
compatibility_policy: current-generation-cutover-no-derived-migration
---

# MLFF P5 single-source replay-lineage adapter repair

## 0. Purpose and authority

This workplan corrects one bounded implementation defect in the post-selection cross-validation replay-lineage adapter. It does **not** redesign replay science, target-size selection, multi-size selection, CV acceptance, final production, persistence authority, or the fail-closed lineage model.

The frozen scientific and architectural authority remains the current mdstats MLFF design and, specifically for this surface, `workplans/archive/mlff-target-size-v7-packages/P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` revision 11 and its retained revision-10 lineage requirements.

The implementation baseline is:

```text
d6f5338b21a792420bf363fc858be8d4a39a5f71
```

The defect is classified as a **first-order local integration nonconformance with a clean owning-layer cause**. The repair must therefore alter the existing adapter wiring rather than adding a compatibility shim, fallback, wrapper, duplicated identity object, or new replay-lineage machinery.

Do not reopen frozen architecture unless implementation evidence contradicts the diagnosis or reveals that the canonical single-source replay context no longer owns the source and split artifacts described below.

---

## 1. Product and scientific invariants that must remain unchanged

The repair must preserve all existing P5 invariants, including:

1. P4/CampaignStore remains the sole current selected-target authority.
2. Cross-validation runs only from a current frozen selected binding.
3. Replay training exposure and independent TRUE_DFT replay admissibility remain distinct scientific roles.
4. `PostSelectionReplayResolution` remains transport only; it does not become scientific authority.
5. `compute_replay_lineage_digest()` remains fail-closed.
6. Single-source replay lineage continues to require all of:

```text
source_content_digest
source_sha256
split_manifest_digest
```

7. No path may become scientific lineage identity.
8. Source SHA may not substitute for missing canonical source content identity.
9. CV binds replay lineage; final production and restart must re-resolve and exactly reauthenticate that lineage.
10. `current-generation-cutover-no-derived-migration` remains in force: no inferred interface, implicit defaults, helper-shape compatibility fallback, or upgrade-by-assumption.
11. Multi-size target selection remains an ordered collection of independent `(N_selected, H_cv, H_prod)` bindings sharing only the scientifically common replay authority where designed.
12. Full long-running GPU/production qualification remains deferred to the established final-release/user-machine qualification stage; this bounded repair requires only focused CPU-safe semantic, regression, and integration evidence.

---

## 2. Observed failure

A valid post-selection cross-validation invocation with two manually selected sizes reaches the P5 replay-lineage resolver and fails before meaningful fold execution:

```text
PostSelectionError:
Single-source replay lineage requires source content digest,
source SHA256, and split manifest digest.
```

The relevant run had two frozen selected bindings, e.g. sizes `512` and `8192`. The multi-size state is not itself the defect: the failure occurs in shared single-source replay-lineage resolution and can affect a replay-enabled single-size CV path as well.

The preceding MACE/PyTorch legacy TorchScript warnings are not causal. The fatal exception is mdstats' own fail-closed lineage validator rejecting an incompletely populated transport object.

---

## 3. Diagnosis and root cause

### 3.1 Canonical producer shape

`_campaign_cli_core._single_source_replay_context(cfg, paths)` builds a canonical runtime context whose top-level scientific artifacts include conceptually:

```python
context = {
    "config": single,
    "source": source,
    "source_index": source_index,
    "true_cache": true_cache,
    "split": split,
    ...
    "plan": plan,
    "true_resolution": true_resolution,
    "records": records,
}
```

The same function also builds a nested persistence-record map such as:

```python
records = {
    "replay_single_source_config": single,
    "replay_source": source,
    "replay_true_label_cache": true_cache,
    "replay_split_manifest": split,
    ...
}
```

The `records` keys are persistence names. They are not the top-level runtime-context API.

### 3.2 Broken adapter wiring

`campaign_post_selection_runtime._resolve_post_selection_replay_resolution()` correctly obtains the real single-source context and reads other top-level runtime owners such as `plan` and `true_resolution`, but then reads the source and split artifacts using persistence-record names at the wrong nesting level:

```python
source_art = single_ctx.get("replay_source")
split_manifest = single_ctx.get("replay_split_manifest")
```

Those lookups return `None` because the canonical top-level keys are `source` and `split`.

The adapter therefore constructs `PostSelectionReplayResolution` with missing mandatory single-source lineage fields:

```text
source_content_digest = None
source_sha256 = None
split_manifest_digest = None
```

`compute_replay_lineage_digest()` then correctly rejects the incomplete resolution.

### 3.3 Defect classification

This is an implementation integration defect at the P5 adapter boundary:

```text
_single_source_replay_context()
    -> _resolve_post_selection_replay_resolution()
    -> compute_replay_lineage_digest()
```

The validator is behaving correctly. The producer already exposes the required canonical scientific artifacts. No additional authority or data model is required.

---

## 4. Frozen repair strategy

### 4.1 Required owning-layer rewire

Repair only the erroneous adapter lookups so the existing canonical runtime-context owners feed the existing transport:

```diff
- source_art = single_ctx.get("replay_source")
- split_manifest = single_ctx.get("replay_split_manifest")
+ source_art = single_ctx["source"]
+ split_manifest = single_ctx["split"]
```

Strict indexing is preferred because a successfully constructed single-source replay context is required to own these artifacts. If the producer contract regresses in the future, the adapter should fail immediately at the boundary rather than silently converting mandatory scientific identity into `None` and deferring the failure to the lineage validator.

The exact local variable names may change if current source has drifted, but the semantic rule is frozen:

```text
P5 single-source replay resolution must consume the canonical
runtime-context source and split artifacts directly from their actual owner.
```

### 4.2 Explicitly forbidden repairs

Do **not**:

- weaken or bypass `compute_replay_lineage_digest()`;
- make missing single-source source/split lineage optional;
- substitute `source_sha256` for `source_content_digest`;
- derive split lineage from train/monitor materializations;
- infer single-source lineage from filesystem paths;
- special-case the two-size or multi-size path;
- add a compatibility helper that checks both old and new key names;
- reach into `single_ctx["records"]` merely to preserve the mistaken persistence-record vocabulary;
- duplicate `source` or `split` into new context aliases;
- create a new replay-resolution wrapper, lineage cache, translation layer, migration layer, or adapter class;
- mutate frozen scientific/architectural documentation to accommodate the defect.

If implementation drift means the canonical top-level `source` or `split` owner no longer exists, stop and return to Software Design review rather than inventing a fallback.

---

## 5. Expected affected surface

Primary executable owner:

- `mdstats/training_data/campaign_post_selection_runtime.py`

Likely regression/acceptance tests:

- `tests/test_mlff_replay_unify1d.py`
- `tests/test_mlff_target_size_p5_r10_guards.py`
- `tests/test_mlff_target_size_multi_size_integration.py`
- other narrowly affected P5 replay/CV tests only if current repository structure requires them.

No production data schema, persisted wire format, CLI syntax, method identity definition, lineage digest definition, or architecture-manual change is expected.

---

## 6. Implementation stage

### R1 — rewire canonical single-source replay artifacts into P5 resolution

This repair is one coherent stage.

#### Required code changes

1. Inspect the current `_single_source_replay_context()` producer and confirm the canonical top-level owners for source artifact and split manifest are still `source` and `split` or their direct current equivalents.
2. Inspect `_resolve_post_selection_replay_resolution()` and replace only the incorrect persistence-record-name lookups with the canonical runtime-context owners.
3. Prefer fail-fast direct access for mandatory context members.
4. Preserve all existing construction of:
   - replay interface;
   - train artifact;
   - monitor artifact;
   - training label mode;
   - TRUE_DFT label mode;
   - true-label source identity;
   - method identity;
   - lineage digest.
5. Make no changes to validator permissiveness or digest semantics.

#### Semantic closure check

After the edit, source inspection must establish:

```text
single-source context producer owns source + split canonically
P5 adapter reads those exact owners
PostSelectionReplayResolution carries their canonical content identities
compute_replay_lineage_digest remains unchanged and fail-closed
no compatibility aliases/fallbacks were added
no path-derived lineage was added
```

---

## 7. Regression and acceptance obligations

Tests must close the real integration seam rather than only exercising synthetic already-populated resolution objects.

### 7.1 Real single-source TRUE_DFT lineage path

Using a bounded real single-source replay fixture/context:

1. construct the real `_single_source_replay_context()`;
2. call the real `_resolve_post_selection_replay_resolution()`;
3. assert:

```python
resolution.source_content_digest == single_ctx["source"].content_digest
resolution.source_sha256 == single_ctx["source"].sha256
resolution.split_manifest_digest == single_ctx["split"].content_digest
```

4. pass the resulting resolution to `compute_replay_lineage_digest()` and require success.

This test must fail under the pre-repair lookup bug.

### 7.2 Foundation-pseudolabel single-source path

Exercise the supported bounded pseudolabel replay path and verify:

- replay training artifact remains foundation pseudolabel;
- independent monitor remains TRUE_DFT;
- canonical source/split lineage is complete;
- lineage digest succeeds without changing semantic label ownership.

### 7.3 Restart/currentness stability

Clear any relevant in-process unified replay context cache through the existing accepted test seam, reconstruct the context, and establish that unchanged source bytes/configuration/split produce the same replay-lineage digest.

Do not add a new cache or restart mechanism for this test.

### 7.4 Mutation invalidation

Existing or minimally extended guards must establish that changing scientifically relevant source bytes or split membership/configuration changes the authenticated lineage and invalidates stale descendants as already designed.

Do not weaken this counterfactual merely to make the repaired path pass.

### 7.5 Multi-size admission regression

Run a bounded cross-validation admission path with at least two frozen selected sizes and verify:

- shared replay lineage resolves successfully before/for the per-size CV orchestration as current design requires;
- both selected entries retain their independent `(N_selected, H_cv, H_prod)` bindings;
- no multi-size special-case lineage logic is introduced;
- the repaired shared replay resolution is identical in scientific identity for the same replay source/split.

This is regression coverage for the observed trigger, not a redesign of multi-size selection.

---

## 8. Minimum test execution

At minimum execute the focused affected surface:

```bash
pytest -q \
  tests/test_mlff_replay_unify1d.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_multi_size_integration.py
```

Then execute the broader bounded P5 guard surface:

```bash
pytest -q tests/test_mlff_target_size_p5_*.py
```

If current file names differ, select the equivalent current tests covering the same owners and report the exact commands actually run.

If the implementation change unexpectedly affects replay persistence, final-production reauthentication, CampaignStore currentness, or other P5 owners, re-derive the affected surface and expand regression accordingly. Do not mask unrelated failures.

Long production/GPU qualification is not required for this bounded adapter repair.

---

## 9. Acceptance criteria

The repair is implementation-complete only when all are true:

```text
[ ] canonical single-source producer contract inspected
[ ] P5 adapter consumes canonical source artifact owner directly
[ ] P5 adapter consumes canonical split manifest owner directly
[ ] mandatory source_content_digest is populated from canonical source
[ ] mandatory source_sha256 is populated from canonical source
[ ] mandatory split_manifest_digest is populated from canonical split
[ ] compute_replay_lineage_digest remains fail-closed and unchanged in permissiveness
[ ] TRUE_DFT and pseudolabel replay semantics remain distinct
[ ] real producer -> adapter -> digest integration test passes
[ ] source/split mutation still invalidates lineage as designed
[ ] restart/currentness re-resolution remains stable for unchanged inputs
[ ] bounded two-size CV admission no longer fails at replay-lineage resolution
[ ] no path-based identity added
[ ] no compatibility fallback, wrapper, alias layer, or duplicated authority added
[ ] focused affected regression passes
[ ] broader bounded P5 regression passes
```

---

## 10. Review gate and reopen triggers

After implementation, run an independent Software Design review against this workplan and the retained P5 authority.

**PASS** only if the implementation is an owning-layer rewire with complete real-boundary regression evidence and no weakening of lineage science.

Reopen design only if repository evidence establishes one of the following:

1. `_single_source_replay_context()` no longer canonically owns source/split scientific artifacts;
2. multiple competing owners for source or split identity exist and cannot be resolved by removing/rewiring one;
3. the same persistence-name/runtime-name confusion is repeated broadly enough to indicate an architectural boundary failure rather than this local defect;
4. fixing the adapter exposes an actual contradiction between replay lineage requirements and executable replay semantics;
5. current persisted compatibility obligations require a scientific identity migration not covered by the existing current-generation cutover policy.

Absent one of those triggers, do not expand the solution beyond the local repair and its regression coverage.

---

## 11. Handoff summary

### Product invariant

Post-selection CV and final production must authenticate replay provenance exactly and fail closed when required scientific identity is absent.

### Frozen architecture

The canonical single-source replay builder owns source/split artifacts; P5 transports those identities into `PostSelectionReplayResolution`; `compute_replay_lineage_digest()` authenticates them; CV/final descendants bind the resulting lineage.

### Delegated implementation solution

Correct the two adapter lookups to consume the existing canonical top-level runtime-context artifacts directly, with fail-fast mandatory access.

### Required proof

Exercise the real producer→adapter→lineage-digest boundary for TRUE_DFT and pseudolabel replay, preserve tamper/currentness guards, and reproduce a bounded multi-size CV admission without the prior lineage exception.

### Unresolved risk

No architectural risk is presently identified. The only expected implementation risk is test fixture drift that may have hidden the incorrect adapter nesting; resolve that by making tests follow the real ownership chain rather than by adding compatibility behavior to production code.
