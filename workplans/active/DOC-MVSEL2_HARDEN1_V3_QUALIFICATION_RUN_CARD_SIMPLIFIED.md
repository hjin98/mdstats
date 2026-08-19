---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-REV8-LIGHTWEIGHT
protocol_version: 3.1.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 8
status: PREPARED_FOR_TARGET_QUALIFICATION
---

# MVSEL2 hardening — REV8 autonomous workstation qualification

## Governing design and implementation

Design authority:

`workplans/active/DOC-MVSEL2_HARDEN1_V3_REV8_FINAL_REVIEWED_QUALIFICATION.md`

Implementation execution record:

`workplans/active/DOC-MVSEL2_HARDEN1_V3_REV8_IMPLEMENTATION.md`

REV5-REV7 execution procedures are superseded. The current qualifier is a short current-candidate measurement bound to the complete production graph; it is not a production replay.

Packaged/runtime code changed during REV8, so earlier candidate/package evidence is not silently inherited. The implementation code anchor after the autonomous qualifier was completed is `c7f67572a37c81b8eba05e6cbf601f933d46fbe1`; subsequent workplan/run-card commits are coordination-only unless a later product/source diff says otherwise. The qualifier records the actual Git HEAD and requires a clean tracked/staged working tree before executing candidate checks.

## One command

From the up-to-date `feat/mvsel2-forward-lazy` checkout:

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

No ChatGPT/Codex process must remain connected. The command automatically runs the affected tests/package check first, then the bounded production-data checks, then publishes compact evidence and cleans owned scratch.

The `mace` environment must already contain the repository's normal test/build dependencies (`pytest`, `build`, `pip`, NumPy, and mdstats runtime dependencies). Missing tooling is `BLOCKED` environment evidence, not a product FAIL.

## Resource behavior

The driver discovers effective CPU affinity, host/cgroup available memory, free disk, and stricter user caps. It derives:

1. effective capacity;
2. hard containment;
3. a smaller normal operating envelope.

Defaults/guards:

- hard total wall boundary: 15 minutes;
- explicit `--total-timeout-seconds` may only tighten that boundary;
- hard aggregate scratch: no more than 1 GiB and further reduced by free-space constraints;
- RSS hard containment is derived conservatively from currently effective memory; explicit `--max-rss-gib` may only tighten it;
- normal operating RSS/time/scratch stay materially below the hard boundaries;
- aggregate owned-process RSS, scratch blocks, wall time, and host/cgroup memory pressure are supervised externally;
- `RLIMIT_AS` is not used because the large file-backed MVIDX virtual mapping is not resident-memory demand.

The normal workstation target remains approximately 5-8 minutes. The watchdog is emergency containment, not the workload-sizing mechanism.

## Automatic stage G5 — candidate regression/package preflight

Before production MVIDX is mapped, the supervised worker automatically:

1. requires clean tracked/staged candidate state;
2. runs the affected focused v2 regressions, REV8 harness tests, and adjacent REPAIR1 regression;
3. materializes a clean tracked candidate with `git archive` into owned scratch;
4. builds one wheel with `python -m build --wheel --no-isolation`;
5. isolated-installs that wheel under scratch;
6. imports from an unrelated scratch cwd and requires version `0.20.242a0` plus import origin beneath the isolated install;
7. requires the wheel to exclude `workplans/`.

The focused set is:

```text
tests/test_mlff_repair2.py
tests/test_mlff_mvstate2.py
tests/test_mlff_mvsel2_forward.py
tests/test_mlff_mvmigrate2.py
tests/test_mlff_mvsel2_hardening.py
tests/test_mlff_mvsel2_oracle.py
tests/test_mlff_mvsel2_rev8_qualification.py
tests/test_mlff_target_data2c_repair1.py
```

Pytest exit 1 or a demonstrated build/install/import/package-content defect is product FAIL. Missing test/build capability, collection/infrastructure failure, or ambiguous working-tree state is BLOCKED.

This replaces a separate manual G5 sequence; the same one command performs it under the hard supervisor.

## LQ0 — ownership, quiescence, and admission

The parent:

- creates separate compact evidence and disposable scratch roots;
- scavenges only abandoned scratch with a valid matching `OWNER.json` and dead recorded owner process;
- captures production SQLite/config identity twice across a short quiescence interval before launch;
- includes the SQLite main DB plus any material `-wal`/rollback-journal content in identity, while deliberately excluding transient `-shm` reader marks;
- refuses to launch production work if authority is changing;
- hashes/checks production identity again after execution.

Production input change or non-quiescence is `BLOCKED`, not product FAIL.

## LQ1 — full production binding, tiny execution

The worker opens the production SQLite database with `mode=ro`, explicitly deserializes production authority, and opens the native forward-only MVIDX in place.

It authenticates:

- 36,408 candidates;
- 165 families;
- complete current forward-edge count and MVIDX digest;
- production MVSEL2 authority;
- materializable ladder through 16,384;
- native forward-only execution.

Only candidates 0, midpoint, and final candidate are sampled for forward incidence. No complete candidate sweep and no fresh full-domain feasibility/state build is performed.

No writable `CampaignStore` is constructed on the production database.

## LQ2 — exact 128 -> 256 recovery

The current production 128, 256, and 16,384 MVSTATE2 checkpoints are required.

For recovery:

1. copy only the 128 and 256 checkpoint bundles into run-owned scratch;
2. restore/authenticate the production 256 authority;
3. corrupt only the scratch 256 pointer record;
4. require runtime fallback to the scratch 128 checkpoint;
5. replay only canonical selected candidates at ranks 128..255 with the exact production score/select mutation primitives;
6. compare reconstructed state exactly against authenticated production 256 state.

Exact comparison covers selected order, availability, every family multiplicity/coverage mass, obligation counts, unsatisfied-required count, correlation-unit counts, and representative utility.

A recovery/state mismatch is product FAIL. Missing/corrupt external authority that prevents a trustworthy comparison is BLOCKED.

## LQ3 — shared exact REPAIR2 micro-benchmark

Production and qualification now share `mvsel2_repair_checkpoint_runtime.py`; the qualification harness does not duplicate `_proposal`, `_better`, swap mutation, coverage, or obligation science.

Mandatory rungs: 128 and 256.

Adaptive extension:

- add 512 only if required proposal/timing evidence is still absent;
- add at most 1024 if still needed and admitted;
- stop once proposal-cost/material evidence is sufficient;
- never enlarge merely to force an accepted swap.

If an accepted repair divergence occurs, subsequent measured rungs carry the repaired state/order exactly as production does rather than restoring a later pure-selector checkpoint.

PASS assertions on measured rungs include default policy, zero rejected-proposal full-state copies, no inverse mutation, and no coverage/hard-obligation regression. Accepted-swap semantic branches remain covered by the focused regression suite.

The actual production 16,384 checkpoint is restored as the mandatory large-rung compatibility sentinel. No 16,384 REPAIR2 computation is launched solely for qualification.

If no bounded measured rung exercises proposal cost through the allowed extension, the performance component is BLOCKED instead of guessed.

## LQ4 — fresh current-candidate selector + combined >=10x bound

The old approximately 69x MVSEL2 projection is advisory historical evidence only.

### Legacy baseline

Only the legacy MVSEL1 baseline is reused. Reuse requires:

- exact current production graph identity;
- original `local-user-ProBuild` host context, unless the operator explicitly supplies `--accept-same-host-equivalent` after establishing equivalence;
- no Git diff from historical source head `f23426d426af21a54914f4e62181ce09e864330b` across the frozen legacy comparator surface.

Failure to establish that baseline is BLOCKED. The driver never launches a full legacy MVSEL1 replay automatically.

### Current selector measurement

The current candidate is measured directly:

1. restore real MVSTATE2 rank 128;
2. run exact current Phase A from 128 until Phase A completes, requiring every chosen candidate to match authenticated production order;
3. conservatively bound unmeasured ranks 0..127 with the maximum measured Phase-A rank cost;
4. build one exact current Phase-B lazy frontier;
5. run exactly 32 current Phase-B ranks and require production-order identity;
6. conservatively project the remaining ranks to 16,384 with the maximum measured Phase-B rank cost.

REV8 changes the exact frontier *execution mechanics* to family-streaming: each candidate's FP64 representative gain is still accumulated in canonical family order, but a family's mmap pages are released immediately after that family is scanned. Focused parity requires bit-identical exact scores/generations/heap authority versus the legacy rebase. Campaign selection, checkpoint resume, and qualification all use this shared streaming frontier.

Admission for the rebase uses current resident memory plus a conservative multiple of the largest single mapped family, with additional headroom. It no longer assumes the misleading post-release RSS and does not plan to touch all 35+ GiB of forward pages resident at once.

Selector bound:

```text
setup_upper = max(
    2 * current_reference_plus_forward_restore_seconds,
    4 * historical_cold_preflight_total_seconds
)
phase_a_prefix_upper = 128 * max_current_phase_a_rank_seconds
selector_upper = 1.25 * (
    setup_upper
    + phase_a_prefix_upper
    + current_phase_a_128_to_completion_seconds
    + current_exact_rebase_seconds
    + (16384 - phase_a_end) * max_current_phase_b_rank_seconds
)
```

REPAIR2 bound:

```text
work_i = shell_size_i + proposals_i * candidate_count
unit_seconds = max(rung_wall_seconds_i / max(1, work_i))
P_cap = removal_shortlist_limit * (max_swaps_per_shell + max_passes_per_shell)
work_upper_r = shell_size_r + P_cap * candidate_count
repair_upper = 4 * unit_seconds * sum(work_upper_r over materializable rungs <=16384)
combined_speedup_lower = historical_mvsel1_baseline_seconds / (selector_upper + repair_upper)
```

PASS requires `combined_speedup_lower >= 10.0`.

A successfully measured bound below 10x is product/performance FAIL. Missing safely establishable baseline/proposal/rebase evidence is BLOCKED. The threshold is never lowered and there is no unbounded fallback replay.

## LQ5 — all-terminal cleanup and compact evidence

The layout is:

```text
qualification/bounded-mvsel2/
  evidence/<run-id>/...
  scratch/<run-id>/OWNER.json
  scratch/<run-id>/...
  state.json
  summary.json
```

The supervisor retains compact worker/stage evidence and bounded log tails, keeps only a small number of previous evidence capsules, and removes the entire owned scratch run on PASS, FAIL, BLOCKED, ordinary exceptions, SIGINT, or SIGTERM.

SIGKILL/power-loss cleanup is handled on the next startup only when the ownership manifest proves the directory belongs to this qualifier and its recorded owner process is no longer the same live process.

## Result semantics

- demonstrated semantic/product/package/performance violation -> `FAIL`;
- missing/unstable external input, missing environment capability, unsafe minimum workload, or ambiguous harness/input exception -> `BLOCKED`;
- hard containment activation -> `BLOCKED` as `QUALIFICATION_RESOURCE_MODEL_FAILURE`, never automatic product FAIL and never an automatic limit increase;
- optional telemetry/cosmetic metadata defects -> advisory when safety and interpretation remain intact.

## Evidence to return

After the command completes, the only files normally needed for review are:

```text
qualification/bounded-mvsel2/summary.json
qualification/bounded-mvsel2/state.json
qualification/bounded-mvsel2/evidence/<latest-run>/summary.json
qualification/bounded-mvsel2/evidence/<latest-run>/worker.json
```

plus the bounded G5/worker log tails if a stage failed or blocked.

The qualifier's own large temporary candidate archive, wheel/install tree, scratch SQLite database, and copied MVSTATE2 bundles are not final evidence and are removed automatically.
