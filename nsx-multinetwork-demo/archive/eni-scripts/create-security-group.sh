#!/bin/bash
# Create security group for secondary networks

set -e

source ./aws-env.sh

echo "========================================"
echo "Creating Security Group"
echo "========================================"
echo ""

SG_NAME="nsx-demo-secondary-networks"
SG_DESC="Allow inter-pod communication on secondary networks"

# Check if security group already exists
EXISTING_SG=$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" \
              "Name=group-name,Values=$SG_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null)

if [[ $EXISTING_SG == sg-* ]]; then
    echo "ℹ️  Security group already exists: $EXISTING_SG"
    SG_ID=$EXISTING_SG
else
    echo "Creating security group: $SG_NAME..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "$SG_DESC" \
        --vpc-id $VPC_ID \
        --query 'GroupId' \
        --output text)

    echo "✓ Created: $SG_ID"
fi

echo ""
echo "Configuring inbound rules..."

# Allow all traffic from the same security group (pods can talk to each other)
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol all \
    --source-group $SG_ID 2>/dev/null || echo "  (Rule may already exist)"

# Allow all traffic from secondary network CIDRs
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol all \
    --cidr 10.0.200.0/24 2>/dev/null || echo "  (Rule may already exist)"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol all \
    --cidr 10.0.201.0/24 2>/dev/null || echo "  (Rule may already exist)"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol all \
    --cidr 10.0.202.0/24 2>/dev/null || echo "  (Rule may already exist)"

echo "✓ Inbound rules configured"
echo ""

echo "========================================"
echo "✓ Security Group Ready"
echo "========================================"
echo ""
echo "Security Group ID: $SG_ID"
echo ""

# Save SG_ID to aws-env.sh
echo "export SG_ID=\"$SG_ID\"" >> aws-env.sh

echo "✓ Added SG_ID to aws-env.sh"
echo ""
echo "Next: Run ./create-and-attach-enis.sh"
