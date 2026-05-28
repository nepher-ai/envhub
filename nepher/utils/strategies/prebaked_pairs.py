# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""PrebakedPairStrategy — offline-generated (start, end) position pairs."""

from __future__ import annotations

import json
import math
from pathlib import Path
import torch


def _coerce_to_nested_float_lists(positions: torch.Tensor | list) -> list[list[float]]:
    """Store positions as plain Python lists so configs (e.g. Hydra/OmegaConf) can serialize."""
    if isinstance(positions, torch.Tensor):
        return positions.detach().cpu().tolist()
    return [list(row) for row in positions]


class PrebakedPairStrategy:
    """Strategy backed by pre-computed (start, end) position pairs.

    Pair selection is ``env_ids.long() % num_pairs`` — deterministic per env.

    Yaw options:
        * ``"face_goal"`` — ``atan2(end - start)``
        * ``"random"`` — uniform in *yaw_range*
        * any ``float`` — fixed yaw for every spawn
    """

    def __init__(
        self,
        starts: torch.Tensor | list,
        ends: torch.Tensor | list,
        yaw_mode: str | float = "face_goal",
        yaw_range: tuple[float, float] = (-math.pi, math.pi),
    ):
        self._starts = _coerce_to_nested_float_lists(starts)
        self._ends = _coerce_to_nested_float_lists(ends)
        self._yaw_mode = yaw_mode
        self._yaw_range = yaw_range

    @property
    def num_pairs(self) -> int:
        return len(self._starts)

    # ------------------------------------------------------------------
    # PositionStrategy interface
    # ------------------------------------------------------------------

    def gen_spawn(self, n, *, device="cpu", env_ids=None, **kw):
        idx = env_ids.long() % self.num_pairs
        t_starts = torch.as_tensor(self._starts, dtype=torch.float32, device=device)
        t_ends = torch.as_tensor(self._ends, dtype=torch.float32, device=device)
        starts = t_starts[idx]
        ends = t_ends[idx]

        if self._yaw_mode == "face_goal":
            delta = ends - starts
            yaws = torch.atan2(delta[:, 1], delta[:, 0])
        elif self._yaw_mode == "random":
            lo, hi = self._yaw_range
            yaws = torch.rand(n, device=device) * (hi - lo) + lo
        else:
            yaws = torch.full((n,), float(self._yaw_mode), device=device)

        return starts.clone(), yaws

    def gen_goal(self, n, *, device="cpu", env_ids=None, **kw):
        idx = env_ids.long() % self.num_pairs
        t_ends = torch.as_tensor(self._ends, dtype=torch.float32, device=device)
        return t_ends[idx].clone()

    def validate(self, positions, **kw):
        return torch.ones(len(positions), dtype=torch.bool, device=positions.device)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_positions_json(cls, path: str | Path, **kw) -> PrebakedPairStrategy:
        """Load from the ``generate_positions.py`` output format.

        Each cell has an *origin* ``[x, y, z]`` and a list of *pairs* with
        local ``start`` / ``end`` offsets.  Origins are baked into the
        resulting lists so the strategy operates in absolute local coords.
        """
        with open(path) as f:
            data = json.load(f)
        starts, ends = [], []
        for cell in data["cells"]:
            ox, oy, oz = cell["origin"]
            for pair in cell["pairs"]:
                starts.append([ox + pair["start"][0], oy + pair["start"][1], pair["start"][2]])
                ends.append([ox + pair["end"][0], oy + pair["end"][1], pair["end"][2]])
        return cls(starts=starts, ends=ends, **kw)
