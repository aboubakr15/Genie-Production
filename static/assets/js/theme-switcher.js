/*--------------------------------------------------------------
# GENIE THEME SWITCHER
# Version: 1.0
# Description: Toggle between dark and light themes with localStorage persistence
--------------------------------------------------------------*/

(function() {
    'use strict';

    // Theme configuration
    const THEME_STORAGE_KEY = 'genie-theme';
    const THEME_DARK = 'dark';
    const THEME_LIGHT = 'light';

    /**
     * Get the current theme from localStorage or default to dark
     */
    function getCurrentTheme() {
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        return savedTheme || THEME_DARK;
    }

    /**
     * Apply theme to the document
     */
    function applyTheme(theme) {
        const root = document.documentElement;
        root.setAttribute('data-theme', theme);

        // Store the theme preference
        localStorage.setItem(THEME_STORAGE_KEY, theme);

        // Update button text and icon
        updateThemeButton(theme);

        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    /**
     * Toggle between themes
     */
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
        applyTheme(newTheme);

        // Add a subtle animation
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    /**
     * Update theme toggle button appearance
     */
    function updateThemeButton(theme) {
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (!themeBtn) return;

        const icon = themeBtn.querySelector('i');
        const text = themeBtn.querySelector('.theme-text');

        if (theme === THEME_LIGHT) {
            // Currently light, show option to switch to dark
            if (icon) {
                icon.className = 'bi bi-moon-stars-fill me-2';
            }
            if (text) {
                text.textContent = 'Dark Mode';
            }
            themeBtn.className = 'dropdown-item theme-toggle-btn';
        } else {
            // Currently dark, show option to switch to light
            if (icon) {
                icon.className = 'bi bi-sun-fill me-2';
            }
            if (text) {
                text.textContent = 'Light Mode';
            }
            themeBtn.className = 'dropdown-item theme-toggle-btn';
        }
    }

    /**
     * Initialize theme on page load
     */
    function initTheme() {
        // Apply saved theme immediately to prevent flash
        const theme = getCurrentTheme();
        applyTheme(theme);
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', attachListeners);
        } else {
            attachListeners();
        }
    }

    function attachListeners() {
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (themeBtn) {
            themeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                toggleTheme();
            });
        }
    }

    // Initialize immediately (before DOM ready) to prevent flash
    initTheme();

    // Setup event listeners when DOM is ready
    setupEventListeners();

    // Expose toggleTheme globally for manual triggering if needed
    window.toggleGenieTheme = toggleTheme;
    window.getGenieTheme = getCurrentTheme;

})();
