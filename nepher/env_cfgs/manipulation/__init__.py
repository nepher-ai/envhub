"""Manipulation environment configuration classes.

- AbstractManipulationEnvCfg: Abstract base with scene-description hooks
- PresetManipulationEnvCfg: Fully specified preset (objects, goals, table, lighting)
- ManipulationObjectCfg: Per-object descriptor (rigid / deformable / articulated)
- ManipulationGoalCfg: Per-goal descriptor (interpreted by the IsaacLab HL env)

Task-type subclasses (in ``task_cfgs/``):
- PickAndPlacePresetCfg: Pick-and-place with multi-scenario benchmark support
- StackPresetCfg:   Stacking tasks (stub)
- InsertPresetCfg:  Insertion tasks (stub)
- PullPresetCfg:    Pull/drag tasks (stub)
"""

from nepher.env_cfgs.manipulation.base_mani_cfg import AbstractManipulationEnvCfg
from nepher.env_cfgs.manipulation.preset_mani_cfg import (
    ManipulationGoalCfg,
    ManipulationObjectCfg,
    PresetManipulationEnvCfg,
)
from nepher.env_cfgs.manipulation.task_cfgs import (
    InsertPresetCfg,
    PickAndPlacePresetCfg,
    PullPresetCfg,
    StackPresetCfg,
)

from nepher.env_cfgs.registry import register_config_class

register_config_class("manipulation", "preset", PresetManipulationEnvCfg)
register_config_class("manipulation", "pick_and_place", PickAndPlacePresetCfg)

__all__ = [
    "AbstractManipulationEnvCfg",
    "ManipulationGoalCfg",
    "ManipulationObjectCfg",
    "PresetManipulationEnvCfg",
    "PickAndPlacePresetCfg",
    "StackPresetCfg",
    "InsertPresetCfg",
    "PullPresetCfg",
]
