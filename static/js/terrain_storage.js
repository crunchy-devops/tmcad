// Terrain storage management
async function loadSavedTerrains() {
    try {
        const response = await fetch('/api/terrains');
        const terrains = await response.json();
        
        const terrainsList = document.getElementById('savedTerrains');
        terrainsList.innerHTML = terrains.map(terrain => `
            <div class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${terrain.name}</h6>
                    <small>${new Date(terrain.created_at).toLocaleString()}</small>
                </div>
                <p class="mb-1">Points: ${terrain.point_count}</p>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="loadSavedTerrain(${terrain.id})">Load</button>
                    <button class="btn btn-outline-danger" onclick="deleteSavedTerrain(${terrain.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showStatus('Error loading saved terrains: ' + error.message);
    }
}

async function loadSavedTerrain(terrainId) {
    try {
        const response = await fetch(`/api/terrains/${terrainId}`);
        const data = await response.json();
        
        // Update global terrain data with high precision points
        terrainData = {
            points: data.points.map(p => ({
                id: p.id,
                x: Number(p.x.toFixed(2)),  // Maintain 0.01 precision as per memory
                y: Number(p.y.toFixed(2)),
                z: Number(p.z.toFixed(2))
            })),
            bounds: data.terrain.bounds,
            totalPoints: data.terrain.point_count
        };
        
        // Update break lines
        breakLines = data.break_lines || [];
        
        // Update visualization
        updateVisualization();
        
        // Update stats
        const statsHtml = `
            <p><strong>Points:</strong> ${data.terrain.point_count}</p>
            <p><strong>Bounds:</strong></p>
            <ul>
                <li>X: ${data.terrain.bounds.x[0].toFixed(2)} to ${data.terrain.bounds.x[1].toFixed(2)}</li>
                <li>Y: ${data.terrain.bounds.y[0].toFixed(2)} to ${data.terrain.bounds.y[1].toFixed(2)}</li>
                <li>Z: ${data.terrain.bounds.z[0].toFixed(2)} to ${data.terrain.bounds.z[1].toFixed(2)}</li>
            </ul>
        `;
        document.getElementById('terrainStats').innerHTML = statsHtml;
        
        showStatus('Terrain loaded successfully');
    } catch (error) {
        showStatus('Error loading terrain: ' + error.message);
    }
}

async function deleteSavedTerrain(terrainId) {
    if (!confirm('Are you sure you want to delete this terrain?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/terrains/${terrainId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadSavedTerrains();
            showStatus('Terrain deleted successfully');
        } else {
            const data = await response.json();
            showStatus('Error: ' + data.message);
        }
    } catch (error) {
        showStatus('Error deleting terrain: ' + error.message);
    }
}

// Load saved terrains when the page loads
document.addEventListener('DOMContentLoaded', () => {
    loadSavedTerrains();
});
