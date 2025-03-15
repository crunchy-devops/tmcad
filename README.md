# Memory-Efficient Terrain Point Management

A highly optimized Python implementation for managing large terrain point datasets with minimal memory footprint and efficient spatial operations.

## Features

### Point3D Class
- Memory-efficient immutable points (32 bytes per point)
- Geometric operations (distance, slope, bearing)
- Special handling for cardinal directions
- Array-based data conversion

### PointCloud Class
- O(1) index-based point retrieval
- KD-tree spatial indexing
- Memory-optimized coordinate storage
- Efficient nearest neighbor searches
- Points within radius queries

## Performance

- **Memory Usage**: 32.07 bytes per point
- **Scaling**: ~30MB per million points
- **Point Retrieval**: ~290K ops/sec (index-based)
- **ID Lookup**: 
  - 53K ops/sec for 1K points
  - 70 ops/sec for 1M points

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from point3d import Point3D, PointCloud

# Create points
p1 = Point3D(id=1, x=0.0, y=0.0, z=0.0)
p2 = Point3D(id=2, x=3.0, y=4.0, z=0.0)

# Calculate geometric properties
distance = p1.distance_to(p2)  # 5.0
slope = p1.slope_to(p2)       # 0.0 degrees
bearing = p1.bearing_to(p2)   # 90.0 degrees (east)

# Create point cloud
cloud = PointCloud()
cloud.add_point(p1)
cloud.add_point(p2)

# Find nearest neighbors
neighbors = cloud.nearest_neighbors(p1, k=2)
nearby = cloud.points_within_radius(p1, radius=10.0)

# Efficient bulk operations
points_array = cloud.get_points_array()  # Returns numpy array
```

## Testing

Run the test suite with coverage report:

```bash
python -m pytest test_point3d.py -v --cov=point3d --cov-report=term-missing
```

Current test coverage: 98%

## Implementation Details

### Memory Optimization
- Uses `@dataclass(slots=True, frozen=True)` for minimal footprint
- Stores coordinates in `array.array('d')` for efficient memory use
- Implements O(1) index-based access for performance
- Avoids creating unnecessary Point3D instances

### Spatial Indexing
- Uses scipy's cKDTree for efficient spatial queries
- Lazy KD-tree construction to minimize overhead
- Optimized nearest neighbor and radius searches
- Memory-efficient coordinate storage

### Geometric Operations
- Efficient distance calculations
- Accurate slope determination
- Cardinal direction-aware bearing calculations
- Direct array access for performance

## Requirements

- Python 3.10+
- numpy>=1.21.0
- scipy>=1.7.3
- pytest>=7.1.3 (for testing)
- pytest-cov>=6.0.0 (for coverage)
