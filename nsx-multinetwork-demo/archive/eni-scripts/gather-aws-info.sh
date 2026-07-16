#!/bin/bash
# Gather AWS information for multi-ENI setup

set -e

echo "========================================"
echo "AWS Multi-ENI Setup - Information Gathering"
echo "========================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   brew install awscli  (on macOS)"
    echo "   or visit: https://aws.amazon.com/cli/"
    exit 1
fi

echo "✓ AWS CLI found"
echo ""

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run:"
    echo "   aws configure"
    exit 1
fi

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "✓ AWS Account: $ACCOUNT"
echo ""

# Find worker nodes
echo "Finding OpenShift worker nodes..."
WORKERS=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=*tsanders-virt-demo*worker*" \
              "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].[InstanceId,PrivateIpAddress,Placement.AvailabilityZone,VpcId,SubnetId]' \
    --output text)

if [ -z "$WORKERS" ]; then
    echo "❌ No worker nodes found. Check cluster name filter."
    exit 1
fi

echo "$WORKERS" | while read INSTANCE_ID PRIVATE_IP AZ VPC_ID SUBNET_ID; do
    echo "  Worker: $INSTANCE_ID"
    echo "    IP: $PRIVATE_IP"
    echo "    AZ: $AZ"
    echo "    VPC: $VPC_ID"
    echo "    Subnet: $SUBNET_ID"
    echo ""
done

# Get VPC info
echo "Getting VPC information..."
VPC_ID=$(echo "$WORKERS" | head -1 | awk '{print $4}')
VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID --query 'Vpcs[0].CidrBlock' --output text)
echo "  VPC ID: $VPC_ID"
echo "  VPC CIDR: $VPC_CIDR"
echo ""

# Get AZ
AZ=$(echo "$WORKERS" | head -1 | awk '{print $3}')
echo "  Availability Zone: $AZ"
echo ""

# Check existing subnets
echo "Existing subnets in VPC:"
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].[CidrBlock,SubnetId,Tags[?Key==`Name`].Value|[0]]' \
    --output table

echo ""
echo "========================================"
echo "Summary - Save This Information:"
echo "========================================"
echo "VPC_ID=$VPC_ID"
echo "VPC_CIDR=$VPC_CIDR"
echo "AZ=$AZ"
echo ""
echo "Worker Instances:"
echo "$WORKERS" | awk '{print $1, $2}'
echo ""
echo "Recommended Secondary Subnets (verify no conflicts):"
echo "  Web Tier:  10.10.100.0/24"
echo "  App Tier:  10.10.150.0/24"
echo "  DB Tier:   10.10.200.0/24"
echo ""
echo "Next: Create these subnets in AWS Console or use create-subnets.sh"
