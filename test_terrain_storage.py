import numpy as np
import os
from point3d import Point3D
from terrain_storage import TerrainManager

def generate_sample_terrain(num_points: int = 1000, seed: int = 42) -> list:
    """Generate sample terrain points following a gaussian distribution."""
    np.random.seed(seed)
    points = []
    for i in range(num_points):
        points.append(Point3D(
            id=i,
            x=np.random.normal(0, 100),
            y=np.random.normal(0, 100),
            z=np.random.normal(0, 10)  # Less variation in height
        ))
    return points

def test_spatial_queries():
    print("\nTesting Spatial Queries:")
    print("-" * 50)
    
    # Create terrain with sample points
    terrain = TerrainManager(precision=0.01)
    points = generate_sample_terrain(1000)
    terrain.add_points(points)
    
    # Test nearest neighbor search
    query_point = Point3D(id=9999, x=0, y=0, z=0)
    nearest = terrain.find_nearest_neighbors(query_point, k=5)
    print(f"\nNearest 5 points to origin:")
    for point in nearest:
        dist = ((point.x ** 2 + point.y ** 2 + point.z ** 2) ** 0.5)
        print(f"Point {point.id}: ({point.x:.2f}, {point.y:.2f}, {point.z:.2f}), Distance: {dist:.2f}")
    
    # Test radius search
    radius = 50
    points_in_radius = terrain.find_points_in_radius(query_point, radius)
    print(f"\nFound {len(points_in_radius)} points within {radius} units of origin")

def test_compression_and_storage():
    print("\nTesting Compression and Storage:")
    print("-" * 50)
    
    # Create and save terrain
    terrain = TerrainManager(precision=0.01)
    points = generate_sample_terrain(10000)
    terrain.add_points(points)
    
    # Get original statistics
    original_stats = terrain.get_statistics()
    print("\nOriginal Terrain Statistics:")
    print(f"Number of points: {original_stats['num_points']}")
    print(f"Bounds: {original_stats['bounds']}")
    print(f"Mean position: {[f'{x:.2f}' for x in original_stats['mean']]}")
    
    # Save to HDF5
    filename = "test_terrain.h5"
    terrain.save_to_hdf5(filename)
    file_size = os.path.getsize(filename) / 1024  # Size in KB
    print(f"\nCompressed terrain saved to {filename}")
    print(f"File size: {file_size:.2f} KB")
    print(f"Bytes per point: {(file_size * 1024) / len(points):.2f}")
    
    # Load and verify
    loaded_terrain = TerrainManager.load_from_hdf5(filename)
    loaded_stats = loaded_terrain.get_statistics()
    print("\nVerifying loaded terrain...")
    print(f"Points preserved: {loaded_stats['num_points'] == original_stats['num_points']}")
    
    # Clean up
    os.remove(filename)

if __name__ == "__main__":
    test_spatial_queries()
    test_compression_and_storage()
