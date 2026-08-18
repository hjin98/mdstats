# mdstats 0.20.241a0 - MVSEL production-density scaling hardening

This maintenance release fixes the time and RAM behavior of TARGET-DATA2C-MVSEL1 on the supplied 36,408-candidate, 165-family, 9.51-billion-edge MPA-0 campaign index. The earlier implementation materialized a complete FP64 indexed-weight array per family during initialization and retained every processed scatter row until its numerical guard ran. On the largest production families those transients drove peak RSS near the 64 GiB workstation limit.

Initialization now gathers weights in exact complete-CSR-row chunks under a 512 MiB temporary target and advises the operating system that scanned inverse mmap pages may be reclaimed. Sparse updates keep a candidate-sized touched bitmap. Families whose candidate/witness rectangle is at least 98% populated use sorted contiguous-run adds while preserving canonical witness order and one identical FP64 scalar operation per candidate.

The scoped production profile restores the authenticated MVIDX, initializes MVSEL, executes rank 0, and stops. Initialization improves from about 80.3 s to 55.9 s; rank 0 improves from about 239.9 s to 49.7 s; combined work improves about 3.03x. Peak RSS falls from about 51.5 GiB to 19.2 GiB. Exact kernel/oracle tests pass. The complete `prepare` campaign was not run, GPU behavior is not qualified, and CPU threading remains rejected as a low-value memory-bandwidth optimization.

Architecture revision 103, dependency schema 83, scientific selector identity, persisted MVSEL/MVSTATE schemas, and `FINAL-GPU1` as the next scientific gate remain unchanged.
