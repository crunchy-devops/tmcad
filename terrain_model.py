from __future__ import annotations
import numpy as np
from scipy.spatial import Delaunay, cKDTree
import json
from typing import List, Tuple, Optional, Set, Dict
from point3d import Point3D, PointCloud
import logging

class TerrainModel:
    """Manages terrain point cloud with geometric operations and analysis capabilities."""
    
    def __init__(self, name: str):
        """Initialize terrain model with given name."""
        self.name = name
        self.points = PointCloud()  # Using array-based storage for O(1) access
        self._kdtree = None
        self._triangulation = None
        self._break_lines: List[List[int]] = []
        self._stats = {
            'point_count': 0,
            'bounds': {'min_x': float('inf'), 'max_x': float('-inf'),
                      'min_y': float('inf'), 'max_y': float('-inf'),
                      'min_z': float('inf'), 'max_z': float('-inf')},
            'mean_slope': 0.0,
            'max_slope': 0.0,
            'surface_area': 0.0,
            'volume': 0.0,
            'slopes': {}  # Store slope values per point for visualization
        }
        self._points_array_cache = None  # Cache for frequently accessed points array

    @property
    def min_elevation(self) -> float:
        """Get minimum elevation (z) value using array-based access."""
        if len(self.points) == 0:
            return 0.0
        points_array = self._get_points_array()
        return float(np.min(points_array[:, 2]))

    @property
    def max_elevation(self) -> float:
        """Get maximum elevation (z) value using array-based access."""
        if len(self.points) == 0:
            return 0.0
        points_array = self._get_points_array()
        return float(np.max(points_array[:, 2]))

    @property
    def avg_elevation(self) -> float:
        """Get average elevation (z) value using array-based access."""
        if len(self.points) == 0:
            return 0.0
        points_array = self._get_points_array()
        return float(np.mean(points_array[:, 2]))

    @property
    def surface_area(self) -> float:
        """Get terrain surface area in square meters."""
        return self._stats['surface_area']

    @property
    def volume(self) -> float:
        """Get terrain volume in cubic meters."""
        return self._stats['volume']

    def _get_points_array(self) -> np.ndarray:
        """Get points array with caching for better performance."""
        if self._points_array_cache is None:
            self._points_array_cache = self.points.get_points_array()
        return self._points_array_cache

    def add_point(self, point: Point3D) -> None:
        """Add a point to the terrain model and update statistics."""
        self.points.add_point(point)
        self._update_bounds(point)
        self._stats['point_count'] += 1
        # Invalidate cached computations
        self._kdtree = None
        self._triangulation = None
        self._points_array_cache = None

    def _update_bounds(self, point: Point3D) -> None:
        """Update terrain bounds with new point."""
        bounds = self._stats['bounds']
        bounds['min_x'] = min(bounds['min_x'], point.x)
        bounds['max_x'] = max(bounds['max_x'], point.x)
        bounds['min_y'] = min(bounds['min_y'], point.y)
        bounds['max_y'] = max(bounds['max_y'], point.y)
        bounds['min_z'] = min(bounds['min_z'], point.z)
        bounds['max_z'] = max(bounds['max_z'], point.z)

    def add_break_line(self, point_ids: List[int]) -> None:
        """Add a break line defined by a sequence of point IDs."""
        # Validate all points exist using index-based access
        points_array = self._get_points_array()
        id_to_index = self.points._id_to_index
        if not all(pid in id_to_index for pid in point_ids):
            raise ValueError("All points in break line must exist in terrain")
        self._break_lines.append(point_ids)
        # Invalidate triangulation
        self._triangulation = None

    def get_nearest_points(self, x: float, y: float, k: int = 1) -> List[Point3D]:
        """Find k nearest points to given (x,y) coordinates using KD-tree."""
        if self._kdtree is None:
            points_array = self._get_points_array()
            self._kdtree = cKDTree(points_array[:, :2])  # Only use x,y for search
        
        distances, indices = self._kdtree.query([x, y], k=k)
        points_array = self._get_points_array()
        id_list = list(self.points._id_to_index.keys())
        
        # Use array operations for better performance
        result = []
        if k == 1:
            indices = [indices]
        for idx in indices:
            point_coords = points_array[idx]
            result.append(Point3D(
                id=id_list[idx],
                x=point_coords[0],
                y=point_coords[1],
                z=point_coords[2]
            ))
        return result

    def interpolate_elevation(self, x: float, y: float) -> Optional[float]:
        """Interpolate Z value at given (x,y) using barycentric interpolation."""
        if self._triangulation is None:
            self._compute_triangulation()
        
        if self._triangulation is None:  # Not enough points
            return None
            
        try:
            points_array = self._get_points_array()
            simplex_index = self._triangulation.find_simplex([x, y])
            
            if simplex_index < 0:  # Point outside triangulation
                return None
                
            # Use array operations for better performance
            vertices = self._triangulation.points[self._triangulation.simplices[simplex_index]]
            z_values = points_array[self._triangulation.simplices[simplex_index]][:, 2]
            
            # Compute barycentric coordinates
            b = self._triangulation.transform[simplex_index, :2]
            origin = self._triangulation.transform[simplex_index, 2]
            xy_diff = np.array([x - origin[0], y - origin[1]])
            bary = np.hstack((b @ xy_diff, 1 - np.sum(b @ xy_diff)))
            
            # Interpolate z value using dot product
            return float(np.dot(bary, z_values))
        except Exception:
            return None

    def _compute_triangulation(self) -> None:
        """Compute Delaunay triangulation respecting break lines."""
        if len(self.points) < 3:
            return
            
        points_array = self._get_points_array()
        self._triangulation = Delaunay(points_array[:, :2])

    def compute_surface_metrics(self) -> None:
        """Compute surface metrics including slope, area, and volume."""
        if len(self.points) < 3:
            # Not enough points for triangulation
            self._stats.update({
                'mean_slope': 0.0,
                'max_slope': 0.0,
                'surface_area': 0.0,
                'volume': 0.0,
                'slopes': {}
            })
            return

        points_array = self._get_points_array()
        try:
            # Create triangulation if not exists
            if self._triangulation is None:
                self._compute_triangulation()
                
            triangles = points_array[self._triangulation.simplices]
            
            # Use array operations for better performance
            v1 = triangles[:, 1] - triangles[:, 0]
            v2 = triangles[:, 2] - triangles[:, 0]
            normals = np.cross(v1, v2)
            
            # Compute areas and slopes in a single pass
            normal_lengths = np.linalg.norm(normals, axis=1)
            unit_normals = normals / normal_lengths[:, np.newaxis]
            areas = normal_lengths / 2
            
            # Compute slopes using vectorized operations
            vertical = np.array([0, 0, 1])
            dot_products = np.dot(unit_normals, vertical)
            dot_products = np.clip(dot_products, -1.0, 1.0)
            slopes = np.arccos(np.abs(dot_products))
            slopes_deg = np.degrees(slopes)
            
            # Update statistics
            self._stats.update({
                'mean_slope': float(np.mean(slopes_deg)),
                'max_slope': float(np.max(slopes_deg)),
                'surface_area': float(np.sum(areas)),
                'volume': float(np.sum(areas * np.mean(triangles[:, :, 2], axis=1)))
            })
            
            # Compute point slopes using array operations
            point_slopes = np.zeros(len(points_array))
            point_counts = np.zeros(len(points_array))
            
            for i, triangle in enumerate(self._triangulation.simplices):
                slope = slopes_deg[i]
                np.add.at(point_slopes, triangle, slope)
                np.add.at(point_counts, triangle, 1)
            
            # Store averaged slopes per point
            id_list = list(self.points._id_to_index.keys())
            self._stats['slopes'] = {
                id_list[i]: point_slopes[i] / point_counts[i]
                for i in range(len(points_array))
                if point_counts[i] > 0
            }
            
        except Exception as e:
            logging.error(f"Error computing surface metrics: {str(e)}")
            # Reset metrics on error
            self._stats.update({
                'mean_slope': 0.0,
                'max_slope': 0.0,
                'surface_area': 0.0,
                'volume': 0.0,
                'slopes': {}
            })

    def get_stats(self) -> Dict:
        """Get terrain statistics."""
        if len(self.points) > 0:
            # Only compute metrics if we have points
            self.compute_surface_metrics()
            
            # Fix bounds if no points were added
            bounds = self._stats['bounds']
            if bounds['min_x'] == float('inf'):
                bounds.update({
                    'min_x': 0, 'max_x': 0,
                    'min_y': 0, 'max_y': 0,
                    'min_z': 0, 'max_z': 0
                })
        
        return self._stats

    @classmethod
    def from_dict(cls, data: Dict) -> TerrainModel:
        """Create TerrainModel from dictionary data."""
        model = cls(data['name'])
        
        # Add points
        for point_data in data['points']:
            if isinstance(point_data, (list, tuple)):
                pid, x, y, z = point_data
            else:
                pid, x, y, z = point_data['id'], point_data['x'], point_data['y'], point_data['z']
            model.add_point(Point3D(id=pid, x=x, y=y, z=z))
        
        # Add break lines
        for break_line in data.get('break_lines', []):
            model.add_break_line(break_line)
        
        return model

    def to_dict(self) -> Dict:
        """Convert TerrainModel to dictionary."""
        return {
            'name': self.name,
            'points': [(p.id, p.x, p.y, p.z) for p in self.points],
            'break_lines': self._break_lines,
            'stats': self.get_stats()
        }
