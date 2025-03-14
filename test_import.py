from dxf_importer import DXFImporter
from database import Database
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dxf_import():
    """Test DXF import with plan-masse.dxf and validate terrain metrics."""
    logger.info("Starting DXF import test...")
    
    # Initialize components
    importer = DXFImporter()
    database = Database()
    
    # Import terrain
    dxf_path = os.path.join('data', 'plan-masse.dxf')
    logger.info(f"Importing {dxf_path}...")
    
    try:
        # Import terrain
        terrain = importer.import_terrain(dxf_path, "plan-masse")
        
        if not terrain or len(terrain.points) == 0:
            logger.error("No points were imported from the DXF file")
            logger.error("Please check:")
            logger.error("1. DXF file contains TEXT entities in the 'z value TN' layer")
            logger.error("2. TEXT entities contain valid elevation values")
            return
        
        # Get terrain metrics
        metrics = {
            'points': len(terrain.points),
            'min_elevation': terrain.min_elevation,
            'max_elevation': terrain.max_elevation,
            'avg_elevation': terrain.avg_elevation,
            'surface_area': terrain.surface_area,
            'volume': terrain.volume
        }
        
        # Print metrics
        logger.info("\nTerrain Metrics:")
        logger.info(f"Points: {metrics['points']}")
        logger.info(f"Elevation range: {metrics['min_elevation']:.2f}m to {metrics['max_elevation']:.2f}m")
        logger.info(f"Average elevation: {metrics['avg_elevation']:.2f}m")
        logger.info(f"Surface area: {metrics['surface_area']:.2f} m²")
        logger.info(f"Volume: {metrics['volume']:.2f} m³")
        
        # Validate against expected metrics
        expected_metrics = {
            'points': 54,
            'min_elevation': 90.70,
            'max_elevation': 104.40,
            'avg_elevation': 97.55,
            'surface_area': 2150.22,
            'volume': 16344.06
        }
        
        def within_tolerance(actual, expected, tolerance=0.1):
            """Check if actual value is within tolerance of expected value."""
            return abs(actual - expected) <= abs(expected * tolerance)
        
        # Validate metrics
        validation_results = {
            'points': metrics['points'] == expected_metrics['points'],
            'min_elevation': within_tolerance(metrics['min_elevation'], expected_metrics['min_elevation']),
            'max_elevation': within_tolerance(metrics['max_elevation'], expected_metrics['max_elevation']),
            'avg_elevation': within_tolerance(metrics['avg_elevation'], expected_metrics['avg_elevation']),
            'surface_area': within_tolerance(metrics['surface_area'], expected_metrics['surface_area']),
            'volume': within_tolerance(metrics['volume'], expected_metrics['volume'])
        }
        
        # Print validation results
        logger.info("\nValidation Results:")
        for metric, is_valid in validation_results.items():
            logger.info(f"{metric}: {'[PASS]' if is_valid else '[FAIL]'}")
        
        # Save to database if validation passes
        if all(validation_results.values()):
            database.save_terrain(terrain)
            logger.info("\nAll metrics within tolerance!")
            logger.info("Terrain saved to database successfully")
        else:
            logger.warning("\nSome terrain metrics do not match expected values")
            logger.warning("Please check the DXF import process and terrain calculations")
            
    except Exception as e:
        logger.error(f"Error during import test: {str(e)}")

if __name__ == "__main__":
    test_dxf_import()
