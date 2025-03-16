"""
Demonstrate DXF to Point3D conversion with PointCloud integration.
Shows memory efficiency and layer management capabilities.
"""

from dxf_converter import DxfConverter
from point3d import PointCloud

def main():
    # Initialize converter and cloud
    converter = DxfConverter()
    cloud = PointCloud()
    
    # Show available layers
    layers = converter.get_text_layers('data/plan-masse.dxf')
    print(f'Available layers: {layers}')
    
    # Load points from z value TN layer
    points = converter.load_points_from_file(
        'data/plan-masse.dxf',
        layer='z value TN'  # Using primary terrain layer
    )
    
    # Add points to cloud and track IDs
    point_ids = []
    for point in points:
        cloud.add_point(point)
        point_ids.append(point.id)
    
    # Print statistics
    print(f'\nLoaded {len(points)} points into PointCloud')
    print(f'Memory footprint: 32 bytes per point (8 bytes each for id, x, y, z)')
    print(f'Total memory: {32 * len(points) / 1024:.2f} KB')
    
    # Show some geometric calculations
    if len(point_ids) >= 2:
        # Get two points by ID for calculations
        p1 = cloud.get_point(point_ids[0])
        p2 = cloud.get_point(point_ids[1])
        
        print(f'\nSample calculations between first two points:')
        print(f'Point 1: ({p1.x:.2f}, {p1.y:.2f}, {p1.z:.2f})')
        print(f'Point 2: ({p2.x:.2f}, {p2.y:.2f}, {p2.z:.2f})')
        print(f'Distance: {p1.distance_to(p2):.2f} units')
        print(f'Slope: {p1.slope_to(p2):.2f}%')
        print(f'Bearing: {p1.bearing_to(p2):.2f} degrees')
        
        # Demonstrate slope between points using cloud
        slope = cloud.slope_between_points(point_ids[0], point_ids[1])
        print(f'Slope (via cloud): {slope:.2f}%')

if __name__ == '__main__':
    main()
