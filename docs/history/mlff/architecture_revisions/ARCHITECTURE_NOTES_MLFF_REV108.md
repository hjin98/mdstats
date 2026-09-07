# MLFF architecture revision 108 - Target-size normalization, practical ceiling, objective repair

Revision 108 closes three coupled defects in the target-size experiment.

**Optimizer-progress normalization.** Candidate `N` performs `ceil(N/B)`
optimizer updates per epoch under the screen's fixed number of dataset passes,
so a fixed learning rate and EMA decay gave larger candidates more optimizer
progress as well as more data - a second variable the experiment never intended.
Learning-rate amplitude and EMA decay are now normalized against one
configurable reference size (`1024 / 1.0e-4 / 0.99999` by default) by the exact
batch-aware scale `s_N = ceil(N_ref/B) / ceil(N/B)`, with no cap, floor, or
survivor-dependent rescaling. Each `(N, seed)` derives its realization once from
the full candidate geometry and replays it across every rung; restart validation
rejects drift. Everything else - epoch and fidelity boundaries, batch size, LR
shape, Adam settings, precision, seed set - is held fixed. The policy belongs to
P3 execution identity, so it invalidates trajectories without invalidating
preparation.

**Practical-ceiling selection.** The configured ladder ceiling is a practical
budget limit, not a requirement that convergence occur below it. A materially
superior `Nmax` is now `SELECTED` with the non-blocking warning code
`nonconverged_at_configured_ceiling` rather than a blocking terminal failure;
practical equivalence still prefers the smaller finalist, an interior winner is
selected normally, and genuinely insufficient comparison remains blocking. No new
status or lifecycle was added: the result commits through the ordinary
`TERMINAL_SELECTED` transition and continues to cross-validation. The
terminal-decision rule participates in P2 policy identity
(`practical_equivalence_then_practical_ceiling.v2`), so evidence reduced under
the retired blocking-ceiling rule stays historical and is never relabelled.

**Objective and weighting repair.** Target-size preparation resolved
`[objective]` through library defaults that merely happened to agree with the
configured values; it now shares one config resolver with post-selection. The
three weighting layers are separated: global E/F/S coefficients belong to
`TrainingObjectivePolicy` and are emitted explicitly into every generated MACE
configuration, per-configuration weights belong to `ConfigurationWeightPolicy`,
and per-frame property weights are local availability masks rather than per-frame
copies of the global ratio. The executable loss family moved from MACE's
`UniversalLoss` - which scales residuals inside a Huber evaluation and ignores
`config_weight`, and therefore cannot represent the declared contract - to the
native weighted energy+force+stress loss, whose reductions consume configuration
and property weights linearly. Model construction is unaffected, so
reconstruction and EVAL2 semantics are preserved while identity now names what
actually executes.

Historical fixed-LR, old-loss, and blocking-ceiling evidence remains readable
under its own schema and is never migrated into corrected evidence; the corrected
screen must establish fresh evidence under the corrected identities.
