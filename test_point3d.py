"""
Test suite for Point3D and PointCloud implementations.

Provides comprehensive testing of memory efficiency, spatial operations,
and geometric calculations with high code coverage.
"""

import unittest
import math
import numpy as np
from array import array
from point3d import Point3D, PointCloud

class TestPoint3D(unittest.TestCase):
    """Test cases for Point3D class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
        self.p2 = Point3D(id=2, x=3.0, y=4.0, z=0.0)
        self.p3 = Point3D(id=3, x=0.0, y=0.0, z=5.0)
        
    def test_initialization(self):
        """Test point initialization and validation."""
        # Valid initialization
        p = Point3D(id=1, x=1.0, y=2.0, z=3.0)
        self.assertEqual(p.id, 1)
        self.assertEqual(p.x, 1.0)
        self.assertEqual(p.y, 2.0)
        self.assertEqual(p.z, 3.0)
        
        # Invalid ID
        with self.assertRaises(ValueError):
            Point3D(id=-1, x=0.0, y=0.0, z=0.0)
            
        # Invalid coordinates
        with self.assertRaises(ValueError):
            Point3D(id=1, x="invalid", y=0.0, z=0.0)
            
    def test_immutability(self):
        """Test point immutability."""
        p = Point3D(id=1, x=1.0, y=2.0, z=3.0)
        with self.assertRaises(Exception):
            p.x = 4.0
            
    def test_distance_calculation(self):
        """Test distance calculations between points."""
        # Horizontal distance
        self.assertEqual(self.p1.distance_to(self.p2), 5.0)
        
        # Vertical distance
        self.assertEqual(self.p1.distance_to(self.p3), 5.0)
        
        # Zero distance
        self.assertEqual(self.p1.distance_to(self.p1), 0.0)
        
    def test_slope_calculation(self):
        """Test slope calculation between points."""
        # Test horizontal slope (0%)
        p1 = Point3D(id=1, x=0, y=0, z=10)
        p2 = Point3D(id=2, x=10, y=0, z=10)
        self.assertEqual(p1.slope_to(p2), 0.0)

        # Test 100% slope (45 degrees)
        p3 = Point3D(id=3, x=0, y=0, z=0)
        p4 = Point3D(id=4, x=10, y=0, z=10)
        self.assertEqual(p3.slope_to(p4), 100.0)

        # Test -50% slope (downhill)
        p5 = Point3D(id=5, x=0, y=0, z=10)
        p6 = Point3D(id=6, x=10, y=0, z=5)
        self.assertEqual(p5.slope_to(p6), -50.0)

        # Test vertical slope (infinite)
        p7 = Point3D(id=7, x=0, y=0, z=0)
        p8 = Point3D(id=8, x=0, y=0, z=10)
        self.assertEqual(p7.slope_to(p8), float('inf'))

        # Test same point (0%)
        p9 = Point3D(id=9, x=5, y=5, z=5)
        self.assertEqual(p9.slope_to(p9), 0.0)

        # Test diagonal movement with slope
        p10 = Point3D(id=10, x=0, y=0, z=0)
        p11 = Point3D(id=11, x=10, y=10, z=10)
        # For a 45-degree angle in xy plane and 10 units rise,
        # run = sqrt(200), so slope = (10/sqrt(200)) * 100
        expected_slope = (10 / math.sqrt(200)) * 100
        self.assertAlmostEqual(p10.slope_to(p11), expected_slope)
        
    def test_bearing_calculation(self):
        """Test bearing calculations between points."""
        # North
        p_north = Point3D(id=4, x=0.0, y=1.0, z=0.0)
        self.assertEqual(self.p1.bearing_to(p_north), 0.0)
        
        # East
        p_east = Point3D(id=5, x=1.0, y=0.0, z=0.0)
        self.assertEqual(self.p1.bearing_to(p_east), 90.0)
        
        # South
        p_south = Point3D(id=6, x=0.0, y=-1.0, z=0.0)
        self.assertEqual(self.p1.bearing_to(p_south), 180.0)
        
        # West
        p_west = Point3D(id=7, x=-1.0, y=0.0, z=0.0)
        self.assertEqual(self.p1.bearing_to(p_west), 270.0)
        
    def test_array_conversion(self):
        """Test conversion to array format."""
        arr = self.p2.to_array()
        self.assertIsInstance(arr, array)
        self.assertEqual(arr.typecode, 'd')
        self.assertEqual(list(arr), [3.0, 4.0, 0.0])
        
    def test_tuple_conversion(self):
        """Test conversion to tuple format."""
        tup = self.p2.to_tuple()
        self.assertIsInstance(tup, tuple)
        self.assertEqual(tup, (3.0, 4.0, 0.0))

class TestPointCloud(unittest.TestCase):
    """Test cases for PointCloud class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cloud = PointCloud()
        self.p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
        self.p2 = Point3D(id=2, x=3.0, y=4.0, z=0.0)
        self.p3 = Point3D(id=3, x=0.0, y=0.0, z=5.0)
        
        self.cloud.add_point(self.p1)
        self.cloud.add_point(self.p2)
        self.cloud.add_point(self.p3)
        
    def test_point_addition(self):
        """Test adding points to cloud."""
        cloud = PointCloud()
        
        # Add point
        cloud.add_point(self.p1)
        self.assertEqual(len(cloud), 1)
        self.assertTrue(1 in cloud)
        
        # Add duplicate point
        with self.assertRaises(ValueError):
            cloud.add_point(self.p1)
            
    def test_point_retrieval(self):
        """Test point retrieval from cloud."""
        # Get existing point
        p = self.cloud.get_point(1)
        self.assertEqual(p.id, 1)
        self.assertEqual(p.x, 0.0)
        self.assertEqual(p.y, 0.0)
        self.assertEqual(p.z, 0.0)
        
        # Get non-existent point
        with self.assertRaises(KeyError):
            self.cloud.get_point(999)
            
    def test_point_removal(self):
        """Test point removal from cloud."""
        # Remove existing point
        self.cloud.remove_point(1)
        self.assertEqual(len(self.cloud), 2)
        self.assertFalse(1 in self.cloud)
        
        # Remove non-existent point
        with self.assertRaises(KeyError):
            self.cloud.remove_point(999)
            
    def test_nearest_neighbors(self):
        """Test nearest neighbor search."""
        # Single nearest neighbor
        neighbors = self.cloud.nearest_neighbors(Point3D(id=4, x=0.1, y=0.1, z=0.1), k=1)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0][0], 1)  # Should find p1
        
        # Multiple nearest neighbors
        neighbors = self.cloud.nearest_neighbors(Point3D(id=4, x=0.0, y=0.0, z=0.0), k=2)
        self.assertEqual(len(neighbors), 2)
        self.assertEqual(neighbors[0][0], 1)  # Should find p1 first
        
    def test_radius_search(self):
        """Test points within radius search."""
        # Small radius
        points = self.cloud.points_within_radius(self.p1, radius=1.0)
        self.assertEqual(len(points), 1)
        
        # Large radius
        points = self.cloud.points_within_radius(self.p1, radius=6.0)
        self.assertEqual(len(points), 3)
        
    def test_coordinate_access(self):
        """Test direct coordinate access."""
        coords = self.cloud.get_point_coords(1)
        self.assertEqual(coords, (0.0, 0.0, 0.0))
        
        with self.assertRaises(KeyError):
            self.cloud.get_point_coords(999)
            
    def test_points_array(self):
        """Test bulk coordinate access."""
        points = self.cloud.get_points_array()
        self.assertIsInstance(points, np.ndarray)
        self.assertEqual(points.shape, (3, 3))
        
    def test_geometric_operations(self):
        """Test geometric operations between points."""
        # Distance
        self.assertEqual(self.cloud.distance_between(1, 2), 5.0)
        
        # Slope
        self.assertEqual(self.cloud.slope_between_points(1, 2), 0.0)
        p5 = Point3D(id=5, x=0, y=0, z=0)
        p6 = Point3D(id=6, x=10, y=0, z=10)
        self.cloud.add_point(p5)
        self.cloud.add_point(p6)
        self.assertEqual(self.cloud.slope_between_points(5, 6), 100.0)
        
        # Bearing
        self.assertAlmostEqual(self.cloud.bearing_between(1, 2), 53.13010235415598)
        
        # Test cardinal directions
        p7 = Point3D(id=7, x=1.0, y=0.0, z=0.0)  # East
        p8 = Point3D(id=8, x=0.0, y=1.0, z=0.0)  # North
        self.cloud.add_point(p7)
        self.cloud.add_point(p8)
        self.assertEqual(self.cloud.bearing_between(1, 7), 90.0)  # Due East
        self.assertEqual(self.cloud.bearing_between(1, 8), 0.0)   # Due North
        
    def test_iteration(self):
        """Test point cloud iteration."""
        points = list(self.cloud)
        self.assertEqual(len(points), 3)
        self.assertEqual(points[0].id, 1)
        self.assertEqual(points[1].id, 2)
        self.assertEqual(points[2].id, 3)
        
if __name__ == '__main__':
    unittest.main()
