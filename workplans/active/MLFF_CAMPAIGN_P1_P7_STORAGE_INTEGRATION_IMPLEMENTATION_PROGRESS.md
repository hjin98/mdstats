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

### Partial Stage 5 - storage composition (INT-F, FINAL-C)

- new `prepared_generation_view` owner adapter classifies `.mdstats/prepared` as
  restart state the current generation requires, with reachability derived from
  prepared manifests rather than from pathnames. No reference-count database, no
  second cache, no new destructive path.

### FINAL-A / FINAL-B

- the first rung discards its uncommitted attempt workspace before fresh
  execution, so partial bytes from an interrupted attempt can never authenticate
  as that attempt's boundary state;
- stale-P3-writer fencing is established through the real CAS transition.

## Executed evidence

New focused/acceptance suites, all executing the real owners with numerical
doubles strictly below them:

- `tests/test_mlff_campaign_prepared_generation.py`
- `tests/test_mlff_bounded_direct_inference.py`
- `tests/test_mlff_campaign_observation_purity.py`
- `tests/test_mlff_campaign_currentness_races.py`
- `tests/test_mlff_target_size_first_boundary_interruption.py`

Affected-surface regression, `pytest -k "mlff or storage or campaign"` on 24
workers in the `mace` environment, compared against the same selection run on
the unmodified branch baseline:

- baseline: 307 failed, 1577 passed, 15 skipped, 8 errors;
- candidate: identical failure set apart from one user-guide documentation
  assertion that encoded the pre-repair "advance never runs qualification"
  claim, which was corrected with the lifecycle change and now passes.

No failure in that suite was introduced by this work. The 307 pre-existing
failures are recorded below.

Structural claims were validated with Semgrep rules checked against known
positive and negative constructs before their zero-finding results were relied
on: no production path submits a whole scientific population to `predict_batch`;
no evidence-store opener creates its root unconditionally; the prepare-only
builder is reachable only from `prepare`. Symbol-level caller closure confirms
exactly two production consumers of the prepared-generation loader.

## Not implemented - the integration remains reopened

The following composed obligations are **not** satisfied and no part of this
progress should be read as closing them:

- the complete fresh-workspace public lifecycle contract of root section 6.1
  (`doctor` through qualification with restart boundaries at every marked point);
- the full FINAL-A interruption matrix (cases 4-7: each required predecessor
  continuation component deleted or corrupted after a committed boundary,
  exercised through the campaign path);
- FINAL-C / R2-F storage composition beyond retention classification: the
  dedup, archive, verify, restore and maintenance operations have not been
  exercised against the prepared representation, and no downstream consumer has
  been re-run after each transformation;
- R2-G irreversible locked-disclosure history across generation advance and
  storage transformation;
- the Hypothesis stateful/property coverage of root section 6.9 and final
  section 5.6 (`hypothesis` is not installed in the project environment);
- the bounded real-MACE CUDA smoke required by INT-B and P4-STAGE-E §6.9-6.10;
- the performance/I-O evidence of root section 6.10 and R2 §4.9.

## Known pre-existing failures, not introduced here

307 failures in the affected selection reproduce identically on the unmodified
branch baseline. They fall into two groups:

- the assembled qualification fixture reaches
  `required_component_rejected:relaxation`, which fails P7 and then cascades
  through every suite built on a qualified campaign - most of
  `test_mlff_storage_reset_integration.py` and the P7 acceptance suites;
- several documentation/specification suites reference spec files that are not
  present in the tree.

They are recorded rather than repaired because they are outside the changes
above; they are, however, part of the assembled surface and must be resolved
before any assembled closure claim.

Separately, running `prepare` again on a campaign whose generation is already
terminal fails inside the result-view writer, which refuses to write terminal
state. This predates the work here and is a genuine defect in `prepare`
idempotence for terminal generations.
