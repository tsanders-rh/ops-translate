# AWS Environment Variables for Multi-ENI Setup
export VPC_ID="vpc-09b9e6eda6b4a762f"
export WEB_SUBNET_1A="subnet-040e4d7f171c56ab2"
export WEB_SUBNET_1B="subnet-00d124c0f0dc480b0"
export APP_SUBNET_1A="subnet-0d49c90df67220a27"
export APP_SUBNET_1B="subnet-039499bd851f5afcf"
export DB_SUBNET_1A="subnet-0d1feb3b46749c2c6"
export DB_SUBNET_1B="subnet-05f253605bb4f38f0"
export WORKER_1A="i-03e6c4ac733d51f1a"
export WORKER_1B="i-04ac50947e72a0e26"
export SG_ID="sg-04498ed97fffb1375"
export WEB_ENI_1A="Creating ENI: nsx-demo-web-worker1...
  Subnet: subnet-040e4d7f171c56ab2
  Instance: i-03e6c4ac733d51f1a
  Device Index: 1
  ✓ Created ENI: eni-01b8a66b38e816f07
  Attaching to instance...
  ✓ Attached: eni-attach-084f4f10592b97d2b
  ✓ Configured ENI

eni-01b8a66b38e816f07"
export APP_ENI_1A="Creating ENI: nsx-demo-app-worker1...
  Subnet: subnet-0d49c90df67220a27
  Instance: i-03e6c4ac733d51f1a
  Device Index: 2
  ✓ Created ENI: eni-0c267c7a529adfdf0
  Attaching to instance...
  ✓ Attached: eni-attach-0db415826e6b43703
  ✓ Configured ENI

eni-0c267c7a529adfdf0"
export DB_ENI_1A="Creating ENI: nsx-demo-db-worker1...
  Subnet: subnet-0d1feb3b46749c2c6
  Instance: i-03e6c4ac733d51f1a
  Device Index: 3
  ✓ Created ENI: eni-0c3c9afeae9c320b5
  Attaching to instance...
  ✓ Attached: eni-attach-0f2cb7e282a3f2989
  ✓ Configured ENI

eni-0c3c9afeae9c320b5"
export WEB_ENI_1B="Creating ENI: nsx-demo-web-worker2...
  Subnet: subnet-00d124c0f0dc480b0
  Instance: i-04ac50947e72a0e26
  Device Index: 1
  ✓ Created ENI: eni-00d45bc7c5559baff
  Attaching to instance...
  ✓ Attached: eni-attach-01a0284ea92300f80
  ✓ Configured ENI

eni-00d45bc7c5559baff"
export APP_ENI_1B="Creating ENI: nsx-demo-app-worker2...
  Subnet: subnet-039499bd851f5afcf
  Instance: i-04ac50947e72a0e26
  Device Index: 2
  ✓ Created ENI: eni-0dd1e8f821394ac25
  Attaching to instance...
  ✓ Attached: eni-attach-017c560a9c08f0a89
  ✓ Configured ENI

eni-0dd1e8f821394ac25"
export DB_ENI_1B="Creating ENI: nsx-demo-db-worker2...
  Subnet: subnet-05f253605bb4f38f0
  Instance: i-04ac50947e72a0e26
  Device Index: 3
  ✓ Created ENI: eni-08f48614493f27402
  Attaching to instance...
  ✓ Attached: eni-attach-0eed8288daa4aeed8
  ✓ Configured ENI

eni-08f48614493f27402"
