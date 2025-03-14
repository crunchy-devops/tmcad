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
const loadingOverlay = document.getElementById('loading-overlay');
const terrainPlot = document.getElementById('terrain-plot');
const debugPanel = document.getElementById('debugPanel');

// Debug logging function
function debugLog(message) {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, -1);
    const logEntry = document.createElement('div');
    logEntry.textContent = `${timestamp} ${message}`;
    debugPanel.appendChild(logEntry);
    debugPanel.scrollTop = debugPanel.scrollHeight;
    console.log(message);
}

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
    debugLog(`Alert shown: ${message} (${type})`);
}

// Function to show loading overlay
function showLoading() {
    loadingOverlay.style.display = 'flex';
    debugLog('Loading overlay shown');
}

// Function to hide loading overlay
function hideLoading() {
    loadingOverlay.style.display = 'none';
    debugLog('Loading overlay hidden');
}

// Function to format terrain statistics
function formatTerrainStats(stats) {
    const bounds = stats.bounds;
    return `
        <div class="mb-3">
            <h6>Point Count</h6>
            <p class="mb-2">${stats.point_count} points</p>
            
            <h6>Terrain Bounds</h6>
            <p class="mb-1">X: ${bounds.min_x.toFixed(2)} to ${bounds.max_x.toFixed(2)} (${(bounds.max_x - bounds.min_x).toFixed(2)} units)</p>
            <p class="mb-1">Y: ${bounds.min_y.toFixed(2)} to ${bounds.max_y.toFixed(2)} (${(bounds.max_y - bounds.min_y).toFixed(2)} units)</p>
            <p class="mb-2">Z: ${bounds.min_z.toFixed(2)} to ${bounds.max_z.toFixed(2)} (${(bounds.max_z - bounds.min_z).toFixed(2)} units)</p>
            
            <h6>Surface Analysis</h6>
            <p class="mb-1">Mean Slope: ${stats.mean_slope}°</p>
            <p class="mb-1">Max Slope: ${stats.max_slope}°</p>
            <p class="mb-1">Surface Area: ${stats.surface_area.toFixed(2)} square units</p>
            <p class="mb-1">Volume above z=0: ${stats.volume.toFixed(2)} cubic units</p>
        </div>
    `;
}

// File Upload Handler
async function uploadDXF() {
    const file = fileInput.files[0];
    const modelName = modelNameInput.value.trim();

    if (!file) {
        showAlert('Please select a DXF file first', 'warning');
        debugLog('No file selected');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.dxf')) {
        showAlert('Please select a valid DXF file', 'warning');
        debugLog('Invalid file type');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (modelName) {
        formData.append('model_name', modelName);
    }

    try {
        uploadButton.disabled = true;
        showLoading();
        debugLog(`Sending request to /api/terrain/import with file: ${file.name}`);
        showAlert('Importing DXF file...', 'info');

        const response = await fetch('/api/terrain/import', {
            method: 'POST',
            body: formData
        });

        debugLog('Received response from server');
        const result = await response.json();
        debugLog(`Response data: ${JSON.stringify(result)}`);

        if (!response.ok) {
            throw new Error(result.error || 'Failed to import DXF file');
        }

        showAlert('DXF file imported successfully!', 'success');
        debugLog('Import completed successfully');
        await loadTerrainList();
        fileInput.value = '';
        modelNameInput.value = '';
    } catch (error) {
        debugLog(`Error: ${error.message}`);
        console.error('Upload error:', error);
        showAlert(error.message, 'danger');
    } finally {
        uploadButton.disabled = false;
        hideLoading();
    }
}

// Load terrain list
async function loadTerrainList() {
    try {
        debugLog('Sending request to /api/terrain/list');
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
        debugLog('Terrain list loaded');
    } catch (error) {
        console.error('Failed to update terrain list:', error);
        debugLog(`Error: ${error.message}`);
        showAlert('Failed to load terrain list', 'danger');
    }
}

// Load and display terrain
async function loadTerrain(name) {
    try {
        debugLog(`Sending request to /api/terrain/${name}`);
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
        debugLog('Terrain plot updated');

        // Update stats display
        terrainStats.innerHTML = formatTerrainStats(terrain.stats);
        debugLog('Terrain stats updated');
    } catch (error) {
        console.error('Failed to load terrain:', error);
        debugLog(`Error: ${error.message}`);
        showAlert('Failed to load terrain data', 'danger');
    }
}

// Delete terrain
async function deleteTerrain(name) {
    if (!confirm(`Are you sure you want to delete terrain "${name}"?`)) {
        return;
    }

    try {
        debugLog(`Sending request to /api/terrain/${name}`);
        const response = await fetch(`/api/terrain/${name}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete terrain');
        }

        showAlert(`Deleted terrain "${name}"`, 'success');
        debugLog(`Terrain "${name}" deleted`);

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
        debugLog(`Error: ${error.message}`);
        showAlert(`Failed to delete terrain "${name}"`, 'danger');
    }
}

// Show loading indicator
function showLoadingIndicator() {
    const loading = document.createElement('div');
    loading.className = 'loading';
    loading.innerHTML = `
        <div class="spinner-border text-primary loading-spinner" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3 text-muted">Processing terrain data...</p>
    `;
    document.getElementById('terrain-view').appendChild(loading);
    debugLog('Loading indicator shown');
}

// Hide loading indicator
function hideLoadingIndicator() {
    const loading = document.querySelector('.loading');
    if (loading) loading.remove();
    debugLog('Loading indicator hidden');
}

// Show elevation plot
function showElevationPlot() {
    if (!currentTerrain) {
        showAlert('Please load a terrain model first', 'warning');
        debugLog('No terrain loaded');
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
    debugLog('Elevation plot shown');
}

// Show slope analysis plot
function showSlopePlot() {
    if (!currentTerrain) {
        showAlert('Please load a terrain model first', 'warning');
        debugLog('No terrain loaded');
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
    debugLog('Slope plot shown');
}

// Toggle 3D/2D view
function toggle3DView() {
    is3DView = !is3DView;
    document.getElementById('terrain-view').classList.toggle('d-none', !is3DView);
    document.getElementById('plot-view').classList.toggle('d-none', is3DView);
    debugLog(`3D view toggled: ${is3DView}`);
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
    debugLog('View reset');
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
    debugLog('Statistics updated');
}

// Event Listeners
uploadButton.addEventListener('click', uploadDXF);

// Initial load
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Application initialized');
    loadTerrainList();
});
