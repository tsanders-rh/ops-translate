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
        setupExportButtons();
        setupSupportedToggle();
        setupInterviewQuestions();
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

    /**
     * Setup export buttons (PDF and CSV)
     */
    function setupExportButtons() {
        const pdfBtn = document.getElementById('export-pdf');
        const csvBtn = document.getElementById('export-csv');

        if (pdfBtn) {
            pdfBtn.addEventListener('click', exportAsPDF);
        }

        if (csvBtn) {
            csvBtn.addEventListener('click', exportAsCSV);
        }
    }

    /**
     * Export report as PDF using browser print
     */
    function exportAsPDF() {
        window.print();
    }

    /**
     * Export migration tasks as CSV
     */
    function exportAsCSV() {
        if (!window.reportData || !window.reportData.gaps || !window.reportData.gaps.components) {
            alert('No gaps data available for export');
            return;
        }

        const components = window.reportData.gaps.components;
        const workspace = window.reportData.workspace || 'workspace';
        const timestamp = window.reportData.timestamp || new Date().toISOString();

        // CSV header
        const headers = [
            'Component',
            'Type',
            'Level',
            'Migration Path',
            'Location',
            'Reason',
            'OpenShift Equivalent',
            'Recommendations'
        ];

        // Build CSV rows
        const rows = components.map(comp => {
            return [
                escapeCSV(comp.name || ''),
                escapeCSV(comp.component_type || ''),
                escapeCSV(comp.level || ''),
                escapeCSV(comp.migration_path || ''),
                escapeCSV(comp.location || ''),
                escapeCSV(comp.reason || ''),
                escapeCSV(comp.openshift_equivalent || ''),
                escapeCSV((comp.recommendations || []).join('; '))
            ];
        });

        // Combine header and rows
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        // Create download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const filename = `${workspace}-migration-tasks-${timestamp.replace(/:/g, '-')}.csv`;

        if (navigator.msSaveBlob) {
            // IE 10+
            navigator.msSaveBlob(blob, filename);
        } else {
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    /**
     * Escape CSV field
     */
    function escapeCSV(field) {
        if (field === null || field === undefined) {
            return '';
        }
        const str = String(field);
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return '"' + str.replace(/"/g, '""') + '"';
        }
        return str;
    }

    /**
     * Initialize recommendation filters
     */
    function initRecommendationFilters() {
        const filterButtons = document.querySelectorAll('.rec-filter-btn');
        const recommendationCards = document.querySelectorAll('.recommendation-card');

        if (filterButtons.length === 0 || recommendationCards.length === 0) {
            return;
        }

        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                const selectedTeam = button.getAttribute('data-team');

                // Update active button
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                // Filter cards
                recommendationCards.forEach(card => {
                    const cardTeam = card.getAttribute('data-team');
                    if (selectedTeam === 'all' || cardTeam === selectedTeam) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        });
    }

    /**
     * Setup toggle for showing/hiding SUPPORTED patterns
     */
    function setupSupportedToggle() {
        const toggleBtn = document.getElementById('toggle-supported');
        if (!toggleBtn) {
            return;  // No toggle button on this page
        }

        const supportedItems = document.querySelectorAll('.gap-item.supported-hidden');
        const toggleText = toggleBtn.querySelector('.toggle-text');
        const supportedCount = toggleBtn.querySelector('.supported-count');

        let isShowing = false;

        toggleBtn.addEventListener('click', function() {
            isShowing = !isShowing;

            supportedItems.forEach(item => {
                if (isShowing) {
                    item.classList.add('show-supported');
                } else {
                    item.classList.remove('show-supported');
                }
            });

            // Update button text and icon
            if (isShowing) {
                toggleText.textContent = 'Hide Supported Patterns';
                toggleBtn.classList.add('active');
                supportedCount.textContent = `(${supportedItems.length} shown)`;
            } else {
                toggleText.textContent = 'Show Supported Patterns';
                toggleBtn.classList.remove('active');
                supportedCount.textContent = `(${supportedItems.length} hidden)`;
            }
        });
    }

    // Initialize recommendation filters on page load
    initRecommendationFilters();

    /**
     * Setup interview question handlers
     */
    function setupInterviewQuestions() {
        const generateButtons = document.querySelectorAll('.interview-generate-yaml');

        generateButtons.forEach(button => {
            button.addEventListener('click', function() {
                const componentLocation = this.getAttribute('data-component-location');
                const interviewSection = this.closest('.interview-section');
                const questions = interviewSection.querySelectorAll('.interview-question');

                // Collect answers
                const answers = {};
                let allAnswered = true;

                questions.forEach(question => {
                    const questionId = question.getAttribute('data-question-id');
                    const selectedOption = question.querySelector('input[type="radio"]:checked');

                    if (selectedOption) {
                        answers[questionId] = selectedOption.value;
                    } else {
                        allAnswered = false;
                    }
                });

                if (!allAnswered) {
                    alert('Please answer all questions before generating the YAML snippet.');
                    return;
                }

                // Generate YAML snippet
                const yamlSnippet = generateAnswersYAML(answers);

                // Display YAML output
                const yamlOutput = interviewSection.querySelector('.interview-yaml-output');
                const yamlCodeElement = yamlOutput.querySelector('.yaml-snippet');
                yamlCodeElement.textContent = yamlSnippet;
                yamlOutput.style.display = 'block';

                // Setup copy button
                const copyBtn = yamlOutput.querySelector('.copy-yaml-btn');
                setupCopyButton(copyBtn, yamlSnippet);
            });
        });
    }

    /**
     * Generate answers.yaml formatted snippet
     */
    function generateAnswersYAML(answers) {
        const lines = [];

        for (const [questionId, answer] of Object.entries(answers)) {
            lines.push(`  ${questionId}: ${answer}`);
        }

        return lines.join('\n');
    }

    /**
     * Setup copy to clipboard functionality
     */
    function setupCopyButton(button, text) {
        // Remove old event listeners by cloning
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        newButton.addEventListener('click', function() {
            // Try modern clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(() => {
                    showCopiedFeedback(newButton);
                }).catch(err => {
                    fallbackCopy(text, newButton);
                });
            } else {
                fallbackCopy(text, newButton);
            }
        });
    }

    /**
     * Fallback copy method for older browsers
     */
    function fallbackCopy(text, button) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();

        try {
            document.execCommand('copy');
            showCopiedFeedback(button);
        } catch (err) {
            alert('Failed to copy to clipboard. Please copy manually.');
        }

        document.body.removeChild(textarea);
    }

    /**
     * Show visual feedback that text was copied
     */
    function showCopiedFeedback(button) {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('copied');

        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }

})();
