"""Tests for FastSpawnSampler grid validation and prebaked strategy caching."""

import math

import numpy as np
import pytest
import torch
import yaml
from PIL import Image

from nepher.utils.fast_spawn_sampler import FastSpawnSampler, OccupancyMapConfig
from nepher.utils.strategies.prebaked_pairs import PrebakedPairStrategy


def _brute_force_validate(sampler: FastSpawnSampler, positions: torch.Tensor) -> torch.Tensor:
    """The original O(N*M) nearest-neighbour check."""
    dists = torch.cdist(positions[:, :2], sampler._valid_positions)
    return dists.min(dim=1).values <= sampler.resolution * 1.5


def _write_map(tmp_path, yaw: float) -> str:
    rng = np.random.default_rng(0)
    img = np.full((60, 80), 255, dtype=np.uint8)
    for _ in range(12):
        r, c = rng.integers(0, 55), rng.integers(0, 75)
        img[r : r + 5, c : c + 5] = 0
    Image.fromarray(img).save(tmp_path / "map.png")
    meta = {"image": "map.png", "resolution": 0.05, "origin": [-1.0, 2.0, yaw], "negate": 0, "free_thresh": 0.2}
    path = tmp_path / "map.yaml"
    path.write_text(yaml.safe_dump(meta), encoding="utf-8")
    return str(path)


def _agreement(sampler: FastSpawnSampler, positions: torch.Tensor) -> float:
    fast = sampler.validate(positions)
    slow = _brute_force_validate(sampler, positions)
    return (fast == slow).float().mean().item()


@pytest.mark.parametrize("yaw", [0.0, 0.4])
@pytest.mark.parametrize("usd_offset", [None, (1.5, -0.5, 0.0), (1.5, -0.5, 0.3)])
def test_omap_grid_validate_matches_brute_force(tmp_path, yaw, usd_offset):
    sampler = FastSpawnSampler(
        omap_config=OccupancyMapConfig(yaml_path=_write_map(tmp_path, yaw), safety_margin=0.1),
        usd_offset=usd_offset,
    )
    assert sampler.validate(sampler.sample(500)).all()

    gen = torch.Generator().manual_seed(1)
    probe = sampler._valid_positions.mean(0) + (torch.rand((3000, 2), generator=gen) - 0.5) * 6.0
    assert _agreement(sampler, probe) > 0.97


def test_bounds_grid_validate_matches_brute_force():
    sampler = FastSpawnSampler(spawn_bounds=(-3, -2, 4, 5), exclusion_rects=[(0, 0, 1, 1)], safety_margin=0.3)
    assert sampler.validate(sampler.sample(500)).all()
    probe = (torch.rand((3000, 2), generator=torch.Generator().manual_seed(2)) - 0.5) * 12.0
    assert _agreement(sampler, probe) > 0.97
    assert not sampler.validate(torch.tensor([[0.5, 0.5], [50.0, 50.0]])).any()


def test_separable_dilation_matches_full_kernel(tmp_path):
    path = _write_map(tmp_path, 0.0)
    sampler = FastSpawnSampler(omap_config=OccupancyMapConfig(yaml_path=path, safety_margin=0.25))

    img = np.array(Image.open(tmp_path / "map.png"))
    occupied = ((255 - img) / 255.0) > 0.2
    m = int(math.ceil(0.25 / 0.05))
    full = torch.nn.functional.max_pool2d(
        torch.from_numpy(occupied.astype(np.float32))[None, None], kernel_size=2 * m + 1, stride=1, padding=m
    )[0, 0].numpy() > 0.5
    assert sampler.num_valid_positions == int((~full).sum())


def test_prebaked_pairs_cache_and_results():
    strategy = PrebakedPairStrategy(starts=[[0, 0, 0], [1, 0, 0]], ends=[[0, 1, 0], [2, 0, 0]])
    ids = torch.tensor([0, 1, 2])
    pos1, yaw1 = strategy.gen_spawn(3, env_ids=ids)
    pos2, _ = strategy.gen_spawn(3, env_ids=ids)
    assert torch.equal(pos1, pos2)
    assert torch.allclose(pos1[:, 0], torch.tensor([0.0, 1.0, 0.0]))
    assert torch.allclose(yaw1, torch.tensor([math.pi / 2, 0.0, math.pi / 2]))
    pos1[0, 0] = 99.0
    assert strategy.gen_spawn(1, env_ids=torch.tensor([0]))[0][0, 0] == 0.0
    assert "_cache" not in vars(strategy) and isinstance(strategy._starts, list)
