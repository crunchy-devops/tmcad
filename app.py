import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dxf_importer import DXFImporter
from database import Database
from terrain_model import TerrainModel
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure directories
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')

# Ensure directories exist
for folder in [UPLOAD_FOLDER, DATA_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    logger.info(f"Created upload folder: {app.config['UPLOAD_FOLDER']}")

def create_terrain_plot(terrain: TerrainModel, is_3d: bool = True) -> str:
    """Create an interactive plot of the terrain using Plotly."""
    logger.info(f"Creating {'3D' if is_3d else '2D'} terrain plot")
    
    points_array = terrain.points.get_points_array()
    point_ids = list(terrain.points._id_to_index.keys())
    
    if is_3d:
        # 3D Surface plot with contour lines
        x = points_array[:, 0]
        y = points_array[:, 1]
        z = points_array[:, 2]
        
        # Create the base surface
        surface = go.Surface(
            x=np.unique(x),
            y=np.unique(y),
            z=griddata((x, y), z, (np.unique(x)[None, :], np.unique(y)[:, None]), method='cubic'),
            opacity=0.6,
            colorscale='Viridis',
            name='Surface',
            showscale=True,
            colorbar=dict(title='Elevation (m)')
        )
        
        # Add contour lines
        contours = go.Surface(
            x=np.unique(x),
            y=np.unique(y),
            z=griddata((x, y), z, (np.unique(x)[None, :], np.unique(y)[:, None]), method='cubic'),
            opacity=0.8,
            showscale=False,
            contours=dict(
                z=dict(
                    show=True,
                    usecolormap=True,
                    highlightcolor="green",
                    project=dict(z=True)
                )
            ),
            name='Contours'
        )
        
        # Add point cloud
        scatter = go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='markers',
            marker=dict(size=3, opacity=0.8),
            name='Points',
            hovertemplate='ID: %{customdata}<br>X: %{x:.2f}m<br>Y: %{y:.2f}m<br>Z: %{z:.2f}m',
            customdata=point_ids
        )
        
        layout = go.Layout(
            scene=dict(
                aspectmode='data',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                xaxis=dict(title='X (m)'),
                yaxis=dict(title='Y (m)'),
                zaxis=dict(title='Z (m)')
            ),
            showlegend=True,
            margin=dict(l=0, r=0, b=0, t=30)
        )
        
        fig = go.Figure(data=[surface, contours, scatter], layout=layout)
        
    else:
        # 2D scatter plot with point IDs and elevations
        scatter = go.Scatter(
            x=points_array[:, 0],
            y=points_array[:, 1],
            mode='markers+text',
            marker=dict(
                size=10,
                color=points_array[:, 2],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Elevation (m)')
            ),
            text=[f'ID: {pid}<br>Z: {z:.2f}m' for pid, z in zip(point_ids, points_array[:, 2])],
            textposition='top center',
            name='Points',
            hovertemplate='ID: %{customdata}<br>X: %{x:.2f}m<br>Y: %{y:.2f}m<br>Z: %{z:.2f}m',
            customdata=point_ids
        )
        
        layout = go.Layout(
            xaxis=dict(title='X (m)', scaleanchor='y', scaleratio=1),
            yaxis=dict(title='Y (m)'),
            showlegend=True,
            margin=dict(l=50, r=50, b=50, t=30),
            hovermode='closest'
        )
        
        fig = go.Figure(data=[scatter], layout=layout)
    
    return fig.to_html(full_html=False, include_plotlyjs=False)

@app.route('/')
def index():
    logger.info("Serving index page")
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

@app.route('/api/dxf/layers', methods=['POST'])
def get_dxf_layers():
    """Get available layers from a DXF file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if not file or not file.filename.endswith('.dxf'):
            return jsonify({'error': 'Invalid file format. Please upload a DXF file.'}), 400
            
        # Save file temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(temp_path)
        
        try:
            # Get layers
            importer = DXFImporter()
            layers = importer.get_layers(temp_path)
            return jsonify({'layers': layers})
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error reading DXF layers: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/import', methods=['POST'])
def import_terrain():
    """Import a terrain from DXF file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if not file or not file.filename.endswith('.dxf'):
            return jsonify({'error': 'Invalid file format. Please upload a DXF file.'}), 400
            
        # Get model name from form
        model_name = request.form.get('model_name', '').strip()
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
            
        # Get selected layers
        layers = request.form.getlist('layers[]')
        if not layers:
            return jsonify({'error': 'At least one layer must be selected'}), 400
            
        logger.info(f"Importing terrain - File: {file.filename}, Model: {model_name}, Layers: {layers}")
            
        # Save file temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(temp_path)
        
        try:
            # Import terrain
            importer = DXFImporter()
            terrain = importer.import_terrain(temp_path, model_name, layers)
            
            # Save to database
            db = Database()
            db.save_terrain(terrain)
            
            # Generate initial plot
            plot_html = create_terrain_plot(terrain, True)
            
            # Return success with plot and stats
            return jsonify({
                'success': True,
                'plot': plot_html,
                'model_name': model_name,
                'stats': terrain.get_stats()
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error importing terrain: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/load', methods=['POST'])
def load_terrain():
    """Load a terrain model from the database."""
    try:
        model_name = request.json.get('model_name', '').strip()
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
            
        logger.info(f"Loading terrain model: {model_name}")
        
        # Load from database
        db = Database()
        terrain = db.load_terrain(model_name)
        
        if not terrain:
            return jsonify({'error': 'Terrain model not found'}), 404
            
        # Generate plot
        plot_html = create_terrain_plot(terrain, True)
        
        return jsonify({
            'success': True,
            'plot': plot_html,
            'model_name': model_name,
            'stats': terrain.get_stats()
        })
        
    except Exception as e:
        logger.error(f"Error loading terrain: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/list', methods=['GET'])
def list_terrains():
    """Get list of available terrain models."""
    try:
        db = Database()
        terrains = db.list_terrains()
        return jsonify({'terrains': terrains})
    except Exception as e:
        logger.error(f"Error listing terrains: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/<name>', methods=['GET'])
def get_terrain(name):
    try:
        db = Database()
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

@app.route('/api/terrain/<name>', methods=['DELETE'])
def delete_terrain(name):
    try:
        db = Database()
        if db.delete_terrain(name):
            return '', 204
        return jsonify({'error': 'Terrain not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting terrain {name}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/plot', methods=['GET'])
def get_terrain_plot():
    """Get terrain plot in 2D or 3D."""
    try:
        name = request.args.get('name')
        is_3d = request.args.get('is_3d', 'true').lower() == 'true'
        
        logger.info(f"Plot request - Name: {name}, 3D: {is_3d}")
        
        if not name:
            logger.error("No terrain name provided")
            return jsonify({'error': 'No terrain name provided'}), 400
            
        db = Database()
        terrain = db.load_terrain(name)
        
        if not terrain:
            logger.error(f"Terrain not found: {name}")
            return jsonify({'error': 'Terrain not found'}), 404
            
        logger.info(f"Creating {'3D' if is_3d else '2D'} plot for terrain: {name}")
        plot_html = create_terrain_plot(terrain, is_3d)
        return jsonify({'plot': plot_html})
        
    except Exception as e:
        logger.error(f"Error generating plot: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/test-visualization')
def test_visualization():
    """Test route to display sample terrain with contour lines."""
    try:
        # Import sample terrain
        dxf_path = os.path.join('data', 'plan-masse.dxf')
        terrain = DXFImporter.import_terrain(dxf_path, "plan-masse")
        
        # Generate plot
        plot_html = create_terrain_plot(terrain)
        
        # Create test page with plot
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Terrain Visualization Test</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                .plot-container {{ height: 800px; }}
            </style>
        </head>
        <body class="bg-light">
            <div class="container py-4">
                <h1 class="mb-4">Terrain Visualization Test</h1>
                <div class="card">
                    <div class="card-body">
                        <div class="plot-container">
                            {plot_html}
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error in test visualization: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(debug=True, port=5000)
