// Global state
let currentTerrain = null;
let is3DView = true;

// Initialize Plotly layout defaults
const plotlyDefaults = {
    layout: {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { l: 50, r: 20, t: 30, b: 50 },
        font: { family: 'system-ui' }
    }
};

// Initialize Plotly.js 3D surface plot
let plotLayout = {
    title: 'Terrain Visualization',
    scene: {
        camera: {
            eye: { x: 1.5, y: 1.5, z: 1.5 }
        },
        aspectmode: 'data',
        xaxis: { title: 'X (m)' },
        yaxis: { title: 'Y (m)' },
        zaxis: { title: 'Z (m)' }
    },
    showlegend: true,
    margin: { l: 0, r: 0, b: 0, t: 30 }
};

// DOM Elements
const uploadButton = document.getElementById('upload-button');
const fileInput = document.getElementById('dxf-file');
const modelNameInput = document.getElementById('model-name');
const terrainList = document.getElementById('terrain-list');
const terrainStats = document.getElementById('terrain-stats');
const alertContainer = document.getElementById('alert-container');

// Alert System
function showAlert(message, type = 'info', duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alertDiv);

    // Auto-dismiss after duration
    setTimeout(() => {
        if (alertDiv.parentNode === alertContainer) {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }
    }, duration);
}

// File Upload Handler
async function uploadDXF() {
    const file = fileInput.files[0];
    const modelName = modelNameInput.value.trim();

    if (!file) {
        showAlert('Please select a DXF file first', 'warning');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.dxf')) {
        showAlert('Please select a valid DXF file', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (modelName) {
        formData.append('model_name', modelName);
    }

    try {
        uploadButton.disabled = true;
        showAlert('Importing DXF file...', 'info');

        const response = await fetch('/api/terrain/import', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Failed to import DXF file');
        }

        showAlert('DXF file imported successfully!', 'success');
        await loadTerrainList();
        fileInput.value = '';
        modelNameInput.value = '';
    } catch (error) {
        console.error('Upload error:', error);
        showAlert(error.message, 'danger');
    } finally {
        uploadButton.disabled = false;
    }
}

// Load terrain list
async function loadTerrainList() {
    try {
        const response = await fetch('/api/terrain/list');
        const terrains = await response.json();

        terrainList.innerHTML = '';
        terrains.terrains.forEach(terrain => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            item.innerHTML = `
                ${terrain.name}
                <span class="badge bg-primary rounded-pill">${terrain.point_count} points</span>
            `;
            item.onclick = (e) => {
                e.preventDefault();
                loadTerrain(terrain.name);
            };
            terrainList.appendChild(item);
        });
    } catch (error) {
        console.error('Failed to update terrain list:', error);
        showAlert('Failed to load terrain list', 'danger');
    }
}

// Load and display terrain
async function loadTerrain(name) {
    try {
        const response = await fetch(`/api/terrain/${name}`);
        if (!response.ok) {
            throw new Error('Failed to load terrain');
        }

        const terrain = await response.json();
        currentTerrain = terrain;

        // Extract point coordinates and slopes
        const x = terrain.points.map(p => p.x);
        const y = terrain.points.map(p => p.y);
        const z = terrain.points.map(p => p.z);
        const slopes = terrain.points.map(p => p.slope);

        // Create surface plot with slope coloring
        const data = [{
            type: 'scatter3d',
            mode: 'markers',
            x: x,
            y: y,
            z: z,
            marker: {
                size: 3,
                color: slopes,
                colorscale: 'Viridis',
                colorbar: {
                    title: 'Slope (degrees)'
                }
            },
            name: 'Terrain Points'
        }];

        // Update plot
        Plotly.newPlot('plot', data, plotLayout);

        // Update stats display
        updateTerrainStats(terrain);
    } catch (error) {
        console.error('Failed to load terrain:', error);
        showAlert('Failed to load terrain data', 'danger');
    }
}

function updateTerrainStats(terrain) {
    terrainStats.innerHTML = `
        <table class="table table-sm">
            <tbody>
                <tr>
                    <th>Name:</th>
                    <td>${terrain.name}</td>
                </tr>
                <tr>
                    <th>Points:</th>
                    <td>${terrain.point_count}</td>
                </tr>
                <tr>
                    <th>Bounds:</th>
                    <td>
                        X: ${terrain.bounds.min_x.toFixed(2)} to ${terrain.bounds.max_x.toFixed(2)}<br>
                        Y: ${terrain.bounds.min_y.toFixed(2)} to ${terrain.bounds.max_y.toFixed(2)}<br>
                        Z: ${terrain.bounds.min_z.toFixed(2)} to ${terrain.bounds.max_z.toFixed(2)}
                    </td>
                </tr>
            </tbody>
        </table>
    `;
}

// Delete terrain
async function deleteTerrain(name) {
    if (!confirm(`Are you sure you want to delete terrain "${name}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/terrain/${name}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete terrain');
        }

        showAlert(`Deleted terrain "${name}"`, 'success');

        // Clear plot if deleted terrain was displayed
        if (currentTerrain && currentTerrain.name === name) {
            Plotly.purge('plot');
            terrainStats.innerHTML = '';
            currentTerrain = null;
        }

        // Refresh terrain list
        await loadTerrainList();
    } catch (error) {
        console.error('Failed to delete terrain:', error);
        showAlert(`Failed to delete terrain "${name}"`, 'danger');
    }
}

// Show loading indicator
function showLoading() {
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.innerHTML = `
        <div class="spinner-border text-primary loading-spinner" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3 text-muted">Processing terrain data...</p>
    `;
    document.getElementById('terrain-view').appendChild(loading);
}

// Hide loading indicator
function hideLoading() {
    const loading = document.querySelector('.loading');
    if (loading) loading.remove();
}

// Show elevation plot
function showElevationPlot() {
    if (!currentTerrain) {
        showAlert('Please load a terrain model first', 'warning');
        return;
    }

    const points = currentTerrain.points;
    const bounds = currentTerrain.stats.bounds;

    // Create elevation heatmap data
    const data = [{
        type: 'contour',
        x: points.map(p => p.x), // x coordinate
        y: points.map(p => p.y), // y coordinate
        z: points.map(p => p.z), // z coordinate
        colorscale: 'Viridis',
        contours: {
            coloring: 'heatmap'
        },
        colorbar: {
            title: 'Elevation (m)'
        }
    }];

    const layout = {
        ...plotlyDefaults.layout,
        title: 'Terrain Elevation',
        xaxis: { title: 'X (m)' },
        yaxis: { title: 'Y (m)' }
    };

    // Switch to plot view
    document.getElementById('terrain-view').classList.add('d-none');
    const plotView = document.getElementById('plot-view');
    plotView.classList.remove('d-none');

    Plotly.newPlot('plot-view', data, layout);
}

// Show slope analysis plot
function showSlopePlot() {
    if (!currentTerrain) {
        showAlert('Please load a terrain model first', 'warning');
        return;
    }

    const points = currentTerrain.points;
    const stats = currentTerrain.stats;

    // Create slope histogram data
    const data = [{
        type: 'histogram',
        x: points.map(p => p.slope),
        nbinsx: 30,
        name: 'Slope Distribution',
        marker: {
            color: 'rgb(158,202,225)',
            line: {
                color: 'rgb(8,48,107)',
                width: 1
            }
        }
    }];

    const layout = {
        ...plotlyDefaults.layout,
        title: 'Slope Analysis',
        xaxis: { title: 'Slope (degrees)' },
        yaxis: { title: 'Count' },
        bargap: 0.05
    };

    // Switch to plot view
    document.getElementById('terrain-view').classList.add('d-none');
    const plotView = document.getElementById('plot-view');
    plotView.classList.remove('d-none');

    Plotly.newPlot('plot-view', data, layout);
}

// Toggle 3D/2D view
function toggle3DView() {
    is3DView = !is3DView;
    document.getElementById('terrain-view').classList.toggle('d-none', !is3DView);
    document.getElementById('plot-view').classList.toggle('d-none', is3DView);
}

// Reset view
function resetView() {
    if (is3DView) {
        // Reset 3D view
        document.getElementById('terrain-view').classList.remove('d-none');
        document.getElementById('plot-view').classList.add('d-none');
    } else {
        // Reset plot view
        showElevationPlot();
    }
}

// Update statistics display
function updateStats() {
    if (!currentTerrain) return;

    const stats = currentTerrain.stats;
    const statsDiv = document.getElementById('terrain-stats');

    statsDiv.innerHTML = `
        <table class="table table-sm stats-table">
            <tbody>
                <tr>
                    <td>Points</td>
                    <td>${stats.point_count}</td>
                </tr>
                <tr>
                    <td>Elevation Range</td>
                    <td>${stats.bounds.min_z.toFixed(2)}m - ${stats.bounds.max_z.toFixed(2)}m</td>
                </tr>
                <tr>
                    <td>Mean Slope</td>
                    <td>${stats.mean_slope.toFixed(1)}°</td>
                </tr>
                <tr>
                    <td>Max Slope</td>
                    <td>${stats.max_slope.toFixed(1)}°</td>
                </tr>
                <tr>
                    <td>Surface Area</td>
                    <td>${stats.surface_area.toFixed(1)} m²</td>
                </tr>
                <tr>
                    <td>Volume</td>
                    <td>${stats.volume.toFixed(1)} m³</td>
                </tr>
            </tbody>
        </table>
    `;
}

// Event Listeners
uploadButton.addEventListener('click', uploadDXF);

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadTerrainList();
});
