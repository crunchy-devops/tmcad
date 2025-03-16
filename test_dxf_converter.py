"""
Test suite for DXF to Point3D conversion functionality.

Tests the conversion of DXF text entities to Point3D objects,
with flexible layer selection and management.
"""

import unittest
from unittest.mock import Mock, patch
import os
from pathlib import Path
import ezdxf
from point3d import Point3D
from dxf_converter import DxfConverter, DxfConversionError

class TestDxfConverter(unittest.TestCase):
    """Test cases for DXF to Point3D conversion."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_file = os.path.join('data', 'plan-masse.dxf')
        self.converter = DxfConverter()
        
        # Verify test file exists
        if not os.path.exists(self.test_file):
            raise FileNotFoundError(
                f"Test file {self.test_file} not found. Please ensure it exists in the data directory."
            )
    
    def test_get_text_layers(self):
        """Test retrieving all layers containing TEXT entities."""
        layers = self.converter.get_text_layers(self.test_file)
        
        # Verify expected layers are present
        self.assertIn('z value TN', layers)
        self.assertIsInstance(layers, list)
        self.assertGreater(len(layers), 0)
        
    def test_convert_text_to_point(self):
        """Test conversion of a single DXF text entity to Point3D."""
        # Load a real text entity from the file
        doc = ezdxf.readfile(self.test_file)
        msp = doc.modelspace()
        texts = list(msp.query('TEXT[layer=="z value TN"]'))
        self.assertGreater(len(texts), 0, "No text entities found in z value TN layer")
        text = texts[0]
        
        point = self.converter._convert_text_to_point(text, id=1)
        self.assertIsInstance(point, Point3D)
        self.assertEqual(point.id, 1)
        self.assertIsInstance(point.x, float)
        self.assertIsInstance(point.y, float)
        self.assertIsInstance(point.z, float)
        
    def test_invalid_z_value(self):
        """Test handling of invalid Z value text."""
        mock_text = Mock()
        mock_text.dxf.insert.x = 1.0
        mock_text.dxf.insert.y = 2.0
        mock_text.dxf.text = "invalid"
        mock_text.dxf.layer = "z value TN"
        
        with self.assertRaises(DxfConversionError):
            self.converter._convert_text_to_point(mock_text, id=1)
            
    def test_load_points_from_file(self):
        """Test loading points from a DXF file with specified layer."""
        points = self.converter.load_points_from_file(self.test_file, layer="z value TN")
        
        # Verify points were loaded
        self.assertGreater(len(points), 0)
        for point in points:
            self.assertIsInstance(point, Point3D)
            self.assertIsInstance(point.x, float)
            self.assertIsInstance(point.y, float)
            self.assertIsInstance(point.z, float)
            
    def test_load_points_from_multiple_layers(self):
        """Test loading points from multiple layers."""
        # Use single layer query format for each layer
        points_layer1 = self.converter.load_points_from_file(self.test_file, layer="z value TN")
        points_layer2 = self.converter.load_points_from_file(self.test_file, layer="terrain naturel")
        
        # Verify points from individual layers
        self.assertGreater(len(points_layer1), 0, "No points found in z value TN layer")
        
        # Now load points using the layers parameter
        points = self.converter.load_points_from_file(
            self.test_file, 
            layers=["z value TN", "terrain naturel"]
        )
        
        # Total points should match sum of individual layers
        self.assertEqual(
            len(points), 
            len(points_layer1) + len(points_layer2),
            "Combined layer query should match sum of individual queries"
        )
            
    def test_file_not_found(self):
        """Test handling of non-existent DXF file."""
        with self.assertRaises(DxfConversionError):
            self.converter.load_points_from_file("nonexistent.dxf")
            
    def test_empty_layer(self):
        """Test handling of DXF file with no points in target layer."""
        # Use a layer that doesn't contain any TEXT entities
        points = self.converter.load_points_from_file(self.test_file, layer="Defpoints")
        self.assertEqual(len(points), 0)
        
    def test_memory_efficiency(self):
        """Test memory efficiency of point conversion."""
        import sys
        
        # Load points
        points = self.converter.load_points_from_file(self.test_file, layer="z value TN")
        self.assertGreater(len(points), 0)
        
        # Check memory size of a single point (should be 32 bytes)
        point_size = sys.getsizeof(points[0])
        self.assertLessEqual(point_size, 64)  # Allow some overhead for Python object
        
if __name__ == '__main__':
    unittest.main()
