# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Preset manipulation environment configuration.

A preset describes the physical scene for a manipulation task:

- A flat list of ``ManipulationObjectCfg`` (heterogeneous physics types —
  rigid, deformable, articulated).
- A flat list of ``ManipulationGoalCfg`` that the IsaacLab HL env uses to
  configure its termination and reward logic (the preset itself carries no
  task logic).
- Table USD, workspace bounds, and lighting.

``get_object_cfgs()`` dispatches on each object's ``physics_type`` and
returns a dict of IsaacLab ``AssetBaseCfg`` subclasses ready to inject into
an ``InteractiveSceneCfg``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg, RigidObjectCfg
from isaaclab.sim.schemas.schemas_cfg import (
    CollisionPropertiesCfg,
    RigidBodyPropertiesCfg,
)
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass

from nepher.env_cfgs.manipulation.base_mani_cfg import AbstractManipulationEnvCfg


# ---------------------------------------------------------------------------
# Per-object descriptor
# ---------------------------------------------------------------------------


@dataclass
class ManipulationObjectCfg:
    """Descriptor for a single object in a manipulation scene.

    Plain ``@dataclass`` (not ``@configclass``) so instances survive pickling
    and can appear inside a list field of a ``@configclass``.
    """

    name: str
    """Scene dict key used to look up this object in ``env.scene``."""

    usd_path: str
    """Path to the object USD file."""

    physics_type: str = "rigid"
    """Physics representation: ``'rigid'`` | ``'deformable'`` | ``'articulated'``."""

    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """Uniform scale applied to the USD mesh."""

    init_pos: tuple[float, float, float] = (0.45, 0.0, 0.055)
    """Default initial world position (x, y, z)."""

    init_rot: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    """Default initial quaternion (w, x, y, z)."""

    material_path: str | None = None
    """Optional physics material USD path."""

    role: str = "object"
    """Semantic role: ``'object'`` | ``'tool'`` | ``'container'`` | ``'surface'``."""

    pick_order: int = 0
    """Pick sequence index (0 = first).  Used by multi-object planners to determine
    which object to grasp next.  Must be unique across all objects in a preset."""

    spawn_range: dict[str, tuple[float, float]] | None = None
    """Per-axis XYZ offset ranges for episode reset, e.g.
    ``{'x': (-0.10, 0.10), 'y': (-0.20, 0.20), 'z': (0.0, 0.0)}``.
    ``None`` means no randomisation."""

    solver_position_iteration_count: int = 16
    solver_velocity_iteration_count: int = 1
    max_angular_velocity: float = 1000.0
    max_linear_velocity: float = 1000.0
    max_depenetration_velocity: float = 5.0
    disable_gravity: bool = False


# ---------------------------------------------------------------------------
# Per-goal descriptor
# ---------------------------------------------------------------------------


@dataclass
class ManipulationGoalCfg:
    """Descriptor for a single goal in a manipulation task.

    The ``type`` field determines which termination / reward function the
    IsaacLab HL env wires up.  All other fields are parameters forwarded to
    that function.
    """

    type: str = "place"
    """Task type: ``'place'`` | ``'pour'`` | ``'stack'`` | ``'insert'`` |
    ``'handover'`` | ``'open'`` | ``'close'`` | ``'push'``."""

    target_object: str = ""
    """Name of the object to act on (must match a ``ManipulationObjectCfg.name``)."""

    goal_object: str | None = None
    """Name of a receiving container / region object, if applicable."""

    goal_pos_default: tuple[float, float, float] | None = None
    """World-frame default goal position.  ``None`` = use the env cfg default."""

    goal_pose_range: dict[str, tuple[float, float]] | None = None
    """Per-axis XYZ offset ranges for goal pose randomisation.  ``None`` = use
    the env cfg default."""

    goal_yaw_range: tuple[float, float] = (-math.pi, math.pi)
    """Yaw randomisation range for goals that have an orientation component."""

    success_threshold_pos: float = 0.02
    """Maximum allowed XY distance to goal centre (m)."""

    success_threshold_ang: float = 0.10
    """Maximum allowed |roll| / |pitch| deviation (rad) for upright check."""

    success_threshold_yaw: float = 0.10
    """Maximum allowed symmetric yaw error vs goal orientation (rad)."""

    grip_open_threshold: float = 0.8
    """Minimum normalised gripper opening fraction at release."""

    success_dwell_s: float = 1.0
    """Seconds the success condition must hold before the episode is terminated."""


# ---------------------------------------------------------------------------
# Preset config
# ---------------------------------------------------------------------------


@configclass
class PresetManipulationEnvCfg(AbstractManipulationEnvCfg):
    """Scene-description config for preset manipulation environments.

    Holds the full physical description of the scene: objects (with heterogeneous
    physics types), goals (interpreted by the HL env), table, workspace, and
    lighting.  Task logic lives entirely in the IsaacLab HL env.

    Example preset file (saved as ``preset.py`` inside an envhub bundle)::

        from nepher.env_cfgs.manipulation.preset_mani_cfg import (
            ManipulationGoalCfg,
            ManipulationObjectCfg,
            PresetManipulationEnvCfg,
        )

        class FrankaLabV1Cfg(PresetManipulationEnvCfg):
            name = "franka-lab-v1"
            objects = [
                ManipulationObjectCfg(
                    name="cube",
                    usd_path="${ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd",
                    scale=(0.8, 0.8, 0.8),
                    init_pos=(0.45, 0.0, 0.055),
                    spawn_range={"x": (-0.10, 0.10), "y": (-0.20, 0.20), "z": (0.0, 0.0)},
                ),
            ]
            goals = [
                ManipulationGoalCfg(
                    type="place",
                    target_object="cube",
                    goal_pos_default=(0.55, 0.0, 0.055),
                    goal_pose_range={"x": (-0.10, 0.10), "y": (-0.20, 0.20), "z": (0.0, 0.0)},
                ),
            ]
    """

    name: str = "manipulation_preset"
    description: str = "Preset manipulation environment with explicit objects and goals"
    category: str = "manipulation"

    # ---- Objects & Goals ----

    objects: list[ManipulationObjectCfg] = field(default_factory=list)
    """Flat list of objects in the scene; heterogeneous physics types supported."""

    goals: list[ManipulationGoalCfg] = field(default_factory=list)
    """Goal descriptors.  The IsaacLab HL env interprets these to configure
    its termination / reward / event logic."""

    # ---- Table ----

    table_usd_path: str = ""
    """USD path for the table asset.  Empty string = keep the env cfg default."""

    table_init_pos: tuple[float, float, float] = (0.55, 0.0, 0.0)
    """Table initial position (x, y, z)."""

    table_init_rot: tuple[float, float, float, float] = (0.70711, 0.0, 0.0, 0.70711)
    """Table initial quaternion (w, x, y, z)."""

    # ---- Workspace ----

    workspace_bounds: tuple[float, float, float, float] = (-0.5, -0.5, 0.5, 0.5)
    """Scene bounds ``(x_min, y_min, x_max, y_max)`` in robot-base frame."""

    # ---- Lighting ----

    sky_light_intensity: float = 2500.0
    sky_color: tuple[float, float, float] = (0.75, 0.75, 0.75)
    sky_texture: str | None = None
    sky_visible: bool = True

    # ---- Layout ----

    env_spacing: float = 2.5
    max_episode_length_s: float = 10.0

    # ========== BaseEnvCfg implementations ==========

    def get_terrain_cfg(self) -> TerrainImporterCfg:
        """Return a flat ground plane terrain config."""
        return TerrainImporterCfg(
            prim_path="/World/ground",
            terrain_type="plane",
            collision_group=-1,
            physics_material=sim_utils.RigidBodyMaterialCfg(
                friction_combine_mode="multiply",
                restitution_combine_mode="multiply",
                static_friction=1.0,
                dynamic_friction=1.0,
                restitution=0.0,
            ),
            debug_vis=False,
        )

    def get_workspace_bounds(self) -> tuple[float, float, float, float]:
        return self.workspace_bounds

    def get_goals(self) -> list[ManipulationGoalCfg]:
        return self.goals

    # ========== Object CFGs (dispatched by physics_type) ==========

    def get_object_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Build IsaacLab asset cfgs for all objects in this preset.

        Dispatches on ``ManipulationObjectCfg.physics_type``:

        - ``'rigid'``       → ``RigidObjectCfg``
        - ``'articulated'`` → ``ArticulationCfg``
        - ``'deformable'``  → ``RigidObjectCfg`` with soft-body material note
          (full deformable support requires IsaacLab >= 2.x DeformableObjectCfg)
        """
        cfgs: dict[str, AssetBaseCfg] = {}
        for obj in self.objects:
            cfgs[obj.name] = self._build_object_cfg(obj)
        return cfgs

    def _build_object_cfg(self, obj: ManipulationObjectCfg) -> AssetBaseCfg:
        prim_path = f"{{ENV_REGEX_NS}}/{obj.name.capitalize()}"

        rigid_props = RigidBodyPropertiesCfg(
            solver_position_iteration_count=obj.solver_position_iteration_count,
            solver_velocity_iteration_count=obj.solver_velocity_iteration_count,
            max_angular_velocity=obj.max_angular_velocity,
            max_linear_velocity=obj.max_linear_velocity,
            max_depenetration_velocity=obj.max_depenetration_velocity,
            disable_gravity=obj.disable_gravity,
        )
        collision_props = CollisionPropertiesCfg(collision_enabled=True)
        # Zero restitution so objects settle without bouncing when dropped into
        # a container, matching real-world behaviour.  friction_combine_mode
        # "multiply" with 1.0 leaves the USD's own friction unchanged (1.0 × f
        # = f), so grasping is unaffected regardless of the asset's material.
        physics_material = sim_utils.RigidBodyMaterialCfg(
            static_friction=1.0,
            dynamic_friction=1.0,
            restitution=0.0,
            friction_combine_mode="multiply",
            restitution_combine_mode="min",
        )

        usd_kwargs: dict = dict(
            usd_path=obj.usd_path,
            scale=obj.scale,
            collision_props=collision_props,
            physics_material=physics_material,
        )

        if obj.physics_type in ("rigid", "deformable"):
            usd_kwargs["rigid_props"] = rigid_props
            spawn_cfg = sim_utils.UsdFileCfg(**usd_kwargs)
            return RigidObjectCfg(
                prim_path=prim_path,
                spawn=spawn_cfg,
                init_state=RigidObjectCfg.InitialStateCfg(
                    pos=obj.init_pos,
                    rot=obj.init_rot,
                ),
            )

        if obj.physics_type == "articulated":
            usd_kwargs.pop("rigid_props", None)
            spawn_cfg = sim_utils.UsdFileCfg(**usd_kwargs)
            return ArticulationCfg(
                prim_path=prim_path,
                spawn=spawn_cfg,
                init_state=ArticulationCfg.InitialStateCfg(
                    pos=obj.init_pos,
                    rot=obj.init_rot,
                ),
            )

        raise ValueError(
            f"Unsupported physics_type '{obj.physics_type}' for object '{obj.name}'. "
            "Expected 'rigid', 'deformable', or 'articulated'."
        )

    # ========== Table CFG ==========

    def get_table_cfg(self) -> AssetBaseCfg | None:
        """Return table asset config, or ``None`` if no override is set."""
        if not self.table_usd_path:
            return None
        return AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Table",
            spawn=sim_utils.UsdFileCfg(usd_path=self.table_usd_path),
            init_state=AssetBaseCfg.InitialStateCfg(
                pos=self.table_init_pos,
                rot=self.table_init_rot,
            ),
        )

    # ========== Lighting ==========

    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        return {
            "light": AssetBaseCfg(
                prim_path="/World/light",
                spawn=sim_utils.DomeLightCfg(
                    intensity=self.sky_light_intensity,
                    color=self.sky_color,
                    texture_file=self.sky_texture,
                    visible_in_primary_ray=self.sky_visible,
                ),
            ),
        }
