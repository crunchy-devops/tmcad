"""
Performance benchmarking for Point3D and PointCloud implementations.

Validates memory efficiency and access performance claims.
"""

import time
import random
import gc
import psutil
import os
from point3d import Point3D, PointCloud

def measure_memory():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def benchmark_point_creation(n_points=1_000_000):
    """Benchmark Point3D creation performance."""
    print(f"\nBenchmarking Point3D creation ({n_points:,} points):")
    
    gc.collect()
    start_mem = measure_memory()
    start_time = time.time()
    
    points = []
    for i in range(n_points):
        x = random.uniform(-1000, 1000)
        y = random.uniform(-1000, 1000)
        z = random.uniform(-1000, 1000)
        points.append(Point3D(id=i, x=x, y=y, z=z))
    
    end_time = time.time()
    end_mem = measure_memory()
    
    creation_time = end_time - start_time
    memory_used = end_mem - start_mem
    points_per_second = n_points / creation_time
    bytes_per_point = (memory_used * 1024 * 1024) / n_points
    
    print(f"Creation speed: {points_per_second:,.0f} points/second")
    print(f"Memory per point: {bytes_per_point:.2f} bytes")
    print(f"Total memory: {memory_used:.2f} MB")
    
    return points

def benchmark_point_cloud(points):
    """Benchmark PointCloud operations."""
    n_points = len(points)
    print(f"\nBenchmarking PointCloud ({n_points:,} points):")
    
    # Test addition performance
    gc.collect()
    start_time = time.time()
    cloud = PointCloud()
    for point in points:
        cloud.add_point(point)
    add_time = time.time() - start_time
    print(f"Addition speed: {n_points/add_time:,.0f} points/second")
    
    # Test index-based access
    gc.collect()
    start_time = time.time()
    n_access = 100_000 if n_points > 100_000 else n_points
    for _ in range(n_access):
        idx = random.randint(0, n_points-1)
        cloud.get_point(idx)
    access_time = time.time() - start_time
    print(f"Index access speed: {n_access/access_time:,.0f} ops/second")
    
    # Test nearest neighbor search
    gc.collect()
    start_time = time.time()
    n_searches = 1000 if n_points > 1000 else n_points
    for _ in range(n_searches):
        point = points[random.randint(0, n_points-1)]
        cloud.nearest_neighbors(point, k=5)
    search_time = time.time() - start_time
    print(f"KD-tree search speed: {n_searches/search_time:,.0f} searches/second")
    
    # Test bulk array access
    gc.collect()
    start_time = time.time()
    n_bulk = 100
    for _ in range(n_bulk):
        _ = cloud.get_points_array()
    end_time = time.time()
    bulk_time = end_time - start_time
    if bulk_time > 0:  # Avoid division by zero
        print(f"Bulk array access speed: {n_bulk/bulk_time:,.0f} ops/second")
    else:
        print("Bulk array access too fast to measure accurately")

def main():
    """Run all benchmarks."""
    print("Starting Point3D and PointCloud benchmarks...")
    
    # Small dataset benchmarks
    points_small = benchmark_point_creation(1000)
    benchmark_point_cloud(points_small)
    
    # Large dataset benchmarks
    points_large = benchmark_point_creation(1_000_000)
    benchmark_point_cloud(points_large)

if __name__ == '__main__':
    main()
