// Error page functionality
function toggleTraceback() {
    const content = document.getElementById('traceback-content');
    const button = document.querySelector('.traceback-toggle');
    const toggleText = button.querySelector('.toggle-text');
    const toggleIcon = button.querySelector('.toggle-icon');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggleText.textContent = 'Hide Technical Details';
        toggleIcon.textContent = '▲';
    } else {
        content.style.display = 'none';
        toggleText.textContent = 'Show Technical Details';
        toggleIcon.textContent = '▼';
    }
}