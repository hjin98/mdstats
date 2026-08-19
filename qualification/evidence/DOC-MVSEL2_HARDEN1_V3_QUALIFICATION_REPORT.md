---
kind: qualification-report
report_id: DOC-MVSEL2-HARDEN1-V3-QUAL-2-REPORT-1
protocol_version: 3.0.0
qualification_handoff_id: DOC-MVSEL2-HARDEN1-V3-QUAL-2
qualification_handoff_sha256: 4376ad1c19db83a347cbeccaba29d8e32bd0d9503a7a5ebb169f55b744eb2f3a
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 1
workplan_sha256: ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity: 56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956
candidate_identity_policy: mdstats.mvsel2-harden1-v3.candidate-identity.v1
overall_status: FAIL
---

# DOC-MVSEL2-HARDEN1-V3 Qualification Report

## Environment

- Execution window: 2026-08-19 00:15-00:40 America/Chicago.
- Host: Linux 6.8.0-136-generic x86_64, glibc 2.35.
- Conda environment: `mace`; Python 3.11.15.
- Relevant resolved packages in the final frozen execution environment: mdstats 0.20.242a0 from the candidate checkout, NumPy 2.4.4, SciPy 1.17.1, psutil 7.2.2, build 1.5.0.
- CPU workstation execution; GPU not exercised.
- Working directory: `$HOME/QE/lammps-proj/zeolite/90_scripts/mdstats`.
- Production input DB: `$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3`.
- Production DB pre/post SHA-256: `4646efc947f37a05894e0099f7db56b8911d8eb497315cf60f9f41ae786c1b92`.
- Qualification driver blob SHA: `fe649742674ecdff7286452ced5ecf044402098e`.

## Candidate preflight

- `HEAD == candidate_commit`: PASS.
- Candidate content identity recomputed/matched: PASS, `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`.
- Workplan and handoff digests matched: PASS.
- Candidate tracked/staged state clean: PASS.
- Undeclared untracked execution-affecting files absent: PASS. Present untracked paths were limited to the declared identity/handoff coordination files and qualification outputs.
- Submodules: none reported by `git submodule status`.
- Source origin: source checkout for Q1-Q3, as required. Q4 was required to prove installed-artifact origin and failed that assertion.
- Final-environment preflight evidence: `qualification/evidence/preflight_final_environment.log`.

## Check results

| Check | Gate(s) | Capability | Mandatory now | Status | Exit | Attempts | Evidence |
|---|---|---|---:|---|---:|---:|---|
| Q1 | H1-H4 | TARGET_RUNTIME | yes | PASS | 0 | 1 final | `qualification/evidence/q1_focused_v2.log` |
| Q2 | H1-H4 | TARGET_RUNTIME | yes | PASS | 0 | 1 final | `qualification/evidence/q2_adjacent_v1.log` |
| Q3 | H5 | TARGET_RUNTIME | yes | FAIL | 1 | 2 final-environment attempts | `qualification/evidence/q3_full_non_slow.log` |
| Q4 | H5 | TARGET_RUNTIME | yes | FAIL | 1 | 2 | `qualification/evidence/q4_wheel_install.log`, `qualification/evidence/q4_wheel_sha256.txt` |
| Q5 | H3/H5 | TARGET_RUNTIME, PRODUCTION_DATA | yes | NOT RUN | - | 0 | Stopped after mandatory Q3/Q4 failures |
| Q6 | H4/H5 | TARGET_RUNTIME, PRODUCTION_DATA | yes | NOT RUN | - | 0 | Depends on successful Q5 output |
| Q7 | H4/H5 | TARGET_RUNTIME, PRODUCTION_DATA | yes | NOT RUN | - | 0 | Expensive check not run after mandatory failures |
| Q8 | H5 | TARGET_HARDWARE | no | DEFERRED | - | 0 | GPU status: DEFERRED_NOT_RUN |

Q8 deferral:

- `mandatory_for_current_acceptance: false`
- `deferred_to: explicit GPU qualification`
- Reason: no GPU execution was requested by the handoff for current CPU/workstation acceptance, and CPU evidence cannot substitute.

## Per-check execution provenance

### Q1

- Exact command: the handoff's five-file focused pytest command.
- Final-environment completion: 2026-08-19 00:22:34 -05:00.
- Result: 40 passed in 3.99 seconds; exit 0.
- Log SHA-256: `b393f62da4d360d0ec2badcfa8c93bbf69118707a79bf9928aa5c72dd3039d4b`.

### Q2

- Exact command: `conda run -n mace pytest -q tests/test_mlff_target_data2c_repair1.py`.
- Final-environment completion: 2026-08-19 00:22:44 -05:00.
- Result: 10 passed, 1 warning in 4.88 seconds; exit 0.
- Log SHA-256: `ac50190e7a0811342d7fa4bfe2b48ec27ebc9a31c388edfe95f4e2a5cb8f2f02`.

### Q3

- Exact command: `conda run -n mace pytest -q -m 'not slow'`.
- A preliminary environment lacked psutil and failed collection. The user then changed the environment; preliminary Q1-Q3 evidence was invalidated and Q1-Q3 were restarted.
- A final-environment attempt was interrupted while the execution runner was being reconciled; its zero-byte log was removed under Q3's declared `CLEAN_RETRY`.
- Authoritative clean retry completed 2026-08-19 00:39:12 -05:00.
- Result: 3,187 passed, 307 failed, 16 skipped, 20 deselected, 1,100 warnings in 518.73 seconds; exit 1.
- Earliest retained failures include broken example-bootstrap/API contracts and numerous version/specification/current-architecture assertions inconsistent with candidate 0.20.242a0.
- Log SHA-256: `b5456e6170e9d41c9519767c04ed28e7149c55c2970ce4eb3dd6b41ed29c5e7f`.

### Q4

- Exact command sequence: the handoff's clean isolated wheel build, target install, installed-origin/version assertion, wheel-content inspection, and artifact hashing.
- Attempt 1: isolated build prerequisite download failed because sandbox DNS/network access was unavailable.
- `CLEAN_RETRY`: removed only `build/`, `dist/`, and `qualification/tmp/wheel-install/`; repeated the exact command with package-index access.
- Attempt 2 built and installed `mdstats-0.20.242a0-py3-none-any.whl`, then failed the installed-origin assertion because Python imported `$HOME/QE/lammps-proj/zeolite/90_scripts/mdstats/mdstats/__init__.py` from the source checkout instead of the target install.
- Final exit: 1.
- Wheel SHA-256: `34b4a496f760b7a7b792f03db3f0dd0e0461de5fc443c05d9d510123d4f9c901`.
- Final log SHA-256: `1b6d35303d9f02c9bff3bfcb6f869be88351e049cc2f055aefef7cc292c39e63`.
- Because the sequence stopped at installed-origin validation, the later wheel-content assertion did not execute and is not inferred PASS.

## Retry history

- Q3 retry mode: `CLEAN_RETRY`; one final-environment retry after deleting only the empty Q3 evidence log. No candidate, scientific, configuration, backend, dataset, or resource-policy change occurred between the final-environment attempts.
- Q4 retry mode: `CLEAN_RETRY`; one retry after deleting only the declared ephemeral build/install outputs. Candidate and test policy were unchanged.
- Earlier user-installed environment dependencies changed the runtime identity. Evidence from before each environment change was invalidated rather than reused.
- No Q5-Q7 retry or execution occurred.

## Evidence reuse

No prior qualification evidence was reused. Q1 and Q2 were rerun after the final environment change. Historical production benchmark JSON was not substituted for Q5-Q7.

## Failures and routing

### Earliest mandatory candidate failure

Q3 failed broadly with 307 failures. Representative classes:

- tests asserting historical package versions such as 0.20.140a0 against candidate 0.20.242a0;
- specification/architecture tests expecting historical sections no longer present in current architecture;
- example bootstrap and compatibility-launcher/API contract failures;
- campaign/runtime and documentation synchronization failures.

Routing: `RETURN_TO_IMPLEMENTATION`.

### Independent distribution failure

Q4 built and installed a wheel but failed to demonstrate import from the installed artifact. The exact handoff command executed from repository root, where source-checkout import precedence defeated the target `PYTHONPATH` assertion.

Routing: `RETURN_TO_IMPLEMENTATION` for correction of the qualification command/harness and any affected packaging contract; issue a new handoff before rerunning affected checks.

### Unexecuted production checks

Q5-Q7 remain `NOT RUN`, not PASS. Mandatory Q3 and Q4 failures already prevent current acceptance; expensive production execution was stopped according to the declared cheap-to-expensive ordering.

## Evidence artifacts

- `qualification/evidence/preflight.log`
- `qualification/evidence/preflight_after_environment_change.log`
- `qualification/evidence/preflight_final_environment.log`
- `qualification/evidence/q1_focused_v2.log`
- `qualification/evidence/q2_adjacent_v1.log`
- `qualification/evidence/q3_full_non_slow.log`
- `qualification/evidence/q4_wheel_install.log`
- `qualification/evidence/q4_wheel_sha256.txt`
- `qualification/evidence/postflight.log`
- `dist/mdstats-0.20.242a0-py3-none-any.whl` (ephemeral failed-check artifact)

## Candidate postflight / source immutability

- Candidate content identity unchanged: PASS, `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`.
- `HEAD` unchanged: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`.
- Tracked candidate source/output unchanged: PASS; no staged or tracked diff.
- Production DB unchanged: PASS, SHA-256 `4646efc947f37a05894e0099f7db56b8911d8eb497315cf60f9f41ae786c1b92`.
- Changes are confined to declared workplan coordination artifacts and `qualification/`, `build/`, and `dist/` ephemeral outputs.
- No product-source mutation was performed.

This report does not declare `MERGE_READY`. The candidate returns to implementation.

