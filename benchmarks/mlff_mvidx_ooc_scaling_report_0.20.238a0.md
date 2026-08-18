# MLFF MVIDX multi-billion-edge scaling hardening - 0.20.238a0

The production failure occurred after a NEIGHBOR1 cache hit with 9,505,021,522 exact edges and 165 required families. PARCORE1 rejected one family because its full in-memory inversion estimate was 6.41 GiB while the stage RAM budget was 5.09 GiB. Reducing inverse worker count cannot solve a single-task-above-budget failure.

0.20.238a0 retains the normal compiled SciPy in-memory transpose for small/direct-API work, but campaign families with inverse payloads >= 8 MiB use an exact row-chunk out-of-core transpose. The final candidate-to-witness uint32 payload is written directly as NPY memmap, bounded chunk scratch is admitted by PARCORE1, and whole NPY-backed arrays are hard-linked into the durable native record where possible. The reported 9.505-billion-edge cache implies about 35.41 GiB of inverse uint32 edge storage; the campaign now preflights that disk requirement plus safety headroom before starting.

At the reported 5.09-GiB stage RAM budget, the same family class is admitted at roughly 0.64 GiB of bounded task accounting rather than 6.41 GiB of full-family in-memory accounting, permitting up to 7 such tasks by RAM admission before other work is considered.

Exactness qualification forces many source-row chunks and compares the result byte-for-byte against the original deterministic full SciPy transpose. Complete MVIDX content digests are unchanged between in-memory and out-of-core paths. The original 111 TARGET-DATA2 scientific tests remain passing with the same 18 warnings; four new out-of-core tests raise the combined functional count to 115.

Architecture revision 103 and dependency schema 83 are unchanged. FINAL-GPU1 remains next.
