from flask import Flask, render_template, jsonify, request
from terrain_storage import TerrainManager
from dxf_importer import DXFPointExtractor
from point3d import Point3D, PointCloud
import json
import os
from datetime import datetime
from terrain_db import TerrainDatabase

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Global instances
terrain_manager = None
break_lines = []
db = TerrainDatabase('terrain.db')

@app.route('/')
def index():
    """Render main visualization page."""
    return render_template('index.html')

@app.route('/api/load-terrain', methods=['POST'])
def load_terrain():
    """Load terrain data from DXF file."""
    try:
        file_path = request.json.get('file_path')
        global terrain_manager, break_lines
        
        # Initialize DXF extractor with the file
        dxf_extractor = DXFPointExtractor(file_path)
        
        # Extract and process points
        points = dxf_extractor.extract_points(layer_name="z value TN")
        terrain_manager = dxf_extractor.create_terrain(points, precision=0.01)  # Use 0.01 precision as per memory
        break_lines = []  # Reset break lines when loading new terrain
        
        # Get terrain bounds for visualization
        bounds = dxf_extractor.analyze_point_cloud(points)
        
        # Save to database with optimized storage
        name = os.path.basename(file_path)
        db.save_terrain(name, points, bounds, {})
        
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
    if not terrain_manager:
        return jsonify([])
        
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        points = []
        # Use O(1) index-based access as per memory
        point_cloud = terrain_manager.point_cloud
        for i in range(start_idx, min(end_idx, len(point_cloud))):
            point = point_cloud.get_point(i)
            points.append({
                'id': point.id,
                'x': round(point.x, 2),  # Maintain 0.01 precision
                'y': round(point.y, 2),
                'z': round(point.z, 2)
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
        
    try:
        point_cloud = terrain_manager.point_cloud
        # Try to find point by ID using O(1) lookup
        point_index = None
        for i in range(len(point_cloud)):
            if point_cloud.get_point(i).id == point_id:
                point_index = i
                break
                
        if point_index is None:
            return jsonify({
                'status': 'error',
                'message': f'Point with ID {point_id} not found'
            }), 404
            
        point = point_cloud.get_point(point_index)
            
        if request.method == 'GET':
            return jsonify({
                'id': point.id,
                'x': round(point.x, 2),  # Maintain 0.01 precision
                'y': round(point.y, 2),
                'z': round(point.z, 2)
            })
        elif request.method == 'PUT':
            data = request.json
            # Create immutable Point3D as per memory
            new_point = Point3D(
                id=point_id,
                x=round(float(data['x']), 2),  # Maintain 0.01 precision
                y=round(float(data['y']), 2),
                z=round(float(data['z']), 2)
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

@app.route('/api/break-lines', methods=['GET', 'POST'])
def handle_break_lines():
    """Get or add break lines."""
    if not terrain_manager:
        return jsonify({'status': 'error', 'message': 'No terrain loaded'}), 400

    if request.method == 'GET':
        break_line_data = []
        point_cloud = terrain_manager.point_cloud
        
        for line in break_lines:
            points = []
            for point_id in line:
                try:
                    # Find point by ID using O(1) lookup
                    point_index = None
                    for i in range(len(point_cloud)):
                        if point_cloud.get_point(i).id == point_id:
                            point_index = i
                            break
                            
                    if point_index is not None:
                        point = point_cloud.get_point(point_index)
                        points.append({
                            'id': point.id,
                            'x': round(point.x, 2),  # Maintain 0.01 precision
                            'y': round(point.y, 2),
                            'z': round(point.z, 2)
                        })
                except Exception:
                    continue
            if points:  # Only add break line if points were found
                break_line_data.append(points)
        return jsonify(break_line_data)

    elif request.method == 'POST':
        try:
            point_ids = request.json.get('point_ids', [])
            if not point_ids or len(point_ids) < 2:
                return jsonify({
                    'status': 'error',
                    'message': 'Break line must contain at least 2 points'
                }), 400

            # Validate all points exist
            point_cloud = terrain_manager.point_cloud
            valid_points = []
            
            for point_id in point_ids:
                point_found = False
                for i in range(len(point_cloud)):
                    if point_cloud.get_point(i).id == point_id:
                        valid_points.append(point_cloud.get_point(i))
                        point_found = True
                        break
                        
                if not point_found:
                    return jsonify({
                        'status': 'error',
                        'message': f'Point with ID {point_id} not found'
                    }), 400

            break_lines.append(point_ids)
            
            # Calculate bounds using the valid points
            bounds = {
                'x': [float('inf'), float('-inf')],
                'y': [float('inf'), float('-inf')],
                'z': [float('inf'), float('-inf')]
            }
            
            for point in valid_points:
                bounds['x'][0] = min(bounds['x'][0], point.x)
                bounds['x'][1] = max(bounds['x'][1], point.x)
                bounds['y'][0] = min(bounds['y'][0], point.y)
                bounds['y'][1] = max(bounds['y'][1], point.y)
                bounds['z'][0] = min(bounds['z'][0], point.z)
                bounds['z'][1] = max(bounds['z'][1], point.z)
            
            # Save to database with break lines
            name = f"terrain_with_breaklines_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            db.save_terrain(name, valid_points, bounds, {}, break_lines)
            
            return jsonify({'status': 'success', 'message': 'Break line added successfully'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/terrains', methods=['GET'])
def list_terrains():
    """List all saved terrain models."""
    try:
        terrains = db.list_terrains()
        return jsonify([{
            'id': t[0],
            'name': t[1],
            'created_at': t[2],
            'point_count': t[3]
        } for t in terrains])
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/terrains/<int:terrain_id>', methods=['GET', 'DELETE'])
def handle_terrain(terrain_id):
    """Get or delete a specific terrain model."""
    try:
        if request.method == 'GET':
            terrain_data = db.load_terrain(terrain_id)
            return jsonify(terrain_data)
        elif request.method == 'DELETE':
            db.delete_terrain(terrain_id)
            return jsonify({'status': 'success', 'message': 'Terrain deleted successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
