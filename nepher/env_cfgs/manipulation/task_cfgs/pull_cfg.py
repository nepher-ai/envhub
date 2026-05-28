# Copyright (c) 2026, Nepher AI
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Pull manipulation preset configuration (stub — not yet implemented)."""

from __future__ import annotations

from isaaclab.utils import configclass

from nepher.env_cfgs.manipulation.preset_mani_cfg import PresetManipulationEnvCfg


@configclass
class PullPresetCfg(PresetManipulationEnvCfg):
    """Preset configuration for pull/drag manipulation tasks (not yet implemented)."""

    task_type: str = "pull"

    def get_object_cfgs(self):
        raise NotImplementedError(
            "PullPresetCfg is a stub.  Implement get_object_cfgs() in a subclass."
        )
