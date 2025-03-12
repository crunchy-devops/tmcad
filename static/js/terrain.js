// Cache for terrain data to minimize API calls
let terrainData = {
    points: [],
    bounds: null,
    currentPage: 1,
    pointsPerPage: 100,
    totalPoints: 0
};

// Initialize plot with empty data
let plot = document.getElementById('terrainPlot');
Plotly.newPlot(plot, [{
    type: 'scatter3d',
    mode: 'markers',
    x: [],
    y: [],
    z: [],
    marker: {
        size: 3,
        color: [],
        colorscale: 'Viridis'
    }
}], {
    scene: {
        aspectmode: 'data',
        camera: {
            eye: {x: 1.5, y: 1.5, z: 1.5}
        }
    },
    margin: {l: 0, r: 0, t: 0, b: 0}
});

async function loadTerrain() {
    const filePath = document.getElementById('dxfFile').value;
    
    try {
        // Load terrain data
        const response = await fetch('/api/load-terrain', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({file_path: filePath})
        });
        
        const data = await response.json();
        if (data.status === 'error') {
            showStatus('Error: ' + data.message);
            return;
        }
        
        // Reset terrain data cache
        terrainData.bounds = data.bounds;
        terrainData.totalPoints = data.point_count;
        terrainData.currentPage = 1;
        
        // Load initial points and stats
        await Promise.all([
            loadPoints(),
            updateTerrainStats()
        ]);
        
        showStatus('Terrain loaded successfully');
    } catch (error) {
        showStatus('Error: ' + error.message);
    }
}

async function loadPoints() {
    try {
        const response = await fetch(`/api/points?page=${terrainData.currentPage}&per_page=${terrainData.pointsPerPage}`);
        const points = await response.json();
        
        // Update terrain data cache
        terrainData.points = points;
        
        // Extract coordinates for plotting
        const x = points.map(p => p.x);
        const y = points.map(p => p.y);
        const z = points.map(p => p.z);
        
        // Update plot with efficient data transfer
        const update = {
            x: [x],
            y: [y],
            z: [z],
            'marker.color': [z]
        };
        
        Plotly.update(plot, update);
    } catch (error) {
        showStatus('Error loading points: ' + error.message);
    }
}

async function updateTerrainStats() {
    try {
        const response = await fetch('/api/terrain-stats');
        const data = await response.json();
        
        if (data.status === 'error') {
            document.getElementById('terrainStats').innerHTML = 'Error loading stats';
            return;
        }
        
        const stats = data.stats;
        let statsHtml = `
            <p><strong>Points:</strong> ${terrainData.totalPoints}</p>
            <p><strong>Density:</strong> ${stats.point_density.toFixed(2)} points/m²</p>
            <p><strong>Bounds:</strong></p>
            <ul>
                <li>X: ${stats.bounds.x[0].toFixed(2)} to ${stats.bounds.x[1].toFixed(2)}</li>
                <li>Y: ${stats.bounds.y[0].toFixed(2)} to ${stats.bounds.y[1].toFixed(2)}</li>
                <li>Z: ${stats.bounds.z[0].toFixed(2)} to ${stats.bounds.z[1].toFixed(2)}</li>
            </ul>
        `;
        
        document.getElementById('terrainStats').innerHTML = statsHtml;
    } catch (error) {
        showStatus('Error updating stats: ' + error.message);
    }
}

async function loadPoint() {
    const pointId = document.getElementById('pointId').value;
    if (!pointId) return;
    
    try {
        const response = await fetch(`/api/point/${pointId}`);
        const point = await response.json();
        
        if (response.ok) {
            document.getElementById('pointEditor').classList.remove('d-none');
            document.getElementById('pointX').value = point.x;
            document.getElementById('pointY').value = point.y;
            document.getElementById('pointZ').value = point.z;
        } else {
            showStatus('Error: ' + point.message);
        }
    } catch (error) {
        showStatus('Error loading point: ' + error.message);
    }
}

async function updatePoint() {
    const pointId = document.getElementById('pointId').value;
    if (!pointId) return;
    
    const pointData = {
        x: parseFloat(document.getElementById('pointX').value),
        y: parseFloat(document.getElementById('pointY').value),
        z: parseFloat(document.getElementById('pointZ').value)
    };
    
    try {
        const response = await fetch(`/api/point/${pointId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(pointData)
        });
        
        const result = await response.json();
        if (response.ok) {
            showStatus('Point updated successfully');
            // Reload points and stats
            await Promise.all([
                loadPoints(),
                updateTerrainStats()
            ]);
        } else {
            showStatus('Error: ' + result.message);
        }
    } catch (error) {
        showStatus('Error updating point: ' + error.message);
    }
}

function showStatus(message) {
    const statusModal = new bootstrap.Modal(document.getElementById('statusModal'));
    document.getElementById('statusMessage').textContent = message;
    statusModal.show();
}

// Add event listeners for plot interactions
plot.on('plotly_click', function(data) {
    if (data.points.length > 0) {
        const point = data.points[0];
        const pointIndex = point.pointNumber;
        const pointData = terrainData.points[pointIndex];
        
        document.getElementById('pointId').value = pointData.id;
        loadPoint();
    }
});
