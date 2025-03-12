import numpy as np
from scipy.interpolate import Rbf, griddata
from scipy.spatial import cKDTree
from typing import List, Tuple, Optional
from point3d import Point3D
from terrain_storage import TerrainManager

class TerrainInterpolator:
    """Interpolation methods for sparse terrain point clouds."""
    
    def __init__(self, terrain: TerrainManager):
        self.terrain = terrain
        self._points_array = None
        self._update_points_array()
        
    def _update_points_array(self) -> None:
        """Convert points to numpy array for interpolation."""
        points = []
        for i in range(len(self.terrain.point_cloud)):
            point = self.terrain.point_cloud.get_point(i)
            points.append([point.x, point.y, point.z])
        self._points_array = np.array(points)
    
    def create_dense_grid(self, 
                         resolution: float = 1.0,
                         method: str = 'cubic') -> List[Point3D]:
        """Create a dense regular grid of points using interpolation."""
        if len(self._points_array) < 3:
            return []
            
        # Create regular grid
        x_min, y_min = self._points_array[:, :2].min(axis=0)
        x_max, y_max = self._points_array[:, :2].max(axis=0)
        
        x = np.arange(x_min, x_max + resolution, resolution)
        y = np.arange(y_min, y_max + resolution, resolution)
        X, Y = np.meshgrid(x, y)
        
        if method == 'rbf':
            # Radial basis function interpolation
            rbf = Rbf(self._points_array[:, 0],
                     self._points_array[:, 1],
                     self._points_array[:, 2],
                     function='thin_plate')
            Z = rbf(X, Y)
        else:
            # Grid-based interpolation
            Z = griddata(
                self._points_array[:, :2],
                self._points_array[:, 2],
                (X, Y),
                method=method
            )
        
        # Create Point3D objects efficiently
        points = []
        point_id = len(self.terrain.point_cloud)
        
        for i in range(len(x)):
            for j in range(len(y)):
                if not np.isnan(Z[j, i]):
                    points.append(Point3D(
                        id=point_id,
                        x=float(X[j, i]),
                        y=float(Y[j, i]),
                        z=float(Z[j, i])
                    ))
                    point_id += 1
        
        return points
    
    def estimate_optimal_resolution(self) -> float:
        """Estimate optimal grid resolution based on point density."""
        if len(self._points_array) < 2:
            return 1.0
            
        # Calculate average nearest neighbor distance
        tree = cKDTree(self._points_array[:, :2])
        distances, _ = tree.query(self._points_array[:, :2], k=2)
        avg_spacing = np.mean(distances[:, 1])
        
        # Return resolution that would give ~4x point density
        return avg_spacing / 2
    
    def calculate_accuracy_metrics(self, 
                                interpolated_points: List[Point3D],
                                test_fraction: float = 0.2) -> dict:
        """Calculate interpolation accuracy using cross-validation."""
        if len(self._points_array) < 5:
            return {}
            
        # Randomly select test points
        n_test = max(1, int(len(self._points_array) * test_fraction))
        test_indices = np.random.choice(
            len(self._points_array),
            n_test,
            replace=False
        )
        
        test_points = self._points_array[test_indices]
        
        # Find nearest interpolated points
        interp_coords = np.array([[p.x, p.y, p.z] for p in interpolated_points])
        tree = cKDTree(interp_coords[:, :2])
        
        # Calculate errors
        distances, indices = tree.query(test_points[:, :2])
        z_errors = np.abs(test_points[:, 2] - interp_coords[indices, 2])
        
        return {
            'mean_absolute_error': float(np.mean(z_errors)),
            'max_absolute_error': float(np.max(z_errors)),
            'rmse': float(np.sqrt(np.mean(z_errors ** 2))),
            'mean_xy_distance': float(np.mean(distances)),
            'test_points': n_test
        }
