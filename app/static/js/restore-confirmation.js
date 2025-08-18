// Restore confirmation page countdown functionality
document.addEventListener('DOMContentLoaded', function() {
    let seconds = 5;
    const countdown = document.getElementById('countdown');
    const mainLink = document.getElementById('main-link');
    
    if (countdown && mainLink) {
        const interval = setInterval(() => {
            seconds--;
            countdown.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(interval);
                window.location.href = mainLink.href;
            }
        }, 1000);
    }
});