# mdstats 0.20.203a0 patch notes

This release implements **TARGET-DATA2C-REPAIR1** (architecture revision 70 / graph schema 52) as diagnostic/pre-migration evidence. REPAIR1 operates only inside the active shell of each MVSEL1 rung, removes only frames with negligible exact unique coverage and no required-obligation ownership, and chooses replacements from the current exact hard/coverage deficit frontier. Every accepted swap strictly improves the frozen lexicographic objective, preserves all lower frozen prefixes, and assigns the replacement to the removed frame's rank.

The MVSEL1 reconstructible obligation cache now retains exact selected multiplicities rather than capping counts at the minimum requirement. This does not change MVSEL1 decisions; it supplies REPAIR1 with exact removal-safety information without subset rescans.

`prepare` now records `target_multi_view_repair` after `target_multi_view_selection` and before the unchanged revision-64 TARGET-DATA2C v4 ladder. No DATA8 membership, target-size learning authority, CuEq policy, or generated default changes in this release.
