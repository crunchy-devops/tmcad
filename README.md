# CAD Terrain Model System

A comprehensive Python-based CAD terrain modeling system with efficient point cloud management, terrain analysis, and 3D visualization capabilities.

## Features

### Core Components
- Memory-optimized Point3D system (32 bytes per point)
- Efficient PointCloud storage with array-based implementation
- Terrain modeling with break line support
- Delaunay triangulation for surface construction
- Barycentric interpolation for elevation computation

### Performance Metrics
- Point storage: 32.07 bytes per point
- Linear memory scaling (30.58MB for 1M points)
- Index-based access: ~290K ops/sec
- Point creation speed: ~265K points/second

### Spatial Features
- KD-tree based spatial indexing
- Fast nearest neighbor queries
- Efficient radius-based searches
- O(log n) lookup complexity

### Data Storage
- SQLite database with optimized schema
- HDF5-based storage with GZIP compression
- Coordinate quantization (0.01 precision)
- Compressed storage: ~9.86 bytes per point

### Visualization
- 3D terrain visualization using Three.js
- Interactive point selection
- Break line creation and editing
- 2D/3D view switching
- Terrain statistics display

## Installation

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open a web browser and navigate to `http://localhost:5000`

3. Import terrain data:
   - Click "Choose File" and select a DXF file
   - Click "Import DXF" to load the terrain

4. Create break lines:
   - Click "Start Break Line"
   - Select points in sequence
   - Click "Finish Break Line" to save

## DXF Import Format
The system expects DXF files with the following structure:
- Layer name: "z value TN"
- Point format: TEXT entities with Z values
- Coordinate system: Local coordinates in meters

## Performance Optimization
- Use index-based access for performance-critical operations
- Enable point caching for frequent ID-based lookups
- Batch operations when possible
- Maintain 0.01 coordinate precision for storage efficiency

## API Endpoints

### Terrain Management
- `GET /api/terrains` - List saved terrains
- `GET /api/terrains/<id>` - Load terrain
- `DELETE /api/terrains/<id>` - Delete terrain
- `POST /api/terrains/import` - Import DXF file

### Break Lines
- `POST /api/terrains/<id>/break-lines` - Add break line

### Interpolation
- `GET /api/terrains/<id>/interpolate?x=<x>&y=<y>` - Get interpolated elevation

## License
See LICENSE file for details.
