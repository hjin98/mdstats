---
kind: implementation-repair-workplan
package_id: CODE-MLFF-TARGET-SIZE-V7-MACE-EXECUTABLE-CONFIG-REPAIR
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
related_packages:
  - CODE-MLFF-TARGET-SIZE-V7-P3
  - CODE-MLFF-TARGET-SIZE-V7-P4
  - CODE-MLFF-TARGET-SIZE-V7-P5
protocol_version: 5.14.0
status: implementation-ready
created_date: 2026-09-04
reviewed_baseline_commit: 79c494cd68db836706295a449b5ef8e52d287cc8
reviewed_baseline_tree: d505ac8f752596d424387fabbd9208d0f1a22a69
trigger: real select-target-size Boundary-1 TRAIN2 launch exits 2 because MACE configargparse rejects structured atomic_numbers from the generated --config file
scope: mechanical MACE executable-configuration projection and affected P3/P4/P5 regression only; no target-size scientific or high-level architectural reopen
---

# MACE executable-config literal serialization repair

## 0. Disposition

**Design/workplan verdict: PASS / implementation-ready.**

The observed failure does not justify reopening target-size scientific design, P1/P2 statistical authority, configurable fidelity, TRAIN2 continuation semantics, P4 campaign/currentness ownership, P5 CV/final-production science, or P7 qualification architecture. It is a mechanical representation failure at the existing mdstats -> pinned-MACE execution boundary.

The repair must alter/reduce the faulty projection rather than add a retry, wrapper, compatibility fallback, second configuration authority, or special-case subprocess path.

Long GPU/production qualification remains deferred. This repair requires bounded functional regression and a real pinned-MACE parser boundary test.

---

## 1. Trigger and exact failure

A real `select-target-size` run restores DATA4 successfully and reaches Boundary 1 with 16 surviving `(N, optimizer seed)` cells. The first TRAIN2 candidate (`n=128`, `seed=1`, boundary `1`) exits before training with MACE/configargparse status 2:

```text
atomic_numbers can't be set to a list '[3, 8, 11, 13, 14, 19]'
unless its action type is changed to 'append' or nargs is set ...
```

`campaign_target_size_runtime.MaceTargetSizeBoundaryTrainer` then truthfully raises `TargetSizeRuntimeError` for the failed candidate rung.

The VASP interruption/velocity warnings and TorchScript deprecation warning in the same run are not causal for this failure and are outside this repair.

---

## 2. Root-cause reconstruction

### 2.1 Canonical mdstats representation is correct

The P3/P5 materialization owners intentionally store configuration as typed, JSON-safe scientific/execution data:

- `atomic_numbers` is a sorted list of integers;
- `E0s` is a mapping;
- candidate architecture contains structured fields such as `radial_MLP` and internal architecture metadata;
- P5 multihead configuration contains a structured `heads` mapping.

Those values participate in mdstats validation/digests and must remain structured. Converting the durable canonical configuration itself into MACE CLI strings would contaminate internal identity with one external parser syntax and would unnecessarily invalidate materialization/restart identities.

### 2.2 The existing executable projection is too literal

`campaign_target_size_runtime.mace_run_configuration(...)` currently:

1. copies selected top-level P3 values unchanged;
2. renames `target_train_file`/`target_valid_file`;
3. blindly flattens every key/value from canonical `mace_architecture` into the MACE run configuration;
4. writes that mapping to `mace_run_config.yaml` (currently JSON text, which is valid YAML) and passes it through `--config`.

`post_selection_execution.post_selection_mace_run_configuration(...)` follows the same basic pattern for P5 and writes YAML.

The pinned MACE 0.3.16 parser does not expose these logically structured options as structured configargparse actions. In particular, `atomic_numbers`, `E0s`, `radial_MLP`, and `heads` are declared `type=str`; MACE later interprets their string contents. Feeding YAML/JSON list or mapping objects therefore fails in configargparse before MACE training logic can normalize them.

### 2.3 The observed `atomic_numbers` error is only the first manifestation

Do not patch only `atomic_numbers`.

The current blind architecture flattening also has two additional correctness hazards:

- canonical `radial_MLP` is a list but MACE's parser expects a scalar string literal;
- canonical architecture metadata contains `schema` and `heads=["target_head"]`. `schema` is not a MACE training CLI argument, and the architecture `heads` list is not the same semantic object as MACE's `--heads` dataset-head dictionary. Exporting either blindly is invalid even if stringified.

P5 has a sibling latent failure: its top-level multihead `heads` mapping is a real MACE `--heads` value and must be encoded as the scalar dictionary literal MACE expects, while a non-multihead P5 run must not accidentally acquire the internal architecture `heads` list through flattening.

The global defect is therefore **uncontrolled projection across a typed internal configuration -> scalar-string external parser boundary**, not a malformed atomic-number list.

---

## 3. Frozen invariants

Implementation must preserve all of the following.

### Tier 1 / scientific and product invariants

- `N` remains the sole target-size data-cardinality variable.
- P1/P2 membership, qualification, seed ordering, reducer/ranking, practical-equivalence, and selected-size semantics do not change.
- Configurable fidelity/boundary epochs and continuous TRAIN2 rung continuation do not change.
- Common fitted preparation, E0 values, objective/property weights, and candidate memberships are unchanged.
- Exact authenticated TRAIN2/EVAL2 evidence remains the only ranking evidence.
- P4 current CampaignStore/root/restart/currentness ownership is unchanged.
- P5 CV/final-production method and head semantics are unchanged.
- Existing P7 software/qualification architecture is not reopened by a parser-boundary repair.

### Frozen execution architecture

- mdstats retains canonical structured internal configuration and its current digest/identity model.
- MACE remains invoked through the existing qualified `mdstats-mace-train` wrapper and `--config` path.
- TRAIN2 runtime-plan identity still travels through the established environment/continuation machinery.
- The generated MACE run config is derived executable syntax, not a second scientific/configuration authority.
- The pinned MACE parser/runtime is the compatibility authority for the external representation.
- No retry-on-parser-error, alternate argv path, parser monkeypatch, MACE fork, or second training wrapper is introduced.

### Identity/restart invariant

For semantically identical canonical candidate/post-selection configurations, this repair must not change the canonical materialization/config digest merely because the derived MACE literal spelling changes. Existing valid materializations and any compatible continuation state remain addressable under their existing mdstats authority. Only the regenerated derived executable config text may differ.

---

## 4. Required end state

There is one explicit representation boundary:

```text
canonical mdstats configuration (typed, authoritative)
        |
        | pure semantic-preserving projection
        v
MACE executable configuration (parser-compatible scalar syntax)
        |
        v
pinned MACE 0.3.16 parser / existing wrapper
```

The projection must satisfy these rules.

### 4.1 Explicit architecture projection; no blind flattening

Replace the current `for key, value in architecture.items(): config.setdefault(...)` behavior with an explicit projection of the canonical architecture fields that are actually MACE training arguments.

At minimum:

- internal architecture `schema` is never emitted to MACE;
- internal architecture `heads=["target_head"]` is never emitted as MACE `--heads`;
- every externally projected architecture key is deliberately mapped/allowed;
- an unexpected canonical architecture field outside the known internal-only and MACE-external sets fails at the mdstats projection boundary rather than silently leaking into MACE.

Do not rename the canonical architecture schema merely to make flattening convenient. Fix the projection.

### 4.2 Encode MACE scalar-literal options at the external boundary

For logically structured values whose pinned MACE parser action is scalar `type=str`, emit a deterministic scalar literal accepted by MACE and semantically equivalent to the canonical value.

The confirmed minimum census is:

- top-level `atomic_numbers`: canonical sequence -> scalar sequence literal;
- top-level `E0s`: canonical mapping/value -> scalar literal where structured;
- architecture `radial_MLP`: canonical sequence -> scalar sequence literal;
- P5 real multihead `heads`: canonical mapping -> scalar mapping literal;
- any structured `embedding_specs` or other currently projected MACE `type=str` field discovered by the final parser-action census.

Do not stringify ordinary numeric/boolean/string values indiscriminately. Do not encode internal-only metadata.

Use deterministic formatting. The chosen representation must round-trip through the pinned MACE parser/downstream literal reader to the same logical value. Do not use `str()` on arbitrary objects whose ordering or representation is unstable.

### 4.3 Treat optional `None` values semantically

Audit canonical optional architecture values such as `edge_irreps`, `num_channels`, `max_L`, `embedding_specs`, and `distance_transform` against the pinned MACE parser defaults.

If canonical `None` means “use the same MACE default/no override,” prefer omission from the executable config rather than feeding YAML null into a scalar parser. If MACE distinguishes an explicit literal `None` from omission for a supported field, preserve that distinction deliberately and test it.

Do not guess; bind this to the exact pinned parser/runtime behavior.

### 4.4 P3 and P5 must use the same representation rule

The same external syntax contract applies to target-size TRAIN2 and post-selection/final-production MACE execution.

Prefer reduction of duplicated translation logic. The implementation may extract a **small pure representation helper** in an existing MACE compatibility/realization owner only if it replaces duplicated P3/P5 conversion code. Do not create a new configuration layer, registry, wrapper, compatibility class hierarchy, or persistent schema.

If a shared helper is unnecessary, keep the two existing run-configuration functions but make their structured-literal policy identical and covered by common tests.

### 4.5 Do not change MACE itself

Do not change MACE's argparse declarations (`nargs`, `append`, etc.) and do not vendor/fork/monkeypatch its parser. The product already pins and qualifies MACE 0.3.16; mdstats owns translation into that dependency's accepted interface.

---

## 5. Affected surface to re-derive

Minimum expected production surface:

- `mdstats/training_data/campaign_target_size_runtime.py`
  - `mace_run_configuration(...)`
  - `MaceTargetSizeBoundaryTrainer.__call__(...)`
- `mdstats/training_data/post_selection_execution.py`
  - `post_selection_mace_run_configuration(...)`
  - `MacePostSelectionTrainer.__call__(...)`
- existing shared MACE compatibility/architecture owner if a pure serializer/projection helper is extracted;
- no change expected to `target_size_execution/candidate.py` or canonical post-selection materialization schemas unless executable evidence proves a separate bug.

Minimum test surface to inspect/extend:

- `tests/test_mlff_target_size_p4d_runtime_cutover.py`;
- P3 candidate/materialization/runtime tests that exercise `mace_run_configuration` and `MaceTargetSizeBoundaryTrainer`;
- `tests/test_mlff_target_size_p5_r9_guards.py` and maintained P5/post-selection execution tests;
- shared MACE/model-feature tests covering canonical architecture and pinned dependency compatibility;
- CLI target-size integration tests that traverse `select-target-size` into the production trainer boundary.

The implementer must use final references/callers to expand this list. Do not restrict regression to filenames named here if changed helpers have additional consumers.

---

## 6. Implementation gates

## Gate A — establish the exact parser contract and projection table

Before editing behavior:

1. inspect the exact pinned MACE 0.3.16 parser actions used by `mdstats-mace-train`;
2. enumerate every key emitted today by `mace_run_configuration(...)` and `post_selection_mace_run_configuration(...)`;
3. classify each emitted key as:
   - direct scalar pass-through;
   - structured value requiring scalar-literal encoding;
   - optional value whose canonical `None` should be omitted or explicitly represented;
   - internal-only mdstats metadata that must never reach MACE;
   - semantic collision (notably internal architecture `heads` vs MACE dataset `--heads`);
4. compare the table against canonical architecture schema fields and both P3/P5 top-level configuration schemas;
5. confirm no other production `--config` emission site bypasses these translation owners.

Use source/reference analysis and, where available, a focused Semgrep query to find production `--config` launches and generated `mace_run_config` writers. A structural tool is evidence support, not a new runtime mechanism.

**Gate A exit:** one complete field-level translation contract explains the observed failure and every sibling structured field before implementation begins.

## Gate B — alter the existing projection

Implement the minimum pure representation correction:

1. preserve canonical internal config values/digests unchanged;
2. remove blind architecture flattening;
3. explicitly project only MACE-consumed architecture fields;
4. encode confirmed structured scalar-string arguments deterministically;
5. correctly omit/internalize `schema` and architecture `heads`;
6. preserve P5's actual multihead `heads` mapping as the MACE dataset-head argument, encoded in the required scalar literal form;
7. handle optional `None` values according to Gate-A evidence;
8. preserve all existing command, working-directory, checkpoint, model/log/result directory, runtime-plan environment, and restart behavior.

**Gate B exit:** the exact real-world `atomic_numbers=[3,8,11,13,14,19]` candidate configuration and representative P5 scratch/naive/multihead configurations can be emitted as MACE parser-compatible configs without changing their mdstats canonical identities.

## Gate C — parser-boundary and integration regression

Add tests at the real dependency boundary, not only dictionary-shape tests.

### C1. Exact target-size parser reproducer

Build a real canonical target-size candidate configuration containing at least:

```text
atomic_numbers = [3, 8, 11, 13, 14, 19]
E0s            = representative fitted mapping
radial_MLP     = canonical list form
architecture schema + internal heads metadata
```

Project it through the real `mace_run_configuration(...)`, write the executable config, and feed that file to the exact pinned MACE parser used by the wrapper.

Acceptance:

- parser does not raise `SystemExit`/configargparse type error;
- parsed `atomic_numbers`, `E0s`, and `radial_MLP` literal values round-trip to the canonical logical values through MACE's expected literal-reading path;
- internal architecture `schema` is absent;
- scratch target-size execution does not receive MACE `heads` from internal architecture metadata;
- no unknown config keys are emitted.

This test must fail against the pre-repair implementation for the same reason as the user run.

### C2. P5 non-multihead parser regression

For scratch and naive-fine-tuning post-selection configurations:

- exact pinned parser accepts emitted config;
- canonical atomic/E0/architecture semantics round-trip;
- internal architecture `heads` does not become MACE `--heads`;
- foundation locator/head semantics remain unchanged where applicable.

### C3. P5 multihead parser regression

For `multihead_replay`:

- emitted MACE `heads` is one scalar dictionary literal;
- pinned parser accepts it;
- MACE's own literal interpretation yields the exact canonical target/replay head dictionary, including nested target-head atomic numbers/E0s;
- replay train/valid paths and canonical head names remain unchanged;
- internal architecture `heads` cannot overwrite or merge with the dataset-head mapping.

### C4. Production-trainer subprocess seam

Exercise the real `MaceTargetSizeBoundaryTrainer`/`MacePostSelectionTrainer` subprocess construction with an external bounded test program that invokes the **real pinned MACE parser** on the generated `--config`. Expensive numerical training may be substituted below that parser boundary, but the production trainer, filesystem config emission, subprocess argv, cwd, and dependency parser must remain real.

This closes the gap left by tests that only inspect the returned dictionary or replace the whole training owner.

**Gate C exit:** both production config-generation paths cross the actual MACE parser boundary successfully.

## Gate D — affected regression and assembled CLI acceptance

After the last executable/test edit:

1. re-derive callers/affected tests from the exact diff;
2. run focused parser/projection tests;
3. run complete affected P3/P4 target-size runtime regression;
4. run complete affected P5/post-selection regression;
5. run shared TRAIN2/model-feature/critical-precision wrapper regression for changed common helpers;
6. run import/collection/static/conflict checks used by the repository;
7. run an assembled bounded `select-target-size` path through Boundary 1 far enough to prove a production candidate passes MACE argument parsing and enters the expected TRAIN2 execution rather than exiting status 2;
8. if the environment cannot perform even a bounded numerical TRAIN2 smoke, record that limitation, but the real pinned parser/subprocess acceptance in Gate C remains mandatory and non-deferred.

Do not require a full 16-cell screen, long GPU training, final production, or P7 physical qualification for this software repair.

**Gate D exit:** no affected functional regression and the original parser failure is no longer reproducible.

---

## 7. Mandatory negative/structural acceptance

The final candidate must also prove:

1. canonical P3/P5 materialization/config digests are unchanged solely by external literal serialization;
2. `mace_architecture["schema"]` never reaches MACE config;
3. P3/non-multihead P5 `mace_architecture["heads"]` never reaches MACE `--heads`;
4. P5 multihead `heads` comes only from the canonical P5 dataset-head mapping;
5. no production MACE `--config` writer bypasses the corrected projection;
6. no code catches this parser error and retries with a second representation;
7. no new persistent compatibility/version registry is introduced;
8. no duplicate MACE parser/schema model is hand-maintained beyond the minimum explicit projection needed for the pinned dependency;
9. unexpected future architecture fields fail at the projection boundary rather than leaking silently into the dependency.

A focused Semgrep/AST source guard may enforce items 2-6 if useful, but it must target actual production owners and be paired with the real parser behavioral tests.

---

## 8. Regression matrix

| Surface | Required evidence |
| --- | --- |
| Canonical candidate materialization | typed `atomic_numbers`/`E0s`/architecture and digests unchanged |
| P3 executable projection | real pinned parser accepts exact reproducer |
| P3 TRAIN2 trainer | real config file + subprocess argv/cwd reaches parser successfully |
| Boundary continuation | n1 -> n2 -> n3/restart behavior unchanged |
| P4 runtime cutover | current campaign `select-target-size` still routes through the same production trainer/owners |
| P5 scratch | parser accepts, no leaked architecture `heads` |
| P5 naive fine-tuning | parser accepts, foundation semantics unchanged |
| P5 multihead replay | parser + literal interpretation preserve exact head mapping/replay paths |
| Shared MACE architecture | canonical JSON-safe model identity unchanged; only external syntax differs |
| Failure behavior | genuine subprocess/training failures still raise existing runtime errors; no retry/fallback |
| Static/collection | affected modules import/collect cleanly; no conflict markers/dead routes |

---

## 9. Non-goals

This repair does not:

- change target-size candidate sizes, seed set, fidelity schedule, ranking, or halving policy;
- refit E0s or other common preparation;
- alter MACE architecture defaults or model scientific identity;
- upgrade MACE/PyTorch or address the TorchScript deprecation warning;
- change VASP parsing/warning behavior;
- change GPU scheduling/resource policy;
- change storage cleanup architecture;
- re-run full production qualification.

Any such need requires separate evidence and authority rather than being smuggled into this parser repair.

---

## 10. Simplification rule for newly exposed failures

Because `atomic_numbers` is likely the first parser rejection in a chain, implementation may expose another field immediately after fixing it. Treat that as evidence about the same projection defect, not as a reason to stack one-off patches.

For every newly exposed config failure ask, in order:

1. Is this key actually a MACE external argument or internal mdstats metadata?
2. If external, what representation does the exact pinned parser/action accept?
3. Can the existing projection be corrected/explicitly narrowed so the failure disappears for all callers?
4. Does the proposed change preserve the canonical typed value and identity?

Do not add per-field fallback/retry branches when one explicit projection rule can solve the class.

---

## 11. Closure requirements

Implementation may close this repair only when all of the following are recorded against the exact final executable commit/tree:

- root-cause field census completed;
- explicit architecture projection replaces blind flattening;
- target-size exact reproducer passes the pinned MACE parser;
- P5 scratch/naive/multihead parser cases pass;
- real production-trainer config/subprocess seam passes the parser-boundary test;
- affected P3/P4/P5/TRAIN2/model-feature regression passes;
- original Boundary-1 status-2 parser failure is no longer reproducible in bounded assembled execution;
- canonical mdstats config/materialization identities remain unchanged by representational serialization;
- no wrapper, retry, second config authority, MACE fork, or compatibility registry was added.

**Implementation disposition: READY.**
