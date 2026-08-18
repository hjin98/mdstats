# mdstats 0.20.232a0 - MVQUAL-PAR1

- Complete MLFF architecture revision 99 / `MVQUAL-PAR1`.
- Add a global PARCORE1 queue for independent same-N domain/selector/size scoring jobs.
- Preserve exact TARGET-DATA2B coverage, MVIDX cross-check, hard-obligation, telemetry, and persisted MVQUAL authority.
- Constrain nested campaign numerical workers to one per outer job, with canonical post-queue comparison reduction.
- Preserve historical direct-API native-thread behavior when no resource scope is supplied.
- Add `[performance].target_multi_view_qualification_workers`, automatic four-lane ceiling, and RAM-admitted score-task estimates.
- Preserve benchmark plan digest `2ebd7f5dc2b560e3150fe4849e7098be2eff56469779f15b2befda74059fc90b` and record about 2.12x paired wall-time improvement on the cloud CPU.
- Keep MACE-MPA-0 medium as the active qualification checkpoint while preserving the same execution contract for MACE-MH-1.
- Next gate: `AUDIT-EVAL-PERF1`.
