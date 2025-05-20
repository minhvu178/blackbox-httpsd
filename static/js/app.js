/**
 * Blackbox Target Manager - Main JavaScript
 * This file handles all interactions between the UI and backend API
 */

// Global state
let targets = [];
let probes = [];
let selectedTargetIds = [];

// DOM Elements
const sidebar = document.getElementById('sidebar');
const content = document.getElementById('content');
const sidebarToggler = document.getElementById('sidebar-toggler');
const selectAllCheckbox = document.getElementById('selectAll');
const targetsList = document.getElementById('targetsList');
const searchInput = document.querySelector('.search-input');
const targetSearchInput = document.querySelector('input[placeholder="Search Target (label=AAA, name=AAA)"]');
const addTargetBtn = document.getElementById('addTargetBtn');
const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
const enableSelectedBtn = document.getElementById('enableSelected');
const disableSelectedBtn = document.getElementById('disableSelected');

// Modal elements
const addTargetModal = new bootstrap.Modal(document.getElementById('addTargetModal'));
const editTargetModal = new bootstrap.Modal(document.getElementById('editTargetModal'));
const deleteConfirmModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
const saveAddButton = document.getElementById('saveAddButton');
const saveEditButton = document.getElementById('saveEditButton');
const confirmDeleteButton = document.getElementById('confirmDeleteButton');

// Polling interval
let pollingInterval = null;
const POLL_INTERVAL = 60000; // 1 minute

// Initialize application
document.addEventListener('DOMContentLoaded', async function() {
    // Toggle sidebar
    sidebarToggler.addEventListener('click', toggleSidebar);
    
    // Initialize event listeners
    initEventListeners();
    
    // Load data
    await Promise.all([
        loadProbes(),
        loadTargets()
    ]);
    
    // Start polling for updates
    startPolling();
});

// Initialize all event listeners
function initEventListeners() {
    // Select all checkbox
    selectAllCheckbox.addEventListener('change', handleSelectAll);
    
    // Search inputs
    searchInput.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            searchTargets(this.value);
        }
    });
    
    targetSearchInput.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            searchTargets(this.value);
        }
    });
    
    // Batch operation buttons
    deleteSelectedBtn.addEventListener('click', () => showDeleteConfirmation(selectedTargetIds));
    enableSelectedBtn.addEventListener('click', () => batchUpdateTargets('enable'));
    disableSelectedBtn.addEventListener('click', () => batchUpdateTargets('disable'));
    
    // Modal action buttons
    addTargetBtn.addEventListener('click', showAddTargetModal);
    saveAddButton.addEventListener('click', handleAddTarget);
    saveEditButton.addEventListener('click', handleEditTarget);
    confirmDeleteButton.addEventListener('click', handleDeleteConfirmed);
}

// Toggle sidebar visibility
function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    content.classList.toggle('expanded');
    
    if (sidebar.classList.contains('collapsed')) {
        document.getElementById('sidebar-title').style.display = 'none';
    } else {
        document.getElementById('sidebar-title').style.display = 'block';
    }
}

// Handle select all checkbox
function handleSelectAll() {
    const checkboxes = document.querySelectorAll('.target-checkbox');
    for (const checkbox of checkboxes) {
        checkbox.checked = this.checked;
    }
    updateSelectedTargets();
}

// Update selected targets array and button states
function updateSelectedTargets() {
    selectedTargetIds = [];
    document.querySelectorAll('.target-checkbox:checked').forEach(checkbox => {
        selectedTargetIds.push(parseInt(checkbox.dataset.id));
    });
    
    const hasSelected = selectedTargetIds.length > 0;
    deleteSelectedBtn.disabled = !hasSelected;
    enableSelectedBtn.disabled = !hasSelected;
    disableSelectedBtn.disabled = !hasSelected;
}

// Render targets list
function renderTargetsList() {
    targetsList.innerHTML = '';
    
    if (targets.length === 0) {
        targetsList.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-3">No targets found</td>
            </tr>
        `;
        return;
    }
    
    targets.forEach(target => {
        const tr = document.createElement('tr');
        
        // Status badge
        let statusBadge = '';
        if (target.last_status === 'UP') {
            statusBadge = '<span class="badge bg-success">UP</span>';
        } else if (target.last_status === 'DOWN') {
            statusBadge = '<span class="badge bg-danger">DOWN</span>';
        } else {
            statusBadge = '<span class="badge bg-secondary">N/A</span>';
        }
        
        tr.innerHTML = `
            <td>
                <div class="form-check">
                    <input class="form-check-input target-checkbox" type="checkbox" data-id="${target.id}">
                </div>
            </td>
            <td>${target.hostname}</td>
            <td>${target.region}</td>
            <td>${target.zone}</td>
            <td>${target.probe_type}</td>
            <td>${target.assignees}</td>
            <td>
                <span class="status-indicator ${target.enabled ? 'status-enabled' : 'status-disabled'}"></span>
                ${target.enabled ? 'Enabled' : 'Disabled'}
            </td>
            <td>${statusBadge}</td>
            <td>${target.last_status_code || 'N/A'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary edit-btn" data-id="${target.id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${target.id}">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        targetsList.appendChild(tr);
    });
    
    // Attach event listeners to action buttons
    attachTargetActionListeners();
}

// Attach event listeners to target action buttons
function attachTargetActionListeners() {
    // Edit buttons
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = parseInt(this.dataset.id);
            showEditTargetModal(targetId);
        });
    });
    
    // Delete buttons
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = parseInt(this.dataset.id);
            showDeleteConfirmation([targetId]);
        });
    });
    
    // Target checkboxes
    document.querySelectorAll('.target-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedTargets);
    });
}

// Show add target modal
function showAddTargetModal() {
    // Reset form
    document.getElementById('addTargetForm').reset();
    
    // Populate probe dropdown if needed
    populateProbeDropdown('add-probes');
    
    addTargetModal.show();
}

// Show edit target modal
function showEditTargetModal(targetId) {
    const target = targets.find(t => t.id === targetId);
    if (!target) {
        alert('Target not found');
        return;
    }
    
    // Populate form fields
    document.getElementById('edit-id').value = target.id;
    document.getElementById('edit-hostname').value = target.hostname;
    document.getElementById('edit-region').value = target.region;
    document.getElementById('edit-zone').value = target.zone;
    document.getElementById('edit-module-type').value = target.probe_type;
    document.getElementById('edit-assignees').value = target.assignees;
    document.getElementById('edit-enabled').checked = target.enabled;
    
    // Populate probe dropdown
    populateProbeDropdown('edit-probes');
    
    editTargetModal.show();
}

// Show delete confirmation modal
function showDeleteConfirmation(targetIds) {
    if (!targetIds || targetIds.length === 0) {
        alert('No targets selected');
        return;
    }
    
    // Get hostnames of targets to be deleted
    const targetNames = targetIds.map(id => {
        const target = targets.find(t => t.id === id);
        return target ? target.hostname : `ID: ${id}`;
    });
    
    // Update modal content
    const deleteList = document.getElementById('delete-targets-list');
    deleteList.innerHTML = '';
    targetNames.forEach(name => {
        const li = document.createElement('li');
        li.textContent = name;
        deleteList.appendChild(li);
    });
    
    // Store targetIds for deletion
    confirmDeleteButton.dataset.targetIds = JSON.stringify(targetIds);
    
    deleteConfirmModal.show();
}

// Populate probe dropdown
function populateProbeDropdown(elementId) {
    const dropdown = document.getElementById(elementId);
    dropdown.innerHTML = '';
    
    // Add default option that contains all probes
    const allProbesText = probes.map(p => `${p.location} / ${p.provider}`).join(', ');
    const defaultOption = document.createElement('option');
    defaultOption.value = 'all';
    defaultOption.textContent = allProbesText || 'Singapore, USA, KOREA / Viettel, FCI, CMC';
    dropdown.appendChild(defaultOption);
    
    // Add individual probes if available
    if (probes.length > 0) {
        probes.forEach(probe => {
            const option = document.createElement('option');
            option.value = probe.id;
            option.textContent = `${probe.location} / ${probe.provider}`;
            dropdown.appendChild(option);
        });
    }
}

// Start polling for updates
function startPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    pollingInterval = setInterval(async () => {
        await loadTargets();
    }, POLL_INTERVAL);
}

// API Functions

// Base URL - adjust this if the API is hosted at a different location
const API_BASE_URL = window.location.origin;

// Load all probes
async function loadProbes() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/probes`);
        if (response.ok) {
            probes = await response.json();
        } else {
            console.error('Failed to load probes');
        }
    } catch (error) {
        console.error('Error loading probes:', error);
    }
}

// Load all targets
async function loadTargets() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/targets`);
        if (response.ok) {
            targets = await response.json();
            renderTargetsList();
        } else {
            console.error('Failed to load targets');
        }
    } catch (error) {
        console.error('Error loading targets:', error);
    }
}

// Search targets
async function searchTargets(query) {
    if (!query) {
        await loadTargets();
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/targets?q=${encodeURIComponent(query)}`);
        if (response.ok) {
            targets = await response.json();
            renderTargetsList();
        } else {
            console.error('Failed to search targets');
        }
    } catch (error) {
        console.error('Error searching targets:', error);
    }
}

// Add a new target
async function handleAddTarget() {
    // Collect form data
    const formData = {
        hostname: document.getElementById('add-hostname').value,
        address: document.getElementById('add-hostname').value, // Using hostname as address for simplicity
        region: document.getElementById('add-region').value,
        zone: document.getElementById('add-zone').value,
        probe_type: document.getElementById('add-module-type').value,
        assignees: document.getElementById('add-assignees').value,
        enabled: document.getElementById('add-enabled').checked
    };
    
    // Validation
    if (!formData.hostname || !formData.region || !formData.zone || !formData.probe_type) {
        alert('Please fill all required fields');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/targets`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            addTargetModal.hide();
            await loadTargets();
            alert('Target added successfully!');
        } else {
            const error = await response.json();
            alert(`Failed to add target: ${error.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error adding target:', error);
        alert('Failed to add target. Please try again.');
    }
}

// Edit an existing target
async function handleEditTarget() {
    const targetId = parseInt(document.getElementById('edit-id').value);
    
    // Collect form data
    const formData = {
        hostname: document.getElementById('edit-hostname').value,
        address: document.getElementById('edit-hostname').value, // Using hostname as address for simplicity
        region: document.getElementById('edit-region').value,
        zone: document.getElementById('edit-zone').value,
        probe_type: document.getElementById('edit-module-type').value,
        assignees: document.getElementById('edit-assignees').value,
        enabled: document.getElementById('edit-enabled').checked
    };
    
    // Validation
    if (!formData.hostname || !formData.region || !formData.zone || !formData.probe_type) {
        alert('Please fill all required fields');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/targets/${targetId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            editTargetModal.hide();
            await loadTargets();
            alert('Target updated successfully!');
        } else {
            const error = await response.json();
            alert(`Failed to update target: ${error.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error updating target:', error);
        alert('Failed to update target. Please try again.');
    }
}

// Delete targets
async function handleDeleteConfirmed() {
    const targetIdsStr = confirmDeleteButton.dataset.targetIds;
    if (!targetIdsStr) {
        alert('No targets selected for deletion');
        return;
    }
    
    const targetIds = JSON.parse(targetIdsStr);
    
    try {
        if (targetIds.length === 1) {
            // Single delete
            const response = await fetch(`${API_BASE_URL}/api/targets/${targetIds[0]}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete target');
            }
        } else {
            // Batch delete
            const response = await fetch(`${API_BASE_URL}/api/targets/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    operation: 'delete',
                    target_ids: targetIds
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete targets');
            }
        }
        
        deleteConfirmModal.hide();
        await loadTargets();
        
        // Reset selection
        selectedTargetIds = [];
        selectAllCheckbox.checked = false;
        updateSelectedTargets();
        
        alert('Target(s) deleted successfully!');
    } catch (error) {
        console.error('Error deleting targets:', error);
        alert(`Failed to delete targets: ${error.message}`);
    }
}

// Batch update targets (enable/disable)
async function batchUpdateTargets(operation) {
    if (selectedTargetIds.length === 0) {
        alert('No targets selected');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/targets/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                operation: operation,
                target_ids: selectedTargetIds
            })
        });
        
        if (response.ok) {
            await loadTargets();
            
            // Reset selection
            selectedTargetIds = [];
            selectAllCheckbox.checked = false;
            updateSelectedTargets();
            
            alert(`Target(s) ${operation}d successfully!`);
        } else {
            const error = await response.json();
            alert(`Failed to ${operation} targets: ${error.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error(`Error ${operation}ing targets:`, error);
        alert(`Failed to ${operation} targets. Please try again.`);
    }
}