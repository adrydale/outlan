
// Block collapse functionality
function initializeBlockCollapse() {
    // Set initial collapse states
    document.querySelectorAll('.block-section').forEach(function(blockSection) {
        const blockId = blockSection.dataset.blockId;
        const collapsed = blockSection.dataset.collapsed === '1';
        const content = blockSection.querySelector('.block-content');
        const collapseIcon = blockSection.querySelector('.collapse-icon');
        
        if (collapsed) {
            content.style.display = 'none';
            collapseIcon.innerHTML = '<path d="M19 13H13v6h-2v-6H5v-2h6V5h2v6h6v2z"/>';
        }
    });
    
    // Add collapse button event listeners
    document.querySelectorAll('.collapse-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const blockId = this.dataset.blockId;
            const blockSection = document.querySelector(`[data-block-id="${blockId}"]`);
            const content = blockSection.querySelector('.block-content');
            const collapseIcon = this.querySelector('.collapse-icon');
            const isCollapsed = content.style.display === 'none';
            
            // Toggle display
            content.style.display = isCollapsed ? 'block' : 'none';
            collapseIcon.innerHTML = isCollapsed ? '<path d="M19 13H5v-2h14v2z"/>' : '<path d="M19 13H13v6h-2v-6H5v-2h6V5h2v6h6v2z"/>';
            
            // Update database
            fetch(`/api/toggle_collapse/${blockId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).catch(error => {
                console.error('Error toggling collapse:', error);
            });
        });
    });
}

// Inline editing functionality
function initializeInlineEditing() {
    // Add rename button event listeners
    document.querySelectorAll('.rename-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const blockId = this.dataset.blockId;
            const blockSection = document.querySelector(`[data-block-id="${blockId}"]`);
            const title = blockSection.querySelector('.block-title');
            const editInput = blockSection.querySelector('.block-name-edit');
            const saveBtn = blockSection.querySelector('.save-btn');
            const cancelBtn = blockSection.querySelector('.cancel-btn');
            const renameBtn = this;
            
            // Show edit mode
            title.style.display = 'none';
            editInput.style.display = 'inline-block';
            saveBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';
            renameBtn.style.display = 'none';
            
            // Focus on input
            editInput.focus();
            editInput.select();
        });
    });
    
    // Add save button event listeners
    document.querySelectorAll('.save-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const blockId = this.dataset.blockId;
            const blockSection = document.querySelector(`[data-block-id="${blockId}"]`);
            const title = blockSection.querySelector('.block-title');
            const editInput = blockSection.querySelector('.block-name-edit');
            const saveBtn = this;
            const cancelBtn = blockSection.querySelector('.cancel-btn');
            const renameBtn = blockSection.querySelector('.rename-btn');
            
            const newName = editInput.value.trim();
            if (newName.length === 0) {
                alert('Block name cannot be empty');
                return;
            }
            
            // Update via AJAX
            fetch(`/rename_block/${blockId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `new_block_name=${encodeURIComponent(newName)}`
            }).then(response => {
                if (response.ok) {
                    // Update title and exit edit mode
                    title.textContent = newName;
                    exitEditMode(blockSection);
                } else {
                    alert('Error saving block name');
                }
            }).catch(error => {
                console.error('Error saving:', error);
                alert('Error saving block name');
            });
        });
    });
    
    // Add cancel button event listeners
    document.querySelectorAll('.cancel-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const blockId = this.dataset.blockId;
            const blockSection = document.querySelector(`[data-block-id="${blockId}"]`);
            const editInput = blockSection.querySelector('.block-name-edit');
            
            // Restore original value
            const title = blockSection.querySelector('.block-title');
            editInput.value = title.textContent;
            
            exitEditMode(blockSection);
        });
    });
    
    // Add enter key support for edit input
    document.querySelectorAll('.block-name-edit').forEach(function(input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const blockId = this.dataset.blockId;
                const blockSection = document.querySelector(`[data-block-id="${blockId}"]`);
                const saveBtn = blockSection.querySelector('.save-btn');
                saveBtn.click();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                const blockId = this.dataset.blockId;
                const blockSection = document.querySelector(`[data-block-id="${blockId}"]`);
                const cancelBtn = blockSection.querySelector('.cancel-btn');
                cancelBtn.click();
            }
        });
    });
}

function exitEditMode(blockSection) {
    const title = blockSection.querySelector('.block-title');
    const editInput = blockSection.querySelector('.block-name-edit');
    const saveBtn = blockSection.querySelector('.save-btn');
    const cancelBtn = blockSection.querySelector('.cancel-btn');
    const renameBtn = blockSection.querySelector('.rename-btn');
    
    // Hide edit mode
    title.style.display = 'inline-block';
    editInput.style.display = 'none';
    saveBtn.style.display = 'none';
    cancelBtn.style.display = 'none';
    renameBtn.style.display = 'inline-block';
}

// Block reordering functionality with up/down arrows
function initializeBlockReordering() {
    // Add up/down button event listeners
    addReorderEventListeners();
    
    // Initialize button states
    updateButtonStates();
}

function addReorderEventListeners() {
    document.querySelectorAll('.move-up-btn').forEach(function(btn) {
        btn.addEventListener('click', handleMoveUp);
    });
    
    document.querySelectorAll('.move-down-btn').forEach(function(btn) {
        btn.addEventListener('click', handleMoveDown);
    });
}

function removeReorderEventListeners() {
    document.querySelectorAll('.move-up-btn').forEach(function(btn) {
        btn.removeEventListener('click', handleMoveUp);
    });
    
    document.querySelectorAll('.move-down-btn').forEach(function(btn) {
        btn.removeEventListener('click', handleMoveDown);
    });
}

function handleMoveUp(e) {
    const blockSection = e.target.closest('.block-section');
    const blockSections = Array.from(document.querySelectorAll('.block-section[data-block-id]'));
    const currentIndex = blockSections.indexOf(blockSection);
    
    if (currentIndex > 0) {
        const prevBlock = blockSections[currentIndex - 1];
        blockSection.parentNode.insertBefore(blockSection, prevBlock);
        updatePositions();
        updateButtonStates();
        saveNewOrder();
    }
}

function handleMoveDown(e) {
    const blockSection = e.target.closest('.block-section');
    const blockSections = Array.from(document.querySelectorAll('.block-section[data-block-id]'));
    const currentIndex = blockSections.indexOf(blockSection);
    
    if (currentIndex < blockSections.length - 1) {
        const nextBlock = blockSections[currentIndex + 1];
        blockSection.parentNode.insertBefore(blockSection, nextBlock.nextSibling);
        updatePositions();
        updateButtonStates();
        saveNewOrder();
    }
}

function updateButtonStates() {
    const blockSections = Array.from(document.querySelectorAll('.block-section[data-block-id]'));
    
    blockSections.forEach((blockSection, index) => {
        const upBtn = blockSection.querySelector('.move-up-btn');
        const downBtn = blockSection.querySelector('.move-down-btn');
        
        if (upBtn) {
            upBtn.disabled = index === 0;
            upBtn.style.opacity = index === 0 ? '0.5' : '1';
        }
        
        if (downBtn) {
            downBtn.disabled = index === blockSections.length - 1;
            downBtn.style.opacity = index === blockSections.length - 1 ? '0.5' : '1';
        }
    });
}

function updatePositions() {
    const blocks = document.querySelectorAll('.block-section');
    blocks.forEach((block, index) => {
        block.dataset.position = index + 1;
    });
}

function saveNewOrder() {
    const blocks = document.querySelectorAll('.block-section[data-block-id]');
    const blockData = Array.from(blocks).map((block, index) => ({
        id: parseInt(block.dataset.blockId),
        position: index + 1
    }));
    
    fetch('/api/update_block_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ blocks: blockData })
    }).then(response => {
        if (response.ok) {
            return response.json();
        } else {
            return response.text().then(text => {
                throw new Error(`HTTP ${response.status}: ${text}`);
            });
        }
    }).then(data => {
        // Success - no need to reload, just update button states
        updateButtonStates();
    }).catch(error => {
        console.error('Error saving order:', error);
        showError('Failed to save block order: ' + error.message);
    });
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    } else {
        alert(message);
    }
}

// Initialize management functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeBlockCollapse();
    initializeInlineEditing();
    initializeBlockReordering();
});