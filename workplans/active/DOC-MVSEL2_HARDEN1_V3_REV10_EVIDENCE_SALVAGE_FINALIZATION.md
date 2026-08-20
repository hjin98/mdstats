---
kind: qualification-plan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 10
protocol_version: 3.1.0
status: READY
product_candidate_anchor: c7f67572a37c81b8eba05e6cbf601f933d46fbe1
source_production_evidence: 20260819-210013-30915
---

# REV10 — evidence-salvage finalization

## Decision

Stop rerunning the full production selector merely to force a naturally occurring REPAIR2 proposal.

The REV9 production run `20260819-210013-30915` already established the expensive material evidence:

- G5 PASS on the frozen product surface;
- LQ1 PASS on the authenticated 36,408-candidate / 165-family / 9,505,021,522-edge production graph;
- LQ2 PASS for exact qualification-owned MVSTATE2 fallback and 128→256 state reconstruction;
- exact current Phase-A→Phase-B execution occurred;
- current Phase-B timing was observed through the rank-512 prefix;
- production REPAIR2 measurements at 128, 256, and 512 all completed with zero proposals, zero swaps, no full-state copies, and no inverse mutation;
- production DB/config identity remained unchanged;
- resource containment remained healthy.

A zero-proposal production rung is a legitimate runtime outcome, not a qualification failure. The prior LQ3 requirement that proposal cost must arise naturally on a bounded production rung was therefore the wrong coupling.

## REV10 qualification model

### A. Reuse the expensive production evidence

No MVSEL2 rerun is required.

The finalizer requires the source evidence capsule to contain:

- G5 PASS;
- LQ1 PASS;
- LQ2 PASS;
- LQ3 measured rungs with `proposals == 0` and clean no-copy/no-inverse invariants;
- LQ4 blocked only because proposal cost was not exercised;
- unchanged G5 material surface between the source evidence candidate and current HEAD.

### B. Conservative selector upper bound from persisted evidence

The source worker's complete elapsed time is used as an upper bound on all setup, Phase A, exact rebase, recovery, and measured early-rung work before terminal block.

The finalizer parses the largest persisted `observed-max-rank` from REV9 admission telemetry and then deliberately charges every one of the 16,384 target ranks at that worst observed current Phase-B rank cost.

```
selector_upper = 1.25 * (
    source_worker_elapsed_seconds
    + 16384 * worst_observed_current_phase_b_rank_seconds
)
```

This overcounts measured work and therefore does not depend on unpersisted fine-grained Phase-A or rebase timing.

### C. Separate production-graph proposal-kernel microbenchmark

Proposal cost is measured independently from naturally occurring repair eligibility.

The finalizer opens the same production reference and native-forward MVIDX read-only and invokes the real current REPAIR2 `_proposal` kernel on timing-only synthetic states built over the real production forward domain.

The synthetic timing state:

- uses the real 36,408-candidate forward authority;
- uses real reference witness weights, candidate incidence rows, obligation definitions, correlation-unit codes, and family count;
- marks one sampled removal candidate as selected;
- sets its touched witness multiplicities to two so the zero-unique-removal invariant is valid for the timing path;
- leaves all other candidates available;
- never writes a production record;
- is performance evidence only, not scientific selection/repair authority.

Three production candidates (the existing LQ1 0/mid/final samples) are measured and the slowest `_proposal` wall time is retained.

### D. Conservative REPAIR2 upper bound

Production zero-proposal rungs supply the real shell-scan coefficient:

```
shell_unit = max(wall_seconds / shell_size)
```

The frozen proposal cap remains:

```
P_cap_per_rung = 64 * (32 + 2) = 2176
```

Across the eight materializable rungs:

```
proposal_cap_total = 2176 * 8
```

The final repair bound is:

```
repair_upper = 4 * (
    shell_unit * 16384
    + max_measured_proposal_seconds * proposal_cap_total
)
```

The factor 4 preserves the existing conservative REPAIR2 safety multiplier.

### E. Final acceptance

Reuse the compatible historical MVSEL1 full-order baseline already bound in the source evidence.

```
combined_speedup_lower = B_hist / (selector_upper + repair_upper)
```

- PASS: `combined_speedup_lower >= 10.0`
- FAIL: measured conservative lower bound `< 10.0`
- BLOCKED: source evidence stale/incompatible, production MVIDX identity changed, or proposal microbenchmark cannot be measured safely.

No full selector rerun is permitted merely to make a proposal appear.

## One short finalization command

```bash
EVIDENCE='qualification/bounded-mvsel2/evidence/20260819-210013-30915'
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
DOMAIN='label-domain-5aa1ee5d50cd0b23'

conda run -n mace python scripts/mvsel2_rev10_finalize_existing_evidence.py \
  --evidence "$EVIDENCE" \
  --production-db "$PROD_DB" \
  --domain "$DOMAIN"
```

Expected output artifact:

`qualification/bounded-mvsel2/evidence/20260819-210013-30915/rev10-finalization.json`

## Guardrails

- The product/runtime candidate remains `c7f67572a37c81b8eba05e6cbf601f933d46fbe1`.
- REV10 changes qualification methodology only.
- Production SQLite is opened `mode=ro`.
- The proposal timing state is never labeled scientific authority.
- No production MVSEL2 plan/MVSTATE2 checkpoint is fabricated.
- No 1024/2048/... production selector extension is required for timing evidence.
- No full replay is triggered automatically.
- The `>=10x` acceptance threshold is unchanged.
