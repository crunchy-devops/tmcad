"""
Test script for terrain visualization with contour lines.
Uses the sample plan-masse.dxf file to validate visualization features.
"""
import os
from dxf_importer import DXFImporter
from flask import Flask, render_template
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_visualization():
    """Test terrain visualization with sample DXF file."""
    dxf_path = os.path.join('data', 'plan-masse.dxf')
    logger.info(f"Testing visualization with {dxf_path}")
    
    # Validate DXF file
    if not DXFImporter.validate_dxf(dxf_path):
        logger.error("Error: Invalid DXF file or missing required layer")
        return
    
    # Import terrain
    logger.info("Importing terrain...")
    terrain = DXFImporter.import_terrain(dxf_path, "plan-masse")
    
    # Get terrain stats
    stats = terrain.get_stats()
    logger.info(f"Imported {len(terrain.points)} points")
    logger.info(f"Elevation range: {stats['bounds']['min_z']:.2f}m to {stats['bounds']['max_z']:.2f}m")
    
    return terrain

if __name__ == "__main__":
    test_visualization()
