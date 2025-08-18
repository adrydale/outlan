// Import/Export page functionality
document.addEventListener('DOMContentLoaded', function() {
    const importModeSelect = document.getElementById('import_mode');
    const replaceWarning = document.getElementById('replace-warning');
    
    if (importModeSelect && replaceWarning) {
        importModeSelect.addEventListener('change', function() {
            if (this.value === 'replace') {
                replaceWarning.style.display = 'block';
            } else {
                replaceWarning.style.display = 'none';
            }
        });
    }
});