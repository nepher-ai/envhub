# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Abstract base environment configuration for navigation environments."""

from __future__ import annotations

import torch
from isaaclab.assets import AssetBaseCfg
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass

from nepher.env_cfgs.base import BaseEnvCfg


@configclass
class AbstractNavigationEnvCfg(BaseEnvCfg):
    """Base configuration for navigation environments.
    
    Subclasses must override methods that raise NotImplementedError.
    
    This class extends BaseEnvCfg with navigation-specific functionality.
    """
    
    # Environment identification
    name: str = "abstract"
    description: str = "Abstract navigation environment"
    category: str = "navigation"
    
    # Task semantics
    success_tolerance: float = 0.5  # meters
    goal_z_offset: float = 0.0
    min_start_goal_dist: float = 1.0
    max_start_goal_dist: float = 10.0
    robot_radius: float = 0.3
    max_episode_length_s: float = 30.0
    
    # ========== Required Methods (from BaseEnvCfg) ==========
    
    def get_terrain_cfg(self) -> TerrainImporterCfg:
        """Return terrain configuration."""
        raise NotImplementedError("Subclass must implement get_terrain_cfg()")
    
    def get_scene_cfg(self) -> object:
        """Return scene configuration.
        
        For navigation environments, this returns the config itself as the scene config.
        """
        return self
    
    # ========== Required Methods (Navigation-Specific) ==========
    
    def get_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Return obstacle asset configurations dict."""
        raise NotImplementedError("Subclass must implement get_obstacle_cfgs()")
    
    def gen_goal_random_pos(
        self, env_ids: torch.Tensor, env_origins: torch.Tensor,
        device: str | torch.device = "cpu", **kwargs,
    ) -> torch.Tensor:
        """Generate goal positions (len(env_ids), 3)."""
        raise NotImplementedError("Subclass must implement gen_goal_random_pos()")
    
    def gen_bot_random_pos(
        self, env_ids: torch.Tensor, env_origins: torch.Tensor,
        device: str | torch.device = "cpu", **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Generate robot positions (len(env_ids), 3) and yaws (len(env_ids),)."""
        raise NotImplementedError("Subclass must implement gen_bot_random_pos()")
    
    def validate_positions(
        self, positions: torch.Tensor, env_origins: torch.Tensor,
        device: str | torch.device = "cpu", **kwargs,
    ) -> torch.Tensor:
        """Return boolean tensor (N,) indicating valid positions."""
        raise NotImplementedError("Subclass must implement validate_positions()")
    
    # ========== Optional Hooks ==========
    
    def get_robot_asset_cfg(self) -> AssetBaseCfg | None:
        """Return robot asset config, or None to use default."""
        return None
    
    def get_sensor_cfgs(self) -> dict[str, object]:
        """Return sensor configurations dict."""
        return {}
    
    def get_randomization_cfg(self) -> dict:
        """Return domain randomization configuration."""
        return {}
    
    def get_metric_cfg(self) -> dict:
        """Return metrics/logging configuration."""
        return {}
    
    def get_metric_names(self) -> list[str]:
        """Return list of metric names to track."""
        return self.get_metric_cfg().get("metric_names", [])
    
    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Return light configurations dict."""
        return {}
    
    def get_dynamic_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        """Return dynamic obstacle configurations dict."""
        return {}
    
    def get_region_cfgs(self) -> dict[str, object]:
        """Return semantic region configurations dict."""
        return {}
    
    def build_scene_cfg(self, **kwargs) -> object | None:
        """Return complete scene config, or None to use individual components."""
        return None
    
    # ========== Goal/Waypoint Generation ==========
    
    def update_goals_on_reached(
        self, env_ids: torch.Tensor, current_goals: torch.Tensor,
        env_origins: torch.Tensor, device: str | torch.device = "cpu", **kwargs,
    ) -> torch.Tensor:
        """Update goal positions when reached. Default: regenerate via gen_goal_random_pos."""
        return self.gen_goal_random_pos(env_ids, env_origins, device=device, **kwargs)
    
    def gen_random_waypoints(
        self, env_ids: torch.Tensor, env_origins: torch.Tensor, num_waypoints: int,
        device: str | torch.device = "cpu", min_waypoint_distance: float | None = None,
        max_attempts_per_waypoint: int = 10, **kwargs,
    ) -> torch.Tensor:
        """Generate waypoint sequences (len(env_ids), num_waypoints, 3)."""
        num_envs = len(env_ids)
        waypoints = torch.zeros((num_envs, num_waypoints, 3), device=device)
        waypoints[:, 0] = self.gen_goal_random_pos(env_ids, env_origins, device=device, **kwargs)
        
        for wp_idx in range(1, num_waypoints):
            if not min_waypoint_distance or min_waypoint_distance <= 0:
                waypoints[:, wp_idx] = self.gen_goal_random_pos(
                    env_ids, env_origins, device=device, **kwargs
                )
                continue
                
            prev_wp = waypoints[:, wp_idx - 1]
            for attempt in range(max_attempts_per_waypoint):
                candidates = self.gen_goal_random_pos(env_ids, env_origins, device=device, **kwargs)
                distances = torch.norm(candidates[:, :2] - prev_wp[:, :2], dim=1)
                valid = distances >= min_waypoint_distance
                
                waypoints[valid, wp_idx] = candidates[valid]
                if valid.all() or attempt == max_attempts_per_waypoint - 1:
                    waypoints[~valid, wp_idx] = candidates[~valid]
                    break
        
        return waypoints

# Alias for backward compatibility
AbstractEnvironmentCfg = AbstractNavigationEnvCfg

