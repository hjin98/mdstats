# mdstats 0.20.196a0 - FOUNDATION-AUDIT1 configuration hotfix

## Fixed

A workstation `prepare` run could complete DATA6 recovery and then fail at the start of FOUNDATION-AUDIT1 with:

```text
NameError: name 'cfg' is not defined
```

`_ensure_foundation_target_audit()` reads `performance.foundation_audit_temporary_ram_mib`, but the helper did not receive the campaign configuration. The function now takes `cfg` explicitly and `_prepare_materialization()` passes the active campaign configuration.

## Scientific impact

None. The exception occurred before `build_foundation_target_audit()` was called. FOUNDATION-AUDIT1 definitions and all upstream DATA6/source/TRAIN2 identities are unchanged. Existing valid DATA6 artifacts remain reusable, so the same `prepare` command may be rerun without deleting the workspace.

## Regression

A new helper-level regression uses `foundation_audit_temporary_ram_mib = 321` and verifies that exactly `321 * 1024**2` bytes are passed to the audit builder. The release hardening sweep also checks for other top-level `campaign_cli.py` helpers that read an unbound `cfg`; none remain.
