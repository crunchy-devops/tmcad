"""Memory and performance benchmarks for Point3D and PointCloud classes."""

import time
import random
import psutil
import os
import gc
import numpy as np
from point3d import Point3D, PointCloud

def get_process_memory():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def benchmark_point_creation(num_points):
    """Benchmark point creation and memory usage"""
    # Force garbage collection before starting
    gc.collect()
    time.sleep(0.1)
    
    start_mem = get_process_memory()
    start_time = time.time()
    
    # Create points in batches to reduce overhead
    cloud = PointCloud()
    batch_size = min(10000, num_points)
    for start_idx in range(0, num_points, batch_size):
        end_idx = min(start_idx + batch_size, num_points)
        batch_count = end_idx - start_idx
        
        points = [
            Point3D(
                id=i,
                x=random.uniform(-1000, 1000),
                y=random.uniform(-1000, 1000),
                z=random.uniform(-1000, 1000)
            )
            for i in range(start_idx, end_idx)
        ]
        cloud.add_points(points)
        del points  # Free temporary points after adding to cloud
        gc.collect()  # Clean up temporary objects
    
    end_time = time.time()
    
    # Force garbage collection before measuring final memory
    gc.collect()
    time.sleep(0.1)
    end_mem = get_process_memory()
    
    # Calculate theoretical and actual memory
    theoretical_bytes = num_points * (8 + 8 * 3)  # 8 bytes for id, 8 bytes each for x,y,z
    array_bytes = (len(cloud._ids) * 8 + 24 ) 
    theoretical_mb = theoretical_bytes / (1024 * 1024)
    array_mb = array_bytes / (1024 * 1024)
    total_mb = end_mem - start_mem
    
    time_taken = end_time - start_time
    
    return {
        'points': num_points,
        'time': time_taken,
        'total_memory_mb': total_mb,
        'array_memory_mb': array_mb,
        'theoretical_memory_mb': theoretical_mb,
        'points_per_second': num_points / time_taken,
        'total_bytes_per_point': (total_mb * 1024 * 1024) / num_points,
        'array_bytes_per_point': (array_mb * 1024 * 1024) / num_points,
        'theoretical_bytes_per_point': theoretical_bytes / num_points
    }

def benchmark_point_access(cloud, num_accesses):
    """Benchmark random point access"""
    max_id = cloud.count - 1
    
    # Benchmark index-based access
    start_time = time.time()
    for _ in range(num_accesses):
        idx = random.randint(0, max_id)
        point = cloud.get_point(idx)
        # Verify point integrity
        assert isinstance(point, Point3D)
        assert point.id >= 0
    
    index_time = time.time() - start_time
    
    # Benchmark raw array access
    start_time = time.time()
    for _ in range(num_accesses):
        idx = random.randint(0, max_id)
        i = idx * 3
        x = cloud._coords[i]
        y = cloud._coords[i + 1]
        z = cloud._coords[i + 2]
        id_ = cloud._ids[idx]
    
    array_time = time.time() - start_time
    
    # Benchmark ID-based access
    start_time = time.time()
    ids = list(set(random.randint(0, max_id) for _ in range(min(num_accesses, 1000))))
    for point_id in ids:
        point = cloud.get_point_by_id(point_id)
        if point:
            assert isinstance(point, Point3D)
            assert point.id == point_id
    
    id_time = time.time() - start_time
    id_accesses = len(ids)
    
    return {
        'accesses': num_accesses,
        'index_access_time': index_time,
        'array_access_time': array_time,
        'id_access_time': id_time,
        'id_accesses': id_accesses,
        'index_ops_per_second': num_accesses / index_time,
        'array_ops_per_second': num_accesses / array_time,
        'id_ops_per_second': id_accesses / id_time
    }

def benchmark_nearest_neighbors(cloud, num_queries, k=5):
    """Benchmark nearest neighbor search performance"""
    if cloud.count == 0:
        return None
        
    # Create random query points
    query_points = [
        Point3D(
            id=i + 1000000,  # Use high IDs to avoid conflicts
            x=random.uniform(-1000, 1000),
            y=random.uniform(-1000, 1000),
            z=random.uniform(-1000, 1000)
        )
        for i in range(min(num_queries, 1000))  # Limit number of unique queries
    ]
    
    start_time = time.time()
    for query_point in query_points:
        neighbors = cloud.nearest_neighbors(query_point, k=k)
        # Verify results
        assert len(neighbors) <= k
        assert all(isinstance(p, Point3D) for p in neighbors)
    
    total_time = time.time() - start_time
    
    return {
        'queries': len(query_points),
        'k': k,
        'total_time': total_time,
        'queries_per_second': len(query_points) / total_time
    }

def run_benchmarks():
    print("Running Point3D and PointCloud Benchmarks")
    print("-" * 50)
    
    # Test different dataset sizes
    sizes = [1000, 10000, 100000, 1000000]
    
    for size in sizes:
        print(f"\nTesting with {size:,} points:")
        
        # Creation benchmark
        creation_stats = benchmark_point_creation(size)
        print(f"\nPoint Creation Stats:")
        print(f"Time taken: {creation_stats['time']:.2f} seconds")
        print(f"Points per second: {creation_stats['points_per_second']:,.0f}")
        print("\nMemory Usage:")
        print(f"Theoretical: {creation_stats['theoretical_memory_mb']:.2f} MB " 
              f"({creation_stats['theoretical_bytes_per_point']:.2f} bytes/point)")
        print(f"Array only: {creation_stats['array_memory_mb']:.2f} MB "
              f"({creation_stats['array_bytes_per_point']:.2f} bytes/point)")
        print(f"Total used: {creation_stats['total_memory_mb']:.2f} MB "
              f"({creation_stats['total_bytes_per_point']:.2f} bytes/point)")
        
        # Create a cloud for access benchmarks
        cloud = PointCloud()
        points = [Point3D(id=i, x=0.0, y=0.0, z=0.0) for i in range(size)]
        cloud.add_points(points)
        del points
        gc.collect()
        
        # Access benchmark
        num_accesses = min(size, 100000)  # Cap number of accesses for larger datasets
        access_stats = benchmark_point_access(cloud, num_accesses)
        print(f"\nPoint Access Stats:")
        print(f"Index-based ({num_accesses:,} accesses):")
        print(f"  Time: {access_stats['index_access_time']:.3f} seconds")
        print(f"  Speed: {access_stats['index_ops_per_second']:,.0f} ops/second")
        print(f"\nRaw array ({num_accesses:,} accesses):")
        print(f"  Time: {access_stats['array_access_time']:.3f} seconds")
        print(f"  Speed: {access_stats['array_ops_per_second']:,.0f} ops/second")
        print(f"\nID-based ({access_stats['id_accesses']:,} accesses):")
        print(f"  Time: {access_stats['id_access_time']:.3f} seconds")
        print(f"  Speed: {access_stats['id_ops_per_second']:,.0f} ops/second")
        
        # Nearest neighbor benchmark
        num_queries = min(size, 1000)  # Cap number of queries for larger datasets
        nn_stats = benchmark_nearest_neighbors(cloud, num_queries)
        if nn_stats:
            print(f"\nNearest Neighbor Stats ({nn_stats['queries']:,} queries, k={nn_stats['k']}):")
            print(f"  Time: {nn_stats['total_time']:.3f} seconds")
            print(f"  Speed: {nn_stats['queries_per_second']:,.0f} queries/second")

if __name__ == "__main__":
    run_benchmarks()
