# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

Current MLFF workplans:

- `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN_V2.md` — controlling target-size architecture reset. Target-size selection is completed before CV construction; one target-size study population is partitioned into exact `Tmax(Nmax)` plus residual evaluation reserve; M1/M2/M3 form one frozen nested evaluation ladder; nominal target-size-stage capacity is `Nmax + M3`; the selected target dataset freezes before CV; CV then partitions that selected dataset for training validation and cannot feed back into target-size selection. The plan also introduces exponent-based target/evaluation ladders, configured-ceiling semantics, and destructive retirement of fixed/complement/migration/pre-selection-CV legacy paths.
- `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` — controlling only nonconflicting exact screening-continuation semantics: `fidelity_epochs` are exact `n1/n2/n3` boundaries and production `n` is independent. Any fixed-population, complement-EVAL2, TARGET-SIZE-V5 population-generation, or pre-selection-CV assumptions are superseded by the V2 architecture reset above.
- `MLFF_EVALUATION_PIPELINE_RAM_LEASE_FIX_WORKPLAN.md` — staged-evaluation RAM admission/resource-authority repair. Its execution/resource obligations remain reusable and do not reopen target-size population semantics.
- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout, subject to the V2 target-size population/lifecycle authority where affected.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — MLCV lifecycle/provenance correction. CV is downstream of selected target-size/dataset under V2; any earlier target-size/CV coupling is superseded.

Superseded target-size architecture-reset V1 is retained only as a stub at `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`; Git history preserves its full text. The separate `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN_V1_SUPERSEDED.md` notice is historical coordination only.

The completed TARGET-SIZE-V5 EVAL2 staged-execution/performance workplan is archived at `../archive/MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_WORKPLAN.md`; its accepted execution/resource ownership remains reusable, but its full-complement evaluation population and TARGET-SIZE-V5 generation semantics are not current authority.

The prior target-size Repair-1, screen/production decoupling, and flexible-fidelity workplans remain archived historical engineering context only. They do not independently impose current population, compatibility, migration, or CV-ordering requirements.

Full long real-data/GPU production qualification remains deferred to FINAL-GPU1. Sampling-policy qualification that lacks representative evidence must be reported as deferred/unavailable rather than passed.
