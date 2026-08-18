# MLFF Architecture Revision 96

**Release:** `mdstats 0.20.229a0`  
**Gate:** `COVREF-PAR1`

Revision 96 completes exact CPU parallelization of TARGET-DATA2B reference-radius construction. The historical family-by-family driver used multi-threaded native cKDTree queries inside a serial Python block loop. The new execution path uses the shared PARCORE1 deterministic queue as the outer concurrency layer and fixes each native tree call to one worker.

The scientific algorithm is unchanged: balanced correlation-unit masses, robust scales, scaled Euclidean metric, leave-one-out `beta=1/128` reference mass, extent statistics, family identities, and serialized authority remain identical. Row blocks write to disjoint output ranges, so arbitrary completion order cannot perturb results.

An execution-only adaptive block policy keeps query temporaries cache-sized and exposes enough tasks for high-core-count hosts. O(1) pair-rule and species-residual maps remove repeated linear record scans, and the historical target-label scalar constant-family rejection is moved before expensive radius construction without changing its predicate.

Clean-room qualification also hardened the PARCORE1 fallback boundary: direct FEAS1, NEIGHBOR1-rebuild, and MVIDX calls with no caller-supplied resource scope are no longer bound to transient auto-detected free-RAM snapshots. Explicit campaign scopes still enforce their RAM budgets exactly. This removes host-load-dependent direct-API failures without relaxing campaign memory admission.

The active performance qualification uses the supplied MACE-MPA-0 medium checkpoint only as campaign provenance. COVREF-PAR1 itself contains no foundation-model assumption and remains applicable to MACE-MH-1.

`MVKERNEL1` is the next optimization gate.
