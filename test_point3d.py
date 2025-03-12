from point3d import Point3D, PointCloud

def test_point_operations():
    # Create test points
    p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
    p2 = Point3D(id=2, x=1.0, y=1.0, z=1.0)
    
    # Test distance calculation
    distance = p1.distance_to(p2)
    assert abs(distance - 1.732050807568877) < 1e-10  # √3
    
    # Test serialization/deserialization
    p1_bytes = p1.to_bytes()
    p1_restored = Point3D.from_bytes(p1_bytes)
    assert p1_restored.id == p1.id
    assert p1_restored.x == p1.x
    assert p1_restored.y == p1.y
    assert p1_restored.z == p1.z
    
    # Test PointCloud container
    cloud = PointCloud()
    cloud.add_point(p1)
    cloud.add_point(p2)
    
    # Test point retrieval
    retrieved_p1 = cloud.get_point(0)
    assert retrieved_p1.id == p1.id
    assert retrieved_p1.x == p1.x
    assert retrieved_p1.y == p1.y
    assert retrieved_p1.z == p1.z
    
    # Test point lookup by ID
    found_p2 = cloud.get_point_by_id(2)
    assert found_p2 is not None
    assert found_p2.id == p2.id
    
    print("All tests passed!")

if __name__ == "__main__":
    test_point_operations()
