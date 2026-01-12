# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Fast O(1) spawn sampler using pre-computed valid positions.

All expensive work (occupancy map parsing, collision checks) happens at init.
Runtime sampling is just random index selection - O(1).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import torch
from PIL import Image
import yaml


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
        
        # Dilate obstacles by safety margin using max pooling
        if margin_px > 0:
            occ_tensor = torch.from_numpy(occupied.astype(np.float32)).unsqueeze(0).unsqueeze(0)
            dilated = torch.nn.functional.max_pool2d(
                occ_tensor, 
                kernel_size=2 * margin_px + 1, 
                stride=1, 
                padding=margin_px
            )
            occupied = dilated.squeeze().numpy() > 0.5
        
        # Find free cells (not occupied)
        free_rows, free_cols = np.where(~occupied)
        
        if len(free_rows) == 0:
            # No free cells - use origin as fallback
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
            return torch.ones(len(positions), dtype=torch.bool, device=self.device)
        
        # Compute distances to nearest valid position
        threshold = self.resolution * 1.5
        
        # Batch compute min distances
        # positions: (N, 2), valid: (M, 2)
        pos_exp = positions.unsqueeze(1)  # (N, 1, 2)
        valid_exp = valid.unsqueeze(0)  # (1, M, 2)
        
        # Min distance for each position
        dists = torch.norm(pos_exp - valid_exp, dim=2)  # (N, M)
        min_dists = dists.min(dim=1).values  # (N,)
        
        return min_dists <= threshold

