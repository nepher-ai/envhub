# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Stack manipulation preset configuration (stub — not yet implemented).

Placeholder for stacking task presets.  Subclass :class:`StackPresetCfg`
when implementing stack-specific scene descriptions and success criteria.
"""

from __future__ import annotations

from isaaclab.utils import configclass

from nepher.env_cfgs.manipulation.preset_mani_cfg import PresetManipulationEnvCfg


@configclass
class StackPresetCfg(PresetManipulationEnvCfg):
    """Preset configuration for stacking manipulation tasks.

    Not yet implemented.  Raises :exc:`NotImplementedError` if instantiated
    without overriding the task-specific hooks.
    """

    task_type: str = "stack"

    def get_object_cfgs(self):
        raise NotImplementedError(
            "StackPresetCfg is a stub.  Implement get_object_cfgs() in a subclass."
        )
