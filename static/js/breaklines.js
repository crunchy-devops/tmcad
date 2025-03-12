// Break line management with efficient point caching
let breakLines = [];
let selectedPoints = [];
let pointCache = new Map(); // Cache for O(1) point lookups

function showBreakLineDialog() {
    console.log('Opening break line dialog');
    const modal = document.getElementById('breakLineModal');
    if (!modal) {
        console.error('Break line modal not found');
        return;
    }
    
    // Clear previous values
    document.getElementById('startPointId').value = '';
    document.getElementById('endPointId').value = '';
    
    // Initialize new modal instance
    const bsModal = new bootstrap.Modal(modal, {
        keyboard: false,
        backdrop: 'static'
    });
    bsModal.show();
}

async function addManualBreakLine() {
    console.log('Adding manual break line');
    const startId = parseInt(document.getElementById('startPointId').value);
    const endId = parseInt(document.getElementById('endPointId').value);

    console.log('Point IDs:', startId, endId);

    if (isNaN(startId) || isNaN(endId)) {
        showStatus('Please enter valid point IDs');
        return;
    }

    try {
        console.log('Sending break line request');
        // Add break line with server-side validation
        const response = await fetch('/api/break-lines', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                point_ids: [startId, endId]
            })
        });

        const result = await response.json();
        console.log('Server response:', result);
        
        if (response.ok) {
            // Add to local break lines array
            breakLines.push([startId, endId]);
            
            // Update visualization
            if (typeof updateVisualization === 'function') {
                console.log('Updating visualization');
                updateVisualization();
            } else {
                console.error('updateVisualization function not found');
            }
            
            // Close modal
            const modal = document.getElementById('breakLineModal');
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            } else {
                console.error('Modal instance not found');
            }
            
            // Clear inputs
            document.getElementById('startPointId').value = '';
            document.getElementById('endPointId').value = '';
            
            showStatus('Break line added successfully');
        } else {
            showStatus('Error: ' + result.message);
        }
    } catch (error) {
        console.error('Error in addManualBreakLine:', error);
        showStatus('Error adding break line: ' + error.message);
    }
}

async function addBreakLine() {
    console.log('Adding break line from selection');
    if (selectedPoints.length < 2) {
        showStatus('Select at least 2 points for a break line');
        return;
    }

    try {
        const response = await fetch('/api/break-lines', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                point_ids: selectedPoints
            })
        });

        const result = await response.json();
        console.log('Server response:', result);
        
        if (response.ok) {
            breakLines.push([...selectedPoints]); // Create a copy of selectedPoints
            selectedPoints = [];
            
            // Update visualization
            if (typeof updateVisualization === 'function') {
                console.log('Updating visualization');
                updateVisualization();
            } else {
                console.error('updateVisualization function not found');
            }
            
            updateSelectedPointsList();
            showStatus('Break line added successfully');
        } else {
            showStatus('Error: ' + result.message);
        }
    } catch (error) {
        console.error('Error in addBreakLine:', error);
        showStatus('Error adding break line: ' + error.message);
    }
}

async function loadBreakLines() {
    console.log('Loading break lines');
    try {
        const response = await fetch('/api/break-lines');
        if (response.ok) {
            const data = await response.json();
            console.log('Loaded break lines:', data);
            
            // Extract point IDs from break line data
            breakLines = data.map(line => line.map(point => point.id));
            
            // Update visualization
            if (typeof updateVisualization === 'function') {
                console.log('Updating visualization');
                updateVisualization();
            } else {
                console.error('updateVisualization function not found');
            }
        }
    } catch (error) {
        console.error('Error in loadBreakLines:', error);
        showStatus('Error loading break lines: ' + error.message);
    }
}

function togglePointSelection(pointId) {
    console.log('Toggling point selection:', pointId);
    const index = selectedPoints.indexOf(pointId);
    if (index === -1) {
        selectedPoints.push(pointId);
    } else {
        selectedPoints.splice(index, 1);
    }
    updateSelectedPointsList();
    
    // Update visualization
    if (typeof updateVisualization === 'function') {
        console.log('Updating visualization');
        updateVisualization();
    } else {
        console.error('updateVisualization function not found');
    }
}

function updateSelectedPointsList() {
    const list = document.getElementById('selectedPoints');
    list.innerHTML = selectedPoints.map(id => `
        <li class="list-group-item d-flex justify-content-between align-items-center">
            Point ID: ${id}
            <button class="btn btn-sm btn-danger" onclick="togglePointSelection(${id})">Remove</button>
        </li>
    `).join('');
}

function showStatus(message) {
    console.log('Status message:', message);
    const status = document.getElementById('status');
    if (status) {
        status.textContent = message;
        status.classList.remove('d-none');
        setTimeout(() => {
            status.textContent = '';
            status.classList.add('d-none');
        }, 5000);
    } else {
        console.error('Status element not found');
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing break line functionality');
    // Ensure modal is properly initialized
    const modal = document.getElementById('breakLineModal');
    if (modal) {
        new bootstrap.Modal(modal);
    } else {
        console.error('Break line modal not found during initialization');
    }
});

// Expose functions globally
window.showBreakLineDialog = showBreakLineDialog;
window.addManualBreakLine = addManualBreakLine;
window.addBreakLine = addBreakLine;
window.togglePointSelection = togglePointSelection;
window.loadBreakLines = loadBreakLines;
