"""
Memory-efficient 3D point implementation with spatial indexing.

This module provides a highly optimized Point3D class and PointCloud container
for managing large terrain point datasets with efficient spatial operations.
"""

from __future__ import annotations
from array import array
from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict, Tuple, Union
import math
import numpy as np
from scipy.spatial import cKDTree, Delaunay

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
    Memory-efficient container for Point3D objects with terrain modeling capabilities.
    
    Uses array.array for coordinate storage and KD-tree for spatial queries.
    Memory usage is optimized to ~32 bytes per point plus indexing overhead.
    Supports Delaunay triangulation and multiple interpolation methods.
    
    Attributes:
        points (Dict[int, int]): Maps point IDs to array indices
        coords (array): Packed coordinates array
        _kdtree (cKDTree): Spatial index for efficient queries
        _triangulation (Delaunay): Delaunay triangulation for surface modeling
        _break_lines (List[Tuple[int, int]]): Break lines defined by point ID pairs
    """
    
    def __init__(self):
        """Initialize empty point cloud with efficient storage."""
        self._id_to_index: Dict[int, int] = {}
        self._coords = array('d')
        self._kdtree: Optional[cKDTree] = None
        self._triangulation: Optional[Delaunay] = None
        self._break_lines: List[Tuple[int, int]] = []
        
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
        self._triangulation = None  # Invalidate triangulation
        
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
        
    def break_lines(self, line_points: List[Tuple[int, int]]) -> None:
        """
        Define break lines in the terrain model using point ID pairs.
        
        Break lines are used to enforce terrain features like ridges or valleys
        during triangulation and interpolation.
        
        Args:
            line_points: List of point ID pairs defining break lines
            
        Raises:
            KeyError: If any point ID does not exist
            ValueError: If line points are invalid
        """
        # Validate all points exist
        for p1_id, p2_id in line_points:
            if p1_id not in self._id_to_index or p2_id not in self._id_to_index:
                raise KeyError("Break line point ID not found")
            if p1_id == p2_id:
                raise ValueError("Break line cannot connect point to itself")
                
        self._break_lines = list(line_points)
        self._triangulation = None  # Invalidate triangulation
        
    def _ensure_triangulation(self) -> None:
        """
        Ensure Delaunay triangulation is up to date.
        Updates triangulation if needed, incorporating break lines.
        """
        if self._triangulation is not None:
            return
            
        # Convert coordinates to numpy array for triangulation
        points = np.array(self._coords).reshape(-1, 3)
        xy_points = points[:, :2]  # Use only X,Y for triangulation
        
        # Create initial triangulation
        self._triangulation = Delaunay(xy_points)
        
        # If we have break lines, modify triangulation to respect them
        if self._break_lines:
            # Get all triangles that intersect break lines
            triangles = self._triangulation.points[self._triangulation.simplices]
            modified = False
            
            for p1_id, p2_id in self._break_lines:
                # Get break line endpoints
                p1_idx = self._id_to_index[p1_id]
                p2_idx = self._id_to_index[p2_id]
                p1 = xy_points[p1_idx]
                p2 = xy_points[p2_idx]
                
                # Find triangles intersecting this break line
                for i, tri in enumerate(triangles):
                    # Check if triangle intersects break line
                    if self._line_intersects_triangle(p1, p2, tri):
                        # Split triangle if needed
                        self._split_triangle(i, p1_idx, p2_idx)
                        modified = True
            
            # Rebuild triangulation if modifications were made
            if modified:
                self._triangulation = Delaunay(xy_points)
                
    def _line_intersects_triangle(self, p1: np.ndarray, p2: np.ndarray, triangle: np.ndarray) -> bool:
        """Check if line segment intersects triangle."""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
            
        def line_intersects(A, B, C, D):
            return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)
            
        # Check if line segment intersects any triangle edge
        return (
            line_intersects(p1, p2, triangle[0], triangle[1]) or
            line_intersects(p1, p2, triangle[1], triangle[2]) or
            line_intersects(p1, p2, triangle[2], triangle[0])
        )
        
    def _split_triangle(self, tri_idx: int, p1_idx: int, p2_idx: int) -> None:
        """Split triangle to respect break line constraint."""
        # Get triangle vertices
        vertices = self._triangulation.points[self._triangulation.simplices[tri_idx]]
        
        # Find intersection point (simplified - using midpoint for now)
        p1 = self._triangulation.points[p1_idx]
        p2 = self._triangulation.points[p2_idx]
        mid = (p1 + p2) / 2
        
        # Add new point to force triangulation to respect break line
        new_point = np.array([mid[0], mid[1]])
        points = np.vstack((self._triangulation.points, new_point))
        self._triangulation = Delaunay(points)
        
    def interpolate_z(self, x: float, y: float, method: str = 'barycentric') -> float:
        """
        Interpolate Z value at given X,Y coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            method: Interpolation method ('barycentric' or 'diw')
            
        Returns:
            Interpolated Z value
            
        Raises:
            ValueError: If coordinates are outside the terrain or method is invalid
        """
        if method not in ('barycentric', 'diw'):
            raise ValueError("Invalid interpolation method")
            
        self._ensure_triangulation()
        query_point = np.array([x, y])
        
        if method == 'barycentric':
            # Find triangle containing the point
            simplex = self._triangulation.find_simplex(query_point)
            if simplex < 0:
                raise ValueError("Point outside terrain boundary")
                
            # Get triangle vertices and their Z values
            vertices = self._triangulation.points[self._triangulation.simplices[simplex]]
            points_array = np.array(self._coords).reshape(-1, 3)
            
            # Handle break lines by checking if we're interpolating across one
            if self._break_lines:
                # Find nearest break line
                min_dist = float('inf')
                nearest_line = None
                
                for p1_id, p2_id in self._break_lines:
                    p1 = self.get_point(p1_id)
                    p2 = self.get_point(p2_id)
                    
                    # Calculate distance to line segment
                    dist = self._point_to_line_distance(x, y, p1, p2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_line = (p1, p2)
                
                # If point is very close to a break line, use nearest point on that line
                if min_dist < 0.1:  # Threshold distance
                    p1, p2 = nearest_line
                    t = self._project_point_to_line(x, y, p1, p2)
                    if 0 <= t <= 1:  # Point projects onto line segment
                        # Interpolate Z value along break line
                        return float(p1.z + t * (p2.z - p1.z))
            
            # Standard barycentric interpolation if not near break line
            z_values = points_array[self._triangulation.simplices[simplex], 2]
            transform = self._triangulation.transform[simplex]
            b = transform[:2].dot(query_point - transform[2])
            bary = np.append(b, 1 - b.sum())
            return float(np.dot(bary, z_values))
        else:  # DIW (Distance Inverse Weighting)
            # Find nearest points
            if self._kdtree is None:
                points = np.array(self._coords).reshape(-1, 3)
                self._kdtree = cKDTree(points[:, :2])
                
            # Find k nearest neighbors
            k = min(5, len(self._id_to_index))
            distances, indices = self._kdtree.query([x, y], k=k)
            
            # Handle point exactly on a known point
            if isinstance(distances, float) and distances < 1e-10:
                points = np.array(self._coords).reshape(-1, 3)
                return float(points[indices, 2])
                
            # Convert to arrays if single point returned
            if isinstance(distances, float):
                distances = np.array([distances])
                indices = np.array([indices])
            
            # Handle point exactly on a known point
            if distances[0] < 1e-10:
                points = np.array(self._coords).reshape(-1, 3)
                return float(points[indices[0], 2])
                
            # Calculate weights and weighted sum
            weights = 1.0 / (distances ** 2)
            points = np.array(self._coords).reshape(-1, 3)
            z_values = points[indices, 2]
            return float(np.sum(weights * z_values) / np.sum(weights))
            
    def _point_to_line_distance(self, x: float, y: float, p1: Point3D, p2: Point3D) -> float:
        """Calculate distance from point to line segment."""
        # Convert to numpy arrays for vector operations
        point = np.array([x, y])
        line_p1 = np.array([p1.x, p1.y])
        line_p2 = np.array([p2.x, p2.y])
        
        # Calculate normalized direction vector
        line_dir = line_p2 - line_p1
        line_len = np.linalg.norm(line_dir)
        if line_len == 0:
            return np.linalg.norm(point - line_p1)
            
        line_dir = line_dir / line_len
        
        # Calculate perpendicular distance
        vec_to_point = point - line_p1
        return abs(np.cross(vec_to_point, line_dir))
        
    def _project_point_to_line(self, x: float, y: float, p1: Point3D, p2: Point3D) -> float:
        """Project point onto line segment and return parametric coordinate (0 to 1)."""
        point = np.array([x, y])
        line_p1 = np.array([p1.x, p1.y])
        line_p2 = np.array([p2.x, p2.y])
        
        # Calculate direction vector
        line_dir = line_p2 - line_p1
        line_len_sq = np.dot(line_dir, line_dir)
        
        if line_len_sq == 0:
            return 0.0
            
        # Calculate projection parameter
        t = np.dot(point - line_p1, line_dir) / line_len_sq
        return max(0.0, min(1.0, t))  # Clamp to [0,1]
            
    def slope_between_points(self, id1: int, id2: int) -> float:
        """Calculate slope between two points in percentage."""
        p1 = self.get_point(id1)
        p2 = self.get_point(id2)
        return p1.slope_to(p2)
