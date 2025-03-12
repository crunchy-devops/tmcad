import numpy as np
from scipy.spatial import cKDTree
import h5py
from typing import List, Tuple, Optional, Union
from point3d import Point3D, PointCloud
import struct

class TerrainManager:
    """
    Advanced terrain management system with spatial indexing and efficient storage.
    Provides compression, spatial queries, and HDF5-based persistence.
    """
    def __init__(self, precision: float = 0.001):
        self.precision = precision  # Quantization precision
        self.point_cloud = PointCloud()
        self.kdtree: Optional[cKDTree] = None
        self._coordinate_scale = 1.0 / precision
        
    def add_points(self, points: List[Point3D]) -> None:
        """Add multiple points and update spatial index."""
        for point in points:
            self.point_cloud.add_point(point)
        self._update_spatial_index()
    
    def _update_spatial_index(self) -> None:
        """Update the KD-tree spatial index."""
        if len(self.point_cloud) == 0:
            return
            
        # Convert points to numpy array for KD-tree
        points_array = np.zeros((len(self.point_cloud), 3))
        for i in range(len(self.point_cloud)):
            point = self.point_cloud.get_point(i)
            points_array[i] = [point.x, point.y, point.z]
            
        self.kdtree = cKDTree(points_array)
    
    def find_nearest_neighbors(self, query_point: Point3D, k: int = 1) -> List[Point3D]:
        """Find k nearest neighbors to the query point."""
        if not self.kdtree or len(self.point_cloud) == 0:
            return []
            
        distances, indices = self.kdtree.query(
            [query_point.x, query_point.y, query_point.z],
            k=min(k, len(self.point_cloud))
        )
        
        if k == 1:
            indices = [indices]
            
        return [self.point_cloud.get_point(int(idx)) for idx in indices]
    
    def find_points_in_radius(self, center: Point3D, radius: float) -> List[Point3D]:
        """Find all points within a given radius of the center point."""
        if not self.kdtree:
            return []
            
        indices = self.kdtree.query_ball_point(
            [center.x, center.y, center.z],
            radius
        )
        return [self.point_cloud.get_point(idx) for idx in indices]
    
    def quantize_coordinates(self, coord: float) -> int:
        """Quantize a coordinate value to reduce storage size."""
        return int(round(coord * self._coordinate_scale))
    
    def dequantize_coordinates(self, quantized: int) -> float:
        """Convert quantized value back to float coordinate."""
        return quantized / self._coordinate_scale
    
    def save_to_hdf5(self, filename: str) -> None:
        """
        Save terrain data to HDF5 format with compression.
        Includes quantized coordinates and metadata.
        """
        with h5py.File(filename, 'w') as f:
            # Store metadata
            f.attrs['precision'] = self.precision
            f.attrs['num_points'] = len(self.point_cloud)
            
            # Prepare compressed arrays
            ids = np.zeros(len(self.point_cloud), dtype=np.uint64)
            coords = np.zeros((len(self.point_cloud), 3), dtype=np.int32)
            
            # Quantize and store points
            for i in range(len(self.point_cloud)):
                point = self.point_cloud.get_point(i)
                ids[i] = point.id
                coords[i] = [
                    self.quantize_coordinates(point.x),
                    self.quantize_coordinates(point.y),
                    self.quantize_coordinates(point.z)
                ]
            
            # Create compressed datasets
            f.create_dataset('ids', data=ids, compression='gzip', compression_opts=9)
            f.create_dataset('coordinates', data=coords, compression='gzip', compression_opts=9)
    
    @classmethod
    def load_from_hdf5(cls, filename: str) -> 'TerrainManager':
        """
        Load terrain data from HDF5 format.
        Reconstructs point cloud and spatial index.
        """
        terrain = cls()
        
        with h5py.File(filename, 'r') as f:
            # Load metadata
            terrain.precision = f.attrs['precision']
            terrain._coordinate_scale = 1.0 / terrain.precision
            
            # Load compressed arrays
            ids = f['ids'][:]
            coords = f['coordinates'][:]
            
            # Reconstruct points
            points = []
            for i in range(len(ids)):
                points.append(Point3D(
                    id=int(ids[i]),
                    x=terrain.dequantize_coordinates(coords[i, 0]),
                    y=terrain.dequantize_coordinates(coords[i, 1]),
                    z=terrain.dequantize_coordinates(coords[i, 2])
                ))
            
            # Add points to terrain
            terrain.add_points(points)
            
        return terrain
    
    def get_statistics(self) -> dict:
        """Calculate statistical information about the terrain."""
        if len(self.point_cloud) == 0:
            return {}
            
        points_array = np.zeros((len(self.point_cloud), 3))
        for i in range(len(self.point_cloud)):
            point = self.point_cloud.get_point(i)
            points_array[i] = [point.x, point.y, point.z]
            
        return {
            'num_points': len(self.point_cloud),
            'bounds': {
                'min': points_array.min(axis=0).tolist(),
                'max': points_array.max(axis=0).tolist()
            },
            'mean': points_array.mean(axis=0).tolist(),
            'std': points_array.std(axis=0).tolist()
        }
