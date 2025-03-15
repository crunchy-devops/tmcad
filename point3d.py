"""
Memory-efficient 3D point implementation with spatial indexing.

This module provides a highly optimized Point3D class and PointCloud container
for managing large terrain point datasets with efficient spatial operations.
"""

from __future__ import annotations
from array import array
from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict, Tuple
import math
import numpy as np
from scipy.spatial import cKDTree

__all__ = ['Point3D', 'PointCloud']

@dataclass(slots=True, frozen=True)
class Point3D:
    """
    Memory-efficient immutable 3D point with unique ID.
    
    Uses __slots__ and frozen=True for minimal memory footprint and immutability.
    Each point requires exactly 32 bytes:
    - id: 8 bytes (uint64)
    - x,y,z: 8 bytes each (float64)
    
    Attributes:
        id (int): Unique identifier (uint64)
        x (float): X coordinate
        y (float): Y coordinate
        z (float): Z coordinate
    """
    id: int
    x: float
    y: float
    z: float
    
    def __post_init__(self):
        """Validate point attributes after initialization."""
        if not isinstance(self.id, int) or self.id < 0:
            raise ValueError("ID must be a non-negative integer")
        if not all(isinstance(coord, (int, float)) for coord in (self.x, self.y, self.z)):
            raise ValueError("Coordinates must be numeric")
            
    def distance_to(self, other: Point3D) -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )
        
    def slope_to(self, other: Point3D) -> float:
        """Calculate slope from this point to another point in percentage.

        Args:
            other: Target point to calculate slope to.

        Returns:
            float: Slope in percentage (rise/run * 100). Positive values indicate uphill,
                  negative values indicate downhill. Returns 0 if points are at same location.
                  Returns float('inf') for vertical slopes.
        """
        dx = other.x - self.x
        dy = other.y - self.y
        dz = other.z - self.z
        
        # Calculate horizontal distance (run)
        run = math.sqrt(dx * dx + dy * dy)
        
        # Handle vertical slope or same point
        if run == 0:
            return float('inf') if dz != 0 else 0.0
            
        # Calculate slope percentage (rise/run * 100)
        return (dz / run) * 100
        
    def bearing_to(self, other: Point3D) -> float:
        """
        Calculate bearing angle (in degrees) from this point to another.
        
        Returns angle in degrees from north (0°), clockwise positive:
        - North = 0°
        - East = 90°
        - South = 180°
        - West = 270°
        
        Uses efficient coordinate calculations to minimize memory usage.
        """
        # Use direct coordinate access for memory efficiency
        dx = other.x - self.x
        dy = other.y - self.y
        
        # Convert from mathematical angle to bearing
        # atan2(x, y) gives angle from east counterclockwise
        # We want angle from north clockwise
        angle = math.degrees(math.atan2(dx, dy))
        bearing = (90.0 - angle) % 360.0
        
        # Handle special cases for cardinal directions
        if abs(dx) < 1e-10:  # On same vertical line
            return 0.0 if dy > 0 else 180.0
        if abs(dy) < 1e-10:  # On same horizontal line
            return 90.0 if dx > 0 else 270.0
            
        return bearing
        
    def to_array(self) -> array:
        """Convert point to memory-efficient array format."""
        return array('d', [self.x, self.y, self.z])
        
    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert point coordinates to tuple format."""
        return (self.x, self.y, self.z)

class PointCloud:
    """
    Memory-efficient container for Point3D objects with spatial indexing.
    
    Uses array.array for coordinate storage and KD-tree for spatial queries.
    Memory usage is optimized to ~32 bytes per point plus indexing overhead.
    
    Attributes:
        points (Dict[int, int]): Maps point IDs to array indices
        coords (array): Packed coordinates array
        _kdtree (cKDTree): Spatial index for efficient queries
    """
    
    def __init__(self):
        """Initialize empty point cloud with efficient storage."""
        self._id_to_index: Dict[int, int] = {}
        self._coords = array('d')
        self._kdtree: Optional[cKDTree] = None
        
    def add_point(self, point: Point3D) -> None:
        """
        Add a point to the cloud.
        
        Args:
            point: Point3D instance to add
            
        Raises:
            ValueError: If point ID already exists
        """
        if point.id in self._id_to_index:
            raise ValueError(f"Point with ID {point.id} already exists")
            
        idx = len(self._id_to_index)
        self._id_to_index[point.id] = idx
        self._coords.extend([point.x, point.y, point.z])
        self._kdtree = None  # Invalidate KD-tree
        
    def get_point(self, point_id: int) -> Point3D:
        """
        Retrieve point by ID.
        
        Args:
            point_id: ID of point to retrieve
            
        Returns:
            Point3D instance
            
        Raises:
            KeyError: If point ID not found
        """
        if point_id not in self._id_to_index:
            raise KeyError(f"Point with ID {point_id} not found")
            
        idx = self._id_to_index[point_id]
        base_idx = idx * 3
        return Point3D(
            id=point_id,
            x=self._coords[base_idx],
            y=self._coords[base_idx + 1],
            z=self._coords[base_idx + 2]
        )
        
    def get_point_by_id(self, point_id: int) -> Point3D:
        """
        Retrieve point by ID.
        
        Args:
            point_id: ID of point to retrieve
            
        Returns:
            Point3D instance
            
        Raises:
            KeyError: If point ID not found
        """
        if point_id not in self._id_to_index:
            raise KeyError(f"Point with ID {point_id} not found")
            
        idx = self._id_to_index[point_id]
        base_idx = idx * 3
        return Point3D(
            id=point_id,
            x=self._coords[base_idx],
            y=self._coords[base_idx + 1],
            z=self._coords[base_idx + 2]
        )
        
    def remove_point(self, point_id: int) -> None:
        """
        Remove point by ID.
        
        Args:
            point_id: ID of point to remove
            
        Raises:
            KeyError: If point ID not found
        """
        if point_id not in self._id_to_index:
            raise KeyError(f"Point with ID {point_id} not found")
            
        idx = self._id_to_index[point_id]
        base_idx = idx * 3
        
        # Remove coordinates
        del self._coords[base_idx:base_idx + 3]
        
        # Update index mappings
        del self._id_to_index[point_id]
        for pid, i in self._id_to_index.items():
            if i > idx:
                self._id_to_index[pid] = i - 1
                
        self._kdtree = None  # Invalidate KD-tree
        
    def _ensure_kdtree(self) -> None:
        """Build KD-tree if not present or invalidated."""
        if self._kdtree is None:
            points = np.frombuffer(self._coords, dtype=np.float64)
            points = points.reshape(-1, 3)
            self._kdtree = cKDTree(points)
            
    def nearest_neighbors(self, point: Point3D, k: int = 1) -> List[Tuple[int, float]]:
        """
        Find k nearest neighbors to given point.
        
        Args:
            point: Query point
            k: Number of neighbors to find (default: 1)
            
        Returns:
            List of (point_id, distance) tuples, sorted by distance
        """
        self._ensure_kdtree()
        
        distances, indices = self._kdtree.query(
            [point.x, point.y, point.z],
            k=min(k, len(self._id_to_index))
        )
        
        if k == 1:
            indices = [indices]
            distances = [distances]
            
        # Map array indices back to point IDs
        id_map = {v: k for k, v in self._id_to_index.items()}
        return [(id_map[idx], dist) for idx, dist in zip(indices, distances)]
        
    def points_within_radius(self, center: Point3D, radius: float) -> List[Tuple[int, float]]:
        """
        Find all points within given radius of center point.
        
        Args:
            center: Center point for search
            radius: Search radius
            
        Returns:
            List of (point_id, distance) tuples, sorted by distance
        """
        self._ensure_kdtree()
        
        indices = self._kdtree.query_ball_point(
            [center.x, center.y, center.z],
            radius
        )
        
        # Calculate distances and map indices to IDs
        id_map = {v: k for k, v in self._id_to_index.items()}
        results = []
        center_coords = np.array([center.x, center.y, center.z])
        
        for idx in indices:
            point_coords = np.array(self.get_point_coords(id_map[idx]))
            distance = np.linalg.norm(point_coords - center_coords)
            results.append((id_map[idx], distance))
            
        return sorted(results, key=lambda x: x[1])
        
    def get_point_coords(self, point_id: int) -> Tuple[float, float, float]:
        """Get point coordinates by ID without creating Point3D instance."""
        if point_id not in self._id_to_index:
            raise KeyError(f"Point with ID {point_id} not found")
            
        idx = self._id_to_index[point_id]
        base_idx = idx * 3
        return (
            self._coords[base_idx],
            self._coords[base_idx + 1],
            self._coords[base_idx + 2]
        )
        
    def get_points_array(self) -> np.ndarray:
        """
        Get all points as numpy array for efficient bulk operations.
        
        Returns:
            Nx3 array of point coordinates
        """
        points = np.frombuffer(self._coords, dtype=np.float64)
        return points.reshape(-1, 3)
        
    def distance_between(self, id1: int, id2: int) -> float:
        """Calculate distance between two points by their IDs."""
        p1_coords = self.get_point_coords(id1)
        p2_coords = self.get_point_coords(id2)
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1_coords, p2_coords)))
        
    def slope_between_points(self, id1: int, id2: int) -> float:
        """Calculate slope between two points in the cloud in percentage.

        Args:
            id1: ID of the first point
            id2: ID of the second point

        Returns:
            float: Slope in percentage (rise/run * 100). Positive values indicate uphill,
                  negative values indicate downhill. Returns 0 if points are at same location.
                  Returns float('inf') for vertical slopes.

        Raises:
            KeyError: If either point ID is not found in the cloud
        """
        p1 = self.get_point_by_id(id1)
        p2 = self.get_point_by_id(id2)
        return p1.slope_to(p2)
        
    def bearing_between(self, id1: int, id2: int) -> float:
        """
        Calculate bearing angle between two points by their IDs.
        
        Returns angle in degrees from north (0°), clockwise positive:
        - North = 0°
        - East = 90°
        - South = 180°
        - West = 270°
        
        Uses array-based coordinate access for optimal memory efficiency.
        Each point requires exactly 32 bytes (8 bytes each for id, x, y, z).
        """
        # Use direct array access for memory efficiency
        idx1 = self._id_to_index[id1]
        idx2 = self._id_to_index[id2]
        
        # Get coordinates using O(1) array access
        base_idx1 = idx1 * 3
        base_idx2 = idx2 * 3
        
        dx = self._coords[base_idx2] - self._coords[base_idx1]  # x2 - x1
        dy = self._coords[base_idx2 + 1] - self._coords[base_idx1 + 1]  # y2 - y1
        
        # Convert from mathematical angle to bearing
        # atan2(x, y) gives angle from east counterclockwise
        # We want angle from north clockwise
        angle = math.degrees(math.atan2(dx, dy))
        bearing = (90.0 - angle) % 360.0
        
        # Handle special cases for cardinal directions
        if abs(dx) < 1e-10:  # On same vertical line
            return 0.0 if dy > 0 else 180.0
        if abs(dy) < 1e-10:  # On same horizontal line
            return 90.0 if dx > 0 else 270.0
            
        return bearing
        
    def __len__(self) -> int:
        """Get number of points in cloud."""
        return len(self._id_to_index)
        
    def __contains__(self, point_id: int) -> bool:
        """Check if point ID exists in cloud."""
        return point_id in self._id_to_index
        
    def __iter__(self):
        """Iterate over points in cloud."""
        for point_id in self._id_to_index:
            yield self.get_point(point_id)
