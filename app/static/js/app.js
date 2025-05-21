/**
 * Blackbox Target Manager - Main JavaScript
 * This file handles all interactions between the UI and backend API
 */

// Global state
let targets = [];
let probes = [];
let selectedTargetIds = [];

// DOM Elements
const sidebar = document.querySelector('.sidebar');
const content = document.getElementById('content');
const sidebarToggler = document.getElementById('sidebar-toggler');
const selectAllCheckbox = document.getElementById('selectAll');
const targetsList = document.getElementById('targetsList');
const searchInput = document.querySelector('.search-input');
const targetSearchInput = document.querySelector('input[placeholder="Search Target (label=AAA, name=AAA)"]');
const addTargetBtn = document.getElementById('addTargetBtn');
const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');

// These buttons might have different IDs or class names based on the actual rendered HTML
// We'll check if they exist before adding event listeners
const enableSelectedBtn = document.querySelector('button[id="enableSelected"], button.btn-success');
const disableSelectedBtn = document.querySelector('button[id="disableSelected"], button.btn-secondary');

// Modal elements
let addTargetModal, editTargetModal, deleteConfirmModal;
let saveAddButton, saveEditButton, confirmDeleteButton;

// Initialize modals if they exist
function initModals() {
    const addTargetModalElement = document.getElementById('addTargetModal');
    const editTargetModalElement = document.getElementById('editTargetModal');
    const deleteConfirmModalElement = document.getElementById('deleteConfirmModal');
    
    if (addTargetModalElement) {
        addTargetModal = new bootstrap.Modal(addTargetModalElement);
        saveAddButton = document.getElementById('saveAddButton');
    }
    
    if (editTargetModalElement) {
        editTargetModal = new bootstrap.Modal(editTargetModalElement);
        saveEditButton = document.getElementById('saveEditButton');
    }
    
    if (deleteConfirmModalElement) {
        deleteConfirmModal = new bootstrap.Modal(deleteConfirmModalElement);
        confirmDeleteButton = document.getElementById('confirmDeleteButton');
    }
}

// Polling interval
let pollingInterval = null;
const POLL_INTERVAL = 60000; // 1 minute

// Initialize application
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOM loaded, initializing application...');
    
    // Initialize modals
    initModals();
    
    // Toggle sidebar if elements exist
    if (sidebarToggler && sidebar && content) {
        sidebarToggler.addEventListener('click', toggleSidebar);
    }
    
    // Initialize event listeners
    initEventListeners();
    
    try {
        // Load data
        await Promise.all([
            loadProbes(),
            loadTargets()
        ]);
        
        // Start polling for updates
        startPolling();
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});

// Initialize all event listeners
function initEventListeners() {
    // Select all checkbox
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAll);
    }
    
    // Search inputs
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                searchTargets(this.value);
            }
        });
    }
    
    if (targetSearchInput) {
        targetSearchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                searchTargets(this.value);
            }
        });
    }
    
    // Batch operation buttons
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', () => showDeleteConfirmation(selectedTargetIds));
    }
    
    if (enableSelectedBtn) {
        enableSelectedBtn.addEventListener('click', () => batchUpdateTargets('enable'));
    }
    
    if (disableSelectedBtn) {
        disableSelectedBtn.addEventListener('click', () => batchUpdateTargets('disable'));
    }
    
    // Modal action buttons
    if (addTargetBtn) {
        addTargetBtn.addEventListener('click', showAddTargetModal);
    }
    
    if (saveAddButton) {
        saveAddButton.addEventListener('click', handleAddTarget);
    }
    
    if (saveEditButton) {
        saveEditButton.addEventListener('click', handleEditTarget);
    }
    
    if (confirmDeleteButton) {
        confirmDeleteButton.addEventListener('click', handleDeleteConfirmed);
    }
    
    // Try to find action buttons by class or text content if IDs aren't available
    const actionButtons = document.querySelectorAll('.btn');
    actionButtons.forEach(button => {
        const buttonText = button.textContent.trim().toLowerCase();
        if (buttonText.includes('enable') && !enableSelectedBtn) {
            button.addEventListener('click', () => batchUpdateTargets('enable'));
        } else if (buttonText.includes('disable') && !disableSelectedBtn) {
            button.addEventListener('click', () => batchUpdateTargets('disable'));
        } else if (buttonText.includes('delete selected') && !deleteSelectedBtn) {
            button.addEventListener('click', () => showDeleteConfirmation(selectedTargetIds));
        } else if (buttonText.includes('add') && !addTargetBtn) {
            button.addEventListener('click', showAddTargetModal);
        }
    });
}

// Toggle sidebar visibility
function toggleSidebar() {
    if (sidebar && content) {
        sidebar.classList.toggle('collapsed');
        content.classList.toggle('expanded');
        
        const sidebarTitle = document.getElementById('sidebar-title');
        if (sidebarTitle) {
            if (sidebar.classList.contains('collapsed')) {
                sidebarTitle.style.display = 'none';
            } else {
                sidebarTitle.style.display = 'block';
            }
        }
    } else {
        console.error('Sidebar or content elements not found');
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
    
    // Update button states if they exist
    if (deleteSelectedBtn) {
        deleteSelectedBtn.disabled = !hasSelected;
    }
    
    if (enableSelectedBtn) {
        enableSelectedBtn.disabled = !hasSelected;
    }
    
    if (disableSelectedBtn) {
        disableSelectedBtn.disabled = !hasSelected;
    }
    
    // Try to find buttons by class if IDs aren't available
    document.querySelectorAll('.btn').forEach(button => {
        const buttonText = button.textContent.trim().toLowerCase();
        if (buttonText.includes('delete selected') || 
            buttonText.includes('enable selected') || 
            buttonText.includes('disable selected')) {
            button.disabled = !hasSelected;
        }
    });
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
    console.log('Showing add target modal');
    
    // Check if the modal exists
    if (!addTargetModal) {
        console.error('Add target modal not found. Creating a fallback modal.');
        
        // Create a modal dynamically if it doesn't exist
        const modalHtml = `
        <div class="modal fade" id="addTargetModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add Target</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addTargetForm">
                            <div class="mb-3">
                                <label for="add-hostname" class="form-label">Hostname</label>
                                <input type="text" class="form-control" id="add-hostname" required>
                            </div>
                            <div class="mb-3">
                                <label for="add-region" class="form-label">Region</label>
                                <select class="form-select" id="add-region" required>
                                    <option value="">Select Region</option>
                                    <option value="US-East">US-East</option>
                                    <option value="US-West">US-West</option>
                                    <option value="EU">EU</option>
                                    <option value="Asia">Asia</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="add-zone" class="form-label">Zone</label>
                                <input type="text" class="form-control" id="add-zone" required>
                            </div>
                            <div class="mb-3">
                                <label for="add-module-type" class="form-label">Module Type</label>
                                <select class="form-select" id="add-module-type" required>
                                    <option value="">Select Type</option>
                                    <option value="HTTP">HTTP</option>
                                    <option value="ICMP">ICMP</option>
                                    <option value="TCP">TCP</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="add-assignees" class="form-label">Assignees</label>
                                <input type="text" class="form-control" id="add-assignees" required>
                            </div>
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="add-enabled" checked>
                                <label class="form-check-label" for="add-enabled">Enabled</label>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="saveAddButton">Save</button>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Append the modal to the body
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);
        
        // Initialize the modal
        const modalElement = document.getElementById('addTargetModal');
        addTargetModal = new bootstrap.Modal(modalElement);
        
        // Add event listener to the save button
        saveAddButton = document.getElementById('saveAddButton');
        if (saveAddButton) {
            saveAddButton.addEventListener('click', handleAddTarget);
        }
    }
    
    // Reset form if it exists
    const addForm = document.getElementById('addTargetForm');
    if (addForm) {
        addForm.reset();
    }
    
    // Populate probe dropdown if needed
    try {
        populateProbeDropdown('add-probes');
    } catch (error) {
        console.warn('Could not populate probe dropdown:', error);
    }
    
    // Show the modal
    try {
        addTargetModal.show();
    } catch (error) {
        console.error('Error showing add target modal:', error);
        alert('Could not open the Add Target form. Please check the console for details.');
    }
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
    if (!dropdown) {
        console.warn(`Dropdown element with ID '${elementId}' not found`);
        return;
    }
    
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