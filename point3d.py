"""Memory-efficient 3D point implementation using array.array.

This module provides optimized Point3D and PointCloud classes with memory-efficient
storage and fast geometric operations. The implementation uses array.array for minimal
memory footprint and scipy for efficient spatial indexing.

Memory Usage:
- Point3D: 16 bytes (4 bytes for id, 4 bytes each for x, y, z)
- PointCloud: ~16 bytes per point at scale
"""

__all__ = ['Point3D', 'PointCloud']

import math
import array
import numpy as np
from scipy.spatial import cKDTree
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple

@dataclass(frozen=True, slots=True)
class Point3D:
    """Memory-efficient immutable 3D point representation."""
    id: int
    x: float
    y: float
    z: float
    
    def __init__(self, id: int, x: float, y: float, z: float) -> None:
        """Initialize point with validation."""
        # Validate inputs before setting
        if not isinstance(id, int):
            raise ValueError("ID must be an integer")
        if id < 0:
            raise ValueError("ID must be non-negative")
        if not all(isinstance(v, (int, float)) for v in (x, y, z)):
            raise ValueError("Coordinates must be numeric values")
        
        # Use object.__setattr__ to set values since class is frozen
        object.__setattr__(self, 'id', id)
        object.__setattr__(self, 'x', float(x))
        object.__setattr__(self, 'y', float(y))
        object.__setattr__(self, 'z', float(z))
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate Euclidean distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    
    def slope_to(self, other: 'Point3D') -> float:
        """Calculate slope to another point in percent."""
        run = math.sqrt(
            (other.x - self.x) * (other.x - self.x) +
            (other.y - self.y) * (other.y - self.y)
        )
        if run == 0:
            return float('inf') if other.z > self.z else float('-inf')
        
        rise = other.z - self.z
        return (rise / run) * 100.0
    
    def bearing_to(self, other: 'Point3D') -> float:
        """Calculate bearing to another point in degrees."""
        dx = other.x - self.x
        dy = other.y - self.y
        angle = math.atan2(dy, dx) * 180.0 / math.pi
        bearing = 90.0 - angle
        
        while bearing < 0:
            bearing += 360.0
        while bearing >= 360:
            bearing -= 360.0
        
        return bearing


class PointCloud:
    """Memory-efficient collection of Point3D instances with spatial indexing."""
    
    __slots__ = ('_ids', '_coords', '_id_to_index', '_kdtree', '_size')
    
    def __init__(self) -> None:
        """Initialize an empty point cloud."""
        self._ids = array.array('l')     # signed long (4 bytes)
        self._coords = array.array('f')  # float (4 bytes)
        self._id_to_index: Dict[int, int] = {}
        self._kdtree: Optional[cKDTree] = None
        self._size: int = 0
    
    def add_point(self, point: Point3D) -> None:
        """Add a single point to the cloud."""
        # Validate point
        if point.id < 0:
            raise ValueError("Point ID must be non-negative")
        if point.id in self._id_to_index:
            raise ValueError(f"Point ID {point.id} already exists")
        
        # Add point data
        self._ids.append(point.id)
        self._coords.extend([point.x, point.y, point.z])
        self._id_to_index[point.id] = self._size
        self._size += 1
        self._kdtree = None
    
    def add_points(self, points: List[Point3D]) -> None:
        """Add multiple points to the cloud efficiently."""
        if not points:
            return
        
        # Validate points first to avoid partial updates
        for point in points:
            if point.id < 0:
                raise ValueError("Point ID must be non-negative")
            if point.id in self._id_to_index:
                raise ValueError(f"Point ID {point.id} already exists")
        
        # Add points in batch
        base_idx = self._size
        for i, point in enumerate(points):
            self._ids.append(point.id)
            self._coords.extend([point.x, point.y, point.z])
            self._id_to_index[point.id] = base_idx + i
        
        self._size += len(points)
        self._kdtree = None
    
    def get_point(self, point_id: int) -> Point3D:
        """Retrieve a point by its ID."""
        if point_id not in self._id_to_index:
            raise KeyError(f"Point ID {point_id} not found")
        
        idx = self._id_to_index[point_id]
        base = idx * 3
        return Point3D(
            self._ids[idx],
            self._coords[base],
            self._coords[base + 1],
            self._coords[base + 2]
        )
    
    def _ensure_kdtree(self) -> None:
        """Ensure KD-tree is built for spatial queries."""
        if self._kdtree is None and self._size > 0:
            # Create view of coordinates as numpy array
            coords = np.frombuffer(
                self._coords,
                dtype=np.float32,
                count=self._size * 3
            ).reshape(-1, 3)
            
            # Build KD-tree with minimal memory overhead
            self._kdtree = cKDTree(
                coords,
                leafsize=16,
                compact_nodes=True,
                balanced_tree=True,
                copy_data=False
            )
    
    def nearest_neighbors(self, point: Point3D, k: int = 1) -> List[Point3D]:
        """Find k nearest neighbors to the given point."""
        if self._size == 0:
            return []
        
        if k > self._size:
            k = self._size
        
        self._ensure_kdtree()
        
        # Query KD-tree with point coordinates
        coords = np.array([point.x, point.y, point.z], dtype=np.float32)
        distances, indices = self._kdtree.query(coords, k=k)
        
        # Convert indices to points
        indices = np.atleast_1d(indices)  # Ensure 1D array
        return [
            Point3D(
                self._ids[idx],
                self._coords[idx * 3],
                self._coords[idx * 3 + 1],
                self._coords[idx * 3 + 2]
            )
            for idx in indices
        ]
    
    def distance(self, id1: int, id2: int) -> float:
        """Calculate distance between two points by their IDs."""
        p1 = self.get_point(id1)
        p2 = self.get_point(id2)
        return p1.distance_to(p2)
    
    def slope(self, id1: int, id2: int) -> float:
        """Calculate slope between two points by their IDs."""
        p1 = self.get_point(id1)
        p2 = self.get_point(id2)
        return p1.slope_to(p2)
    
    def bearing(self, id1: int, id2: int) -> float:
        """Calculate bearing between two points by their IDs."""
        p1 = self.get_point(id1)
        p2 = self.get_point(id2)
        return p1.bearing_to(p2)
    
    @property
    def count(self) -> int:
        """Get the number of points in the cloud."""
        return self._size
