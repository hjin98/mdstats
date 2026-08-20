# G4-N3 native MVSEL2 product closeout

Date: 2026-08-20
Branch: `feat/mvsel2-forward-lazy`

## Scope

This record closes the product-performance gate for the exact forward-only MVSEL2 native/OpenMP Phase-B implementation. Raw workstation evidence is retained in the repository root as `g4n3-mvsel2.txt`, `g4n3-time.txt`, `g4n3-disk-before.txt`, and `g4n3-disk-after.txt`.

## Real-MVIDX preflight

The bounded preflight evaluated 64,869,475 real MVIDX1 forward edges over 256 deterministic available candidates.

| workers | best time | speedup vs native 1 worker |
|---:|---:|---:|
| 1 | 0.037 s | 1.00x |
| 2 | 0.024 s | 1.56x |
| 4 | 0.016 s | 2.34x |
| 8 | 0.014 s | 2.59x |

The 2.59x best parallel speedup exceeded the 1.75x activation threshold, so the product path selected 8 workers.

## Product selection

- restart cardinality: 2,048
- restart mode: `mvstate2+journal`
- Phase-B backend: `native-openmp`
- effective workers: 8
- final cardinality: 16,384
- selector progress time from resumed 2,048 state to 16,384: 00:06:17
- final reported throughput: 37.996 ranks/s
- complete MVSEL2 stage acceptance time: 00:10:12
- accepted checkpoints: 7
- native forward runtime: true
- rank history: true
- cumulative candidate-evaluation forward edges: 1,031,737,100,160
- cumulative mutation forward edges: 3,928,291,901

The new-rank interval contains 14,336 accepted ranks, corresponding to approximately 72.0 million candidate-evaluation forward edges per new rank. The prior G4b product baseline was approximately 2.0 ranks/s and approximately 95.8 million evaluation edges/rank, so G4-N3 is roughly 19x faster in rank throughput while also reducing evaluated-edge demand by about 25%.

## Resource envelope

The enclosing 20-minute `prepare` command continued into REPAIR2 after MVSEL2 had already completed and therefore cannot isolate MVSEL2 peak memory. Whole-command evidence was:

- wall time: 00:20:02.28 (external timeout, exit 124, during REPAIR2)
- user time: 3,037.17 s
- system time: 132.87 s
- peak RSS: 90,532,644 KiB
- major faults: 74,186
- minor faults: 13,819,157
- swap: 0
- filesystem input: 161,069,304 blocks
- filesystem output: 323,360 blocks
- `.mdstats` size before: 87G
- `.mdstats` size after: 87G

The peak RSS is approximately 1.9% above the historical G4b whole-stage value and includes REPAIR2 activity, so it is recorded as a non-attributable whole-command caveat rather than an MVSEL2 regression. No swap occurred, no second persistent graph was created, and the G4c/G4d release/refault execution path remained retired.

## Gate decision

G4-N2 and G4-N3 PASS.

The native/OpenMP exact row scorer is retained as the accepted production Phase-B execution backend with the existing bitwise runtime qualification and G4b serial fallback. No further MVSEL2 optimization is justified before downstream stages are measured.

The next observed bottleneck is REPAIR2: after MVSEL2 acceptance, the same run reported REPAIR2 rungs 128, 256, and 512 at approximately 00:00:37, 00:00:38, and 00:00:41 respectively with zero proposals, then reached the external 20-minute timeout before the next rung report. REPAIR2 therefore becomes the next optimization boundary.
