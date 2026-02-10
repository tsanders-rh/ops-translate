# Playwright HTML Report Demo

This directory contains Playwright tests for the ops-translate HTML report interactive features.

## What's Tested

The tests validate the interactive features of the static HTML report:

1. **Card-based filtering** - Click summary cards to filter gaps by classification
2. **Filter indicator** - Shows/hides based on active filter
3. **Gap item visibility** - Only matching items shown when filtered
4. **Clear filter** - Reset to show all gaps
5. **Export buttons** (if implemented) - Download functionality

## Setup

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install chromium
```

## Running Tests

### Standard test mode

```bash
# Run all tests
npm run test:playwright

# Run tests in headed mode (see the browser)
npm run test:playwright:headed

# Run tests with UI mode (interactive debugging)
npm run test:playwright:ui
```

### Demo/Presentation mode

The demo mode runs slower with pauses between actions, perfect for recordings or presentations:

```bash
npm run test:playwright:demo
```

This runs the "demo mode" test with:
- 1920x1080 viewport (good for recordings)
- Slower interactions with pauses
- Deterministic click path through filtering features

## Report Structure

The tests target the sample HTML report:

```
examples/sample-report/
  ├── index.html          # Main report
  └── assets/
      ├── app.js          # Interactive filtering logic
      └── styles.css      # Styling
```

## Configuration

See `playwright.config.ts` in the project root for:
- Web server configuration (serves the sample report)
- Timeout settings
- Video/screenshot capture settings
- Viewport sizes

## CI Integration

The tests are designed to work in CI environments:
- Uses `http-server` to serve static files
- No external dependencies required
- Deterministic test execution
- Screenshots/videos on failure

## Recording a Demo

To record a demo video:

```bash
# Run in headed mode
npm run test:playwright:demo

# Or record with Playwright trace viewer
npx playwright test --trace on

# View the trace
npx playwright show-trace test-results/.../trace.zip
```

## Troubleshooting

**Port already in use**: If port 4173 is busy, kill the process or update `playwright.config.ts`

**Report not found**: Ensure `examples/sample-report/index.html` exists

**Tests fail on filter**: Check that `assets/app.js` implements the filtering logic
