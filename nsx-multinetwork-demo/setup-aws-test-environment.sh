#!/bin/bash
set -e

# NSX Multi-Network Demo - AWS Test Environment Setup Script
# This script configures an OpenShift cluster on AWS for testing MultiNetworkPolicy
#
# Prerequisites:
# - OpenShift 4.12+ cluster on AWS
# - Cluster admin access
# - MultiNetworkPolicy enabled on cluster
# - kubectl/oc CLI configured

NAMESPACE="${NAMESPACE:-virt-lab}"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

echo "=========================================="
echo "NSX Multi-Network Demo - AWS Setup"
echo "=========================================="
echo ""
echo "Cluster: $(oc whoami --show-server 2>/dev/null || echo 'Not connected')"
echo "Namespace: $NAMESPACE"
echo "Kubeconfig: $KUBECONFIG_PATH"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check oc/kubectl
    if ! command -v oc &> /dev/null; then
        echo "❌ ERROR: 'oc' command not found. Please install OpenShift CLI."
        exit 1
    fi

    # Check cluster connection
    if ! oc whoami &> /dev/null; then
        echo "❌ ERROR: Not connected to OpenShift cluster. Please login first."
        exit 1
    fi

    # Check cluster admin permissions
    if ! oc auth can-i create machineconfigs &> /dev/null; then
        echo "⚠️  WARNING: You may not have cluster admin permissions. Node configuration may fail."
    fi

    # Check MultiNetworkPolicy support
    MULTI_NET_ENABLED=$(oc get network.operator.openshift.io cluster -o jsonpath='{.spec.useMultiNetworkPolicy}' 2>/dev/null || echo "false")
    if [ "$MULTI_NET_ENABLED" != "true" ]; then
        echo "❌ ERROR: MultiNetworkPolicy is not enabled on this cluster."
        echo ""
        echo "To enable, run:"
        echo "  oc patch network.operator.openshift.io cluster --type=merge \\"
        echo "    -p '{\"spec\":{\"useMultiNetworkPolicy\":true}}'"
        echo ""
        echo "Then wait for network operator to finish updating:"
        echo "  oc wait --for=condition=Progressing=False --timeout=300s co/network"
        exit 1
    fi

    echo "✓ Prerequisites met"
    echo ""
}

# Function to create namespace
create_namespace() {
    echo "Creating namespace '$NAMESPACE'..."

    if oc get namespace "$NAMESPACE" &> /dev/null; then
        echo "✓ Namespace '$NAMESPACE' already exists"
    else
        oc create namespace "$NAMESPACE"
        echo "✓ Namespace '$NAMESPACE' created"
    fi
    echo ""
}

# Function to get worker node names
get_worker_nodes() {
    echo "Detecting worker nodes..."
    WORKER_NODES=$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[*].metadata.name}')

    if [ -z "$WORKER_NODES" ]; then
        echo "❌ ERROR: No worker nodes found in cluster"
        exit 1
    fi

    echo "Found worker nodes:"
    for node in $WORKER_NODES; do
        echo "  - $node"
    done
    echo ""
}

# Function to configure iptables on worker nodes
configure_worker_nodes() {
    echo "Configuring iptables on worker nodes..."
    echo "This allows traffic between secondary networks (10.244.0.0/16)"
    echo ""

    for node in $WORKER_NODES; do
        echo "Configuring $node..."

        # Add iptables rule to allow forwarding between secondary networks
        oc debug node/$node -- chroot /host bash -c \
            "iptables -I FORWARD 1 -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT" \
            2>&1 | grep -v "Starting pod" | grep -v "Removing debug pod" | grep -v "To use host binaries" || true

        echo "  ✓ iptables configured on $node"
    done

    echo ""
    echo "⚠️  NOTE: iptables rules are temporary and will be lost on node reboot"
    echo "    To make permanent, create a MachineConfig (see documentation)"
    echo ""
}

# Function to apply NetworkAttachmentDefinitions
apply_nads() {
    echo "Applying NetworkAttachmentDefinitions..."

    # Check if NAD file exists
    NAD_FILE="$(dirname "$0")/nad-aws-bridge-test.yaml"

    if [ ! -f "$NAD_FILE" ]; then
        echo "❌ ERROR: NAD file not found: $NAD_FILE"
        echo "Please ensure you're running this script from the nsx-multinetwork-demo directory"
        exit 1
    fi

    oc apply -f "$NAD_FILE"
    echo "✓ NetworkAttachmentDefinitions applied"
    echo ""

    # Show created NADs
    echo "Created networks:"
    oc get network-attachment-definitions -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,NETWORK:.spec.config | grep -v "config"
    echo ""
}

# Function to deploy test pods
deploy_test_pods() {
    echo "Deploying test pods..."

    # Check if test pods file exists
    PODS_FILE="$(dirname "$0")/test-pods-demo.yaml"

    if [ ! -f "$PODS_FILE" ]; then
        echo "❌ ERROR: Test pods file not found: $PODS_FILE"
        exit 1
    fi

    # Select first worker node for all pods (required for bridge CNI cross-pod connectivity)
    SELECTED_NODE=$(echo $WORKER_NODES | awk '{print $1}')
    echo "Selected node for all pods: $SELECTED_NODE"
    echo "  (Bridge CNI networks require pods on same node for connectivity)"
    echo ""

    # Delete existing pods if any
    oc delete pods -n "$NAMESPACE" --all --wait=false &> /dev/null || true
    sleep 3

    # Apply test pods with node name substitution
    sed "s/WORKER_NODE_PLACEHOLDER/$SELECTED_NODE/g" "$PODS_FILE" | oc apply -f -

    echo "Waiting for pods to be ready (timeout: 90s)..."
    if oc wait --for=condition=ready pod/web-server pod/app-server pod/db-server \
        -n "$NAMESPACE" --timeout=90s &> /dev/null; then
        echo "✓ All test pods are ready"
    else
        echo "⚠️  WARNING: Some pods may not be ready yet. Check with: oc get pods -n $NAMESPACE"
    fi
    echo ""
}

# Function to verify MultiNetworkPolicy
verify_policies() {
    echo "Verifying MultiNetworkPolicy resources..."

    POLICY_COUNT=$(oc get multi-networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)

    if [ "$POLICY_COUNT" -eq 0 ]; then
        echo "⚠️  WARNING: No MultiNetworkPolicy resources found"
        echo "    These should be deployed separately using ops-translate"
    else
        echo "✓ Found $POLICY_COUNT MultiNetworkPolicy resources"
        oc get multi-networkpolicy -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,NETWORK:.metadata.annotations.'k8s\.v1\.cni\.cncf\.io/policy-for'
    fi
    echo ""
}

# Function to test connectivity
test_connectivity() {
    echo "Testing pod-to-pod connectivity on secondary networks..."
    echo ""

    # Get pod IPs
    WEB_IP=$(oc exec -n "$NAMESPACE" web-server -- ip -4 addr show net1 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1)
    APP_IP=$(oc exec -n "$NAMESPACE" app-server -- ip -4 addr show net1 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1)
    DB_IP=$(oc exec -n "$NAMESPACE" db-server -- ip -4 addr show net1 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1)

    if [ -z "$WEB_IP" ] || [ -z "$APP_IP" ] || [ -z "$DB_IP" ]; then
        echo "❌ ERROR: Could not retrieve pod IPs. Pods may not be ready."
        return 1
    fi

    echo "Pod IPs on secondary networks:"
    echo "  web-server: $WEB_IP (10.244.100.0/24)"
    echo "  app-server: $APP_IP (10.244.150.0/24)"
    echo "  db-server:  $DB_IP (10.244.200.0/24)"
    echo ""

    # Test web → app
    echo -n "Testing web → app ($WEB_IP → $APP_IP)... "
    if oc exec -n "$NAMESPACE" web-server -- ping -c 2 -W 2 "$APP_IP" &> /dev/null; then
        echo "✓ PASS"
    else
        echo "❌ FAIL"
        return 1
    fi

    # Test app → db
    echo -n "Testing app → db ($APP_IP → $DB_IP)... "
    if oc exec -n "$NAMESPACE" app-server -- ping -c 2 -W 2 "$DB_IP" &> /dev/null; then
        echo "✓ PASS"
    else
        echo "❌ FAIL"
        return 1
    fi

    # Test web → db
    echo -n "Testing web → db ($WEB_IP → $DB_IP)... "
    if oc exec -n "$NAMESPACE" web-server -- ping -c 2 -W 2 "$DB_IP" &> /dev/null; then
        echo "✓ PASS"
    else
        echo "❌ FAIL"
        return 1
    fi

    echo ""
    echo "✓ All connectivity tests passed!"
    echo ""
}

# Function to print summary
print_summary() {
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Resources created in namespace '$NAMESPACE':"
    echo ""
    echo "NetworkAttachmentDefinitions:"
    oc get network-attachment-definitions -n "$NAMESPACE" -o name | sed 's/^/  - /'
    echo ""
    echo "Pods:"
    oc get pods -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,IP-NET1:.metadata.annotations.'k8s\.v1\.cni\.cncf\.io/network-status' | head -4
    echo ""
    echo "MultiNetworkPolicies:"
    if [ "$(oc get multi-networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)" -gt 0 ]; then
        oc get multi-networkpolicy -n "$NAMESPACE" -o name | sed 's/^/  - /'
    else
        echo "  (none - deploy using ops-translate)"
    fi
    echo ""
    echo "Quick Test Commands:"
    echo "  # View all resources"
    echo "  oc get network-attachment-definitions,pods,multi-networkpolicy -n $NAMESPACE"
    echo ""
    echo "  # Test connectivity"
    echo "  oc exec -n $NAMESPACE web-server -- ping -c 3 10.244.150.11"
    echo "  oc exec -n $NAMESPACE app-server -- ping -c 3 10.244.200.11"
    echo ""
    echo "  # View pod network details"
    echo "  oc exec -n $NAMESPACE web-server -- ip addr show net1"
    echo ""
    echo "For more information, see: AWS_TEST_ENVIRONMENT_SUMMARY.md"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    create_namespace
    get_worker_nodes
    configure_worker_nodes
    apply_nads
    deploy_test_pods
    verify_policies

    # Test connectivity
    if test_connectivity; then
        print_summary
        exit 0
    else
        echo "❌ Connectivity tests failed. Please check the configuration."
        echo "   Run: oc get pods -n $NAMESPACE"
        echo "   And check pod logs for errors."
        exit 1
    fi
}

# Run main function
main "$@"
