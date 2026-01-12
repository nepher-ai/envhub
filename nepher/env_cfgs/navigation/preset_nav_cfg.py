# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Base environment preset configuration with manually defined obstacles.

This preset supports environments with obstacles defined either as:
- Geometric primitives (cuboids) with configurable size, position, and color
- USD file assets with configurable position and scale

The preset uses free zone computation to ensure safe robot and goal positioning
in obstacle-free areas.
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
from nepher.utils.free_zone_finder import FreeZone, Rectangle, find_free_zones


@dataclass
class ObstacleConfig:
    """Configuration for a single obstacle.
    
    Obstacles can be defined as either:
    - A cuboid primitive with size and color (when usd_path is None)
    - A USD file asset (when usd_path is provided)
    
    Obstacles can be static (default) or dynamic. Dynamic obstacles can be moved
    programmatically during simulation and respond to physics forces.
    """
    
    # Position in world coordinates (x, y, z)
    position: tuple[float, float, float] = (2.0, 0.0, 0.25)
    """World position of the obstacle center (x, y, z)."""
    
    # Cuboid configuration (used when usd_path is None)
    size: tuple[float, float, float] = (0.5, 0.5, 0.5)
    """Size of cuboid obstacle (width, depth, height). Used when usd_path is None."""
    
    color: tuple[float, float, float] = (0.8, 0.2, 0.2)
    """RGB color for cuboid obstacle. Used when usd_path is None."""
    
    # USD asset configuration (used when usd_path is provided)
    usd_path: str | None = None
    """Path to USD file for obstacle asset. If None, uses cuboid primitive."""
    
    usd_scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """Scale factor for USD asset (x, y, z). Used when usd_path is provided."""
    
    # Dynamic obstacle configuration
    is_dynamic: bool = False
    """Whether this obstacle is dynamic (can move). If True, kinematic_enabled=False."""
    
    include_in_static_layout: bool = True
    """Whether to include this obstacle in static layout calculations (free zones, collision checking).
    Set to False for fully dynamic obstacles that move unpredictably. Default True includes
    the obstacle at its initial position for planning purposes."""
    
    # Path-based movement configuration (for dynamic obstacles)
    path_waypoints: list[tuple[float, float]] | None = None
    """List of (x, y) waypoints defining the path for dynamic obstacles. 
    If None and is_dynamic=True, obstacle stays at initial position."""
    
    movement_speed: float = 0.5
    """Movement speed along path in m/s. Only used if path_waypoints is provided."""
    
    path_loop: bool = True
    """If True, obstacle loops back to start after reaching end. If False, reverses direction (ping-pong)."""
    
    initial_path_progress: float = 0.0
    """Initial progress along path (0.0 = start, 1.0 = end). Used for randomization/staggering."""


@configclass
class PresetNavigationEnvCfg(AbstractNavigationEnvCfg):
    """Base configuration for environment presets with manually defined obstacles.
    
    This preset is designed for environments where obstacles are explicitly defined
    in the configuration. It supports both geometric primitives (cuboids) and USD
    file assets as obstacles.
    
    The preset automatically computes free zones from obstacles and uses them for
    safe robot and goal positioning. It validates positions to ensure they don't
    overlap with obstacles or go out of playground bounds.
    
    Performance: Free zones are cached after first computation to avoid expensive
    recomputation on every reset. Position sampling is vectorized for batch efficiency.
    """
    
    # Preset identification
    name: str = "obstacle_preset"
    description: str = "Base environment preset with manually defined obstacles"
    category: str = "navigation"
    
    # ========== Cached Data (computed lazily, not serialized) ==========
    # These are runtime caches, not configuration fields
    _cached_free_zones: list[FreeZone] | None = None
    _cached_zone_bounds: torch.Tensor | None = None  # Shape: (num_zones, 4) for x_min, y_min, x_max, y_max
    _cached_zone_probs: torch.Tensor | None = None   # Shape: (num_zones,) for area-weighted sampling
    
    # Terrain configuration
    terrain_type: str = "plane"
    """Type of terrain: 'plane' for flat terrain, 'generator' for generated terrain."""
    
    terrain_friction: float = 1.0
    """Static and dynamic friction coefficient for terrain."""
    
    terrain_restitution: float = 0.0
    """Restitution coefficient for terrain collisions."""
    
    terrain_usd_path: str | None = None
    """Path to USD file for terrain mesh. If None, uses terrain_type."""
    
    env_spacing: float = 20.0
    """Environment spacing for grid-like origins (meters). Used for multi-environment layouts."""
    
    # Obstacles configuration
    obstacles: list[ObstacleConfig] = field(default_factory=list)
    """List of obstacle configurations. Can include cuboids and USD assets."""
    
    # Playground bounds (x_min, y_min, x_max, y_max) in world coordinates
    # If None, playground is auto-computed from obstacles with margin
    playground: tuple[float, float, float, float] | None = None
    """Playground boundary (x_min, y_min, x_max, y_max). If None, auto-computed."""
    
    # Free zone computation parameters
    playground_margin: float = 2.0
    """Margin for auto-computed playground (meters). Used when playground is None."""
    
    min_zone_size: float = 0.7
    """Minimum dimension (width and height) of a free zone (meters)."""
    
    max_zones: int | None = None
    """Maximum number of free zones to compute. If None, no limit."""
    
    clearance: float = 0.05
    """Clearance margin to shrink free zones by for safety (meters)."""
    
    robot_safety_margin: float = 0.25
    """Additional safety margin around robot for position generation (meters)."""
    
    # Robot initial position ranges (used as fallback when free zones unavailable)
    robot_init_pos_x_range: tuple[float, float] = (-0.5, 0.5)
    """Range for robot initial x position. Used as fallback."""
    
    robot_init_pos_y_range: tuple[float, float] = (-0.5, 0.5)
    """Range for robot initial y position. Used as fallback."""
    
    robot_init_yaw_range: tuple[float, float] = (-math.pi, math.pi)
    """Range for robot initial yaw angle in radians."""
    
    # ========== Lighting & Background Configuration ==========
    
    sky_light_intensity: float = 750.0
    """Intensity of the dome/sky light."""
    
    sky_texture: str | None = None
    """Path to HDRI texture for sky background. If None, uses uniform white color."""
    
    sky_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    """RGB color for sky light (used when sky_texture is None)."""
    
    sky_visible: bool = True
    """Whether the sky is visible. If False, sky appears black (indoor scenes)."""
    
    # ========== Abstract Method Implementations ==========
    
    def get_terrain_cfg(self) -> TerrainImporterCfg:
        """Generate terrain configuration."""
        return TerrainImporterCfg(
            prim_path="/World/ground",
            terrain_type=self.terrain_type,
            terrain_generator=None,
            usd_path=self.terrain_usd_path,
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
        
        Converts ObstacleConfig entries into AssetBaseCfg objects suitable for
        spawning in the simulation. Supports both cuboid primitives and USD assets.
        
        Returns:
            Dictionary mapping obstacle names to their asset configurations.
        """
        obstacle_cfgs = {}
        collision_props = sim_utils.CollisionPropertiesCfg(collision_enabled=True)
        
        for i, obs in enumerate(self.obstacles):
            name = f"obstacle_{i + 1}"
            # Configure rigid body properties based on whether obstacle is dynamic
            rigid_props = sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                kinematic_enabled=not obs.is_dynamic  # Dynamic obstacles are not kinematic
            )
            
            if obs.usd_path is not None:
                # Use USD asset
                spawn_cfg = sim_utils.UsdFileCfg(
                    usd_path=obs.usd_path,
                    scale=obs.usd_scale,
                    rigid_props=rigid_props,
                    collision_props=collision_props,
                )
            else:
                # Use cuboid primitive
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
        """Generate light asset configurations (dome/sky light).
        
        Returns:
            Dictionary with sky_light configuration.
        """
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
    
    def gen_goal_random_pos(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> torch.Tensor:
        """Generate goal positions inside free zones (vectorized, cached).
        
        This method uses cached free zones and vectorized sampling for high performance.
        Goals are guaranteed to be in obstacle-free areas safe for navigation.
        
        Args:
            env_ids: Tensor of environment indices to generate goals for.
            env_origins: Tensor of shape (num_envs, 3) containing environment origins.
            device: Device to create tensors on.
            **kwargs: Additional keyword arguments (unused, for interface compatibility).
            
        Returns:
            Tensor of shape (len(env_ids), 3) containing goal positions (x, y, z).
            Z-coordinate is set to goal_z_offset from the abstract base.
        """
        num_goals = len(env_ids)
        goal_pos = torch.zeros((num_goals, 3), device=device)
        
        # Get cached zone data (computed once, reused)
        zone_bounds, zone_probs = self._get_zone_sampling_data(device)
        
        if zone_bounds is None:
            # Fallback: use playground bounds if no free zones found
            playground = self._get_playground()
            if playground is None:
                x_min, y_min, x_max, y_max = -2.0, -2.0, 2.0, 2.0
            else:
                x_min, y_min = playground.x_min, playground.y_min
                x_max, y_max = playground.x_max, playground.y_max
            
            # Vectorized sampling from playground
            goal_pos[:, 0] = torch.rand(num_goals, device=device) * (x_max - x_min) + x_min
            goal_pos[:, 1] = torch.rand(num_goals, device=device) * (y_max - y_min) + y_min
        else:
            # Vectorized zone selection (all environments at once)
            assert zone_probs is not None  # Both are always set together
            zone_indices = torch.multinomial(zone_probs, num_goals, replacement=True)
            
            # Get bounds for selected zones: (num_goals, 4)
            selected_bounds = zone_bounds[zone_indices]
            
            # Vectorized random sampling within selected zone bounds
            rand_xy = torch.rand((num_goals, 2), device=device)
            goal_pos[:, 0] = rand_xy[:, 0] * (selected_bounds[:, 2] - selected_bounds[:, 0]) + selected_bounds[:, 0]
            goal_pos[:, 1] = rand_xy[:, 1] * (selected_bounds[:, 3] - selected_bounds[:, 1]) + selected_bounds[:, 1]
        
        # Set z-coordinate to goal offset
        goal_pos[:, 2] = self.goal_z_offset
        
        # Add environment origins
        goal_pos[:, :2] += env_origins[env_ids, :2]
        return goal_pos
    
    def gen_bot_random_pos(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Generate robot initial positions and yaws inside free zones (vectorized, cached).
        
        This method uses cached free zones and vectorized sampling for high performance.
        Positions are guaranteed to be in obstacle-free areas safe for robot spawning.
        
        Args:
            env_ids: Tensor of environment indices to generate positions for.
            env_origins: Tensor of shape (num_envs, 3) containing environment origins.
            device: Device to create tensors on.
            **kwargs: Additional keyword arguments (unused, for interface compatibility).
            
        Returns:
            Tuple of (positions, yaws):
            - positions: Tensor of shape (len(env_ids), 3) containing (x, y, z).
            - yaws: Tensor of shape (len(env_ids),) containing yaw angles.
        """
        num_positions = len(env_ids)
        positions = torch.zeros((num_positions, 3), device=device)
        
        # Get cached zone data (computed once, reused)
        zone_bounds, zone_probs = self._get_zone_sampling_data(device)
        
        # Vectorized yaw sampling (always needed)
        yaw_range = self.robot_init_yaw_range[1] - self.robot_init_yaw_range[0]
        yaws = torch.rand(num_positions, device=device) * yaw_range + self.robot_init_yaw_range[0]
        
        if zone_bounds is None:
            # Fallback: vectorized sampling from configured ranges
            x_range = self.robot_init_pos_x_range[1] - self.robot_init_pos_x_range[0]
            y_range = self.robot_init_pos_y_range[1] - self.robot_init_pos_y_range[0]
            positions[:, 0] = torch.rand(num_positions, device=device) * x_range + self.robot_init_pos_x_range[0]
            positions[:, 1] = torch.rand(num_positions, device=device) * y_range + self.robot_init_pos_y_range[0]
        else:
            # Vectorized zone selection (all environments at once)
            assert zone_probs is not None  # Both are always set together
            zone_indices = torch.multinomial(zone_probs, num_positions, replacement=True)
            
            # Get bounds for selected zones: (num_positions, 4)
            selected_bounds = zone_bounds[zone_indices]
            
            # Vectorized random sampling within selected zone bounds
            rand_xy = torch.rand((num_positions, 2), device=device)
            positions[:, 0] = rand_xy[:, 0] * (selected_bounds[:, 2] - selected_bounds[:, 0]) + selected_bounds[:, 0]
            positions[:, 1] = rand_xy[:, 1] * (selected_bounds[:, 3] - selected_bounds[:, 1]) + selected_bounds[:, 1]
        
        # Add environment origins
        positions[:, :2] += env_origins[env_ids, :2]
        return positions, yaws
    
    def validate_positions(
        self,
        positions: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        robot_radius: float | None = None,
        **kwargs,
    ) -> torch.Tensor:
        """Validate that positions are safe (not in obstacles, within bounds).
        
        Checks if positions are:
        1. Within playground bounds (if playground is configured)
        2. Not overlapping with any obstacles (with robot radius clearance)
        
        Args:
            positions: Tensor of shape (N, 2) or (N, 3) with positions (x, y) or (x, y, z).
            env_origins: Tensor of shape (num_envs, 3) containing environment origins.
            device: Device to create tensors on.
            robot_radius: Safety radius around robot for collision checking. 
                         If None, uses self.robot_radius.
            **kwargs: Additional keyword arguments (unused, for interface compatibility).
            
        Returns:
            Boolean tensor of shape (N,) indicating which positions are valid.
            True means position is valid/safe, False means invalid/unsafe.
        """
        if robot_radius is None:
            robot_radius = self.robot_radius
        
        # Extract 2D positions (x, y only)
        if positions.shape[1] == 3:
            pos_2d = positions[:, :2]
        else:
            pos_2d = positions
        
        num_positions = pos_2d.shape[0]
        valid = torch.ones(num_positions, dtype=torch.bool, device=device)
        
        # Get obstacle layout with robot radius clearance
        obstacle_boxes = self._get_obstacle_layout(clearance=robot_radius)
        playground = self._get_playground()
        
        # Check each position
        for i in range(num_positions):
            x, y = pos_2d[i, 0].item(), pos_2d[i, 1].item()
            
            # Check playground bounds
            if playground is not None:
                if (x < playground.x_min or x > playground.x_max or
                    y < playground.y_min or y > playground.y_max):
                    valid[i] = False
                    continue
            
            # Check obstacle collisions
            for obs_box in obstacle_boxes:
                if (obs_box.x_min <= x <= obs_box.x_max and
                    obs_box.y_min <= y <= obs_box.y_max):
                    valid[i] = False
                    break
        
        return valid
    
    # ========== Helper Methods ==========
    
    def _get_zone_sampling_data(
        self, device: str | torch.device = "cpu"
    ) -> tuple[torch.Tensor | None, torch.Tensor | None]:
        """Get cached zone bounds and probabilities for vectorized sampling.
        
        Computes free zones once and caches the results. Returns pre-computed
        tensors optimized for batch position sampling.
        
        Args:
            device: Device to create/move tensors to.
            
        Returns:
            Tuple of (zone_bounds, zone_probs):
            - zone_bounds: Tensor of shape (num_zones, 4) with [x_min, y_min, x_max, y_max]
                          per zone (with safety margin applied). None if no zones.
            - zone_probs: Tensor of shape (num_zones,) with area-weighted probabilities.
                         None if no zones.
        """
        # Compute free zones if not cached
        if self._cached_free_zones is None:
            self._cached_free_zones, _, _ = self._compute_free_zones()
        
        free_zones = self._cached_free_zones
        if not free_zones:
            return None, None
        
        # Compute zone bounds tensor if not cached (or move to correct device)
        if self._cached_zone_bounds is None or self._cached_zone_bounds.device != torch.device(device):
            num_zones = len(free_zones)
            zone_bounds = torch.zeros((num_zones, 4), device=device)
            zone_areas = torch.zeros(num_zones, device=device)
            
            for i, zone in enumerate(free_zones):
                # Get zone bounds with safety margin
                x_min = min(zone.x1, zone.x2) + self.robot_safety_margin
                x_max = max(zone.x1, zone.x2) - self.robot_safety_margin
                y_min = min(zone.y1, zone.y2) + self.robot_safety_margin
                y_max = max(zone.y1, zone.y2) - self.robot_safety_margin
                
                # Ensure valid bounds (fall back to original if margin makes it invalid)
                if x_max <= x_min:
                    x_min, x_max = min(zone.x1, zone.x2), max(zone.x1, zone.x2)
                if y_max <= y_min:
                    y_min, y_max = min(zone.y1, zone.y2), max(zone.y1, zone.y2)
                
                zone_bounds[i] = torch.tensor([x_min, y_min, x_max, y_max], device=device)
                zone_areas[i] = zone.area
            
            # Compute area-weighted probabilities
            zone_probs = zone_areas / zone_areas.sum()
            
            self._cached_zone_bounds = zone_bounds
            self._cached_zone_probs = zone_probs
        
        return self._cached_zone_bounds, self._cached_zone_probs
    
    def clear_zone_cache(self) -> None:
        """Clear cached free zone data.
        
        Call this if obstacles are modified after initialization to force
        recomputation of free zones on next position generation.
        """
        self._cached_free_zones = None
        self._cached_zone_bounds = None
        self._cached_zone_probs = None
    
    def _get_obstacle_layout(self, clearance: float = 0.0) -> list[Rectangle]:
        """Generate bounding boxes for all obstacles.
        
        Only includes obstacles that have include_in_static_layout=True (excludes
        fully dynamic obstacles that move unpredictably).
        
        Args:
            clearance: Optional clearance margin around each obstacle.
            
        Returns:
            List of Rectangle bounding boxes for each obstacle that should be
            included in static layout calculations.
        """
        boxes = []
        for obs in self.obstacles:
            # Skip obstacles that should not be included in static layout
            if not obs.include_in_static_layout:
                continue
            
            # For USD assets, use a default size if not specified
            # In practice, you might want to read bounding box from USD metadata
            if obs.usd_path is not None:
                # Use a reasonable default size for USD assets
                # This could be improved by reading actual bounding box
                half_x = (obs.usd_scale[0] * 0.5) + clearance
                half_y = (obs.usd_scale[1] * 0.5) + clearance
            else:
                half_x = obs.size[0] / 2.0 + clearance
                half_y = obs.size[1] / 2.0 + clearance
            
            boxes.append(Rectangle(
                x_min=obs.position[0] - half_x,
                y_min=obs.position[1] - half_y,
                x_max=obs.position[0] + half_x,
                y_max=obs.position[1] + half_y,
            ))
        return boxes

    def _get_playground(self) -> Rectangle | None:
        """Get playground bounds as a Rectangle.
        
        Returns:
            Rectangle if playground is configured, None otherwise.
        """
        if self.playground is None:
            return None
        return Rectangle(
            x_min=self.playground[0],
            y_min=self.playground[1],
            x_max=self.playground[2],
            y_max=self.playground[3],
        )

    def _compute_free_zones(
        self,
    ) -> tuple[list[FreeZone], list[Rectangle], Rectangle]:
        """Compute free zones that are safe for robot navigation.
        
        Uses class configuration attributes for all parameters.
        
        Returns:
            Tuple of (free_zones, obstacle_boxes, playground).
        """
        playground = self._get_playground()
        
        # Get obstacle layout (no clearance expansion for free zone computation)
        obstacle_layout = self._get_obstacle_layout(clearance=0.0)
        
        # Use utility function to find free zones
        # The clearance parameter shrinks free zones by that amount for safety
        free_zones, playground = find_free_zones(
            obstacle_boxes=obstacle_layout,
            playground=playground,
            playground_margin=self.playground_margin,
            min_zone_size=self.min_zone_size,
            max_zones=self.max_zones,
            clearance=self.clearance,
        )
        
        return free_zones, obstacle_layout, playground

# Alias for backward compatibility
ObstacleEnvironmentPresetCfg = PresetNavigationEnvCfg

