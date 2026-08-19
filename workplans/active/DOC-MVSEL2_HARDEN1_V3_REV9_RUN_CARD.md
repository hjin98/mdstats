---
kind: qualification-run-card
handoff: DOC-MVSEL2-HARDEN1-V3-REV9-NO-PREEXISTING-STATE
protocol_version: 3.1.0
plan_revision: 9
status: READY
---

# REV9 MVSEL2 qualification run card

## Preconditions

- Branch: `feat/mvsel2-forward-lazy`.
- Pull latest REV9 qualification scripts.
- Production database/config remain unchanged and quiescent during the run.
- No production MVSEL2 plan or MVSTATE2 checkpoints are required.
- Do not copy or rebuild the production `.mdstats` tree.

## Command

```bash
set -euo pipefail
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'

conda run -n mace python scripts/mvsel2_bounded_qualification.py \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN"
```

## Expected execution shape

1. G5 is reused when its material surface is byte-identical; otherwise it reruns.
2. LQ1 opens the reference + native-forward MVIDX once, read-only.
3. Current exact Phase A runs from rank 0 to completion while qualifier-owned MVSTATE2 snapshots are persisted at 128 and 256.
4. LQ2 corrupts only the qualifier-owned 256 pointer, proves fallback to 128, replays ranks 128..255, and requires exact state equivalence.
5. LQ3 measures shared REPAIR2 at 128/256; it extends to 512 and at most 1024 only if proposal-cost evidence is still absent and the operating envelope admits the work.
6. LQ4 reuses the same live selector state for one exact streaming Phase-B rebase and >=32 current ranks, then projects selector+REPAIR2 through 16,384.
7. PASS requires conservative combined speedup >=10x and unchanged production identity.
8. All generated MVSTATE2, scratch SQLite, wheel/build artifacts, and other large temporary evidence are qualification-owned and cleaned automatically.

## Normal evidence to return

```text
qualification/bounded-mvsel2/summary.json
qualification/bounded-mvsel2/state.json
qualification/bounded-mvsel2/evidence/<latest-run>/worker.json
```

If terminal status is BLOCKED or FAIL, also return the displayed `reason=` line and, if needed, the compact `worker.log` tail.

## Interpretation guardrails

- `NO_MVSTATE2_ARTIFACTS` is no longer a blocker.
- Qualification-owned checkpoints are not labeled production checkpoints.
- Historical MVSEL2 ~69x remains advisory only.
- A hard RSS/wall/scratch hit during admitted minimum evidence is a qualification resource-model blocker, not automatically a product failure.
- A measured combined speedup below 10x is a product/performance failure.
