---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-REV5-BOUNDED
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 5
status: PREPARED_FOR_QUALIFICATION
---

# MVSEL2 hardening — bounded standalone workstation run card

## One-command execution

The old REV4 Q5/Q6/Q7 copy-based procedure is retired. Do not run the old qualification helpers that clone the complete `.mdstats` directory.

From the `feat/mvsel2-forward-lazy` checkout, run:

```bash
set -euo pipefail
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
ROOT='qualification/bounded-mvsel2'
mkdir -p "$ROOT"

conda run -n mace python scripts/mvsel2_bounded_qualification.py \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN" \
  --root "$ROOT" \
  --max-rss-gib 40 \
  --max-scratch-gib 4 \
  --q5-timeout-seconds 5400 \
  --q6-timeout-seconds 5400 \
  --total-timeout-seconds 10800 \
  2>&1 | tee "$ROOT/driver.log"
```

Codex/ChatGPT does not need to remain connected after this command starts.

The script defaults are 48 GiB RSS / 8 GiB scratch, but this run card intentionally uses the tighter 40 GiB / 4 GiB workstation envelope on a 64 GiB machine. Raising either ceiling should be deliberate and should follow inspection of the prior limit-hit evidence rather than being the first response.

## Resource guarantees

The driver is fail-closed:

- this run card caps the supervised worker at 40 GiB RSS;
- this run card caps the whole qualification root at 4 GiB physical scratch blocks;
- Q5 and Q6 each have a 90-minute wall limit;
- the entire run has a 3-hour wall limit;
- expensive work executes in supervised child processes;
- a sustained RAM/disk limit violation or stage timeout terminates the worker;
- the complete production `.mdstats` directory is never cloned;
- production database/config are hashed before and after material stages.

If a limit is hit, do not automatically raise it. Preserve `state.json` and the stage log and treat the limit hit as scaling evidence.

## What the driver does

### Q5 recovery

Q5 reads the production reference/MVIDX in place, copies only MVSTATE2 checkpoint bundles into bounded scratch, corrupts the newest checkpoint record in scratch, identifies the highest older compatible checkpoint independently, resumes from it, and compares the result against the already-authenticated production selector digest.

It does **not** copy the full campaign cache and does **not** run a redundant uninterrupted rank-zero production selector.

Transient Q5 checkpoint scratch is deleted after PASS.

### Q6 REPAIR2 production ladder

Q6 invokes the existing read-only production REPAIR2 benchmark directly against the production database and native forward-only MVIDX state. It measures the fixed-eight ladder through 16,384 under the watchdog.

### Q7 performance

Q7 does not launch a fresh multi-hour/day MVSEL1 replay. It authenticates the existing conservative production-density benchmark against the current MVIDX1 content digest, 36,408 candidates, and 165 families. The bound evidence must still report >=10x; otherwise Q7 fails and a new bounded comparator must be designed.

## Restart behavior

The driver writes:

```text
qualification/bounded-mvsel2/state.json
```

after every stage. Rerunning the same command reuses PASS stages only if the production DB/config identity is unchanged. This makes terminal loss, shell interruption, and agent/token limits non-destructive.

The final compact outputs are:

```text
qualification/bounded-mvsel2/q5_recovery.json
qualification/bounded-mvsel2/q6_repair2_production.json
qualification/bounded-mvsel2/q7_performance_reuse.json
qualification/bounded-mvsel2/summary.json
qualification/bounded-mvsel2/state.json
```

plus stage logs.

## Existing evidence

Q1 focused correctness, Q2 adjacent V1 compatibility, and Q4 wheel/install qualification remain reusable while their product/package surfaces remain unchanged. This workstation command is for the remaining production-scale qualification only.

## Stop conditions

Stop and return the evidence if any of these occurs:

- `RSS_LIMIT_EXCEEDED`;
- `SCRATCH_LIMIT_EXCEEDED`;
- `TIME_LIMIT_EXCEEDED`;
- Q5 fallback/digest mismatch;
- Q6 fixed-eight/no-copy/no-inverse assertion failure;
- Q7 graph-identity mismatch or conservative projected speedup <10x;
- production DB/config hash changes during qualification.

These are substantive signals. Do not work around them by making the workstation unbounded.
