from __future__ import annotations
from dataclasses import dataclass
import array
import struct
from typing import Dict, List, Optional, Tuple
import numpy as np

@dataclass(slots=True, frozen=True)
class Point3D:
    """
    Immutable 3D point with fixed memory footprint.
    Uses slots and frozen to prevent dynamic attributes and modifications.
    Total memory per point: 32 bytes (8 bytes each for id, x, y, z)
    """
    id: int
    x: float
    y: float
    z: float

    def to_array(self) -> array.array:
        """Convert point to array format for efficient storage."""
        return array.array('d', [self.x, self.y, self.z])

    def to_bytes(self) -> bytes:
        """Convert point to binary format for serialization."""
        return struct.pack('Qddd', self.id, self.x, self.y, self.z)

    @classmethod
    def from_bytes(cls, data: bytes) -> Point3D:
        """Create point from binary format."""
        id_, x, y, z = struct.unpack('Qddd', data)
        return cls(id=id_, x=x, y=y, z=z)

class PointCloud:
    """
    Memory-efficient point cloud storage using array-based implementation.
    Uses array.array for coordinate storage to minimize memory usage.
    Provides O(1) index-based access and efficient bulk operations.
    """
    def __init__(self):
        """Initialize empty point cloud."""
        self._coords = array.array('d')  # Store x,y,z coordinates
        self._ids = array.array('Q')  # Store point IDs
        self._id_to_index: Dict[int, int] = {}  # Map point ID to array index
        self._cached_points: Dict[int, Point3D] = {}  # Cache for frequently accessed points

    def add_point(self, point: Point3D) -> None:
        """Add point to cloud. O(1) operation."""
        if point.id in self._id_to_index:
            raise ValueError(f"Point with ID {point.id} already exists")
            
        # Add coordinates to array
        self._coords.extend([point.x, point.y, point.z])
        self._ids.append(point.id)
        
        # Update ID mapping
        self._id_to_index[point.id] = len(self._ids) - 1
        
        # Clear cached numpy array
        self._cached_array = None

    def get_point(self, point_id: int) -> Optional[Point3D]:
        """
        Get point by ID. 
        Uses caching for frequently accessed points.
        O(1) operation with cache hit, O(1) without cache.
        """
        # Check cache first
        if point_id in self._cached_points:
            return self._cached_points[point_id]
            
        # Get from storage
        if point_id not in self._id_to_index:
            return None
            
        idx = self._id_to_index[point_id]
        base_idx = idx * 3
        point = Point3D(
            id=self._ids[idx],
            x=self._coords[base_idx],
            y=self._coords[base_idx + 1],
            z=self._coords[base_idx + 2]
        )
        
        # Add to cache
        self._cached_points[point_id] = point
        
        # Limit cache size
        if len(self._cached_points) > 1000:
            # Remove oldest entries
            remove_ids = list(self._cached_points.keys())[:-500]
            for rid in remove_ids:
                del self._cached_points[rid]
        
        return point

    def get_points_array(self) -> np.ndarray:
        """
        Get points as numpy array for efficient computation.
        Shape: (n_points, 3) for x,y,z coordinates.
        """
        if not self._coords:
            return np.zeros((0, 3))
        return np.array(self._coords).reshape(-1, 3)

    def get_all_points(self) -> List[Point3D]:
        """Get all points as list. Use sparingly due to memory impact."""
        points = []
        for i in range(len(self._ids)):
            base_idx = i * 3
            points.append(Point3D(
                id=self._ids[i],
                x=self._coords[base_idx],
                y=self._coords[base_idx + 1],
                z=self._coords[base_idx + 2]
            ))
        return points

    def __len__(self) -> int:
        """Get number of points in cloud."""
        return len(self._ids)

    def __iter__(self):
        """Iterate through points. Memory-efficient implementation."""
        for i in range(len(self._ids)):
            base_idx = i * 3
            yield Point3D(
                id=self._ids[i],
                x=self._coords[base_idx],
                y=self._coords[base_idx + 1],
                z=self._coords[base_idx + 2]
            )

    def to_bytes(self) -> bytes:
        """Convert point cloud to binary format for serialization."""
        # Format: [count(Q)][id1(Q)x1(d)y1(d)z1(d)][id2(Q)x2(d)y2(d)z2(d)]...
        count = len(self._ids)
        data = struct.pack('Q', count)
        for i in range(count):
            base_idx = i * 3
            data += struct.pack('Qddd',
                self._ids[i],
                self._coords[base_idx],
                self._coords[base_idx + 1],
                self._coords[base_idx + 2]
            )
        return data

    @classmethod
    def from_bytes(cls, data: bytes) -> PointCloud:
        """Create point cloud from binary format."""
        cloud = cls()
        count = struct.unpack('Q', data[:8])[0]
        pos = 8
        
        # Pre-allocate arrays
        cloud._coords = array.array('d', [0.0] * (count * 3))
        cloud._ids = array.array('Q', [0] * count)
        
        # Read points in bulk
        for i in range(count):
            id_, x, y, z = struct.unpack('Qddd', data[pos:pos+32])
            base_idx = i * 3
            cloud._ids[i] = id_
            cloud._coords[base_idx:base_idx+3] = [x, y, z]
            cloud._id_to_index[id_] = i
            pos += 32
            
        return cloud
