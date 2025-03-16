"""
Test suite for terrain modeling capabilities of PointCloud.

Tests Delaunay triangulation, barycentric interpolation, break lines,
and DIW interpolation while maintaining memory efficiency.
"""

import unittest
import math
import numpy as np
from point3d import Point3D, PointCloud

class TestTerrainModeling(unittest.TestCase):
    def setUp(self):
        """Create a simple terrain model for testing."""
        self.cloud = PointCloud()
        
        # Create a terrain with a ridge line
        # Points form a valley with a ridge running through it:
        #
        # Z values:
        # 15   10   15    (top row)
        # 10   5    10    (middle row)
        # 15   10   15    (bottom row)
        #
        # Ridge line connects middle points of top and bottom rows,
        # forcing elevation to stay high along that line
        self.points = [
            Point3D(1, 0, 0, 15),  # Bottom left
            Point3D(2, 1, 0, 10),  # Bottom center (ridge point)
            Point3D(3, 2, 0, 15),  # Bottom right
            Point3D(4, 0, 1, 10),  # Middle left
            Point3D(5, 1, 1, 5),   # Center
            Point3D(6, 2, 1, 10),  # Middle right
            Point3D(7, 0, 2, 15),  # Top left
            Point3D(8, 1, 2, 10),  # Top center (ridge point)
            Point3D(9, 2, 2, 15),  # Top right
        ]
        
        for point in self.points:
            self.cloud.add_point(point)
            
    def test_barycentric_interpolation(self):
        """Test barycentric interpolation at known points and midpoints."""
        # Test at known points
        for point in self.points:
            z = self.cloud.interpolate_z(point.x, point.y, method='barycentric')
            self.assertAlmostEqual(z, point.z, places=6)
            
        # Test at center of grid
        z = self.cloud.interpolate_z(1.0, 1.0, method='barycentric')
        self.assertAlmostEqual(z, 5.0, places=6)  # Center point value
        
        # Test at edge midpoint
        z = self.cloud.interpolate_z(0.5, 0.0, method='barycentric')
        self.assertAlmostEqual(z, 12.5, places=6)  # Average of 15 and 10
        
    def test_diw_interpolation(self):
        """Test Distance Inverse Weighting interpolation."""
        # Test at known points
        for point in self.points:
            z = self.cloud.interpolate_z(point.x, point.y, method='diw')
            self.assertAlmostEqual(z, point.z, places=6)
            
        # Test at point with known weighted average
        # Center point should be influenced more by closer points
        z = self.cloud.interpolate_z(1.0, 1.0, method='diw')
        self.assertTrue(4.5 <= z <= 5.5)  # Should be close to center value
        
    def test_break_lines(self):
        """Test break line functionality."""
        # Define a ridge line connecting top and bottom center points
        ridge_line = [(2, 8)]  # Connect bottom center to top center
        self.cloud.break_lines(ridge_line)
        
        # Test points on either side of the ridge line
        # Points slightly left and right of ridge at y=1.0
        z_left = self.cloud.interpolate_z(0.8, 1.0, method='barycentric')
        z_right = self.cloud.interpolate_z(1.2, 1.0, method='barycentric')
        
        # Point on the ridge line
        z_ridge = self.cloud.interpolate_z(1.0, 1.0, method='barycentric')
        
        # Ridge should maintain higher elevation
        self.assertGreater(z_ridge, z_left)
        self.assertGreater(z_ridge, z_right)
        self.assertGreater(z_ridge, 7.0)  # Ridge should be higher than valley
        
        # Test that break line maintains continuity along its length
        z_bottom = self.cloud.interpolate_z(1.0, 0.2, method='barycentric')
        z_top = self.cloud.interpolate_z(1.0, 1.8, method='barycentric')
        
        # Points along ridge should maintain higher elevation
        self.assertGreater(z_bottom, 8.0)
        self.assertGreater(z_top, 8.0)
        
    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        # Test point outside terrain boundary
        with self.assertRaises(ValueError):
            self.cloud.interpolate_z(-1.0, -1.0)
            
        # Test invalid interpolation method
        with self.assertRaises(ValueError):
            self.cloud.interpolate_z(1.0, 1.0, method='invalid')
            
        # Test invalid break line points
        with self.assertRaises(KeyError):
            self.cloud.break_lines([(1, 999)])  # Non-existent point ID
            
        with self.assertRaises(ValueError):
            self.cloud.break_lines([(1, 1)])  # Same point
            
    def test_memory_efficiency(self):
        """Verify memory efficiency of terrain operations."""
        import sys
        
        # Get initial memory size
        initial_size = sys.getsizeof(self.cloud._coords)
        
        # Add more points
        for i in range(1000):
            point = Point3D(
                id=100 + i,
                x=np.random.uniform(0, 2),
                y=np.random.uniform(0, 2),
                z=np.random.uniform(10, 12)
            )
            self.cloud.add_point(point)
            
        # Verify memory growth is linear
        final_size = sys.getsizeof(self.cloud._coords)
        points_added = 1000
        bytes_per_point = (final_size - initial_size) / points_added
        
        # Each point should use ~24 bytes (3 float64 values)
        self.assertLess(bytes_per_point, 25)
        
        # Test interpolation performance
        import time
        start_time = time.time()
        for _ in range(100):
            self.cloud.interpolate_z(1.0, 1.0)
        avg_time = (time.time() - start_time) / 100
        
        # Interpolation should be reasonably fast
        self.assertLess(avg_time, 0.01)  # Less than 10ms per interpolation

if __name__ == '__main__':
    unittest.main()
