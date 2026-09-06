---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: implemented-pending-independent-review
created_date: 2026-09-05
amended_date: 2026-09-06
review_revision: 7
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_design_handoff_commit: 43a8b5f78880b9faaf4b023e979cb6303b1291e3
reviewed_implementation_commit: 119fab779a79566b4262067249c8986a8a7fc978
reviewed_assembled_source_commit: dcb0c9fc603e1f83d2657a6f4c4bb6c4e777012a
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
design_handoff_verdict: pass
implementation_review_verdict: no-pass
closure_verdict: no-pass
---

# MLFF target-size optimizer normalization, practical-ceiling selection, objective-weight, and training-policy identity rework

## 0. Current independent implementation review

**Overall implementation review: NO-PASS / bounded repair remains.**  
**Software Design / Frozen architecture: PASS / unchanged.**

Software Design independently reviewed executable implementation commit
`119fab779a79566b4262067249c8986a8a7fc978` and assembled source/documentation
commit `dcb0c9fc603e1f83d2657a6f4c4bb6c4e777012a` against this Revision 7 handoff,
the inherited P3 restart/partial-boundary/acceleration-replay authorities, P4
currentness/adoption authority, P5 CV/final-production authority, and Protocol
5.15.0.

No new scientific or architectural deficiency was found. The implementation
uses the accepted owners and mostly follows the required reduction-oriented
repair strategy: strict validation is consolidated in existing helpers and
first-rung writer exclusion reuses the existing advisory artifact lock rather
than introducing a lease database, new attempt identity, or second restart
state machine.

Three genuine blockers remain. They are implementation/acceptance
nonconformances against the already accepted design, so this file remains the
sole current implementation entrance. **Do not create a new design amendment or
parallel repair plan for them.**

### 0.1 Concerns now semantically closed by the implementation

The following prior R7 concerns are accepted at source/design level and must be
preserved through final regression:

1. **Live-writer-safe first-rung ownership is implemented with existing
   repository machinery.** First-rung execution acquires the existing adjacent
   `artifact_publication_lock` for the deterministic materialization path,
   re-authenticates durable progress after acquiring the lock, and holds the
   fence through cleanup, materialization, TRAIN2/EVAL2 work, and accepted cell
   publication. A competing writer waits and then reuses accepted progress;
   lock ownership is execution-local and kernel-released on process exit.
2. **Serial stale first-rung retry remains correct.** Unaccepted materialization
   and checkpoint scratch can be reclaimed for a fresh `start_epoch=0` attempt,
   while accepted progress remains immutable recovery authority.
3. **Target-size optimizer-normalization policy is now exact-domain and
   fail-closed.** Current config and current-schema deserialization no longer
   pre-coerce malformed integer/real/string values.
4. **`TrainingObjectivePolicy` and `ConfigurationWeightPolicy` are now
   exact-domain and fail-closed.** Objective coefficients, group-awareness,
   focus collections, configuration-weight flags, multipliers, and bounds are
   validated before normalization; current-schema readers pass raw values to
   those validators.
5. **Persisted `MaceOptimizerPolicy.from_dict()` no longer pre-coerces current
   policy fields.** Malformed current values now reach direct-constructor
   validation rather than being silently repaired by `int/float/bool` casts.
6. **Conditionally inert general `[training].ema_decay` remains absent from
   target-size materialization when EMA is disabled; realized target-size beta
   remains scientific when EMA is enabled.**
7. **P5 historical-method cutover remains closed through the real final
   production authorization owner.** Historical CV evidence cannot authorize
   corrected final production.
8. Practical-ceiling selection, paired-seed ranking, target-size normalization
   mathematics, objective/configuration/local-mask separation, common
   preparation ownership, partial-boundary recovery, historical acceleration
   replay, P4 selected flow, and fresh P5 production remain architecturally
   intact.

### 0.2 Remaining blockers

1. **Canonical real-value normalization is incomplete in independently
   constructible `MaceOptimizerPolicy`.** The constructor validates
   `learning_rate`, `ema_decay`, `weight_decay`, and `clip_grad` as finite real
   numbers but retains an accepted integer object unchanged. Consequently
   semantically identical values such as `1` and `1.0` can serialize/hash
   differently even though this workplan explicitly requires real fields to be
   canonicalized to float *after* validation. This is a current scientific
   method-identity split, not a style issue.
2. **The new pinned-MACE weighted-loss test is not proxy-proof for mdstats
   forwarding.** It correctly instantiates the real MACE loss and checks the
   numerical reduction, but its `_batch(...)` helper constructs new ASE objects
   and directly injects `config_weight`, `config_energy_weight`,
   `config_forces_weight`, and `config_stress_weight`. The test can therefore
   stay green if the real mdstats ExtXYZ exporter stops forwarding
   configuration weights or duplicates global E/F/S coefficients into local
   property weights. The accepted claim is the assembled mdstats-export -> MACE
   loss path, not MACE's isolated behavior after the test manually supplies the
   intended values.
3. **Final assembled executable evidence is still absent.** The reviewed source
   commit has only the documentation-PDF GitHub Actions run in accessible
   repository evidence. Required focused/stage-local tests, proxy-proof pinned
   MACE 0.3.16 acceptance, real-owner integration, and final affected-surface
   regression have not been established on the final executable candidate.
   Required checks that did not execute are not a pass.

---

## 1. Tier-1 problem and scientific invariants

The target-size experiment asks:

> Within the configured practical target-data budget, what is the smallest
> nested target-training cardinality whose performance is not materially
> improved by using more unique target data; and, if no plateau is demonstrated
> before the practical ceiling, what is the best permitted size available?

The sole target-data-cardinality independent variable remains:

```text
N = number of target configurations used for gradient training
T_N = pi_train[:N]
```

The optimizer-seed set is the stochastic replicate dimension. Ranking consumes
authenticated paired-seed target-side EVAL2 evidence at exact configured
fidelity/evaluation boundaries.

Binding Tier-1 product/scientific invariants:

- exact nested `T_N = pi_train[:N]` membership;
- one P1 canonical frame authority and neutral statistical substrate;
- one `P_train / M3` split and one `pi_train / pi_eval` authority;
- configured candidate/evaluation ladders and `q -> min(q,4) -> 2 -> 1`
  successive-halving topology;
- paired-seed arithmetic-mean aggregation and target-force RMSE ranking;
- practical-equivalence preference for smaller data size;
- materially superior configured ceiling is `SELECTED` with
  `nonconverged_at_configured_ceiling` warning metadata, not a blocking
  scientific failure;
- insufficient comparison remains blocking;
- one continuous scientific trajectory per `(N, optimizer_seed)` across
  `n1 -> n2 -> n3` with exact authenticated predecessor continuation;
- P4 owns terminal/currentness/adoption;
- P5 cross-validates exactly frozen `T_selected` and final production starts
  fresh from exactly `T_selected`;
- no screen/CV checkpoint becomes final-production parent;
- historical accepted evidence is never silently reinterpreted under a current
  execution realization or corrected method.

No unconfigured rescue size is invented.

---

## 2. Frozen high-level architecture

The Frozen authority graph remains:

```text
canonical frame authority
  -> neutral statistical substrate
  -> one P_train / M3 split
  -> one pi_train / pi_eval
  -> one common deterministic preparation
  -> paired (N, optimizer-seed) screen
  -> exact n1 -> n2 -> n3 continuation
  -> direct M1/M2/M3 EVAL2
  -> one target-size reducer
  -> one N_selected / T_selected
  -> post-selection CV on exactly T_selected
  -> fresh final production on exactly T_selected
```

Also Frozen:

- target-size optimizer-progress normalization is screen-specific:
  `U_ref=ceil(N_ref/B)`, `U_N=ceil(N/B)`, `s_N=U_ref/U_N`,
  `LR_N=LR_ref*s_N`, `beta_N=beta_ref**s_N`;
- no hidden cap/floor, survivor-dependent rescaling, or rung-local normalized
  trajectory reconstruction;
- general `[training].learning_rate` and `[training].ema_decay` are not
  target-size LR/EMA-decay authority;
- realized target-size LR and realized EMA beta are scientific when applicable;
- global E/F/S coefficients, configuration weights, and local property
  availability/modifier weights are distinct semantic layers;
- target-size/P5 executable loss remains dependency-native MACE
  `WeightedEnergyForcesStressLoss` / accepted `loss="stress"` semantics;
- P3 owns target-size execution, immutable accepted evidence, restart, and
  replay; P4 owns currentness/terminal adoption; P5 owns CV/fresh production;
- accepted logical-cell evidence is durable science/restart authority;
  unaccepted first-rung workspace is execution-local scratch;
- process liveness/locking is execution state and must not become scientific
  identity;
- final production starts fresh;
- production-scale GPU qualification remains deferred to final release.

The restart-epoch handoff and acceleration-replay sibling workplans remain
binding relatives: later rungs must resume the exact authenticated predecessor,
new execution realization may govern new work but may not rewrite accepted
historical trajectory identity, and no second checkpoint/restart authority may
be introduced.

---

## 3. Accepted implementation state to preserve

Retain all already-correct behavior, including:

- practical-ceiling selected-warning semantics and exact selected-membership
  digest;
- one normalized `(N, seed)` trajectory across all three rungs;
- seed-neutral screen identity excludes optimizer seed, candidate-local
  acceleration realization, general LR/EMA decay, workers,
  `valid_batch_size`, and `eval_interval`, while retaining true
  trajectory-changing optimizer/precision/backend state;
- candidate realization retains exact membership/count, update geometry,
  full-`n3` exposure, precision, seed, normalization identity, effective
  LR/EMA, LR schedule, and candidate-local acceleration provenance;
- general EMA decay is omitted/ignored when target-size EMA is disabled, while
  realized beta remains authenticated when enabled;
- `TrainingObjectivePolicy` owns global E/F/S coefficients;
  `ConfigurationWeightPolicy` owns per-configuration multipliers; local
  property weights remain availability/local modifiers normally `1` present / `0`
  absent;
- common preparation owns objective/configuration-weight/E0/harness inputs but
  not training batch size or learned-model dtype;
- accepted partial-boundary evidence is authenticated/reused; only missing
  active cells execute; later rungs use the existing P3 continuation owner;
- historical acceleration realization is replayed from accepted evidence rather
  than replaced by the current invocation's realization;
- corrected P5 method recipe and exact method-digest authorization prevent
  historical pre-cutover CV evidence from authorizing corrected production.

---

## 4. Repair R7-1 — finish canonical `MaceOptimizerPolicy` real-value normalization

### 4.1 Diagnosis

Current `MaceOptimizerPolicy.__post_init__()` correctly rejects booleans,
strings, non-real types, NaN, and infinities for its real fields. It then checks
ranges but does not assign the validated real values back as canonical floats.
Its `_payload()` serializes the retained attributes directly.

Therefore:

```text
MaceOptimizerPolicy(learning_rate=1)
MaceOptimizerPolicy(learning_rate=1.0)
```

can describe the same declared real method value yet produce different canonical
JSON and policy digests. The same issue applies to `ema_decay`, `weight_decay`,
and `clip_grad`.

This violates the already-Frozen canonical-domain rule:

> validate finite real numeric values without coercing malformed values, then
> canonicalize accepted real values to float before identity/serialization.

### 4.2 Required repair

Repair the existing constructor; do not create another policy or validator
layer.

Preferred reduction:

- reuse the existing shared `strict_finite_real` helper (or equivalently reduce
  the hand-written loop to the same semantics) for `learning_rate`,
  `ema_decay`, `weight_decay`, and `clip_grad`;
- preserve the existing field-specific ranges;
- after exact-type/finiteness validation, assign the canonical `float` result
  into each dataclass field before `_payload()`, digesting, or downstream use;
- preserve exact-int semantics for batch sizes, workers, epoch/eval counts, and
  seed, and exact-bool semantics for EMA/AMSGrad;
- do not accept numeric strings or booleans merely to canonicalize them.

Do not introduce a schema migration just for this correction. If an existing
explicit legacy-schema digest reader is demonstrably affected by canonicalizing
an otherwise supported historical numeric representation, preserve that
reader's historical digest verification inside the **existing compatibility
branch**, using already-validated raw legacy representation where necessary.
Do not create a new compatibility registry or alternate policy identity.

### 4.3 Required acceptance

At minimum prove:

- `1` and `1.0` (and analogous integer-valued real inputs) canonicalize to the
  same float-valued current policy payload and policy digest;
- current-schema serialize/deserialize round trips retain that canonical form;
- malformed bool/string/non-finite values still fail before identity/execution;
- valid non-integral reals retain their exact declared values;
- supported legacy round-trip/digest tests remain green if those schemas are
  still part of the product compatibility surface;
- the bounded four-family coercion/normalization census remains clean.

The already-correct target-normalization/objective/configuration-weight readers
must not be broadened again.

---

## 5. Repair R7-2 — make pinned-MACE objective acceptance proxy-proof through the mdstats exporter

### 5.1 Diagnosis

`tests/test_mlff_target_size_mace_objective_realization.py` now provides useful
real dependency evidence:

- non-default global coefficients;
- real MACE parser and `get_loss_fn`;
- `WeightedEnergyForcesStressLoss`, not `UniversalLoss`;
- independent expected weighted-MSE calculation;
- local-mask and missing-stress behavior.

However its numerical batch helper creates new ASE `Atoms` and writes
`config_weight`, `config_energy_weight`, `config_forces_weight`, and
`config_stress_weight` directly from test literals. That bypasses the production
mdstats export owner which is responsible for forwarding fitted configuration
weights and local property masks into ExtXYZ.

The test therefore proves MACE consumes correctly injected values, but not that
mdstats injects the right values. It could pass if production forwarding were
removed or if global coefficients were incorrectly copied into the local
weights.

### 5.2 Required repair

Alter the existing semantic acceptance path rather than adding production
machinery.

Use a bounded real mdstats preparation/materialization/export fixture with:

- deliberately non-default, distinguishable global objective coefficients;
- deliberately non-default configuration weighting that produces at least one
  configuration weight distinguishable from `1.0`;
- at least one missing-property frame so the exported local mask contains zero;
- ordinary present properties whose exported local weights are `1.0`, not
  copies of the global objective coefficients.

Then feed the **actual mdstats-exported ExtXYZ frames** (or the exact production
export-owner output parsed through ASE) into MACE's real
`config_from_atoms`/`AtomicData` path. Do not replace their weight metadata with
test-authored literals after export.

Through that assembled path prove:

1. generated MACE config carries the non-default global E/F/S coefficients;
2. exported `config_weight` equals mdstats' realized configuration-weight
   authority for the chosen frame(s);
3. exported `config_energy_weight` / `config_forces_weight` /
   `config_stress_weight` are local availability/modifier values and are not
   copies of the global coefficient ratio;
4. missing property exports/arrives as a zero local mask and contributes zero;
5. MACE 0.3.16 instantiates `WeightedEnergyForcesStressLoss`, not
   `UniversalLoss`;
6. MACE's dependency-computed loss on the exported batch agrees with an
   independently derived expected value;
7. the test would fail if mdstats stopped forwarding configuration weights,
   copied global coefficients into local weights, selected another loss family,
   or fell back to MACE defaults.

Numerical workload may remain tiny. The production materialization/export and
MACE semantic owners must not be replaced by doubles for the claim they own.

### 5.3 Dependency/version requirement

The acceptance environment must positively establish `mace-torch==0.3.16` (or
the repository's qualified exact equivalent package identity) and execute these
tests. `pytest.importorskip("mace")` is acceptable for ordinary developer
portability, but a skipped result is **not** closure evidence for this workplan.

---

## 6. Repair R7-3 — execute final assembled functional closure

Source inspection cannot close executable acceptance. After R7-1 and R7-2 are
assembled, run the required evidence on one final executable candidate.

### 6.1 Focused/stage-local checks

Run and retain evidence for:

- strict four-family policy-domain tests including the new real-value
  canonicalization equivalence;
- serial first-rung interruption/retry and execution-only drift;
- concurrent live-writer test: A owns/materializes/pauses; B cannot delete,
  mutate, or duplicate-run; A completion allows B to re-authenticate/reuse;
- crash/release/reclaim path after no accepted progress;
- accepted progress immutability and genuine scientific-drift negatives;
- EMA-disabled/general-decay and EMA-enabled/reference-beta identity cases;
- revised proxy-proof pinned-MACE objective/export/loss semantic acceptance.

The existing direct logical-cell concurrency test is useful focused evidence.
Final assembled integration must additionally establish that the production
`select-target-size` orchestration actually reaches the same fenced owner and
reconciliation behavior; do not add a second synchronization path merely to
make this test convenient.

### 6.2 Final affected regression and integration

Re-derive the transitive affected surface from the final diff and execute the
complete affected regression. At minimum include final versions of:

- target-size statistical authority and practical-ceiling reducer;
- P3A-P3F and later P3 closure/replay/currentness suites;
- restart-epoch handoff and partial-boundary recovery;
- acceleration-realization replay;
- first-boundary interruption/retry and concurrent writer ownership;
- canonical optimizer/normalization/objective/configuration-weight policy
  domains and identity parity;
- realized MACE architecture, executable config, binary/critical precision, and
  TRAIN2 continuation/restart;
- objective/weight/export and the proxy-proof real MACE 0.3.16 loss test;
- affected P4 currentness/adoption;
- P5 identity, historical-method rejection, CV/final-production authorization,
  materialization/execution/publication;
- prepared-generation identity/currentness and campaign lifecycle/status;
- affected documentation/specification integrity.

Retain bounded real-owner practical-ceiling flow:

```text
terminal paired-seed reducer evidence
 -> SELECTED Nmax + nonconverged_at_configured_ceiling warning
 -> real P3 terminal head
 -> P4 TERMINAL_SELECTED adoption/currentness
 -> exact N_selected / T_selected
 -> next lifecycle command = cross-validate
```

If the affected boundary cannot be confidently bounded, run the broader MLFF
regression suite. Run repository/project-required checks as applicable.

Accessible repository evidence for `119fab...` currently establishes only the
successful documentation-PDF workflow. The implementation must therefore make
the functional test execution/results reviewable (CI/checks or another
repository-governed test record sufficient to identify commands, candidate,
and pass/skip/fail status).

Production-scale GPU qualification remains **deferred** and must not be used as
a substitute for this functional closure.

---

## 7. Simplicity and authority boundaries

### Frozen

Frozen authority is limited to:

- Tier-1 scientific question and exact `T_N` membership;
- P1 -> P5 authority graph;
- practical-ceiling selected-warning semantics;
- inverse-update LR/EMA normalization mathematics;
- one continuous target-size trajectory per `(N, seed)`;
- exact P3 accepted-evidence/restart ownership;
- accepted-progress vs unaccepted-attempt-scratch distinction;
- process liveness excluded from scientific identity;
- historical acceleration replay vs current-new-work realization distinction;
- target-size general-LR/general-EMA-decay exclusion and realized LR/EMA
  authority;
- global objective / configuration weight / local property mask separation;
- dependency-native weighted E/F/S MACE loss family;
- one canonical shared optimizer/method semantics;
- P5 exact method-digest authorization and fresh final production;
- no silent reinterpretation of historical evidence.

### Delegated Tier 2

Implementation may alter/simplify:

- exact validation helper factoring;
- test fixture layout;
- exact bounded test data used to create non-default configuration weights;
- use of the existing export record/ExtXYZ path to feed the MACE semantic test;
- diagnostics and redundant helpers made obsolete by consolidation.

Prefer changing/reducing existing owners and tests over adding adapters,
wrappers, registries, or parallel policy objects.

### Reopen Software Design only if evidence invalidates a Frozen assumption

Examples include:

- the existing execution-local lock cannot safely fence first-rung ownership
  without a materially different persistent liveness architecture;
- a supported historical policy schema intrinsically depends on lossy current
  numeric reinterpretation rather than an explicit historical representation;
- the real mdstats exporter and pinned MACE 0.3.16 cannot realize the accepted
  global/configuration/local-weight ownership separation;
- existing P3/P5 authority boundaries cannot express exact restart/currentness
  or historical-method rejection without architectural change.

Do not reopen Design because a current helper/test API is inconvenient.

---

## 8. Forbidden repair patterns

Do not close this work by:

- adding a second optimizer policy/validator hierarchy;
- weakening exact-type validation to make integer/float identity tests pass;
- accepting numeric strings or booleans as reals/integers;
- changing scientific identity to include worker/validation-batch/liveness data;
- adding a persisted lock/lease database, new scientific attempt ID,
  compatibility registry, mutable latest pointer, cleanup daemon, or second
  restart authority;
- weakening immutable create-or-verify or accepted partial-boundary evidence;
- deleting accepted evidence to force a clean rerun;
- bypassing the production mdstats export owner in the semantic loss acceptance;
- manually injecting the expected configuration/local weights after export and
  calling that end-to-end evidence;
- treating parser/config equality as loss semantics;
- counting a skipped MACE test as pass;
- creating a local UniversalLoss replacement or MACE adapter merely for testing;
- adding a new target-size terminal/warning lifecycle;
- substituting production-scale GPU qualification for functional regression.

---

## 9. Reopened implementation sequence

### Gate R7-1 — canonical real-value identity closure

- canonicalize valid `MaceOptimizerPolicy` real fields to float after strict
  validation at the existing constructor owner;
- preserve supported legacy digest semantics only through the existing explicit
  compatibility branch if actually needed;
- add integer-valued-real vs float-valued-real identity/round-trip tests;
- rerun focused four-family domain/parity/structural checks.

### Gate R7-2 — proxy-proof pinned-MACE semantic closure

- alter the existing real-MACE semantic acceptance to consume actual
  mdstats-exported weight/mask metadata;
- exercise non-default global objective, non-default configuration weight,
  present-property local weight, and missing-property zero mask;
- execute real qualified MACE 0.3.16 loss and independent expected reduction.

### Gate R7-3 — final assembled acceptance

- run focused concurrency/restart/policy/MACE checks;
- run production-owner integration including target-size practical-ceiling ->
  P4 -> P5 handoff and retained P5 historical-method rejection;
- re-derive and execute complete affected regression/project checks on one final
  candidate;
- regenerate derived documentation only after any normative Markdown change.

No long GPU/full-production qualification is required for these gates.

---

## 10. Closure criteria

Close this workplan only when all are true:

- valid real-valued optimizer inputs have one canonical float identity regardless
  of integer-vs-float Python representation, while malformed values remain
  rejected;
- all four plan-owned policy families retain exact-domain fail-closed behavior
  and stable valid round trips;
- first-rung live-writer fencing, serial crash/retry, owner-death reclaim, and
  accepted evidence immutability pass through the real P3 owner path;
- target-size general EMA decay remains inert when EMA is disabled and realized
  beta remains scientific when enabled;
- proxy-proof MACE 0.3.16 acceptance consumes actual mdstats-exported
  configuration/local weights, instantiates the accepted weighted loss, and
  matches an independent numerical expectation;
- P5 corrected method identity remains exact and historical-method CV evidence
  remains rejected by the real final-production owner;
- practical-ceiling selected-warning flow remains intact through P4/P5;
- final re-derived affected regression, assembled integration, and project
  checks execute and pass on the final candidate with required tests not skipped;
- no new competing configuration/restart/materialization/liveness/loss authority
  is introduced.

**Independent Software Design review verdict: NO-PASS / rework-required.**  
**Frozen scientific/high-level architecture verdict: PASS / no redesign.**

## 11. Rework implementation evidence — 2026-09-06

The R7-1 and R7-2 repairs are implemented on the dedicated branch. The
executable candidate used for validation is base commit
`573ba3005edc40810cbbe009de8de18915ca5728` plus the working-tree changes in:

- `mdstats/training_data/protocol.py`
- `tests/test_mlff_target_size_policy_domain_rework.py`
- `tests/test_mlff_target_size_mace_objective_realization.py`

The binary diff digest for those three candidate files is
`f2d8204ff65b443fa5676c1773c727345c9d0b82de801e14a0b18065196a65f7`.
The earlier `reviewed_*` commit identities and `NO-PASS` verdicts above remain
the historical independent-review record; this evidence records implementation
completion pending a fresh independent review of the new candidate.

### Focused acceptance

```text
conda run -n mace python3 -m compileall -q mdstats/training_data \
  tests/test_mlff_target_size_mace_objective_realization.py \
  tests/test_mlff_target_size_policy_domain_rework.py
  PASS

conda run -n mace python3 -m pytest -n 32 --dist=load \
  tests/test_mlff_target_size_policy_domain_rework.py \
  tests/test_mlff_target_size_mace_objective_realization.py
  47 passed, 20 warnings in 14.57s
```

The focused suite exercised integer-valued-real versus float-valued-real
optimizer identity, exact policy domains, the real mdstats P1-P3 preparation /
materialization / ExtXYZ exporter, and MACE's dependency-native weighted loss.
The semantic test positively established `mace-torch==0.3.16`, instantiated
`WeightedEnergyForcesStressLoss`, consumed the exported local masks and
configuration weights, and matched the independent numerical reduction.

### Final affected-surface regression

The affected surface was re-derived from the final source/test diff and the
workplan's transitive P3/P4/P5/TRAIN2/campaign requirements. It was executed
with all 32 online CPUs:

```text
conda run -n mace python3 -m pytest -n 32 --dist=load \
  tests/test_mlff_target_size*.py \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_data9a5_critical_precision.py \
  tests/test_mlff_prec1_precision_profiles.py \
  tests/test_mlff_train2a_policy.py tests/test_mlff_train2b_runtime.py \
  tests/test_mlff_prepared_common_atomic_reference_order.py \
  tests/test_mlff_campaign_assembled_lifecycle.py \
  tests/test_mlff_campaign_prepare_boundary.py \
  tests/test_mlff_campaign_prepared_generation.py \
  tests/test_mlff_campaign_currentness_races.py \
  tests/test_mlff_campaign_storage_composition.py \
  tests/test_mlff_data8_specification.py \
  tests/test_mlff_data9b3_campaign_cli_specification.py
  945 passed, 2 skipped, 1819 warnings in 232.28s (0:03:52)
```

The two skips are environmental and were not counted as passes:

1. `tests/test_mlff_data9a5_critical_precision.py:114` — the real MPA-0 model
   or VASP trajectory is not mounted.
2. `tests/test_mlff_target_size_p6_p5a6_compatibility.py:138` — the preserved
   P5A6 compatibility workspace is absent.

The first-rung live-writer/retry, practical-ceiling -> P4 terminal adoption ->
P5 `cross-validate` flow, historical-method rejection, and affected campaign
currentness/restart paths all passed in the assembled run. Final non-PDF
`git diff --check` also passed. No GPU or production-scale external-reference
qualification is claimed; those remain outside this executable closure.
