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
        setupClearFilterButton();
        setupViewFindingsLinks();
    }

    /**
     * Setup click handlers for summary cards to filter gaps list
     */
    function setupCardFiltering() {
        const cards = document.querySelectorAll('.summary-cards .card');
        const gapItems = document.querySelectorAll('.gap-item');
        const filterIndicator = document.getElementById('filter-indicator');
        const filterName = document.getElementById('filter-name');

        if (cards.length === 0 || gapItems.length === 0) {
            return;  // No filtering needed
        }

        let activeFilter = null;

        cards.forEach(card => {
            card.addEventListener('click', function() {
                const filter = this.dataset.filter;
                const filterLabel = this.querySelector('.card-label').textContent;

                // Toggle filter
                if (activeFilter === filter) {
                    // Clear filter
                    clearFilter();
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

                    // Show filter indicator
                    if (filterIndicator && filterName) {
                        filterName.textContent = filterLabel;
                        filterIndicator.classList.remove('hidden');
                    }

                    // Scroll to gaps section
                    const gapsSection = document.querySelector('.gaps-section');
                    if (gapsSection) {
                        gapsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        });

        // Make clearFilter accessible to other functions
        window.clearGapFilter = clearFilter;

        function clearFilter() {
            activeFilter = null;
            cards.forEach(c => c.classList.remove('active-filter'));
            gapItems.forEach(item => item.classList.remove('hidden'));

            // Hide filter indicator
            if (filterIndicator) {
                filterIndicator.classList.add('hidden');
            }
        }
    }

    /**
     * Setup clear filter button
     */
    function setupClearFilterButton() {
        const clearBtn = document.getElementById('clear-filter');
        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                if (window.clearGapFilter) {
                    window.clearGapFilter();
                }
            });
        }
    }

    /**
     * Setup "View Findings" links to clear filters before navigating
     */
    function setupViewFindingsLinks() {
        const viewFindingsLinks = document.querySelectorAll('.action-link');

        viewFindingsLinks.forEach(link => {
            link.addEventListener('click', function() {
                // Clear any active filter so user sees all findings for this file
                if (window.clearGapFilter) {
                    window.clearGapFilter();
                }
                // Let the default anchor navigation happen
            });
        });
    }

})();
