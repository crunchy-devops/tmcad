// Global state
let currentModelName = null;
let is3DView = true;

// Show loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Show alert message
function showAlert(message, type = 'danger') {
    const alertContainer = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

// Update terrain statistics
function updateStats(stats) {
    const statsContainer = document.getElementById('terrain-stats');
    statsContainer.innerHTML = `
        <div class="table-responsive">
            <table class="table table-sm">
                <tbody>
                    <tr>
                        <th>Points:</th>
                        <td>${stats.point_count}</td>
                    </tr>
                    <tr>
                        <th>Min Elevation:</th>
                        <td>${stats.min_elevation.toFixed(2)} m</td>
                    </tr>
                    <tr>
                        <th>Max Elevation:</th>
                        <td>${stats.max_elevation.toFixed(2)} m</td>
                    </tr>
                    <tr>
                        <th>Area:</th>
                        <td>${stats.area.toFixed(2)} m²</td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;
}

// Update terrain view
function updateTerrainView(plotHtml) {
    const container = document.getElementById('terrain-view');
    container.innerHTML = plotHtml;
}

// Load available models
async function loadModelList() {
    try {
        const response = await fetch('/api/terrain/list');
        const data = await response.json();
        
        const modelList = document.getElementById('model-list');
        if (data.terrains && data.terrains.length > 0) {
            modelList.innerHTML = data.terrains.map(name => `
                <div class="form-check">
                    <button class="btn btn-link text-decoration-none" onclick="loadModel('${name}')">
                        ${name}
                    </button>
                </div>
            `).join('');
        } else {
            modelList.innerHTML = '<p class="text-muted mb-0">No models available</p>';
        }
    } catch (error) {
        console.error('Error loading model list:', error);
        showAlert('Failed to load available models');
    }
}

// Load model from database
async function loadModel(modelName) {
    showLoading();
    try {
        const response = await fetch('/api/terrain/load', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model_name: modelName })
        });
        
        const data = await response.json();
        if (data.success) {
            currentModelName = data.model_name;
            updateTerrainView(data.plot);
            updateStats(data.stats);
            showAlert(`Model "${modelName}" loaded successfully`, 'success');
        } else {
            showAlert(data.error || 'Failed to load model');
        }
    } catch (error) {
        console.error('Error loading model:', error);
        showAlert('Failed to load model');
    } finally {
        hideLoading();
    }
}

// Get DXF layers
async function getDxfLayers(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/dxf/layers', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.layers) {
            const layerList = document.getElementById('layer-list');
            layerList.innerHTML = data.layers.map(layer => `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${layer}" name="layers[]" id="layer-${layer}">
                    <label class="form-check-label" for="layer-${layer}">
                        ${layer}
                    </label>
                </div>
            `).join('');
        } else {
            throw new Error(data.error || 'Failed to get layers');
        }
    } catch (error) {
        console.error('Error getting layers:', error);
        showAlert('Failed to read DXF layers');
        document.getElementById('dxf-file').value = '';
    }
}

// Handle file selection
document.getElementById('dxf-file').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        showLoading();
        await getDxfLayers(file);
        hideLoading();
    }
});

// Handle form submission
document.getElementById('import-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    showLoading();
    
    const formData = new FormData();
    const file = document.getElementById('dxf-file').files[0];
    const modelName = document.getElementById('model-name').value.trim();
    const selectedLayers = Array.from(document.querySelectorAll('input[name="layers[]"]:checked')).map(cb => cb.value);
    
    if (!modelName) {
        showAlert('Please enter a model name');
        hideLoading();
        return;
    }
    
    if (!file) {
        showAlert('Please select a DXF file');
        hideLoading();
        return;
    }
    
    if (selectedLayers.length === 0) {
        showAlert('Please select at least one layer');
        hideLoading();
        return;
    }
    
    formData.append('file', file);
    formData.append('model_name', modelName);
    selectedLayers.forEach(layer => formData.append('layers[]', layer));
    
    try {
        const response = await fetch('/api/terrain/import', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            currentModelName = data.model_name;
            updateTerrainView(data.plot);
            updateStats(data.stats);
            showAlert('Terrain imported successfully', 'success');
            loadModelList(); // Refresh model list
        } else {
            showAlert(data.error || 'Failed to import terrain');
        }
    } catch (error) {
        console.error('Error importing terrain:', error);
        showAlert('Failed to import terrain');
    } finally {
        hideLoading();
    }
});

// Toggle 3D/2D view
document.getElementById('toggle-3d').addEventListener('click', async () => {
    if (!currentModelName) {
        showAlert('Please import or load a terrain model first');
        return;
    }
    
    is3DView = !is3DView;
    const button = document.getElementById('toggle-3d');
    button.innerHTML = is3DView ? 
        '<i class="bi bi-square"></i> Show 2D' : 
        '<i class="bi bi-cube"></i> Show 3D';
        
    showLoading();
    try {
        const response = await fetch('/api/terrain/plot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_name: currentModelName,
                is_3d: is3DView
            })
        });
        
        const data = await response.json();
        if (data.success) {
            updateTerrainView(data.plot);
        } else {
            showAlert(data.error || 'Failed to update view');
            // Revert the view state
            is3DView = !is3DView;
            button.innerHTML = is3DView ? 
                '<i class="bi bi-square"></i> Show 2D' : 
                '<i class="bi bi-cube"></i> Show 3D';
        }
    } catch (error) {
        console.error('Error updating view:', error);
        showAlert('Failed to update view');
    } finally {
        hideLoading();
    }
});

// Load model list on page load
document.addEventListener('DOMContentLoaded', loadModelList);
