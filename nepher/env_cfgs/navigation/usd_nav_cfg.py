# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Base USD environment configuration for loading complete scenes from USD files.

This preset supports environments loaded entirely from USD files, where:
- The terrain, obstacles, and scene elements are defined in the USD file
- Spawn areas (free zones) are explicitly defined for safe robot/goal positioning
- Collision geometry comes from the USD file's collision meshes

Unlike PresetNavigationEnvCfg which manually defines obstacles, this preset
treats the USD file as a complete scene and focuses on defining navigation-relevant
areas within that scene.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import torch

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass

from nepher.env_cfgs.navigation.abstract_nav_cfg import AbstractNavigationEnvCfg
from nepher.utils.free_zone_finder import FreeZone, Rectangle
from nepher.utils.fast_spawn_sampler import FastSpawnSampler, OccupancyMapConfig


@dataclass
class SpawnAreaConfig:
    """Configuration for a spawn area (free zone) where robots/goals can be placed.
    
    Spawn areas define rectangular regions that are safe for robot and goal spawning.
    These should be placed in collision-free areas of the USD scene.
    """
    
    # Bounds in world coordinates (x_min, y_min, x_max, y_max)
    bounds: tuple[float, float, float, float] = (-1.0, -1.0, 1.0, 1.0)
    """Rectangular bounds (x_min, y_min, x_max, y_max) in world coordinates."""
    
    weight: float = 1.0
    """Relative weight for random selection. Higher weight = more likely to be selected."""
    
    allow_robot_spawn: bool = True
    """Whether robots can spawn in this area."""
    
    allow_goal_spawn: bool = True
    """Whether goals can spawn in this area."""
    
    name: str = ""
    """Optional name for this spawn area (e.g., 'room_1', 'hallway')."""
    
    @property
    def x_min(self) -> float:
        return self.bounds[0]
    
    @property
    def y_min(self) -> float:
        return self.bounds[1]
    
    @property
    def x_max(self) -> float:
        return self.bounds[2]
    
    @property
    def y_max(self) -> float:
        return self.bounds[3]
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)
    
    def to_rectangle(self) -> Rectangle:
        """Convert to Rectangle object for compatibility with free zone utilities."""
        return Rectangle(
            x_min=self.x_min,
            y_min=self.y_min,
            x_max=self.x_max,
            y_max=self.y_max,
        )


@dataclass
class ExclusionZoneConfig:
    """Configuration for an exclusion zone where robots/goals cannot be placed.
    
    Exclusion zones define rectangular regions that should be avoided for spawning,
    even if they fall within a spawn area. Useful for marking static obstacles,
    furniture, or other hazards within the USD scene.
    """
    
    # Bounds in world coordinates (x_min, y_min, x_max, y_max)
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    """Rectangular bounds (x_min, y_min, x_max, y_max) in world coordinates."""
    
    name: str = ""
    """Optional name for this exclusion zone (e.g., 'table_1', 'pillar')."""
    
    @property
    def x_min(self) -> float:
        return self.bounds[0]
    
    @property
    def y_min(self) -> float:
        return self.bounds[1]
    
    @property
    def x_max(self) -> float:
        return self.bounds[2]
    
    @property
    def y_max(self) -> float:
        return self.bounds[3]
    
    def to_rectangle(self) -> Rectangle:
        """Convert to Rectangle object for compatibility with free zone utilities."""
        return Rectangle(
            x_min=self.x_min,
            y_min=self.y_min,
            x_max=self.x_max,
            y_max=self.y_max,
        )
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside this exclusion zone."""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


@configclass
class UsdNavigationEnvCfg(AbstractNavigationEnvCfg):
    """Base configuration for USD-based navigation environments.
    
    This preset loads a complete environment from a USD file and provides
    mechanisms for defining spawn areas and exclusion zones for safe
    robot and goal positioning.
    
    The USD file should contain:
    - Terrain/ground geometry
    - Static obstacles and scene elements
    - Collision meshes for physics interaction
    
    Spawn areas and exclusion zones are defined separately to allow flexible
    configuration of navigation-safe regions within the scene.
    """
    
    # Preset identification
    name: str = "usd_env"
    description: str = "Base USD environment loaded from a scene file"
    category: str = "navigation"
    
    # ========== USD Scene Configuration ==========
    
    usd_path: str = ""
    """Path to the main USD file containing the environment scene."""
    
    usd_scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """Scale factor for the USD scene (x, y, z)."""
    
    usd_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    """Position offset for the USD scene (x, y, z)."""
    
    usd_rotation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    """Rotation quaternion for the USD scene (w, x, y, z)."""
    
    # ========== Terrain Configuration ==========
    
    terrain_type: str = "usd"
    """Type of terrain: 'usd' to load terrain from usd_path, 'plane' for flat ground."""
    
    terrain_friction: float = 1.0
    """Static and dynamic friction coefficient for terrain."""
    
    terrain_restitution: float = 0.0
    """Restitution coefficient for terrain collisions."""
    
    env_spacing: float = 50.0
    """Environment spacing for grid-like origins (meters). Should be large enough to contain the USD scene."""
    
    # ========== Spawn Area Configuration ==========
    
    spawn_areas: list[SpawnAreaConfig] = field(default_factory=list)
    """List of spawn area configurations. Defines where robots/goals can be placed."""
    
    exclusion_zones: list[ExclusionZoneConfig] = field(default_factory=list)
    """List of exclusion zone configurations. Defines areas to avoid for spawning."""
    
    # Playground bounds (x_min, y_min, x_max, y_max) in world coordinates
    # If None, playground is auto-computed from spawn areas
    playground: tuple[float, float, float, float] | None = None
    """Playground boundary (x_min, y_min, x_max, y_max). If None, auto-computed from spawn areas."""
    
    # Safety margins
    robot_safety_margin: float = 0.25
    """Additional safety margin around robot for position generation (meters)."""
    
    spawn_area_margin: float = 0.1
    """Margin to shrink spawn areas by for safety (meters)."""
    
    # Robot initial position/yaw ranges (used as fallback when no spawn areas defined)
    robot_init_pos_x_range: tuple[float, float] = (-1.0, 1.0)
    """Range for robot initial x position. Used as fallback."""
    
    robot_init_pos_y_range: tuple[float, float] = (-1.0, 1.0)
    """Range for robot initial y position. Used as fallback."""
    
    robot_init_yaw_range: tuple[float, float] = (-math.pi, math.pi)
    """Range for robot initial yaw angle in radians."""
    
    # ========== Fast Spawn Sampler Configuration ==========
    
    occupancy_map_yaml: str | None = None
    """Path to occupancy map YAML file for fast collision-free sampling."""
    
    spawn_grid_resolution: float = 0.1
    """Grid resolution (meters) for pre-computing valid spawn positions."""
    
    min_robot_goal_distance: float = 1.0
    """Minimum distance between robot spawn and goal positions."""
    
    # ========== Lighting & Background Configuration ==========
    
    use_usd_lighting: bool = True
    """Whether to use lighting defined in the USD file. If False, uses custom lighting."""
    
    sky_light_intensity: float = 750.0
    """Intensity of the dome/sky light (used when use_usd_lighting=False)."""
    
    sky_texture: str | None = None
    """Path to HDRI texture for sky background. If None, uses uniform color."""
    
    sky_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """RGB color for sky light (used when sky_texture is None)."""
    
    sky_visible: bool = True
    """Whether the sky is visible. If False, sky appears black (indoor scenes)."""
    
    # ========== Abstract Method Implementations ==========
    
    def get_terrain_cfg(self) -> TerrainImporterCfg:
        """Generate terrain configuration.
        
        If terrain_type is 'usd', uses the usd_path as terrain.
        Otherwise, creates a flat plane terrain.
        """
        if self.terrain_type == "usd" and self.usd_path:
            return TerrainImporterCfg(
                prim_path="/World/ground",
                terrain_type="usd",
                terrain_generator=None,
                usd_path=self.usd_path,
                env_spacing=self.env_spacing,
                max_init_terrain_level=None,
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
        else:
            return TerrainImporterCfg(
                prim_path="/World/ground",
                terrain_type="plane",
                terrain_generator=None,
                usd_path=None,
                env_spacing=self.env_spacing,
                max_init_terrain_level=None,
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
    
    def get_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Generate obstacle asset configurations.
        
        For USD environments, obstacles are typically included in the USD file.
        This method returns an empty dict by default. Override if you need
        to add additional obstacles programmatically.
        
        Returns:
            Empty dictionary (obstacles are in the USD file).
        """
        return {}
    
    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Generate light asset configurations.
        
        If use_usd_lighting is True, returns empty dict (lighting from USD).
        Otherwise, returns a dome/sky light configuration.
        
        Returns:
            Dictionary with sky_light configuration, or empty if using USD lighting.
        """
        if self.use_usd_lighting:
            return {}
        
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
    
    # ========== Fast Sampler (lazy initialized) ==========
    _spawn_sampler: FastSpawnSampler | None = None
    
    def _get_spawn_sampler(self, device: str | torch.device = "cpu") -> FastSpawnSampler:
        """Get or create the fast spawn sampler (lazy init)."""
        if self._spawn_sampler is not None:
            return self._spawn_sampler
        
        # Build occupancy map config if yaml path provided
        omap_cfg = None
        if self.occupancy_map_yaml:
            omap_cfg = OccupancyMapConfig(
                yaml_path=self.occupancy_map_yaml,
                safety_margin=self.robot_safety_margin,
            )
        
        # Build spawn bounds from spawn areas or fallback ranges
        spawn_bounds = None
        if self.spawn_areas:
            x_min = min(a.x_min for a in self.spawn_areas)
            y_min = min(a.y_min for a in self.spawn_areas)
            x_max = max(a.x_max for a in self.spawn_areas)
            y_max = max(a.y_max for a in self.spawn_areas)
            spawn_bounds = (x_min, y_min, x_max, y_max)
        else:
            spawn_bounds = (
                self.robot_init_pos_x_range[0],
                self.robot_init_pos_y_range[0],
                self.robot_init_pos_x_range[1],
                self.robot_init_pos_y_range[1],
            )
        
        # Build exclusion zones list
        exclusions = [(z.x_min, z.y_min, z.x_max, z.y_max) for z in self.exclusion_zones]
        
        self._spawn_sampler = FastSpawnSampler(
            device=device,
            omap_config=omap_cfg,
            spawn_bounds=spawn_bounds,
            exclusion_rects=exclusions,
            grid_resolution=self.spawn_grid_resolution,
            safety_margin=self.robot_safety_margin,
        )
        return self._spawn_sampler
    
    def gen_goal_random_pos(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> torch.Tensor:
        """Generate goal positions - O(1) per sample using pre-computed valid cells.
        
        Args:
            env_ids: Tensor of environment indices to generate goals for.
            env_origins: Tensor of shape (num_envs, 3) containing environment origins.
            device: Device to create tensors on.
            **kwargs: robot_positions (Tensor) - if provided, ensures min distance.
            
        Returns:
            Tensor of shape (len(env_ids), 3) containing goal positions (x, y, z).
        """
        n = len(env_ids)
        sampler = self._get_spawn_sampler(device)
        
        robot_positions = kwargs.get("robot_positions")
        if robot_positions is not None and self.min_robot_goal_distance > 0:
            xy = sampler.sample_with_min_distance(
                n, 
                existing_positions=robot_positions[:, :2],
                min_distance=self.min_robot_goal_distance,
            )
        else:
            xy = sampler.sample(n)
        
        # Build (x, y, 0) positions relative to env origins
        goal_pos = torch.zeros((n, 3), device=device)
        goal_pos[:, :2] = xy + env_origins[env_ids, :2]
        return goal_pos
    
    def gen_bot_random_pos(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Generate robot positions - O(1) per sample using pre-computed valid cells.
        
        Args:
            env_ids: Tensor of environment indices to generate positions for.
            env_origins: Tensor of shape (num_envs, 3) containing environment origins.
            device: Device to create tensors on.
            **kwargs: Unused.
            
        Returns:
            Tuple of (positions, yaws):
            - positions: Tensor of shape (len(env_ids), 3) containing (x, y, z).
            - yaws: Tensor of shape (len(env_ids),) containing yaw angles.
        """
        n = len(env_ids)
        sampler = self._get_spawn_sampler(device)
        
        xy = sampler.sample(n)
        
        # Build positions relative to env origins
        positions = torch.zeros((n, 3), device=device)
        positions[:, :2] = xy + env_origins[env_ids, :2]
        
        # Random yaw
        yaw_min, yaw_max = self.robot_init_yaw_range
        yaws = torch.rand(n, device=device) * (yaw_max - yaw_min) + yaw_min
        
        return positions, yaws
    
    def validate_positions(
        self,
        positions: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        robot_radius: float | None = None,
        **kwargs,
    ) -> torch.Tensor:
        """Validate positions against pre-computed valid cells - O(N) batch check.
        
        Args:
            positions: Tensor of shape (N, 2) or (N, 3) with positions (x, y) or (x, y, z).
            env_origins: Tensor of shape (num_envs, 3) containing environment origins.
            device: Device to create tensors on.
            robot_radius: Unused (safety margin is baked into sampler).
            **kwargs: env_ids (Tensor) - if provided, subtracts corresponding origins.
            
        Returns:
            Boolean tensor of shape (N,) - True if position is valid/safe.
        """
        sampler = self._get_spawn_sampler(device)
        
        # Extract xy only
        xy = positions[:, :2] if positions.shape[1] >= 2 else positions
        
        # Subtract env origins if env_ids provided
        env_ids = kwargs.get("env_ids")
        if env_ids is not None:
            xy = xy - env_origins[env_ids, :2]
        
        return sampler.validate(xy.to(device))
    
    # ========== Helper Methods ==========
    
    def _get_playground(self) -> Rectangle | None:
        """Get playground bounds as a Rectangle.
        
        If playground is not configured, computes bounds from spawn areas.
        
        Returns:
            Rectangle if playground is configured or can be computed, None otherwise.
        """
        if self.playground is not None:
            return Rectangle(
                x_min=self.playground[0],
                y_min=self.playground[1],
                x_max=self.playground[2],
                y_max=self.playground[3],
            )
        
        # Compute from spawn areas
        if not self.spawn_areas:
            return None
        
        x_min = min(area.x_min for area in self.spawn_areas)
        y_min = min(area.y_min for area in self.spawn_areas)
        x_max = max(area.x_max for area in self.spawn_areas)
        y_max = max(area.y_max for area in self.spawn_areas)
        
        return Rectangle(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
    
    def _sample_position_from_areas(
        self,
        areas: list[SpawnAreaConfig],
        device: str | torch.device = "cpu",
        safety_margin: float = 0.0,
        max_attempts: int = 100,
    ) -> tuple[float, float]:
        """Sample a random position from the given spawn areas.
        
        Uses weighted random selection based on area size and weight.
        Avoids exclusion zones.
        
        Args:
            areas: List of spawn areas to sample from.
            device: Device for tensor operations.
            safety_margin: Additional margin to shrink spawn areas by.
            max_attempts: Maximum number of attempts to find valid position.
            
        Returns:
            Tuple of (x, y) position.
        """
        if not areas:
            return (0.0, 0.0)
        
        # Compute weighted areas for selection
        weighted_areas = torch.tensor(
            [area.area * area.weight for area in areas], 
            device=device
        )
        area_probs = weighted_areas / weighted_areas.sum()
        
        for _ in range(max_attempts):
            # Select area based on weighted probability
            area_idx: int = int(torch.multinomial(area_probs, 1).item())
            area = areas[area_idx]
            
            # Get area bounds with safety margin
            margin = self.spawn_area_margin + safety_margin
            x_min = area.x_min + margin
            x_max = area.x_max - margin
            y_min = area.y_min + margin
            y_max = area.y_max - margin
            
            # Ensure valid bounds
            if x_max <= x_min:
                x_min = area.x_min
                x_max = area.x_max
            if y_max <= y_min:
                y_min = area.y_min
                y_max = area.y_max
            
            # Sample random position
            x = torch.rand(1, device=device).item() * (x_max - x_min) + x_min
            y = torch.rand(1, device=device).item() * (y_max - y_min) + y_min
            
            # Check exclusion zones
            in_exclusion = False
            for zone in self.exclusion_zones:
                if zone.contains_point(x, y):
                    in_exclusion = True
                    break
            
            if not in_exclusion:
                return (x, y)
        
        # Fallback: return center of first area
        return areas[0].center
    
    def get_spawn_areas_as_free_zones(self) -> list[FreeZone]:
        """Convert spawn areas to FreeZone objects for compatibility.
        
        Useful for integration with existing free zone-based algorithms.
        
        Returns:
            List of FreeZone objects corresponding to spawn areas.
        """
        free_zones = []
        for area in self.spawn_areas:
            if area.allow_robot_spawn or area.allow_goal_spawn:
                free_zones.append(FreeZone(
                    x1=area.x_min + self.spawn_area_margin,
                    y1=area.y_min + self.spawn_area_margin,
                    x2=area.x_max - self.spawn_area_margin,
                    y2=area.y_max - self.spawn_area_margin,
                ))
        return free_zones
    
    def get_exclusion_zones_as_rectangles(self) -> list[Rectangle]:
        """Convert exclusion zones to Rectangle objects.
        
        Useful for integration with obstacle avoidance algorithms.
        
        Returns:
            List of Rectangle objects corresponding to exclusion zones.
        """
        return [zone.to_rectangle() for zone in self.exclusion_zones]
    
    def get_scene_asset_cfg(self) -> AssetBaseCfg | None:
        """Get asset configuration for the USD scene.
        
        Returns an AssetBaseCfg for loading the USD scene as a static asset,
        separate from the terrain. Useful when you need the scene as an asset
        rather than terrain.
        
        Returns:
            AssetBaseCfg for the USD scene, or None if usd_path is not set.
        """
        if not self.usd_path:
            return None
        
        return AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Scene",
            spawn=sim_utils.UsdFileCfg(
                usd_path=self.usd_path,
                scale=self.usd_scale,
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    rigid_body_enabled=True,
                    kinematic_enabled=True,
                ),
                collision_props=sim_utils.CollisionPropertiesCfg(
                    collision_enabled=True,
                ),
            ),
            init_state=AssetBaseCfg.InitialStateCfg(
                pos=self.usd_position,
                rot=self.usd_rotation,
            ),
        )

# Alias for backward compatibility
UsdEnvironmentCfg = UsdNavigationEnvCfg

