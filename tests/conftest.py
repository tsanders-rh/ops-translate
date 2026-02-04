"""
Pytest configuration and shared fixtures.
"""

import tempfile
from pathlib import Path

import pytest

from ops_translate.workspace import Workspace


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        workspace = Workspace(workspace_path)
        workspace.initialize()
        yield workspace
        # Cleanup happens automatically when context exits


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def powercli_fixture(fixtures_dir):
    """Return path to PowerCLI test fixture."""
    return fixtures_dir / "powercli" / "simple-vm.ps1"


@pytest.fixture
def vrealize_fixture(fixtures_dir):
    """Return path to vRealize test fixture."""
    return fixtures_dir / "vrealize" / "simple-workflow.xml"


@pytest.fixture
def mock_llm_config():
    """Return configuration for mock LLM provider."""
    return {"llm": {"provider": "mock", "model": "mock-model"}}
