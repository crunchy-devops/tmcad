import numpy as np
from scipy.spatial import ConvexHull, Delaunay
from scipy.interpolate import griddata
from typing import List, Tuple, Optional, Dict, Any
from point3d import Point3D
from terrain_storage import TerrainManager

class TerrainAnalyzer:
    """Advanced spatial analysis for terrain point clouds."""
    
    def __init__(self, terrain: TerrainManager):
        self.terrain = terrain
        self._points_array = None
        self._update_points_array()
        
    def _update_points_array(self) -> None:
        """Convert points to numpy array for analysis."""
        points = []
        for i in range(len(self.terrain.point_cloud)):
            point = self.terrain.point_cloud.get_point(i)
            points.append([point.x, point.y, point.z])
        self._points_array = np.array(points)
    
    def calculate_slope(self, point: Point3D, radius: float = 10.0) -> float:
        """
        Calculate local slope (in degrees) around a point using neighboring points.
        Uses plane fitting to nearby points.
        """
        neighbors = self.terrain.find_points_in_radius(point, radius)
        if len(neighbors) < 3:
            return 0.0
            
        # Create local coordinate system
        points = np.array([[p.x, p.y, p.z] for p in neighbors])
        center = points.mean(axis=0)
        points = points - center
        
        # Fit plane using SVD
        _, _, vh = np.linalg.svd(points)
        normal = vh[2]
        
        # Calculate angle with vertical
        slope_rad = np.arccos(abs(normal[2]))
        return np.degrees(slope_rad)
    
    def calculate_roughness(self, point: Point3D, radius: float = 10.0) -> float:
        """
        Calculate local terrain roughness as the standard deviation
        of point heights from the best-fit plane.
        """
        neighbors = self.terrain.find_points_in_radius(point, radius)
        if len(neighbors) < 3:
            return 0.0
            
        points = np.array([[p.x, p.y, p.z] for p in neighbors])
        center = points.mean(axis=0)
        points = points - center
        
        # Fit plane
        _, s, vh = np.linalg.svd(points)
        normal = vh[2]
        
        # Calculate distances to plane
        distances = np.abs(np.dot(points, normal))
        return np.std(distances)
    
    def generate_contours(self, 
                         resolution: float = 1.0,
                         levels: Optional[List[float]] = None) -> Dict[float, List[List[Tuple[float, float]]]]:
        """
        Generate terrain contour lines at specified height levels.
        Returns dictionary mapping heights to lists of contour line segments.
        """
        if len(self._points_array) < 3:
            return {}
            
        # Create regular grid
        x_min, y_min = self._points_array[:, :2].min(axis=0)
        x_max, y_max = self._points_array[:, :2].max(axis=0)
        
        x = np.arange(x_min, x_max + resolution, resolution)
        y = np.arange(y_min, y_max + resolution, resolution)
        X, Y = np.meshgrid(x, y)
        
        # Interpolate heights
        Z = griddata(
            self._points_array[:, :2],
            self._points_array[:, 2],
            (X, Y),
            method='cubic'
        )
        
        # Generate contour lines
        if levels is None:
            levels = np.linspace(Z.min(), Z.max(), 10)
            
        from matplotlib import pyplot as plt
        contours = plt.contour(X, Y, Z, levels=levels)
        plt.close()
        
        # Convert to dictionary of line segments
        result = {}
        for level, segs in zip(contours.levels, contours.allsegs):
            result[float(level)] = [seg.tolist() for seg in segs]
        
        return result
    
    def calculate_volume(self, base_height: Optional[float] = None) -> float:
        """
        Calculate volume of terrain above specified base height.
        If base_height is None, uses minimum point height.
        """
        if len(self._points_array) < 3:
            return 0.0
            
        if base_height is None:
            base_height = self._points_array[:, 2].min()
            
        # Create triangulation
        tri = Delaunay(self._points_array[:, :2])
        
        volume = 0.0
        for simplex in tri.simplices:
            points = self._points_array[simplex]
            # Calculate volume of triangular prism
            a = points[1] - points[0]
            b = points[2] - points[0]
            area = abs(np.cross(a[:2], b[:2])) / 2
            avg_height = np.mean(points[:, 2]) - base_height
            volume += area * avg_height
            
        return volume
    
    def calculate_surface_area(self) -> float:
        """Calculate actual surface area of terrain (not projected area)."""
        if len(self._points_array) < 3:
            return 0.0
            
        # Create triangulation
        tri = Delaunay(self._points_array[:, :2])
        
        area = 0.0
        for simplex in tri.simplices:
            points = self._points_array[simplex]
            # Calculate area of triangle in 3D
            a = points[1] - points[0]
            b = points[2] - points[0]
            area += np.linalg.norm(np.cross(a, b)) / 2
            
        return area
    
    def analyze_terrain_features(self) -> Dict[str, Any]:
        """
        Perform comprehensive terrain analysis.
        Returns dictionary with various terrain metrics.
        """
        if len(self._points_array) < 3:
            return {}
            
        # Calculate basic statistics
        heights = self._points_array[:, 2]
        x_range = self._points_array[:, 0].max() - self._points_array[:, 0].min()
        y_range = self._points_array[:, 1].max() - self._points_array[:, 1].min()
        
        # Calculate convex hull
        hull = ConvexHull(self._points_array[:, :2])
        
        # Sample points for slope analysis
        sample_size = min(100, len(self._points_array))
        indices = np.random.choice(len(self._points_array), sample_size, replace=False)
        slopes = []
        roughness = []
        
        for idx in indices:
            point = self.terrain.point_cloud.get_point(idx)
            slopes.append(self.calculate_slope(point))
            roughness.append(self.calculate_roughness(point))
        
        return {
            'height_range': float(heights.max() - heights.min()),
            'mean_height': float(heights.mean()),
            'std_height': float(heights.std()),
            'area_2d': float(hull.area),  # Projected area
            'area_3d': self.calculate_surface_area(),  # Actual surface area
            'volume': self.calculate_volume(),
            'mean_slope': float(np.mean(slopes)),
            'max_slope': float(np.max(slopes)),
            'mean_roughness': float(np.mean(roughness)),
            'terrain_complexity': float(self.calculate_surface_area() / hull.area),
            'x_range': float(x_range),
            'y_range': float(y_range),
            'point_density': len(self._points_array) / hull.area
        }
