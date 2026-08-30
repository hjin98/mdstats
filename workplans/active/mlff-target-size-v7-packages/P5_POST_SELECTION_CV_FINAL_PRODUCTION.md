---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 8
amended_date: 2026-08-30
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision7_implementation_baseline_commit: d1575a26426339d67c856ed0d66ea3e394bba30a
revision6_implementation_baseline_commit: 81e72cdb22cdbfddae0508592b2b38b3f80aae2f
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Independent review of revision-7 implementation found a bounded set of P5-local implementation nonconformances. The qualified TRAIN2 launch path is substantially repaired, but the new real-owner paths contain two hard runtime import failures; canonical foundation inspection still fails open to an uninspected byte-only identity; replay scientific policy still hashes path spelling; retained method fields are not yet all consumed by execution; and scientific input bytes are not all reauthenticated at the final pre-launch boundary. Revision 8 freezes exact corrections and real-owner acceptance so implementation does not need to infer how to close these defects.
---

# P5 revision 8 — fail-closed identity, execution parity, and pre-launch authentication closure

## 0. Authority, scope, and precedence

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific and architectural verdict. P5 remains bound to Protocol 5.8.0. Revision 8 supersedes prior P5 revisions as the current implementation handoff. Prior P5 requirements remain binding unless this revision explicitly replaces their realization.

The implementation baseline under correction is:

```text
d1575a26426339d67c856ed0d66ea3e394bba30a  P5A2
```

This is a bounded implementation repair. Do not reopen P1-P4, target-size science, selected-set semantics, the P1 split-exclusion authority, CV acceptance science, replay-retention science, M3's role, or final-production freshness.

The following P5 semantics are frozen and must remain true:

- P4 CampaignStore/current-terminal authority is the only current `N_selected/T_selected` owner.
- `T_selected = pi_train[:N_selected]` exactly; replay, CV, M3, or final production may not widen or redefine it.
- CV occurs only after selection, uses configured `K >= 2`, exact selected-only coverage, and the full canonical P1 split-exclusion/protected-relation projection.
- Every required fold and required CV seed/variant must pass. Mean, majority, best-seed, partial-fold, K0/K1, and `cv_not_performed` authorization are forbidden.
- Held-out outer CV target data may not influence fitted preparation, training, checkpoint selection, or replay admissibility for that fold.
- Replay and physical evidence are hard admissibility/diagnostic evidence only. They may reject a checkpoint but receive zero target-ranking, tie-breaking, fold-acceptance, seed-ranking, committee-ranking, or target-size-selection credit.
- M3 remains development/model-selection evidence only, not independent validation.
- Final production is fresh from full exact `T_selected`, with fresh optimizer/RNG/run state and no continuation from screening/CV checkpoints or optimizer state.
- `[training].max_num_epochs` is final-production-only horizon authority and remains independent of target-size `n3` and CV budget.
- Screen/CV/final namespaces and restart/evidence identities remain collision-proof.
- Policy -> plan -> realized evidence remains acyclic; CV/final evidence may not backflow into P4 authority.
- Full production/GPU qualification remains deferred. Bounded functional, regression, and integration tests are mandatory now.

P6 remains blocked until revision 8 reaches semantic closure, functional closure, and independent P5 review pass.

---

## 1. Exact revision-7 defects to repair

### 1.1 Two hard runtime failures

At baseline `d1575a2`:

- `mdstats/training_data/post_selection_identity.py` calls `Path(...)` in the new foundation/replay identity path but does not import `Path`.
- `mdstats/training_data/campaign_post_selection_runtime.py` calls `hashlib.sha256(...)` in replay-monitor authentication but does not import `hashlib`.

These are not test-only defects. They lie on the real non-scratch/replay-enabled execution path.

**Required correction:**

- add `from pathlib import Path` to `post_selection_identity.py`;
- do **not** add another ad-hoc whole-file `hashlib.read_bytes()` implementation to the runtime. Import and use the repository's canonical `sha256_file_cached` helper from `._common` for replay/foundation/artifact authentication. The trainer/runtime may still use `hashlib` for small in-memory config bytes if already appropriate, but scientific file authentication should use the shared file-hash owner.

### 1.2 Foundation identity still fails open

The baseline `resolve_post_selection_foundation_identity()` attempts canonical `inspect_mace_foundation()` + `MaceFoundationSpec.resolve()`, but catches every exception and falls back to `FoundationPotentialIdentity.from_file()`.

That fallback is forbidden for current P5 authorization. It can hide:

- corrupt or unsupported checkpoints;
- missing MACE/torch inspection capability;
- wrong configured foundation family;
- unavailable selected head;
- ambiguous multi-head checkpoint with no explicit head;
- any future canonical compatibility rejection.

A byte hash alone is not sufficient current P5 scientific identity.

### 1.3 Replay shared method identity still contains path spelling

The baseline uses `ReplaySingleSourceConfig.content_digest` for `replay_exposure_policy_digest`. That digest includes `replay_set_path`. The legacy branch also hashes replay path strings.

This violates the frozen separation:

```text
shared method identity = replay semantics/policy
plan lineage          = exact authenticated replay bytes/split/views
runtime locator       = filesystem path only
```

Relocating identical replay input must not invalidate accepted scientific method identity.

### 1.4 Identity -> execution parity is still incomplete

The optimizer-family defect was corrected, but the audit stopped early.

At baseline:

- `resolve_shared_optimizer_settings()` includes `eval_interval` in the shared method digest;
- canonical `MaceOptimizerPolicy` also owns `eval_interval`;
- `_post_selection_mace_config()` does not emit it;
- `_MACE_CONFIG_PASSTHROUGH_KEYS` does not pass it to MACE.

Therefore an `eval_interval` mutation can change the validated method identity without changing the executable MACE job.

Acceleration needs the same closure. The repository already owns `MaceAccelerationPolicy.training_config()` (`enable_cueq`, `only_cueq`) and `MaceOptimizerPolicy.acceleration_policy`; P5 must route that established owner, not maintain an identity-only backend string.

### 1.5 Final pre-launch byte authentication is incomplete

Revision 7 correctly authenticates the internal P5 config and replay TRUE_DFT monitor in the trainer, but the final launch boundary does not yet authenticate every scientific file MACE will consume.

Before the wrapper process starts, the trainer must know and authenticate:

- target training ExtXYZ;
- target validation/checkpoint-monitor ExtXYZ;
- configured foundation checkpoint for non-scratch methods;
- replay training ExtXYZ for multihead replay;
- replay monitor ExtXYZ when exposed to MACE/TRAIN2;
- the exact TRUE_DFT replay monitor SHA bound by `Train2RuntimePlan`.

No subprocess may start first and discover a mismatch later during EVAL2.

---

## 2. Frozen correction design

### 2.1 Canonical foundation resolution: exact required implementation

**Owning file:** `mdstats/training_data/post_selection_identity.py`

Replace the current fallback resolver with a strict resolver equivalent to:

```python
def resolve_post_selection_foundation_identity(
    path,
    *,
    requested_head=None,
    model_family="MACE-MPA-0",
):
    if path is None or not str(path).strip():
        return None

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise TrainingDataInputError(
            f"Foundation checkpoint does not exist: {source}."
        )

    from .foundation import MaceFoundationSpec, inspect_mace_foundation

    inspection = inspect_mace_foundation(source)
    identity = MaceFoundationSpec(
        family=model_family,
        requested_head=requested_head,
    ).resolve(inspection)

    if identity.inspection_state != "inspected":
        raise TrainingDataInputError(
            "Current P5 requires an inspected canonical foundation identity."
        )
    return identity
```

The exact spelling may differ, but all semantics above are mandatory.

**Forbidden:**

```python
except Exception:
    return FoundationPotentialIdentity.from_file(...)
```

Do not catch canonical inspection/family/head errors merely to continue. If adding context, catch only a known exception type and re-raise with the original exception chained.

#### Head resolution

In `resolve_post_selection_method_policies()` do not convert a missing configured head to the literal string `"default"` before inspection.

Resolve input as:

```text
explicit non-empty configured foundation head -> requested_head=<that head>
omitted/empty foundation head                -> requested_head=None
```

Then let `MaceFoundationSpec.resolve()` own the rule:

- singleton checkpoint + omitted head -> canonical singleton head;
- multi-head checkpoint + omitted head -> fail closed;
- explicitly unavailable head -> fail closed.

After resolution, set runtime `foundation_head` from `foundation_identity.foundation_head`, not from the pre-inspection input string.

For non-scratch methods, `foundation_potential_identity` must be non-null and inspected before CV plan construction. Scratch is the only valid no-foundation case.

### 2.2 Foundation runtime locator versus scientific identity

Keep the resolved absolute checkpoint path as a runtime locator only:

```text
PostSelectionMethodPolicies.foundation_model = resolved path
PostSelectionMethodPolicies.foundation_head  = canonical resolved head
```

Scientific identity remains:

```text
foundation_identity.canonical_content_digest
```

`TargetSizeCommonTrainingPolicy.foundation_checkpoint_digest` and `PostSelectionMethodIdentity` must bind that content identity.

Required exact invariants:

```text
same valid checkpoint bytes + same canonical head, path A -> path B
    same PostSelectionMethodIdentity

same path, changed checkpoint bytes
    changed/failing PostSelectionMethodIdentity; old CV cannot authorize final

same checkpoint, different valid canonical head
    different PostSelectionMethodIdentity

wrong family / unavailable head / corrupt checkpoint / inspection unavailable
    pre-training failure
```

### 2.3 Path-free replay method policy identity

**Owning file:** `post_selection_identity.py`

Introduce one private or public helper for the shared replay-policy digest. Do not reuse `ReplaySingleSourceConfig.content_digest` directly because that record intentionally contains the source locator.

For canonical single-source replay, hash only the normalized semantic payload:

```python
{
    "schema": "mdstats.post-selection-replay-policy.v2",
    "enabled": True,
    "interface": "single_source",
    "training_exposure": "separate_multihead_replay",
    "training_label_mode": single_replay.label_mode.value,
    "split_ratio": list(single_replay.split_ratio),
    "split_seed": int(single_replay.split_seed),
    "true_dft_monitor_required": True,
    "target_head_name": resolved_target_head_name,
    "replay_head_name": "pt_head",
}
```

The payload must contain **no path** and no realized source/view SHA. Split ratio/seed remain here because they define the method's replay sampling policy; the exact resulting split membership belongs to plan lineage.

For replay disabled, use one stable no-replay policy digest containing only semantic `enabled=False`/`training_exposure="none"` state.

For supported legacy split-file replay:

- normalize the accepted legacy label/exposure semantics through existing config semantics;
- use `interface="legacy_split"` and the normalized semantic mode/role fields;
- do not hash `replay_train`, `replay_monitor`, `replay_true_labels`, or any other path;
- exact legacy file bytes/artifacts belong only to the plan lineage digest;
- if the legacy configuration cannot determine its semantic label/exposure mode unambiguously, reject it before training rather than using path spelling as identity.

### 2.4 Exact replay lineage: fail closed and path independent

The current `compute_replay_lineage_digest()` is too permissive because it uses `getattr(..., None)` and silently catches source-hash failures.

Replace it with a strict lineage resolver/builder. It may remain named `compute_replay_lineage_digest`, but the implementation must validate required fields before hashing.

For canonical single-source replay the plan lineage payload must contain:

```text
schema = mdstats.post-selection-replay-lineage.v2
interface = single_source
ReplaySourceArtifact.content_digest
ReplaySourceArtifact.sha256
ReplaySplitManifest.content_digest
replay training view/artifact content or logical digest
replay training file SHA256
TRUE_DFT replay monitor view/artifact content or logical digest
TRUE_DFT replay monitor file SHA256
TRUE_DFT label mode
```

Use existing persisted/current canonical replay owners where necessary. If the current `_resolve_true_label_replay_inputs()` result does not expose source/split identities directly, add a small adapter that also loads the already-owned current `ReplaySourceArtifact` and `ReplaySplitManifest` from the campaign authority/store. Do not reconstruct the split algorithm inside P5.

For supported legacy pre-split replay, there is no synthetic single-source/split authority to invent. Bind:

```text
interface = legacy_split
canonical train artifact/content digest + train SHA256
canonical TRUE_DFT monitor artifact/content digest + monitor SHA256
canonical separate true-label artifact identity if the legacy owner exposes one
normalized legacy replay semantic mode
```

No lineage payload may include a filesystem path.

**Failure behavior:** missing source/split/view identity that is required for the active interface is `PostSelectionError`/`TrainingDataInputError`. There is no `try/except: pass`, no `None` placeholder that weakens identity, and no fallback to a path hash.

Required invariants:

```text
same replay bytes + same replay policy + same split, relocated
    same method identity and same replay lineage

same path, source bytes changed
    replay lineage changes/fails; accepted CV cannot authorize final

split seed/ratio/membership changed
    method and/or replay lineage changes as appropriate; accepted CV cannot authorize final

TRUE_DFT monitor bytes changed
    replay lineage changes/fails and TRAIN2 launch is rejected
```

### 2.5 Finish identity -> execution parity; do not remove supported fields

Revision 8 freezes the disposition of the known retained fields so the implementer does not need to choose between removal and routing.

#### `eval_interval`: ROUTE IT

`MaceOptimizerPolicy` already owns `eval_interval`, so this is a supported control.

In `_post_selection_mace_config()` add:

```python
"eval_interval": int(optimizer_policy.eval_interval),
```

In `_MACE_CONFIG_PASSTHROUGH_KEYS` add:

```text
eval_interval
```

The resulting `mace_run_config.yaml` must contain the exact resolved value.

#### acceleration backend: ROUTE THE CANONICAL POLICY

Do not add a new acceleration abstraction.

Use the existing `MaceAccelerationPolicy` and `MaceOptimizerPolicy.acceleration_policy` owners.

Required behavior:

1. `resolve_post_selection_method_policies()` must normalize the P5 method's backend through `MaceAccelerationPolicy`, not by retaining an unchecked free-form string.
2. The method identity's `acceleration_backend` must equal the canonical acceleration policy's `backend.value`.
3. `_optimizer_policy_for()` must produce a `MaceOptimizerPolicy` whose `acceleration_policy.backend.value` equals `context.method.acceleration_backend`. Add an explicit fail-closed assertion before materialization/training if they differ.
4. `_post_selection_mace_config()` must merge:

```python
optimizer_policy.acceleration_policy.training_config()
```

which currently supplies `enable_cueq` and `only_cueq`.
5. Add `enable_cueq` and `only_cueq` to `_MACE_CONFIG_PASSTHROUGH_KEYS` so the translated executable MACE config actually receives them.
6. Do not reinterpret CuEq/OEQ realization policy in P5. Existing acceleration qualification/realization owners continue to govern whether the requested backend is usable.

#### checkpoint interval: KEEP CURRENT ROUTING

`checkpoint_interval_epochs` is already consumed through `cv_training_budget_policy()` / `final_production_training_budget_policy()` -> `TrainingBudgetPolicy` -> `Train2RuntimePlan`. Preserve this path and add a parity test rather than adding another MACE config knob.

#### dtype: FAIL CLOSED

Current P5 silently coerces an unsupported dtype to `float64`. Replace this with `TrainingDataInputError`.

Accepted current values are exactly:

```text
float32
float64
```

No unsupported dtype may silently change the method being validated.

#### training mode: FAIL CLOSED

After normalization, accepted P5 modes are exactly:

```text
scratch
naive_fine_tuning
multihead_replay
```

Reject any other explicit value before expensive work.

#### complete retained-field audit

After the concrete fixes above, inspect every field serialized by `PostSelectionMethodIdentity._payload()` and every component digest it references. For each field, record one source-level consumer in test comments or the implementation review notes; do not create a new persistent registry.

A retained scientific/configuration field is acceptable only if:

```text
mutation -> real owner/executable semantics change
or
mutation -> explicit pre-training rejection
```

A material executable method change is acceptable only if the corresponding method identity changes/rejects stale CV.

### 2.6 One final pre-launch scientific-file authentication boundary

**Owning file:** `mdstats/training_data/post_selection_execution.py`

Extend `PostSelectionRungRequest` so `MacePostSelectionTrainer` receives enough canonical identity to authenticate every file the child will consume. Prefer passing the existing identity/artifact objects rather than duplicating independent SHA state.

Required request additions, names may vary but semantics may not:

```text
foundation_identity: FoundationPotentialIdentity | None
foundation_model_path: Path | None
replay_train_artifact: canonical replay artifact | None
replay_train_path: Path | None
replay_monitor_artifact: canonical replay artifact | None
replay_monitor_path: Path | None
```

`execute_post_selection_run()` must populate those fields directly from `context.method_policies` and the one canonical replay resolution already used for materialization/runtime-plan construction.

Before `subprocess.run(...)`, `MacePostSelectionTrainer.__call__()` must authenticate, in this order:

1. internal P5 config bytes/digest/schema;
2. target training ExtXYZ at `materialization_directory / target_train_artifact.relative_path` against the artifact's recorded SHA;
3. target validation/checkpoint-monitor ExtXYZ against its recorded SHA;
4. for non-scratch methods, foundation path exists and `sha256_file_cached(path) == foundation_identity.sha256`;
5. if internal config contains a foundation locator/head, they must agree with the request's canonical locator and `foundation_identity.foundation_head`;
6. for `multihead_replay`, replay train path/artifact are present and file SHA matches the canonical artifact;
7. when replay monitor is passed to MACE/TRAIN2, replay monitor path/artifact are present and file SHA matches the canonical artifact;
8. when `request.plan.replay_monitor_enabled`, the same replay monitor SHA must also equal `request.plan.true_replay_monitor_sha256`;
9. only after all checks pass may the executable config be written/used and the wrapper subprocess start.

Use `sha256_file_cached`; do not `read_bytes()` multi-GB scientific files merely to hash them.

If any identity/path disagreement occurs, raise `PostSelectionExecutionError` before process launch.

The trainer does not need to authenticate outer-evaluation data because MACE training does not consume it. EVAL2's existing artifact owner remains responsible when outer evaluation is read.

### 2.7 Preserve the revision-7 TRAIN2 corrections

Do not regress the already-corrected path:

- internal P5 config is authenticated;
- `post_selection_mace_run_configuration()` is the one internal->MACE translation owner;
- `mace_run_config.yaml` (or equivalent version-agnostic executable file) is passed to `mdstats-mace-train`;
- wrapper cwd is the materialization directory unless every artifact path is absolute;
- child environment copies `os.environ` and sets `MDSTATS_TRAIN2_RUNTIME_PLAN`;
- `PYTHONHASHSEED` equals the optimizer seed;
- replay-enabled run sets `MDSTATS_TRAIN2_TRUE_REPLAY_PATH` to the exact authenticated TRUE_DFT monitor;
- replay runtime plan carries the exact monitor SHA;
- wrapper nonzero exit fails closed;
- successful wrapper must yield canonical `load_train2_runtime_summary(request.checkpoint_directory)` evidence;
- summary plan/optimizer/budget/LR/structure geometry remains authenticated before checkpoint evaluation;
- existing wrapper signal/completion supervision remains authoritative.

---

## 3. Implementation sequence

### P5-R8A — hard failures + fail-closed scientific identity

**Expected files**

- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/campaign_post_selection_runtime.py`
- `mdstats/training_data/post_selection_cv_plan.py` / `post_selection_production.py` only if strict lineage validation requires a signature adjustment
- tests

**Required edits**

1. Fix missing imports/use canonical file hashing.
2. Remove foundation broad fallback and require inspected canonical identity.
3. Resolve omitted versus explicit foundation head correctly; runtime head comes from canonical identity.
4. Replace path-containing replay policy digest with the path-free semantic payload.
5. Replace permissive replay lineage helper with strict, path-independent authenticated lineage.
6. Reject invalid dtype and invalid training mode.

**R8A focused tests must call the real owners:**

- import/execute `resolve_post_selection_foundation_identity()`; do not test only `FoundationPotentialIdentity.from_file()`;
- invalid/corrupt model must raise from canonical inspection, proving no byte-only fallback;
- existing real MACE checkpoint fixture: relocation retains canonical P5 method identity;
- same valid checkpoint with changed bytes invalidates/fails;
- multi-head fixture with omitted head fails; explicit valid heads resolve distinctly;
- real canonical replay campaign moved from source path A to B with same bytes/policy/split gives same shared method identity and same plan lineage;
- replay source byte mutation at same path changes/fails lineage;
- split seed/ratio change changes method policy and realized lineage as appropriate;
- direct execution of the real replay-enabled runtime authentication line must not raise `NameError` and must reject a bad SHA.

Run affected foundation/replay/P5 identity/CV-plan/final-plan regression before R8B.

### P5-R8B — executable parity + final pre-launch authentication

**Expected files**

- `mdstats/training_data/post_selection_execution.py`
- `mdstats/training_data/campaign_post_selection_runtime.py`
- `post_selection_identity.py` only for canonical acceleration normalization
- tests

**Required edits**

1. Route `eval_interval` into internal P5 config and translated MACE config.
2. Route canonical `MaceAccelerationPolicy.training_config()` into the executable MACE config and enforce identity/backend equality with the per-run `MaceOptimizerPolicy`.
3. Extend `PostSelectionRungRequest` with foundation/replay identity artifacts/paths.
4. Authenticate target train, target monitor, foundation, replay train, replay monitor, and runtime TRUE_DFT SHA before subprocess launch.
5. Preserve all already-correct revision-7 TRAIN2 launch/summary behavior.

**R8B production-trainer contract test**

Use the real `MacePostSelectionTrainer`. A deterministic fake wrapper executable is allowed because the external numerical MACE process is below the owner under acceptance. The test must capture the executable config/environment/cwd and whether the wrapper was invoked.

It must prove:

- executable config contains `eval_interval` exactly;
- e3nn policy produces `enable_cueq=false` with the canonical `only_cueq` value;
- cueq policy produces the canonical acceleration training config when that policy is constructible in the bounded fixture;
- method backend and optimizer backend mismatch fails before wrapper launch;
- target train SHA mismatch -> wrapper invocation count remains zero;
- target monitor SHA mismatch -> zero launches;
- foundation SHA mismatch -> zero launches;
- replay train SHA mismatch -> zero launches;
- replay monitor SHA mismatch -> zero launches;
- runtime-plan TRUE_DFT SHA mismatch -> zero launches;
- valid inputs -> exactly one wrapper launch;
- wrapper receives translated config, exact TRAIN2 environment, exact cwd, and canonical summary loading remains required.

Run affected MACE config, MaceOptimizerPolicy, acceleration, TRAIN2 runtime/wrapper, DATA8/post-selection materialization, and provider regressions before R8C.

### P5-R8C — assembled real-owner closure

Create or repair one bounded assembled test that traverses the production P5 owner chain rather than manufacturing authorization inputs.

Required path:

```text
real campaign config
 -> real CampaignStore/current P4 SELECTED authority
 -> real resolve_post_selection_method_policies
 -> real canonical foundation inspection/spec/head resolution
 -> real canonical replay source/split/TRUE_DFT resolution
 -> real path-free PostSelectionMethodIdentity
 -> real authenticated replay_lineage_digest
 -> real CV plan/folds from selected + P1 relation authority
 -> real fold preparation/materialization
 -> real Train2RuntimePlan
 -> real MacePostSelectionTrainer config/env/pre-launch authentication
 -> fake only the expensive external MACE numerical work
 -> real canonical TRAIN2 summary/checkpoint authentication
 -> real EVAL2 decision path
 -> candidate replay + canonical foundation baseline on the same TRUE_DFT monitor
 -> real target-only representative selection
 -> real held-out outer acceptance
 -> real all-required CV campaign acceptance
 -> real final-plan method/replay-lineage reauthentication
 -> fresh full-T_selected final orchestration
 -> real M3 development selection semantics
 -> real currentness-fenced publication
 -> fresh-process/reopened-store restart authentication
```

Allowed bounded fakes:

- external numerical MACE optimization;
- deterministic numerical prediction values below the real provider/evaluation orchestration boundary where needed for speed;
- tiny synthetic target/replay datasets.

Forbidden substitutions for the assembled claim:

- patching `resolve_post_selection_method_policies()` or foundation/replay identity resolvers;
- constructing `FoundationPotentialIdentity.from_file()` directly in place of P5 foundation resolution;
- precomputing `replay_lineage_digest` and injecting it into a plan;
- directly constructing `Eval2CheckpointRecord` replay metrics;
- replacing `MacePostSelectionTrainer` with `PostSelectionHarness` when claiming trainer orchestration/pre-launch authentication;
- seeding `CvCampaignAcceptance` or final authorization;
- replacing CampaignStore/currentness/restart ownership with a custom in-memory stand-in.

The assembled test must fail if either missing-import regression is reintroduced, if foundation inspection falls back, if replay paths enter scientific identity, if trainer pre-launch authentication is bypassed, or if CV->final replay/method currentness is broken.

---

## 4. Mandatory negative and parity matrix

Revision 8 is not closed unless all of these claims are protected by direct behavior or structural evidence:

1. real foundation resolver executes without missing imports;
2. corrupt/unsupported foundation cannot downgrade to byte-only identity;
3. wrong foundation family fails;
4. multi-head omitted head fails;
5. unavailable explicit head fails;
6. foundation relocation with same bytes/head preserves P5 method identity;
7. foundation bytes changed at same path invalidate/fail old method/CV;
8. replay shared method digest contains no filesystem path;
9. replay source relocation with same bytes/policy/split preserves method identity;
10. replay lineage contains no filesystem path;
11. replay source byte mutation invalidates CV->final authorization;
12. replay split seed/ratio/membership mutation invalidates the appropriate policy/lineage;
13. TRUE_DFT monitor byte mutation fails before training/evaluation;
14. invalid dtype rejects instead of coercing to float64;
15. invalid training mode rejects;
16. unsupported optimizer family remains rejected;
17. `eval_interval` mutation changes both method identity and executable MACE config;
18. checkpoint interval mutation changes method identity and TRAIN2 budget/checkpoint policy;
19. acceleration backend mutation changes method identity and canonical MACE acceleration training config/policy;
20. method acceleration backend cannot disagree with run optimizer acceleration backend;
21. target train artifact tamper blocks wrapper launch;
22. target monitor artifact tamper blocks wrapper launch;
23. foundation artifact tamper blocks wrapper launch;
24. replay train artifact tamper blocks wrapper launch;
25. replay monitor artifact tamper blocks wrapper launch;
26. runtime TRUE_DFT SHA/path mismatch blocks wrapper launch;
27. internal P5 config cannot be handed directly to MACE;
28. TRAIN2 runtime environment remains exact;
29. canonical TRAIN2 summary is mandatory after wrapper success;
30. canonical foundation replay baseline uses the canonical head and same TRUE_DFT monitor as candidate;
31. replay remains zero-credit to target ordering/ties/acceptance ranking;
32. held-out outer CV target data cannot select the checkpoint it evaluates;
33. all required folds/seeds remain mandatory;
34. M3 remains development/model-selection only;
35. production horizon remains independent from `n3` and CV budget;
36. current P4 generation race still rejects stale publication;
37. CV/final evidence cannot modify target-size authority;
38. restart reload reauthenticates method, foundation, replay lineage, selected binding, and final plan.

The implementer may combine related checks in fewer test functions. Do not create one test per list item merely for numbering.

---

## 5. Final affected-surface regression requirement

After all R8 executable changes, re-derive the affected surface from the assembled candidate. At minimum rerun the bounded tests covering:

- P5 revision-8 guards and assembled integration;
- prior P5 A-G / revision-6/revision-7 guards that still protect unaffected obligations;
- P4 selected/currentness and commit-time stale-generation fencing;
- generalized foundation identity/head inspection;
- replay single-source + supported legacy normalization, split, true-label view, pseudolabel exposure where applicable;
- common DATA7/DATA8 preparation/materialization affected by P5 reuse;
- `MaceOptimizerPolicy` and acceleration training config;
- TRAIN2 budget/LR/runtime/environment/checkpoint summary/provider authentication;
- EVAL2 target/replay admissibility and target-only ordering;
- CV plan/fold/acceptance;
- final production/M3/fresh-run semantics;
- persistence/restart/current pointer resolution;
- CLI/orchestrator entrypoints that invoke cross-validation/final production.

If impact cannot be bounded confidently after implementation, run the broader available MLFF training-data regression suite.

A green new guard file alone is not final acceptance. A required real-owner test that did not execute is not a pass.

No long GPU/data-heavy production qualification is required for P5 closure. Any target-machine GPU performance/resource qualification remains deferred to final release.

---

## 6. Implementation completion conditions

Implementation may mark P5 implemented only when all are true on one assembled candidate:

```text
semantic closure
  + no broad foundation fallback
  + path-free replay scientific identity
  + strict authenticated replay lineage
  + complete retained method identity -> execution parity
  + all scientific training inputs authenticated before wrapper launch
  + qualified TRAIN2 launch/summary path preserved
  + real replay candidate/foundation admissibility path preserved
  + stage-local affected regression passed
  + final affected-surface regression passed
  + assembled real-owner integration passed
```

Do not mark P5 implemented merely because the 38 negative/parity claims are represented in a test file. The production source path itself must satisfy them.

### Reopen-only-on-evidence triggers

Reopen Design only if repository evidence proves one of the following:

- canonical `MaceFoundationSpec` cannot represent the actually supported P5 foundation family/head semantics;
- canonical replay owners cannot expose stable source/split/view content identities without changing the replay architecture;
- MACE's accepted parser does not support `eval_interval` or the existing `MaceAccelerationPolicy.training_config()` despite current repository contracts claiming those controls;
- final pre-launch authentication cannot be performed without violating an existing immutable-artifact or wrapper ownership contract.

If none of those is proven, these are implementation repairs under this workplan, not redesign decisions.
