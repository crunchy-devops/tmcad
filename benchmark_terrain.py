"""
Benchmark terrain modeling capabilities using real DXF data.

Demonstrates:
1. Loading points from plan-masse.dxf
2. Delaunay triangulation analysis
3. DIW interpolation performance
4. Memory efficiency metrics
"""

import time
import numpy as np
from point3d import PointCloud
from dxf_converter import DxfConverter

def print_memory_stats(cloud: PointCloud, points_loaded: int) -> None:
    """Print memory usage statistics."""
    import sys
    coords_size = sys.getsizeof(cloud._coords)
    bytes_per_point = coords_size / points_loaded
    
    print("\nMemory Statistics:")
    print(f"Total points: {points_loaded}")
    print(f"Coordinate array size: {coords_size / 1024:.2f} KB")
    print(f"Bytes per point: {bytes_per_point:.2f}")
    print(f"Estimated total memory: {(32 * points_loaded) / 1024:.2f} KB")

def analyze_triangulation(cloud: PointCloud) -> None:
    """Analyze Delaunay triangulation properties."""
    cloud._ensure_triangulation()
    triangles = cloud._triangulation.simplices
    points = cloud._triangulation.points
    
    # Calculate basic statistics
    num_triangles = len(triangles)
    num_points = len(points)
    
    # Calculate triangle areas and angles
    areas = []
    min_angles = []
    
    for triangle in triangles:
        # Get triangle vertices
        vertices = points[triangle]
        
        # Calculate edges
        edges = np.roll(vertices, -1, axis=0) - vertices
        
        # Calculate area using cross product
        area = abs(np.cross(edges[0], edges[1])) / 2
        areas.append(area)
        
        # Calculate angles
        angles = []
        for i in range(3):
            v1 = edges[i]
            v2 = -edges[(i+2)%3]
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
            angles.append(np.degrees(angle))
        min_angles.append(min(angles))
    
    print("\nTriangulation Analysis:")
    print(f"Number of points: {num_points}")
    print(f"Number of triangles: {num_triangles}")
    print(f"Average triangle area: {np.mean(areas):.2f}")
    print(f"Min triangle area: {min(areas):.2f}")
    print(f"Max triangle area: {max(areas):.2f}")
    print(f"Average minimum angle: {np.mean(min_angles):.2f}°")
    print(f"Minimum angle overall: {min(min_angles):.2f}°")

def benchmark_interpolation(cloud: PointCloud, num_points: int = 1000) -> None:
    """Benchmark interpolation performance."""
    # Get bounding box for random point generation
    points = np.array(cloud._coords).reshape(-1, 3)
    min_x, min_y = np.min(points[:, :2], axis=0)
    max_x, max_y = np.max(points[:, :2], axis=0)
    
    # Generate random points for interpolation
    np.random.seed(42)  # For reproducibility
    test_points = np.random.uniform(
        low=[min_x, min_y],
        high=[max_x, max_y],
        size=(num_points, 2)
    )
    
    print("\nInterpolation Benchmark:")
    
    # Benchmark barycentric interpolation
    start_time = time.time()
    success = 0
    for x, y in test_points:
        try:
            cloud.interpolate_z(x, y, method='barycentric')
            success += 1
        except ValueError:
            continue
    barycentric_time = time.time() - start_time
    
    print(f"\nBarycentric Interpolation:")
    print(f"Points processed: {num_points}")
    print(f"Successful interpolations: {success}")
    print(f"Total time: {barycentric_time:.3f} seconds")
    print(f"Average time per point: {(barycentric_time/num_points)*1000:.3f} ms")
    
    # Benchmark DIW interpolation
    start_time = time.time()
    success = 0
    for x, y in test_points:
        try:
            cloud.interpolate_z(x, y, method='diw')
            success += 1
        except ValueError:
            continue
    diw_time = time.time() - start_time
    
    print(f"\nDIW Interpolation:")
    print(f"Points processed: {num_points}")
    print(f"Successful interpolations: {success}")
    print(f"Total time: {diw_time:.3f} seconds")
    print(f"Average time per point: {(diw_time/num_points)*1000:.3f} ms")

def main():
    # Load points from DXF
    print("Loading points from plan-masse.dxf...")
    converter = DxfConverter()
    points = converter.load_points_from_file(
        'data/plan-masse.dxf',
        layer='z value TN'
    )
    
    # Create point cloud
    cloud = PointCloud()
    for point in points:
        cloud.add_point(point)
    
    print(f"\nLoaded {len(points)} points from DXF")
    
    # Print memory statistics
    print_memory_stats(cloud, len(points))
    
    # Analyze triangulation
    analyze_triangulation(cloud)
    
    # Benchmark interpolation
    benchmark_interpolation(cloud)

if __name__ == '__main__':
    main()
