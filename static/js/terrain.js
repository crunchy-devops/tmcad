// Global terrain data and visualization state
let terrainData = {
    points: [],
    bounds: null,
    currentPage: 1,
    pointsPerPage: 100,
    totalPoints: 0
};

let is2DMode = false;
let plot = document.getElementById('terrainPlot');

// Initialize plot with empty data
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

// Point cache for O(1) lookups
let pointCache = new Map();

function updateVisualization() {
    if (!terrainData.points || !terrainData.points.length) return;

    // Update point cache for O(1) lookups
    pointCache.clear();
    terrainData.points.forEach(p => pointCache.set(p.id, p));

    const traces = [];
    
    // Main point trace
    const mainTrace = {
        type: is2DMode ? 'scatter' : 'scatter3d',
        mode: is2DMode ? 'markers+text' : 'markers',
        x: terrainData.points.map(p => p.x),
        y: terrainData.points.map(p => p.y),
        text: terrainData.points.map(p => `ID: ${p.id}<br>Z: ${p.z.toFixed(2)}`),
        marker: {
            size: is2DMode ? 8 : 3,
            color: terrainData.points.map(p => p.z),
            colorscale: 'Viridis',
            colorbar: {
                title: 'Elevation (Z)'
            }
        },
        hoverinfo: 'text',
        name: 'Points'
    };

    if (is2DMode) {
        mainTrace.textposition = 'top';
    } else {
        mainTrace.z = terrainData.points.map(p => p.z);
    }

    traces.push(mainTrace);

    // Break lines
    if (typeof breakLines !== 'undefined' && breakLines.length > 0) {
        breakLines.forEach((line, index) => {
            // Use O(1) point lookups from cache
            const points = line.map(id => pointCache.get(id)).filter(p => p);
            if (points.length >= 2) {
                const breakLineTrace = {
                    type: is2DMode ? 'scatter' : 'scatter3d',
                    mode: 'lines',
                    x: points.map(p => p.x),
                    y: points.map(p => p.y),
                    line: {
                        color: 'red',
                        width: 2
                    },
                    name: `Break Line ${index + 1}`
                };
                
                if (!is2DMode) {
                    breakLineTrace.z = points.map(p => p.z);
                }
                
                traces.push(breakLineTrace);
            }
        });
    }

    // Selected points highlight
    if (typeof selectedPoints !== 'undefined' && selectedPoints.length > 0) {
        // Use O(1) point lookups from cache
        const selectedPointsData = selectedPoints
            .map(id => pointCache.get(id))
            .filter(p => p);
        
        const selectedTrace = {
            type: is2DMode ? 'scatter' : 'scatter3d',
            mode: 'markers',
            x: selectedPointsData.map(p => p.x),
            y: selectedPointsData.map(p => p.y),
            marker: {
                size: is2DMode ? 12 : 6,
                color: 'red',
                symbol: 'circle-open'
            },
            name: 'Selected Points'
        };

        if (!is2DMode) {
            selectedTrace.z = selectedPointsData.map(p => p.z);
        }

        traces.push(selectedTrace);
    }

    const layout = is2DMode ? {
        title: '2D Terrain View with Point IDs',
        showlegend: true,
        hovermode: 'closest',
        xaxis: {
            title: 'X Coordinate',
            zeroline: false
        },
        yaxis: {
            title: 'Y Coordinate',
            zeroline: false,
            scaleanchor: 'x',
            scaleratio: 1
        }
    } : {
        scene: {
            aspectmode: 'data',
            camera: {
                eye: {x: 1.5, y: 1.5, z: 1.5}
            },
            xaxis: {title: 'X Coordinate'},
            yaxis: {title: 'Y Coordinate'},
            zaxis: {title: 'Elevation (Z)'}
        },
        margin: {l: 0, r: 0, t: 0, b: 0},
        showlegend: true
    };

    Plotly.newPlot(plot, traces, layout);

    // Add click handler for point selection in 2D mode
    if (is2DMode) {
        plot.on('plotly_click', (data) => {
            const point = data.points[0];
            const pointId = terrainData.points[point.pointIndex].id;
            if (typeof togglePointSelection === 'function') {
                togglePointSelection(pointId);
            }
        });
    }
}

function toggleViewMode() {
    is2DMode = !is2DMode;
    document.getElementById('view2D').classList.toggle('active');
    updateVisualization();
}

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
        await loadPoints();
        updateTerrainStats();
        
        // Load break lines if they exist
        if (typeof loadBreakLines === 'function') {
            await loadBreakLines();
        }
        
        showStatus('Terrain loaded successfully');
    } catch (error) {
        showStatus('Error: ' + error.message);
    }
}

async function loadPoints() {
    try {
        const response = await fetch(`/api/points?page=${terrainData.currentPage}&per_page=${terrainData.pointsPerPage}`);
        const points = await response.json();
        
        // Update terrain data cache with high precision points
        terrainData.points = points.map(p => ({
            id: p.id,
            x: Number(p.x.toFixed(2)),  // Maintain 0.01 precision as per memory
            y: Number(p.y.toFixed(2)),
            z: Number(p.z.toFixed(2))
        }));
        
        updateVisualization();
    } catch (error) {
        showStatus('Error loading points: ' + error.message);
    }
}

function updateTerrainStats() {
    if (terrainData.bounds) {
        document.getElementById('terrainStats').innerHTML = `
            <p><strong>Total Points:</strong> ${terrainData.totalPoints}</p>
            <p><strong>X Range:</strong> ${terrainData.bounds.x[0].toFixed(2)} to ${terrainData.bounds.x[1].toFixed(2)}</p>
            <p><strong>Y Range:</strong> ${terrainData.bounds.y[0].toFixed(2)} to ${terrainData.bounds.y[1].toFixed(2)}</p>
            <p><strong>Z Range:</strong> ${terrainData.bounds.z[0].toFixed(2)} to ${terrainData.bounds.z[1].toFixed(2)}</p>
        `;
    }
}

async function loadPoint(pointId) {
    try {
        const response = await fetch(`/api/point/${pointId}`);
        if (!response.ok) {
            throw new Error('Point not found');
        }
        const point = await response.json();
        return {
            id: point.id,
            x: Number(point.x.toFixed(2)),  // Maintain 0.01 precision
            y: Number(point.y.toFixed(2)),
            z: Number(point.z.toFixed(2))
        };
    } catch (error) {
        showStatus('Error loading point: ' + error.message);
        return null;
    }
}

async function updatePoint(pointId, newZ) {
    try {
        const point = await loadPoint(pointId);
        if (!point) return;

        const response = await fetch(`/api/point/${pointId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                x: point.x,
                y: point.y,
                z: Number(newZ.toFixed(2))  // Maintain 0.01 precision
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update point');
        }

        await loadPoints();
        showStatus('Point updated successfully');
    } catch (error) {
        showStatus('Error updating point: ' + error.message);
    }
}

function showStatus(message) {
    const status = document.getElementById('status');
    status.textContent = message;
    setTimeout(() => status.textContent = '', 5000);
}

// Initialize plot variable and add click handler
document.addEventListener('DOMContentLoaded', () => {
    plot = document.getElementById('terrainPlot');
});

// Make functions globally available
window.updateVisualization = updateVisualization;
window.toggleViewMode = toggleViewMode;
window.loadTerrain = loadTerrain;
window.loadPoints = loadPoints;
window.updatePoint = updatePoint;
