# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""PositionStrategy protocol — pluggable position generation interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import torch


@runtime_checkable
class PositionStrategy(Protocol):
    """Pluggable position generation strategy.

    Implementations produce LOCAL coordinates (relative to sub-terrain
    or cell origin).  The EnvCfg layer adds env_origins, device transfer,
    and z-offset.
    """

    def gen_spawn(
        self,
        n: int,
        *,
        device: str | torch.device = "cpu",
        env_ids: torch.Tensor | None = None,
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return (positions ``(n, 3)``, yaws ``(n,)``) in local coords."""
        ...

    def gen_goal(
        self,
        n: int,
        *,
        device: str | torch.device = "cpu",
        env_ids: torch.Tensor | None = None,
        spawn_positions: torch.Tensor | None = None,
        **kwargs,
    ) -> torch.Tensor:
        """Return goal positions ``(n, 3)`` in local coords."""
        ...

    def validate(
        self,
        positions: torch.Tensor,
        **kwargs,
    ) -> torch.Tensor:
        """Return boolean mask ``(n,)`` — ``True`` = valid."""
        ...
