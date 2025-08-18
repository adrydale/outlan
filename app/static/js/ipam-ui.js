// Cancel edit function
function cancelEdit() {
    const baseUrl = document.documentElement.getAttribute('data-base-url') || '/';
    window.location.href = baseUrl;
}

// Container expand/collapse functionality with session persistence
function toggleContainer(containerId) {
    const expandIcon = document.querySelector(`[data-container-id="${containerId}"] .expand-icon`);
    const subnets = document.querySelectorAll(`tr.container-subnet[data-container-id="${containerId}"]`);
    
    if (expandIcon && subnets.length > 0) {
        const isExpanded = expandIcon.classList.contains('expanded');
        
        if (isExpanded) {
            // Collapse
            expandIcon.classList.remove('expanded');
            expandIcon.textContent = '+';
            subnets.forEach(subnet => {
                subnet.style.display = 'none';
            });
            // Save collapsed state
            saveContainerState(containerId, false);
        } else {
            // Expand
            expandIcon.classList.add('expanded');
            expandIcon.textContent = '−';
            subnets.forEach(subnet => {
                subnet.style.display = 'table-row';
            });
            // Save expanded state
            saveContainerState(containerId, true);
        }
    }
}

// Save container state to localStorage
function saveContainerState(containerId, isExpanded) {
    try {
        let containerStates = JSON.parse(localStorage.getItem('outlan_container_states') || '{}');
        containerStates[containerId] = isExpanded;
        localStorage.setItem('outlan_container_states', JSON.stringify(containerStates));
    } catch (error) {
        console.warn('Could not save container state:', error);
    }
}

// Load container state from localStorage - returns null if no saved state exists
function loadContainerState(containerId) {
    try {
        let containerStates = JSON.parse(localStorage.getItem('outlan_container_states') || '{}');
        return containerStates.hasOwnProperty(containerId) ? containerStates[containerId] : null;
    } catch (error) {
        console.warn('Could not load container state:', error);
        return null;
    }
}

// Initialize container states on page load - only apply saved states, leave defaults alone
function initializeContainerStates() {
    document.querySelectorAll('.container-row').forEach(containerRow => {
        const containerId = containerRow.getAttribute('data-container-id');
        const expandIcon = containerRow.querySelector('.expand-icon');
        const subnets = document.querySelectorAll(`tr.container-subnet[data-container-id="${containerId}"]`);
        
        if (containerId && expandIcon && subnets.length > 0) {
            const savedState = loadContainerState(containerId);
            
            // Only apply state if we have a saved preference, otherwise leave template defaults
            if (savedState !== null) {
                if (savedState) {
                    // Expand
                    expandIcon.classList.add('expanded');
                    expandIcon.textContent = '−';
                    subnets.forEach(subnet => {
                        subnet.style.display = 'table-row';
                    });
                } else {
                    // Collapse
                    expandIcon.classList.remove('expanded');
                    expandIcon.textContent = '+';
                    subnets.forEach(subnet => {
                        subnet.style.display = 'none';
                    });
                }
            }
        }
    });
}

// Mobile menu functionality
function toggleMobileMenu(trigger) {
    const menu = trigger.nextElementSibling;
    const isOpen = menu.classList.contains('show');
    
    // Close all other open menus
    document.querySelectorAll('.mobile-actions-menu.show').forEach(openMenu => {
        if (openMenu !== menu) {
            openMenu.classList.remove('show');
        }
    });
    
    // Toggle current menu
    if (isOpen) {
        menu.classList.remove('show');
    } else {
        menu.classList.add('show');
    }
}

// Initialize mobile menu event listeners
function initMobileMenu() {
    // Close mobile menus when clicking outside
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.mobile-row-actions') && !event.target.closest('.mobile-block-actions')) {
            document.querySelectorAll('.mobile-actions-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });
}

// Initialize UI components
document.addEventListener('DOMContentLoaded', function() {
    initializeContainerStates();
    initMobileMenu();
});