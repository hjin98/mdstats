# NEIGHBOR1 FEAS1 -> MVIDX1 cloud CPU qualification

**Release:** mdstats 0.20.227a0  
**Architecture revision:** 94  
**Active foundation:** MACE-MPA-0 medium (NEIGHBOR1 contract also supports MACE-MH-1)  
**Scientific authority change:** none

NEIGHBOR1 computes exact TARGET-DATA2B neighborhoods once during FEAS1, streams canonical forward CSR, and lets MVIDX1 adopt that authenticated graph instead of repeating geometry. The benchmark uses the PERFBASE1 deterministic authority: 6 families, 49,152 witnesses, and 3,194,880 exact edges.

All trials retain FEAS1 digest `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613` and MVIDX1 digest `e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c`. The streamed forward CSR is invariant at `0220c89084fe957e85eb1e1c87a581eaa44869f11cb98bee7f7bd8cdafd3d74e`.

## Final same-host results

| Workers | Implementation | FEAS/CSR median (s) | MVIDX median (s) | Total median (s) | Process CPU median (s) |
|---:|---|---:|---:|---:|---:|
| 1 | untouched 0.20.226a0 | 0.7835 | 1.4182 | 2.2017 | 2.2304 |
| 1 | NEIGHBOR1 0.20.227a0 | 0.9609 | 0.3149 | 1.2758 | 1.3323 |
| 3 | untouched 0.20.226a0 | 0.5468 | 2.2269 | 2.7737 | 3.3085 |
| 3 | NEIGHBOR1 0.20.227a0 | 0.6990 | 0.3356 | 1.0346 | 1.5311 |

At the automatic three-lane budget the end-to-end median improves by **2.68x**, from 2.7737 s to 1.0346 s. At one worker it improves by **1.73x**. Isolated FEAS1 is slightly more expensive because it now produces the reusable CSR, but the eliminated second geometry sweep more than repays that cost.

An independent release-tagged reproduction was also retained rather than selecting only the favorable paired timing. Under later, noisier host scheduling it measured 1.3386 s at one worker and 1.5263 s at three workers, while reproducing all three scientific digests exactly. This is consistent with the gate rule that timings are execution evidence and exact output identity is the authority.

## Exact reuse checks

- FEAS-emitted and standalone-rebuilt forward CSR are identical across worker/block settings.
- MVIDX cached and rebuild paths are identical.
- Cache-hit MVIDX succeeds with `ExactNeighborhoodEngine.query_block` replaced by a fail-fast sentinel, proving no geometric query occurs.
- Native persistence round-trips exactly and rejects modified array bytes.
- Final CSR allocation is admitted against the stage RAM budget before stream materialization.

## Acceptance

**PASS.** Scientific digests are unchanged and the shared graph materially reduces FEAS1->MVIDX1 wall time. `MVIDX-REUSE1` is next; it will optimize only the remaining stable CSR-to-CSC inversion.
