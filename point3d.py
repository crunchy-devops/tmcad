"""Memory-efficient 3D point representation and operations.

This module provides a highly optimized Point3D class with coordinate quantization
and compressed storage, achieving ~10 bytes per point while maintaining 0.01 precision.
"""
from __future__ import annotations

import array
import math
import os
import struct
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.spatial import cKDTree


@dataclass(slots=True, frozen=True)
class Point3D:
    """Memory-efficient immutable 3D point representation."""
    id: int
    x: float
    y: float
    z: float

    def distance_to(self, other: Point3D) -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def slope_to(self, other: Point3D) -> float:
        """Calculate slope to another point in percentage."""
        run = math.sqrt((other.x - self.x) ** 2 + (other.y - self.y) ** 2)
        if run == 0:
            return float('inf') if other.z > self.z else float('-inf')
        rise = other.z - self.z
        return (rise / run) * 100

    def bearing_to(self, other: Point3D) -> float:
        """Calculate bearing angle to another point in degrees."""
        dx = other.x - self.x
        dy = other.y - self.y
        
        angle = math.degrees(math.atan2(dy, dx))
        bearing = 90 - angle
        return bearing % 360


class PointCloud:
    """Memory-efficient collection of Point3D instances.
    
    Uses coordinate quantization and compressed storage:
    - id: uint32 (4 bytes)
    - x,y,z: int16 (2 bytes each) with 0.01 precision
    
    Total size per point: 10 bytes
    """
    _COORD_SCALE = 100.0  # Store coordinates with 0.01 precision
    _POINT_DTYPE = np.dtype([
        ('id', np.uint32),    # 4 bytes
        ('coords', np.int16, 3)  # 6 bytes (2 bytes × 3)
    ])
    _CHUNK_SIZE = 4096  # Process points in chunks

    def __init__(self):
        """Initialize empty point cloud with memory-mapped storage."""
        # Create memory-mapped file for points
        self._data_file = tempfile.NamedTemporaryFile(suffix='.npy', delete=False)
        self._points = np.memmap(
            self._data_file.name,
            dtype=self._POINT_DTYPE,
            mode='w+',
            shape=(0,)
        )
        
        # Create memory-mapped file for spatial index
        self._spatial_file = tempfile.NamedTemporaryFile(suffix='.npy', delete=False)
        self._spatial_array = None
        
        # Minimal in-memory data structures
        self._id_to_index = {}
        self._kdtree = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _quantize(self, coord: float) -> int:
        """Quantize coordinate to int16 with 0.01 precision."""
        return int(round(coord * self._COORD_SCALE))

    def _dequantize(self, coord: int) -> float:
        """Dequantize coordinate from int16 to float."""
        return coord / self._COORD_SCALE

    def add_points(self, points: Union[List[Point3D], np.ndarray]) -> None:
        """Add multiple points efficiently using vectorized operations."""
        if isinstance(points, np.ndarray):
            # Convert and quantize coordinates
            ids = points[:, 0].astype(np.uint32)
            coords = np.round(points[:, 1:] * self._COORD_SCALE).astype(np.int16)
        else:
            # Convert points to numpy arrays
            ids = np.array([p.id for p in points], dtype=np.uint32)
            coords = np.array([
                [self._quantize(p.x), self._quantize(p.y), self._quantize(p.z)]
                for p in points
            ], dtype=np.int16)
        
        # Create new points array
        new_points = np.empty(len(ids), dtype=self._POINT_DTYPE)
        new_points['id'] = ids
        new_points['coords'] = coords
        
        # Process in chunks to reduce memory usage
        chunk_size = self._CHUNK_SIZE
        for i in range(0, len(new_points), chunk_size):
            chunk = new_points[i:i + chunk_size]
            
            # Resize memory-mapped array
            old_size = len(self._points)
            new_size = old_size + len(chunk)
            
            # Create new memory-mapped array with increased size
            new_mmap = np.memmap(
                self._data_file.name,
                dtype=self._POINT_DTYPE,
                mode='r+',
                shape=(new_size,)
            )
            
            # Copy existing data
            if old_size > 0:
                new_mmap[:old_size] = self._points[:]
            
            # Add new chunk
            new_mmap[old_size:new_size] = chunk
            
            # Update index
            for j, point_id in enumerate(chunk['id']):
                self._id_to_index[int(point_id)] = old_size + j
            
            # Update points array
            del self._points
            self._points = new_mmap
            
            # Force sync to disk
            self._points.flush()
        
        # Clear spatial index
        self._clear_spatial_index()

    def add_point(self, point: Point3D) -> None:
        """Add a single point to the cloud."""
        # Convert to arrays for consistency
        self.add_points([point])

    def get_point(self, point_id: int) -> Point3D:
        """Retrieve a point by its ID."""
        if point_id not in self._id_to_index:
            raise KeyError(f"Point ID {point_id} not found")
        
        idx = self._id_to_index[point_id]
        point_data = self._points[idx]
        
        return Point3D(
            id=int(point_data['id']),
            x=self._dequantize(point_data['coords'][0]),
            y=self._dequantize(point_data['coords'][1]),
            z=self._dequantize(point_data['coords'][2])
        )

    def _clear_spatial_index(self) -> None:
        """Clear spatial index to free memory."""
        if self._kdtree is not None:
            del self._kdtree
            self._kdtree = None
        
        if self._spatial_array is not None:
            del self._spatial_array
            self._spatial_array = None

    def _ensure_kdtree(self) -> None:
        """Build KD-tree if not already built."""
        if self._kdtree is None:
            # Create memory-mapped array for coordinates
            coords = self._points['coords'].astype(np.float64) / self._COORD_SCALE
            np.save(self._spatial_file.name, coords)
            self._spatial_array = np.load(
                self._spatial_file.name,
                mmap_mode='r'
            )
            
            # Build KD-tree using memory-mapped array
            self._kdtree = cKDTree(
                self._spatial_array,
                leafsize=32,  # Larger leaf size for better memory efficiency
                compact_nodes=True,
                balanced_tree=True,
                boxsize=None
            )

    def nearest_neighbors(self, point: Point3D, k: int = 1) -> List[Point3D]:
        """Find k nearest neighbors to a point."""
        self._ensure_kdtree()
        
        # Query KD-tree
        coords = np.array([point.x, point.y, point.z])
        dists, indices = self._kdtree.query(
            coords,
            k=k,
            workers=-1,
            distance_upper_bound=np.inf,
            p=2,
            eps=0.01
        )
        
        if k == 1:
            indices = [indices]
        
        # Convert to Point3D instances
        points_data = self._points[indices]
        return [
            Point3D(
                id=int(p['id']),
                x=self._dequantize(p['coords'][0]),
                y=self._dequantize(p['coords'][1]),
                z=self._dequantize(p['coords'][2])
            )
            for p in points_data
        ]

    def distance(self, id1: int, id2: int) -> float:
        """Calculate distance between two points by their IDs."""
        return self.get_point(id1).distance_to(self.get_point(id2))

    def slope(self, id1: int, id2: int) -> float:
        """Calculate slope between two points by their IDs."""
        return self.get_point(id1).slope_to(self.get_point(id2))

    def bearing(self, id1: int, id2: int) -> float:
        """Calculate bearing between two points by their IDs."""
        return self.get_point(id1).bearing_to(self.get_point(id2))

    def close(self) -> None:
        """Close and cleanup resources."""
        if hasattr(self, '_points'):
            del self._points
        
        if hasattr(self, '_data_file'):
            try:
                os.unlink(self._data_file.name)
            except (OSError, PermissionError):
                pass
        
        if hasattr(self, '_spatial_file'):
            try:
                os.unlink(self._spatial_file.name)
            except (OSError, PermissionError):
                pass
        
        self._executor.shutdown(wait=True)
        self._clear_spatial_index()

    @property
    def count(self) -> int:
        """Get number of points in cloud."""
        return len(self._points)
