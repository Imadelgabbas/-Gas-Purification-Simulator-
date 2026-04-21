/* ================================
   Gas Purification App JavaScript
   ================================ */

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Gas Purification App initialized');
    initializeEventListeners();
});

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    // Add event listeners here as functionality grows
}

/**
 * Utility function to make API calls
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise}
 */
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

/**
 * Display a notification message
 * @param {string} message - Message to display
 * @param {string} type - Alert type (success, danger, warning, info)
 */
function showNotification(message, type = 'info') {
    const alertClass = `alert-${type}`;
    const alertHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', alertHTML);
    }
}

/**
 * Update progress bar
 * @param {number} percentage - Progress percentage (0-100)
 */
function updateProgressBar(percentage) {
    const progressFill = document.getElementById('progressFill');
    if (progressFill) {
        progressFill.style.width = `${Math.min(100, percentage)}%`;
    }
}

/**
 * Show loading spinner
 * @param {boolean} show - Show or hide spinner
 */
function toggleLoadingSpinner(show = true) {
    // Implementation for loading spinner
    if (show) {
        console.log('Loading...');
    } else {
        console.log('Loading complete');
    }
}

/**
 * Validate form data
 * @param {object} formData - Form data to validate
 * @returns {boolean}
 */
function validateFormData(formData) {
    for (let key in formData) {
        if (formData[key] === '' || formData[key] === null) {
            showNotification(`Field ${key} is required`, 'warning');
            return false;
        }
    }
    return true;
}

/**
 * Reset form to initial state
 * @param {string} formId - ID of form to reset
 */
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

// Log initialization
console.log('Main JavaScript loaded successfully');
