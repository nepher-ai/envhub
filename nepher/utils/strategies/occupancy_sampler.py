# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""OccupancySamplerStrategy — wraps FastSpawnSampler for USD / real-world scenes."""

from __future__ import annotations

import math

import torch

from nepher.utils.fast_spawn_sampler import FastSpawnSampler, OccupancyMapConfig


class OccupancySamplerStrategy:
    """O(1) position sampling from a pre-computed occupancy grid.

    The underlying :class:`FastSpawnSampler` is lazily initialised on first
    use so that heavy work (map loading, grid building) is deferred until
    the target device is known.
    """

    def __init__(
        self,
        *,
        omap_config: OccupancyMapConfig | None = None,
        spawn_bounds: tuple[float, float, float, float] | None = None,
        exclusion_rects: list[tuple[float, float, float, float]] | None = None,
        grid_resolution: float = 0.1,
        safety_margin: float = 0.5,
        usd_offset: tuple[float, float, float] | None = None,
        yaw_range: tuple[float, float] = (-math.pi, math.pi),
    ):
        self._omap_config = omap_config
        self._spawn_bounds = spawn_bounds
        self._exclusion_rects = exclusion_rects or []
        self._grid_resolution = grid_resolution
        self._safety_margin = safety_margin
        self._usd_offset = usd_offset
        self._yaw_range = yaw_range
        self._sampler: FastSpawnSampler | None = None

    def _get_sampler(self, device: str | torch.device = "cpu") -> FastSpawnSampler:
        if self._sampler is None:
            self._sampler = FastSpawnSampler(
                device=device,
                omap_config=self._omap_config,
                spawn_bounds=self._spawn_bounds,
                exclusion_rects=self._exclusion_rects,
                grid_resolution=self._grid_resolution,
                safety_margin=self._safety_margin,
                usd_offset=self._usd_offset,
            )
        return self._sampler

    # ------------------------------------------------------------------
    # PositionStrategy interface
    # ------------------------------------------------------------------

    def gen_spawn(self, n, *, device="cpu", env_ids=None, **kw):
        xy = self._get_sampler(device).sample(n)
        positions = torch.zeros((n, 3), device=device)
        positions[:, :2] = xy.to(device)
        lo, hi = self._yaw_range
        yaws = torch.rand(n, device=device) * (hi - lo) + lo
        return positions, yaws

    def gen_goal(self, n, *, device="cpu", env_ids=None, spawn_positions=None, **kw):
        xy = self._get_sampler(device).sample(n)
        goals = torch.zeros((n, 3), device=device)
        goals[:, :2] = xy.to(device)
        return goals

    def validate(self, positions, **kw):
        device = positions.device
        xy = positions[:, :2] if positions.shape[1] >= 2 else positions
        return self._get_sampler(device).validate(xy.to(device))
