import time
import random
import psutil
import os
from point3d import Point3D, PointCloud

def get_process_memory():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def benchmark_point_creation(num_points):
    """Benchmark point creation and memory usage"""
    start_mem = get_process_memory()
    start_time = time.time()
    
    # Create points
    cloud = PointCloud()
    for i in range(num_points):
        point = Point3D(
            id=i,
            x=random.uniform(-1000, 1000),
            y=random.uniform(-1000, 1000),
            z=random.uniform(-1000, 1000)
        )
        cloud.add_point(point)
    
    end_time = time.time()
    end_mem = get_process_memory()
    
    time_taken = end_time - start_time
    memory_used = end_mem - start_mem
    
    return {
        'points': num_points,
        'time': time_taken,
        'memory': memory_used,
        'points_per_second': num_points / time_taken,
        'bytes_per_point': (memory_used * 1024 * 1024) / num_points
    }

def benchmark_point_access(cloud, num_accesses):
    """Benchmark random point access"""
    max_index = len(cloud) - 1
    start_time = time.time()
    
    # Random index access
    for _ in range(num_accesses):
        idx = random.randint(0, max_index)
        point = cloud.get_point(idx)
    
    index_time = time.time() - start_time
    
    # Random ID access
    start_time = time.time()
    for _ in range(num_accesses):
        point_id = random.randint(0, max_index)
        point = cloud.get_point_by_id(point_id)
    
    id_time = time.time() - start_time
    
    return {
        'accesses': num_accesses,
        'index_access_time': index_time,
        'id_access_time': id_time,
        'index_ops_per_second': num_accesses / index_time,
        'id_ops_per_second': num_accesses / id_time
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
        print(f"Memory used: {creation_stats['memory']:.2f} MB")
        print(f"Points per second: {creation_stats['points_per_second']:,.0f}")
        print(f"Bytes per point: {creation_stats['bytes_per_point']:.2f}")
        
        # Create a cloud for access benchmarks
        cloud = PointCloud()
        for i in range(size):
            point = Point3D(id=i, x=0.0, y=0.0, z=0.0)
            cloud.add_point(point)
        
        # Access benchmark
        num_accesses = min(size, 100000)  # Cap number of accesses for larger datasets
        access_stats = benchmark_point_access(cloud, num_accesses)
        print(f"\nPoint Access Stats ({num_accesses:,} accesses):")
        print(f"Index access time: {access_stats['index_access_time']:.3f} seconds")
        print(f"ID access time: {access_stats['id_access_time']:.3f} seconds")
        print(f"Index ops/second: {access_stats['index_ops_per_second']:,.0f}")
        print(f"ID ops/second: {access_stats['id_ops_per_second']:,.0f}")

if __name__ == "__main__":
    run_benchmarks()
