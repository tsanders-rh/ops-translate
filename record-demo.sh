#!/usr/bin/env bash
#
# Record Playwright demo video of HTML report
#
# Usage:
#   ./record-demo.sh                    # Record demo mode test
#   ./record-demo.sh --all              # Record all tests
#   ./record-demo.sh --codegen          # Interactive recording
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create output directory for videos
mkdir -p media/demos

echo -e "${BLUE}ops-translate HTML Report Demo Recording${NC}"
echo ""

case "${1:-demo}" in
    --all)
        echo -e "${YELLOW}Recording all tests...${NC}"
        npx playwright test --config=playwright-demo.config.ts --headed
        ;;
    --codegen)
        echo -e "${YELLOW}Starting interactive recording...${NC}"
        npx playwright codegen http://127.0.0.1:4173/index.html
        ;;
    *)
        echo -e "${YELLOW}Recording demo mode test...${NC}"
        npx playwright test --config=playwright-demo.config.ts --headed -g "demo mode"
        ;;
esac

echo ""
echo -e "${GREEN}Recording complete!${NC}"
echo ""

# Find the most recent video
LATEST_VIDEO=$(find test-results -name "*.webm" -type f -print0 | xargs -0 ls -t | head -1)

if [ -n "$LATEST_VIDEO" ]; then
    echo -e "${BLUE}Latest video:${NC} $LATEST_VIDEO"

    # Copy to media/demos with timestamp
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    DEMO_VIDEO="media/demos/html-report-demo-${TIMESTAMP}.webm"
    cp "$LATEST_VIDEO" "$DEMO_VIDEO"

    echo -e "${GREEN}Saved to:${NC} $DEMO_VIDEO"
    echo ""

    # Show file size
    SIZE=$(du -h "$DEMO_VIDEO" | cut -f1)
    echo -e "${BLUE}File size:${NC} $SIZE"

    # Optional: Convert to MP4 if ffmpeg is available
    if command -v ffmpeg &> /dev/null; then
        echo ""
        read -p "Convert to MP4? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            MP4_VIDEO="${DEMO_VIDEO%.webm}.mp4"
            echo -e "${YELLOW}Converting to MP4...${NC}"
            ffmpeg -i "$DEMO_VIDEO" -c:v libx264 -preset slow -crf 22 -c:a aac -b:a 128k "$MP4_VIDEO" -y
            echo -e "${GREEN}MP4 saved to:${NC} $MP4_VIDEO"
        fi
    fi

    echo ""
    echo -e "${BLUE}To view:${NC}"
    echo "  open \"$DEMO_VIDEO\""
    echo ""
    echo -e "${BLUE}To clean up test artifacts:${NC}"
    echo "  rm -rf test-results/ playwright-report/"
else
    echo -e "${YELLOW}No video found. Recording may have failed.${NC}"
fi
