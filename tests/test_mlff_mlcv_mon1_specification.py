from __future__ import annotations

import mdstats




def test_mlcv_mon1_public_monitor_contract() -> None:
    assert mdstats.MLCV_MONITOR_POLICY_SCHEMA == "mdstats.mlcv-monitor-policy.v1"
    assert mdstats.MLCV_MONITOR_CATALOG_SCHEMA == "mdstats.mlcv-monitor-catalog.v1"
    policy = mdstats.MlcvMonitorPolicy()
    assert policy.target_light_configurations == 256
    assert policy.replay_light_configurations == 512
    assert policy.training_diagnostic_configurations == 256
    for name in (
        "MlcvMonitorPolicy",
        "MlcvRunMonitorRecord",
        "MlcvReplayMonitorRecord",
        "MlcvMonitorCatalog",
        "write_mlcv_diagnostic_history",
    ):
        assert name in mdstats.__all__
