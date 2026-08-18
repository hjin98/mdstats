# FOUNDATION-AUDIT1-HF1 specification

**Release:** `mdstats 0.20.196a0`  
**Architecture revision:** `63`  
**Graph schema:** `45`

## Failure

`campaign_cli._ensure_foundation_target_audit()` consumes the campaign setting `performance.foundation_audit_temporary_ram_mib` but previously referenced `cfg` without receiving it. After DATA6 materialization, FOUNDATION-AUDIT1 therefore raised `NameError: name 'cfg' is not defined` before audit construction.

## Acceptance

1. `_ensure_foundation_target_audit()` receives `cfg` explicitly as a keyword-only argument.
2. `_prepare_materialization()` passes the active campaign configuration to the helper.
3. A non-default RAM limit is converted exactly from MiB to bytes and forwarded to `build_foundation_target_audit()`.
4. Non-positive RAM limits retain the existing fail-closed validation.
5. No other top-level `campaign_cli.py` helper reads an unbound `cfg` symbol.
6. DATA6, FOUNDATION-AUDIT1 science, e3nn source policy, CuEq TRAIN2 policy, deterministic selections, and restart/content identities are unchanged.
