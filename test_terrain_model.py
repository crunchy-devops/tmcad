import os
import pytest
import numpy as np
from point3d import Point3D, PointCloud
from terrain_model import TerrainModel
from dxf_importer import DXFImporter

@pytest.fixture
def simple_terrain():
    """Create a simple terrain with 4 points forming a square."""
    terrain = TerrainModel("test_terrain")
    # Create a 1x1 square with varying heights
    terrain.add_point(Point3D(id=1, x=0.0, y=0.0, z=0.0))
    terrain.add_point(Point3D(id=2, x=1.0, y=0.0, z=1.0))
    terrain.add_point(Point3D(id=3, x=0.0, y=1.0, z=1.0))
    terrain.add_point(Point3D(id=4, x=1.0, y=1.0, z=0.0))
    return terrain

@pytest.fixture
def complex_terrain():
    """Create a more complex terrain with multiple points."""
    terrain = TerrainModel("complex_terrain")
    # Create a 3x3 grid with varying heights
    points = [
        (1, 0.0, 0.0, 0.0), (2, 1.0, 0.0, 1.0), (3, 2.0, 0.0, 0.5),
        (4, 0.0, 1.0, 1.0), (5, 1.0, 1.0, 2.0), (6, 2.0, 1.0, 1.5),
        (7, 0.0, 2.0, 0.5), (8, 1.0, 2.0, 1.5), (9, 2.0, 2.0, 1.0)
    ]
    for pid, x, y, z in points:
        terrain.add_point(Point3D(id=pid, x=x, y=y, z=z))
    return terrain

@pytest.fixture
def dxf_terrain():
    """Create a terrain from a real DXF file."""
    # Get absolute path to DXF file
    dxf_path = os.path.join(os.path.dirname(__file__), 'data', 'plan-masse.dxf')
    
    # Import terrain from DXF using specified layer
    terrain = DXFImporter.import_terrain(dxf_path, "dxf_test_terrain", layers=["z value TN"])
    return terrain

def test_terrain_initialization():
    """Test terrain model initialization."""
    terrain = TerrainModel("test")
    assert terrain.name == "test"
    assert len(terrain.points) == 0
    assert terrain._kdtree is None
    assert terrain._triangulation is None
    assert terrain._break_lines == []

def test_add_point(simple_terrain):
    """Test adding points and bounds updating."""
    # Check point count
    assert len(simple_terrain.points) == 4
    
    # Check bounds
    bounds = simple_terrain._stats['bounds']
    assert bounds['min_x'] == 0.0
    assert bounds['max_x'] == 1.0
    assert bounds['min_y'] == 0.0
    assert bounds['max_y'] == 1.0
    assert bounds['min_z'] == 0.0
    assert bounds['max_z'] == 1.0

def test_add_break_line(simple_terrain):
    """Test adding break lines."""
    # Add valid break line
    simple_terrain.add_break_line([1, 2])
    assert len(simple_terrain._break_lines) == 1
    assert simple_terrain._break_lines[0] == [1, 2]
    
    # Test adding invalid break line
    with pytest.raises(ValueError):
        simple_terrain.add_break_line([1, 999])  # Non-existent point ID

def test_get_nearest_points(complex_terrain):
    """Test nearest point search."""
    # Test single point search
    nearest = complex_terrain.get_nearest_points(0.1, 0.1, k=1)
    assert len(nearest) == 1
    assert nearest[0].id == 1  # Should be closest to point 1
    
    # Test multiple points search
    nearest = complex_terrain.get_nearest_points(1.0, 1.0, k=4)
    assert len(nearest) == 4
    # Point 5 should be exactly at query location
    assert any(p.id == 5 for p in nearest)

def test_interpolate_elevation(complex_terrain):
    """Test elevation interpolation."""
    # Test point exactly at a vertex
    z = complex_terrain.interpolate_elevation(1.0, 1.0)
    assert abs(z - 2.0) < 1e-6  # Should be exactly at point 5
    
    # Test interpolation between points
    z = complex_terrain.interpolate_elevation(0.5, 0.5)
    assert z is not None
    assert 0.0 <= z <= 2.0  # Should be within the range of surrounding points
    
    # Test point outside terrain
    z = complex_terrain.interpolate_elevation(10.0, 10.0)
    assert z is None

def test_compute_surface_metrics(complex_terrain):
    """Test surface metrics computation."""
    complex_terrain.compute_surface_metrics()
    stats = complex_terrain._stats
    
    # Check that all metrics are computed
    assert stats['mean_slope'] >= 0.0
    assert stats['max_slope'] >= 0.0
    assert stats['surface_area'] > 0.0
    assert stats['volume'] >= 0.0
    
    # Check slopes dictionary
    assert len(stats['slopes']) == len(complex_terrain.points)
    for slope in stats['slopes'].values():
        assert 0.0 <= slope <= 90.0  # Slopes should be in degrees

def test_empty_terrain_metrics():
    """Test metrics computation with insufficient points."""
    terrain = TerrainModel("empty")
    terrain.compute_surface_metrics()
    
    # All metrics should be zero
    assert terrain._stats['mean_slope'] == 0.0
    assert terrain._stats['max_slope'] == 0.0
    assert terrain._stats['surface_area'] == 0.0
    assert terrain._stats['volume'] == 0.0

def test_terrain_serialization(complex_terrain):
    """Test terrain serialization."""
    # Get terrain data
    data = complex_terrain.to_dict()
    
    # Check basic properties
    assert data['name'] == "complex_terrain"
    assert len(data['points']) == 9
    assert 'break_lines' in data
    
    # Recreate terrain from data
    new_terrain = TerrainModel.from_dict(data)
    assert new_terrain.name == complex_terrain.name
    assert len(new_terrain.points) == len(complex_terrain.points)
    
    # Compare bounds
    old_bounds = complex_terrain._stats['bounds']
    new_bounds = new_terrain._stats['bounds']
    for key in old_bounds:
        assert abs(old_bounds[key] - new_bounds[key]) < 1e-6

def test_point_immutability():
    """Test Point3D immutability and memory efficiency."""
    point = Point3D(id=1, x=1.0, y=2.0, z=3.0)
    
    # Test slots
    with pytest.raises((AttributeError, TypeError)):
        point.new_attr = 42
    
    # Test immutability
    with pytest.raises(AttributeError):
        point.x = 10.0

def test_point_cloud_efficiency():
    """Test PointCloud memory efficiency and operations."""
    cloud = PointCloud()
    
    # Test array-based storage
    for i in range(1000):
        cloud.add_point(Point3D(id=i, x=float(i), y=float(i), z=float(i)))
    
    # Test numpy array conversion
    points_array = cloud.get_points_array()
    assert isinstance(points_array, np.ndarray)
    assert points_array.shape == (1000, 3)
    
    # Test point caching
    point = cloud.get_point(42)
    cached_point = cloud.get_point(42)
    assert point is cached_point  # Should return same object
    
    # Test cache size limit
    for i in range(2000):  # Access many points to trigger cache cleanup
        cloud.get_point(i % 1000)
    assert len(cloud._cached_points) <= 1000  # Cache should be limited

def test_dxf_terrain_import(dxf_terrain):
    """Test terrain imported from DXF file."""
    # Verify terrain was created
    assert dxf_terrain is not None
    assert len(dxf_terrain.points) > 0
    
    # Check that points have valid coordinates
    bounds = dxf_terrain._stats['bounds']
    assert bounds['min_x'] < bounds['max_x']
    assert bounds['min_y'] < bounds['max_y']
    assert bounds['min_z'] < bounds['max_z']
    
    # Test surface metrics computation
    dxf_terrain.compute_surface_metrics()
    stats = dxf_terrain._stats
    
    # Verify metrics are computed
    assert stats['mean_slope'] >= 0.0
    assert stats['max_slope'] >= 0.0
    assert stats['surface_area'] > 0.0
    assert stats['volume'] >= 0.0
    
    # Test point retrieval performance
    points_array = dxf_terrain.points.get_points_array()
    assert isinstance(points_array, np.ndarray)
    assert points_array.shape[1] == 3  # Each point should have x,y,z
    
    # Test memory efficiency
    point = next(iter(dxf_terrain.points))
    with pytest.raises((AttributeError, TypeError)):
        point.new_attr = 42  # Should fail due to slots
