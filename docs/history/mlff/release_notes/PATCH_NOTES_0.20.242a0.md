# mdstats 0.20.242a0 patch notes

## MVSEL2 forward/lazy selector chain

This release replaces new-campaign MVSEL1 eager inverse-scatter execution with MVSEL2, MVSTATE2, and REPAIR2 while preserving the frozen target-data scientific policy. MVIDX1 remains unchanged and legacy v1 records remain explicitly readable.

MVSEL2 uses compact witness multiplicity and exact candidate-forward scans in Phase A. Phase B uses an exact rebase followed by a certified lazy representative frontier with conservative outward-rounded bounds. REPAIR2 evaluates and applies active-shell swaps using the same forward state without reconstructing eager candidate gains or invoking inverse mutation. MVSTATE2 publishes authenticated atomic checkpoints containing continuation state only.

Production-density qualification used the read-only 36,408-candidate, 165-family, 9,505,021,522-edge campaign graph. Complete Phase A took 163.126 seconds, the sampled Phase-B maximum rank took 0.721 seconds with zero fallback, and the conservative full-order projection was 69.06 times faster than the same-host MVSEL1 projection. Current post-Phase-A release RSS was about 695 MiB; the exact global Phase-B rebase reached about 10.5 GiB current RSS and 36.1 GiB process peak through file-backed page residency. A 256-rank production-prefix MVSTATE2 checkpoint occupied 19,335,294 bytes, wrote in 0.081 seconds, read and revalidated in 0.340 seconds, and REPAIR2 processed the 128/256 rungs in 25.33 seconds with no inverse mutation. No GPU qualification was run.
