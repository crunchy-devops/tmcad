import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dxf_importer import DXFImporter
from database import Database
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# Initialize components
dxf_importer = DXFImporter()
database = Database()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'dxf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_terrain_plot(terrain, is_3d=True):
    """Create an interactive plot of the terrain using Plotly."""
    logger.info(f"Creating {'3D' if is_3d else '2D'} terrain plot")
    
    # Get points array efficiently using PointCloud's array-based storage
    points_array = terrain.points.get_points_array()
    point_ids = list(terrain.points._id_to_index.keys())
    
    if is_3d:
        # Create grid for interpolation
        x = points_array[:, 0]
        y = points_array[:, 1]
        z = points_array[:, 2]
        
        # Compute grid size based on point density
        grid_size = int(np.sqrt(len(x)))
        xi = np.linspace(np.min(x), np.max(x), grid_size)
        yi = np.linspace(np.min(y), np.max(y), grid_size)
        
        # Create meshgrid for surface plotting
        X, Y = np.meshgrid(xi, yi)
        Z = griddata((x, y), z, (X, Y), method='cubic')
        
        # Create the base surface
        surface = go.Surface(
            x=xi,
            y=yi,
            z=Z,
            opacity=0.6,
            colorscale='Viridis',
            name='Surface',
            showscale=True,
            colorbar=dict(title='Elevation (m)')
        )
        
        # Add contour lines
        contours = go.Surface(
            x=xi,
            y=yi,
            z=Z,
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
        
        # Add point cloud with efficient hover data
        scatter = go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='markers',
            marker=dict(
                size=3,
                opacity=0.8,
                color=z,
                colorscale='Viridis',
                showscale=False
            ),
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
            margin=dict(l=0, r=0, b=0, t=30),
            title=dict(
                text=f'Terrain Model: {terrain.name}',
                x=0.5,
                y=0.95
            )
        )
        
        fig = go.Figure(data=[surface, contours, scatter], layout=layout)
        
    else:
        # 2D scatter plot with elevation heatmap
        scatter = go.Scatter(
            x=points_array[:, 0],
            y=points_array[:, 1],
            mode='markers',
            marker=dict(
                size=10,
                color=points_array[:, 2],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Elevation (m)')
            ),
            name='Points',
            hovertemplate='ID: %{customdata}<br>X: %{x:.2f}m<br>Y: %{y:.2f}m<br>Z: %{z:.2f}m',
            customdata=point_ids,
            text=[f'{z:.2f}m' for z in points_array[:, 2]],
            textposition='top center'
        )
        
        layout = go.Layout(
            xaxis=dict(title='X (m)', scaleanchor='y', scaleratio=1),
            yaxis=dict(title='Y (m)'),
            showlegend=True,
            margin=dict(l=50, r=50, b=50, t=50),
            hovermode='closest',
            title=dict(
                text=f'Terrain Model: {terrain.name}',
                x=0.5,
                y=0.95
            )
        )
        
        fig = go.Figure(data=[scatter], layout=layout)
    
    return fig.to_html(full_html=False, include_plotlyjs=False)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/dxf/layers', methods=['POST'])
def get_dxf_layers():
    """Get available layers from DXF file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
            
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get layers from DXF
        layers = dxf_importer.get_layers(filepath)
        
        # Clean up
        os.remove(filepath)
        
        return jsonify({'layers': layers})
        
    except Exception as e:
        logger.error(f"Error getting DXF layers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/import', methods=['POST'])
def import_terrain():
    """Import terrain from DXF file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
            
        # Get model name and layer
        model_name = request.form.get('model_name')
        layer = request.form.get('layer', 'z value TN')
        
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
            
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Import terrain
            terrain = dxf_importer.import_terrain(filepath, model_name, layer)
            
            # Save to database
            database.save_terrain(terrain)
            
            # Get terrain metrics
            metrics = {
                'points': len(terrain.points),
                'min_elevation': terrain.min_elevation,
                'max_elevation': terrain.max_elevation,
                'avg_elevation': terrain.avg_elevation,
                'surface_area': terrain.surface_area,
                'volume': terrain.volume,
                'bounds': {
                    'min_x': terrain._stats['bounds']['min_x'],
                    'max_x': terrain._stats['bounds']['max_x'],
                    'min_y': terrain._stats['bounds']['min_y'],
                    'max_y': terrain._stats['bounds']['max_y']
                }
            }
            
            # Generate initial plot
            plot_html = create_terrain_plot(terrain, True)
            
            return jsonify({
                'message': 'Terrain imported successfully',
                'model_name': model_name,
                'metrics': metrics,
                'plot': plot_html
            })
            
        finally:
            # Clean up
            os.remove(filepath)
            
    except Exception as e:
        logger.error(f"Error importing terrain: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/load', methods=['POST'])
def load_terrain():
    """Load terrain model from database."""
    try:
        # Get model name
        model_name = request.json.get('model_name')
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
            
        # Load from database
        terrain = database.load_terrain(model_name)
        if not terrain:
            return jsonify({'error': 'Model not found'}), 404
            
        # Get terrain metrics
        metrics = {
            'points': len(terrain.points),
            'min_elevation': terrain.min_elevation,
            'max_elevation': terrain.max_elevation,
            'avg_elevation': terrain.avg_elevation,
            'surface_area': terrain.surface_area,
            'volume': terrain.volume,
            'bounds': {
                'min_x': terrain._stats['bounds']['min_x'],
                'max_x': terrain._stats['bounds']['max_x'],
                'min_y': terrain._stats['bounds']['min_y'],
                'max_y': terrain._stats['bounds']['max_y']
            }
        }
        
        # Generate plot
        plot_html = create_terrain_plot(terrain, True)
        
        return jsonify({
            'message': 'Terrain loaded successfully',
            'model_name': model_name,
            'metrics': metrics,
            'plot': plot_html
        })
        
    except Exception as e:
        logger.error(f"Error loading terrain: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/<name>/load', methods=['GET'])
def load_terrain_name(name):
    """Load terrain model from database."""
    try:
        terrain = database.load_terrain(name)
        if not terrain:
            return jsonify({'error': 'Terrain model not found'}), 404
            
        metrics = {
            'points': len(terrain.points),
            'min_elevation': terrain.min_elevation,
            'max_elevation': terrain.max_elevation,
            'avg_elevation': terrain.avg_elevation,
            'surface_area': terrain.surface_area,
            'volume': terrain.volume,
            'bounds': {
                'min_x': terrain._stats['bounds']['min_x'],
                'max_x': terrain._stats['bounds']['max_x'],
                'min_y': terrain._stats['bounds']['min_y'],
                'max_y': terrain._stats['bounds']['max_y']
            }
        }
        
        # Generate plot using memory-efficient array-based storage
        plot_html = create_terrain_plot(terrain, True)
        
        return jsonify({
            'model_name': name,
            'metrics': metrics,
            'plot': plot_html
        })
        
    except Exception as e:
        logger.error(f"Error loading terrain model: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/list', methods=['GET'])
def list_terrain():
    """List available terrain models."""
    try:
        models = database.list_terrains()
        return jsonify({'models': models})
    except Exception as e:
        logger.error(f"Error listing terrain models: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/<name>', methods=['GET'])
def get_terrain(name):
    """Get terrain model by name."""
    try:
        terrain = database.load_terrain(name)
        if not terrain:
            return jsonify({'error': 'Terrain model not found'}), 404
            
        metrics = {
            'points': len(terrain.points),
            'min_elevation': terrain.min_elevation,
            'max_elevation': terrain.max_elevation,
            'avg_elevation': terrain.avg_elevation,
            'surface_area': terrain.surface_area,
            'volume': terrain.volume,
            'bounds': {
                'min_x': terrain._stats['bounds']['min_x'],
                'max_x': terrain._stats['bounds']['max_x'],
                'min_y': terrain._stats['bounds']['min_y'],
                'max_y': terrain._stats['bounds']['max_y']
            }
        }
        
        return jsonify({
            'model_name': name,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Error getting terrain model: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/<name>/plot', methods=['GET'])
def get_terrain_plot(name):
    """Get terrain plot in 2D or 3D."""
    try:
        terrain = database.load_terrain(name)
        if not terrain:
            return jsonify({'error': 'Terrain model not found'}), 404
            
        is_3d = request.args.get('type', '3d').lower() == '3d'
        plot_html = create_terrain_plot(terrain, is_3d)
        
        return jsonify({
            'model_name': name,
            'plot': plot_html
        })
        
    except Exception as e:
        logger.error(f"Error generating terrain plot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/<name>', methods=['DELETE'])
def delete_terrain(name):
    """Delete terrain model by name."""
    try:
        if database.delete_terrain(name):
            return jsonify({'message': f'Terrain model {name} deleted successfully'})
        else:
            return jsonify({'error': 'Terrain model not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting terrain model: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-visualization')
def test_visualization():
    """Test route to display sample terrain with contour lines."""
    try:
        # Import sample terrain
        dxf_path = os.path.join('data', 'plan-masse.dxf')
        terrain = dxf_importer.import_terrain(dxf_path, "plan-masse")
        
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
