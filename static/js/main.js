// Main JavaScript file for terrain visualization

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI components
    const fileInput = document.getElementById('file-input');
    const modelNameInput = document.getElementById('model-name');
    const importButton = document.getElementById('import-button');
    const loadModelSelect = document.getElementById('load-model-select');
    const loadButton = document.getElementById('load-button');
    const plotContainer = document.getElementById('plot-container');
    const metricsContainer = document.getElementById('metrics-container');
    const loadingSpinner = document.createElement('div');
    loadingSpinner.className = 'spinner';
    loadingSpinner.style.display = 'none';
    document.body.appendChild(loadingSpinner);

    // Show loading spinner
    function showLoading() {
        loadingSpinner.style.display = 'block';
    }

    // Hide loading spinner
    function hideLoading() {
        loadingSpinner.style.display = 'none';
    }

    // Display error message
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    // Display success message
    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        document.body.appendChild(successDiv);
        setTimeout(() => successDiv.remove(), 5000);
    }

    // Display terrain metrics with bounds
    function displayMetrics(metrics) {
        metricsContainer.innerHTML = `
            <h3>Terrain Metrics</h3>
            <table>
                <tr><td>Points:</td><td>${metrics.points}</td></tr>
                <tr><td>Min Elevation:</td><td>${metrics.min_elevation.toFixed(2)} m</td></tr>
                <tr><td>Max Elevation:</td><td>${metrics.max_elevation.toFixed(2)} m</td></tr>
                <tr><td>Average Elevation:</td><td>${metrics.avg_elevation.toFixed(2)} m</td></tr>
                <tr><td>Surface Area:</td><td>${metrics.surface_area.toFixed(2)} m²</td></tr>
                <tr><td>Volume:</td><td>${metrics.volume.toFixed(2)} m³</td></tr>
                <tr><td>X Range:</td><td>${metrics.bounds.min_x.toFixed(2)} m to ${metrics.bounds.max_x.toFixed(2)} m</td></tr>
                <tr><td>Y Range:</td><td>${metrics.bounds.min_y.toFixed(2)} m to ${metrics.bounds.max_y.toFixed(2)} m</td></tr>
            </table>
        `;
    }

    // Update available models list
    async function updateModelsList() {
        try {
            const response = await fetch('/api/terrain/list');
            const data = await response.json();
            
            if (response.ok) {
                loadModelSelect.innerHTML = '';
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    loadModelSelect.appendChild(option);
                });
            } else {
                showError(data.error || 'Failed to fetch models list');
            }
        } catch (error) {
            showError('Error fetching models list: ' + error.message);
        }
    }

    // Get available layers from DXF file
    async function getDXFLayers(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/dxf/layers', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                return data.layers;
            } else {
                throw new Error(data.error || 'Failed to get DXF layers');
            }
        } catch (error) {
            throw error;
        }
    }

    // Import terrain from DXF file
    async function importTerrain(file, modelName) {
        showLoading();
        
        try {
            // Get available layers first
            const layers = await getDXFLayers(file);
            const targetLayer = layers.find(l => l === 'z value TN') || layers[0];
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('model_name', modelName);
            formData.append('layer', targetLayer);
            
            const response = await fetch('/api/terrain/import', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showSuccess('Terrain imported successfully');
                // Create new plot div to ensure clean state
                plotContainer.innerHTML = '<div id="terrain-plot"></div>';
                Plotly.newPlot('terrain-plot', data.plot.data, data.plot.layout);
                displayMetrics(data.metrics);
                await updateModelsList();
            } else {
                showError(data.error || 'Failed to import terrain');
            }
        } catch (error) {
            showError('Error importing terrain: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    // Load existing terrain model
    async function loadTerrain(modelName) {
        showLoading();
        
        try {
            // Get terrain data and plot
            const response = await fetch(`/api/terrain/${modelName}/load`);
            const data = await response.json();
            
            if (response.ok) {
                showSuccess('Terrain loaded successfully');
                // Create new plot div to ensure clean state
                plotContainer.innerHTML = '<div id="terrain-plot"></div>';
                Plotly.newPlot('terrain-plot', data.plot.data, data.plot.layout);
                displayMetrics(data.metrics);
            } else {
                showError(data.error || 'Failed to load terrain');
            }
        } catch (error) {
            showError('Error loading terrain: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    // Event listeners
    importButton.addEventListener('click', () => {
        const file = fileInput.files[0];
        const modelName = modelNameInput.value.trim();
        
        if (!file) {
            showError('Please select a DXF file');
            return;
        }
        
        if (!modelName) {
            showError('Please enter a model name');
            return;
        }
        
        importTerrain(file, modelName);
    });

    loadButton.addEventListener('click', () => {
        const modelName = loadModelSelect.value;
        if (!modelName) {
            showError('Please select a model to load');
            return;
        }
        loadTerrain(modelName);
    });

    // Initialize
    updateModelsList();
});
