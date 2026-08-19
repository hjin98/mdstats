---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-S9-SIMPLE
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
status: PREPARED_FOR_QUALIFICATION
---

# MVSEL2 hardening — simplified S9 qualification run card

## Purpose

Finish the substantive MVSEL2/REPAIR2 workstation qualification without repeating the metadata/handoff failures from the earlier Protocol-v3 dogfood.

This run card follows the materiality-first Protocol v3. It freezes the software result and material inputs, not exact shell spelling. Harmless cwd, quoting, activation, scratch/log-path, or unambiguous path corrections may be made locally and recorded without returning to implementation.

## Material candidate boundary

Product candidate:

`a9cb41ad9b1c6305de195f1a88b71ea098e582b7`

The current coordination branch may be used directly because commits after the candidate contain coordination/evidence plus `.gitignore`, not product/runtime/test/package code. Before executing, verify this remains true with a focused diff across product-defining paths, for example:

```bash
git diff --name-only a9cb41ad9b1c6305de195f1a88b71ea098e582b7..HEAD -- \
  mdstats tests benchmarks pyproject.toml docs release scripts
```

If that command reports a product-defining change that could affect these checks, stop and reassess the affected evidence. Changes only under `workplans/`, `qualification/`, or `.gitignore` are coordination and do not create a new product candidate.

## Material production inputs

```text
Production DB:
$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3

Campaign config:
$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml

Label domain:
label-domain-5aa1ee5d50cd0b23

Expected candidates: 36,408
Expected families: 165
```

The production DB and config are read-only inputs for this qualification. Q5-Q7 operate on qualification-local clones. Record their SHA-256 before and after Q5-Q7 because these are real external content boundaries; unexpected mutation is blocking.

## Acceptance-critical checks

### Q1 — focused MVSEL2/REPAIR2 correctness

Required result: PASS.

Previously executed against this unchanged candidate on the target workstation: **40 passed**.

Evidence reuse is allowed. Rerun only if the candidate/product paths changed or the existing evidence is unavailable/untrustworthy.

Relevant tests:

```text
tests/test_mlff_repair2.py
tests/test_mlff_mvstate2.py
tests/test_mlff_mvsel2_forward.py
tests/test_mlff_mvmigrate2.py
tests/test_mlff_mvsel2_hardening.py
```

### Q2 — adjacent MVSEL1 compatibility

Required result: PASS.

Previously executed against this unchanged candidate on the target workstation: **10 passed**.

Evidence reuse is allowed under the same rule.

Relevant test:

```text
tests/test_mlff_target_data2c_repair1.py
```

### Q3 — broad repository health/regression attribution

The repository is not currently maintained as a globally green non-slow suite: the unchanged candidate previously completed with 3,187 passed, 307 failed, 16 skipped, and 20 deselected. Therefore an exit code of 1 is not, by itself, an MVSEL2 candidate failure.

Use the existing candidate JUnit/log evidence first (`qualification/evidence/q3_candidate.xml` and the revision-2 report). Group failures by test file/error class and determine whether any failure is plausibly caused by the MVSEL2 hardening change surface or its affected consumers.

Blocking condition: a candidate-attributable or plausibly candidate-attributable regression.

Nonblocking condition: failures clearly outside the MVSEL2 change surface that represent pre-existing/stale repository-health contracts (for example historical version/spec/bootstrap/compatibility assertions already identified in the prior report).

If existing evidence is insufficient for attribution, rerun only the candidate broad suite; do **not** construct another historical/counterfactual baseline solely to manufacture a green oracle:

```bash
conda run -n mace pytest -q -m 'not slow' --junitxml=qualification/s9/q3_candidate.xml
```

Record the observed failures and attribution. Do not call the broad suite globally PASS if it is red; record it as a health finding while deciding the MVSEL2 acceptance requirement by attribution.

### Q4 — installed distribution behavior

Required result: PASS.

Previously rerun successfully against this unchanged candidate: wheel built, installed to an isolated target, imported from outside the source checkout, reported `0.20.242a0`, and excluded `workplans/` from the wheel.

Evidence reuse is allowed. Rerun only if product/package/build paths changed or the existing evidence is unavailable.

### Q5 — real production corrupt-newest MVSTATE2 recovery

Required result:

- production-sized native forward-only MVIDX path is used;
- at least two MVSTATE2 checkpoints exist;
- newest checkpoint is corrupted only in the qualification-local clone;
- runtime actually selects the immediately preceding valid checkpoint as its resume pointer;
- resumed final selection digest exactly equals uninterrupted selection digest;
- production DB/config remain unchanged.

Use the strengthened material recovery harness:

```bash
set -euo pipefail
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
mkdir -p qualification/s9
sha256sum "$PROD_DB" "$CONFIG" > qualification/s9/production_inputs_before.sha256
rm -rf qualification/s9/q5
conda run -n mace python workplans/active/DOC-MVSEL2_HARDEN1_V3_Q5_RECOVERY_CHECK.py \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN" \
  --clone-root qualification/s9/q5 \
  --output qualification/s9/q5_recovery.json \
  > qualification/s9/q5_recovery.log 2>&1
sha256sum "$PROD_DB" "$CONFIG" > qualification/s9/production_inputs_after_q5.sha256
cmp qualification/s9/production_inputs_before.sha256 qualification/s9/production_inputs_after_q5.sha256
```

A different but equivalent scratch/log path or environment-activation command is permitted.

### Q6 — production-sized REPAIR2 ladder/resource behavior

Prerequisite: Q5 PASS and its ephemeral clone exists.

Required result:

- fixed-eight ladder through 16,384 is measured on 36,408 candidates / 165 families;
- all required rungs execute;
- rejected proposals use zero full forward-state copies;
- inverse mutation is false;
- native forward-only reader remains the execution path;
- production inputs remain unchanged.

Suggested command:

```bash
Q5_DB="$PWD/qualification/s9/q5/.mdstats/campaign.sqlite3"
conda run -n mace python benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py \
  "$Q5_DB" \
  --domain 'label-domain-5aa1ee5d50cd0b23' \
  --workplan-id DOC-MVSEL2-HARDEN1-V3 \
  --workplan-revision 2 \
  --workplan-sha256 42a9075ecd96eb16a36ab9fc1d09c8bd4522022ef1749f6554dfa153c0faa52c \
  --expected-candidate-count 36408 \
  --expected-family-count 165 \
  --output qualification/s9/q6_repair2_production.json \
  > qualification/s9/q6_repair2_production.log 2>&1
```

The workplan metadata flags above are required by the existing benchmark parser but are **not independent acceptance criteria**. A metadata mismatch in the JSON does not invalidate the measured REPAIR2 behavior.

### Q7 — same-host v1 vs v2 production performance

Required result: the end-to-end v2 selector+repair chain is at least **10x faster** than the v1 chain on the same production input/configuration and same host/resource policy.

Use fresh independent qualification-local clones and the actual config path:

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
rm -rf qualification/s9/q7
conda run -n mace python workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py q7 \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN" \
  --clone-root qualification/s9/q7 \
  --output qualification/s9/q7_performance.json \
  > qualification/s9/q7_performance.log 2>&1
sha256sum "$PROD_DB" "$CONFIG" > qualification/s9/production_inputs_after_q7.sha256
cmp qualification/s9/production_inputs_before.sha256 qualification/s9/production_inputs_after_q7.sha256
```

The driver returns nonzero if the 10x floor is missed. If the comparison cannot be made fairly because of a real environment/resource inconsistency, report that material issue instead of constructing a synthetic historical baseline.

## Future qualification obligation

GPU qualification is **not required for the present workstation acceptance**. It remains a future final-release obligation. Do not run GPU qualification in this S9 session.

## Allowed local corrections

Qualification may correct and continue for:

- cwd/import-origin setup;
- conda activation syntax;
- shell quoting;
- scratch/log/evidence paths;
- the unambiguous production config path above;
- equivalent commands that preserve the material check;
- non-material report metadata.

Do not return to implementation for these alone.

## True blocking/failure routing

Return `RETURN_TO_IMPLEMENTATION` for a real product/test/harness defect that changes the substantive result, including Q5 recovery failure, Q6 state-copy/inverse/ladder failure, candidate-attributable regression, package failure, or Q7 performance below the frozen 10x threshold.

Return `DESIGN_REVISION_REQUIRED` only if the actual product target/acceptance semantics must change.

Return `BLOCKED` only when a required workstation/production input or execution capability is genuinely unavailable.

If Q1-Q7 material requirements are satisfied (with Q1/Q2/Q4 validly reused where applicable), produce a compact qualification evidence summary and route to `software-verification`. Do not manufacture a new handoff revision merely to fix reporting details.
