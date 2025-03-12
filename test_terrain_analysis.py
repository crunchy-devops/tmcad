import numpy as np
from point3d import Point3D
from terrain_storage import TerrainManager
from terrain_analysis import TerrainAnalyzer

def generate_hill_terrain(num_points: int = 1000, seed: int = 42) -> TerrainManager:
    """Generate a sample hill-shaped terrain for testing."""
    np.random.seed(seed)
    
    # Create terrain manager
    terrain = TerrainManager(precision=0.01)
    
    # Generate points in a circular pattern with height following a gaussian
    radius = np.sqrt(np.random.uniform(0, 100, num_points))
    theta = np.random.uniform(0, 2*np.pi, num_points)
    
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    # Create a hill shape using gaussian
    z = 50 * np.exp(-(radius**2)/(2*30**2))
    # Add some noise
    z += np.random.normal(0, 0.5, num_points)
    
    # Create and add points
    points = []
    for i in range(num_points):
        point = Point3D(
            id=i,
            x=float(x[i]),
            y=float(y[i]),
            z=float(z[i])
        )
        points.append(point)
    
    terrain.add_points(points)
    return terrain

def test_terrain_analysis():
    print("\nTesting Terrain Analysis Features")
    print("-" * 50)
    
    # Generate sample terrain
    terrain = generate_hill_terrain(1000)
    analyzer = TerrainAnalyzer(terrain)
    
    # Test slope calculation
    center_point = Point3D(id=9999, x=0, y=0, z=50)
    slope = analyzer.calculate_slope(center_point, radius=10.0)
    print(f"\nSlope at center point: {slope:.2f}°")
    
    # Test roughness calculation
    roughness = analyzer.calculate_roughness(center_point, radius=10.0)
    print(f"Roughness at center point: {roughness:.3f} units")
    
    # Generate and test contours
    print("\nGenerating contour lines...")
    contours = analyzer.generate_contours(resolution=2.0)
    print(f"Generated contours at {len(contours)} height levels")
    
    # Calculate volume and surface area
    volume = analyzer.calculate_volume()
    surface_area = analyzer.calculate_surface_area()
    print(f"\nTerrain volume: {volume:.2f} cubic units")
    print(f"Surface area: {surface_area:.2f} square units")
    
    # Comprehensive terrain analysis
    print("\nComprehensive Terrain Analysis:")
    analysis = analyzer.analyze_terrain_features()
    for key, value in analysis.items():
        print(f"{key}: {value:.2f}")

if __name__ == "__main__":
    test_terrain_analysis()
