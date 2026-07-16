#!/bin/bash
# Create and attach ENIs to worker nodes

set -e

source ./aws-env.sh

echo "========================================"
echo "Creating and Attaching ENIs"
echo "========================================"
echo ""

# Function to create and attach ENI
create_and_attach_eni() {
    local SUBNET_ID=$1
    local INSTANCE_ID=$2
    local DEVICE_INDEX=$3
    local NAME=$4

    echo "Creating ENI: $NAME..."
    echo "  Subnet: $SUBNET_ID"
    echo "  Instance: $INSTANCE_ID"
    echo "  Device Index: $DEVICE_INDEX"

    # Create ENI
    ENI_ID=$(aws ec2 create-network-interface \
        --subnet-id $SUBNET_ID \
        --groups $SG_ID \
        --description "$NAME" \
        --tag-specifications "ResourceType=network-interface,Tags=[{Key=Name,Value=$NAME}]" \
        --query 'NetworkInterface.NetworkInterfaceId' \
        --output text)

    if [[ $ENI_ID != eni-* ]]; then
        echo "  ❌ Failed to create ENI"
        return 1
    fi

    echo "  ✓ Created ENI: $ENI_ID"

    # Wait a moment for ENI to be ready
    sleep 2

    # Attach to instance
    echo "  Attaching to instance..."
    ATTACHMENT_ID=$(aws ec2 attach-network-interface \
        --network-interface-id $ENI_ID \
        --instance-id $INSTANCE_ID \
        --device-index $DEVICE_INDEX \
        --query 'AttachmentId' \
        --output text)

    if [[ $ATTACHMENT_ID != eni-attach-* ]]; then
        echo "  ❌ Failed to attach ENI"
        return 1
    fi

    echo "  ✓ Attached: $ATTACHMENT_ID"

    # Disable source/dest check (required for routing)
    aws ec2 modify-network-interface-attribute \
        --network-interface-id $ENI_ID \
        --no-source-dest-check >/dev/null 2>&1 || true

    echo "  ✓ Configured ENI"
    echo ""

    echo "$ENI_ID"
}

echo "Worker 1 (us-east-1a): $WORKER_1A"
echo "Worker 2 (us-east-1b): $WORKER_1B"
echo ""

echo "========================================
Creating ENIs for Worker 1 (us-east-1a)
========================================"
echo ""

WEB_ENI_1A=$(create_and_attach_eni $WEB_SUBNET_1A $WORKER_1A 1 "nsx-demo-web-worker1")
APP_ENI_1A=$(create_and_attach_eni $APP_SUBNET_1A $WORKER_1A 2 "nsx-demo-app-worker1")
DB_ENI_1A=$(create_and_attach_eni $DB_SUBNET_1A $WORKER_1A 3 "nsx-demo-db-worker1")

echo "========================================
Creating ENIs for Worker 2 (us-east-1b)
========================================"
echo ""

WEB_ENI_1B=$(create_and_attach_eni $WEB_SUBNET_1B $WORKER_1B 1 "nsx-demo-web-worker2")
APP_ENI_1B=$(create_and_attach_eni $APP_SUBNET_1B $WORKER_1B 2 "nsx-demo-app-worker2")
DB_ENI_1B=$(create_and_attach_eni $DB_SUBNET_1B $WORKER_1B 3 "nsx-demo-db-worker2")

echo "========================================"
echo "✓ All ENIs Created and Attached!"
echo "========================================"
echo ""
echo "Worker 1 (us-east-1a) ENIs:"
echo "  Web Tier: $WEB_ENI_1A (device index 1)"
echo "  App Tier: $APP_ENI_1A (device index 2)"
echo "  DB Tier:  $DB_ENI_1A (device index 3)"
echo ""
echo "Worker 2 (us-east-1b) ENIs:"
echo "  Web Tier: $WEB_ENI_1B (device index 1)"
echo "  App Tier: $APP_ENI_1B (device index 2)"
echo "  DB Tier:  $DB_ENI_1B (device index 3)"
echo ""

# Save ENI IDs to aws-env.sh
cat >> aws-env.sh <<EOF
export WEB_ENI_1A="$WEB_ENI_1A"
export APP_ENI_1A="$APP_ENI_1A"
export DB_ENI_1A="$DB_ENI_1A"
export WEB_ENI_1B="$WEB_ENI_1B"
export APP_ENI_1B="$APP_ENI_1B"
export DB_ENI_1B="$DB_ENI_1B"
EOF

echo "✓ Saved ENI IDs to aws-env.sh"
echo ""
echo "IMPORTANT: ENIs are attached, but nodes need to be rebooted"
echo "           or NetworkManager restarted to recognize them."
echo ""
echo "Next: Run ./configure-enis-on-nodes.sh"
