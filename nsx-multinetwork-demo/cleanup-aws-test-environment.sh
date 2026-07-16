#!/bin/bash
set -e

# NSX Multi-Network Demo - AWS Test Environment Cleanup Script
# Removes all resources created by setup-aws-test-environment.sh

NAMESPACE="${NAMESPACE:-virt-lab}"

echo "=========================================="
echo "NSX Multi-Network Demo - Cleanup"
echo "=========================================="
echo ""
echo "This will remove:"
echo "  - Namespace: $NAMESPACE (and all resources within)"
echo "  - Note: iptables rules will persist until node reboot"
echo ""

# Confirm deletion
read -p "Are you sure you want to delete namespace '$NAMESPACE'? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Deleting namespace '$NAMESPACE'..."

if oc get namespace "$NAMESPACE" &> /dev/null; then
    oc delete namespace "$NAMESPACE" --wait=true
    echo "✓ Namespace '$NAMESPACE' deleted"
else
    echo "ℹ Namespace '$NAMESPACE' does not exist"
fi

echo ""
echo "=========================================="
echo "Cleanup Complete"
echo "=========================================="
echo ""
echo "Note: iptables FORWARD rules on worker nodes will persist until"
echo "      the nodes are rebooted. They are harmless and allow traffic"
echo "      between 10.244.0.0/16 networks."
echo ""
echo "To manually remove iptables rules now:"
echo "  for node in \$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[*].metadata.name}'); do"
echo "    oc debug node/\$node -- chroot /host iptables -D FORWARD -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT"
echo "  done"
echo ""
