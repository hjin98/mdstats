# MLFF-DATA9B3 specification: unified campaign CLI and bounded production verification

Version: 0.20.58a0  
Status: implemented

## Purpose

DATA9B3 turns the DATA2-DATA9B2 record families into one deliberate user workflow.
It does not replace their scientific ownership. It supplies a small UNIX-style
interface that exposes the safe stage boundaries, resumes expensive work, explains
why a gate failed, and keeps implementation records out of the user's ordinary
working surface.

The canonical source-checkout entry point is:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml <command>
```

## User-visible contract

The ordinary campaign contains only:

```text
campaign.toml
<workspace>/campaign-manifest.json
<workspace>/data/                 # MACE data/configuration generations
<workspace>/runs/                 # logs and checkpoints
<workspace>/models/               # selected target-head committee
<workspace>/results/
  campaign-benchmark.json
  fine-tuning-result.json
  production-verification.json
```

Internal immutable records and resumable caches live below
`<workspace>/.mdstats/`. The orchestration state is one SQLite database rather
than a collection of top-level stage JSON files. DATA8 sidecars and content-
addressed generations remain because MACE reproducibility requires them, but they
are implementation artifacts inside `data/`, not separate user decisions.

## Command surface

The CLI shall expose only these workflow commands:

- `init`: write one documented TOML configuration;
- `doctor`: check inputs, checkpoint-bound replay qualification, package
  imports, precision wrappers, and CUDA availability;
- `prepare`: discover and approve one manifest, build DATA2-DATA5, run or resume
  the checkpoint-bound DATA6 sweep, materialize all requested DATA7/DATA8
  variants, and require a passed DATA9A production gate;
- `preflight`: verify every DATA8 job and run one required real one-epoch MACE
  smoke; `--check-only` verifies bytes but cannot authorize training;
- `train`: print, execute, or resume the frozen fold/final campaign;
- `evaluate`: evaluate every saved checkpoint, enforce the frozen metric policy,
  aggregate folds and seeds, compare naive/replay protocols, export the target-
  head committee, and emit `ProtocolFreezeRecord`;
- `verify`: run bounded NVE deployment checks on every frozen committee member;
- `status`: display all gates and the next safe command;
- `advance`: execute only the next incomplete gate;
- `guide`: print the short scientific workflow.

No command may silently skip a failed or waiting gate.

## Configuration contract

`campaign.toml` owns user choices rather than runtime observations. It includes:

- source, foundation checkpoint, replay train, and replay monitor locations;
- material profile and atom groups;
- correlation-aware partition policy;
- foundation inference device/dtype;
- selection sizes;
- naive/replay modes and seeds;
- objective, optimizer, execution, and checkpoint thresholds;
- bounded NVE verification structures and limits.

Paths are resolved relative to the configuration file. A non-positive execution
timeout means no campaign wall-clock timeout. The critical-FP64 wrappers are
mandatory even when the model body uses FP32.

## State and restart contract

`CampaignStore` shall:

1. use one SQLite database;
2. store canonical `to_dict()` payloads and content digests;
3. record stage state as `not_started`, `waiting`, `running`, `complete`, or
   `failed`;
4. atomically preserve the latest successful evidence before a process exits;
5. retain a compact event log;
6. never use the database location as scientific identity.

The expensive DATA6 sweep, DATA7/DATA8 materialization, and DATA9B training jobs
remain restartable through their native records. CLI state summarizes those
records rather than weakening their verification.

After a passed production DATA9A gate, `prepare` shall persist a compact restart
receipt that binds the current configuration bytes, input file-stat identities,
scientific record digests, DATA6 sweep checkpoint/plan identity, and the complete
DATA8 variant/plan/bundle/tree matrix. An unchanged plain `prepare` shall verify
that receipt and return as a no-op; it shall not construct a MACE calculator,
rerun inference, rebuild finalized DATA6, reconstruct foundation energies, or
rehash/rematerialize DATA7/DATA8 trees.

When only downstream protocol identity changes, restart shall be selective. Normalized frame arrays shall remain unloaded until DATA6 recomputation or changed DATA7/DATA8 materialization requires them. A
matching complete DATA6 sweep may be restored from its compact checkpoint with
sidecar authentication deferred to first scientific use. Finalized DATA6 may be
reused only when source, frame, DATA4, DATA5, policy, checkpoint, sweep-plan,
sweep-checkpoint, descriptor-manifest, and prediction-manifest identities all
match. Each unchanged DATA7/DATA8 variant shall retain its existing promoted
content-addressed tree; only changed, missing, or invalid variants may be rebuilt.
Explicit `prepare --rebuild-catalog` remains the user-controlled full upstream
reconstruction path.

Every completed CLI stage is bound to the SHA-256 of the current `campaign.toml`.
Editing the configuration makes earlier completions visibly stale until the
corresponding stage is rerun. Direct commands require the preceding stage to be
complete for the current configuration; `train` additionally requires a passed
real one-epoch preflight record.

## Manifest review gate

The first `prepare` call may discover files, but it shall stop after writing
`campaign-manifest.json`. The user must inspect reference groups, independent
replicas/structural realizations, initial/equilibrium regime declarations, and
strain metadata. `prepare --approve-manifest` binds the exact reviewed digest.
Any later edit invalidates approval and requires explicit reapproval. Full source
quality and production-regime assessment is mandatory. When VASP controls leave
the ensemble unresolved, production evidence may use only an explicit reviewed
`ensemble` assertion paired with a nonempty `ensemble_assertion_basis`; the CLI
shall never silently promote an unresolved ensemble or fabricate qualified
quality/production outcomes.

## Campaign matrix contract

Every enabled method declares its own explicit matrix:

```text
selection.sizes x training.<method>.seeds x
(training.<method>.cross_validation_folds + one final-development job)
```

`training.<method>.fold_partition_seed` freezes the platform-independent fold
assignment. `cross_validation_folds = 0` is final-only; `1` is invalid; `K >= 2`
materializes exactly K folds. Each configured variant receives independent DATA8
protocol identity. The CLI shall reject unknown methods, duplicate/negative seeds,
missing variants, a failed DATA9A gate, or raw `mace_run_train` execution. Legacy
`training.modes`/`training.seeds` files remain readable for restart compatibility.

## Seed and restart determinism amendment

The initial TOML shall expose every campaign pseudo-random seed: per-method MACE
seeds, per-method fold-partition seeds, replay selection, randomized feature
projection, and verification velocity initialization. MACE child interpreters
shall receive `PYTHONHASHSEED` equal to the run seed. A resumed MACE 0.3.16 loop
shall start at the epoch after the verified checkpoint epoch. Progress accounting
shall count one committed realization per epoch and only post-checkpoint rows from
the active attempt; epoch display is monotonic.

## Checkpoint and replay evaluation amendment

Candidate replay evaluation uses `pt_head`. A replay baseline may be:

- a matching multi-head initialization, using `pt_head`; or
- a single-head foundation checkpoint, with no explicit head selector.

`CheckpointEvaluationPolicy.replay_baseline_head_name` is therefore independent
of `replay_head_name`. Legacy records default to `pt_head`; new single-head
foundation workflows may serialize `null`. This prevents a production CLI from
requiring a fictitious `pt_head` on the foundation checkpoint.

Before DATA6-DATA8 materialization, the CLI shall also qualify the replay input
itself. For multi-head campaigns it requires:

- local train and monitor files with no geometry overlap;
- finite energy/force labels and valid optional stress;
- an explicit label mode (`external_pseudolabel` or `external_true_label`);
- for pseudo-labels, the SHA-256 identity of the exact configured foundation
  checkpoint on both files;
- coverage of the configured target elements;
- configured minimum train and monitor counts.

Undersized replay is a blocking production error by default. An explicit
`allow_small_corpus = true` override is available only for bounded exploratory
or software-smoke work and shall be recorded as a warning.

## Bounded production verification

`verify` is a deployment precheck, not a substitute for system-specific physical
validation. For each frozen committee member, verification structures, and
configured temperatures, it records:

- finiteness of energy and force;
- linear NVE total-energy drift in eV/atom/ps;
- minimum periodic pair distance;
- maximum atomic force;
- exact model, structure, timestep, temperature, and step count.

Default hard drift is 0.026 eV/atom/ps. A production candidate should be
comfortably below that limit. Atomic collapse, non-finite values, excessive
forces, or hard drift rejection fail the stage and produce corrective guidance.

RDF, coordination, site occupancy, VDOS, and diffusion remain owned by the
analysis modules and are still required before scientific deployment.
The consolidated verification record shall therefore identify its level as
`bounded_predeployment` and its scientific-acceptance status as
`required_separately`.

## Output and guidance contract

The CLI shall make success and failure legible without reading internal records.
It must report:

- source/frame counts and leakage status;
- sweep and materialization progress;
- production gate blockers;
- exact run IDs and commands in dry-run mode;
- selected epoch and target force metric per run;
- selected protocol mode and committee paths;
- bounded verification drift and minimum distance;
- actionable corrective guidance.

The consolidated result files are reporting products; immutable native records
remain authoritative.

## Failure behavior

The CLI shall fail closed for:

- unapproved or changed manifests;
- missing foundation/replay inputs;
- replay train/monitor overlap or malformed labels;
- missing replay-label provenance, checkpoint mismatch, absent target elements,
  or an undersized production replay corpus;
- unavailable critical-precision wrappers;
- requested CUDA with unavailable CUDA;
- failed DATA5 leakage audit;
- incomplete DATA6/DATA8 evidence;
- non-passed production qualification;
- incomplete campaign matrix;
- changed checkpoint or monitor bytes;
- no admissible checkpoint;
- incomplete seed coverage for the committee;
- bounded deployment instability.

Keyboard interruption returns code 130 and explicitly states that verified
records remain resumable.

## Acceptance tests

DATA9B3 is accepted when focused tests establish:

- command/help surface and configuration generation;
- one-database state persistence;
- digest-bound manifest approval;
- source-checkout precision wrapper shims;
- deterministic variant expansion;
- replay baseline-head compatibility;
- actionable stability guidance;
- status/next-command behavior;
- discovery of the supplied 27-file flat LTA archive;
- existing DATA9B1/DATA9B2 real-MACE regression compatibility;
- acyclic architecture dependencies;
- wheel/source execution parity.
