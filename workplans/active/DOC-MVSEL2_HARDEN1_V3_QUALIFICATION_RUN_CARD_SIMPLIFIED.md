---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-REV4-MATERIALITY
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 4
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
status: PREPARED_FOR_QUALIFICATION
---

# MVSEL2 hardening — REV4 material qualification run card

## Objective

Finish the remaining substantive CPU/workstation qualification of the frozen MVSEL2/REPAIR2 candidate. Correct harmless execution details locally; stop only for a real product/material failure, ambiguous material input, or unavailable required workstation capability.

## Material candidate and inputs

Product candidate:

`a9cb41ad9b1c6305de195f1a88b71ea098e582b7`

Later coordination commits are allowed only when they do not alter product/runtime/test/package/spec/release behavior relevant to these checks. Verify this with a focused candidate-to-HEAD diff before execution. Changes confined to `workplans/`, `qualification/`, or `.gitignore` do not create a new product candidate.

Production inputs:

```text
Database:
$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3

Configuration:
$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml

Label domain:
label-domain-5aa1ee5d50cd0b23

Expected candidates: 36,408
Expected families: 165
```

The production DB/config are read-only. All mutable qualification state is a physical copy in `qualification/rev4/` (or an equivalent disjoint scratch path). No hard links to production are allowed.

If the config has moved, qualification may substitute exactly one unambiguous config for this same FP32 campaign and record the actual path. If multiple plausible configs exist, stop as `BLOCKED` rather than guessing.

## Reused evidence

### Q1 — focused MVSEL2/REPAIR2 correctness

**PASS, reused:** 40 focused tests passed on the unchanged product candidate. Rerun only if product/test behavior relevant to Q1 changed or the evidence is shown to be untrustworthy.

### Q2 — adjacent MVSEL1 compatibility

**PASS, reused:** 10 adjacent-v1 tests passed on the unchanged product candidate. Same reuse rule as Q1.

### Q4 — isolated installed artifact

**PASS, reused:** the candidate wheel built and installed into an isolated target, imported from outside the checkout, reported the expected package version, and did not ship `workplans/`. Rerun only after a material package/build/product change.

Administrative workplan/report/hash changes do not invalidate Q1/Q2/Q4.

## Q3 — broad regression attribution

Use the existing candidate JUnit/report evidence first. The repository-wide non-slow suite is not currently globally green, so the aggregate 307 failures do not automatically fail this candidate.

Acceptance rule:

- a failure with a plausible causal path to MVSEL2/REPAIR2 hardening or an affected consumer must be resolved by existing or focused follow-up evidence;
- clearly unrelated stale/historical version/spec/bootstrap/documentation failures are repository-health findings, not candidate failures;
- lack of a historical matching failure is not by itself evidence that this candidate caused the failure.

If existing evidence is insufficient for a plausible candidate-related class, run the smallest focused follow-up first. Rerun the full candidate non-slow suite only if focused evidence cannot resolve attribution. Do not construct a historical/counterfactual baseline.

## Q5 — production corrupt-newest MVSTATE2 recovery

Required behavior:

1. make a physical copy of production `.mdstats` into disjoint scratch;
2. generate fresh uninterrupted v2 authority/checkpoints on the copy;
3. prevalidate the newest checkpoint and independently identify the highest older valid compatible checkpoint;
4. corrupt only the validated newest checkpoint in scratch;
5. require the runtime resume pointer to equal the prevalidated older checkpoint;
6. require the resumed final digest to equal uninterrupted execution exactly;
7. leave production DB/config unchanged.

Suggested execution:

```bash
set -euo pipefail
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
ROOT="$PWD/qualification/rev4"
mkdir -p "$ROOT"
sha256sum "$PROD_DB" "$CONFIG" > "$ROOT/production_inputs_before.sha256"
rm -rf "$ROOT/q5"
conda run -n mace python workplans/active/DOC-MVSEL2_HARDEN1_V3_Q5_RECOVERY_CHECK.py \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN" \
  --clone-root "$ROOT/q5" \
  --output "$ROOT/q5_recovery.json" \
  > "$ROOT/q5_recovery.log" 2>&1
sha256sum "$PROD_DB" "$CONFIG" > "$ROOT/production_inputs_after_q5.sha256"
cmp "$ROOT/production_inputs_before.sha256" "$ROOT/production_inputs_after_q5.sha256"
```

If an external process changed a production input during the attempt, invalidate that attempt and restart from a stable snapshot. Do not classify that as a candidate failure.

## Q6 — independent clean production REPAIR2 scale/resource behavior

Q6 **must not consume the intentionally corrupted Q5 clone**. Prepare its own fresh physical snapshot and clean v2 authority/checkpoints:

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
ROOT="$PWD/qualification/rev4"
rm -rf "$ROOT/q6"
conda run -n mace python workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py q6-prepare \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN" \
  --clone-root "$ROOT/q6" \
  --output "$ROOT/q6_prepare.json" \
  > "$ROOT/q6_prepare.log" 2>&1
Q6_DB="$ROOT/q6/.mdstats/campaign.sqlite3"
conda run -n mace python benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py \
  "$Q6_DB" \
  --domain "$DOMAIN" \
  --workplan-id DOC-MVSEL2-HARDEN1-V3 \
  --workplan-revision 4 \
  --workplan-sha256 advisory-not-an-acceptance-gate \
  --expected-candidate-count 36408 \
  --expected-family-count 165 \
  --output "$ROOT/q6_repair2_production.json" \
  > "$ROOT/q6_repair2_production.log" 2>&1
```

The legacy workplan metadata arguments are parser inputs only and are not software acceptance criteria.

Q6 PASS requires the 36,408-candidate/165-family fixed-eight ladder through 16,384, all required rung measurements, zero rejected-proposal full forward state copies, no inverse mutation, and the native forward-only execution path.

## Q7 — independent same-host v1/v2 performance

Use fresh copy-only v1/v2 snapshots. The driver implements the frozen noise policy:

- if the first valid fresh pair is >=10x, PASS on that pair;
- if the first valid pair is <10x, retain it and run two more fresh pairs under the same material environment; the median of all three valid pairs decides;
- do not discard a valid slow measurement merely to improve the result.

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
ROOT="$PWD/qualification/rev4"
rm -rf "$ROOT/q7"
conda run -n mace python workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py q7 \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN" \
  --clone-root "$ROOT/q7" \
  --output "$ROOT/q7_performance.json" \
  > "$ROOT/q7_performance.log" 2>&1
sha256sum "$PROD_DB" "$CONFIG" > "$ROOT/production_inputs_after_q7.sha256"
cmp "$ROOT/production_inputs_before.sha256" "$ROOT/production_inputs_after_q7.sha256"
```

If the host is materially loaded or resource settings changed enough to make a measurement unfair, correct that environment and repeat the affected attempt. Do not reinterpret a valid below-floor result as a harness error.

## Production-input immutability

SHA-256 checks protect a real external-content boundary here. A mismatch means only that the affected attempt cannot establish a stable-input result. Determine whether qualification itself mutated production (blocking defect) or an external process changed it (restart that attempt). It does not automatically imply a product failure.

## Operational corrections allowed in place

Qualification may correct and continue for cwd/import-origin setup, conda activation syntax, shell quoting, scratch/log/evidence paths, one unambiguous moved config path for the same campaign, equivalent commands preserving the same material check, and legacy/advisory report or workplan metadata. Do not create another workplan revision for those alone.

## True failure/blocking routing

- real product or acceptance-critical harness defect -> `RETURN_TO_IMPLEMENTATION`;
- frozen product/threshold contradiction -> `DESIGN_REVISION_REQUIRED`;
- genuinely unavailable/ambiguous required workstation input or capability -> `BLOCKED`;
- harmless operational/report defect -> correct locally and continue.

GPU qualification is outside this CPU/workstation run and remains a final-release obligation.

When Q3/Q5/Q6/Q7 are resolved, write a compact evidence summary and invoke `software-verification`. Do not expand the report into another provenance project.
