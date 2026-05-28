# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""UniformBoxStrategy — trivial uniform sampling in an axis-aligned bounding box."""

from __future__ import annotations

import math

import torch


class UniformBoxStrategy:
    """Uniform random sampling inside an axis-aligned bounding box.

    Useful as a simple fallback or for flat environments without obstacles.
    """

    def __init__(
        self,
        bounds: tuple[float, float, float, float],
        yaw_range: tuple[float, float] = (-math.pi, math.pi),
        z: float = 0.0,
    ):
        self._bounds = bounds  # (x_min, y_min, x_max, y_max)
        self._yaw_range = yaw_range
        self._z = z

    def _sample_xy(self, n: int, device: str | torch.device) -> torch.Tensor:
        x_min, y_min, x_max, y_max = self._bounds
        xy = torch.rand((n, 2), device=device)
        xy[:, 0] = xy[:, 0] * (x_max - x_min) + x_min
        xy[:, 1] = xy[:, 1] * (y_max - y_min) + y_min
        return xy

    # ------------------------------------------------------------------
    # PositionStrategy interface
    # ------------------------------------------------------------------

    def gen_spawn(self, n, *, device="cpu", env_ids=None, **kw):
        pos = torch.zeros((n, 3), device=device)
        pos[:, :2] = self._sample_xy(n, device)
        pos[:, 2] = self._z
        lo, hi = self._yaw_range
        yaws = torch.rand(n, device=device) * (hi - lo) + lo
        return pos, yaws

    def gen_goal(self, n, *, device="cpu", env_ids=None, spawn_positions=None, **kw):
        goals = torch.zeros((n, 3), device=device)
        goals[:, :2] = self._sample_xy(n, device)
        goals[:, 2] = self._z
        return goals

    def validate(self, positions, **kw):
        x_min, y_min, x_max, y_max = self._bounds
        xy = positions[:, :2] if positions.shape[1] >= 2 else positions
        return (
            (xy[:, 0] >= x_min) & (xy[:, 0] <= x_max)
            & (xy[:, 1] >= y_min) & (xy[:, 1] <= y_max)
        )
