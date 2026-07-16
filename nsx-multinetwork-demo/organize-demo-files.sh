#!/bin/bash
set -e

# NSX Multi-Network Demo - File Organization Script
# Moves legacy/experimental files to archive, deletes obsolete files

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE_DIR="$DEMO_DIR/archive"

echo "=========================================="
echo "NSX Multi-Network Demo - File Cleanup"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Create archive/ directory"
echo "  2. Move 24 legacy files to archive/"
echo "  3. Delete 11 obsolete files"
echo "  4. Keep 9 essential files in main directory"
echo ""
echo "Directory: $DEMO_DIR"
echo ""

# Show what will be kept
echo "✅ Essential files that will be KEPT (9):"
echo "  - setup-aws-test-environment.sh"
echo "  - cleanup-aws-test-environment.sh"
echo "  - nad-aws-bridge-test.yaml"
echo "  - test-pods-demo.yaml"
echo "  - multi-networkpolicy-install.yaml"
echo "  - README-AWS-SETUP.md"
echo "  - QUICK-REFERENCE.md"
echo "  - INDEX.md"
echo "  - AWS_TEST_ENVIRONMENT_SUMMARY.md"
echo ""

# Confirm
read -p "Proceed with cleanup? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Creating archive directory..."

# Create archive directory
mkdir -p "$ARCHIVE_DIR"
mkdir -p "$ARCHIVE_DIR/experimental-nads"
mkdir -p "$ARCHIVE_DIR/eni-scripts"
mkdir -p "$ARCHIVE_DIR/legacy-docs"

# Archive ENI scripts
echo ""
echo "📦 Archiving ENI-related scripts..."
FILES_TO_ARCHIVE_SCRIPTS=(
    "aws-env.sh"
    "create-and-attach-enis.sh"
    "create-security-group.sh"
    "create-subnets-fixed.sh"
    "create-subnets.sh"
    "gather-aws-info.sh"
)

for file in "${FILES_TO_ARCHIVE_SCRIPTS[@]}"; do
    if [ -f "$DEMO_DIR/$file" ]; then
        mv "$DEMO_DIR/$file" "$ARCHIVE_DIR/eni-scripts/"
        echo "  ✓ Moved $file"
    fi
done

# Archive experimental NAD configurations
echo ""
echo "📦 Archiving experimental NAD configurations..."
FILES_TO_ARCHIVE_NADS=(
    "nad-aws-eni-final.yaml"
    "nad-aws-eni-l2-fixed.yaml"
    "nad-aws-eni-with-routes.yaml"
    "nad-aws-macvlan.yaml"
    "nad-aws-test-setup.yaml"
    "nad-aws-ipvlan-l3-working.yaml"
    "nad-bridge-routed.yaml"
    "nad-bridge-simple.yaml"
    "nad-ipvlan-l2.yaml"
    "nad-ipvlan-l3.yaml"
    "nad-macvlan-demo.yaml"
    "nad-macvlan-vlan-interfaces.yaml"
    "nad-macvlan-with-routes.yaml"
    "nad-simple-demo.yaml"
    "nad-single-network-demo.yaml"
    "nad-vlan-configured.yaml"
)

for file in "${FILES_TO_ARCHIVE_NADS[@]}"; do
    if [ -f "$DEMO_DIR/$file" ]; then
        mv "$DEMO_DIR/$file" "$ARCHIVE_DIR/experimental-nads/"
        echo "  ✓ Moved $file"
    fi
done

# Archive legacy documentation
echo ""
echo "📦 Archiving legacy documentation..."
FILES_TO_ARCHIVE_DOCS=(
    "AWS_MULTI_ENI_SETUP.md"
    "CONNECTIVITY_ANALYSIS.md"
    "DEMO_RESULTS.md"
    "DEPLOYMENT_SUMMARY.md"
    "FINAL_DEMO_SUMMARY.md"
    "SOLUTION_GUIDE_AWS.md"
)

for file in "${FILES_TO_ARCHIVE_DOCS[@]}"; do
    if [ -f "$DEMO_DIR/$file" ]; then
        mv "$DEMO_DIR/$file" "$ARCHIVE_DIR/legacy-docs/"
        echo "  ✓ Moved $file"
    fi
done

# Delete obsolete files
echo ""
echo "🗑️  Deleting obsolete files..."
FILES_TO_DELETE=(
    "check-app.sh"
    "check-pods.sh"
    "DEPLOY_FIX.sh"
    "redeploy-demo.sh"
    "simple-network-test.sh"
    "test-policy-enforcement.sh"
    "test-traffic-vlan.sh"
    "test-pods.yaml"
    "ops-translate.yaml"
    "CLEANUP-PLAN.md"
)

for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$DEMO_DIR/$file" ]; then
        rm "$DEMO_DIR/$file"
        echo "  ✓ Deleted $file"
    fi
done

# Create archive README
echo ""
echo "📝 Creating archive README..."
cat > "$ARCHIVE_DIR/README.md" <<'EOF'
# Archived Files

This directory contains experimental approaches and legacy files from the NSX multi-network demo development process.

## Directory Structure

- **eni-scripts/** - Scripts for AWS ENI-based approach (didn't work)
- **experimental-nads/** - Various NAD configurations tested (most didn't work)
- **legacy-docs/** - Old documentation and analysis

## Why These Were Archived

### ENI Scripts
The original plan was to use actual AWS Elastic Network Interfaces (ENIs) for secondary networks. This approach was complex and required:
- Creating AWS subnets
- Attaching ENIs to instances
- Registering secondary IPs with AWS
- Complex routing configuration

It was abandoned in favor of the simpler bridge CNI approach.

### Experimental NADs
These represent different CNI plugin approaches tested:
- **ipvlan L2** - Connectivity issues with pod-to-pod communication
- **ipvlan L3** - Required IP forwarding on host, device busy errors
- **macvlan** - Required AWS secondary IP registration, MAC address issues
- **bridge with routing** - Overly complex

The final working solution uses **bridge CNI** (nad-aws-bridge-test.yaml in parent directory).

### Legacy Docs
Documentation created during the troubleshooting and development process. Superseded by:
- README-AWS-SETUP.md
- QUICK-REFERENCE.md
- AWS_TEST_ENVIRONMENT_SUMMARY.md

## Reference Only

These files are kept for reference but are not part of the working solution.
For the current working setup, see the parent directory.
EOF

echo "  ✓ Created archive/README.md"

# Update INDEX.md to remove archived file references
echo ""
echo "📝 Updating INDEX.md..."

# Create a note about archived files
cat >> "$DEMO_DIR/INDEX.md" <<'EOF'

---

## 📦 Archived Files

Experimental and legacy files have been moved to the `archive/` directory.
These include:
- ENI-based approach scripts
- Experimental NAD configurations
- Legacy documentation

See `archive/README.md` for details.
EOF

echo "  ✓ Updated INDEX.md"

# Summary
echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Main directory now contains:"
ls -1 "$DEMO_DIR" | grep -E '\.(sh|yaml|md)$' | grep -v organize-demo-files.sh
echo ""
echo "Archived files location:"
echo "  $ARCHIVE_DIR/"
echo ""
echo "Files archived:"
find "$ARCHIVE_DIR" -type f | wc -l | xargs echo "  "
echo ""
echo "✅ Demo directory is now clean and organized!"
echo ""
echo "To verify everything still works:"
echo "  ./setup-aws-test-environment.sh"
echo ""
