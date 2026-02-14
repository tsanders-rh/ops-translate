"""
Linting utilities for generated Ansible code.

Integrates with ansible-lint to validate generated playbooks and roles.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class AnsibleLintResult:
    """Result of ansible-lint execution."""

    def __init__(
        self,
        success: bool,
        violations: list[dict[str, Any]],
        files_checked: int,
        stdout: str | None = None,
        stderr: str | None = None,
    ):
        """
        Initialize lint result.

        Args:
            success: True if linting passed (no violations)
            violations: List of violation dicts
            files_checked: Number of files checked
            stdout: Standard output from ansible-lint
            stderr: Standard error from ansible-lint
        """
        self.success = success
        self.violations = violations
        self.files_checked = files_checked
        self.stdout = stdout
        self.stderr = stderr

    @property
    def violation_count(self) -> int:
        """Total number of violations."""
        return len(self.violations)

    def get_violations_by_severity(self) -> dict[str, list[dict[str, Any]]]:
        """
        Group violations by severity.

        Returns:
            Dict mapping severity (error/warning/info) to violations
        """
        by_severity: dict[str, list[dict[str, Any]]] = {
            "error": [],
            "warning": [],
            "info": [],
        }

        for violation in self.violations:
            severity = violation.get("level", "warning").lower()
            if severity in by_severity:
                by_severity[severity].append(violation)
            else:
                by_severity["warning"].append(violation)

        return by_severity

    def get_violations_by_file(self) -> dict[str, list[dict[str, Any]]]:
        """
        Group violations by file.

        Returns:
            Dict mapping filename to violations
        """
        by_file: dict[str, list[dict[str, Any]]] = {}

        for violation in self.violations:
            filename = violation.get("filename", "unknown")
            if filename not in by_file:
                by_file[filename] = []
            by_file[filename].append(violation)

        return by_file


def is_ansible_lint_available() -> bool:
    """
    Check if ansible-lint is installed and available.

    Returns:
        True if ansible-lint is available, False otherwise
    """
    return shutil.which("ansible-lint") is not None


def run_ansible_lint(
    path: Path,
    config_file: Path | None = None,
    format: str = "json",
    strict: bool = False,
) -> AnsibleLintResult:
    """
    Run ansible-lint on a path (file or directory).

    Args:
        path: Path to lint (file or directory)
        config_file: Optional path to ansible-lint config file (.ansible-lint)
        format: Output format (json, plain, codeclimate, sarif)
        strict: If True, warnings are treated as errors

    Returns:
        AnsibleLintResult with violations and metadata

    Raises:
        FileNotFoundError: If ansible-lint is not installed
        RuntimeError: If ansible-lint execution fails unexpectedly
    """
    if not is_ansible_lint_available():
        raise FileNotFoundError(
            "ansible-lint is not installed. Install with: pip install ansible-lint"
        )

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # Build command
    cmd = ["ansible-lint", "--format", format]

    if config_file and config_file.exists():
        cmd.extend(["--config-file", str(config_file)])

    if strict:
        cmd.append("--strict")

    cmd.append(str(path))

    # Run ansible-lint
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
        )

        # ansible-lint returns:
        # - 0: No violations
        # - 2: Violations found
        # - 1: Fatal error (e.g., syntax error in playbook)
        success = result.returncode == 0

        violations = []
        files_checked = 0

        # Parse JSON output
        if format == "json" and result.stdout:
            try:
                lint_data = json.loads(result.stdout)

                # ansible-lint JSON format varies by version
                # Try to extract violations from different formats
                if isinstance(lint_data, list):
                    violations = lint_data
                elif isinstance(lint_data, dict):
                    # Extract violations, defaulting to empty list
                    violations = lint_data.get("violations") or lint_data.get("results") or []
                    files_checked = lint_data.get("files_checked", 0)

            except json.JSONDecodeError:
                # If JSON parsing fails, return empty violations
                pass

        return AnsibleLintResult(
            success=success,
            violations=violations,
            files_checked=files_checked,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    except subprocess.TimeoutExpired:
        raise RuntimeError("ansible-lint execution timed out (60s)")
    except Exception as e:
        raise RuntimeError(f"ansible-lint execution failed: {e}")


def generate_lint_report(result: AnsibleLintResult) -> str:
    """
    Generate human-readable lint report.

    Args:
        result: AnsibleLintResult from run_ansible_lint()

    Returns:
        Markdown-formatted lint report
    """
    lines = []

    lines.append("# Ansible Lint Report\n")

    if result.success:
        lines.append("**Status**: ✅ PASSED\n")
        lines.append(f"No violations found ({result.files_checked} files checked)\n")
    else:
        lines.append("**Status**: ❌ FAILED\n")
        lines.append(f"Found {result.violation_count} violation(s)\n")

    if result.violations:
        by_severity = result.get_violations_by_severity()

        for severity in ["error", "warning", "info"]:
            severity_violations = by_severity[severity]
            if not severity_violations:
                continue

            severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}[severity]
            lines.append(f"\n## {severity_icon} {severity.title()} ({len(severity_violations)})\n")

            for violation in severity_violations:
                rule_id = violation.get("tag", violation.get("rule", {}).get("id", "unknown"))
                message = violation.get("message", "No message")
                filename = violation.get("filename", "unknown")
                line = violation.get("line", violation.get("linenumber", "?"))

                lines.append(f"### {rule_id}\n")
                lines.append(f"**File**: `{filename}:{line}`\n")
                lines.append(f"**Message**: {message}\n")

    return "\n".join(lines)
