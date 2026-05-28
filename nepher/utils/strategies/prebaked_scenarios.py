# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""PrebakedScenarioStrategy — offline-generated multi-object manipulation scenarios.

Mirrors :class:`PrebakedPairStrategy` (navigation) for manipulation benchmarks.

Each scenario defines, for M objects sorted by ``pick_order``:
  - spawn_pos / spawn_rot : robot-local-frame spawn pose
  - goal_pos  / goal_rot  : robot-local-frame goal pose

Scenario selection at episode reset: ``env_id % num_scenarios``.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch


class PrebakedScenarioStrategy:
    """Strategy backed by pre-computed multi-object manipulation scenarios.

    Scenario selection is ``env_ids.long() % num_scenarios`` — fully
    deterministic per env, diverse across parallel envs.

    All positions are in **robot-local frame** (added to ``env_origins`` by the
    reset event at runtime).

    Args:
        scenarios: List of scenario dicts, each with keys:
            ``"objects"`` — list of ``{name, pick_order, spawn_pos, spawn_rot}``
            ``"goals"``   — list of ``{target_object, goal_pos, goal_rot}``
    """

    def __init__(self, scenarios: list[dict]) -> None:
        if not scenarios:
            raise ValueError("PrebakedScenarioStrategy requires at least one scenario.")

        def _sorted_objects(sc: dict) -> list[dict]:
            return sorted(sc["objects"], key=lambda o: o["pick_order"])

        first_objects = _sorted_objects(scenarios[0])
        self._object_names: list[str] = [o["name"] for o in first_objects]
        M = len(self._object_names)

        spawn_pos_all: list[list] = []
        spawn_rot_all: list[list] = []
        goal_pos_all:  list[list] = []
        goal_rot_all:  list[list] = []

        for sc in scenarios:
            objs = _sorted_objects(sc)
            goal_by_name = {g["target_object"]: g for g in sc["goals"]}

            sc_spawn_pos, sc_spawn_rot = [], []
            sc_goal_pos,  sc_goal_rot  = [], []

            for obj in objs:
                sc_spawn_pos.append(list(obj["spawn_pos"]))
                sc_spawn_rot.append(list(obj["spawn_rot"]))
                goal = goal_by_name[obj["name"]]
                sc_goal_pos.append(list(goal["goal_pos"]))
                sc_goal_rot.append(list(goal["goal_rot"]))

            spawn_pos_all.append(sc_spawn_pos)   # (M, 3)
            spawn_rot_all.append(sc_spawn_rot)   # (M, 4)
            goal_pos_all.append(sc_goal_pos)     # (M, 3)
            goal_rot_all.append(sc_goal_rot)     # (M, 4)

        # Store as plain Python nested lists for pickle/config serialization
        # compatibility — same convention as PrebakedPairStrategy.
        self._spawn_pos = spawn_pos_all   # (S, M, 3)
        self._spawn_rot = spawn_rot_all   # (S, M, 4)
        self._goal_pos  = goal_pos_all    # (S, M, 3)
        self._goal_rot  = goal_rot_all    # (S, M, 4)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def num_scenarios(self) -> int:
        """Total number of pre-baked scenarios."""
        return len(self._spawn_pos)

    @property
    def num_objects(self) -> int:
        """Number of objects per scenario (M)."""
        return len(self._object_names)

    @property
    def object_names(self) -> list[str]:
        """Object names in pick_order (index 0 = picked first)."""
        return list(self._object_names)

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def get_spawns(
        self,
        env_ids: torch.Tensor,
        device: str | torch.device = "cpu",
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return spawn poses for the given env IDs.

        Returns:
            spawn_pos: ``(N, M, 3)`` robot-local-frame spawn positions.
            spawn_rot: ``(N, M, 4)`` spawn orientations (wxyz quaternion).
        """
        idx = env_ids.long() % self.num_scenarios
        t_pos = torch.as_tensor(self._spawn_pos, dtype=torch.float32, device=device)
        t_rot = torch.as_tensor(self._spawn_rot, dtype=torch.float32, device=device)
        return t_pos[idx], t_rot[idx]

    def get_goals(
        self,
        env_ids: torch.Tensor,
        device: str | torch.device = "cpu",
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return goal poses for the given env IDs.

        Returns:
            goal_pos: ``(N, M, 3)`` robot-local-frame goal positions.
            goal_rot: ``(N, M, 4)`` goal orientations (wxyz quaternion).
        """
        idx = env_ids.long() % self.num_scenarios
        t_pos = torch.as_tensor(self._goal_pos, dtype=torch.float32, device=device)
        t_rot = torch.as_tensor(self._goal_rot, dtype=torch.float32, device=device)
        return t_pos[idx], t_rot[idx]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: str | Path) -> "PrebakedScenarioStrategy":
        """Load from a ``scenarios.json`` file (``data["scenarios"]`` list)."""
        with open(path) as f:
            data = json.load(f)
        return cls(data["scenarios"])
