// Real-time validation for CIDR format
function initCidrValidation() {
    document.querySelectorAll('input[name="cidr"]').forEach(function(input) {
        // Prevent invalid characters (only allow numbers, periods, and forward slash)
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            if (!/[\d\.\/]/.test(char) && e.which !== 8 && e.which !== 9 && e.which !== 37 && e.which !== 39) {
                e.preventDefault();
            }
        });
        
        // Handle paste events to filter invalid content
        input.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            const validChars = pastedText.replace(/[^\d\.\/]/g, '');
            if (validChars) {
                this.value = validChars;
            }
        });
        
        // Real-time validation and cleaning
        input.addEventListener('input', function() {
            // Remove any invalid characters (keep only numbers, periods, and forward slash)
            this.value = this.value.replace(/[^\d\.\/]/g, '');
            
            const cidrPattern = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/;
            if (this.value && !cidrPattern.test(this.value)) {
                this.setCustomValidity('Please enter a valid CIDR format (e.g., 192.168.1.0/24)');
                this.style.borderColor = '#ef4444';
            } else {
                this.setCustomValidity('');
                this.style.borderColor = '';
            }
        });
        
        // Clear validation on blur if empty
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.setCustomValidity('');
                this.style.borderColor = '';
            }
        });
    });
}

// Real-time validation for base network (similar to CIDR validation)
function initBaseNetworkValidation() {
    document.querySelectorAll('input[name="base_network"], input.base-network-input').forEach(function(input) {
        // Prevent invalid characters
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            if (!/[\d\.\/]/.test(char) && e.which !== 8 && e.which !== 9 && e.which !== 37 && e.which !== 39) {
                e.preventDefault();
            }
        });
        
        // Handle paste events to filter invalid content
        input.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            const validChars = pastedText.replace(/[^\d\.\/]/g, '');
            if (validChars) {
                this.value = validChars;
            }
        });
        
        // Real-time validation and cleaning
        input.addEventListener('input', function() {
            // Remove any invalid characters (keep only numbers, periods, and forward slash)
            this.value = this.value.replace(/[^\d\.\/]/g, '');
            
            const cidrPattern = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/;
            if (this.value && !cidrPattern.test(this.value)) {
                this.setCustomValidity('Please enter a valid CIDR format (e.g., 192.168.1.0/24)');
                this.style.borderColor = '#ef4444';
            } else {
                this.setCustomValidity('');
                this.style.borderColor = '';
            }
        });
        
        // Clear validation on blur if empty
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.setCustomValidity('');
                this.style.borderColor = '';
            }
        });
    });
}

// Real-time validation for VLAN ID
function initVlanValidation() {
    document.querySelectorAll('input[name="vlan_id"]').forEach(function(input) {
        // Prevent non-numeric input
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            if (!/[\d]/.test(char) && e.which !== 8 && e.which !== 9 && e.which !== 37 && e.which !== 39) {
                e.preventDefault();
            }
        });
        
        // Handle paste events to filter non-numeric content
        input.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            const numericOnly = pastedText.replace(/[^\d]/g, '');
            if (numericOnly) {
                this.value = numericOnly;
            }
        });
        
        // Real-time validation
        input.addEventListener('input', function() {
            // Remove any non-numeric characters
            this.value = this.value.replace(/[^\d]/g, '');
            
            const vlan = parseInt(this.value);
            if (this.value && (vlan < 1 || vlan > 4094)) {
                this.setCustomValidity('VLAN ID must be between 1 and 4094');
                this.style.borderColor = '#ef4444';
            } else {
                this.setCustomValidity('');
                this.style.borderColor = '';
            }
        });
        
        // Clear validation on blur if empty
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.setCustomValidity('');
                this.style.borderColor = '';
            }
        });
    });
}

// Form submission with success feedback
function initFormValidation() {
    document.querySelectorAll('.subnet-form').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                return false;
            }
        });
    });
}

// Initialize all validation on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initCidrValidation();
    initBaseNetworkValidation();
    initVlanValidation();
    initFormValidation();
});