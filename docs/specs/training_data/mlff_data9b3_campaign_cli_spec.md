# Current-generation MLFF campaign CLI specification

Version: `mdstats 0.20.242a0` current contract
Status: implemented for the P1-P5 functional campaign lifecycle

## Purpose and authority

The campaign CLI projects the current source, statistical, target-size,
post-selection, and production owners into one restartable user workflow. It
does not replace those owners or create a second scientific state machine.
Architecture defines ownership and data flow; this specification defines the
public command, configuration, persistence, currentness, and failure contract.

The source-checkout entry point is:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml <command>
```

## Public command surface

The parser exposes exactly these commands:

```text
init
doctor
prepare
select-target-size
cross-validate
train-production
status
advance
guide
storage
```

The scientific lifecycle is:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`storage` is orthogonal artifact management. `status` and `advance` derive
their projection from the same current owners. The current campaign has no
separate pre-screen gate or downstream physical-test command; downstream
qualification is a later product boundary and is not dispatched by P6.

No command may silently skip a failed, stale, waiting, or incompatible current
authority. An automatic target-size diagnostic that completes without a
recommendation is reported as a successful diagnostic result: it leaves the
current provisional design unchanged and does not prohibit an explicit
target-size choice.

## User-visible layout

The operator supplies `campaign.toml`. The workspace contains:

```text
<workspace>/campaign-manifest.json
<workspace>/.mdstats/campaign.sqlite3
<workspace>/.mdstats/                 # current records and reconstructible caches
<workspace>/data/                      # current MACE materializations
<workspace>/runs/                      # authorized checkpoints and logs
<workspace>/models/                    # current production publication
<workspace>/results/                   # bounded summaries and cleanup reports
```

SQLite rows and content-addressed files are authoritative only through their
own current owners. File existence, a caller-held object, or a cache path is
not evidence of currentness.

## Configuration contract

`campaign.toml` owns requested policy and source locations. Runtime observations
and durable scientific outcomes are persisted separately. Paths are resolved
relative to the configuration file, and a non-positive execution timeout means
no campaign wall-clock timeout.

The generated current configuration exposes:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]

[post_selection.cv]
fold_count = 2
partition_seed = 7
seeds = [11]
max_num_epochs = 2
acceptance_maximum = 0.5

[post_selection.production]
seeds = [5]
```

The configured power ceiling is not a fixed scientific constant. Candidates
are additionally bounded by the available `P_train` population and the
current policy. Optimizer seeds are authored by the sole enabled training
method; there is no separate target-size seed namespace. Pre-target fold-count
and partition-seed fields are not current target-size/CV authoring controls.

The learned model precision is `single` (FP32) or `double` (FP64). Critical
mdstats reductions, geometry/statistical arithmetic, and persistent bookkeeping
remain FP64. The acceleration backend, MACE interface, and runtime identity
are bound by the doctor/current protocol record.

Policy configuration is fail-closed at the existing semantic owners. Finite
real fields reject booleans and strings, integer fields require actual
integers, boolean fields require actual booleans, and collection elements are
validated before canonical ordering or float conversion. This includes the
target-size normalization reference, global objective, and configuration-weight
policies. Current-schema readers reject malformed values before identity or
execution; only an explicitly supported historical reader may apply a
historical representation.

## Command behavior

### `init`

`init` writes an annotated configuration with current target-size and
post-selection sections. It must not generate retired lifecycle sections or
imply an unconfigured target-size ceiling. Existing configuration files are
not overwritten without the explicit force behavior defined by the parser.

### `doctor`

`doctor` checks source paths, manifest inputs, foundation/replay identity,
package/runtime imports, precision wrappers, requested backend, and available
resources. A successful result records the exact runtime realization used by
later owners. Unsupported hardware or unavailable long-production resources
remain an explicit unavailable/deferred condition, never a fabricated pass.

### `prepare`

`prepare` authenticates the manifest and constructs/reuses the current neutral
substrate:

```text
source/frame/label authority
  -> protected statistical relations
  -> one P_train/M3 split and pi_train/pi_eval
  -> one common target-size preparation
```

It selects no target size, trains no candidate, ranks no checkpoint, and
publishes no final model. It is restartable and idempotent when all current
inputs and identities match, including when the current generation already
carries a complete automatic diagnostic: an unchanged `prepare` is a successful
no-op that leaves the canonical generation, its diagnostic evidence, and its
derived result view exactly as they were.

`prepare` is the sole command permitted to interpret live inputs, so it also
owns detecting that they changed. Before reusing the stored lower-level
catalog it compares the approved manifest digest that catalog was built from
and each source's own byte-identity and control signatures against the files on
disk. Materially changed valid inputs are routed through the ordinary catalog
reconstruction path and committed as a fresh canonical generation; malformed or
unapproved changes still fail under their existing owners. No operator flag is
required for this. `--approve-manifest` records the reviewed digest;
`--refresh-inferences` refreshes proposed source metadata before approval;
`--rebuild-catalog` remains an explicit unconditional reconstruction request,
not the mechanism by which ordinary input changes are noticed.

Durable publication is create-or-verify. A prepared component, generation
manifest, or normalized frame entry whose content identity already exists on
disk is authenticated against that identity -- for a frame entry, including
every array member's hash, shape, and dtype -- before this generation may reuse
it. Conflicting or corrupt content fails before adoption and is never
overwritten, because another adopted generation may still depend on the bytes
that are actually there.

Adoption is compare-and-set against the currentness token captured *before* the
expensive construction began, and no campaign-wide writer lock is held across
that construction. Two concurrent preparations that produce the same prepared
identity converge on one generation; a preparation whose snapshot was built
against superseded state fails closed rather than advancing the newer
generation.

At the destructive generation boundary, obsolete derived target-size records
are detected before semantic decoding, quarantined under a namespace no
current loader reads, and rejected rather than migrated. Lower-level source or
content caches are reusable only after current-owner revalidation.

### `select-target-size`

```text
select-target-size <N>
select-target-size --auto
[--select-horizon-cv <positive integer>] [--select-horizon <positive integer>]
```

This command owns the **provisional** downstream training design and freezes
nothing. A bare invocation is invalid and must give actionable usage guidance;
`<N>` and `--auto` are mutually exclusive.

`select-target-size <N>` loads the current prepared generation, establishes
currentness, resolves the P2 qualified candidate set, requires `N` to be one of
those configured qualified candidates, derives `T_N = pi_train[:N]`, validates
that membership through the existing P2 training-order owner, resolves a
complete provisional horizon snapshot, and CAS-publishes the new proposal. It
performs **no** target-size candidate training and no EVAL2 work.

`--select-horizon-cv` sets the provisional CV max epochs and `--select-horizon`
the provisional final-production max epochs. Each successful proposal-setting
invocation resolves a complete proposal: an omitted flag resolves from
`[post_selection.cv].max_num_epochs` (default 30) or `[training].max_num_epochs`
(default 30) *at that moment*, and the resolved values are persisted, so later
configuration edits do not mutate an existing proposal. An earlier override never
becomes a sticky default. The CLI never rewrites `campaign.toml`.

`select-target-size --auto` runs or reuses the optional automatic diagnostic. It
runs the configurable ladder and direct evaluation populations through the
authenticated continuation

```text
n1 / M1 -> n2 / M2 -> n3 / M3
```

with paired optimizer seeds from the sole enabled method. Each candidate is an
exact prefix of the one `pi_train` order. The reducer publishes either a
**recommended** `N` with the exact identity of `pi_train[:N]`, or a typed
no-recommendation outcome. Replay and later validation evidence cannot affect
that computation. A valid recommendation becomes the current provisional `N`.

A completed diagnostic that produces no recommendation must not partially modify
any proposal field: the diagnostic evidence and its portable report are
committed, any previously valid proposal is unchanged, and the command returns
normal success while stating that no recommendation was established.

If a current reusable complete diagnostic already exists for the campaign's
automatic-screen scientific/execution identity, `--auto` authenticates and
reloads it, performs zero new TRAIN2/EVAL2 work, and says so. Provisional `N`,
either horizon flag, either configured horizon, report presentation, status
wording, report path, and selection-source provenance never invalidate a current
diagnostic.

A diagnostic may run for hours. It captures the selection state it intends to
update; if a newer explicit choice or a `cross-validate` freeze intervened, the
evidence and report are still published but the stale recommendation is not
installed, and the command says so.

Every terminal diagnostic writes one portable, self-contained Markdown report
under the campaign `results/` tree at a stable per-generation filename. It is a
derived, rebuildable projection of authenticated evidence and is never read as
authority.

Candidate learning-rate amplitude and EMA decay are normalized against the
configured reference size (`[target_data.size_convergence.optimizer_normalization]`)
so a larger candidate does not also receive more optimizer progress; epoch
counts, batch size, LR shape, and every other optimizer setting stay fixed
across candidates.

The configured ladder ceiling is a practical budget limit. When `Nmax` remains
materially superior to every other successful terminal finalist, it is
**recommended** and the result carries the non-blocking warning code
`nonconverged_at_configured_ceiling`; `status`, the derived result view, and the
portable report state the warning alongside the recommendation. Inside the
practical-equivalence band the smaller finalist is still preferred. Genuinely
insufficient comparison remains a typed no-recommendation outcome, and no
unconfigured intermediate or rescue size is ever synthesized.

### `cross-validate`

This command is the freeze boundary. It requires a current provisional proposal,
loads and authenticates the current prepared generation, revalidates the
proposed `N` against the current qualified candidate set, derives exact
`T_selected = pi_train[:N]`, reproduces its membership digest, and publishes the
frozen target selection together with both effective role horizons through the
existing currentness/CAS boundaries before any numerical CV work begins. No
automatic-diagnostic execution head or reducer is required for this transition.
After the freeze, `select-target-size` in either form must not mutate the
design.

It then constructs the
configured `K >= 2` post-selection folds inside exactly `T_selected`. It binds
protected relations, fold/seed identities, target-only checkpoint choice, and
the all-required-fold/all-required-seed acceptance predicate. It cannot alter
the selected size or membership. Missing, stale, or failed fold evidence blocks
final production while leaving the selected authority unchanged.

### `train-production`

This command requires accepted current post-selection method evidence. It
starts fresh from the accepted foundation and trains the complete exact
`T_selected` under the frozen production horizon and the production policy. A
screen or CV checkpoint is never a production parent. Publication rechecks
currentness at commit time and cannot promote work from a superseded
generation.

### `status`, `advance`, and `guide`

`status` projects the current owner states and reports the next safe action.
`advance` dispatches only the next current lifecycle owner. `guide` prints the
same six-command scientific lifecycle and current configuration/restart
semantics. Neither command writes a second scientific authority.

Observation is read-only, coherent, and authenticated. One lifecycle answer
reads the target-size revision and every post-selection/qualification pointer
row it depends on inside a single campaign-store read transaction, so the
ancestry it reports is one that existed: pointer publication mutates campaign
metadata without moving the target-size revision, and an answer may never
combine a pre-publication view of one stage with a post-publication view of
another. Each compact record a pointer names is loaded through its accepted
read-only typed store and must reproduce the identity the pointer named before
any of its fields -- a cross-validation acceptance, a release verdict --
influences the report. A missing, unparseable, or misidentified record is
reported as blocked. Observation creates no evidence root, opens no provider,
and reconstructs no upstream authority.

### `storage`

Storage reports and manages only campaign-owned artifacts. Read-only inventory
is available through `storage report`. Cleanup tiers require their documented
dry-run/apply behavior; archive create, integrity check, and restore are
reversible and independently content-checked. External inputs, current
scientific records, selected checkpoints, restart state, and diagnostic
evidence remain protected.

## Persistence and restart

`CampaignStore` shall:

1. use one SQLite database for durable campaign state;
2. serialize canonical payloads with content identities under their owners;
3. record operational stage state without treating it as scientific authority;
4. preserve the latest successful evidence before process exit;
5. retain bounded event history;
6. never use the database location itself as scientific identity.

Current preparation and post-selection owners rederive their input identities
on every reopen. A matching completed record is reused only after source,
policy, parent, payload, and currentness authentication. A missing, corrupt,
stale, or incompatible derived cache is rebuilt by its owner; it is not
silently accepted or translated.

Each current write uses a generation-neutral prepare/restart identity. A
historical generation marker may be inspected only by the reject-only cutover
detector and may not authorize semantic reconstruction. The exact accepted
current-generation P5A6 workspace must remain reopenable without a pre-load
rewrite; P6 compatibility evidence is separate from fresh P6 restart evidence.

Configuration changes have selective invalidation:

```text
target/frame/label/order/ladder/fidelity/common-preparation change
    -> new target-size generation and descendants
post-selection CV-only change
    -> CV and final-production descendants only
production-only horizon/runtime change
    -> final-production descendants only
```

Provenance-only presentation changes do not change scientific arithmetic.

## Failure contract

The CLI fails closed for unapproved or changed manifests, missing or
incompatible source/foundation/replay inputs, invalid labels, unresolved
protected relations, unsupported policy generation, stale current pointers,
missing required folds/seeds, corrupt checkpoint/companion state, no admissible
checkpoint, target-size lineage mismatch, incompatible persisted state, or a
currentness race at publication.

Keyboard interruption returns the parser's documented interruption status and
states that authenticated records remain resumable. Errors identify the owning
command and the safe corrective action; they do not fall back to a different
scientific selector or downstream model.

## Acceptance boundary

The current CLI contract is established through the real parser/facade,
generated-config parsing, current prepare/selection/CV/production owners,
CampaignStore close/reopen, currentness reauthentication, storage cleanup
owners, and exact-generation reject-before-reuse tests. The mandatory
P5A6-to-P6 qualification additionally authenticates the baseline worktree and
import roots before producing state, then opens the unchanged workspace in a
separate P6 process.

P6 acceptance is current functional/restart/public-surface closure. It is not
GPU, long real-data, M-ladder decision-preservation, deployment, physical,
calibration, locked-test, or final-release qualification.
