# MLFF architecture revision 63 - FOUNDATION-AUDIT1 configuration-plumbing hotfix

**Release:** `mdstats 0.20.196a0`  
**Gate:** `FOUNDATION-AUDIT1-HF1`  
**Dependency-graph schema:** `45`

Revision 63 repairs an orchestration-only defect in `campaign_cli._ensure_foundation_target_audit()`. The helper consumes `performance.foundation_audit_temporary_ram_mib` to bound transient audit memory, but revision 62 left that configuration lookup referencing a non-local `cfg` symbol. A workstation prepare run therefore reached FOUNDATION-AUDIT1 after DATA6 and raised `NameError` before audit construction.

The helper now receives the campaign configuration explicitly as a keyword-only argument from `_prepare_materialization()`. Regression coverage invokes the helper with a non-default RAM setting and verifies the exact byte threshold propagated to `build_foundation_target_audit()`. A static top-level helper sweep confirms no other `campaign_cli.py` function loads `cfg` without receiving or defining it.

No scientific authority changes: foundation-model identity, DATA6 descriptors/predictions, FOUNDATION-AUDIT1 metric definitions, target role freezes, source e3nn execution, TRAIN2 CuEq execution, deterministic selection, and restart/content identities remain unchanged.
