---
kind: implementation-execution
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 8
protocol_version: 3.1.0
status: PREPARED_FOR_TARGET_QUALIFICATION
governing_design: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV8_FINAL_REVIEWED_QUALIFICATION.md
code_candidate_anchor: c7f67572a37c81b8eba05e6cbf601f933d46fbe1
---

# REV8 lightweight autonomous qualification — implementation execution

## Outcome

REV8 implementation is source-complete and handed off for target-workstation qualification.

The frozen MVSEL2/MVSTATE2/REPAIR2 scientific semantics, MVIDX1 identity, checkpoint identity, and combined-chain `>=10x` floor were not changed. The implementation changes execution mechanics and qualification orchestration only.

The new packaged/runtime code candidate anchor is:

`c7f67572a37c81b8eba05e6cbf601f933d46fbe1`

A compare from this anchor to the branch immediately before this execution record was finalized showed only the REV8 qualification run-card change; no `mdstats/`, `scripts/`, tests, package/config, benchmark authority, or other product/execution source changed after the anchor. This execution-record commit is also coordination-only.

Because packaged `mdstats/` runtime bytes changed, earlier package/focused evidence from candidate `a9cb41ad...` is not promoted to the new candidate. The one-command qualifier reruns the materially affected tests and wheel/install/import automatically before production-data work.

## Implemented design

### R8-G0 — frozen implementation interpretation — COMPLETE

- REV8 final reviewed design remains authority.
- Legacy baseline compatibility surface is explicit and fail-closed.
- Runtime/package changes create a new candidate rather than inheriting stale package evidence.
- Full production identity remains separate external-input authority.

### R8-G1 — autonomous resource supervisor — IMPLEMENTED / TARGET EXECUTION PENDING

Implemented in:

- `scripts/mvsel2_qualification_support.py`
- `scripts/mvsel2_bounded_qualification.py`

Behavior:

- discovers CPU affinity, host/cgroup available memory, disk headroom, and stricter user caps;
- distinguishes effective capacity, hard containment, and a smaller operating envelope;
- fixed normal hard wall default is 15 minutes; explicit wall/RSS/scratch flags only tighten limits;
- hard scratch maximum is <=1 GiB and further constrained by free disk;
- monitors aggregate owned-process-group RSS, physical scratch blocks, wall time, and host/cgroup memory pressure;
- does not use `RLIMIT_AS`;
- writes run-owned `OWNER.json` and safely scavenges only abandoned scratch with proven ownership;
- cleans run-owned scratch after PASS/FAIL/BLOCKED, exception, SIGINT, or SIGTERM;
- bounds retained logs/evidence and keeps only a small number of prior evidence capsules;
- captures SQLite main DB plus material WAL/rollback-journal content and config identity;
- requires two matching production identities across a short pre-launch quiescence interval;
- rechecks production identity after execution;
- routes hard containment to `BLOCKED/QUALIFICATION_RESOURCE_MODEL_FAILURE`, never automatic product FAIL or limit increase;
- routes ambiguous harness/input exceptions to BLOCKED while preserving explicit measured product failures.

### R8-G2 — production binding and exact recovery micro-integration — IMPLEMENTED / TARGET EXECUTION PENDING

The worker:

- uses SQLite `mode=ro` plus explicit production-record deserialization;
- never creates writable `CampaignStore` on the production DB;
- maps the native forward-only MVIDX once for LQ1-LQ4;
- authenticates the full production graph/selection ladder but samples only candidates 0/mid/final for LQ1 incidence;
- requires production 128, 256, and 16,384 MVSTATE2 checkpoints;
- copies only 128/256 checkpoint bundles to owned recovery scratch;
- corrupts only the scratch 256 record;
- requires runtime fallback to 128;
- replays only canonical ranks 128..255 through exact v2 score/select mutations;
- compares selected order, availability, every family multiplicity/coverage mass, obligation counts, unsatisfied-required count, correlation-unit counts, and representative utility exactly against the authenticated 256 state;
- restores 16,384 read-only as the large-rung compatibility sentinel.

No full selector search or fresh full-domain validation is used for LQ2.

### R8-G3 — shared checkpoint-started REPAIR2 + bounded exact rebase — IMPLEMENTED / TARGET EXECUTION PENDING

New packaged runtime:

- `mdstats/training_data/mvsel2_repair_checkpoint_runtime.py`
- `mdstats/training_data/mvsel2_streaming_frontier.py`
- narrow routing changes in `mdstats/training_data/campaign_cli.py`

REPAIR2:

- production and qualification share one exact per-rung helper;
- the helper starts from authenticated MVSTATE2 state and does not perform a fresh full-domain feasibility scan;
- `_proposal`, `_better`, accepted mutation, coverage, obligation, and trace science remain the canonical existing implementation;
- production full-ladder orchestration uses the same helper;
- qualification measures 128 and 256, adds 512 and at most 1024 only when proposal/timing evidence remains insufficient;
- if a real accepted swap occurs, later measured rungs carry repaired state/order exactly as production does rather than restoring a later pure-selector checkpoint.

Phase-B exact rebase:

- representative gain is still accumulated for every available candidate in canonical family order with the same FP64 per-family sums;
- execution is transposed family-major so a family's mmap pages are dropped immediately after that family is scanned;
- campaign selector module and resumable selector alias are routed to the same streaming frontier;
- qualification imports the same patched frontier through the shared REV8 runtime seam.

This removes the previous tendency to retain pages from the complete 9.5-billion-edge forward relation until rebase completion without changing the scientific authority.

### R8-G4 — fresh current-candidate combined performance bound — IMPLEMENTED / TARGET EXECUTION PENDING

Legacy MVSEL1 baseline reuse requires:

- current graph identity match;
- `local-user-ProBuild` host context unless explicit same-host equivalence is accepted;
- no Git diff from historical source head `f23426d426af21a54914f4e62181ce09e864330b` across the frozen legacy comparator surface.

The historical ~69x MVSEL2 projection is advisory only.

Current candidate measurement:

- restore real rank 128;
- run exact Phase A from 128 to current Phase-A completion and require production-order identity at every measured rank;
- perform one current exact family-streaming Phase-B rebase after admission predicts memory/time headroom;
- run exactly 32 Phase-B ranks and require production-order identity;
- project remaining ranks conservatively with the maximum measured Phase-B rank cost;
- bound unmeasured Phase-A ranks 0..127 using the maximum current measured Phase-A rank cost;
- combine that selector bound with the conservative REPAIR2 proposal-cost projection;
- require `combined_speedup_lower >= 10.0`.

A measured result below 10x is product/performance FAIL. Missing safely establishable baseline/proposal/rebase evidence is BLOCKED. There is no automatic full MVSEL1/MVSEL2 replay.

### R8-G5 — affected tests and package qualification — IMPLEMENTED AS AUTOMATIC PRE-STAGE / NOT YET EXECUTED ON TARGET

Implemented in:

`scripts/mvsel2_qualification_preflight.py`

The same one-command qualifier, under the external resource supervisor, first:

1. requires clean tracked/staged state;
2. runs:
   - `tests/test_mlff_repair2.py`
   - `tests/test_mlff_mvstate2.py`
   - `tests/test_mlff_mvsel2_forward.py`
   - `tests/test_mlff_mvmigrate2.py`
   - `tests/test_mlff_mvsel2_hardening.py`
   - `tests/test_mlff_mvsel2_oracle.py`
   - `tests/test_mlff_mvsel2_rev8_qualification.py`
   - `tests/test_mlff_target_data2c_repair1.py`
3. materializes a clean tracked candidate with `git archive` into owned scratch;
4. builds one wheel with `python -m build --wheel --no-isolation`;
5. isolated-installs it under owned scratch;
6. imports it from an unrelated cwd and requires version `0.20.242a0` plus install-root origin;
7. requires `workplans/` to be absent from the wheel.

New focused REV8 tests cover:

- shared checkpoint-started REPAIR2 complete trace/master-order equivalence with canonical REPAIR2;
- no fresh full-domain validation when compatible checkpoints cover rungs;
- campaign routing to the shared repair helper;
- family-streaming exact frontier bit parity with the legacy rebase for exact scores, generations, heap, and generation;
- campaign and resume routing to the streaming frontier;
- repair projection fail-closed behavior when proposal cost is unmeasured;
- selector projection monotonicity;
- resource caps only tightening defaults;
- wall override unable to raise the 15-minute default;
- WAL-inclusive/SHM-excluding production identity;
- ownership-scavenger safety.

No target-runtime tests were fabricated in this chat environment. The repository has no default-branch GitHub Actions workflow available to execute this candidate remotely, and the local execution container cannot materialize the private repo checkout. Protocol 3.1 therefore leaves these checks as real target execution, now embedded in G6 rather than requiring manual commands.

### R8-G6 — one-command workstation qualification — PENDING_EXTERNAL

Authority:

`scripts/mvsel2_bounded_qualification.py`

Command:

```bash
conda run -n mace python scripts/mvsel2_bounded_qualification.py \
  --production-db $HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3 \
  --config $HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml \
  --domain label-domain-5aa1ee5d50cd0b23
```

This single command performs G5 then LQ1-LQ4, publishes compact summary/state/evidence, and cleans large owned test/build/recovery scratch automatically. No agent session is required after launch.

## Gate state

| Gate | Implementation | Target execution | Notes |
|---|---|---|---|
| R8-G0 | COMPLETE | NOT_REQUIRED | Frozen design/implementation choices. |
| R8-G1 | COMPLETE | PENDING_G6 | Resource/admission/watchdog/cleanup implemented. |
| R8-G2 | COMPLETE | PENDING_G6 | Production binding/recovery implemented. |
| R8-G3 | COMPLETE | PENDING_G6 | Shared repair + streaming rebase implemented. |
| R8-G4 | COMPLETE | PENDING_G6 | Current selector/combined performance bound implemented. |
| R8-G5 | COMPLETE | PENDING_G6 | Tests/package qualification automated inside one-command worker. |
| R8-G6 | PREPARED | PENDING_EXTERNAL | Run once on target workstation and return compact evidence. |

## Evidence expected from G6

Normally sufficient for qualification review:

```text
qualification/bounded-mvsel2/summary.json
qualification/bounded-mvsel2/state.json
qualification/bounded-mvsel2/evidence/<latest-run>/summary.json
qualification/bounded-mvsel2/evidence/<latest-run>/worker.json
```

Bounded G5/worker log tails are retained only as needed for a FAIL/BLOCKED diagnosis. Candidate archive, wheel/install tree, scratch SQLite DB, and copied checkpoints are disposable and removed on terminal cleanup.
