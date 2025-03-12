from flask import Flask, render_template, jsonify, request
from terrain_storage import TerrainManager
from dxf_importer import DXFPointExtractor
from point3d import Point3D
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Global terrain manager instance
terrain_manager = None

@app.route('/')
def index():
    """Render main visualization page."""
    return render_template('index.html')

@app.route('/api/load-terrain', methods=['POST'])
def load_terrain():
    """Load terrain data from DXF file."""
    try:
        file_path = request.json.get('file_path')
        global terrain_manager
        
        # Initialize DXF extractor
        extractor = DXFPointExtractor(file_path)
        
        # Extract and process points
        points = extractor.extract_points(layer_name="z value TN")
        terrain_manager = extractor.create_terrain(points, precision=0.01)
        
        # Get terrain bounds for visualization
        stats = extractor.analyze_point_cloud(points)
        bounds = stats['bounds']
        
        return jsonify({
            'status': 'success',
            'message': f'Loaded {len(points)} points',
            'bounds': bounds,
            'point_count': len(points)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/points')
def get_points():
    """Get terrain points with pagination."""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        if not terrain_manager:
            return jsonify([])
            
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        points = []
        for i in range(start_idx, min(end_idx, len(terrain_manager.point_cloud))):
            point = terrain_manager.point_cloud.get_point(i)
            points.append({
                'id': point.id,
                'x': point.x,
                'y': point.y,
                'z': point.z
            })
        
        return jsonify(points)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/point/<int:point_id>', methods=['GET', 'PUT'])
def handle_point(point_id):
    """Get or update a specific point."""
    if not terrain_manager:
        return jsonify({
            'status': 'error',
            'message': 'No terrain loaded'
        }), 400
        
    if request.method == 'GET':
        try:
            point = terrain_manager.point_cloud.get_point_by_id(point_id)
            return jsonify({
                'id': point.id,
                'x': point.x,
                'y': point.y,
                'z': point.z
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 404
            
    elif request.method == 'PUT':
        try:
            data = request.json
            new_point = Point3D(
                id=point_id,
                x=float(data['x']),
                y=float(data['y']),
                z=float(data['z'])
            )
            terrain_manager.update_point(point_id, new_point)
            return jsonify({
                'status': 'success',
                'message': 'Point updated successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

@app.route('/api/terrain-stats')
def get_terrain_stats():
    """Get terrain statistics."""
    if not terrain_manager:
        return jsonify({
            'status': 'error',
            'message': 'No terrain loaded'
        }), 400
        
    try:
        points = [terrain_manager.point_cloud.get_point(i) 
                 for i in range(len(terrain_manager.point_cloud))]
        stats = DXFPointExtractor.analyze_point_cloud(points)
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
