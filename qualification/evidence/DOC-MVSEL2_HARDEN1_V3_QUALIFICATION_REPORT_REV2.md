---
kind: qualification-report
report_id: DOC-MVSEL2-HARDEN1-V3-QUAL-REPORT-REV2-1
protocol_version: 3.0.0
qualification_handoff_id: DOC-MVSEL2-HARDEN1-V3-QUAL-REV2-1
qualification_handoff_sha256: 889683eb7a0ef1a90ca1301b60b02298b2e71adcb1f353bcad95bfd134775a6f
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 2
workplan_sha256: 42a9075ecd96eb16a36ab9fc1d09c8bd4522022ef1749f6554dfa153c0faa52c
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity: 56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956
candidate_identity_policy: mdstats.mvsel2-harden1-v3.candidate-identity.v1
overall_status: FAIL
---

# DOC-MVSEL2-HARDEN1-V3 revision-2 Qualification Report

## Outcome

Revision-2 qualification does not pass. Q1, Q2, and Q4 passed. Q3 is
`BLOCKED` because the exact authenticated baseline aborts collection with exit
2, so the required differential comparator cannot run. Q5 and Q7 are
`BLOCKED` because the bound driver resolves a production configuration path
that does not exist; Q6 is dependency-blocked by Q5. Q8 remains the declared
nonblocking GPU deferment.

The earliest violated requirement is Q3 execution comparability. Revision-2
workplan section 10 explicitly routes an exact baseline that cannot execute
comparably to `DESIGN_REVISION_REQUIRED`. This report does not declare
`MERGE_READY`.

## Environment

- Host/runtime: `local-user-ProBuild`, Linux `6.8.0-136-generic`, x86_64.
- Conda environment: `mace`.
- Python/pytest: Python 3.11.15, pytest 9.1.1.
- Material dependencies: NumPy 2.4.4, SciPy 1.17.1, psutil 7.2.2,
  build 1.5.0.
- CPU execution: `OMP_NUM_THREADS=1`; GPU qualification was not executed.
- Material environment: `CUDA_HOME=/usr/local/cuda-12.6` and qualification-local
  `MPLCONFIGDIR`; full capture is in `q3_environment.txt`.
- Working directory:
  `$HOME/QE/lammps-proj/zeolite/90_scripts/mdstats`.
- Candidate import origin:
  `$HOME/QE/lammps-proj/zeolite/90_scripts/mdstats/mdstats/__init__.py`.
- Baseline import origin:
  `/tmp/mdstats-mvsel2-q3-baseline-e24d5168/mdstats/__init__.py`.

## Candidate preflight

- `HEAD == candidate_commit`: PASS.
- Candidate content identity recomputed/matched: PASS,
  `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`.
- Revision-2 workplan SHA-256 matched: PASS,
  `42a9075ecd96eb16a36ab9fc1d09c8bd4522022ef1749f6554dfa153c0faa52c`.
- Comparator Git blob matched: PASS,
  `8816669d3a0dc6ad862bff47ff113470e271835b`.
- Driver Git blob recorded:
  `fe649742674ecdff7286452ced5ecf044402098e`.
- Candidate tracked/staged state clean: PASS.
- Undeclared untracked execution-affecting files absent: PASS. Initial
  untracked files were limited to the two handoff-declared copies under
  `qualification/tmp/`.
- Production DB initial SHA-256:
  `4646efc947f37a05894e0099f7db56b8911d8eb497315cf60f9f41ae786c1b92`.
- Submodules/LFS: not material to this handoff; none were invoked.

## Check results

| Check | Gate(s) | Capability | Mandatory now | Status | Exit | Attempts | Evidence |
|---|---|---|---|---|---:|---:|---|
| Q1 | H1/H5 | TARGET_RUNTIME | yes | PASS | 0 | 1 | `q1_focused_v2_rev2.log`: 40 passed |
| Q2 | H5 | TARGET_RUNTIME | yes | PASS | 0 | 1 | `q2_adjacent_v1_rev2.log`: 10 passed, 1 warning |
| Q3 | H5 | TARGET_RUNTIME | yes | BLOCKED | 2 | 1 | baseline exit 2; candidate exit 1; comparator not run |
| Q4 | H5 | BUILD/INSTALL | yes | PASS | 0 | 2 | isolated wheel/install/import and package-content checks passed |
| Q5 | H2/H3 | PRODUCTION_DATA | yes | BLOCKED | 1 | 1 | bound `campaign.toml` path absent |
| Q6 | H4 | PRODUCTION_DATA | yes | BLOCKED | - | 0 | Q5 clone prerequisite unavailable |
| Q7 | H4/H5 | PRODUCTION_DATA | yes | BLOCKED | 1 | 1 | bound `campaign.toml` path absent |
| Q8 | - | GPU | no | DEFERRED | - | 0 | `DEFERRED_NOT_RUN` per handoff |

## Per-check execution provenance

### Q1

- Command/cwd: the handoff-bound focused pytest command, executed from the
  candidate root with `conda run -n mace`.
- Completion: 2026-08-19 01:44:11 -0500.
- Input identity: exact candidate and five handoff-listed v2 test files.
- Result: PASS, 40 passed in 3.55 seconds.
- Evidence SHA-256:
  `7c06c74ef3ca187b8ef7fd04ca8c3adb59f354ffcdff0c1c3df023b1f30d52ab`.

### Q2

- Command/cwd: the handoff-bound adjacent-v1 pytest command, executed from the
  candidate root with `conda run -n mace`.
- Completion: 2026-08-19 01:44:22 -0500.
- Result: PASS, 10 passed and one velocity-reconstruction warning in 4.56
  seconds.
- Evidence SHA-256:
  `81c63db027d747611c353d7b81d14d0e7d66601265e19f85c18d3569371a0588`.

### Q3

- Command/cwd: the exact handoff Q3 script, using candidate root and a fresh
  local clone at `/tmp/mdstats-mvsel2-q3-baseline-e24d5168`.
- Baseline: exact commit
  `e24d5168ce01bf2d773339e1a91d5ded4871a57f`, clean checkout and verified
  candidate-local import.
- Candidate: exact commit
  `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`, verified candidate-local import.
- Baseline result: exit 2 during collection, 2 errors and 20 deselected. The
  missing `tests/data/mesh_topology_revision_stage1_cases.json` is not tracked
  at the baseline commit. Collection also raises
  `ModuleNotFoundError: test_mlff_data5_partition_roles` despite its test file
  being tracked at the baseline commit.
- Candidate result: exit 1, 3,187 passed, 307 failed, 16 skipped, and 20
  deselected in 517.05 seconds. JUnit contains 3,510 testcases, 307 failures,
  0 errors, and 16 skipped.
- Guard result: because baseline exit was greater than 1, the handoff-required
  comparator was correctly not invoked and no `q3_differential.json` was
  produced.
- Retry: not attempted. The missing baseline tracked artifact is deterministic,
  not transient; a clean retry cannot make the exact baseline comparable.
- Evidence: `q3_environment.txt`, `q3_baseline.xml`, `q3_candidate.xml`, both
  logs, `q3_pytest_exitcodes.txt`, and
  `q3_baseline_collection_diagnosis.txt`; their digests are indexed in
  `rev2_evidence_sha256.txt`.
- Result: BLOCKED; routing `DESIGN_REVISION_REQUIRED`.

### Q4

- Command/cwd: exact handoff clean wheel/build/install/import/content sequence.
- Attempt 1: isolated build failed before wheel construction because the
  sandbox could not resolve `pypi.org` to install `setuptools>=68`.
- Retry mode: `CLEAN_RETRY`, the single permitted retry. `build/`, `dist/`, and
  `qualification/tmp/wheel-install` were removed and recreated; network access
  was enabled without changing candidate or build policy.
- Attempt 2 result: PASS. Import executed from `qualification/tmp`, resolved
  beneath the absolute isolated install target, version was exactly
  `0.20.242a0`, and the wheel contained 377 entries with no `workplans/` entry.
- Completion: 2026-08-19 01:54:55 -0500.
- Wheel: `dist/mdstats-0.20.242a0-py3-none-any.whl`.
- Wheel SHA-256:
  `8e87588a80aa61ce6ca876355b586aad23c9530a08f2aec6af977205d920dd54`.

### Q5

- Command/cwd: exact handoff Q5 driver command from candidate root.
- Result: exit 1 before clone/runtime execution. The driver resolved
  `$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/campaign.toml`,
  which does not exist.
- Diagnostic: an apparent config exists at
  `$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml`,
  but the exact handoff did not authorize an override. It was not substituted.
- Production DB before/after SHA-256 matched exactly.
- Retry: not attempted; the missing bound input path is deterministic.
- Result: BLOCKED.

### Q6

- Not executed because the handoff requires Q5's cloned DB at
  `qualification/tmp/mvsel2-q5/.mdstats/campaign.sqlite3`; Q5 stopped before
  creating it.
- Result: BLOCKED by prerequisite.

### Q7

- Command/cwd: exact handoff Q7 driver command from candidate root.
- Result: exit 1 before clone/performance execution for the same missing bound
  `campaign.toml` path as Q5.
- Production DB before/after SHA-256 matched exactly.
- Retry: not attempted; no transient measurement was reached.
- Result: BLOCKED.

### Q8

- Result: `DEFERRED_NOT_RUN`, nonblocking for the current workstation
  acceptance contract. No GPU qualification claim is made.

## Retry history

- Q1/Q2: `NONE`, one fresh attempt each.
- Q3: `NONE`; clean retry was not used because exact-baseline collection is
  deterministically impossible with the missing tracked artifact.
- Q4: one `CLEAN_RETRY` after a network-only isolated-build failure; no
  candidate, scientific, build, or package policy changed.
- Q5/Q7: `NONE`; both stopped on a deterministic missing handoff input before
  production-clone mutation or measurement.
- Q6/Q8: no attempts.

## Evidence reuse

No REV1 PASS result was reused as the sole REV2 result. Q1 and Q2 were rerun
fresh. REV1 Q3 remains historical diagnostic evidence only. REV1 Q4 was
invalidated and rerun. Q5-Q7 had no prior execution evidence.

## Failures and blockers

- Earliest violated requirement: Q3 baseline/candidate execution
  comparability, workplan revision-2 section 4.2 and handoff Q3.
- Q3 evidence: `q3_baseline.log`, `q3_baseline.xml`,
  `q3_pytest_exitcodes.txt`, and `q3_baseline_collection_diagnosis.txt`.
- Independent production blocker: Q5/Q7 driver expects a configuration at a
  path not present in the bound production workspace.
- Routing: `DESIGN_REVISION_REQUIRED` for the Q3 baseline-oracle contradiction.
  Q5-Q7 additionally require a corrected source-bound handoff/input path.

## Evidence artifacts

- Environment/preflight: `q3_environment.txt`,
  `production_db_sha256_before_rev2.txt`.
- Focused/adjacent tests: `q1_focused_v2_rev2.log`,
  `q2_adjacent_v1_rev2.log` and exit-code files.
- Differential attempt: `q3_baseline.log`, `q3_baseline.xml`,
  `q3_candidate.log`, `q3_candidate.xml`, `q3_pytest_exitcodes.txt`, and
  `q3_baseline_collection_diagnosis.txt`.
- Distribution: `q4_wheel_sha256_rev2.txt`, `q4_rev2.exitcode`, and the wheel
  under `dist/`.
- Production blockers: Q5/Q7 logs and status files.
- Integrity: `postflight_rev2.txt`, `rev2_evidence_sha256.txt`.

## Candidate postflight / source immutability

- Candidate commit unchanged: PASS.
- Candidate content identity unchanged: PASS,
  `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`.
- Tracked/staged candidate source/output unchanged: PASS; both diffs empty.
- Production DB unchanged: PASS, SHA-256
  `4646efc947f37a05894e0099f7db56b8911d8eb497315cf60f9f41ae786c1b92`.
- Writes were confined to declared `qualification/`, `build/`, `dist/`, and
  exact `/tmp` baseline-clone paths.
- Untracked state is confined to declared qualification evidence/scratch and
  isolated-install outputs; no untracked product-source shadowing file exists.

