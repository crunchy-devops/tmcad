"""Unit tests for Point3D and PointCloud classes."""
import math
import os
import time
from typing import List

import numpy as np
import psutil
import pytest

from point3d import Point3D, PointCloud


class TestPoint3D:
    """Test Point3D class functionality."""

    def test_point_creation(self):
        """Test point creation and attribute access."""
        point = Point3D(1, 2.5, 3.5, 4.5)
        assert point.id == 1
        assert point.x == 2.5
        assert point.y == 3.5
        assert point.z == 4.5

    def test_invalid_id(self):
        """Test that negative IDs raise ValueError."""
        with pytest.raises(ValueError):
            Point3D(-1, 0.0, 0.0, 0.0)

    def test_distance_calculation(self):
        """Test distance calculation between points."""
        p1 = Point3D(1, 0, 0, 0)
        p2 = Point3D(2, 3, 4, 0)
        assert p1.distance_to(p2) == 5.0

    def test_slope_calculation(self):
        """Test slope calculation between points."""
        p1 = Point3D(1, 0, 0, 0)
        p2 = Point3D(2, 3, 0, 4)
        # Rise = 4, run = 3
        assert p1.slope_to(p2) == pytest.approx(133.33333, rel=1e-5)

    def test_vertical_slope(self):
        """Test slope calculation for vertical lines."""
        p1 = Point3D(1, 0, 0, 0)
        p2 = Point3D(2, 0, 0, 5)
        assert p1.slope_to(p2) == float('inf')
        p3 = Point3D(3, 0, 0, -5)
        assert p1.slope_to(p3) == float('-inf')

    def test_bearing_calculation(self):
        """Test bearing calculation between points."""
        p1 = Point3D(1, 0, 0, 0)
        # Test cardinal directions
        p_north = Point3D(2, 0, 1, 0)
        p_east = Point3D(3, 1, 0, 0)
        p_south = Point3D(4, 0, -1, 0)
        p_west = Point3D(5, -1, 0, 0)

        assert p1.bearing_to(p_north) == pytest.approx(0.0)
        assert p1.bearing_to(p_east) == pytest.approx(90.0)
        assert p1.bearing_to(p_south) == pytest.approx(180.0)
        assert p1.bearing_to(p_west) == pytest.approx(270.0)


@pytest.fixture
def cloud() -> PointCloud:
    """Create a fresh PointCloud instance for each test."""
    return PointCloud()


class TestPointCloud:
    """Test PointCloud class functionality."""

    def test_point_addition(self, cloud: PointCloud):
        """Test adding points to cloud."""
        p1 = Point3D(1, 1.0, 2.0, 3.0)
        cloud.add_point(p1)
        assert cloud.count == 1

        p2 = Point3D(2, 4.0, 5.0, 6.0)
        cloud.add_point(p2)
        assert cloud.count == 2

    def test_point_retrieval(self, cloud: PointCloud):
        """Test retrieving points by ID."""
        original = Point3D(1, 1.0, 2.0, 3.0)
        cloud.add_point(original)
        retrieved = cloud.get_point(1)
        
        assert retrieved.id == original.id
        assert retrieved.x == original.x
        assert retrieved.y == original.y
        assert retrieved.z == original.z

        with pytest.raises(KeyError):
            cloud.get_point(999)

    def test_distance_between_points(self, cloud: PointCloud):
        """Test distance calculation between points by ID."""
        cloud.add_point(Point3D(1, 0, 0, 0))
        cloud.add_point(Point3D(2, 3, 4, 0))
        assert cloud.distance(1, 2) == 5.0

    def test_slope_between_points(self, cloud: PointCloud):
        """Test slope calculation between points by ID."""
        cloud.add_point(Point3D(1, 0, 0, 0))
        cloud.add_point(Point3D(2, 3, 0, 4))
        assert cloud.slope(1, 2) == pytest.approx(133.33333, rel=1e-5)

    def test_bearing_between_points(self, cloud: PointCloud):
        """Test bearing calculation between points by ID."""
        cloud.add_point(Point3D(1, 0, 0, 0))
        cloud.add_point(Point3D(2, 1, 1, 0))  # 45 degrees
        assert cloud.bearing(1, 2) == pytest.approx(45.0)

    def test_nearest_neighbors(self, cloud: PointCloud):
        """Test nearest neighbor search."""
        # Test empty cloud
        query = Point3D(999, 0.5, 0, 0)
        assert len(cloud.nearest_neighbors(query, k=2)) == 0

        # Add test points
        points = [
            Point3D(1, 0, 0, 0),    # Origin
            Point3D(2, 1, 0, 0),    # 1 unit on x-axis
            Point3D(3, 0, 1, 0),    # 1 unit on y-axis
            Point3D(4, 0, 0, 1)     # 1 unit on z-axis
        ]
        for p in points:
            cloud.add_point(p)

        # Test with k=1
        neighbors = cloud.nearest_neighbors(Point3D(999, 0.1, 0.1, 0.1), k=1)
        assert len(neighbors) == 1
        assert neighbors[0].id == 1  # Should be closest to origin

        # Test with k=2
        neighbors = cloud.nearest_neighbors(Point3D(999, 0.9, 0, 0), k=2)
        assert len(neighbors) == 2
        assert neighbors[0].id == 2  # Closest to (1,0,0)
        assert neighbors[1].id == 1  # Second closest is origin

        # Test with k > number of points
        neighbors = cloud.nearest_neighbors(query, k=10)
        assert len(neighbors) == 4  # Should only return available points

    def test_vectorized_point_addition(self, cloud: PointCloud):
        """Test adding multiple points at once."""
        points = [
            Point3D(1, 0, 0, 0),
            Point3D(2, 1, 1, 1),
            Point3D(3, 2, 2, 2)
        ]
        cloud.add_points(points)
        assert cloud.count == 3

        # Verify all points were added correctly
        for p in points:
            stored = cloud.get_point(p.id)
            assert stored.x == p.x
            assert stored.y == p.y
            assert stored.z == p.z

    def test_large_dataset_performance(self, cloud: PointCloud):
        """Performance test with 1000 points to verify memory and speed targets."""
        # Test with 1000 points as per memory metrics
        n_points = 1000
        rng = np.random.default_rng(42)
        
        # Generate coordinates all at once
        coords = rng.random((n_points, 3), dtype=np.float32)
        
        # Create all points first to avoid memory fragmentation
        points = [
            Point3D(i, coords[i, 0], coords[i, 1], coords[i, 2])
            for i in range(n_points)
        ]
        
        # Force garbage collection and measure baseline memory
        import gc
        gc.collect()
        time.sleep(0.1)
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        
        # Measure add performance with multiple iterations
        n_iterations = 5
        add_times = []
        for _ in range(n_iterations):
            cloud = PointCloud()  # Fresh cloud for each iteration
            start_time = time.perf_counter()  # Use high-resolution timer
            cloud.add_points(points)
            add_times.append(time.perf_counter() - start_time)
        
        add_time = np.mean(add_times)  # Average add time
        points_per_sec = n_points / add_time if add_time > 0 else float('inf')
        
        # Clear points list and force garbage collection
        points = None
        coords = None
        gc.collect()
        time.sleep(0.1)
        
        # Test ID-based lookup performance
        n_lookups = 1000  # More lookups for better timing accuracy
        lookup_times = []
        for _ in range(n_iterations):
            start_time = time.perf_counter()
            for _ in range(n_lookups):
                point_id = rng.integers(0, n_points)
                cloud.get_point(point_id)
            lookup_times.append(time.perf_counter() - start_time)
        
        lookup_time = np.mean(lookup_times)  # Average lookup time
        lookups_per_sec = n_lookups / lookup_time if lookup_time > 0 else float('inf')
        
        # Test KNN search performance
        k = 5
        knn_times = []
        query_point = Point3D(999, 0.5, 0.5, 0.5)
        for _ in range(n_iterations):
            start_time = time.perf_counter()
            neighbors = cloud.nearest_neighbors(query_point, k=k)
            knn_times.append(time.perf_counter() - start_time)
            assert len(neighbors) == k
        
        knn_time = np.mean(knn_times)  # Average KNN search time
        
        # Measure final memory usage
        gc.collect()
        time.sleep(0.1)
        final_memory = process.memory_info().rss
        memory_per_point = (final_memory - baseline_memory) / n_points
        
        # Performance assertions based on memory system design
        assert points_per_sec >= 250000, f"Add performance: {points_per_sec:.0f} points/sec"
        assert lookups_per_sec >= 50000, f"Lookup performance: {lookups_per_sec:.0f} lookups/sec"
        assert memory_per_point <= 35.0, f"Memory usage: {memory_per_point:.2f} bytes/point"
        assert knn_time <= 0.001, f"KNN search time: {knn_time*1000:.2f} ms"
