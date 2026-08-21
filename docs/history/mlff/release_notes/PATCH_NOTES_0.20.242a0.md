# mdstats 0.20.242a0 patch notes

## MVSEL2 forward/lazy selector chain

This release candidate replaces new-campaign MVSEL1 eager inverse-scatter execution with MVSEL2, MVSTATE2, and REPAIR2 while preserving the frozen target-data scientific policy. MVIDX1 remains unchanged and legacy v1 records remain explicitly readable.

MVSEL2 uses compact witness multiplicity and exact candidate-forward scans in Phase A. Phase B uses an exact rebase followed by a certified lazy representative frontier with conservative outward-rounded bounds. REPAIR2 evaluates and applies active-shell swaps using the same forward state without reconstructing eager candidate gains or invoking inverse mutation. MVSTATE2 publishes authenticated atomic checkpoints containing continuation state only.

## Historical pre-hardening performance evidence

Before the Protocol-v3 hardening rescue, production-density measurements were collected on the read-only 36,408-candidate, 165-family, 9,505,021,522-edge campaign graph. Complete Phase A took 163.126 seconds, the sampled Phase-B maximum rank took 0.721 seconds with zero fallback, and the conservative full-order projection was 69.06 times faster than the same-host MVSEL1 projection. Post-Phase-A release RSS was about 695 MiB; the exact global Phase-B rebase reached about 10.5 GiB current RSS and 36.1 GiB process peak through file-backed page residency. A 256-rank production-prefix MVSTATE2 checkpoint occupied 19,335,294 bytes, wrote in 0.081 seconds, read and revalidated in 0.340 seconds, and the then-current REPAIR2 path processed only the 128/256 production-prefix rungs in 25.33 seconds.

Those measurements are retained as historical pre-hardening evidence only. They do **not** constitute Protocol-v3 acceptance of the rescued candidate and do not satisfy the current full-ladder REPAIR2 requirement through rank 16,384, the full non-slow regression requirement, clean wheel/install/import qualification, or StageResourceScope production integration qualification. Those checks remain `NOT_RUN` until executed against the frozen rescued candidate in the target workstation environment with the production campaign inputs. No GPU qualification has been run; GPU remains `DEFERRED_NOT_RUN`.
