---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision: 10
protocol_version: 5.8.0
entry_p6_accepted_executable_commit: f55d59b28c9db890dcb6a3c167a067ef5f37e8a2
entry_p6_accepted_executable_tree: e9a6d5f9d1a798f07dab88bd56dafcc73fe0e491
entry_p6_evidence_commit: 82371ecdab5f981255d0853a11477596be2623d3
implementation_start_commit: ac61edd12cb941a5c6bcdfe06832cd567ad0f936
p7_executable_source_tree_digest: e3ef475a1f2ff1fd96e5a5e566aac28f365ab455c9688072e756c18a1c480b55
status: implementation-complete-pending-design-review
recorded_date: 2026-08-31
---

# P7 revision 10 — implementation evidence

Implementation authority: `P7_REVISION_10_AUTHORITY.md` composed with
`P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md`,
`P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md`,
`P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md`, and the frozen
parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`.

## 1. P7-0 predecessor and executable-baseline rebind gate

P6 revision 13 is `PASS` per `P6_REVISION_13_COMPLETION_AUTHORITY.md`.
Implementation began at branch head `ac61edd`. The compare from the accepted
executable commit `f55d59b2` to `ac61edd` contains only non-executable files:

```text
workplans/active/mlff-target-size-v7-packages/P6_IMPLEMENTATION_EVIDENCE.md
workplans/active/mlff-target-size-v7-packages/P6_REVISION_13_COMPLETION_AUTHORITY.md
workplans/active/mlff-target-size-v7-packages/P7_REVISION_10_AUTHORITY.md
workplans/active/mlff-target-size-v7-packages/P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md
workplans/active/mlff-target-size-v7-packages/README.md
```

No source, test, tool, or configuration change intervened, so the accepted P1-P6
executable candidate was entered without reconciliation.

Owners identified and consumed rather than recreated:

| Concern | Accepted owner |
|---|---|
| current selected binding | `campaign_post_selection.load_current_selected_training_context` |
| post-selection CV | `campaign_post_selection_runtime.resolve_current_cv_{plan,acceptance}` |
| final production completion (the product boundary) | `campaign_post_selection_runtime.resolve_current_final_production_completion` |
| post-selection immutable store / currentness fence | `post_selection_store` |
| checkpoint provider authentication | `post_selection_execution.authenticate_post_selection_provider` |
| deployment export | `mace_deployment.export_mace_deployment_artifact` |
| resources | `resources` |
| current cache / safe cleanup | unchanged P6 transitional owners |

### Baseline before any edit

Measured fresh on this machine at the accepted executable commit `f55d59b2`
(`conda run -n mace python -m pytest -n 16 -q -p no:randomly`):

```text
205 failed, 2839 passed, 15 skipped, 100 errors in 425s
```

The recorded P6 figure (`202 failed, 2843 passed, 14 skipped, 100 errors`)
differs by a handful of environment-sensitive tests; the freshly measured
baseline is the comparison used below.

## 2. Implementation

New package `mdstats/training_data/qualification/`:

```text
errors.py               typed qualification failures
identity.py             executable candidate, environment fingerprint, spec identity
runtime_capability.py   real LAMMPS/ML-IAP probe and process-group execution
_lammps_worker.py       out-of-process deployed-runtime worker
publication.py          intake/authentication of the accepted P5 publication
binding.py              QualificationInputBinding and neutral evidence roles
spec.py                 frozen specification resolution from configuration
plan.py                 candidate-independent physical plan, qualification plan
reference.py            external reference request/import/authentication
geometry.py             deterministic geometry, topology, relaxation helpers
providers.py            model access through the accepted P5 provider owner
components.py           one immutable typed component-evidence record
deployment.py           P7-B deployment parity
physical.py             P7-C local PES and strain response
relaxation.py           P7-D relaxation
dynamics.py             P7-D finite-temperature dynamics
calibration.py          P7-E uncertainty calibration
locked.py               P7-F one-shot locked activation and result
record.py               terminal record and release-evidence index
store.py                canonical P7 persistence, attempts, retention fence
runtime.py              the single qualification owner
commands.py             qualification status | run | activate-locked
```

Modified predecessor source (two files):

- `_campaign_cli_core.py` — the `qualification` command family, its three
  command wrappers, the generated `[qualification]` configuration block, the
  guide text, and composition of the new retention fence into the ownership
  boundary. `PIPELINE`, `advance`, and every training-lifecycle owner are
  unchanged.
- `storage_accounting.py` — `CompositeRetentionFence`, a pure reduction that
  consults several lifecycle fences and can only ever retain more.

### Reconciliations and deliberate boundaries

1. **D1 realized.** No `FinalProductionPublication` class was created. The
   accepted P5 `resolve_current_final_production_completion` is the publication
   owner; `AuthenticatedFinalPublication` is a read-only descendant view that
   cannot be deserialized from bytes, by construction.
2. **Committee policy `single_best_final_seed` is blocked, not invented.** The
   accepted P5 owner does not durably publish the pre-qualification M3
   development evidence a single-best member decision would require: run
   evidence carries the monitor-metric *digest*, not its value, and the
   representative record is not stored. Qualification therefore fails closed
   with an explicit typed error rather than introducing a member-selection rule
   it is forbidden to own. This is reopen trigger 1 of revision 10 §10 and is
   recorded as a blocking item in section 5. The generated default,
   `all_qualified_final_seeds`, is fully implemented.
3. **Executable currentness is the source-tree digest**, not the branch head, so
   documentation-only commits cannot stale executable evidence while any source
   change does. Git commit/tree are recorded for audit ordering only.
4. **Machine capacity is recorded but excluded from environment identity**, and
   installed rather than free memory is captured, so an immutable evidence
   record is reproducible on the same host.
5. **`waiting_for_reference` is not persisted** as durable component evidence: it
   is the absence of evidence, and persisting it would make a later supplied
   reference unreachable.

## 3. Executed checks

All commands run in the `mace` conda environment.

### P7 acceptance suite

```bash
conda run -n mace python -m pytest tests/test_mlff_p7_post_production_qualification.py -n 16 -q -p no:randomly
```

```text
44 passed
```

Coverage includes: structural single-publication/no-selection-authority proof;
retired-architecture and successor-storage absence; locked-evidence
unreachability from training/selection/CV/production and from the run path;
`advance` isolation; publication reopen determinism; member byte-mutation
fail-closed; unsupported committee policy fail-closed; physical-plan
candidate-independence (including a structural proof that the plan owner cannot
reach a model or a member); reference request publication, protocol mismatch,
and partial-bundle rejection; the mandatory assembled integration through the
real parser and owners; executable/environment/specification/member identity
staleness and documentation-change non-staleness; specification-change scope;
tampered-record hard failure; stale-generation publication fence; resume reusing
only authenticated evidence; partial component publication rejection; cleanup
preservation of referenced artifacts and release evidence; attempt reference
release and post-crash reconstruction; provider release on success and
exception; byte-identical evidence under bounded concurrency; deployment
divergence, dynamics instability, relaxation divergence, and committee-member
failure all rejecting the exact publication without substitution; deterministic
recovery of a known calibration scaling factor; `not_applicable` calibration for
a single-model product; locked activation preconditions, second-activation
refusal, locked failure, and post-hoc policy loosening; strain-mode request and
qualification; topology-change detection independent of averaged error; and a
bounded **real** LAMMPS/ML-IAP execution through the deployed-artifact path.

### Affected predecessor acceptance surface

```bash
conda run -n mace python -m pytest tests/test_mlff_target_size_p6_destructive_closure.py -q -p no:randomly   # 30 passed
conda run -n mace python -m pytest tests/test_mlff_campaign_cli.py -q -p no:randomly                          # 11 passed
conda run -n mace python -m pytest tests/test_mlff_target_size_p4f_storage_docs_structure.py -q -p no:randomly # 18 passed
conda run -n mace python -m pytest tests/test_mlff_doc_arch1_specification.py -q -p no:randomly                # 8 passed
conda run -n mace python -m pytest tests/test_docs_pdf_builder.py -q -p no:randomly                            # 13 passed
```

Three predecessor tests asserted the *previous* public surface and were updated
to the accepted new one while keeping their protected concerns intact:

- `test_parser_exposes_the_current_lifecycle_surface` now also pins the frozen
  `qualification` semantic split;
- `test_p6_public_command_surface_is_the_current_lifecycle_only` adds
  `qualification` and additionally asserts it is absent from `PIPELINE`;
- `test_p4f_req3_user_guide_does_not_claim_a_retired_lifecycle` now requires the
  guide to describe qualification as a non-selecting consumer.

No accepted P6 scientific, storage, restart, or cleanup semantics changed.

### Repository-wide regression on the frozen candidate

```bash
conda run -n mace python -m pytest -n 16 -q -p no:randomly
```

```text
202 failed, 2887 passed, 14 skipped, 100 errors in 645s
```

Set difference against the freshly measured baseline: **zero new failing node
IDs and zero new erroring node IDs.** Three baseline-flaky `test_mlff_train2b_runtime`
tests passed in the candidate run that had failed in the baseline run.

## 4. Documentation

- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md` — the
  qualification owner graph, the no-selection boundary, and the successor
  storage handoff entry points; the assembled
  `mlff_training_data_architecture.md` was regenerated by its assembler.
- `docs/guides/mlff_campaign_cli_user_guide.md` — the qualification command
  family, the three non-failure outcomes, and the locked-test contract.
- `docs/specs/training_data/mlff_p7_post_production_qualification_spec.md` — new
  behavior specification.
- `docs/INDEX.md`, `README.md`, and the machine-readable dependency graph's
  forbidden-path list.

## 5. Unresolved / blocking

1. **`single_best_final_seed` publication policy is unavailable.** See section 2
   item 2. Closing it requires a predecessor decision - either P5 durably
   publishes its pre-qualification member-ranking evidence, or the policy is
   retired - and either is a reopen of the affected P5/P7 surface, not something
   qualification may decide.
2. **Derived PDFs are stale.** `mlff_training_data_architecture.pdf` and
   `mlff_campaign_cli_user_guide.pdf` were not regenerated: the pinned
   `mace-dependencies/typst-*` toolchain is absent from this environment. The
   Markdown authorities are current and the PDF planner tests pass.
3. **Final target-machine qualification has not been run.** Everything above is
   functional and regression evidence. The deferred real-production claim
   requires the exact frozen candidate and the exact frozen publication on the
   intended target machine with real external reference evidence, and is not
   claimed here.
