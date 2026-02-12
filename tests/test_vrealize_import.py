"""
Unit tests for vRealize bundle import functionality.

Tests bundle detection, extraction, manifest generation, and security features.
"""

import json
import tempfile
from pathlib import Path

import pytest

from ops_translate.summarize.vrealize import (
    _compute_dir_hash,
    _compute_file_hash,
    _extract_action_fqname,
    _is_safe_path,
    import_vrealize_bundle,
)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures/vrealize/bundles"


class TestBundleDetection:
    """Tests for bundle type detection."""

    def test_detect_single_workflow_xml(self, tmp_path):
        """Test that single XML files are detected as workflows."""
        xml_file = tmp_path / "workflow.xml"
        xml_file.write_text('<?xml version="1.0"?><workflow/>')

        manifest = import_vrealize_bundle(xml_file, tmp_path)

        assert manifest["source_type"] == "vrealize_workflow"
        assert len(manifest["workflows"]) == 1
        assert manifest["workflows"][0]["name"] == "workflow"

    def test_detect_directory_bundle(self):
        """Test that directory bundles are detected correctly."""
        bundle_dir = FIXTURES_DIR / "simple-bundle"
        assert bundle_dir.exists(), "Test fixture not found"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(bundle_dir, workspace_root)

        assert manifest["source_type"] == "vrealize_bundle"
        assert len(manifest["workflows"]) >= 1
        assert len(manifest["actions"]) >= 2
        assert len(manifest["configurations"]) >= 1

    def test_detect_package_bundle(self):
        """Test that .package files are extracted and processed."""
        package_file = FIXTURES_DIR / "simple-bundle.package"
        assert package_file.exists(), "Test fixture not found"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(package_file, workspace_root)

        assert manifest["source_type"] == "vrealize_bundle"
        assert len(manifest["workflows"]) >= 1
        assert len(manifest["actions"]) >= 2


class TestManifestGeneration:
    """Tests for manifest generation and content."""

    def test_manifest_structure(self):
        """Test that manifest has correct structure and required fields."""
        bundle_dir = FIXTURES_DIR / "simple-bundle"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(bundle_dir, workspace_root)

            # Check required top-level fields
            assert "source_path" in manifest
            assert "source_type" in manifest
            assert "import_timestamp" in manifest
            assert "sha256" in manifest
            assert "workflows" in manifest
            assert "actions" in manifest
            assert "configurations" in manifest
            assert "action_index" in manifest

            # Check action_index structure
            assert "count" in manifest["action_index"]
            assert "file" in manifest["action_index"]

            # Verify manifest was written to workspace
            manifest_file = workspace_root / "input/vrealize/manifest.json"
            assert manifest_file.exists()

            # Verify manifest is valid JSON
            with open(manifest_file) as f:
                loaded_manifest = json.load(f)
            assert loaded_manifest == manifest

    def test_workflow_metadata(self):
        """Test that workflow entries have correct metadata."""
        bundle_dir = FIXTURES_DIR / "simple-bundle"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(bundle_dir, workspace_root)

        workflows = manifest["workflows"]
        assert len(workflows) > 0

        for workflow in workflows:
            assert "path" in workflow
            assert "absolute_path" in workflow
            assert "name" in workflow
            assert "sha256" in workflow
            assert workflow["path"].startswith("workflows/")
            assert workflow["path"].endswith(".workflow.xml")

    def test_action_metadata_and_fqname(self):
        """Test that action entries have correct metadata and FQN."""
        bundle_dir = FIXTURES_DIR / "simple-bundle"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(bundle_dir, workspace_root)

        actions = manifest["actions"]
        assert len(actions) >= 2

        # Check for NSX action
        nsx_actions = [a for a in actions if "nsx" in a["fqname"]]
        assert len(nsx_actions) > 0
        nsx_action = nsx_actions[0]
        assert nsx_action["fqname"] == "com.acme.nsx/createSegment"
        assert "actions/com.acme.nsx/" in nsx_action["path"]

        # Check for utils action
        utils_actions = [a for a in actions if "utils" in a["fqname"]]
        assert len(utils_actions) > 0
        utils_action = utils_actions[0]
        assert utils_action["fqname"] == "com.acme.utils/validateInput"

    def test_configuration_metadata(self):
        """Test that configuration entries have correct metadata."""
        bundle_dir = FIXTURES_DIR / "simple-bundle"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(bundle_dir, workspace_root)

        configs = manifest["configurations"]
        assert len(configs) >= 1

        for config in configs:
            assert "path" in config
            assert "absolute_path" in config
            assert "sha256" in config
            assert config["path"].startswith("configurations/")


class TestActionFQNameExtraction:
    """Tests for action fully-qualified name extraction."""

    def test_fqname_with_module(self, tmp_path):
        """Test FQN extraction for action in module."""
        actions_dir = tmp_path / "actions"
        actions_dir.mkdir()

        module_dir = actions_dir / "com.acme.nsx"
        module_dir.mkdir()

        action_file = module_dir / "createSegment.action.xml"
        action_file.touch()

        fqname = _extract_action_fqname(action_file, actions_dir)
        assert fqname == "com.acme.nsx/createSegment"

    def test_fqname_nested_module(self, tmp_path):
        """Test FQN extraction for action in nested module."""
        actions_dir = tmp_path / "actions"
        actions_dir.mkdir()

        module_dir = actions_dir / "com" / "acme" / "nsx"
        module_dir.mkdir(parents=True)

        action_file = module_dir / "createFirewall.action.xml"
        action_file.touch()

        fqname = _extract_action_fqname(action_file, actions_dir)
        assert fqname == "com/acme/nsx/createFirewall"

    def test_fqname_no_module(self, tmp_path):
        """Test FQN extraction for action without module."""
        actions_dir = tmp_path / "actions"
        actions_dir.mkdir()

        action_file = actions_dir / "simpleAction.action.xml"
        action_file.touch()

        fqname = _extract_action_fqname(action_file, actions_dir)
        assert fqname == "simpleAction"


class TestHashingFunctions:
    """Tests for file and directory hashing."""

    def test_file_hash_deterministic(self, tmp_path):
        """Test that file hashing is deterministic."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = _compute_file_hash(test_file)
        hash2 = _compute_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_file_hash_changes_with_content(self, tmp_path):
        """Test that file hash changes when content changes."""
        test_file = tmp_path / "test.txt"

        test_file.write_text("content 1")
        hash1 = _compute_file_hash(test_file)

        test_file.write_text("content 2")
        hash2 = _compute_file_hash(test_file)

        assert hash1 != hash2

    def test_dir_hash_deterministic(self, tmp_path):
        """Test that directory hashing is deterministic."""
        (tmp_path / "file1.txt").write_text("content 1")
        (tmp_path / "file2.txt").write_text("content 2")

        hash1 = _compute_dir_hash(tmp_path)
        hash2 = _compute_dir_hash(tmp_path)

        assert hash1 == hash2

    def test_dir_hash_changes_with_structure(self, tmp_path):
        """Test that directory hash changes when structure changes."""
        (tmp_path / "file1.txt").write_text("content")
        hash1 = _compute_dir_hash(tmp_path)

        (tmp_path / "file2.txt").write_text("content")
        hash2 = _compute_dir_hash(tmp_path)

        assert hash1 != hash2


class TestZipSlipProtection:
    """Tests for zip-slip security protection."""

    def test_safe_path_within_base(self, tmp_path):
        """Test that safe paths within base directory are allowed."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        target_path = base_dir / "subdir" / "file.txt"
        assert _is_safe_path(base_dir, target_path) is True

    def test_unsafe_path_parent_traversal(self, tmp_path):
        """Test that parent traversal paths are blocked."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        # Create a path that tries to escape
        target_path = base_dir / ".." / "outside.txt"
        assert _is_safe_path(base_dir, target_path) is False

    def test_unsafe_path_absolute_outside(self, tmp_path):
        """Test that absolute paths outside base are blocked."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        outside_path = tmp_path / "outside" / "file.txt"
        assert _is_safe_path(base_dir, outside_path) is False

    def test_malicious_zip_rejected(self):
        """Test that malicious ZIP with path traversal is rejected."""
        malicious_zip = FIXTURES_DIR / "malicious.zip"
        assert malicious_zip.exists(), "Malicious ZIP fixture not found"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)

            # Import should raise ValueError due to unsafe paths
            with pytest.raises(ValueError, match="Unsafe path"):
                import_vrealize_bundle(malicious_zip, workspace_root)


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with single workflow import."""

    def test_single_xml_import_still_works(self, tmp_path):
        """Test that importing a single workflow XML still works."""
        # Create a simple workflow XML
        workflow_xml = tmp_path / "test-workflow.xml"
        workflow_xml.write_text(
            '<?xml version="1.0"?>'
            '<workflow xmlns="http://vmware.com/vco/workflow">'
            "<display-name>Test Workflow</display-name>"
            "</workflow>"
        )

        manifest = import_vrealize_bundle(workflow_xml, tmp_path)

        assert manifest["source_type"] == "vrealize_workflow"
        assert len(manifest["workflows"]) == 1
        assert manifest["workflows"][0]["name"] == "test-workflow"
        assert len(manifest["actions"]) == 0
        assert len(manifest["configurations"]) == 0


class TestErrorHandling:
    """Tests for error handling and validation."""

    def test_nonexistent_path_raises_error(self, tmp_path):
        """Test that importing non-existent path raises error."""
        nonexistent = tmp_path / "does-not-exist"

        with pytest.raises(ValueError, match="Path not found"):
            import_vrealize_bundle(nonexistent, tmp_path)

    def test_unsupported_file_type_raises_error(self, tmp_path):
        """Test that unsupported file types raise error."""
        unsupported = tmp_path / "file.txt"
        unsupported.write_text("not a workflow")

        with pytest.raises(ValueError, match="Unsupported file type"):
            import_vrealize_bundle(unsupported, tmp_path)

    def test_empty_bundle_directory(self, tmp_path):
        """Test that empty bundle directory produces empty manifest."""
        bundle_dir = tmp_path / "empty-bundle"
        bundle_dir.mkdir()

        # Create subdirectories but no files
        (bundle_dir / "workflows").mkdir()
        (bundle_dir / "actions").mkdir()
        (bundle_dir / "configurations").mkdir()

        manifest = import_vrealize_bundle(bundle_dir, tmp_path)

        assert manifest["source_type"] == "vrealize_bundle"
        assert len(manifest["workflows"]) == 0
        assert len(manifest["actions"]) == 0
        assert len(manifest["configurations"]) == 0
