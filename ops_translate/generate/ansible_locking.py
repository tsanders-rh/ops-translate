"""
Ansible distributed locking task generation.

Generates Ansible tasks for acquiring and releasing distributed locks
to prevent race conditions in concurrent workflows.
"""

from typing import Any

from ops_translate.summarize.vrealize_locking import LockPattern, sanitize_resource_name


class LockingTaskGenerator:
    """
    Generate Ansible locking tasks for different backends.

    Supports:
    - Redis (recommended for production)
    - Consul (alternative distributed system)
    - File-based (simple, not suitable for distributed systems)
    """

    def __init__(self, backend: str = "redis"):
        """
        Initialize locking task generator.

        Args:
            backend: Locking backend (redis, consul, or file)
        """
        if backend not in ["redis", "consul", "file"]:
            raise ValueError(f"Unsupported locking backend: {backend}")

        self.backend = backend

    def generate_lock_tasks(
        self, pattern: LockPattern, work_tasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Generate complete locking structure with acquire/work/release.

        Returns a block/always task structure:
        - block: [acquire_lock, ...work_tasks...]
        - always: [release_lock]

        Args:
            pattern: Detected lock pattern from vRO code
            work_tasks: Tasks to execute while holding the lock

        Returns:
            Ansible block task with locking structure
        """
        var_name = sanitize_resource_name(pattern.resource)

        # Generate lock acquisition tasks
        acquire_tasks = self._generate_lock_acquisition(pattern)

        # Generate lock release tasks
        release_tasks = self._generate_lock_release(pattern)

        # Build block/always structure
        block_tasks = []

        # Add lock acquisition
        if isinstance(acquire_tasks, list):
            block_tasks.extend(acquire_tasks)
        else:
            block_tasks.append(acquire_tasks)

        # Add work tasks
        block_tasks.extend(work_tasks)

        # Build complete structure
        task = {
            "name": f"Execute with lock: {pattern.resource}",
            "block": block_tasks,
            "always": release_tasks if isinstance(release_tasks, list) else [release_tasks],
        }

        return task

    def _generate_lock_acquisition(
        self, pattern: LockPattern
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Generate lock acquisition task(s) based on backend."""
        if self.backend == "redis":
            return self._generate_redis_lock(pattern)
        elif self.backend == "consul":
            return self._generate_consul_lock(pattern)
        elif self.backend == "file":
            return self._generate_file_lock(pattern)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    def _generate_lock_release(self, pattern: LockPattern) -> list[dict[str, Any]] | dict[str, Any]:
        """Generate lock release task(s) based on backend."""
        if self.backend == "redis":
            return self._generate_redis_unlock(pattern)
        elif self.backend == "consul":
            return self._generate_consul_unlock(pattern)
        elif self.backend == "file":
            return self._generate_file_unlock(pattern)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    def _generate_redis_lock(self, pattern: LockPattern) -> dict[str, Any]:
        """
        Generate Redis-based lock acquisition task.

        Uses community.general.redis_data with NX (set if not exists) flag
        and automatic expiration to prevent deadlocks.
        """
        var_name = sanitize_resource_name(pattern.resource)
        lock_key = f"lock:{pattern.resource}"

        return {
            "name": f"Acquire lock: {pattern.resource}",
            "community.general.redis_data": {
                "key": lock_key,
                "value": "{{ ansible_date_time.epoch }}",
                "expiration": pattern.timeout * 1000,  # Convert to milliseconds
                "nx": True,  # Only set if doesn't exist
            },
            "register": f"{var_name}_lock",
            "until": f"{var_name}_lock is not failed",
            "retries": max(pattern.timeout // 5, 12),  # Retry for up to timeout duration
            "delay": 5,
        }

    def _generate_redis_unlock(self, pattern: LockPattern) -> dict[str, Any]:
        """Generate Redis-based lock release task."""
        var_name = sanitize_resource_name(pattern.resource)
        lock_key = f"lock:{pattern.resource}"

        return {
            "name": f"Release lock: {pattern.resource}",
            "community.general.redis_data": {
                "key": lock_key,
                "state": "absent",
            },
            "when": f"{var_name}_lock is succeeded",
        }

    def _generate_consul_lock(self, pattern: LockPattern) -> list[dict[str, Any]]:
        """
        Generate Consul-based lock acquisition tasks.

        Consul locking requires creating a session first, then acquiring
        the lock using KV store with session association.
        """
        var_name = sanitize_resource_name(pattern.resource)
        session_var = f"{var_name}_session"
        lock_var = f"{var_name}_lock"

        return [
            {
                "name": f"Create Consul session for {pattern.resource}",
                "community.general.consul_session": {
                    "state": "present",
                    "name": f"lock_{pattern.resource}",
                    "ttl": pattern.timeout,
                },
                "register": session_var,
            },
            {
                "name": f"Acquire Consul lock: {pattern.resource}",
                "community.general.consul_kv": {
                    "key": f"locks/{pattern.resource}",
                    "value": "{{ ansible_date_time.epoch }}",
                    "session": f"{{{{ {session_var}.session_id }}}}",
                },
                "register": lock_var,
                "until": f"{lock_var} is not failed",
                "retries": max(pattern.timeout // 5, 12),
                "delay": 5,
            },
        ]

    def _generate_consul_unlock(self, pattern: LockPattern) -> dict[str, Any]:
        """
        Generate Consul-based lock release task.

        Destroying the session automatically releases the lock.
        """
        var_name = sanitize_resource_name(pattern.resource)
        session_var = f"{var_name}_session"

        return {
            "name": f"Release Consul lock: {pattern.resource}",
            "community.general.consul_session": {
                "state": "absent",
                "session_id": f"{{{{ {session_var}.session_id }}}}",
            },
            "when": f"{session_var} is defined",
        }

    def _generate_file_lock(self, pattern: LockPattern) -> dict[str, Any]:
        """
        Generate file-based lock acquisition task.

        WARNING: File-based locks are NOT suitable for distributed systems.
        Only use for single-node testing or development.
        """
        var_name = sanitize_resource_name(pattern.resource)
        lock_file = f"/var/lock/ansible/{var_name}.lock"

        return {
            "name": f"Acquire file lock: {pattern.resource} (WARNING: not distributed)",
            "ansible.builtin.file": {
                "path": lock_file,
                "state": "touch",
                "modification_time": "preserve",
                "access_time": "preserve",
            },
            "register": f"{var_name}_lock",
            "until": f"{var_name}_lock is not failed",
            "retries": max(pattern.timeout // 5, 12),
            "delay": 5,
            "failed_when": False,  # Don't fail if file exists
        }

    def _generate_file_unlock(self, pattern: LockPattern) -> dict[str, Any]:
        """Generate file-based lock release task."""
        var_name = sanitize_resource_name(pattern.resource)
        lock_file = f"/var/lock/ansible/{var_name}.lock"

        return {
            "name": f"Release file lock: {pattern.resource}",
            "ansible.builtin.file": {
                "path": lock_file,
                "state": "absent",
            },
            "when": f"{var_name}_lock is succeeded",
        }


def generate_locking_setup_doc(backend: str, output_path: str) -> str:
    """
    Generate LOCKING_SETUP.md documentation for the specified backend.

    Args:
        backend: Locking backend (redis, consul, or file)
        output_path: Path where the documentation will be saved

    Returns:
        Markdown documentation content
    """
    redis_setup = """## Redis Setup (Recommended)

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
"""

    consul_setup = """## Consul Setup (Alternative)

Consul provides distributed locking with session-based TTLs.

### Installation

```bash
# RHEL/CentOS
sudo dnf install consul

# Ubuntu
wget https://releases.hashicorp.com/consul/1.16.0/consul_1.16.0_linux_amd64.zip
unzip consul_1.16.0_linux_amd64.zip
sudo mv consul /usr/local/bin/
```

### Configuration

```bash
# Start Consul agent (development mode)
consul agent -dev

# Or production mode with configuration
consul agent -config-dir=/etc/consul.d
```

### Ansible Configuration

```yaml
# group_vars/all/consul.yml
consul_host: "consul.example.com"
consul_port: 8500
consul_token: "{{ vault_consul_token }}"
```
"""

    file_setup = """## File-Based Locking (Development Only)

**WARNING**: File-based locks are NOT suitable for distributed systems.
Only use for single-node testing or development.

### Setup

```bash
# Create lock directory
sudo mkdir -p /var/lock/ansible
sudo chown $(whoami):$(whoami) /var/lock/ansible
sudo chmod 755 /var/lock/ansible
```

### Limitations

- **Not distributed**: Only works on a single machine
- **No automatic cleanup**: Stale locks must be manually removed
- **Race conditions**: Not atomic across network filesystems (NFS, CIFS)

For production, use Redis or Consul instead.
"""

    backend_sections = {
        "redis": redis_setup,
        "consul": consul_setup,
        "file": file_setup,
    }

    all_setups = f"""# Distributed Locking Setup

Generated playbooks use distributed locking to prevent race conditions
when workflows run concurrently.

**Current backend**: {backend}

{backend_sections.get(backend, "Unknown backend")}

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
{"vault_redis_password: changeme123" if backend == "redis" else "vault_consul_token: changeme123"}
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
redis_password: "{{ vault_redis_password }}"
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
consul_token: "{{ vault_consul_token }}"
```

---

For more information, see:
- Redis: https://redis.io/docs/manual/patterns/distributed-locks/
- Consul: https://www.consul.io/docs/dynamic-app-config/sessions
- Ansible collections: https://docs.ansible.com/ansible/latest/collections/community/general/
"""

    return all_setups
