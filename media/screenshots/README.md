# HTML Report Screenshots

Screenshots of the ops-translate HTML report for documentation and README.

## Captured Screenshots

### Executive Summary
**File:** `executive-summary.png` (398K)
**Description:** Overview of the Executive tab with translation summary and migration story

### Architecture Overview
**File:** `architecture-overview.png` (169K)
**Description:** Architecture tab showing classification cards and component breakdown

### Classification Cards
**File:** `classification-cards.png` (16K)
**Description:** Close-up of interactive classification cards (SUPPORTED, PARTIAL, BLOCKED, MANUAL)

### Gap Analysis
**File:** `gap-analysis.png` (255K)
**Description:** Detailed gap analysis showing component-by-component migration guidance

### Filtered View
**File:** `filtered-view.png` (223K)
**Description:** Demonstration of interactive filtering (showing PARTIAL components)

### Implementation Guide
**File:** `implementation-guide.png` (284K)
**Description:** Implementation tab with step-by-step migration instructions

### Decision Interview Overview
**File:** `decision-interview-overview.png` (320K)
**Description:** Decision Interview tab overview with summary cards

### Decision Interview Questions
**File:** `decision-interview-questions.png` (300K)
**Description:** Interactive question packs for gathering migration context

### Full Executive Page
**File:** `full-report-executive.png` (942K)
**Description:** Full-page screenshot of Executive tab for comprehensive overview

## Regenerating Screenshots

To regenerate all screenshots:

```bash
./capture-screenshots.sh
```

## Usage in README

Example markdown for embedding screenshots:

```markdown
## Sample HTML Report

### Executive Summary
![Executive Summary](media/screenshots/executive-summary.png)

### Interactive Classification
![Classification Cards](media/screenshots/classification-cards.png)

### Decision Interview
![Decision Interview](media/screenshots/decision-interview-overview.png)
```

## Technical Details

- Resolution: 2560x1440 (2K) for high quality
- Format: PNG for lossless quality
- Browser: Chromium via Playwright
- Source: examples/sample-report/index.html
