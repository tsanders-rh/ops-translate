#!/usr/bin/env bash
#
# Capture screenshots of HTML report for documentation
#
# Usage:
#   ./capture-screenshots.sh
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}ops-translate HTML Report Screenshots${NC}"
echo ""

# Create screenshots directory
mkdir -p media/screenshots

echo -e "${YELLOW}Capturing screenshots...${NC}"
echo ""

# Run Playwright screenshot test
npx playwright test tests/playwright/screenshots.spec.ts \
    --config=playwright-demo.config.ts \
    --headed

echo ""
echo -e "${GREEN}✓ Screenshots captured!${NC}"
echo ""

# List captured screenshots
echo -e "${BLUE}Captured screenshots:${NC}"
ls -lh media/screenshots/*.png | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo -e "${BLUE}Location:${NC} media/screenshots/"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review screenshots in media/screenshots/"
echo "  2. Add to README.md with:"
echo "     ![Description](media/screenshots/filename.png)"
echo "  3. Commit to repo: git add media/screenshots/ && git commit -m 'Add report screenshots'"
echo ""
