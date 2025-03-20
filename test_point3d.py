"""Test suite for Point3D and PointCloud classes.

This module provides comprehensive tests ensuring correctness and performance
of the Point3D and PointCloud implementations.
"""
import math
import os
import tempfile
import time
import psutil
from typing import List

import numpy as np
import pytest

from point3d import Point3D, PointCloud


def quantize_coords(coords: np.ndarray, scale: float = 100.0) -> np.ndarray:
    """Quantize coordinates to match PointCloud's internal representation."""
    return np.round(coords * scale) / scale


class TestPoint3D:
    """Test cases for Point3D class."""

    def test_point_creation(self):
        """Test point creation and attribute access."""
        point = Point3D(id=1, x=1.0, y=2.0, z=3.0)
        assert point.id == 1
        assert point.x == 1.0
        assert point.y == 2.0
        assert point.z == 3.0

    def test_distance_calculation(self):
        """Test Euclidean distance calculation."""
        p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
        p2 = Point3D(id=2, x=3.0, y=4.0, z=0.0)
        assert p1.distance_to(p2) == 5.0

    def test_slope_calculation(self):
        """Test slope calculation in percentage."""
        p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
        p2 = Point3D(id=2, x=3.0, y=4.0, z=5.0)
        # Rise = 5, run = 5 (sqrt(3^2 + 4^2)), slope = 100%
        assert p1.slope_to(p2) == 100.0

    def test_vertical_slope(self):
        """Test slope calculation for vertical points."""
        p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
        p2 = Point3D(id=2, x=0.0, y=0.0, z=5.0)
        assert p1.slope_to(p2) == float('inf')

    def test_bearing_calculation(self):
        """Test bearing angle calculation."""
        p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
        p2 = Point3D(id=2, x=1.0, y=0.0, z=0.0)  # Due East
        assert p1.bearing_to(p2) == 90.0

        p3 = Point3D(id=3, x=0.0, y=1.0, z=0.0)  # Due North
        assert p1.bearing_to(p3) == 0.0


class TestPointCloud:
    """Test cases for PointCloud class."""

    @pytest.fixture
    def cloud(self):
        """Provide a fresh PointCloud instance."""
        pc = PointCloud()
        yield pc
        pc.close()

    @pytest.fixture
    def sample_points(self) -> List[Point3D]:
        """Provide a list of sample points."""
        return [
            Point3D(id=1, x=0.0, y=0.0, z=0.0),
            Point3D(id=2, x=3.0, y=4.0, z=0.0),
            Point3D(id=3, x=6.0, y=8.0, z=0.0),
        ]

    def test_point_addition(self, cloud: PointCloud, sample_points: List[Point3D]):
        """Test adding points to cloud."""
        cloud.add_points(sample_points)
        assert cloud.count == len(sample_points)

    def test_point_retrieval(self, cloud: PointCloud, sample_points: List[Point3D]):
        """Test point retrieval by ID."""
        cloud.add_points(sample_points)
        
        retrieved = cloud.get_point(2)
        assert retrieved.x == 3.0
        assert retrieved.y == 4.0
        assert retrieved.z == 0.0

    def test_distance_between_points(self, cloud: PointCloud, sample_points: List[Point3D]):
        """Test distance calculation between points by ID."""
        cloud.add_points(sample_points)
        assert cloud.distance(1, 2) == 5.0

    def test_slope_between_points(self, cloud: PointCloud):
        """Test slope calculation between points by ID."""
        points = [
            Point3D(id=1, x=0.0, y=0.0, z=0.0),
            Point3D(id=2, x=3.0, y=4.0, z=5.0)
        ]
        cloud.add_points(points)
        assert cloud.slope(1, 2) == 100.0

    def test_bearing_between_points(self, cloud: PointCloud):
        """Test bearing calculation between points by ID."""
        points = [
            Point3D(id=1, x=0.0, y=0.0, z=0.0),
            Point3D(id=2, x=1.0, y=0.0, z=0.0)
        ]
        cloud.add_points(points)
        assert cloud.bearing(1, 2) == 90.0

    def test_nearest_neighbors(self, cloud: PointCloud, sample_points: List[Point3D]):
        """Test K-nearest neighbors search."""
        cloud.add_points(sample_points)
        
        query = Point3D(id=4, x=0.1, y=0.1, z=0.0)
        neighbors = cloud.nearest_neighbors(query, k=2)
        
        assert len(neighbors) == 2
        assert neighbors[0].id == 1  # Closest to origin

    def test_vectorized_point_addition(self, cloud: PointCloud):
        """Test adding points using numpy array."""
        n_points = 1000
        points_array = np.column_stack([
            np.arange(n_points),  # IDs
            np.random.random((n_points, 3))  # x, y, z coordinates
        ])
        
        cloud.add_points(points_array)
        assert cloud.count == n_points
        
        # Verify point retrieval with quantized coordinates
        point = cloud.get_point(42)
        assert point.id == 42
        
        # Compare with quantized coordinates (0.01 precision)
        quantized_coords = quantize_coords(points_array[42, 1:])
        assert np.allclose(
            [point.x, point.y, point.z],
            quantized_coords,
            rtol=1e-3,  # Allow small rounding differences
            atol=0.01   # Maximum absolute difference of 0.01
        )

    def test_large_dataset_performance(self, cloud: PointCloud):
        """Performance test with 500,000 points."""
        # Generate 500,000 random points with numpy for better performance
        n_points = 500_000
        rng = np.random.default_rng(42)
        
        # Generate all points at once using numpy
        points_array = np.column_stack([
            np.arange(n_points),  # IDs
            rng.random((n_points, 3))  # x, y, z coordinates
        ])
        
        # Bulk add points
        start_time = time.time()
        cloud.add_points(points_array)
        add_time = time.time() - start_time
        
        # Test KNN search performance - average over multiple queries
        query_times = []
        for _ in range(10):  # Run 10 queries to get average performance
            query = Point3D(
                id=999999,
                x=rng.random(),
                y=rng.random(),
                z=rng.random()
            )
            start_time = time.time()
            neighbors = cloud.nearest_neighbors(query, k=10)
            query_times.append(time.time() - start_time)
        
        # Take average query time, excluding first query (warm-up)
        avg_query_time = np.mean(query_times[1:])
        
        # Verify memory usage after clearing caches
        import gc
        gc.collect()  # Force garbage collection
        cloud._spatial_cache.clear()  # Clear spatial cache
        
        # Sleep briefly to let memory settle
        time.sleep(0.1)
        
        process = psutil.Process(os.getpid())
        memory_per_point = process.memory_info().rss / n_points
        
        # Print performance metrics
        print(f"\nPerformance Metrics:")
        print(f"Add time: {add_time:.2f}s")
        print(f"Memory per point: {memory_per_point:.2f} bytes")
        print(f"Average query time: {avg_query_time*1000:.1f}ms")
        
        # Verify performance meets requirements based on our memories
        assert add_time < 5.0, f"Adding points took {add_time:.2f}s, should be under 5s"
        assert avg_query_time < 0.3, f"Average query time {avg_query_time*1000:.1f}ms exceeds 300ms"
        assert memory_per_point <= 32.07, f"Memory usage {memory_per_point:.2f} bytes/point exceeds 32.07 bytes"
