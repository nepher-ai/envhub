# Copyright (c) 2026, Nepher AI
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Insert manipulation preset configuration (stub — not yet implemented)."""

from __future__ import annotations

from isaaclab.utils import configclass

from nepher.env_cfgs.manipulation.preset_mani_cfg import PresetManipulationEnvCfg


@configclass
class InsertPresetCfg(PresetManipulationEnvCfg):
    """Preset configuration for insertion manipulation tasks (not yet implemented)."""

    task_type: str = "insert"

    def get_object_cfgs(self):
        raise NotImplementedError(
            "InsertPresetCfg is a stub.  Implement get_object_cfgs() in a subclass."
        )
