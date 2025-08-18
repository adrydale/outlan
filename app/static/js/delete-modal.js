// Delete confirmation modal functionality
function showDeleteModal(type, id, name, details) {
    const modal = document.getElementById('deleteModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalDetails = document.getElementById('modalDetails');
    const modalDetailsBody = document.getElementById('modalDetailsBody');
    const confirmBtn = document.getElementById('modalConfirmBtn');
    
    if (type === 'block') {
        modalTitle.textContent = 'Delete Block';
        modalMessage.innerHTML = '<p>Are you sure you want to delete the block <strong id="blockNameToDelete"></strong>?</p><p>This will also delete all subnets and containers within this block.</p>';
        document.getElementById('blockNameToDelete').textContent = name;
        modalDetails.style.display = 'none';
        confirmBtn.onclick = function() { deleteBlock(id); };
    } else if (type === 'container') {
        modalTitle.textContent = 'Delete Container';
        modalMessage.innerHTML = '<p>Are you sure you want to delete the container <strong id="containerNameToDelete"></strong>?</p><p>This will not affect existing subnets, but the container\'s segment planning will be lost.</p>';
        document.getElementById('containerNameToDelete').textContent = name;
        modalDetails.style.display = 'none';
        confirmBtn.onclick = function() { deleteContainer(id); };
    } else if (type === 'subnet') {
        modalTitle.textContent = 'Delete Subnet';
        modalMessage.innerHTML = '<p>Are you sure you want to delete this subnet?</p><p>This subnet is part of block <strong id="subnetBlockName"></strong>.</p>';
        document.getElementById('subnetBlockName').textContent = details.block;
        modalDetails.style.display = 'block';
        modalDetailsBody.innerHTML = `
            <tr>
                <td id="subnetCidr"></td>
                <td id="subnetVlan"></td>
                <td id="subnetName"></td>
            </tr>
        `;
        document.getElementById('subnetCidr').textContent = details.cidr;
        document.getElementById('subnetVlan').textContent = details.vlan;
        document.getElementById('subnetName').textContent = details.name;
        confirmBtn.onclick = function() { deleteSubnet(id); };
    }
    
    modal.style.display = 'flex';
    
    // Focus the confirm button for keyboard navigation
    confirmBtn.focus();
}

function hideDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
}

function deleteBlock(blockId) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/delete_block/' + blockId;
    
    
    document.body.appendChild(form);
    form.submit();
}

function deleteContainer(containerId) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/delete_container/' + containerId;
    
    
    document.body.appendChild(form);
    form.submit();
}

function deleteSubnet(subnetId) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/delete_subnet/' + subnetId;
    
    
    document.body.appendChild(form);
    form.submit();
}

// Initialize delete modal functionality
function initDeleteModal() {
    const modal = document.getElementById('deleteModal');
    
    if (!modal) return; // Modal not present on this page
    
    // Close modal when clicking outside or on cancel
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            hideDeleteModal();
        }
    });
    
    const cancelBtn = document.getElementById('modalCancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', hideDeleteModal);
    }
    
    // Add keyboard support
    document.addEventListener('keydown', function(e) {
        if (modal.style.display === 'flex') {
            if (e.key === 'Enter') {
                e.preventDefault();
                const confirmBtn = document.getElementById('modalConfirmBtn');
                if (confirmBtn) confirmBtn.click();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideDeleteModal();
            }
        }
    });
    
    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const deleteType = this.getAttribute('data-delete-type');
            const deleteName = this.getAttribute('data-delete-name');
            
            if (deleteType === 'block') {
                const blockId = this.getAttribute('data-block-id');
                showDeleteModal('block', blockId, deleteName);
            } else if (deleteType === 'container') {
                const containerId = this.getAttribute('data-container-id');
                showDeleteModal('container', containerId, deleteName);
            } else if (deleteType === 'subnet') {
                const subnetId = this.getAttribute('data-delete-id');
                const cidr = this.getAttribute('data-delete-cidr');
                const vlan = this.getAttribute('data-delete-vlan');
                const block = this.getAttribute('data-delete-block');
                const details = {
                    cidr: cidr,
                    vlan: vlan,
                    name: deleteName,
                    block: block
                };
                showDeleteModal('subnet', subnetId, deleteName, details);
            }
        });
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initDeleteModal);