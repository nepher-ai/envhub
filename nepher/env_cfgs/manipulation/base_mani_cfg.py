# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Abstract base environment configuration for manipulation environments."""

from __future__ import annotations

from isaaclab.assets import AssetBaseCfg
from isaaclab.utils import configclass

from nepher.env_cfgs.base import BaseEnvCfg


@configclass
class AbstractManipulationEnvCfg(BaseEnvCfg):
    """Base configuration for manipulation environments.

    Subclasses describe a physical scene (table, objects, lighting, workspace
    bounds) without encoding any task logic.  The IsaacLab environment reads
    the typed objects and goals and configures its own rewards, events, and
    terminations from them.
    """

    # Environment identification
    name: str = "abstract_manipulation"
    description: str = "Abstract manipulation environment"
    category: str = "manipulation"

    # Shared layout parameters
    env_spacing: float = 2.5
    """Centre-to-centre distance between parallel environments (m)."""

    max_episode_length_s: float = 10.0
    """Maximum episode duration in seconds."""

    # ========== Required implementations ==========

    def get_terrain_cfg(self):
        """Return ground-plane terrain configuration."""
        raise NotImplementedError("Subclass must implement get_terrain_cfg()")

    def get_scene_cfg(self):
        """Return self (the cfg acts as its own scene descriptor)."""
        return self

    def get_object_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Return dict mapping object name → IsaacLab AssetBaseCfg.

        Implementations must dispatch on each object's ``physics_type`` to
        produce the appropriate cfg subclass (``RigidObjectCfg``,
        ``DeformableObjectCfg``, ``ArticulationCfg``).
        """
        raise NotImplementedError("Subclass must implement get_object_cfgs()")

    def get_goals(self) -> list:
        """Return list of ``ManipulationGoalCfg`` descriptors."""
        return []

    def get_workspace_bounds(self) -> tuple[float, float, float, float]:
        """Return workspace bounds ``(x_min, y_min, x_max, y_max)``."""
        raise NotImplementedError("Subclass must implement get_workspace_bounds()")

    # ========== Optional hooks ==========

    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Return dict of lighting asset configs."""
        return {}

    def get_table_cfg(self) -> AssetBaseCfg | None:
        """Return table asset config, or ``None`` to keep the env default."""
        return None

    def get_metric_names(self) -> list[str]:
        """Return metric names tracked during evaluation."""
        return []
