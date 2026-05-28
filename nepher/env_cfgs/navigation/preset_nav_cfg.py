# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Preset environment configuration with manually defined obstacles.

This preset describes a scene — terrain, obstacles, and lighting.
Position generation is delegated to a ``PositionStrategy`` set by the
concrete environment bundle (or a subclass ``__post_init__``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.terrains import TerrainGeneratorCfg, TerrainImporterCfg
from isaaclab.utils import configclass

from nepher.env_cfgs.navigation.abstract_nav_cfg import AbstractNavigationEnvCfg


@dataclass
class ObstacleConfig:
    """Configuration for a single obstacle.

    Obstacles can be cuboid primitives (``usd_path is None``) or USD assets.
    They can be static (default) or dynamic with optional path-based movement.
    """

    position: tuple[float, float, float] = (2.0, 0.0, 0.25)
    """World position of the obstacle center (x, y, z)."""

    size: tuple[float, float, float] = (0.5, 0.5, 0.5)
    """Cuboid size (w, d, h). Used when ``usd_path is None``."""

    color: tuple[float, float, float] = (0.8, 0.2, 0.2)
    """RGB colour for cuboid obstacle."""

    usd_path: str | None = None
    """Path to USD file. If ``None``, a cuboid primitive is used."""

    usd_scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """Scale factor for USD asset."""

    is_dynamic: bool = False
    """Dynamic obstacles have ``kinematic_enabled=False``."""

    include_in_static_layout: bool = True
    """Include in static layout queries. Set ``False`` for fully-dynamic obstacles."""

    path_waypoints: list[tuple[float, float]] | None = None
    """(x, y) waypoints for dynamic obstacle movement."""

    movement_speed: float = 0.5
    """Movement speed along path (m/s)."""

    path_loop: bool = True
    """Loop (``True``) or ping-pong (``False``) along path."""

    initial_path_progress: float = 0.0
    """Initial progress along path (0–1)."""


@configclass
class PresetNavigationEnvCfg(AbstractNavigationEnvCfg):
    """Scene-description config for preset environments with explicit obstacles.

    Position generation is **not** handled here — environments must assign a
    ``position_strategy`` (or override ``gen_bot_pos`` / ``gen_goal_pos``).
    """

    name: str = "obstacle_preset"
    description: str = "Base environment preset with manually defined obstacles"
    category: str = "navigation"

    # ========== Terrain ==========

    terrain_type: str = "plane"
    """``'plane'`` | ``'generator'`` | ``'usd'``."""

    terrain_friction: float = 1.0
    terrain_restitution: float = 0.0

    terrain_usd_path: str | None = None
    """USD terrain mesh (used when ``terrain_type='usd'``)."""

    terrain_generator: TerrainGeneratorCfg | None = None
    """Procedural generator config (used when ``terrain_type='generator'``)."""

    terrain_max_init_level: int | None = None
    terrain_visual_material: sim_utils.VisualMaterialCfg | None = None

    env_spacing: float = 20.0

    # ========== Obstacles ==========

    obstacles: list[ObstacleConfig] = field(default_factory=list)
    """Explicit obstacle list (cuboids and/or USD assets)."""

    playground: tuple[float, float, float, float] | None = None
    """Scene bounds ``(x_min, y_min, x_max, y_max)``. ``None`` = unset."""

    # ========== Lighting ==========

    sky_light_intensity: float = 750.0
    sky_texture: str | None = None
    sky_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    sky_visible: bool = True

    # ========== Scene Config Implementations ==========

    def get_terrain_cfg(self) -> TerrainImporterCfg:
        cfg = TerrainImporterCfg(
            prim_path="/World/ground",
            terrain_type=self.terrain_type,
            terrain_generator=self.terrain_generator,
            usd_path=self.terrain_usd_path,
            env_spacing=self.env_spacing,
            max_init_terrain_level=self.terrain_max_init_level,
            collision_group=-1,
            physics_material=sim_utils.RigidBodyMaterialCfg(
                friction_combine_mode="multiply",
                restitution_combine_mode="multiply",
                static_friction=self.terrain_friction,
                dynamic_friction=self.terrain_friction,
                restitution=self.terrain_restitution,
            ),
            debug_vis=False,
        )
        if self.terrain_visual_material is not None:
            cfg.visual_material = self.terrain_visual_material
        return cfg

    def get_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        obstacle_cfgs: dict[str, AssetBaseCfg] = {}
        collision_props = sim_utils.CollisionPropertiesCfg(collision_enabled=True)

        for i, obs in enumerate(self.obstacles):
            name = f"obstacle_{i + 1}"
            rigid_props = sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                kinematic_enabled=not obs.is_dynamic,
            )
            if obs.usd_path is not None:
                spawn_cfg = sim_utils.UsdFileCfg(
                    usd_path=obs.usd_path,
                    scale=obs.usd_scale,
                    rigid_props=rigid_props,
                    collision_props=collision_props,
                )
            else:
                spawn_cfg = sim_utils.CuboidCfg(
                    size=obs.size,
                    rigid_props=rigid_props,
                    collision_props=collision_props,
                    visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=obs.color),
                )
            obstacle_cfgs[name] = AssetBaseCfg(
                prim_path="{ENV_REGEX_NS}/" + name.capitalize().replace("_", ""),
                spawn=spawn_cfg,
                init_state=AssetBaseCfg.InitialStateCfg(pos=obs.position),
            )
        return obstacle_cfgs

    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        return {
            "sky_light": AssetBaseCfg(
                prim_path="/World/skyLight",
                spawn=sim_utils.DomeLightCfg(
                    intensity=self.sky_light_intensity,
                    color=self.sky_color,
                    texture_file=self.sky_texture,
                    visible_in_primary_ray=self.sky_visible,
                ),
            ),
        }

    # ========== Helpers ==========

    def _get_playground(self) -> tuple[float, float, float, float] | None:
        """Return playground bounds tuple, or ``None`` if unset."""
        return self.playground
