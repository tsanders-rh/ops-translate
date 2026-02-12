"""Tests for vRealize LockingSystem pattern detection."""

from ops_translate.summarize.vrealize_locking import (
    LockPattern,
    detect_locking_patterns,
    sanitize_resource_name,
)


def test_detect_simple_lock_pattern():
    """Test detection of simple lock/unlock pattern."""
    script = """
    LockingSystem.lockGlobalStringRead("ip_10.0.1.50", 300);
    assignIP(vm, "10.0.1.50");
    LockingSystem.unlockGlobalStringRead("ip_10.0.1.50");
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "ip_10.0.1.50"
    assert patterns[0].timeout == 300
    assert patterns[0].unlock_position is not None


def test_detect_lock_without_timeout():
    """Test detection of lock without explicit timeout (uses default)."""
    script = """
    LockingSystem.lockGlobalStringRead("hostname_web-01");
    setHostname(vm, "web-01");
    LockingSystem.unlockGlobalStringRead("hostname_web-01");
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "hostname_web-01"
    assert patterns[0].timeout == 300  # Default timeout
    assert patterns[0].unlock_position is not None


def test_detect_lock_with_try_finally():
    """Test detection of try/finally pattern around lock."""
    script = """
    LockingSystem.lockGlobalStringRead("ip_10.0.1.50", 300);

    try {
        assignIP(vm, "10.0.1.50");
        registerDNS(vm);
    } finally {
        LockingSystem.unlockGlobalStringRead("ip_10.0.1.50");
    }
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "ip_10.0.1.50"
    assert patterns[0].has_try_finally is True


def test_detect_multiple_locks():
    """Test detection of multiple lock patterns."""
    script = """
    LockingSystem.lockGlobalStringRead("ip_10.0.1.50", 300);
    assignIP(vm, "10.0.1.50");
    LockingSystem.unlockGlobalStringRead("ip_10.0.1.50");

    LockingSystem.lockGlobalStringRead("hostname_web-01", 180);
    setHostname(vm, "web-01");
    LockingSystem.unlockGlobalStringRead("hostname_web-01");
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 2
    assert patterns[0].resource == "ip_10.0.1.50"
    assert patterns[0].timeout == 300
    assert patterns[1].resource == "hostname_web-01"
    assert patterns[1].timeout == 180


def test_detect_lock_without_unlock():
    """Test detection of lock without corresponding unlock."""
    script = """
    LockingSystem.lockGlobalStringRead("ip_10.0.1.50", 300);
    assignIP(vm, "10.0.1.50");
    // Missing unlock - bad practice!
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "ip_10.0.1.50"
    assert patterns[0].unlock_position is None  # No unlock found


def test_no_locks_detected():
    """Test script without any locking."""
    script = """
    assignIP(vm, "10.0.1.50");
    registerDNS(vm);
    System.log("IP assigned");
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 0


def test_lock_with_single_quotes():
    """Test lock detection with single quotes."""
    script = """
    LockingSystem.lockGlobalStringRead('ip_10.0.1.50', 300);
    assignIP(vm, "10.0.1.50");
    LockingSystem.unlockGlobalStringRead('ip_10.0.1.50');
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "ip_10.0.1.50"


def test_lock_with_whitespace_variations():
    """Test lock detection with various whitespace."""
    script = """
    LockingSystem.lockGlobalStringRead(  "ip_10.0.1.50"  ,  300  );
    assignIP(vm, "10.0.1.50");
    LockingSystem.unlockGlobalStringRead(  "ip_10.0.1.50"  );
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "ip_10.0.1.50"
    assert patterns[0].timeout == 300


def test_sanitize_resource_name_with_dots():
    """Test sanitizing resource name with dots."""
    assert sanitize_resource_name("ip_10.0.1.50") == "ip_10_0_1_50"


def test_sanitize_resource_name_with_hyphens():
    """Test sanitizing resource name with hyphens."""
    assert sanitize_resource_name("host-name.domain.com") == "host_name_domain_com"


def test_sanitize_resource_name_with_special_chars():
    """Test sanitizing resource name with special characters."""
    assert sanitize_resource_name("resource@#$%name") == "resource____name"


def test_sanitize_resource_name_starting_with_number():
    """Test sanitizing resource name that starts with a number."""
    assert sanitize_resource_name("10.0.1.50") == "lock_10_0_1_50"


def test_sanitize_resource_name_already_valid():
    """Test sanitizing already valid resource name."""
    assert sanitize_resource_name("valid_resource_name") == "valid_resource_name"


def test_lock_pattern_ordering():
    """Test that lock patterns are ordered by position in script."""
    script = """
    doSomething();

    LockingSystem.lockGlobalStringRead("resource_b", 300);
    workB();
    LockingSystem.unlockGlobalStringRead("resource_b");

    doSomethingElse();

    LockingSystem.lockGlobalStringRead("resource_a", 180);
    workA();
    LockingSystem.unlockGlobalStringRead("resource_a");
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 2
    # Patterns should be ordered by position
    assert patterns[0].resource == "resource_b"
    assert patterns[1].resource == "resource_a"
    assert patterns[0].lock_position < patterns[1].lock_position


def test_complex_resource_name():
    """Test detection with complex resource names."""
    script = """
    LockingSystem.lockGlobalStringRead("network_vlan_100_port_8080", 600);
    configurePort();
    LockingSystem.unlockGlobalStringRead("network_vlan_100_port_8080");
    """

    patterns = detect_locking_patterns(script)

    assert len(patterns) == 1
    assert patterns[0].resource == "network_vlan_100_port_8080"
    assert patterns[0].timeout == 600


def test_lock_pattern_dataclass():
    """Test LockPattern dataclass creation."""
    pattern = LockPattern(
        resource="test_resource",
        timeout=300,
        lock_position=100,
        unlock_position=200,
        has_try_finally=True,
    )

    assert pattern.resource == "test_resource"
    assert pattern.timeout == 300
    assert pattern.lock_position == 100
    assert pattern.unlock_position == 200
    assert pattern.has_try_finally is True


def test_lock_pattern_dataclass_defaults():
    """Test LockPattern dataclass with default values."""
    pattern = LockPattern(
        resource="test_resource",
        timeout=300,
        lock_position=100,
    )

    assert pattern.resource == "test_resource"
    assert pattern.timeout == 300
    assert pattern.lock_position == 100
    assert pattern.unlock_position is None  # Default
    assert pattern.has_try_finally is False  # Default
