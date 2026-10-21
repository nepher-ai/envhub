# Copyright (c) 2026, Nepher Robotics
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Fast O(1) spawn sampler using pre-computed valid positions.

All expensive work (occupancy map parsing, collision checks) happens at init.
Runtime sampling is just random index selection - O(1).
"""

from __future__ import annotations

import math
import os
import warnings
from dataclasses import dataclass

import numpy as np
import torch
from PIL import Image
import yaml


def _rotate(x: float, y: float, yaw: float) -> tuple[float, float]:
    c, s = math.cos(yaw), math.sin(yaw)
    return c * x - s * y, s * x + c * y


@dataclass
class OccupancyMapConfig:
    """Configuration for loading an occupancy map."""
    yaml_path: str
    """Path to the occupancy map YAML file."""
    safety_margin: float = 0.5
    """Safety margin in meters around obstacles."""
    

class FastSpawnSampler:
    """Pre-computes valid spawn positions for O(1) runtime sampling.
    
    At init: Scans occupancy map / spawn areas, builds tensor of valid (x,y) coords.
    At runtime: torch.randint + index lookup = O(1) per sample.
    
    Note on ROS occupancy map conventions:
        - Origin is at the BOTTOM-LEFT of the image in world coordinates
        - +Y in world points UPWARD, but image row 0 is at TOP
        - origin = [x, y, theta] where theta is map rotation (yaw) in radians
    """
    
    def __init__(
        self,
        device: str | torch.device = "cpu",
        omap_config: OccupancyMapConfig | None = None,
        spawn_bounds: tuple[float, float, float, float] | None = None,
        exclusion_rects: list[tuple[float, float, float, float]] | None = None,
        grid_resolution: float = 0.1,
        safety_margin: float = 0.5,
        usd_offset: tuple[float, float, float] | None = None,
    ):
        """Initialize the fast spawn sampler.
        
        Args:
            device: Torch device for tensors.
            omap_config: Occupancy map config (YAML path + margin). If provided, uses omap.
            spawn_bounds: (x_min, y_min, x_max, y_max) fallback spawn area if no omap.
            exclusion_rects: List of (x_min, y_min, x_max, y_max) exclusion zones.
            grid_resolution: Grid cell size in meters for discretization.
            safety_margin: Safety margin around obstacles in meters.
            usd_offset: Optional (x, y, yaw) offset to reconcile map frame with USD placement.
                        Applied AFTER map-to-world transform. Use when USD scene origin
                        doesn't match the map's world origin.
        """
        self.device = device
        self.resolution = grid_resolution
        self.safety_margin = safety_margin
        self.usd_offset = usd_offset
        self._valid_positions: torch.Tensor | None = None
        self._num_valid: int = 0
        # Lattice used by validate(): world xy -> (row, col) via
        # local = R(-grid_yaw) @ xy + grid_shift, col = local_x / step,
        # row = local_y / step (flipped when grid_flip_rows).
        self._grid_valid: torch.Tensor | None = None
        self._grid_step: float = grid_resolution
        self._grid_yaw: float = 0.0
        self._grid_shift: tuple[float, float] = (0.0, 0.0)
        self._grid_flip_rows: bool = False
        
        if omap_config and os.path.exists(omap_config.yaml_path):
            self._init_from_occupancy_map(omap_config)
        elif spawn_bounds:
            self._init_from_bounds(spawn_bounds, exclusion_rects or [])
        else:
            # Fallback: 10x10m area centered at origin
            self._init_from_bounds((-5.0, -5.0, 5.0, 5.0), exclusion_rects or [])
    
    def _init_from_occupancy_map(self, config: OccupancyMapConfig) -> None:
        """Load occupancy map and extract all free cells.
        
        Correctly handles ROS occupancy map conventions:
        - origin is at BOTTOM-LEFT of image in world frame
        - image row 0 is at TOP (so must flip Y)
        - origin[2] is yaw rotation in radians
        """
        with open(config.yaml_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f.read())
        
        img_path = os.path.join(os.path.dirname(config.yaml_path), meta["image"])
        img = np.array(Image.open(img_path))
        
        resolution = meta["resolution"]
        origin = meta["origin"]  # [x, y, theta] in world coords
        origin_x, origin_y = origin[0], origin[1]
        origin_yaw = origin[2] if len(origin) > 2 else 0.0  # rotation in radians
        
        # Get image dimensions (height = rows, width = cols)
        img_height = img.shape[0]
        
        margin_px = int(np.ceil(config.safety_margin / resolution))
        
        # Build occupancy grid (True = occupied)
        # Handle both grayscale and RGB images
        if len(img.shape) == 3:
            pixel_values = img[:, :, 0]
        else:
            pixel_values = img
            
        if meta.get("negate", False):
            occupied = (pixel_values / 255.0) > meta["free_thresh"]
        else:
            occupied = ((255 - pixel_values) / 255.0) > meta["free_thresh"]
        
        # Dilate obstacles by the safety margin. A square max filter is separable,
        # so two 1-D passes cost O(k) per pixel instead of O(k^2).
        if margin_px > 0:
            occ = torch.from_numpy(occupied.astype(np.float32))[None, None]
            k = 2 * margin_px + 1
            occ = torch.nn.functional.max_pool2d(occ, kernel_size=(k, 1), stride=1, padding=(margin_px, 0))
            occ = torch.nn.functional.max_pool2d(occ, kernel_size=(1, k), stride=1, padding=(0, margin_px))
            occupied = occ[0, 0].numpy() > 0.5

        free = ~occupied
        free_rows, free_cols = np.where(free)

        if len(free_rows) == 0:
            warnings.warn(
                f"Occupancy map {config.yaml_path} has no free cells after a "
                f"{config.safety_margin} m safety margin; spawning at the map origin.",
                stacklevel=3,
            )
            self._valid_positions = torch.tensor([[origin_x, origin_y]], device=self.device)
            self._num_valid = 1
            return
        
        # Convert pixel coords to world coords (ROS convention)
        # 
        # ROS occupancy map convention:
        #   - origin is the real-world pose of the BOTTOM-LEFT corner of the image
        #   - In the image, row 0 is TOP, but in world coords that's the TOP of the map
        #   - So for a pixel at (row, col):
        #       world_x = origin_x + col * resolution
        #       world_y = origin_y + (image_height - 1 - row) * resolution
        #
        # The (image_height - 1 - row) flips the Y axis from image coords to world coords
        
        world_x = origin_x + free_cols * resolution
        world_y = origin_y + (img_height - 1 - free_rows) * resolution
        
        # Apply map rotation (yaw) if non-zero
        # Rotation is around the origin point
        if abs(origin_yaw) > 1e-6:
            cos_yaw = np.cos(origin_yaw)
            sin_yaw = np.sin(origin_yaw)
            
            # Translate to origin, rotate, translate back
            dx = world_x - origin_x
            dy = world_y - origin_y
            
            world_x = origin_x + dx * cos_yaw - dy * sin_yaw
            world_y = origin_y + dx * sin_yaw + dy * cos_yaw
        
        # Apply USD offset if provided (reconcile map frame with USD scene frame)
        if self.usd_offset is not None:
            usd_x, usd_y = self.usd_offset[0], self.usd_offset[1]
            usd_yaw = self.usd_offset[2] if len(self.usd_offset) > 2 else 0.0
            
            if abs(usd_yaw) > 1e-6:
                cos_yaw = np.cos(usd_yaw)
                sin_yaw = np.sin(usd_yaw)
                rotated_x = world_x * cos_yaw - world_y * sin_yaw
                rotated_y = world_x * sin_yaw + world_y * cos_yaw
                world_x = rotated_x + usd_x
                world_y = rotated_y + usd_y
            else:
                world_x = world_x + usd_x
                world_y = world_y + usd_y
        
        # Stack as (N, 2) tensor
        positions = np.stack([world_x, world_y], axis=1).astype(np.float32)
        self._valid_positions = torch.from_numpy(positions).to(self.device)
        self._num_valid = len(positions)

        # Inverse of the transforms above, for grid-based validate().
        usd_x, usd_y, usd_yaw = 0.0, 0.0, 0.0
        if self.usd_offset is not None:
            usd_x, usd_y = self.usd_offset[0], self.usd_offset[1]
            usd_yaw = self.usd_offset[2] if len(self.usd_offset) > 2 else 0.0
        total_yaw = origin_yaw + usd_yaw
        inv_ux, inv_uy = _rotate(-usd_x, -usd_y, -total_yaw)
        inv_ox, inv_oy = _rotate(-origin_x, -origin_y, -origin_yaw)
        self._set_grid(
            free,
            step=resolution,
            yaw=total_yaw,
            shift=(inv_ux + inv_ox, inv_uy + inv_oy),
            flip_rows=True,
        )

    def _set_grid(
        self,
        valid: np.ndarray,
        *,
        step: float,
        yaw: float,
        shift: tuple[float, float],
        flip_rows: bool,
    ) -> None:
        """Store a lookup grid where a cell is True if a valid position lies within
        ``1.5 * grid_resolution`` of it (same tolerance as the original nearest-neighbour check)."""
        radius = 1.5 * self.resolution / step
        r = int(math.floor(radius))
        mask = torch.from_numpy(valid.astype(np.float32))[None, None]
        if r > 0:
            offsets = torch.arange(-r, r + 1, dtype=torch.float32)
            disk = (offsets[:, None] ** 2 + offsets[None, :] ** 2 <= radius**2).float()[None, None]
            mask = torch.nn.functional.pad(mask, (r, r, r, r))
            mask = torch.nn.functional.conv2d(mask, disk, padding=r)
        self._grid_valid = (mask[0, 0] > 0.5).to(self.device)
        self._grid_pad = r
        self._grid_rows = valid.shape[0]
        self._grid_step = step
        self._grid_yaw = yaw
        self._grid_shift = shift
        self._grid_flip_rows = flip_rows
    
    def _init_from_bounds(
        self,
        bounds: tuple[float, float, float, float],
        exclusions: list[tuple[float, float, float, float]],
    ) -> None:
        """Generate valid positions from rectangular bounds, excluding zones."""
        x_min, y_min, x_max, y_max = bounds
        
        # Generate grid of candidate positions
        xs = np.arange(x_min + self.safety_margin, x_max - self.safety_margin, self.resolution)
        ys = np.arange(y_min + self.safety_margin, y_max - self.safety_margin, self.resolution)
        
        if len(xs) == 0 or len(ys) == 0:
            # Area too small - use center
            cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
            self._valid_positions = torch.tensor([[cx, cy]], device=self.device)
            self._num_valid = 1
            return
        
        xx, yy = np.meshgrid(xs, ys)
        candidates = np.stack([xx.ravel(), yy.ravel()], axis=1)
        
        # Filter out exclusion zones
        valid_mask = np.ones(len(candidates), dtype=bool)
        for ex_xmin, ex_ymin, ex_xmax, ex_ymax in exclusions:
            # Expand exclusion by safety margin
            in_exclusion = (
                (candidates[:, 0] >= ex_xmin - self.safety_margin) &
                (candidates[:, 0] <= ex_xmax + self.safety_margin) &
                (candidates[:, 1] >= ex_ymin - self.safety_margin) &
                (candidates[:, 1] <= ex_ymax + self.safety_margin)
            )
            valid_mask &= ~in_exclusion
        
        valid_positions = candidates[valid_mask].astype(np.float32)

        if len(valid_positions) > 0:
            self._set_grid(
                valid_mask.reshape(len(ys), len(xs)),
                step=self.resolution,
                yaw=0.0,
                shift=(-float(xs[0]), -float(ys[0])),
                flip_rows=False,
            )

        if len(valid_positions) == 0:
            # All positions excluded - use center of bounds
            cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
            self._valid_positions = torch.tensor([[cx, cy]], device=self.device)
            self._num_valid = 1
        else:
            self._valid_positions = torch.from_numpy(valid_positions).to(self.device)
            self._num_valid = len(valid_positions)
    
    @property
    def num_valid_positions(self) -> int:
        """Number of pre-computed valid positions."""
        return self._num_valid
    
    @property 
    def is_ready(self) -> bool:
        """Check if sampler has valid positions."""
        return self._valid_positions is not None and self._num_valid > 0
    
    def sample(self, n: int) -> torch.Tensor:
        """Sample n random positions in O(1).
        
        Args:
            n: Number of positions to sample.
            
        Returns:
            Tensor of shape (n, 2) with (x, y) world coordinates.
        """
        if self._valid_positions is None or self._num_valid == 0:
            return torch.zeros((n, 2), device=self.device)
        
        indices = torch.randint(0, self._num_valid, (n,), device=self.device)
        return self._valid_positions[indices]
    
    def sample_with_min_distance(
        self,
        n: int,
        existing_positions: torch.Tensor | None = None,
        min_distance: float = 1.0,
        max_attempts: int = 10,
    ) -> torch.Tensor:
        """Sample n positions with minimum distance constraint.
        
        Args:
            n: Number of positions to sample.
            existing_positions: (M, 2) tensor of positions to avoid.
            min_distance: Minimum distance between sampled positions and existing ones.
            max_attempts: Max attempts per sample before accepting any valid position.
            
        Returns:
            Tensor of shape (n, 2) with (x, y) world coordinates.
        """
        valid = self._valid_positions
        if valid is None or self._num_valid == 0:
            return torch.zeros((n, 2), device=self.device)
        
        result = torch.zeros((n, 2), device=self.device)
        
        for i in range(n):
            for _ in range(max_attempts):
                idx = torch.randint(0, self._num_valid, (1,), device=self.device)
                pos = valid[idx]
                
                # Check distance to existing positions
                if existing_positions is not None and len(existing_positions) > 0:
                    dists = torch.norm(existing_positions - pos, dim=1)
                    if dists.min() < min_distance:
                        continue
                
                # Check distance to already sampled positions
                if i > 0:
                    dists = torch.norm(result[:i] - pos, dim=1)
                    if dists.min() < min_distance:
                        continue
                
                result[i] = pos.squeeze()
                break
            else:
                # Max attempts reached - just pick random
                idx = torch.randint(0, self._num_valid, (1,), device=self.device)
                result[i] = valid[idx].squeeze()
        
        return result
    
    def validate(self, positions: torch.Tensor) -> torch.Tensor:
        """Check if positions are in the valid set (approximate).
        
        Uses nearest-neighbor check against valid positions.
        
        Args:
            positions: (N, 2) tensor of positions to validate.
            
        Returns:
            Boolean tensor of shape (N,) - True if position is near a valid cell.
        """
        valid = self._valid_positions
        if valid is None or self._num_valid == 0 or len(positions) == 0:
            return torch.ones(len(positions), dtype=torch.bool, device=positions.device)

        if self._grid_valid is None:
            # Single fallback position: a direct distance check is cheap.
            dists = torch.norm(positions[:, None, :2].to(valid.device) - valid[None], dim=2)
            return (dists.min(dim=1).values <= self.resolution * 1.5).to(positions.device)

        grid = self._grid_valid
        xy = positions[:, :2].to(device=grid.device, dtype=torch.float32)
        c, s = math.cos(self._grid_yaw), math.sin(self._grid_yaw)
        local_x = c * xy[:, 0] + s * xy[:, 1] + self._grid_shift[0]
        local_y = -s * xy[:, 0] + c * xy[:, 1] + self._grid_shift[1]
        cols = torch.round(local_x / self._grid_step).long()
        rows = torch.round(local_y / self._grid_step).long()
        if self._grid_flip_rows:
            rows = (self._grid_rows - 1) - rows
        rows = rows + self._grid_pad
        cols = cols + self._grid_pad

        height, width = grid.shape
        inside = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
        result = torch.zeros(len(positions), dtype=torch.bool, device=grid.device)
        result[inside] = grid[rows[inside], cols[inside]]
        return result.to(positions.device)

