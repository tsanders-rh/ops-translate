"""Tests for Ansible distributed locking task generation."""

import pytest

from ops_translate.generate.ansible_locking import (
    LockingTaskGenerator,
    generate_locking_setup_doc,
)
from ops_translate.summarize.vrealize_locking import LockPattern


@pytest.fixture
def simple_lock_pattern():
    """Create a simple lock pattern for testing."""
    return LockPattern(
        resource="ip_10.0.1.50",
        timeout=300,
        lock_position=0,
        unlock_position=100,
        has_try_finally=False,
    )


@pytest.fixture
def work_tasks():
    """Create sample work tasks."""
    return [
        {
            "name": "Assign IP to VM",
            "ansible.builtin.debug": {"msg": "Assigning IP"},
        },
        {
            "name": "Register DNS",
            "ansible.builtin.debug": {"msg": "Registering DNS"},
        },
    ]


def test_redis_backend_initialization():
    """Test Redis backend initialization."""
    generator = LockingTaskGenerator(backend="redis")
    assert generator.backend == "redis"


def test_consul_backend_initialization():
    """Test Consul backend initialization."""
    generator = LockingTaskGenerator(backend="consul")
    assert generator.backend == "consul"


def test_file_backend_initialization():
    """Test file backend initialization."""
    generator = LockingTaskGenerator(backend="file")
    assert generator.backend == "file"


def test_invalid_backend_raises_error():
    """Test that invalid backend raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported locking backend"):
        LockingTaskGenerator(backend="invalid")


def test_generate_redis_lock(simple_lock_pattern):
    """Test Redis lock generation."""
    generator = LockingTaskGenerator(backend="redis")
    lock_task = generator._generate_redis_lock(simple_lock_pattern)

    assert lock_task["name"] == "Acquire lock: ip_10.0.1.50"
    assert "community.general.redis_data" in lock_task
    assert lock_task["community.general.redis_data"]["key"] == "lock:ip_10.0.1.50"
    assert lock_task["community.general.redis_data"]["nx"] is True
    assert lock_task["community.general.redis_data"]["expiration"] == 300000  # 300s * 1000ms
    assert lock_task["register"] == "ip_10_0_1_50_lock"
    assert lock_task["retries"] == 60  # 300 // 5
    assert lock_task["delay"] == 5


def test_generate_redis_unlock(simple_lock_pattern):
    """Test Redis unlock generation."""
    generator = LockingTaskGenerator(backend="redis")
    unlock_task = generator._generate_redis_unlock(simple_lock_pattern)

    assert unlock_task["name"] == "Release lock: ip_10.0.1.50"
    assert "community.general.redis_data" in unlock_task
    assert unlock_task["community.general.redis_data"]["key"] == "lock:ip_10.0.1.50"
    assert unlock_task["community.general.redis_data"]["state"] == "absent"
    assert unlock_task["when"] == "ip_10_0_1_50_lock is succeeded"


def test_generate_consul_lock(simple_lock_pattern):
    """Test Consul lock generation."""
    generator = LockingTaskGenerator(backend="consul")
    lock_tasks = generator._generate_consul_lock(simple_lock_pattern)

    assert len(lock_tasks) == 2

    # Check session creation task
    session_task = lock_tasks[0]
    assert session_task["name"] == "Create Consul session for ip_10.0.1.50"
    assert "community.general.consul_session" in session_task
    assert session_task["community.general.consul_session"]["state"] == "present"
    assert session_task["community.general.consul_session"]["ttl"] == 300
    assert session_task["register"] == "ip_10_0_1_50_session"

    # Check lock acquisition task
    lock_task = lock_tasks[1]
    assert lock_task["name"] == "Acquire Consul lock: ip_10.0.1.50"
    assert "community.general.consul_kv" in lock_task
    assert lock_task["community.general.consul_kv"]["key"] == "locks/ip_10.0.1.50"
    assert lock_task["register"] == "ip_10_0_1_50_lock"
    assert lock_task["retries"] == 60


def test_generate_consul_unlock(simple_lock_pattern):
    """Test Consul unlock generation."""
    generator = LockingTaskGenerator(backend="consul")
    unlock_task = generator._generate_consul_unlock(simple_lock_pattern)

    assert unlock_task["name"] == "Release Consul lock: ip_10.0.1.50"
    assert "community.general.consul_session" in unlock_task
    assert unlock_task["community.general.consul_session"]["state"] == "absent"
    assert unlock_task["when"] == "ip_10_0_1_50_session is defined"


def test_generate_file_lock(simple_lock_pattern):
    """Test file-based lock generation."""
    generator = LockingTaskGenerator(backend="file")
    lock_task = generator._generate_file_lock(simple_lock_pattern)

    assert "WARNING: not distributed" in lock_task["name"]
    assert "ansible.builtin.file" in lock_task
    assert lock_task["ansible.builtin.file"]["path"] == "/var/lock/ansible/ip_10_0_1_50.lock"
    assert lock_task["ansible.builtin.file"]["state"] == "touch"
    assert lock_task["register"] == "ip_10_0_1_50_lock"
    assert lock_task["failed_when"] is False


def test_generate_file_unlock(simple_lock_pattern):
    """Test file-based unlock generation."""
    generator = LockingTaskGenerator(backend="file")
    unlock_task = generator._generate_file_unlock(simple_lock_pattern)

    assert unlock_task["name"] == "Release file lock: ip_10.0.1.50"
    assert "ansible.builtin.file" in unlock_task
    assert unlock_task["ansible.builtin.file"]["path"] == "/var/lock/ansible/ip_10_0_1_50.lock"
    assert unlock_task["ansible.builtin.file"]["state"] == "absent"


def test_generate_lock_tasks_with_redis(simple_lock_pattern, work_tasks):
    """Test complete lock task generation with Redis backend."""
    generator = LockingTaskGenerator(backend="redis")
    block_task = generator.generate_lock_tasks(simple_lock_pattern, work_tasks)

    assert block_task["name"] == "Execute with lock: ip_10.0.1.50"
    assert "block" in block_task
    assert "always" in block_task

    # Block should contain lock acquisition + work tasks
    block = block_task["block"]
    assert len(block) == 3  # 1 lock + 2 work tasks
    assert "Acquire lock" in block[0]["name"]
    assert block[1]["name"] == "Assign IP to VM"
    assert block[2]["name"] == "Register DNS"

    # Always should contain lock release
    always = block_task["always"]
    assert len(always) == 1
    assert "Release lock" in always[0]["name"]


def test_generate_lock_tasks_with_consul(simple_lock_pattern, work_tasks):
    """Test complete lock task generation with Consul backend."""
    generator = LockingTaskGenerator(backend="consul")
    block_task = generator.generate_lock_tasks(simple_lock_pattern, work_tasks)

    assert "block" in block_task
    assert "always" in block_task

    # Block should contain session + lock + work tasks
    block = block_task["block"]
    assert len(block) == 4  # 1 session + 1 lock + 2 work tasks
    assert "Create Consul session" in block[0]["name"]
    assert "Acquire Consul lock" in block[1]["name"]

    # Always should contain session destroy
    always = block_task["always"]
    assert len(always) == 1
    assert "Release Consul lock" in always[0]["name"]


def test_lock_timeout_calculation():
    """Test that lock timeout affects retry count."""
    short_pattern = LockPattern(
        resource="short_lock", timeout=60, lock_position=0, unlock_position=100
    )
    long_pattern = LockPattern(
        resource="long_lock", timeout=600, lock_position=0, unlock_position=100
    )

    generator = LockingTaskGenerator(backend="redis")

    short_lock = generator._generate_redis_lock(short_pattern)
    long_lock = generator._generate_redis_lock(long_pattern)

    # Short timeout should have fewer retries
    assert short_lock["retries"] == 12  # max(60 // 5, 12) = 12
    assert long_lock["retries"] == 120  # 600 // 5 = 120


def test_generate_locking_setup_doc_redis():
    """Test Redis setup documentation generation."""
    doc = generate_locking_setup_doc("redis", "/output/LOCKING_SETUP.md")

    assert "Redis Setup (Recommended)" in doc
    assert "dnf install redis" in doc
    assert "redis-cli ping" in doc
    assert "redis_host" in doc
    assert "vault_redis_password" in doc
    assert "ansible-galaxy collection install community.general" in doc


def test_generate_locking_setup_doc_consul():
    """Test Consul setup documentation generation."""
    doc = generate_locking_setup_doc("consul", "/output/LOCKING_SETUP.md")

    assert "Consul Setup (Alternative)" in doc
    assert "consul agent" in doc
    assert "consul_host" in doc
    assert "vault_consul_token" in doc
    assert "ansible-galaxy collection install community.general" in doc


def test_generate_locking_setup_doc_file():
    """Test file-based setup documentation generation."""
    doc = generate_locking_setup_doc("file", "/output/LOCKING_SETUP.md")

    assert "File-Based Locking (Development Only)" in doc
    assert "WARNING" in doc
    assert "Not distributed" in doc
    assert "/var/lock/ansible" in doc
    assert "For production, use Redis or Consul" in doc


def test_redis_lock_key_format(simple_lock_pattern):
    """Test that Redis lock keys follow correct format."""
    generator = LockingTaskGenerator(backend="redis")
    lock_task = generator._generate_redis_lock(simple_lock_pattern)

    key = lock_task["community.general.redis_data"]["key"]
    assert key.startswith("lock:")
    assert key == "lock:ip_10.0.1.50"


def test_consul_lock_key_format(simple_lock_pattern):
    """Test that Consul lock keys follow correct format."""
    generator = LockingTaskGenerator(backend="consul")
    lock_tasks = generator._generate_consul_lock(simple_lock_pattern)

    key = lock_tasks[1]["community.general.consul_kv"]["key"]
    assert key.startswith("locks/")
    assert key == "locks/ip_10.0.1.50"


def test_lock_variable_naming():
    """Test that lock variables are properly sanitized."""
    pattern = LockPattern(
        resource="host-name.domain.com",
        timeout=300,
        lock_position=0,
        unlock_position=100,
    )

    generator = LockingTaskGenerator(backend="redis")
    lock_task = generator._generate_redis_lock(pattern)

    # Variable name should be sanitized
    assert lock_task["register"] == "host_name_domain_com_lock"
    assert lock_task["until"] == "host_name_domain_com_lock is not failed"


def test_empty_work_tasks(simple_lock_pattern):
    """Test lock generation with no work tasks."""
    generator = LockingTaskGenerator(backend="redis")
    block_task = generator.generate_lock_tasks(simple_lock_pattern, [])

    # Should still have lock acquisition and release
    assert "block" in block_task
    assert "always" in block_task
    assert len(block_task["block"]) == 1  # Just the lock acquisition
    assert len(block_task["always"]) == 1  # Just the lock release


def test_lock_expiration_milliseconds(simple_lock_pattern):
    """Test that Redis expiration is correctly converted to milliseconds."""
    generator = LockingTaskGenerator(backend="redis")
    lock_task = generator._generate_redis_lock(simple_lock_pattern)

    # 300 seconds should be 300000 milliseconds
    expiration = lock_task["community.general.redis_data"]["expiration"]
    assert expiration == 300000


def test_minimum_retries():
    """Test that retries have a minimum value."""
    short_pattern = LockPattern(
        resource="very_short", timeout=10, lock_position=0, unlock_position=100
    )

    generator = LockingTaskGenerator(backend="redis")
    lock_task = generator._generate_redis_lock(short_pattern)

    # Even with timeout=10, should have at least 12 retries
    assert lock_task["retries"] == 12  # max(10 // 5, 12) = 12
