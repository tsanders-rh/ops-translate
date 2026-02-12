"""
vRealize LockingSystem pattern detection.

Detects vRO LockingSystem calls for distributed locking and extracts
lock acquisition/release pairs for translation to Ansible locking tasks.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class LockPattern:
    """Represents a detected locking pattern in vRO code."""

    resource: str
    timeout: int  # Seconds
    lock_position: int
    unlock_position: int | None = None
    has_try_finally: bool = False


def detect_locking_patterns(script: str) -> list[LockPattern]:
    """
    Detect LockingSystem lock/unlock pairs in JavaScript code.

    Supports patterns:
    - LockingSystem.lockGlobalStringRead("resource", timeout)
    - LockingSystem.unlockGlobalStringRead("resource")
    - Try/finally blocks wrapping locked code

    Args:
        script: JavaScript code from vRO workflow

    Returns:
        List of detected lock patterns with resource, timeout, and positions

    Example:
        >>> script = '''
        ... LockingSystem.lockGlobalStringRead("ip_10.0.1.50", 300);
        ... assignIP(vm, "10.0.1.50");
        ... LockingSystem.unlockGlobalStringRead("ip_10.0.1.50");
        ... '''
        >>> patterns = detect_locking_patterns(script)
        >>> patterns[0].resource
        'ip_10.0.1.50'
        >>> patterns[0].timeout
        300
    """
    patterns = []

    # Pattern: LockingSystem.lockGlobalStringRead("resource", timeout)
    # Match both with and without timeout parameter
    lock_pattern = r'LockingSystem\.lockGlobalStringRead\(\s*["\'](.+?)["\']\s*(?:,\s*(\d+))?\s*\)'

    # Find all lock acquisitions
    locks: dict[str, dict[str, Any]] = {}
    for match in re.finditer(lock_pattern, script):
        resource = match.group(1)
        timeout_str = match.group(2)
        timeout = int(timeout_str) if timeout_str else 300  # Default 5 min

        locks[resource] = {
            "timeout": timeout,
            "lock_position": match.start(),
            "unlock_position": None,
            "has_try_finally": False,
        }

    # Pattern: LockingSystem.unlockGlobalStringRead("resource")
    unlock_pattern = r'LockingSystem\.unlockGlobalStringRead\(\s*["\'](.+?)["\']\s*\)'

    # Find corresponding unlocks
    for match in re.finditer(unlock_pattern, script):
        resource = match.group(1)
        if resource in locks:
            locks[resource]["unlock_position"] = match.start()

    # Detect try/finally blocks around locks
    try_pattern = r"\btry\s*\{"
    finally_pattern = r"\bfinally\s*\{"

    for resource, lock_info in locks.items():
        # Check if there's a try block near the lock (either before or after)
        lock_pos = lock_info["lock_position"]
        unlock_pos = lock_info.get("unlock_position")

        if unlock_pos:
            # Check if there's a try block between lock and unlock
            segment = script[lock_pos:unlock_pos]
            try_match = re.search(try_pattern, segment)

            # Also check just after lock (lock might be before try)
            script_after_lock = script[lock_pos:]
            try_after_match = re.search(
                try_pattern, script_after_lock[:200]
            )  # Check next 200 chars

            # Check if there's a finally block that contains the unlock
            finally_match = re.search(finally_pattern, script_after_lock)

            if finally_match:
                finally_start = lock_pos + finally_match.start()
                # Check if unlock is inside finally block (after finally start)
                if unlock_pos > finally_start:
                    lock_info["has_try_finally"] = True
                    continue

            # Alternative pattern: lock, try { work }, finally { unlock }
            if try_after_match or try_match:
                # Look for finally after try
                if finally_match and unlock_pos > (lock_pos + finally_match.start()):
                    lock_info["has_try_finally"] = True

    # Convert to LockPattern objects
    for resource, info in locks.items():
        pattern = LockPattern(
            resource=resource,
            timeout=info["timeout"],
            lock_position=info["lock_position"],
            unlock_position=info.get("unlock_position"),
            has_try_finally=info["has_try_finally"],
        )
        patterns.append(pattern)

    # Sort by position in script
    patterns.sort(key=lambda p: p.lock_position)

    return patterns


def sanitize_resource_name(resource: str) -> str:
    """
    Sanitize resource name for use as Ansible variable.

    Converts special characters to underscores and ensures valid variable name.

    Args:
        resource: Resource name from LockingSystem call

    Returns:
        Sanitized variable name

    Example:
        >>> sanitize_resource_name("ip_10.0.1.50")
        'ip_10_0_1_50'
        >>> sanitize_resource_name("host-name.domain.com")
        'host_name_domain_com'
    """
    # Replace special characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", resource)

    # Ensure doesn't start with number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"lock_{sanitized}"

    return sanitized
