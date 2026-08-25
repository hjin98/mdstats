# MLFF architecture revision 106 - Configurable target-size fidelity

Revision 106 makes target-size screening a configurable semantic three-boundary
funnel. The current defaults are `(1,3,10)` under an independent full TRAIN2
horizon of `30`, but neither the graph nor the protocol identity treats those
default numbers as architecture-stage names.

The target-size policy owns the configured coarse, short, and final screen
boundaries. Training-budget policy independently owns the full schedule horizon;
screen checkpoints are exact continuation endpoints on that schedule, not
shortened schedules. Final-screen and full-horizon reference roles remain
distinct even when they coincide physically.

The only supported historical compatibility boundary is the immediately
preceding fixed-fidelity campaign. It can reuse authenticated unchanged
preparation inputs after re-authentication, but historical target-size evidence
is never relabeled as configurable-fidelity evidence. Older or ambiguous state
fails closed and is re-prepared at the narrowest safe boundary.
