# Distributed Locking Setup

Generated playbooks use distributed locking to prevent race conditions
when workflows run concurrently.

**Current backend**: redis

## Redis Setup (Recommended)

Redis provides distributed locking with automatic expiration to prevent deadlocks.

### Installation

```bash
# RHEL/CentOS
sudo dnf install redis

# Ubuntu
sudo apt-get install redis-server
```

### Configuration

```bash
# Enable and start Redis
sudo systemctl enable --now redis

# Test connectivity
redis-cli ping
# Expected output: PONG
```

### High Availability (Optional)

For production environments, consider Redis Sentinel or Redis Cluster:

```bash
# Redis Sentinel for automatic failover
sudo dnf install redis-sentinel
sudo systemctl enable --now redis-sentinel
```

### Ansible Configuration

```yaml
# group_vars/all/redis.yml
redis_host: "redis.example.com"
redis_port: 6379
redis_password: "{{ vault_redis_password }}"
```


---

## Required Ansible Collections

```bash
# Install community.general collection
ansible-galaxy collection install community.general
```

## Vault Variables

Store credentials in Ansible Vault:

```bash
# Create vault file
ansible-vault create group_vars/all/vault.yml
```

```yaml
# vault.yml content
vault_redis_password: changeme123
```

## Testing Locks

### Test Redis Lock

```bash
# Set a test lock
redis-cli SET lock:test_resource "$(date +%s)" EX 300 NX

# Check if lock exists
redis-cli GET lock:test_resource

# Remove test lock
redis-cli DEL lock:test_resource
```

### Test Consul Lock

```bash
# Create session
consul session create -ttl=300s

# Acquire lock
consul kv put -acquire locks/test_resource "$(date +%s)"

# Check lock
consul kv get locks/test_resource

# Release lock
consul session destroy <session-id>
```

## Troubleshooting

### Stale Locks

If a playbook crashes, locks might not be released:

**Redis**:
```bash
# List all locks
redis-cli KEYS "lock:*"

# Remove stale lock
redis-cli DEL lock:ip_10.0.1.50
```

**Consul**:
```bash
# List locks
consul kv get -recurse locks/

# Remove stale lock
consul kv delete locks/ip_10.0.1.50
```

### Lock Timeout Errors

If tasks consistently fail to acquire locks:

1. Increase timeout in vRO workflow (regenerate playbooks)
2. Reduce concurrent playbook executions
3. Check for deadlocks (task A waits for B, B waits for A)

## Alternative Backends

To regenerate playbooks with a different locking backend:

```bash
# Use Redis (default)
ops-translate generate --profile prod --locking-backend redis

# Use Consul
ops-translate generate --profile prod --locking-backend consul

# Disable locking (not recommended for production)
ops-translate generate --profile prod --no-locking
```

## Migration Strategy

When migrating from vRO to Ansible:

1. **Start with Redis** (easiest to set up, widely supported)
2. **Test with file locks** in development (single-node only)
3. **Upgrade to Consul** if you need service discovery + locking
4. **Never disable locking** in production (race conditions!)

## Performance Considerations

- **Lock granularity**: Fine-grained locks (per IP) reduce contention vs coarse locks (all IPs)
- **Timeout tuning**: Longer timeouts prevent failures but increase wait time
- **Retry delay**: 5 seconds is a good default, adjust based on workload
- **Expiration**: Prevents deadlocks if playbook crashes

## Security

### Redis Authentication

```yaml
# Enable authentication in redis.conf
requirepass yourpassword

# Use in playbooks
redis_password: "{ vault_redis_password }"
```

### Consul ACLs

```bash
# Enable ACLs in Consul
consul acl bootstrap

# Create token for Ansible
consul acl token create -description "Ansible locking" -policy-name "ansible-locks"
```

```yaml
# Use in playbooks
consul_token: "{ vault_consul_token }"
```

---

For more information, see:
- Redis: https://redis.io/docs/manual/patterns/distributed-locks/
- Consul: https://www.consul.io/docs/dynamic-app-config/sessions
- Ansible collections: https://docs.ansible.com/ansible/latest/collections/community/general/
