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
- stale-P3-writer fencing is established through the real CAS transition.

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
- the candidate introduced nine failures, each traced and repaired:
  - one user-guide documentation assertion that encoded the pre-repair "advance
    never runs qualification" claim, corrected with the lifecycle change;
  - eight P5 provider-lifetime guards whose `_optimizer_policy_for` stand-in
    omitted `valid_batch_size`; the accepted execution policy owns that bound,
    so a stand-in without it was not standing in for the real thing.

An earlier comparison in this cycle was run against a baseline that already
contained the first commit's changes, and so under-reported the introduced
failures. The comparison above is against the true unmodified head.

## Not implemented - the integration remains reopened

The following composed obligations are **not** satisfied and no part of this
progress should be read as closing them:

- the tail of root section 6.1 - supplying the authenticated reference bundle,
  completing nonlocked qualification, explicit locked activation, and a terminal
  release verdict - is blocked by the P7 fixture defect below;
- FINAL-A cases 4-7: each required predecessor continuation component deleted or
  corrupted after a committed boundary, exercised through the campaign path. The
  first-rung half of the distinction is closed and the corrupt-predecessor half
  is covered at the same owner by the existing P3A4/P3A7 restart negatives, but
  not through the assembled campaign;
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
