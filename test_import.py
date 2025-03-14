from dxf_importer import DXFImporter
from database import Database
import os

def test_dxf_import():
    """Test DXF import with plan-masse.dxf and validate against known metrics."""
    print("Starting DXF import test...")
    
    # Initialize database
    db = Database('terrain.db')
    
    # Import terrain
    dxf_path = os.path.join('data', 'plan-masse.dxf')
    print(f"Importing {dxf_path}...")
    
    # Validate DXF file
    if not DXFImporter.validate_dxf(dxf_path):
        print("Error: Invalid DXF file or missing required layer")
        return
    
    # Import terrain
    terrain = DXFImporter.import_terrain(dxf_path, "plan-masse")
    
    # Get terrain stats
    stats = terrain.get_stats()
    bounds = stats['bounds']
    point_count = stats['point_count']
    
    # Print and validate metrics
    print("\nImport Results:")
    print(f"Point count: {point_count} (Expected: 54)")
    
    if point_count == 0:
        print("Error: No points were imported from the DXF file")
        print("Please check the following:")
        print("1. DXF file contains points in the 'z value TN' layer")
        print("2. Points are stored as TEXT or POINT entities")
        print("3. Z values are properly formatted")
        return
    
    print("\nTerrain Metrics:")
    print(f"Elevation range: {bounds['min_z']:.2f}m to {bounds['max_z']:.2f}m")
    print(f"Area coverage: {bounds['max_x'] - bounds['min_x']:.1f}m × {bounds['max_y'] - bounds['min_y']:.1f}m")
    
    # Calculate point density
    point_density = terrain.get_point_density()
    print(f"Point density: {point_density:.3f} points/m²")
    
    # Print surface metrics
    print(f"Mean slope: {stats['mean_slope']:.2f}°")
    print(f"Maximum slope: {stats['max_slope']:.2f}°")
    print(f"Surface area: {stats['surface_area']:.2f} m²")
    print(f"Volume: {stats['volume']:.2f} m³")
    
    # Validate against known metrics
    print("\nValidation against known metrics:")
    expected_metrics = {
        'point_count': 54,
        'point_density': 0.01,
        'elevation_range': (90.70, 104.40),
        'mean_slope': 21.53,
        'max_slope': 78.60,
        'surface_area': 2150.22,
        'volume': 16344.06
    }
    
    def within_tolerance(actual, expected, tolerance=0.1):
        """Check if actual value is within tolerance of expected value."""
        if isinstance(expected, tuple):
            return all(abs(a - e) <= abs(e * tolerance) for a, e in zip((bounds['min_z'], bounds['max_z']), expected))
        return abs(actual - expected) <= abs(expected * tolerance)
    
    validation_results = {
        'point_count': point_count == expected_metrics['point_count'],
        'point_density': within_tolerance(point_density, expected_metrics['point_density']),
        'elevation_range': within_tolerance(None, expected_metrics['elevation_range']),
        'mean_slope': within_tolerance(stats['mean_slope'], expected_metrics['mean_slope']),
        'max_slope': within_tolerance(stats['max_slope'], expected_metrics['max_slope']),
        'surface_area': within_tolerance(stats['surface_area'], expected_metrics['surface_area']),
        'volume': within_tolerance(stats['volume'], expected_metrics['volume'])
    }
    
    print("Validation Results:")
    for metric, is_valid in validation_results.items():
        print(f"{metric}: {'[PASS]' if is_valid else '[FAIL]'}")
    
    # Save to database if validation passes
    if all(validation_results.values()):
        terrain_id = db.save_terrain(terrain)
        print(f"\nAll metrics within tolerance!")
        print(f"Saved validated terrain to database with ID: {terrain_id}")
    else:
        print("\nWarning: Some terrain metrics do not match expected values")
        print("Please check the DXF import process and terrain calculations")

if __name__ == "__main__":
    test_dxf_import()
