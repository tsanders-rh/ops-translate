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
