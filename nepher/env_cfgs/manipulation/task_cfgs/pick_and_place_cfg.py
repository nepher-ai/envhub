# Copyright (c) 2026, Nepher AI
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Pick-and-place manipulation preset configuration.

Extends :class:`PresetManipulationEnvCfg` with multi-scenario benchmark
support via :class:`PrebakedScenarioStrategy`.

Usage
-----
Subclass :class:`PickAndPlacePresetCfg` in a ``preset.py`` bundle file and
point ``scenario_file`` at a ``scenarios.json`` (same directory)::

    from pathlib import Path
    from nepher.env_cfgs.manipulation.task_cfgs.pick_and_place_cfg import (
        PickAndPlacePresetCfg,
    )

    class MyPickPlaceCfg(PickAndPlacePresetCfg):
        name = "my_pick_place"
        scenario_file = str(Path(__file__).parent / "scenarios.json")
        objects = [...]    # ManipulationObjectCfg — USD + physics only
        goals   = [...]    # ManipulationGoalCfg   — thresholds only

``self.position_strategy`` is populated automatically from the JSON in
``__post_init__``.  Positions (spawn + goal) come from the strategy at
episode reset time (``env_id % num_scenarios``).
"""

from __future__ import annotations

import json
from pathlib import Path

from isaaclab.utils import configclass

from nepher.env_cfgs.manipulation.preset_mani_cfg import PresetManipulationEnvCfg
from nepher.utils.strategies.prebaked_scenarios import PrebakedScenarioStrategy


@configclass
class PickAndPlacePresetCfg(PresetManipulationEnvCfg):
    """Preset configuration for pick-and-place manipulation tasks.

    Extends :class:`PresetManipulationEnvCfg` with:

    - ``task_type = "pick_and_place"``
    - ``scenario_file``: absolute or relative path to a ``scenarios.json``
      file.  Loaded in ``__post_init__`` and stored as
      ``self.position_strategy``.

    ``self.objects`` lists :class:`~nepher.env_cfgs.manipulation.preset_mani_cfg.ManipulationObjectCfg`
    entries for **USD paths and physics params only**.  Spawn / goal positions
    come exclusively from the loaded :class:`PrebakedScenarioStrategy` at
    episode reset time.

    ``self.goals`` lists :class:`~nepher.env_cfgs.manipulation.preset_mani_cfg.ManipulationGoalCfg`
    entries carrying **success thresholds** only (``pos_threshold``,
    ``ang_threshold``, etc.).  Positions in those entries are ignored when a
    strategy is present.
    """

    task_type: str = "pick_and_place"
    scenario_file: str = ""
    """Absolute or relative path to ``scenarios.json``.

    Relative paths are resolved from the current working directory.
    Use ``str(Path(__file__).parent / "scenarios.json")`` in preset files to
    anchor the path to the bundle directory.

    Empty string = no strategy loaded (falls back to random spawn / goal if
    ``spawn_range`` / ``goal_pose_range`` are set on the descriptors).
    """

    def __post_init__(self) -> None:
        """Load scenario strategy from ``scenario_file`` if provided."""
        if self.scenario_file:
            path = Path(self.scenario_file)
            if not path.is_file():
                raise FileNotFoundError(
                    f"PickAndPlacePresetCfg: scenario_file not found: {path}\n"
                    "Check that the path is absolute or relative to the CWD."
                )
            with open(path) as f:
                data = json.load(f)
            self.position_strategy: PrebakedScenarioStrategy = PrebakedScenarioStrategy(
                data["scenarios"]
            )
        else:
            self.position_strategy = None
