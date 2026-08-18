# mdstats 0.20.102a0 patch notes

This release implements MLFF roadmap stage **OPT-VERIFY1**.

- verification structures are parsed once and copied per independent NVE case;
- each adaptive worker retains at most one private calculator and reuses it for adjacent cases on the same model/runtime identity;
- minimum pair distance uses an exact adaptive periodic neighbor list instead of allocating a full `N x N` MIC matrix at each sample;
- orthorhombic/triclinic/sparse-cell equivalence tests preserve the former numerical result;
- package runtime advances to 0.20.102a0 while the frozen MLFF scientific compatibility token remains 0.20.99a0.

No verification threshold, NVE integration setting, model identity, selection policy, or scientific acceptance rule changes.
