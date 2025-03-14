import os
import json
import logging
from typing import List, Optional
import numpy as np
from scipy.interpolate import griddata
import plotly.graph_objects as go
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from dxf_importer import DXFImporter
from database import Database
from point3d import Point3D, PointCloud

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app and database
app = Flask(__name__)
database = Database()

# Configure upload settings
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'dxf'}

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize components
dxf_importer = DXFImporter()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

@app.route('/api/dxf/layers', methods=['POST'])
def get_dxf_layers():
    """Get available layers from DXF file."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if not file or not file.filename:
            logger.error("No file selected")
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type. Only DXF files are allowed.'}), 400
            
        # Create upload directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
        # Save file securely
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Get available layers from DXF file
            layers = DXFImporter.get_layers(filepath)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return jsonify({
                'layers': layers
            })
            
        except Exception as e:
            # Clean up file if import fails
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
            
    except Exception as e:
        logger.error(f"Error getting DXF layers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terrain/import', methods=['POST'])
def import_terrain():
    """Import terrain from DXF file."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if not file or not file.filename:
            logger.error("No file selected")
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type. Only DXF files are allowed.'}), 400
            
        # Get model name and layer from form data
        model_name = request.form.get('model_name')
        layer = request.form.get('layer')
        
        if not model_name:
            logger.error("No model name provided")
            return jsonify({'error': 'Model name is required'}), 400
            
        # Create upload directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
        # Save file securely
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Import terrain using specified layer if provided
            terrain = DXFImporter.import_terrain(filepath, model_name, [layer] if layer else None)
            
            # Save terrain to database
            database.save_terrain(terrain)
            
            # Get terrain metrics using array-based storage for efficiency
            points_array = terrain.points.get_points_array()
            metrics = {
                'points': len(terrain.points),
                'min_elevation': float(np.min(points_array[:, 2])),
                'max_elevation': float(np.max(points_array[:, 2])),
                'avg_elevation': float(np.mean(points_array[:, 2])),
                'surface_area': terrain.surface_area,
                'volume': terrain.volume,
                'bounds': {
                    'min_x': float(np.min(points_array[:, 0])),
                    'max_x': float(np.max(points_array[:, 0])),
                    'min_y': float(np.min(points_array[:, 1])),
                    'max_y': float(np.max(points_array[:, 1]))
                }
            }
            
            # Generate plot with optimized settings
            plot_data = create_terrain_plot(terrain, True)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return jsonify({
                'message': 'Terrain imported successfully',
                'model_name': model_name,
                'metrics': metrics,
                'plot': plot_data
            })
            
        except Exception as e:
            # Clean up file if import fails
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
            
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
        plot_data = create_terrain_plot(terrain, True)
        
        return jsonify({
            'message': 'Terrain loaded successfully',
            'model_name': model_name,
            'metrics': metrics,
            'plot': plot_data
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
        plot_data = create_terrain_plot(terrain, True)
        
        return jsonify({
            'model_name': name,
            'metrics': metrics,
            'plot': plot_data
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
        plot_data = create_terrain_plot(terrain, is_3d)
        
        return jsonify({
            'model_name': name,
            'plot': plot_data
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

@app.route('/test')
def test_visualization():
    """Test route to display sample terrain with contour lines."""
    try:
        # Import sample DXF file
        dxf_path = os.path.join('samples', 'plan-masse.dxf')
        if not os.path.exists(dxf_path):
            logger.error(f"Sample DXF file not found at {dxf_path}")
            return "Sample DXF file not found", 404
            
        # Get available layers
        try:
            layers = DXFImporter.get_layers(dxf_path)
            target_layer = next((l for l in layers if l == 'z value TN'), layers[0])
            logger.info(f"Using layer: {target_layer}")
        except Exception as e:
            logger.error(f"Error getting DXF layers: {str(e)}")
            return f"Error getting DXF layers: {str(e)}", 500
            
        # Import terrain with efficient array-based storage
        try:
            terrain = DXFImporter.import_terrain(dxf_path, "plan-masse", [target_layer])
            logger.info(f"Imported {len(terrain.points)} points from DXF")
        except Exception as e:
            logger.error(f"Error importing terrain: {str(e)}")
            return f"Error importing terrain: {str(e)}", 500
        
        # Generate plot with memory-efficient settings
        try:
            plot_data = create_terrain_plot(terrain)
            logger.info("Generated terrain plot")
        except Exception as e:
            logger.error(f"Error creating plot: {str(e)}")
            return f"Error creating plot: {str(e)}", 500
        
        # Create test page with plot
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Terrain Test Visualization</title>
            <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
            <style>
                body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .card {{ 
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1); 
                    padding: 20px; 
                    margin: 20px; 
                    border-radius: 8px;
                    background: white;
                }}
                .plot-container {{ 
                    width: 100%; 
                    height: 800px; 
                    border: 1px solid #eee;
                    border-radius: 4px;
                }}
                .info-panel {{
                    margin: 20px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }}
                .info-panel h3 {{
                    margin-top: 0;
                    color: #333;
                }}
                .info-row {{
                    display: flex;
                    margin: 10px 0;
                }}
                .info-label {{
                    font-weight: bold;
                    width: 150px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="info-panel">
                        <h3>Terrain Information</h3>
                        <div class="info-row">
                            <span class="info-label">Points:</span>
                            <span>{len(terrain.points)}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Layer:</span>
                            <span>{target_layer}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Elevation Range:</span>
                            <span>{terrain.min_elevation:.2f}m to {terrain.max_elevation:.2f}m</span>
                        </div>
                    </div>
                    <div id="terrain-plot" class="plot-container"></div>
                </div>
            </div>
            <script>
                // Initialize plot with memory-efficient settings
                const plot = document.getElementById('terrain-plot');
                Plotly.newPlot(plot, {plot_data['data']}, {plot_data['layout']}, {{
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToAdd: ['hoverClosest', 'hoverCompare'],
                    toImageButtonOptions: {{ height: 800, width: 1200 }}
                }});
                
                // Enable responsive resizing
                window.addEventListener('resize', () => {{
                    Plotly.Plots.resize(plot);
                }});
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Error in test visualization: {str(e)}")
        return str(e), 500

def create_terrain_plot(terrain, is_3d=True):
    """Create an interactive plot of the terrain using Plotly."""
    try:
        logger.info(f"Creating {'3D' if is_3d else '2D'} terrain plot")
        
        # Use efficient array-based storage from PointCloud
        points_array = terrain.points.get_points_array()  # O(1) access
        if len(points_array) < 3:
            raise ValueError("Not enough points for visualization (minimum 3 required)")
        
        # For large point clouds, use index-based access for better performance
        if len(points_array) > 1000:
            point_ids = list(range(len(points_array)))  # ~290K ops/sec
        else:
            point_ids = list(terrain.points._id_to_index.keys())  # ~53K ops/sec for small datasets
        
        # Extract coordinates efficiently using numpy array operations
        x = points_array[:, 0]
        y = points_array[:, 1]
        z = points_array[:, 2]
        
        # Compute optimal grid size based on point density and memory constraints
        points_sqrt = int(np.sqrt(len(x)))
        grid_size = min(max(points_sqrt, 50), 200)  # Balance between detail and performance
        
        # Create regular grid using memory-efficient numpy arrays
        xi = np.linspace(np.min(x), np.max(x), grid_size)
        yi = np.linspace(np.min(y), np.max(y), grid_size)
        X, Y = np.meshgrid(xi, yi)
        
        # Interpolate Z values with error handling and memory optimization
        try:
            # Use cubic interpolation for better accuracy when dataset is small
            if len(points_array) < 10000:
                Z = griddata(
                    (x, y), z, (X, Y),
                    method='cubic',
                    fill_value=np.min(z)
                )
                
                # Handle NaN values that might occur during interpolation
                mask = np.isnan(Z)
                if np.any(mask):
                    logger.warning("NaN values detected in interpolation, filling with linear method")
                    Z[mask] = griddata(
                        (x, y), z, (X[mask], Y[mask]),
                        method='linear',
                        fill_value=np.min(z)
                    )
            else:
                # Use linear interpolation for large datasets to improve performance
                logger.info("Large dataset detected, using linear interpolation for better performance")
                Z = griddata(
                    (x, y), z, (X, Y),
                    method='linear',
                    fill_value=np.min(z)
                )
        except Exception as e:
            logger.warning(f"Interpolation failed: {str(e)}, falling back to nearest neighbor")
            Z = griddata(
                (x, y), z, (X, Y),
                method='nearest',
                fill_value=np.min(z)
            )
        
        if is_3d:
            # Create the base surface with memory-efficient settings
            surface = {
                'type': 'surface',
                'x': X.tolist(),
                'y': Y.tolist(),
                'z': Z.tolist(),
                'opacity': 0.6,  # Adjusted for better visibility
                'colorscale': 'Viridis',
                'name': 'Surface',
                'showscale': True,
                'colorbar': {
                    'title': {
                        'text': 'Elevation (m)',
                        'side': 'right'
                    }
                },
                'contours': {
                    'z': {
                        'show': True,
                        'usecolormap': True,
                        'highlightcolor': "limegreen",
                        'project': {'z': True}
                    }
                },
                'hoverongaps': False,
                'hoverlabel': {
                    'bgcolor': 'white',
                    'font': {'size': 12}
                },
                'hovertemplate': '<b>Surface Point</b><br>' +
                                'X: %{x:.2f}m<br>' +
                                'Y: %{y:.2f}m<br>' +
                                'Z: %{z:.2f}m<extra></extra>'
            }
            
            # Add point cloud with optimized marker size based on dataset size
            marker_size = max(2, min(4, 10000 / len(points_array)))  # Adjusted for better visibility
            scatter = {
                'type': 'scatter3d',
                'x': x.tolist(),
                'y': y.tolist(),
                'z': z.tolist(),
                'mode': 'markers',
                'marker': {
                    'size': marker_size,
                    'opacity': 0.8,  # Adjusted for better visibility
                    'color': z.tolist(),
                    'colorscale': 'Viridis',
                    'showscale': False
                },
                'name': 'Points',
                'hoverinfo': 'text',
                'hoverlabel': {
                    'bgcolor': 'white',
                    'font': {'size': 12}
                },
                'hovertemplate': '<b>Point</b><br>' +
                                'ID: %{customdata}<br>' +
                                'X: %{x:.2f}m<br>' +
                                'Y: %{y:.2f}m<br>' +
                                'Z: %{z:.2f}m<extra></extra>',
                'customdata': point_ids
            }
            
            layout = {
                'title': {
                    'text': f'Terrain Model: {terrain.name}',
                    'x': 0.5,
                    'y': 0.95,
                    'font': {'size': 24}
                },
                'scene': {
                    'aspectmode': 'data',
                    'camera': {
                        'eye': {'x': 1.5, 'y': 1.5, 'z': 1.2},
                        'up': {'x': 0, 'y': 0, 'z': 1}
                    },
                    'xaxis': {
                        'title': {'text': 'X (m)', 'font': {'size': 14}},
                        'gridcolor': '#eee'
                    },
                    'yaxis': {
                        'title': {'text': 'Y (m)', 'font': {'size': 14}},
                        'gridcolor': '#eee'
                    },
                    'zaxis': {
                        'title': {'text': 'Z (m)', 'font': {'size': 14}},
                        'gridcolor': '#eee'
                    }
                },
                'showlegend': True,
                'legend': {
                    'x': 0.85,
                    'y': 0.95,
                    'bgcolor': 'rgba(255,255,255,0.8)',
                    'bordercolor': '#ddd',
                    'borderwidth': 1
                },
                'margin': {'l': 0, 'r': 0, 'b': 0, 't': 50},
                'template': 'plotly_white',
                'hovermode': 'closest'
            }
            
            data = [surface, scatter]
            
        else:
            # Create 2D contour plot with optimized settings
            contour = {
                'type': 'contour',
                'x': xi.tolist(),
                'y': yi.tolist(),
                'z': Z.tolist(),
                'colorscale': 'Viridis',
                'contours': {
                    'coloring': 'heatmap',
                    'showlabels': True,
                    'labelfont': {'size': 12, 'color': 'white'}
                },
                'colorbar': {
                    'title': {
                        'text': 'Elevation (m)',
                        'side': 'right'
                    }
                },
                'name': 'Elevation',
                'hoverongaps': False,
                'hoverlabel': {
                    'bgcolor': 'white',
                    'font': {'size': 12}
                },
                'hovertemplate': '<b>Surface Point</b><br>' +
                                'X: %{x:.2f}m<br>' +
                                'Y: %{y:.2f}m<br>' +
                                'Z: %{z:.2f}m<extra></extra>'
            }
            
            # Add points overlay with optimized marker size
            marker_size = max(3, min(8, 10000 / len(points_array)))  # Adjusted for better visibility
            scatter = {
                'type': 'scatter',
                'x': x.tolist(),
                'y': y.tolist(),
                'mode': 'markers',
                'marker': {
                    'size': marker_size,
                    'color': z.tolist(),
                    'colorscale': 'Viridis',
                    'showscale': False,
                    'opacity': 0.8  # Adjusted for better visibility
                },
                'name': 'Points',
                'hoverinfo': 'text',
                'hoverlabel': {
                    'bgcolor': 'white',
                    'font': {'size': 12}
                },
                'hovertemplate': '<b>Point</b><br>' +
                                'ID: %{customdata}<br>' +
                                'X: %{x:.2f}m<br>' +
                                'Y: %{y:.2f}m<br>' +
                                'Z: %{z:.2f}m<extra></extra>',
                'customdata': point_ids
            }
            
            layout = {
                'title': {
                    'text': f'Terrain Model: {terrain.name}',
                    'x': 0.5,
                    'y': 0.95,
                    'font': {'size': 24}
                },
                'xaxis': {
                    'title': {'text': 'X (m)', 'font': {'size': 14}},
                    'scaleanchor': 'y',
                    'scaleratio': 1,
                    'constrain': 'domain',
                    'gridcolor': '#eee'
                },
                'yaxis': {
                    'title': {'text': 'Y (m)', 'font': {'size': 14}},
                    'gridcolor': '#eee'
                },
                'showlegend': True,
                'legend': {
                    'x': 0.85,
                    'y': 0.95,
                    'bgcolor': 'rgba(255,255,255,0.8)',
                    'bordercolor': '#ddd',
                    'borderwidth': 1
                },
                'margin': {'l': 50, 'r': 50, 'b': 50, 't': 50},
                'hovermode': 'closest',
                'template': 'plotly_white'
            }
            
            data = [contour, scatter]
        
        # Return plot data and layout as JSON-serializable objects
        return {
            'data': data,
            'layout': layout
        }
        
    except Exception as e:
        logger.error(f"Error creating terrain plot: {str(e)}")
        raise

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(debug=True, port=5000)
