#!/bin/bash
# Create secondary network subnets for multi-ENI setup
# Using 10.0.x.x range to fit within VPC CIDR 10.0.0.0/16

set -e

VPC_ID="vpc-09b9e6eda6b4a762f"
AZ_1A="us-east-1a"
AZ_1B="us-east-1b"

echo "========================================"
echo "Creating Secondary Network Subnets"
echo "========================================"
echo ""
echo "VPC: $VPC_ID (CIDR: 10.0.0.0/16)"
echo "AZs: $AZ_1A, $AZ_1B"
echo ""
echo "Using 10.0.200-202.x ranges (within VPC CIDR)"
echo ""

# Function to create subnet
create_subnet() {
    local NAME=$1
    local CIDR=$2
    local AZ=$3

    echo "Creating subnet: $NAME ($CIDR) in $AZ..."

    # Check if subnet already exists
    EXISTING=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" \
                  "Name=cidr-block,Values=$CIDR" \
        --query 'Subnets[0].SubnetId' \
        --output text 2>/dev/null)

    if [[ $EXISTING == subnet-* ]]; then
        echo "  ℹ️  Subnet already exists: $EXISTING"
        echo "$EXISTING"
        return 0
    fi

    SUBNET_ID=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block $CIDR \
        --availability-zone $AZ \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$NAME}]" \
        --query 'Subnet.SubnetId' \
        --output text 2>&1)

    if [[ $SUBNET_ID == subnet-* ]]; then
        echo "  ✓ Created: $SUBNET_ID"
        echo "$SUBNET_ID"
    else
        echo "  ❌ Failed: $SUBNET_ID"
        return 1
    fi
}

echo "Creating Web Tier subnets (10.0.200.x)..."
WEB_SUBNET_1A=$(create_subnet "nsx-demo-web-tier-1a" "10.0.200.0/25" "$AZ_1A")
WEB_SUBNET_1B=$(create_subnet "nsx-demo-web-tier-1b" "10.0.200.128/25" "$AZ_1B")
echo ""

echo "Creating App Tier subnets (10.0.201.x)..."
APP_SUBNET_1A=$(create_subnet "nsx-demo-app-tier-1a" "10.0.201.0/25" "$AZ_1A")
APP_SUBNET_1B=$(create_subnet "nsx-demo-app-tier-1b" "10.0.201.128/25" "$AZ_1B")
echo ""

echo "Creating DB Tier subnets (10.0.202.x)..."
DB_SUBNET_1A=$(create_subnet "nsx-demo-db-tier-1a" "10.0.202.0/25" "$AZ_1A")
DB_SUBNET_1B=$(create_subnet "nsx-demo-db-tier-1b" "10.0.202.128/25" "$AZ_1B")
echo ""

echo "========================================"
echo "✓ Subnets Created Successfully"
echo "========================================"
echo ""
echo "Web Tier (corresponds to NSX VLAN 100):"
echo "  us-east-1a: $WEB_SUBNET_1A (10.0.200.0/25)"
echo "  us-east-1b: $WEB_SUBNET_1B (10.0.200.128/25)"
echo ""
echo "App Tier (corresponds to NSX VLAN 150):"
echo "  us-east-1a: $APP_SUBNET_1A (10.0.201.0/25)"
echo "  us-east-1b: $APP_SUBNET_1B (10.0.201.128/25)"
echo ""
echo "DB Tier (corresponds to NSX VLAN 200):"
echo "  us-east-1a: $DB_SUBNET_1A (10.0.202.0/25)"
echo "  us-east-1b: $DB_SUBNET_1B (10.0.202.128/25)"
echo ""

# Save to file for next steps
cat > aws-env.sh <<EOF
# AWS Environment Variables for Multi-ENI Setup
export VPC_ID="$VPC_ID"
export WEB_SUBNET_1A="$WEB_SUBNET_1A"
export WEB_SUBNET_1B="$WEB_SUBNET_1B"
export APP_SUBNET_1A="$APP_SUBNET_1A"
export APP_SUBNET_1B="$APP_SUBNET_1B"
export DB_SUBNET_1A="$DB_SUBNET_1A"
export DB_SUBNET_1B="$DB_SUBNET_1B"
export WORKER_1A="i-03e6c4ac733d51f1a"
export WORKER_1B="i-04ac50947e72a0e26"
EOF

echo "✓ Environment variables saved to aws-env.sh"
echo ""
echo "Note: Using 10.0.200-202.x instead of original 10.10.x due to VPC CIDR"
echo "      This doesn't affect the demo - it's just different IP space"
echo ""
echo "Next: Run ./create-security-group.sh"
