"""Tests for TerrainDatabase."""

import unittest
import os
import psutil
from point3d import Point3D
from terrain_db import TerrainDatabase

class TestTerrainDatabase(unittest.TestCase):
    """Test suite for TerrainDatabase."""
    
    def setUp(self):
        """Set up test database."""
        self.db_url = 'sqlite:///:memory:'
        self.db = TerrainDatabase(self.db_url)
        
        # Create test project
        self.project_name = 'test_project'
        self.project = self.db.create_project(self.project_name)
        
        # Create test points
        self.points = [
            Point3D(id=1, x=0.0, y=0.0, z=15.0),
            Point3D(id=2, x=10.0, y=0.0, z=20.0),
            Point3D(id=3, x=0.0, y=10.0, z=25.0),
            Point3D(id=4, x=10.0, y=10.0, z=30.0)
        ]
        
    def tearDown(self):
        """Clean up after test."""
        self.db.Session.close_all()
    
    def test_project_creation(self):
        """Test creating a project."""
        project = self.db.create_project('new_project', 'Test description')
        self.assertEqual(project.name, 'new_project')
        self.assertEqual(project.description, 'Test description')
        
        # Test duplicate project name
        with self.assertRaises(ValueError):
            self.db.create_project('new_project')
    
    def test_point_cloud_creation(self):
        """Test creating point cloud with points."""
        cloud = self.db.create_point_cloud(
            self.project_name,
            'test_cloud',
            self.points
        )
        self.assertEqual(cloud.name, 'test_cloud')
        self.assertEqual(cloud.num_points, len(self.points))
        
        # Test duplicate cloud name in same project
        with self.assertRaises(ValueError):
            self.db.create_point_cloud(
                self.project_name,
                'test_cloud',
                self.points
            )
            
        # Test same cloud name in different project
        other_project = self.db.create_project('other_project')
        cloud2 = self.db.create_point_cloud(
            'other_project',
            'test_cloud',
            self.points
        )
        self.assertEqual(cloud2.name, 'test_cloud')
    
    def test_break_line_storage(self):
        """Test storing break lines."""
        # Create cloud first
        cloud = self.db.create_point_cloud(
            self.project_name,
            'test_cloud',
            self.points
        )
        
        # Add break lines
        lines = [(1, 2), (2, 3), (3, 4)]
        break_lines = self.db.add_break_lines(
            self.project_name,
            'test_cloud',
            lines
        )
        self.assertEqual(len(break_lines), len(lines))
        
        # Test invalid point IDs
        with self.assertRaises(KeyError):
            self.db.add_break_lines(
                self.project_name,
                'test_cloud',
                [(1, 99)]
            )
    
    def test_triangulation_storage(self):
        """Test storing Delaunay triangulation."""
        # Create cloud first
        cloud = self.db.create_point_cloud(
            self.project_name,
            'test_cloud',
            self.points
        )
        
        # Add triangles
        triangles = [(1, 2, 3), (2, 3, 4)]
        properties = [(50.0, 30.0), (50.0, 45.0)]  # area, min_angle
        db_triangles = self.db.store_triangulation(
            self.project_name,
            'test_cloud',
            triangles,
            properties
        )
        self.assertEqual(len(db_triangles), len(triangles))
        
        # Test invalid point IDs
        with self.assertRaises(KeyError):
            self.db.store_triangulation(
                self.project_name,
                'test_cloud',
                [(1, 2, 99)],
                [(50.0, 30.0)]
            )
    
    def test_interpolation_caching(self):
        """Test caching and retrieving interpolated points."""
        # Create cloud first
        cloud = self.db.create_point_cloud(
            self.project_name,
            'test_cloud',
            self.points
        )
        
        # Cache interpolation
        x, y = 5.0, 5.0
        z = 22.5  # Interpolated value
        method = 'barycentric'
        
        point = self.db.cache_interpolation(
            self.project_name,
            'test_cloud',
            x, y, z,
            method
        )
        self.assertEqual(point.x, x)
        self.assertEqual(point.y, y)
        self.assertEqual(point.z, z)
        
        # Retrieve cached value
        cached_z = self.db.get_cached_interpolation(
            self.project_name,
            'test_cloud',
            x, y,
            method
        )
        self.assertEqual(cached_z, z)
        
        # Test non-existent point
        cached_z = self.db.get_cached_interpolation(
            self.project_name,
            'test_cloud',
            100.0, 100.0,
            method
        )
        self.assertIsNone(cached_z)
    
    def test_memory_efficiency(self):
        """Test memory efficiency of database operations."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create large point cloud
        n_points = 10000
        points = [
            Point3D(id=i, x=float(i), y=float(i), z=float(i))
            for i in range(n_points)
        ]
        
        cloud = self.db.create_point_cloud(
            self.project_name,
            'large_cloud',
            points
        )
        
        # Check memory usage
        final_memory = process.memory_info().rss
        memory_per_point = (final_memory - initial_memory) / n_points
        
        # Should be close to 32 bytes per point
        self.assertLess(memory_per_point, 40)  # Allow some overhead
        
if __name__ == '__main__':
    unittest.main()
