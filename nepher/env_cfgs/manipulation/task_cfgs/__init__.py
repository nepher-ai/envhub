# Copyright (c) 2026, Nepher AI
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Task-type-specific manipulation preset configurations.

Each submodule provides a :class:`PresetManipulationEnvCfg` subclass scoped to
a particular objective type, making it easy to register, discover, and extend
each task family independently.

Available task types
--------------------
* ``pick_and_place`` — :class:`PickAndPlacePresetCfg`
* ``stack``          — :class:`StackPresetCfg`         (stub, not yet implemented)
* ``insert``         — :class:`InsertPresetCfg`        (stub, not yet implemented)
* ``pull``           — :class:`PullPresetCfg`          (stub, not yet implemented)
"""

from nepher.env_cfgs.manipulation.task_cfgs.pick_and_place_cfg import (
    PickAndPlacePresetCfg,
)
from nepher.env_cfgs.manipulation.task_cfgs.stack_cfg import StackPresetCfg
from nepher.env_cfgs.manipulation.task_cfgs.insert_cfg import InsertPresetCfg
from nepher.env_cfgs.manipulation.task_cfgs.pull_cfg import PullPresetCfg

__all__ = [
    "PickAndPlacePresetCfg",
    "StackPresetCfg",
    "InsertPresetCfg",
    "PullPresetCfg",
]
