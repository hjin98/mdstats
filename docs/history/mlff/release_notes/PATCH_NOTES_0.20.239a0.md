# mdstats 0.20.239a0 - Python 3.11 DATA6 progress syntax hotfix

This maintenance release fixes an invalid multiline f-string expression in the DATA6 progress reporter shipped in 0.20.238a0. The expression is accepted by the newer PEP 701 f-string grammar but is a SyntaxError under the project-supported Python 3.11 runtime. The timing fields are now computed before interpolation. No scientific, MVIDX, scheduler, or progress-format semantics change. Architecture revision 103 and dependency schema 83 remain current; FINAL-GPU1 remains next.
