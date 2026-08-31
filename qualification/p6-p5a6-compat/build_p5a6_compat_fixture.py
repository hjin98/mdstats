"""Create the mandatory P6 revision-4 P5A6 compatibility fixture.

Runs under the exact accepted P5A6 baseline tree (commit 1670275 / tree
17e2c56).  It drives the real production owners - real config load, real
CampaignStore/SQLite, real P1/P2/P3 preparation and screen, the real P4
reducer/terminal, the real post-selection CV owners and the real fresh final
production/publication owners - through the production CLI parser/dispatch.

Only MACE's numerical work is substituted, at the seams P5 already accepted
below the mdstats owner boundary.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

TARGET = Path(sys.argv[1]).resolve()
if TARGET.exists():
    shutil.rmtree(TARGET)
TARGET.mkdir(parents=True)

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests._mlff_post_selection_fixture import (  # noqa: E402
    PostSelectionHarness,
    build_selected_campaign,
    run_cross_validate,
    run_train_production,
)
from mdstats.training_data import _campaign_cli_core as cli  # noqa: E402
from mdstats.training_data._campaign_cli_core import CampaignStore  # noqa: E402
from mdstats.training_data.campaign_post_selection import (  # noqa: E402
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (  # noqa: E402
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_state import (  # noqa: E402
    load_target_size_campaign_revision,
)

config, workspace = build_selected_campaign(TARGET)
assert run_cross_validate(config, PostSelectionHarness()) == 0
assert run_train_production(config, PostSelectionHarness()) == 0

# Read back through the real owners so the recorded identity is production truth.
cfg, paths = cli._load_config(config)
store = CampaignStore(paths.state_db)
try:
    revision = load_target_size_campaign_revision(store)
    terminal = revision.state.terminal
    selected = load_current_selected_training_context(cfg, paths, store)
    context = build_post_selection_context(cfg, paths, store, trainer=object())
    plan = resolve_current_cv_plan(context)
    acceptance = resolve_current_cv_acceptance(context)
    final_plan = resolve_current_final_production_plan(context)
    identity = {
        "baseline_commit": "1670275487d29bbcde4c59efafdef9d1f8b0ced7",
        "baseline_tree": "17e2c5609974712bda1efd3375f09f42da830f68",
        "generation": revision.state.generation,
        "regime": revision.state.regime.value,
        "lifecycle": revision.state.lifecycle.value,
        "frame_authority_digest": revision.state.frame_authority_digest,
        "neutral_statistical_base_digest": revision.state.neutral_statistical_base_digest,
        "split_exclusion_digest": revision.state.split_exclusion_digest,
        "experiment_definition_digest": revision.state.experiment_definition_digest,
        "common_preparation_digest": revision.state.common_preparation_digest,
        "adopted_execution_head_digest": revision.state.adopted_execution_head_digest,
        "n_selected": terminal.selected_target_size,
        "selected_membership_digest": terminal.selected_membership_digest,
        "selected_membership": list(selected.selected_membership),
        "selected_binding_digest": selected.binding.content_digest,
        "method_identity_digest": context.method.content_digest,
        "cv_plan_digest": plan.content_digest,
        "cv_acceptance_digest": acceptance.content_digest,
        "final_plan_digest": final_plan.content_digest,
    }
finally:
    store.close()

(TARGET / "P5A6_FIXTURE_IDENTITY.json").write_text(
    json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(identity, indent=2, sort_keys=True))
