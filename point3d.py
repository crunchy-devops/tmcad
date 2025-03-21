"""Memory-efficient 3D point cloud implementation."""
from dataclasses import dataclass
import struct
import array
import numpy as np
from scipy.spatial import cKDTree

@dataclass(slots=True, frozen=True)
class Point3D:
    """
    Memory-efficient 3D point class optimized for terrain modeling.
    Uses __slots__ and frozen dataclass for optimal memory usage.
    Each point uses exactly 32 bytes:
    - id: 8 bytes (uint64)
    - x,y,z: 8 bytes each (float64)
    """
    id: int
    x: float
    y: float
    z: float
    
    def to_bytes(self) -> bytes:
        """Serialize point to 32 bytes."""
        return struct.pack('!Qddd', self.id, self.x, self.y, self.z)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Point3D':
        """Deserialize from 32 bytes."""
        id_, x, y, z = struct.unpack('!Qddd', data)
        return cls(id=id_, x=x, y=y, z=z)
    
    def __hash__(self):
        """Enable using points as dictionary keys."""
        return hash(self.id)
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate Euclidean distance to another point."""
        return ((self.x - other.x) ** 2 + 
                (self.y - other.y) ** 2 + 
                (self.z - other.z) ** 2) ** 0.5

class PointCloud:
    """
    Memory-efficient container for Point3D objects.
    Uses array-based storage with contiguous memory layout:
    - _ids: array of uint64 (8 bytes per ID)
    - _coords: array of float64 (24 bytes per point: 8 each for x,y,z)
    Total memory per point: 32 bytes
    """
    def __init__(self):
        """Initialize empty arrays for IDs and coordinates."""
        self._ids = array.array('Q')  # unsigned long long (uint64)
        self._coords = array.array('d', [0.0] * 3)  # double precision float (float64)
        self._kdtree = None
        self._kdtree_dirty = True
    
    @property
    def count(self) -> int:
        """Get number of points."""
        return len(self._ids)
    
    def add_point(self, point: Point3D) -> None:
        """Add a single point."""
        self._ids.append(point.id)
        self._coords.extend([point.x, point.y, point.z])
        self._kdtree_dirty = True
    
    def add_points(self, points) -> None:
        """Add multiple points efficiently."""
        for point in points:
            self._ids.append(point.id)
            self._coords.extend([point.x, point.y, point.z])
        self._kdtree_dirty = True
    
    def get_point(self, index: int) -> Point3D:
        """Get point by index (O(1) access)."""
        if not 0 <= index < self.count:
            raise IndexError("Point index out of range")
        base = index * 3
        return Point3D(
            id=self._ids[index],
            x=self._coords[base],
            y=self._coords[base + 1],
            z=self._coords[base + 2]
        )
    
    def get_point_by_id(self, point_id: int) -> Point3D:
        """Get point by ID (O(n) access)."""
        try:
            index = self._ids.index(point_id)
            return self.get_point(index)
        except ValueError:
            return None
    
    def _ensure_kdtree(self) -> None:
        """Build KD-tree if needed."""
        if self._kdtree_dirty or self._kdtree is None:
            coords = np.frombuffer(self._coords, dtype=np.float64)
            coords = coords.reshape(-1, 3)
            self._kdtree = cKDTree(coords)
            self._kdtree_dirty = False
    
    def nearest_neighbors(self, point: Point3D, k: int = 1) -> list:
        """Find k nearest neighbors."""
        if self.count == 0:
            return []
        
        self._ensure_kdtree()
        query = np.array([[point.x, point.y, point.z]])
        distances, indices = self._kdtree.query(query, k=min(k, self.count))
        
        # Handle both single and multiple neighbor cases
        if k == 1:
            indices = [indices]
        
        return [self.get_point(i) for i in indices]
