from dataclasses import dataclass
import struct
from typing import ClassVar, Dict, Optional
import array

@dataclass(slots=True, frozen=True)
class Point3D:
    """
    Memory-efficient 3D point class optimized for terrain modeling with millions of points.
    Uses __slots__ and frozen dataclass for optimal memory usage and data integrity.
    """
    # Instance attributes
    id: int
    x: float
    y: float
    z: float
    
    def to_bytes(self) -> bytes:
        """
        Serialize the point to bytes for efficient storage.
        Format: id (8 bytes) + x,y,z coordinates (8 bytes each) = 32 bytes total
        """
        return struct.pack('!Qddd', self.id, self.x, self.y, self.z)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Point3D':
        """
        Deserialize bytes back into a Point3D object.
        """
        id_, x, y, z = struct.unpack('!Qddd', data)
        return cls(id=id_, x=x, y=y, z=z)
    
    def __hash__(self):
        """Enable using points as dictionary keys or set members."""
        return hash(self.id)
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate Euclidean distance to another point."""
        return ((self.x - other.x) ** 2 + 
                (self.y - other.y) ** 2 + 
                (self.z - other.z) ** 2) ** 0.5

class PointCloud:
    """
    Efficient container for managing large collections of Point3D objects.
    Uses array-based storage for memory efficiency.
    """
    def __init__(self):
        self._ids = array.array('Q')  # unsigned long long for IDs
        self._coords = array.array('d')  # double precision floats for coordinates
        self._point_cache = {}  # Limited cache for frequently accessed points
        
    def add_point(self, point: Point3D) -> None:
        """Add a point to the collection."""
        self._ids.append(point.id)
        self._coords.extend([point.x, point.y, point.z])
        
    def get_point(self, index: int) -> Point3D:
        """Get point by index."""
        if index >= len(self._ids):
            raise IndexError("Point index out of range")
        base = index * 3
        return Point3D(
            id=self._ids[index],
            x=self._coords[base],
            y=self._coords[base + 1],
            z=self._coords[base + 2]
        )
    
    def get_point_by_id(self, point_id: int) -> Optional[Point3D]:
        """Get point by ID. Less efficient than get_point(index)."""
        try:
            index = self._ids.index(point_id)
            return self.get_point(index)
        except ValueError:
            return None
            
    def __len__(self) -> int:
        """Return number of points in collection."""
        return len(self._ids)
