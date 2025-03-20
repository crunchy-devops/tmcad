# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

"""High-performance 3D point implementation using Cython.

This module provides optimized Point3D and PointCloud classes with memory-efficient
storage and fast geometric operations. The implementation uses Cython for performance
and includes KD-tree spatial indexing for efficient nearest neighbor searches.
"""

import cython
from libc.math cimport sqrt, atan2, M_PI
from libc.stdlib cimport malloc, free
import numpy as np
cimport numpy as np
from scipy.spatial import cKDTree

# Type definitions for numpy arrays
np.import_array()
DTYPE = np.float32  # Use float32 for KD-tree operations
ITYPE = np.uint32   # Use uint32 for IDs
QTYPE = np.int16    # Use int16 for quantized coordinates

ctypedef np.float32_t DTYPE_t
ctypedef np.uint32_t ITYPE_t
ctypedef np.int16_t QTYPE_t

cdef class Point3D:
    """Memory-efficient immutable 3D point representation.
    
    Attributes:
        id (int): Unique identifier for the point
        x (float): X coordinate
        y (float): Y coordinate
        z (float): Z coordinate
    """
    cdef readonly unsigned int id
    cdef readonly float x, y, z
    
    def __init__(self, unsigned int id, float x, float y, float z):
        """Initialize Point3D with ID and coordinates.
        
        Args:
            id (int): Unique identifier
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
        """
        self.id = id
        self.x = x
        self.y = y
        self.z = z
    
    def __repr__(self):
        return f"Point3D(id={self.id}, x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f})"
    
    cpdef float distance_to(self, Point3D other):
        """Calculate Euclidean distance to another point.
        
        Args:
            other (Point3D): Target point
            
        Returns:
            float: Euclidean distance between points
        """
        cdef float dx = self.x - other.x
        cdef float dy = self.y - other.y
        cdef float dz = self.z - other.z
        return sqrt(dx * dx + dy * dy + dz * dz)
    
    cpdef float slope_to(self, Point3D other):
        """Calculate slope to another point in percentage.
        
        Args:
            other (Point3D): Target point
            
        Returns:
            float: Slope in percentage, infinity for vertical slopes
        """
        cdef float run = sqrt(
            (other.x - self.x) * (other.x - self.x) +
            (other.y - self.y) * (other.y - self.y)
        )
        if run == 0:
            return float('inf') if other.z > self.z else float('-inf')
        
        cdef float rise = other.z - self.z
        return (rise / run) * 100.0
    
    cpdef float bearing_to(self, Point3D other):
        """Calculate bearing angle to another point in degrees.
        
        Args:
            other (Point3D): Target point
            
        Returns:
            float: Bearing angle in degrees (0-360)
        """
        cdef float dx = other.x - self.x
        cdef float dy = other.y - self.y
        cdef float angle = atan2(dy, dx) * 180.0 / M_PI
        cdef float bearing = 90.0 - angle
        
        # Normalize to 0-360 range
        while bearing < 0:
            bearing += 360.0
        while bearing >= 360:
            bearing -= 360.0
        
        return bearing


cdef class PointCloud:
    """Memory-efficient collection of Point3D instances with spatial indexing.
    
    Uses quantized coordinates and efficient storage:
    - id: uint32 (4 bytes)
    - x,y,z: int16 (2 bytes × 3)
    Total: 10 bytes per point
    """
    cdef readonly dict _id_to_index
    cdef readonly np.ndarray _coords
    cdef readonly np.ndarray _ids
    cdef readonly object _kdtree
    cdef readonly Py_ssize_t _capacity
    cdef readonly Py_ssize_t _size
    cdef readonly float _scale
    cdef readonly float _min_x, _min_y, _min_z
    cdef readonly float _max_x, _max_y, _max_z
    
    def __init__(self, Py_ssize_t initial_capacity=1024):
        """Initialize empty point cloud.
        
        Args:
            initial_capacity (int): Initial capacity for arrays
        """
        self._id_to_index = {}
        self._capacity = initial_capacity
        self._size = 0
        self._scale = 100.0  # Store coordinates with 0.01 precision
        
        # Initialize bounds
        self._min_x = self._min_y = self._min_z = float('inf')
        self._max_x = self._max_y = self._max_z = float('-inf')
        
        # Pre-allocate arrays with efficient types
        self._coords = np.zeros((initial_capacity, 3), dtype=QTYPE)
        self._ids = np.zeros(initial_capacity, dtype=ITYPE)
        self._kdtree = None
    
    cdef void _resize(self, Py_ssize_t new_capacity):
        """Resize internal arrays."""
        cdef np.ndarray new_coords = np.zeros((new_capacity, 3), dtype=QTYPE)
        cdef np.ndarray new_ids = np.zeros(new_capacity, dtype=ITYPE)
        
        # Copy existing data
        new_coords[:self._size] = self._coords[:self._size]
        new_ids[:self._size] = self._ids[:self._size]
        
        # Update arrays
        self._coords = new_coords
        self._ids = new_ids
        self._capacity = new_capacity
    
    cdef tuple _quantize(self, float x, float y, float z):
        """Quantize coordinates to int16."""
        # Update bounds
        self._min_x = min(self._min_x, x)
        self._min_y = min(self._min_y, y)
        self._min_z = min(self._min_z, z)
        self._max_x = max(self._max_x, x)
        self._max_y = max(self._max_y, y)
        self._max_z = max(self._max_z, z)
        
        # Normalize to [0, 1] range
        cdef float nx = (x - self._min_x) / (self._max_x - self._min_x) if self._max_x > self._min_x else 0
        cdef float ny = (y - self._min_y) / (self._max_y - self._min_y) if self._max_y > self._min_y else 0
        cdef float nz = (z - self._min_z) / (self._max_z - self._min_z) if self._max_z > self._min_z else 0
        
        # Scale to int16 range
        return (
            <short>(nx * 32767),
            <short>(ny * 32767),
            <short>(nz * 32767)
        )
    
    cdef tuple _dequantize(self, short qx, short qy, short qz):
        """Dequantize coordinates from int16."""
        # Convert back to [0, 1] range
        cdef float nx = qx / 32767.0
        cdef float ny = qy / 32767.0
        cdef float nz = qz / 32767.0
        
        # Scale back to original range
        return (
            nx * (self._max_x - self._min_x) + self._min_x,
            ny * (self._max_y - self._min_y) + self._min_y,
            nz * (self._max_z - self._min_z) + self._min_z
        )
    
    cpdef void add_point(self, Point3D point):
        """Add a single point to the cloud.
        
        Args:
            point (Point3D): Point to add
        """
        # Resize if needed
        if self._size >= self._capacity:
            self._resize(self._capacity * 2)
        
        # Quantize coordinates
        cdef short qx, qy, qz
        qx, qy, qz = self._quantize(point.x, point.y, point.z)
        
        # Add point
        self._id_to_index[point.id] = self._size
        self._ids[self._size] = point.id
        self._coords[self._size, 0] = qx
        self._coords[self._size, 1] = qy
        self._coords[self._size, 2] = qz
        self._size += 1
        
        # Invalidate KD-tree
        self._kdtree = None
    
    def add_points(self, points):
        """Add multiple points efficiently.
        
        Args:
            points (list[Point3D]): Points to add
        """
        cdef Py_ssize_t n_points = len(points)
        cdef Py_ssize_t new_size = self._size + n_points
        
        # Resize if needed
        while new_size > self._capacity:
            self._resize(self._capacity * 2)
        
        # Add points in batch
        cdef Point3D point
        cdef Py_ssize_t i
        cdef short qx, qy, qz
        for i, point in enumerate(points):
            # Update bounds and quantize
            qx, qy, qz = self._quantize(point.x, point.y, point.z)
            
            # Store point
            idx = self._size + i
            self._id_to_index[point.id] = idx
            self._ids[idx] = point.id
            self._coords[idx, 0] = qx
            self._coords[idx, 1] = qy
            self._coords[idx, 2] = qz
        
        self._size = new_size
        
        # Invalidate KD-tree
        self._kdtree = None
    
    cpdef Point3D get_point(self, unsigned int point_id):
        """Retrieve a point by its ID.
        
        Args:
            point_id (int): ID of the point to retrieve
            
        Returns:
            Point3D: Retrieved point
            
        Raises:
            KeyError: If point_id is not found
        """
        if point_id not in self._id_to_index:
            raise KeyError(f"Point ID {point_id} not found")
        
        cdef Py_ssize_t idx = self._id_to_index[point_id]
        cdef short qx = self._coords[idx, 0]
        cdef short qy = self._coords[idx, 1]
        cdef short qz = self._coords[idx, 2]
        
        # Dequantize coordinates
        cdef float x, y, z
        x, y, z = self._dequantize(qx, qy, qz)
        
        return Point3D(
            self._ids[idx],
            x, y, z
        )
    
    cpdef void _ensure_kdtree(self):
        """Build KD-tree if not already built."""
        if self._kdtree is None:
            # Convert quantized coordinates to float32 for KD-tree
            cdef np.ndarray[DTYPE_t, ndim=2] coords = np.empty((self._size, 3), dtype=DTYPE)
            cdef float x, y, z
            cdef Py_ssize_t i
            
            for i in range(self._size):
                x, y, z = self._dequantize(
                    self._coords[i, 0],
                    self._coords[i, 1],
                    self._coords[i, 2]
                )
                coords[i, 0] = x
                coords[i, 1] = y
                coords[i, 2] = z
            
            # Build KD-tree with float32 coordinates
            self._kdtree = cKDTree(
                coords,
                leafsize=32,
                compact_nodes=True,
                balanced_tree=True,
                copy_data=False
            )
    
    cpdef list nearest_neighbors(self, Point3D point, int k=1):
        """Find k nearest neighbors to a point.
        
        Args:
            point (Point3D): Query point
            k (int): Number of neighbors to find
            
        Returns:
            list[Point3D]: List of k nearest neighbors
        """
        self._ensure_kdtree()
        
        # Query KD-tree
        cdef np.ndarray[DTYPE_t, ndim=1] coords = np.array(
            [point.x, point.y, point.z],
            dtype=DTYPE
        )
        
        # Get distances and indices
        distances, indices = self._kdtree.query(
            coords,
            k=k,
            workers=4,
            distance_upper_bound=np.inf,
            p=2,
            eps=0.0
        )
        
        if k == 1:
            indices = [indices]
        
        # Convert to Point3D instances
        cdef list results = []
        cdef Py_ssize_t idx
        cdef float x, y, z
        
        for idx in indices:
            x, y, z = self._dequantize(
                self._coords[idx, 0],
                self._coords[idx, 1],
                self._coords[idx, 2]
            )
            results.append(Point3D(
                self._ids[idx],
                x, y, z
            ))
        
        return results
    
    cpdef float distance(self, unsigned int id1, unsigned int id2):
        """Calculate distance between two points by their IDs.
        
        Args:
            id1 (int): ID of first point
            id2 (int): ID of second point
            
        Returns:
            float: Euclidean distance between points
        """
        cdef Point3D p1 = self.get_point(id1)
        cdef Point3D p2 = self.get_point(id2)
        return p1.distance_to(p2)
    
    cpdef float slope(self, unsigned int id1, unsigned int id2):
        """Calculate slope between two points by their IDs.
        
        Args:
            id1 (int): ID of first point
            id2 (int): ID of second point
            
        Returns:
            float: Slope in percentage
        """
        cdef Point3D p1 = self.get_point(id1)
        cdef Point3D p2 = self.get_point(id2)
        return p1.slope_to(p2)
    
    cpdef float bearing(self, unsigned int id1, unsigned int id2):
        """Calculate bearing between two points by their IDs.
        
        Args:
            id1 (int): ID of first point
            id2 (int): ID of second point
            
        Returns:
            float: Bearing angle in degrees
        """
        cdef Point3D p1 = self.get_point(id1)
        cdef Point3D p2 = self.get_point(id2)
        return p1.bearing_to(p2)
    
    @property
    def count(self):
        """Get number of points in cloud."""
        return self._size
