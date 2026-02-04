"""
Unit tests for workspace functionality.
"""


def test_workspace_initialization(temp_workspace):
    """Test workspace is initialized with correct structure"""
    workspace = temp_workspace

    # Verify directory structure
    assert workspace.root.exists()
    assert (workspace.root / "input" / "powercli").exists()
    assert (workspace.root / "input" / "vrealize").exists()
    assert (workspace.root / "intent").exists()
    assert (workspace.root / "mapping").exists()
    assert (workspace.root / "output" / "ansible").exists()
    assert (workspace.root / "output" / "kubevirt").exists()
    assert (workspace.root / "runs").exists()

    # Verify config file exists
    assert workspace.config_file.exists()


def test_workspace_load_config(temp_workspace):
    """Test loading workspace configuration"""
    workspace = temp_workspace

    config = workspace.load_config()

    assert config is not None
    assert "llm" in config
    assert "profiles" in config
    assert "lab" in config["profiles"]
    assert "prod" in config["profiles"]


def test_workspace_config_structure(temp_workspace):
    """Test workspace config has expected structure"""
    workspace = temp_workspace
    config = workspace.load_config()

    # Verify LLM config
    assert "provider" in config["llm"]
    assert "model" in config["llm"]
    assert "api_key_env" in config["llm"]

    # Verify profiles
    for profile_name in ["lab", "prod"]:
        profile = config["profiles"][profile_name]
        assert "default_namespace" in profile
        assert "default_network" in profile
        assert "default_storage_class" in profile
