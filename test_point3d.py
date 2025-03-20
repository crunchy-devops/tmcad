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
        points = [
            Point3D(1, 0, 0, 0),
            Point3D(2, 1, 0, 0),
            Point3D(3, 2, 0, 0),
            Point3D(4, 3, 0, 0)
        ]
        for p in points:
            cloud.add_point(p)

        query = Point3D(999, 0.5, 0, 0)
        neighbors = cloud.nearest_neighbors(query, k=2)
        assert len(neighbors) == 2
        assert neighbors[0].id == 1  # Closest to (0,0,0)
        assert neighbors[1].id == 2  # Second closest

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
        """Performance test with 100,000 points."""
        # Generate 100,000 random points with numpy for better performance
        n_points = 100_000
        rng = np.random.default_rng(42)

        # Generate all points at once using numpy
        points: List[Point3D] = []
        for i in range(n_points):
            points.append(Point3D(
                i,
                rng.random(),
                rng.random(),
                rng.random()
            ))

        # Bulk add points
        start_time = time.time()
        cloud.add_points(points)
        add_time = time.time() - start_time

        # Test KNN search performance - average over multiple queries
        query_times = []
        for _ in range(10):  # Run 10 queries to get average performance
            query = Point3D(
                999999,
                rng.random(),
                rng.random(),
                rng.random()
            )
            start_time = time.time()
            neighbors = cloud.nearest_neighbors(query, k=10)
            query_times.append(time.time() - start_time)

        # Take average query time, excluding first query (warm-up)
        avg_query_time = np.mean(query_times[1:])

        # Verify memory usage
        import gc
        gc.collect()  # Force garbage collection

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
