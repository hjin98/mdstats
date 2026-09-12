# Historical narrative: replay label default and stage-ownership evolution

**Status:** non-normative history
**Current authority:** `docs/arch_manuals/mlff_training_data/40_training_evaluation.md` and the specifications indexed by `docs/specs/training_data/README.md`

## What the single external replay source originally assumed

Replay unification replaced the split-file replay interface with one external
`[paths].replay_set` corpus and derived every train/monitor/true-label/pseudo
file internally. During that transition the generated configuration emitted
`label_mode = "foundation_pseudolabel"`, and a campaign that omitted every
label selector was rejected or, through a legacy alias, could resolve into
pseudo semantics. Pseudo replay therefore behaved like a de facto default even
though it is the expensive and less direct of the two label policies.

Construction ownership was equally implicit. One helper resolved *and built*
the whole single-source replay authority, and everything that needed replay
called it: `doctor`, replay qualification, and every post-selection consumer.
That single helper was convenient, and it was also the defect: describing or
validating a campaign could build replay science, and consuming replay science
could rebuild it.

## Why that combination produced a resource failure, not only a modelling one

A cold single-source pseudo-label path could enter replay-wide MACE inference
before TRAIN2 scheduler admission, because the owner that happened to run
first - `doctor`, or a post-selection read - constructed the prediction cache.
The internally constructed CUDA provider was never explicitly retired and the
per-batch executor was recreated for every outer batch, so the PyTorch
allocator high-water and the provider residency survived the operation. TRAIN2
then correctly observed a large live baseline and could resolve zero safe
admissions and fail closed.

The scheduler was not the owner of that residency and was not weakened to
compensate. The corrected owners are: source truth is the default label policy,
pseudo is explicit, replay-wide pseudo inference belongs only to `prepare`, and
the provider lifetime ends at that prepare-time consumer.

## What the current contract fixes, and why each part exists

- **Source truth is the new single-source default.** Omitting every label
  selector resolves to `TRUE_DFT`; generated configuration states it
  explicitly. Pseudo stays opt-in because it is the choice that costs a
  foundation inference pass over the whole replay corpus.
- **One selector normalization.** Agreeing legacy aliases normalize to the same
  canonical choice; conflicting or unsupported spellings are rejected instead
  of silently defaulting in either direction.
- **Exact configuration domains.** Split seed and ratio components are exact
  integers, so two different campaign spellings cannot coerce onto one
  scientific split.
- **Construction and consumption are different owners.** `doctor` validates;
  `prepare` constructs and publishes; post-selection authenticates and may
  rebuild only disposable representations. `replay_plan_doctor` is retired from
  current single-source use rather than kept with weaker meaning, and realized
  replay qualification moved to the owner that actually realizes it.
- **Current replay records are exact interface state.** Mode switches *and*
  interface switches - single-source to none, single-source to legacy split -
  retire the aliases that no longer belong, atomically, without deleting
  physical caches or immutable history.
- **Long mutable-source reads verify consumed geometry.** A pre-read content
  check cannot prove the bytes read later, so each consumed frame reproduces
  its authenticated canonical geometry identity before dependent output is
  recorded under it, and the source is re-authenticated before publication.
- **Execution realization is not scientific identity.** Prediction batch width,
  shard size, graph-cache layout, progress reporting, and a learned OOM-safe
  batch never cause reinference or lineage churn.
- **Pseudo predictions survive truth-label-only changes.** Foundation
  predictions depend on geometry and prediction policy, not on source truth, so
  a truth-only mutation with unchanged geometry keeps them while the
  independent mandatory TRUE_DFT monitor refreshes on its own.
- **Lifecycle observes one coherent snapshot.** Target revision, current replay
  lineage, and P5/P7 pointers are read together, because each read being
  internally coherent does not make their combination a state that existed.

## Consequences for existing campaigns

A campaign that relied on the earlier omitted-selector interpretation is a
genuine semantic change and its old evidence is historical rather than
reinterpreted. The narrowed preparation-configuration projection also means an
in-flight campaign is asked to rerun `prepare` once; the target-size scientific
substrate, its screen evidence, and its frozen selection are unaffected,
because replay has never been a target-size scientific parent.
