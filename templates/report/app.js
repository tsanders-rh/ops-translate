/**
 * ops-translate HTML Report Interactive Features
 *
 * Provides filtering and interactive behavior without requiring a server.
 */

(function() {
    'use strict';

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        setupCardFiltering();
    }

    /**
     * Setup click handlers for summary cards to filter gaps list
     */
    function setupCardFiltering() {
        const cards = document.querySelectorAll('.summary-cards .card');
        const gapItems = document.querySelectorAll('.gap-item');

        if (cards.length === 0 || gapItems.length === 0) {
            return;  // No filtering needed
        }

        let activeFilter = null;

        cards.forEach(card => {
            card.addEventListener('click', function() {
                const filter = this.dataset.filter;

                // Toggle filter
                if (activeFilter === filter) {
                    // Clear filter
                    activeFilter = null;
                    cards.forEach(c => c.classList.remove('active-filter'));
                    gapItems.forEach(item => item.classList.remove('hidden'));
                } else {
                    // Apply filter
                    activeFilter = filter;

                    // Update card styles
                    cards.forEach(c => c.classList.remove('active-filter'));
                    this.classList.add('active-filter');

                    // Filter gaps
                    gapItems.forEach(item => {
                        if (item.dataset.level === filter) {
                            item.classList.remove('hidden');
                        } else {
                            item.classList.add('hidden');
                        }
                    });

                    // Scroll to gaps section
                    const gapsSection = document.querySelector('.gaps-section');
                    if (gapsSection) {
                        gapsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        });
    }

})();
