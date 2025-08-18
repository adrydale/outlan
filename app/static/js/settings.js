// Settings page theme display functionality
(function() {
    // Get the actual theme from localStorage or document attribute
    const localStorageTheme = localStorage.getItem('theme');
    const documentTheme = document.documentElement.getAttribute('data-theme');
    const serverTheme = document.documentElement.getAttribute('data-server-theme') || 'light';
    
    // Determine the actual theme being used
    let actualTheme = localStorageTheme || documentTheme || serverTheme;
    
    // If no theme is set anywhere, default to server theme
    if (!actualTheme) {
        actualTheme = serverTheme;
    }
    
    // Check if localStorage is overriding the server theme
    const themeSourceElement = document.getElementById('theme-source');
    const themeValueElement = document.getElementById('theme-value');
    const mobileThemeSourceElement = document.getElementById('mobile-theme-source');
    const mobileThemeValueElement = document.getElementById('mobile-theme-value');
    
    if (localStorageTheme && localStorageTheme !== serverTheme) {
        // Update desktop elements
        if (themeSourceElement && themeValueElement) {
            themeSourceElement.textContent = 'LOCALSTORAGE';
            themeValueElement.textContent = localStorageTheme;
        }
        
        // Update mobile elements
        if (mobileThemeSourceElement && mobileThemeValueElement) {
            mobileThemeSourceElement.textContent = 'LOCALSTORAGE';
            mobileThemeValueElement.textContent = localStorageTheme;
        }
    }
})();