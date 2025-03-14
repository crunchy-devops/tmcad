import os
from dxf_importer import DXFImporter
import numpy as np

def analyze_terrain_model(dxf_path: str, layer: str):
    """Analyze terrain model properties and metrics."""
    print(f"\nAnalyzing terrain from DXF file: {os.path.basename(dxf_path)}")
    print(f"Layer: {layer}\n")
    
    # Import terrain
    terrain = DXFImporter.import_terrain(dxf_path, "test_terrain", layers=[layer])
    
    # Basic statistics
    print("Basic Statistics:")
    print(f"Number of points: {len(terrain.points)}")
    
    # Get bounds
    bounds = terrain._stats['bounds']
    print("\nTerrain Bounds:")
    print(f"X range: {bounds['min_x']:.2f} to {bounds['max_x']:.2f} ({bounds['max_x'] - bounds['min_x']:.2f} units)")
    print(f"Y range: {bounds['min_y']:.2f} to {bounds['max_y']:.2f} ({bounds['max_y'] - bounds['min_y']:.2f} units)")
    print(f"Z range: {bounds['min_z']:.2f} to {bounds['max_z']:.2f} ({bounds['max_z'] - bounds['min_z']:.2f} units)")
    
    # Compute surface metrics
    terrain.compute_surface_metrics()
    stats = terrain._stats
    
    print("\nSurface Metrics:")
    print(f"Mean slope: {stats['mean_slope']:.2f}°")
    print(f"Max slope: {stats['max_slope']:.2f}°")
    print(f"Surface area: {stats['surface_area']:.2f} square units")
    print(f"Volume above z=0: {stats['volume']:.2f} cubic units")
    
    # Point distribution analysis
    points_array = terrain.points.get_points_array()
    x = points_array[:, 0]
    y = points_array[:, 1]
    z = points_array[:, 2]
    
    print("\nPoint Distribution:")
    print(f"Mean elevation: {np.mean(z):.2f}")
    print(f"Median elevation: {np.median(z):.2f}")
    print(f"Std deviation: {np.std(z):.2f}")
    
    # Point density
    area = (bounds['max_x'] - bounds['min_x']) * (bounds['max_y'] - bounds['min_y'])
    density = len(terrain.points) / area
    print(f"\nPoint density: {density:.2f} points per square unit")
    
    # Memory usage analysis
    points_memory = len(terrain.points) * 32  # 32 bytes per point as per design
    print(f"\nMemory Usage:")
    print(f"Points memory: {points_memory / 1024:.2f} KB")
    print(f"Bytes per point: {points_memory / len(terrain.points):.2f}")
    
    # Test point retrieval performance
    import time
    start_time = time.time()
    for _ in range(1000):
        terrain.get_nearest_points(
            (bounds['min_x'] + bounds['max_x']) / 2,
            (bounds['min_y'] + bounds['max_y']) / 2,
            k=1
        )
    query_time = (time.time() - start_time) / 1000
    print(f"\nPerformance:")
    print(f"Average nearest point query time: {query_time*1000:.2f} ms")

if __name__ == '__main__':
    dxf_path = os.path.join(os.path.dirname(__file__), 'data', 'plan-masse.dxf')
    analyze_terrain_model(dxf_path, "z value TN")
