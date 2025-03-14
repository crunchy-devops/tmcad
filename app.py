import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dxf_importer import DXFImporter
from database import Database
from terrain_model import TerrainModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = Database()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/import', methods=['POST'])
def import_terrain():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.dxf'):
            return jsonify({'error': 'Invalid file type. Please upload a DXF file'}), 400

        # Secure the filename and save
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Import terrain from DXF
            model_name = request.form.get('model_name', os.path.splitext(filename)[0])
            terrain = DXFImporter.import_terrain(filepath, model_name)
            
            # Save to database
            db.save_terrain(terrain)
            
            # Return success response
            return jsonify({
                'name': terrain.name,
                'point_count': len(terrain.points),
                'bounds': terrain.bounds
            })

        finally:
            # Clean up uploaded file
            os.remove(filepath)

    except Exception as e:
        logger.error(f"Error importing terrain: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/terrains', methods=['GET'])
def list_terrains():
    try:
        terrains = []
        for terrain in db.list_terrains():
            terrains.append({
                'name': terrain.name,
                'point_count': len(terrain.points)
            })
        return jsonify(terrains)
    except Exception as e:
        logger.error(f"Error listing terrains: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/terrain/<name>', methods=['GET'])
def get_terrain(name):
    try:
        terrain = db.get_terrain(name)
        if not terrain:
            return jsonify({'error': 'Terrain not found'}), 404

        return jsonify({
            'name': terrain.name,
            'point_count': len(terrain.points),
            'bounds': terrain.bounds,
            'points': [
                [p.x, p.y, p.z] for p in terrain.points
            ]
        })
    except Exception as e:
        logger.error(f"Error getting terrain {name}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/terrain/<name>', methods=['DELETE'])
def delete_terrain(name):
    try:
        if db.delete_terrain(name):
            return '', 204
        return jsonify({'error': 'Terrain not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting terrain {name}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
