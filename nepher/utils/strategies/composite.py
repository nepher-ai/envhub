# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""CompositeStrategy — weighted random delegation across child strategies."""

from __future__ import annotations

import torch


class CompositeStrategy:
    """Delegates each sample to a child strategy chosen by weighted random selection.

    Useful for environments with multiple navigable regions of differing size
    or importance (e.g. 70 % room A, 30 % room B).

    ``validate`` returns ``True`` if *any* child considers the position valid.
    """

    def __init__(
        self,
        strategies: list,
        weights: list[float] | None = None,
    ):
        if not strategies:
            raise ValueError("CompositeStrategy requires at least one child strategy.")
        self._strategies = strategies
        raw = weights or [1.0] * len(strategies)
        total = sum(raw)
        self._weights = [w / total for w in raw]

    def _assign(self, n: int, device: str | torch.device) -> torch.Tensor:
        return torch.multinomial(
            torch.tensor(self._weights, device=device), n, replacement=True,
        )

    # ------------------------------------------------------------------
    # PositionStrategy interface
    # ------------------------------------------------------------------

    def gen_spawn(self, n, *, device="cpu", env_ids=None, **kw):
        assignments = self._assign(n, device)
        all_pos = torch.zeros((n, 3), device=device)
        all_yaws = torch.zeros(n, device=device)
        for i, strategy in enumerate(self._strategies):
            mask = assignments == i
            count = int(mask.sum())
            if count == 0:
                continue
            sub_ids = env_ids[mask] if env_ids is not None else None
            pos, yaws = strategy.gen_spawn(count, device=device, env_ids=sub_ids, **kw)
            all_pos[mask] = pos
            all_yaws[mask] = yaws
        return all_pos, all_yaws

    def gen_goal(self, n, *, device="cpu", env_ids=None, spawn_positions=None, **kw):
        assignments = self._assign(n, device)
        all_goals = torch.zeros((n, 3), device=device)
        for i, strategy in enumerate(self._strategies):
            mask = assignments == i
            count = int(mask.sum())
            if count == 0:
                continue
            sub_ids = env_ids[mask] if env_ids is not None else None
            sub_spawn = spawn_positions[mask] if spawn_positions is not None else None
            all_goals[mask] = strategy.gen_goal(
                count, device=device, env_ids=sub_ids, spawn_positions=sub_spawn, **kw,
            )
        return all_goals

    def validate(self, positions, **kw):
        valid = torch.zeros(len(positions), dtype=torch.bool, device=positions.device)
        for strategy in self._strategies:
            valid |= strategy.validate(positions, **kw)
        return valid
