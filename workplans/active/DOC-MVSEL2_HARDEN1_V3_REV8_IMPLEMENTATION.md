---
kind: implementation-execution
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 8
protocol_version: 3.1.0
status: IN_PROGRESS
governing_design: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV8_FINAL_REVIEWED_QUALIFICATION.md
---

# REV8 lightweight autonomous qualification — implementation execution

## Frozen implementation interpretation

REV8 is the material design authority. This execution record does not change MVSEL2/MVSTATE2/REPAIR2 scientific semantics, MVIDX1 identity, checkpoint identity, or the combined-chain >=10x floor.

The implementation follows Protocol 3.1 software-implementation and software-qualification doctrine: normal qualification is deliberately smaller than its hard containment envelope; only material failures block; qualification is one-command/autonomous; production authority is read-only; owned transient state is cleaned on all terminal paths.

## Concrete implementation decisions frozen at R8-G0

1. **Shared REPAIR2 science.** Factor the exact per-rung repair execution into one private helper. Production full-ladder orchestration and qualification both call that helper. Qualification never copies `_proposal`, `_better`, swap mutation, coverage, or obligation logic.
2. **Checkpoint-started evidence.** Qualification restores authenticated MVSTATE2 state directly and invokes the shared helper without constructing a fresh full-domain forward state. This prevents the 9.5-billion-edge validation scan from becoming benchmark setup.
3. **Production DB boundary.** The qualifier uses SQLite `mode=ro` plus explicit deserialization for production records; writable `CampaignStore` is confined to qualification-owned scratch where recovery fault injection requires it.
4. **Legacy baseline compatibility surface.** Reuse `benchmarks/mlff_mvsel_production_density_2026-08-18.json` only on the same production graph/host context and only when Git reports no changes from historical source head `f23426d426af21a54914f4e62181ce09e864330b` across the legacy baseline assumption surface: `mdstats/training_data/target_multi_view_selector.py`, `target_multi_view_selection_state.py`, `target_multi_view_repair.py`, `target_coverage_sparse_index.py`, plus the legacy benchmark artifact itself. A mismatch is BLOCKED; no full MVSEL1 replay is launched.
5. **Current selector projection.** Restore real 128 state, execute current Phase A from rank 128 to completion, perform one exact lazy-frontier rebase, then exactly 32 Phase-B ranks. All chosen candidates must match authenticated production master order. Project the remainder conservatively per REV8.
6. **Resource containment.** One parent supervisor owns one serial mapped compute worker. Effective affinity/cgroup/host memory and disk are discovered automatically. User resource flags only tighten discovered limits. Aggregate owned-process RSS, physical scratch blocks, wall time, and available memory pressure are monitored. `RLIMIT_AS` is not used.
7. **Scratch ownership.** Every scratch run has `OWNER.json`; startup removes abandoned scratch only when the manifest proves qualifier ownership and the recorded parent is no longer alive. PASS/FAIL/BLOCKED/exception/SIGINT/SIGTERM cleanup preserves only compact evidence/log tail.
8. **Candidate boundary.** Because the shared rung helper touches packaged `mdstats/` runtime source, R8 implementation creates a new Git candidate. Affected v2 tests and wheel/build/install/import must be rerun before workstation qualification. Unaffected earlier evidence remains reusable by materiality.

## Gate execution

| Gate | Status | Acceptance |
|---|---|---|
| R8-G0 | COMPLETE | Frozen implementation choices above; legacy baseline surface resolved. |
| R8-G1 | IN_PROGRESS | Autonomous resource discovery/admission/watchdog/ownership/cleanup. |
| R8-G2 | PENDING | LQ1 production binding + exact 128->256 recovery without full validation. |
| R8-G3 | PENDING | Shared checkpoint-started REPAIR2 helper + adaptive 128/256/[512/1024] evidence. |
| R8-G4 | PENDING | Fresh current selector projection + conservative combined >=10x arithmetic. |
| R8-G5 | PENDING | Focused runtime/harness tests + wheel/install/import for new candidate. |
| R8-G6 | PENDING_EXTERNAL | One-command workstation production qualification and compact evidence handoff. |

## Execution note

The Protocol-3.1 implementation runner is intentionally CI-gated. It applies the packaged-runtime helper, autonomous qualifier, and focused harness tests in an isolated checkout, then commits them only after focused MVSEL2/MVSTATE2/REPAIR2 tests and isolated wheel import pass. A runner failure is implementation evidence, not permission to weaken REV8.

## Qualification command target

```bash
conda run -n mace python scripts/mvsel2_bounded_qualification.py \
  --production-db $HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3 \
  --config $HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml \
  --domain label-domain-5aa1ee5d50cd0b23
```

The script must discover/safely size itself. Hard limits are emergency containment, not benchmark targets.
