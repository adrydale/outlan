// Snapshot summary collapsible functionality
function initSnapshotCollapsible() {
    const snapshotSummary = document.getElementById('snapshot-summary');
    const snapshotToggle = document.getElementById('snapshot-toggle');
    const snapshotContent = document.getElementById('snapshot-content');
    const toggleIcon = document.getElementById('snapshot-toggle-icon');
    
    if (!snapshotSummary || !snapshotToggle || !snapshotContent || !toggleIcon) {
        return; // Not on a page with snapshot summary
    }
    
    // Check if we're on mobile
    let isMobile = window.innerWidth <= 767;
    
    // Get stored state or use default
    const storageKey = 'snapshot-summary-collapsed';
    const storedState = localStorage.getItem(storageKey);
    
    let isCollapsed;
    if (storedState !== null) {
        // Use stored preference
        isCollapsed = storedState === 'true';
    } else {
        // Use default: collapsed on both desktop and mobile
        isCollapsed = true;
    }
    
    // Apply initial state
    updateSnapshotState(isCollapsed);
    
    // Add click handler
    snapshotToggle.addEventListener('click', function() {
        const currentState = snapshotSummary.classList.contains('collapsed');
        const newState = !currentState;
        updateSnapshotState(newState);
        localStorage.setItem(storageKey, newState.toString());
    });
    
    function updateSnapshotState(collapsed) {
        if (collapsed) {
            snapshotSummary.classList.add('collapsed');
            snapshotToggle.setAttribute('aria-expanded', 'false');
            toggleIcon.innerHTML = '<path d="M19 13H13v6h-2v-6H5v-2h6V5h2v6h6v2z"/>';
        } else {
            snapshotSummary.classList.remove('collapsed');
            snapshotToggle.setAttribute('aria-expanded', 'true');
            toggleIcon.innerHTML = '<path d="M19 13H5v-2h14v2z"/>';
        }
        
        // Add mobile-specific class for mobile devices
        if (isMobile && collapsed) {
            snapshotSummary.classList.add('mobile-collapsed');
        } else {
            snapshotSummary.classList.remove('mobile-collapsed');
        }
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        const newIsMobile = window.innerWidth <= 767;
        if (newIsMobile !== isMobile) {
            isMobile = newIsMobile;
            const currentState = snapshotSummary.classList.contains('collapsed');
            if (isMobile && currentState) {
                snapshotSummary.classList.add('mobile-collapsed');
            } else {
                snapshotSummary.classList.remove('mobile-collapsed');
            }
        }
    });
}

// Initialize snapshot collapsible on page load
document.addEventListener('DOMContentLoaded', initSnapshotCollapsible);