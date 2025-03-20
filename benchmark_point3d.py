"""Benchmark script for Point3D and PointCloud implementations.

This script measures performance metrics for various operations with 500,000 points:
1. Memory usage per point
2. Point creation speed
3. Point addition speed (single vs bulk)
4. Point retrieval speed (index vs ID-based)
5. Spatial query performance (KNN search)
6. Database operations (save/load)
"""
import os
import tempfile
import time
from typing import List, Tuple

import numpy as np
import psutil
from tabulate import tabulate

from point3d import Point3D, PointCloud


def measure_memory() -> int:
    """Get current memory usage in bytes."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss


def format_speed(operations: int, duration: float) -> str:
    """Format operations per second."""
    ops_per_sec = operations / duration
    if ops_per_sec >= 1_000_000:
        return f"{ops_per_sec/1_000_000:.2f}M ops/sec"
    elif ops_per_sec >= 1_000:
        return f"{ops_per_sec/1_000:.2f}K ops/sec"
    return f"{ops_per_sec:.2f} ops/sec"


def benchmark_point_creation(n_points: int) -> Tuple[float, float]:
    """Benchmark Point3D creation."""
    start_mem = measure_memory()
    start_time = time.time()
    
    points = [
        Point3D(id=i, x=1.0, y=2.0, z=3.0)
        for i in range(n_points)
    ]
    
    duration = time.time() - start_time
    memory_per_point = (measure_memory() - start_mem) / n_points
    
    return duration, memory_per_point


def benchmark_point_addition(cloud: PointCloud, points: List[Point3D]) -> float:
    """Benchmark point addition to PointCloud."""
    start_time = time.time()
    
    for point in points:
        cloud.add_point(point)
    
    return time.time() - start_time


def benchmark_bulk_addition(cloud: PointCloud, points_array: np.ndarray) -> float:
    """Benchmark bulk point addition to PointCloud."""
    start_time = time.time()
    cloud.add_points(points_array)
    return time.time() - start_time


def benchmark_point_retrieval(cloud: PointCloud, n_queries: int) -> Tuple[float, float]:
    """Benchmark point retrieval by ID and index."""
    # Warm up caches
    cloud.get_point(0)
    
    # ID-based retrieval
    start_time = time.time()
    for i in range(n_queries):
        point_id = np.random.randint(0, cloud.count)
        cloud.get_point(point_id)
    id_duration = time.time() - start_time
    
    return id_duration


def benchmark_spatial_queries(cloud: PointCloud, n_queries: int) -> List[float]:
    """Benchmark spatial queries (KNN search)."""
    query_times = []
    
    for _ in range(n_queries):
        query = Point3D(
            id=999999,
            x=np.random.random(),
            y=np.random.random(),
            z=np.random.random()
        )
        
        start_time = time.time()
        neighbors = cloud.nearest_neighbors(query, k=10)
        query_times.append(time.time() - start_time)
    
    return query_times


def benchmark_database_ops(cloud: PointCloud) -> Tuple[float, float]:
    """Benchmark database save and load operations."""
    # Save
    start_time = time.time()
    cloud.save_to_db()
    save_duration = time.time() - start_time
    
    # Load
    start_time = time.time()
    cloud.load_from_db()
    load_duration = time.time() - start_time
    
    return save_duration, load_duration


def main():
    """Run benchmarks and display results."""
    N_POINTS = 500_000
    N_QUERIES = 1000
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize cloud
        cloud = PointCloud(db_path=db_path)
        
        # 1. Point creation benchmark
        creation_time, memory_per_point = benchmark_point_creation(N_POINTS)
        
        # 2. Generate test data
        points = [
            Point3D(id=i, x=np.random.random(), y=np.random.random(), z=np.random.random())
            for i in range(N_POINTS)
        ]
        points_array = np.column_stack([
            np.arange(N_POINTS),
            np.random.random((N_POINTS, 3))
        ])
        
        # 3. Point addition benchmarks
        single_add_time = benchmark_point_addition(PointCloud(db_path=db_path), points[:1000])
        bulk_add_time = benchmark_bulk_addition(cloud, points_array)
        
        # 4. Point retrieval benchmark
        retrieval_time = benchmark_point_retrieval(cloud, N_QUERIES)
        
        # 5. Spatial query benchmark
        query_times = benchmark_spatial_queries(cloud, 100)
        
        # 6. Database operation benchmark
        save_time, load_time = benchmark_database_ops(cloud)
        
        # Display results
        results = [
            ["Memory per Point", f"{memory_per_point:.2f} bytes"],
            ["Point Creation", format_speed(N_POINTS, creation_time)],
            ["Single Point Addition (1K points)", format_speed(1000, single_add_time)],
            ["Bulk Point Addition", format_speed(N_POINTS, bulk_add_time)],
            ["Point Retrieval by ID", format_speed(N_QUERIES, retrieval_time)],
            ["Average KNN Query Time", f"{np.mean(query_times)*1000:.2f}ms"],
            ["95th Percentile KNN Query Time", f"{np.percentile(query_times, 95)*1000:.2f}ms"],
            ["Database Save Time", f"{save_time:.2f}s"],
            ["Database Load Time", f"{load_time:.2f}s"]
        ]
        
        print("\nPoint3D and PointCloud Performance Benchmark")
        print(f"Testing with {N_POINTS:,} points\n")
        print(tabulate(results, headers=["Metric", "Value"], tablefmt="grid"))
        
    finally:
        # Cleanup
        cloud.close()
        try:
            os.unlink(db_path)
        except (OSError, PermissionError):
            pass


if __name__ == "__main__":
    main()
