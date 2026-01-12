# Copyright (c) 2025, Nepher Team
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Free zone computation utilities.

This module provides functions to compute free zones (obstacle-free rectangular regions)
within a playground given a set of obstacle rectangles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


class FreeZone(NamedTuple):
    """A rectangular free zone defined by two corner points."""
    x1: float
    y1: float
    x2: float
    y2: float
    
    @property
    def width(self) -> float:
        """Width of the free zone (x-dimension)."""
        return abs(self.x2 - self.x1)
    
    @property
    def height(self) -> float:
        """Height of the free zone (y-dimension)."""
        return abs(self.y2 - self.y1)
    
    @property
    def area(self) -> float:
        """Area of the free zone."""
        return self.width * self.height
    
    @property
    def center(self) -> tuple[float, float]:
        """Center point of the free zone."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def shrink(self, margin: float) -> FreeZone:
        """Return a new free zone shrunk by the given margin on all sides."""
        return FreeZone(
            x1=self.x1 + margin,
            y1=self.y1 + margin,
            x2=self.x2 - margin,
            y2=self.y2 - margin,
        )

    def expand(self, margin: float) -> FreeZone:
        """Return a new free zone expanded by the given margin on all sides."""
        return FreeZone(
            x1=self.x1 - margin,
            y1=self.y1 - margin,
            x2=self.x2 + margin,
            y2=self.y2 + margin,
        )
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside this free zone.
        
        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.
            
        Returns:
            True if the point is inside the free zone, False otherwise.
        """
        x_min = min(self.x1, self.x2)
        x_max = max(self.x1, self.x2)
        y_min = min(self.y1, self.y2)
        y_max = max(self.y1, self.y2)
        return x_min <= x <= x_max and y_min <= y <= y_max


@dataclass
class Rectangle:
    """Axis-aligned rectangle defined by min/max coordinates."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    
    @property
    def width(self) -> float:
        """Width of the rectangle (x-dimension)."""
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        """Height of the rectangle (y-dimension)."""
        return self.y_max - self.y_min
    
    @property
    def center(self) -> tuple[float, float]:
        """Center point of the rectangle."""
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside this rectangle."""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max
    
    def intersects(self, other: Rectangle) -> bool:
        """Check if this rectangle intersects with another."""
        return not (
            self.x_max < other.x_min or self.x_min > other.x_max or
            self.y_max < other.y_min or self.y_min > other.y_max
        )
    
    def expand(self, margin: float) -> Rectangle:
        """Return a new rectangle expanded by the given margin on all sides."""
        return Rectangle(
            x_min=self.x_min - margin,
            y_min=self.y_min - margin,
            x_max=self.x_max + margin,
            y_max=self.y_max + margin,
        )
    
    def shrink(self, margin: float) -> Rectangle:
        """Return a new rectangle shrunk by the given margin on all sides."""
        return Rectangle(
            x_min=self.x_min + margin,
            y_min=self.y_min + margin,
            x_max=self.x_max - margin,
            y_max=self.y_max - margin,
        )


def compute_bounding_playground(obstacles: list[Rectangle] | None, margin: float = 1.0) -> Rectangle:
    """Compute a playground that bounds all obstacles with a margin."""
    if not obstacles:
        return Rectangle(x_min=-margin, y_min=-margin, x_max=margin, y_max=margin)
    
    return Rectangle(
        x_min=min(obs.x_min for obs in obstacles) - margin,
        y_min=min(obs.y_min for obs in obstacles) - margin,
        x_max=max(obs.x_max for obs in obstacles) + margin,
        y_max=max(obs.y_max for obs in obstacles) + margin,
    )


def _zones_overlap(z1: FreeZone, z2: FreeZone) -> bool:
    """Check if two zones overlap."""
    return not (z1.x2 <= z2.x1 or z1.x1 >= z2.x2 or z1.y2 <= z2.y1 or z1.y1 >= z2.y2)


def _zone_is_obstacle_free(zone: FreeZone, obstacles: list[Rectangle]) -> bool:
    """Check if a zone is completely free of obstacles."""
    return not any(
        not (zone.x2 <= obs.x_min or zone.x1 >= obs.x_max or zone.y2 <= obs.y_min or zone.y1 >= obs.y_max)
        for obs in obstacles
    )


def _remove_overlapping_zones(zones: list[FreeZone]) -> list[FreeZone]:
    """Remove overlapping zones, keeping larger ones (zones must be sorted by area)."""
    non_overlapping = []
    for zone in zones:
        if not any(_zones_overlap(zone, kept) for kept in non_overlapping):
            non_overlapping.append(zone)
    return non_overlapping


def find_free_zones(
    obstacle_boxes: list[Rectangle] | None = None,
    playground: Rectangle | None = None,
    playground_margin: float = 1.0,
    min_zone_size: float = 0.5,
    max_zones: int | None = None,
    clearance: float = 0.3,
) -> tuple[list[FreeZone], Rectangle]:
    """Find free zones within a playground given obstacle rectangles.
    
    A **free zone** is a rectangular region that:
    1. Is entirely within the playground bounds.
    2. Does not overlap with any obstacle rectangle.
    3. Does not overlap with any other free zone.
    4. Has minimum dimensions (width and height) of at least `min_zone_size`.
    
    The algorithm uses a boundary-based sweep approach to maximize the number of zones:
    1. Collect all x and y boundaries from obstacles and playground.
    2. Generate candidate zones from all combinations of these boundaries.
    3. Test each candidate zone to ensure it's obstacle-free.
    4. Filter by minimum size and remove overlapping zones.
    
    This approach finds many more zones than simple subdivision by exploring all possible
    rectangular zones that can be formed from obstacle boundaries.
    
    Args:
        obstacle_boxes: List of Rectangle objects representing obstacles.
        playground: The playground boundary as a Rectangle. If None, computed automatically.
        playground_margin: Margin when auto-computing playground. Default is 1.0m.
        min_zone_size: Minimum dimension (width and height) of a free zone. Default is 0.5m.
        max_zones: Maximum number of free zones to return. Default is None (no limit).
        clearance: Clearance margin to shrink free zones by (for safety). Default is 0.3m.
    
    Returns:
        Tuple of (list of FreeZone objects sorted by area descending, playground Rectangle).
        All returned zones are guaranteed to be non-overlapping with obstacles and each other.
    
    Example:
        >>> obstacles = [
        ...     Rectangle(x_min=2.5, y_min=-0.5, x_max=3.5, y_max=0.5),
        ...     Rectangle(x_min=5.5, y_min=1.5, x_max=6.5, y_max=2.5),
        ... ]
        >>> free_zones, playground = find_free_zones(obstacles)
        >>> print(f"Found {len(free_zones)} non-overlapping free zones")
    """
    obstacle_boxes = obstacle_boxes or []
    playground = playground or compute_bounding_playground(obstacle_boxes, margin=playground_margin)
    
    # Collect all boundary coordinates
    x_coords = sorted({playground.x_min, playground.x_max} | {obs.x_min for obs in obstacle_boxes} | {obs.x_max for obs in obstacle_boxes})
    y_coords = sorted({playground.y_min, playground.y_max} | {obs.y_min for obs in obstacle_boxes} | {obs.y_max for obs in obstacle_boxes})
    
    # Generate candidate zones from all boundary combinations
    candidate_zones = []
    for i, x1 in enumerate(x_coords):
        for x2 in x_coords[i+1:]:
            for j, y1 in enumerate(y_coords):
                for y2 in y_coords[j+1:]:
                    candidate = FreeZone(x1, y1, x2, y2)
                    if (candidate.width >= min_zone_size and candidate.height >= min_zone_size and
                        candidate.x1 >= playground.x_min and candidate.x2 <= playground.x_max and
                        candidate.y1 >= playground.y_min and candidate.y2 <= playground.y_max and
                        _zone_is_obstacle_free(candidate, obstacle_boxes)):
                        candidate_zones.append(candidate)
    
    candidate_zones.sort(key=lambda z: z.area, reverse=True)
    free_zones = _remove_overlapping_zones(candidate_zones)
    
    # Shrink zones by clearance for safety margins
    free_zones = [zone.shrink(clearance) for zone in free_zones]
    return (free_zones[:max_zones] if max_zones else free_zones, playground)

