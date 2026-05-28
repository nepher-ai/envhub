# Copyright (c) 2026, Nepher Robotics
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
from nepher.utils.strategies.protocol import PositionStrategy


@configclass
class AbstractNavigationEnvCfg(BaseEnvCfg):
    """Base configuration for navigation environments.

    Subclasses provide a ``position_strategy`` for spawn / goal generation,
    or override ``gen_bot_pos`` / ``gen_goal_pos`` directly.

    When a strategy is set the abstract base acts as a thin adapter:
    it delegates numerical sampling to the strategy, then applies
    ``env_origins`` offsets, ``goal_z_offset``, and min / max distance
    enforcement centrally — so every strategy gets those features for free.
    """

    # Environment identification
    name: str = "abstract"
    description: str = "Abstract navigation environment"
    category: str = "navigation"

    # Task semantics
    success_tolerance: float = 0.5  # metres
    goal_z_offset: float = 0.0
    min_start_goal_dist: float = 1.0
    max_start_goal_dist: float = 10.0
    robot_radius: float = 0.3
    max_episode_length_s: float = 30.0

    # Position generation (set by environments / subclass __post_init__)
    position_strategy: PositionStrategy | None = None

    # ========== Required Methods (from BaseEnvCfg) ==========

    def get_terrain_cfg(self) -> TerrainImporterCfg:
        raise NotImplementedError("Subclass must implement get_terrain_cfg()")

    def get_scene_cfg(self) -> object:
        return self

    # ========== Position Generation (strategy-delegated) ==========

    def get_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        raise NotImplementedError("Subclass must implement get_obstacle_cfgs()")

    def gen_bot_pos(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Generate robot positions ``(n, 3)`` and yaws ``(n,)``.

        Delegates to ``position_strategy.gen_spawn`` and adds ``env_origins``.
        """
        strategy = self._resolve_strategy()
        local_pos, yaws = strategy.gen_spawn(
            len(env_ids), device=device, env_ids=env_ids, **kwargs,
        )
        local_pos[:, :2] += env_origins[env_ids, :2]
        return local_pos, yaws

    def gen_goal_pos(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> torch.Tensor:
        """Generate goal positions ``(n, 3)``.

        Delegates to ``position_strategy.gen_goal``, applies ``goal_z_offset``
        and ``env_origins``, then enforces min / max distance constraints when
        ``robot_positions`` is available in *kwargs*.
        """
        spawn_pos = kwargs.get("robot_positions")
        strategy = self._resolve_strategy()

        goals = strategy.gen_goal(
            len(env_ids), device=device, env_ids=env_ids,
            spawn_positions=spawn_pos, **kwargs,
        )
        goals[:, 2] = self.goal_z_offset
        goals[:, :2] += env_origins[env_ids, :2]

        if spawn_pos is not None and self.min_start_goal_dist > 0:
            goals = self._enforce_distance_constraints(
                goals, spawn_pos, env_ids, env_origins, device, strategy, **kwargs,
            )
        return goals

    def validate_positions(
        self,
        positions: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> torch.Tensor:
        """Return boolean tensor ``(N,)`` indicating valid positions."""
        strategy = self._resolve_strategy()
        return strategy.validate(positions, **kwargs)

    # ========== Internal Helpers ==========

    def _resolve_strategy(self) -> PositionStrategy:
        if self.position_strategy is None:
            raise NotImplementedError(
                "No position_strategy set. Either assign one or override "
                "gen_bot_pos / gen_goal_pos in your subclass."
            )
        return self.position_strategy

    def _enforce_distance_constraints(
        self,
        goals: torch.Tensor,
        spawn_pos: torch.Tensor,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device,
        strategy: PositionStrategy,
        _max_retries: int = 10,
        **kwargs,
    ) -> torch.Tensor:
        """Retry-resample goals that violate min / max distance to spawn."""
        for _ in range(_max_retries):
            dists = torch.norm(goals[:, :2] - spawn_pos[:, :2], dim=1)
            bad = dists < self.min_start_goal_dist
            if self.max_start_goal_dist > 0:
                bad |= dists > self.max_start_goal_dist
            if not bad.any():
                break
            bad_ids = env_ids[bad]
            new_goals = strategy.gen_goal(
                int(bad.sum()), device=device, env_ids=bad_ids,
                spawn_positions=spawn_pos[bad], **kwargs,
            )
            new_goals[:, 2] = self.goal_z_offset
            new_goals[:, :2] += env_origins[bad_ids, :2]
            goals[bad] = new_goals
        return goals

    # ========== Optional Hooks ==========

    def get_robot_asset_cfg(self) -> AssetBaseCfg | None:
        return None

    def get_sensor_cfgs(self) -> dict[str, object]:
        return {}

    def get_randomization_cfg(self) -> dict:
        return {}

    def get_metric_cfg(self) -> dict:
        return {}

    def get_metric_names(self) -> list[str]:
        return self.get_metric_cfg().get("metric_names", [])

    def get_light_cfgs(self) -> dict[str, AssetBaseCfg]:
        return {}

    def get_dynamic_obstacle_cfgs(self) -> dict[str, AssetBaseCfg]:
        return {}

    def get_region_cfgs(self) -> dict[str, object]:
        return {}

    def build_scene_cfg(self, **kwargs) -> object | None:
        return None

    # ========== Goal / Waypoint Generation ==========

    def update_goals_on_reached(
        self,
        env_ids: torch.Tensor,
        current_goals: torch.Tensor,
        env_origins: torch.Tensor,
        device: str | torch.device = "cpu",
        **kwargs,
    ) -> torch.Tensor:
        return self.gen_goal_pos(env_ids, env_origins, device=device, **kwargs)

    def gen_random_waypoints(
        self,
        env_ids: torch.Tensor,
        env_origins: torch.Tensor,
        num_waypoints: int,
        device: str | torch.device = "cpu",
        min_waypoint_distance: float | None = None,
        max_attempts_per_waypoint: int = 10,
        **kwargs,
    ) -> torch.Tensor:
        """Generate waypoint sequences ``(len(env_ids), num_waypoints, 3)``."""
        num_envs = len(env_ids)
        waypoints = torch.zeros((num_envs, num_waypoints, 3), device=device)
        waypoints[:, 0] = self.gen_goal_pos(env_ids, env_origins, device=device, **kwargs)

        for wp_idx in range(1, num_waypoints):
            if not min_waypoint_distance or min_waypoint_distance <= 0:
                waypoints[:, wp_idx] = self.gen_goal_pos(
                    env_ids, env_origins, device=device, **kwargs,
                )
                continue

            prev_wp = waypoints[:, wp_idx - 1]
            for attempt in range(max_attempts_per_waypoint):
                candidates = self.gen_goal_pos(env_ids, env_origins, device=device, **kwargs)
                distances = torch.norm(candidates[:, :2] - prev_wp[:, :2], dim=1)
                valid = distances >= min_waypoint_distance
                waypoints[valid, wp_idx] = candidates[valid]
                if valid.all() or attempt == max_attempts_per_waypoint - 1:
                    waypoints[~valid, wp_idx] = candidates[~valid]
                    break

        return waypoints
