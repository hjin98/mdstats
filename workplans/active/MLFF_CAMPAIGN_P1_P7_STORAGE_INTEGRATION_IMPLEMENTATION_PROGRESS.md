---
kind: implementation-progress
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
scope: executable progress against the composed assembled-integration authority
disposition: PARTIAL / INTEGRATION STILL REOPENED
---

# Assembled integration implementation progress

This file records what has actually been implemented against the composed
integration authority (root workplan + second-pass amendment + final convergence
amendment + the active P4 prepared-generation repair) and, just as importantly,
what has **not**. It does not grant closure to anything. The assembled campaign
remains **NO-PASS / integration-reopened** until every closure criterion in the
composed authority is satisfied on one exact candidate.

## Implemented

### Stage 1 - prepared-generation ownership (INT-A, P4-STAGE-A/B/C/D, R2-A, F8, F9, F16, F17)

`prepare` is now the sole construction boundary for the target-size scientific
substrate. It publishes an immutable, content-addressed prepared generation and
`CampaignStore` CAS-binds that manifest's digest onto the canonical generation;
publication completes before adoption.

- new owner `mdstats/training_data/campaign_prepared_generation.py`: publication,
  authenticated load, preparation-configuration identity, and the owner
  reachability view used for retention;
- `campaign_target_size_runtime.py` splits the single former role in two -
  `build_prepared_target_size_substrate` (prepare-only) and
  `load_prepared_target_size_generation` (the one canonical downstream consumer);
- `build_screen_context` and `load_validated_target_size_terminal_result` consume
  the published generation; neither can reach the builder, and there is no
  fallback path back to live sources;
- `TargetSizeCampaignState` binds `prepared_manifest_digest`. The field is
  omitted from the payload when absent, so a pre-repair row still authenticates
  and can be *reported* as needing one explicit `prepare` rather than being
  unreadable or silently retrofitted;
- the normalized frame cache is append-only and content-addressed. Entries are
  published under their own content identity and never replaced or deleted, so
  constructing a future generation cannot damage a current one, and two
  generations share every member an edit did not touch;
- `_prepare_catalog` no longer deletes the cache root, and hands its validated
  DATA4 bundle back in memory instead of persisting and immediately restoring it;
- preparation-owned configuration (neutral partition policy, target-size policy)
  is bound into the generation. A changed preparation policy is refused with
  fresh-`prepare` guidance; CV, production, qualification and scheduling settings
  provably cannot invalidate it.

### Stage 2 - bounded direct inference (INT-B, INT-G, P4-STAGE-E/F, F2, F5, F15)

- new `mdstats/training_data/bounded_inference.py`: one small ordered partition
  owner bounded by the accepted `MaceOptimizerPolicy.valid_batch_size`;
- target-size direct EVAL2 and the post-selection sibling both route through it;
  no production path hands a whole scientific population to `predict_batch`;
- the numerical test seams moved **below** the partition owner. Fakes that
  answered for a whole population they never received now fail closed.

### Stage 3 - observation and lifecycle projection (INT-C, INT-D, INT-E, R2-C, R2-E, F3, F4, F10, F12)

- new `mdstats/training_data/campaign_lifecycle.py`: one pure projection from
  persisted owner state (campaign-store revision plus compact P5/P7 pointer
  records), taken as a coherent snapshot;
- new `mdstats/training_data/qualification/observation.py`: compact P7 status
  from pointer rows, immutable records, and attempt component positions - no
  `QualificationSession`, no reference bundle, no inference;
- `command_status` and `qualification status` run under the observational
  capability: no directory creation, read-only store, no wrapper/provider/root
  construction;
- P5/P7 evidence stores accept `create=False`, so a read can inspect an absent
  store without creating it;
- the public lifecycle includes P7. `advance` may route ordinary
  `qualification run` and can never reach locked activation.

### Stage 5 - storage composition (INT-F, R2-F, FINAL-C)

- new `prepared_generation_view` owner adapter classifies `.mdstats/prepared` as
  restart state the current generation requires, with reachability derived from
  prepared manifests rather than from pathnames. No reference-count database, no
  second cache, no new destructive path;
- the affected Storage R38 operation family is exercised against one prepared
  generation - report, deep report, safe and cache cleanup (dry run and apply),
  deduplicate (dry run and apply), archive create (dry run and apply), archive
  list - and after **every** operation a real downstream consumer re-loads the
  generation and is proven to reach no preparation owner;
- retiring a historical generation releases nothing the current one still
  shares: two generations differing in one preparation policy share the entire
  normalized payload plus several immutable components, and every applied
  operation leaves that shared content byte-identical.

### FINAL-A / FINAL-B

- the first rung discards its uncommitted attempt workspace before fresh
  execution, so partial bytes from an interrupted attempt can never authenticate
  as that attempt's boundary state;
- stale-P3-writer fencing is established through the real CAS transition;
- the full interruption matrix now runs through the assembled campaign. With one
  boundary accepted and a continuation rung open, each required predecessor
  component - raw checkpoint, TRAIN2 runtime summary, continuation companion - is
  deleted and corrupted in turn, and a foreign candidate's summary is swapped in.
  Every case fails closed with the reducer, adopted head and generation exactly
  unchanged, and, decisively, **no continuation rung ever restarts from epoch
  zero**: a silent fresh start would be a different trajectory wearing the same
  identity. An ordinary interruption resumes into the same experiment, reusing
  the accepted boundary rather than recomputing it.

That matrix also found a real defect: corrupting the durable TRAIN2 runtime
summary surfaced a bare `json.decoder.JSONDecodeError` instead of the typed
corruption error every other component raises, so a caller distinguishing
"absent" from "corrupt" would have missed it. The summary loader now reports
unreadable durable state as serialization corruption.

### Assembled lifecycle, property coverage, GPU and cost evidence

- **root section 6.1**: one fresh workspace is driven through the real parser and
  dispatch - prepare, select-target-size, cross-validate, train-production,
  qualification status, qualification run - reopening the campaign and
  re-observing between every stage, plus one genuine subprocess boundary. The
  routing sequence is exactly the accepted lifecycle and ends truthfully at
  `waiting_for_reference`. This test found and closed a real projection defect:
  a published `waiting_for_reference` verdict was reported as a *completed*
  qualification stage, which would have told an operator the campaign was done
  while the product was still unqualified;
- **root section 6.9 / final section 5.6**: a model-based state machine over the
  real owners enumerates every bounded interleaving of observe, reopen, repeated
  preparation, changed preparation and storage cleanup (85 walks), checking
  generation monotonicity, immutability of published content, protection of what
  the current generation requires, loader authentication, and agreement between
  the public projection and the owner it projects. `hypothesis` is not a
  dependency of this project; the enumeration is deterministic and total over the
  bounded alphabet, so a failure names an exact reproducible sequence rather than
  a seed;
- **INT-B / P4-STAGE-E sections 6.9-6.10**: a real authenticated MACE checkpoint
  is evaluated on the target hardware class (NVIDIA RTX 3090, 23.55 GiB) through
  the production direct-inference owner with no forward override. Observed:
  `valid_batch_size=1`, population 2, chunk widths `[1, 1]`, one provider state
  across both chunks, peak allocated 16.4 MiB, peak reserved 22.0 MiB;
- **root section 6.10 / P4 section 6.13 / R2 section 4.9**: measured on the real
  commands - `select` first run, `select` resume and `status` each perform
  **zero** DATA4 restores, **zero** source frame reads and **zero** preparation
  builds, and `status` completes in ~0.01 s. Repeating an unchanged preparation
  adds no published object at all; a changed preparation policy republishes only
  the components it actually changes and reuses the entire normalized payload by
  content identity. Warm prepared load keeps every normalized array backed by the
  shared read-only mapping rather than private RAM.

## Executed evidence

New focused/acceptance suites, all executing the real owners with numerical
doubles strictly below them:

- `tests/test_mlff_campaign_prepared_generation.py`
- `tests/test_mlff_campaign_prepared_generation_efficiency.py`
- `tests/test_mlff_bounded_direct_inference.py`
- `tests/test_mlff_bounded_direct_inference_cuda.py`
- `tests/test_mlff_campaign_observation_purity.py`
- `tests/test_mlff_campaign_currentness_races.py`
- `tests/test_mlff_target_size_first_boundary_interruption.py`
- `tests/test_mlff_target_size_continuation_corruption.py`
- `tests/test_mlff_campaign_storage_composition.py`
- `tests/test_mlff_campaign_stateful_properties.py`
- `tests/test_mlff_campaign_assembled_lifecycle.py`

Structural claims were validated with Semgrep rules checked against known
positive and negative constructs before their zero-finding results were relied
on: no production path submits a whole scientific population to `predict_batch`;
no evidence-store opener creates its root unconditionally; the prepare-only
builder is reachable only from `prepare`. Symbol-level caller closure confirms
exactly two production consumers of the prepared-generation loader.

### Affected-surface regression

`pytest -k "mlff or storage or campaign"` in the `mace` environment, compared
against the same selection run in a clean worktree at the unmodified branch head
`28b56eb`:

- true baseline: 299 failed, 1562 passed, 15 skipped, 8 errors;
- final candidate: 299 failed, 1698 passed, 16 skipped, 8 errors.

The failure sets are **identical**: no test fails on the candidate that does not
also fail on the unmodified head, and none that failed there was left unexamined.
The 136 additional passes are the new acceptance suites above.

Getting there required repairing nine failures this work had introduced:

- one user-guide documentation assertion that encoded the pre-repair "advance
  never runs qualification" claim, corrected with the lifecycle change;
- eight P5 provider-lifetime guards whose `_optimizer_policy_for` stand-in
  omitted `valid_batch_size`; the accepted execution policy owns that bound, so
  a stand-in without it was not standing in for the real thing.

An earlier comparison in this cycle was run against a baseline that already
contained the first commit's changes and so under-reported those nine. The
comparison above is against the true unmodified head, in a clean worktree.

## Not implemented - the integration remains reopened

The following composed obligations are **not** satisfied and no part of this
progress should be read as closing them:

- the tail of root section 6.1 - supplying the authenticated reference bundle,
  completing nonlocked qualification, explicit locked activation, and a terminal
  release verdict - is blocked by the P7 fixture defect below;
- R2-F archive verify and restore against the prepared representation: no owner
  in the bounded campaign declares cold-replaceable bulk, so `archive create`
  catalogs nothing and there is no archive to verify or restore. Every other
  affected storage operation is exercised;
- R2-G irreversible locked-disclosure history across generation advance and
  storage transformation, which requires a locked activation and is therefore
  blocked by the same P7 defect.

## Blocking: the P7 bounded qualification fixture cannot relax

`tests/test_mlff_p7_post_production_qualification.py`, the P7 acceptance suites,
and most of `test_mlff_storage_reset_integration.py` fail at
`required_component_rejected:relaxation`. This is a **regression on this
branch**, not a long-standing condition: `git bisect` over the single assembled
P7 test identifies commit `4d61cd1` ("hotfix", carrying the P3 realized-MACE
architecture identity repair and the post-DATA4 authority-reconstruction work)
as the first bad commit; the test passes at its predecessor `323ea89`.

The product owner is behaving correctly. `relax_fixed_cell` uses ASE's FIRE
optimizer, the acceptance thresholds are untouched, and the component truthfully
reports `relaxation_not_converged: step_budget_exhausted`. The defect is in the
bounded acceptance *model*: the fixture's stand-in potential is a harmonic pair
term with `r0 = 6.0 A` over a frustrated cell plus a per-frame constant force
offset, and it does not have a minimum FIRE can reach from this base. Raising the
budget does not help - measured over 25, 50, 200 and 600 steps the maximum force
oscillates (2.60, 2.87, 1.90, 3.79 eV/A) instead of decreasing, while the relaxed
geometry drifts several angstrom from the reference. A model that cannot be
relaxed makes the relaxation component unexercisable in its passing direction: it
can only ever reject.

Repairing this means choosing a bounded reference potential with a reachable
minimum near the canonical geometry. That is a decision about the accepted P7
acceptance model rather than an implementation detail, and it is deliberately
**not** patched here: raising a budget that demonstrably does not converge, or
relaxing a scientific threshold, would manufacture a pass rather than establish
one.

## Other pre-existing failures, not introduced here

Beyond the qualification cascade above, several documentation/specification
suites reference spec files that are not present in the tree. They are recorded
rather than repaired because they are outside the changes above; they are,
however, part of the assembled surface and must be resolved before any assembled
closure claim.

Separately, running `prepare` again on a campaign whose generation is already
terminal fails inside the result-view writer, which refuses to write terminal
state. This predates the work here and is a genuine defect in `prepare`
idempotence for terminal generations.

---

# Review-reopen repair (amendment `..._IMPLEMENTATION_REVIEW_REOPEN.md`)

This section records the repair of the six blocking findings raised by the
independent implementation review. Nothing above is retracted; the items the
previous section recorded as *not implemented* are closed here.

## IR1 -- publication is create-or-verify

`campaign_prepared_generation._publish_bytes` no longer returns on pathname
existence. An object that already carries an expected content identity is read
back and must equal the exact bytes this generation would have written; that is
byte equality against an owner-produced serialization, so it subsumes reparsing
the file through the component type. Conflicting content raises before
`CampaignStore` adoption and is never overwritten, because another adopted
generation may depend on whatever is actually on disk.

`frame_cache.write_frame_data_cache_entry` gained the same discipline for the
normalized entry it reuses, through a new
`authenticate_frame_data_cache_entry`: the entry manifest must reproduce the
identity that names it, and the manifest is then loaded through the existing
verifying reader, which checks every NPY member's hash, shape, and dtype. No
second validator was written.

## IR2 -- `prepare` owns changed-source detection and terminal idempotence

`_changed_preparation_inputs` compares two identities the campaign already
persisted: the approved manifest digest the DATA2 catalog was built from, and
each source's own byte-identity and control signatures, through a new
`changed_vasp_source_identities` that lives beside `authenticate_vasp_source_authority`
and shares its locator resolution. A material change routes into the existing
`_prepare_catalog` owner and commits a fresh generation; no rebuild flag, no
freshness database, no mtime heuristic, and no downstream fallback.

Reaching that path exposed a real defect in `_prepare_catalog`: it read two of
the `[partition]` keys and silently ignored the rest, so DATA5 construction
disagreed with the neutral partition policy the substrate consumes. The
translation now covers the whole namespace (`_partition_policies`).

Terminal idempotence is fixed at the view owner rather than in campaign state:
a terminal revision is rendered by `write_current_target_size_result_view`, a
nonterminal one by the nonterminal writer. The double write of the same payload
that was there before is gone.

## IR3 -- adoption is fenced to the token the build started from

`execute_current_prepare` captures `TargetSizeCampaignRevision.expectation()`
before construction and passes it to `ensure_current_target_size_authorities`
as `expected_start`. Identical concurrent prepares converge (the loser adopts
nothing because the winner published exactly what it would have); a snapshot
built against superseded state raises `TargetSizeStalePreparationError`. The
fence is a comparison: no campaign transaction or writer exclusion is held
across P1/P2 construction, which is what the two-writer acceptance test
demonstrates by running an entire competing prepare while the loser sits inside
publication.

## IR4 -- observation is one coherent, authenticated read

`project_campaign_lifecycle` takes one deferred SQLite read transaction
spanning the target-size head and every P5/P7 pointer row, and derives the
binding inside it. The old re-read-and-retry loop is deleted: it could not have
worked, because pointer publication moves `meta` without moving the target-size
revision. Each compact record is then loaded through its accepted read-only
typed store (`PostSelectionEvidenceStore`, `QualificationEvidenceStore`) and
must reproduce the digest the pointer named before `accepted` or a verdict is
read; missing, unparseable, and misidentified all map to `BLOCKED`.

The same integrity rule was applied to `qualification status`, whose
observation additionally now refuses to report a verdict whose record binds a
superseded qualification specification.

## IR5 -- `M` is not a batch size, including in durable evidence

`batch_size` is removed from `TargetSizePredictionEvidence` and its schema is
`mdstats.target-size.prediction-evidence.v2`. The deterministic execution
partition is `M` together with the accepted execution policy's
`valid_batch_size`, which is already inside the candidate trajectory identity
the evidence binds, so the field was derivable at best and false at worst. The
replay provenance check drops the `batch_size == evaluation_size` comparison
and authenticates the partition policy through the same owner the run used.

## IR6 -- the bounded P7 model is a real potential energy surface

The fixture's per-frame constant *force* offset alongside a constant *energy*
offset was not the derivative of anything, so the model had no PES and
production relaxation truthfully refused to converge. It is replaced by a
harmonic tether:

```text
E(x) = E_pair(x) + k/2 * sum_i |x_i - a_i|^2 + c
F(x) = F_pair(x) - k * (x - a)
```

with `a` and `c` solved per frame so the model still reproduces that frame's
authenticated energy and forces exactly at its canonical geometry. The tether
is coercive in all `3N` modes, including the translational ones the pair term
cannot bind, so a minimum exists and lies within `|F_label - F_pair(x0)| / k`
of the canonical geometry. Measured over the fixture's frames and displaced
modes, FIRE converges in 2-6 steps of the configured 25-step budget. No
production threshold, budget, or owner was changed.

Two negative-direction tests were reconciled with the repaired model: the
relaxation-divergence test now supplies the reference *relaxed geometry* from
an independently softer relaxor while keeping the pointwise reference labels
the product reproduces, and the dynamics-instability test asserts the selected
binding is unchanged rather than asserting a stale literal size.

## New acceptance

- `tests/test_mlff_campaign_prepare_boundary.py` -- preseeded/corrupt component,
  manifest, and NPY member; changed-source rebuild to a fresh generation;
  unchanged and unchanged-terminal no-ops; identical and stale concurrent
  prepares.
- `tests/test_mlff_campaign_observation_coherence.py` -- missing, malformed, and
  misidentified P5/P7 records reported as `BLOCKED` with no managed byte or DB
  row changed; non-hybrid answers across a real prepare adoption and across P5
  and P7 pointer publication.
- `tests/test_mlff_bounded_direct_inference.py` -- durable evidence records the
  population and not the device batch for `M > valid_batch_size`; retired
  full-batch evidence is not current authority.
- `tests/test_mlff_campaign_assembled_lifecycle.py` now runs the whole public
  campaign through reference supply, passing nonlocked qualification, explicit
  locked activation, the terminal `release_qualified` verdict, exact terminal
  reauthentication across a process boundary, a canonical generation advance,
  and an applied storage cleanup -- after which the locked cohort is still
  recorded as revealed.
- `tests/test_mlff_campaign_storage_composition.py` -- the empty archive plan is
  asserted as an owner result (`p1:frame_cache` and `p4:prepared_generations`
  are not archive-eligible, their bytes are untouched, and consumption still
  reaches no preparation owner) instead of being skipped.

---

# Second-review repair (amendment `..._IMPLEMENTATION_REVIEW_R2.md`)

This section records the repair of the two blocking findings raised by the
second independent implementation review. Nothing above is retracted; the R2
amendment closed IR1/IR2/IR3/IR5/IR6 and left IR4 partially open plus a closure-
evidence blocker.

## R2-IR1 -- `qualification status` uses the one coherent, authenticated boundary

`qualification status` had a second, weaker observation path beside the repaired
campaign projection. It loaded the target-size revision on its own, derived a
binding from it, and then read each P7 pointer in a separate `_meta()`
transaction; the qualification plan, each component evidence object, the locked
activation, and the release pointer were all interpreted out of raw JSON. Only
the terminal record went through `QualificationEvidenceStore`.

The repair consolidates rather than adding a third observer.

*Coherence.* `campaign_lifecycle._owner_snapshot` is now the named, shared
read-only boundary `campaign_owner_snapshot`, and `execute_qualification_status`
derives its revision, binding and every P7 pointer digest from exactly that one
deferred SQLite read transaction. `observe_current_qualification` no longer
opens a store or reads a pointer row at all: it takes the pointer mapping the
snapshot produced. No lifecycle revision table, snapshot registry, or second
currentness token was introduced.

*Integrity.* Every content-addressed P7 object whose fields reach an operator is
loaded through `QualificationEvidenceStore.get()` with its own accepted
deserializer -- `ProductionQualificationPlan`, `QualificationComponentEvidence`,
`LockedActivationRecord`, `ReleaseEvidenceIndex`, `ProductionQualificationRecord`
-- and must reproduce the digest the pointer named before any field is read.
Each is additionally checked against the identity it is supposed to belong to,
so authentic bytes describing a different binding or a different component are
not accepted as this answer's truth either.

*Existing owners, not parallel readers.* The attempt state is read through
`authenticate_attempt_state`, the single strict attempt authority, which is
non-creating -- `read_attempt_state` was not usable here because its path helper
creates the attempt root, and an observational command must not. The component
position locator and its immutable position object are read by one new shared
owner, `qualification.runtime.read_component_position`, extracted from
`QualificationSession.completed_component`; both the session and the observation
now use it, and it is the only reader of that representation. Mutable position
state is deliberately still not a CAS object, but a locator that does not
authenticate its position object degrades to `unreadable_position` rather than
choosing which evidence is believed.

*A defect this exposed.* The attempt identity was being re-derived as
`_expected_attempt_identity(selected_binding.content_digest)`, but the owner
derives it from the *qualification input* binding. Status was therefore naming a
directory the owner never wrote to, so every component read as `not_started` and
the attempt state always read as absent. The identity now comes from the
authenticated plan (`plan.attempt_identity`), which is the owner that actually
names the attempt; with no authentic plan there is no attempt to describe, and
status says so instead of guessing.

*Truthful pointer-level states.* `locked_state` and `release_state` distinguish
`absent` from `unreadable`. Reporting a tampered locked activation as "not
activated" would deny an irreversible disclosure, which is exactly the fact this
command exists to report honestly.

The observational capability is unchanged: `create=False`, no
`QualificationSession`, no provider/model/reference execution, no prepared-array
load, no wrapper creation, no managed write. `advance` remains advisory.

## R2-IR2 -- deterministic concurrency acceptance, and closure evidence

`test_answers_across_p5_and_p7_pointer_publication_are_never_hybrid` was
withdrawn. Its mutation published the P5 pointer and then the P7 pointer in two
separate transactions, so a graph with the first published and the second not is
a state that legitimately exists; accepting only the pre- and post-mutation
snapshots asserted that the pair was atomic, and the test could pass merely
because the scheduler never sampled the legitimate interval.

It is replaced by per-owner-boundary tests built on `tests/_mlff_observation_race.py`.
One status answer is paused inside its own open read transaction -- at
`_binding_for`, after the target-size head read and before the first pointer
read, which is exactly the window a hybrid answer would need -- and one real
publication transaction then attempts to commit with a short busy timeout. Under
this store's rollback journal the commit is excluded, which is direct evidence
that no pointer the answer interprets can move underneath it; an implementation
that read each pointer in its own transaction would hold no lock there and the
commit would succeed. The oracle is the boundary the owner really has: the
answer is the whole pre-publication graph, and the post-publication graph
appears only after the publication completes. No production sleep, poll, or
synchronization primitive was added; the pause is a test-only wrapper around one
module-level function and the mutation runs the real owner's real transaction.

The lifecycle oracle also had to be sharpened: a published terminal record with
a nonterminal verdict and no record at all are both `waiting`, so state alone
could not see the mutation. It now compares state *and* message.

## New acceptance

- `tests/test_mlff_qualification_status_observation.py` -- the real
  `qualification status` command and the real P7 stores/publishers, over one
  campaign driven to `release_qualified` with the locked cohort opened:
  - corruption matrix: qualification plan, one current component evidence
    object, locked activation, release evidence and terminal record, each
    missing / malformed / parseable-but-misidentified. In all fifteen cases the
    tampered semantic field is never reported as current truth, a typed
    blocked/unreadable condition is reported instead, the command still exits 0,
    and no managed byte or database row changes -- including that the object it
    could not authenticate is not repaired or recreated;
  - a position locator that no longer authenticates its immutable position
    object degrades to `unreadable_position`;
  - a corrupt attempt-state file degrades to `unreadable` and blocks;
  - coherence matrix: real publication of the qualification-plan,
    qualification-record, locked-activation and release-evidence pointers, and a
    real target-generation adoption, each proven to be excluded from one
    in-flight status answer.
- `tests/test_mlff_campaign_observation_coherence.py` -- the two deterministic
  single-boundary replacements described above.

## Structural evidence

Semgrep rules were validated against the pre-repair sources as known positives
(3 findings) before their zero-finding result on the candidate was relied on: no
`json.load`/`json.loads` in either public observation module; no `SELECT value
FROM meta` in the qualification observation/command path; no independent
`load_target_size_campaign_revision` in `qualification status`. Serena
caller closure confirms exactly two production consumers of
`read_component_position` (the session and the observation) and one production
consumer of `observe_current_qualification`.

## Affected-surface regression on the exact candidate

`pytest -k "mlff or storage or campaign"` in the `mace` environment, run twice
under identical conditions (`-p no:randomly -n 14`, 32-core host): once on this
candidate, and once in a clean worktree at the unmodified branch head `2f720cf`.
The worktree's own `mdstats` package was proven to be the one imported, so the
baseline is genuinely the unmodified code rather than the editable install.

- baseline (`2f720cf`, clean worktree): 117 failed, 1904 passed, 15 skipped;
- candidate: 117 failed, 1927 passed, 15 skipped.

The failure **sets are identical** -- `comm` over the sorted node-id lists gives
an empty difference in both directions. The 23 additional passes are the new
`qualification status` observation suite (22) and the net effect of replacing
one unsound coherence test with two sound ones.

Mapping of the 117 persistent failures: none is on this plan's acceptance
surface. They fall into two unrelated pre-existing families, both present
identically at the unmodified head:

- documentation/specification suites asserting release identities, manual
  status lines, and dependency-graph nodes that are not present in the tree
  (the great majority, all `*_specification.py`); the single one whose name
  mentions qualification,
  `test_mlff_data9a_specification.py::test_data9a_dependency_graph_contains_runtime_qualification_chain`,
  fails on a missing `MACE_DEPENDENCY_MANIFEST` graph node;
- a few stale non-documentation expectations unrelated to campaign
  observation -- a `PartitionRoleBudgetPolicy` default in
  `test_mlff_data4_raw_features_events.py`, a removed
  `campaign_cli.command_evaluate` attribute and two argument-parse
  `SystemExit`s in `test_mlff_mace_compatibility.py` /
  `test_mlff_mace_executable_config.py`.

No campaign-lifecycle, qualification-observation, P7, prepare-boundary,
prepared-generation, storage-composition, currentness, or assembled-lifecycle
test fails on the candidate.

## Required closure suites on the exact candidate

The list R2 section 3.4 requires was also run as one named selection on the same
candidate (`-p no:randomly -n 12`): **690 passed, 0 failed, 0 skipped** in
24m48s.

| requirement | suite |
| --- | --- |
| focused prepare / publication / CAS | `test_mlff_campaign_prepare_boundary.py`, `test_mlff_campaign_prepared_generation.py`, `test_mlff_campaign_prepared_generation_efficiency.py` |
| campaign + qualification observation purity / integrity / coherence | `test_mlff_campaign_observation_purity.py`, `test_mlff_campaign_observation_coherence.py`, `test_mlff_qualification_status_observation.py` |
| bounded direct inference / replay | `test_mlff_bounded_direct_inference.py`, `test_mlff_bounded_direct_inference_cuda.py` |
| P7 post-production qualification acceptance | `test_mlff_p7_post_production_qualification.py` |
| full assembled lifecycle through locked activation and generation advance | `test_mlff_campaign_assembled_lifecycle.py` |
| storage composition incl. the empty-archive owner result and locked-reveal retention | `test_mlff_campaign_storage_composition.py`, `test_mlff_storage_reset_core.py`, `test_mlff_storage_reset_integration.py` |
| P3 interruption / continuation / currentness | `test_mlff_target_size_first_boundary_interruption.py`, `test_mlff_target_size_continuation_corruption.py`, `test_mlff_campaign_currentness_races.py`, `test_mlff_campaign_stateful_properties.py` |
| project-required check | `test_docs_pdf_builder.py` (the repository's only CI gate; it builds documentation PDFs and is triggered by `docs/**/*.md`, none of which this change touches) |

No permanent documentation contract changed. The user guide's claim that `status`
and `qualification status` are observational in the strict sense is now more
true, not less, and no architecture manual or specification names the modules
that were changed, so no PDF republication is due.

## Candidate identity

Every result in this R2 section was produced on the working tree committed as
executable candidate `84868ec` ("qualification status: one coherent,
authenticated observation"). Only this progress record changed afterwards.

This section records repair and evidence; it does not grant closure. The R2
amendment's verdict is the reviewer's to change.
