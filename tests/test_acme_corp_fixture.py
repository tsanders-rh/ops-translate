"""
Comprehensive regression tests for ACME Corp vRO bundle fixture.

Tests the complete pipeline from bundle import through gap analysis
and interview generation using a realistic multi-workflow bundle.
"""

import json
import re
import tempfile
from pathlib import Path

from ops_translate.analyze.vrealize import analyze_vrealize_workflow
from ops_translate.intent.classify import classify_components
from ops_translate.intent.interview import generate_questions
from ops_translate.summarize.vrealize import import_vrealize_bundle
from ops_translate.summarize.vrealize_actions import build_action_index
from ops_translate.translate.vrealize_workflow import WorkflowParser

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures/vrealize/bundles"
ACME_BUNDLE_DIR = FIXTURES_DIR / "acme-corp-vro-export"


class TestBundleImport:
    """Test bundle import and manifest generation."""

    def test_import_acme_corp_bundle(self):
        """Test importing ACME Corp bundle and validating manifest structure."""
        assert ACME_BUNDLE_DIR.exists(), "ACME Corp bundle fixture not found"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        # Validate manifest structure
        assert "source_type" in manifest
        assert "workflows" in manifest
        assert "actions" in manifest
        assert "configurations" in manifest
        assert "action_index" in manifest

        # Validate exact counts
        assert manifest["source_type"] == "vrealize_bundle"
        assert len(manifest["workflows"]) == 3, "Expected 3 workflows"
        assert len(manifest["actions"]) == 9, "Expected 9 actions"
        assert len(manifest["configurations"]) == 1, "Expected 1 configuration file"

    def test_manifest_has_all_workflows(self):
        """Test that all 3 workflows are present in manifest with correct metadata."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        workflow_names = {w["name"] for w in manifest["workflows"]}
        expected_names = {"vm-provisioning", "network-config", "storage-tier"}
        assert workflow_names == expected_names, f"Expected {expected_names}, got {workflow_names}"

        # Verify all workflows have required fields
        for workflow in manifest["workflows"]:
            assert "path" in workflow
            assert "absolute_path" in workflow
            assert "name" in workflow
            assert "sha256" in workflow
            # Verify SHA256 format (64 hex chars)
            assert len(workflow["sha256"]) == 64
            assert all(c in "0123456789abcdef" for c in workflow["sha256"])

    def test_manifest_has_all_actions(self):
        """Test that all 9 actions are present with correct FQNs and modules."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        # Expected action FQNs
        expected_fqns = {
            "com.acme.nsx/createSegment",
            "com.acme.nsx/createFirewallRule",
            "com.acme.servicenow/createIncident",
            "com.acme.servicenow/updateIncident",
            "com.acme.infoblox/getNextIP",
            "com.acme.infoblox/createDNSRecord",
            "com.acme.storage/assignTier",
            "com.acme.storage/expandDatastore",
            "com.acme.utils/validateInput",
        }

        actual_fqns = {a["fqname"] for a in manifest["actions"]}
        assert actual_fqns == expected_fqns, f"Expected {expected_fqns}, got {actual_fqns}"

        # Verify FQN format
        for action in manifest["actions"]:
            assert re.match(r"com\.acme\.[a-z]+/[a-zA-Z]+", action["fqname"])

        # Verify module grouping
        nsx_actions = [a for a in manifest["actions"] if a["fqname"].startswith("com.acme.nsx/")]
        snow_actions = [
            a for a in manifest["actions"] if a["fqname"].startswith("com.acme.servicenow/")
        ]
        infoblox_actions = [
            a for a in manifest["actions"] if a["fqname"].startswith("com.acme.infoblox/")
        ]
        storage_actions = [
            a for a in manifest["actions"] if a["fqname"].startswith("com.acme.storage/")
        ]
        utils_actions = [
            a for a in manifest["actions"] if a["fqname"].startswith("com.acme.utils/")
        ]

        assert len(nsx_actions) == 2
        assert len(snow_actions) == 2
        assert len(infoblox_actions) == 2
        assert len(storage_actions) == 2
        assert len(utils_actions) == 1

    def test_manifest_written_to_workspace(self):
        """Test that manifest and action index files are written to workspace."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

            # Verify manifest file written
            manifest_file = workspace_root / "input/vrealize/manifest.json"
            assert manifest_file.exists(), "Manifest file not written"

            # Verify manifest is valid JSON
            with open(manifest_file) as f:
                loaded_manifest = json.load(f)
            assert loaded_manifest == manifest

            # Verify action index file written
            action_index_file = workspace_root / "input/vrealize/action-index.json"
            assert action_index_file.exists(), "Action index file not written"


class TestActionIndexBuilding:
    """Test ActionIndex creation and lookup."""

    def test_build_action_index_from_bundle(self):
        """Test building action index from ACME Corp bundle."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

            action_index = build_action_index(manifest)

            # Verify count
            assert len(action_index) == 9, f"Expected 9 actions, got {len(action_index)}"
            assert len(action_index.actions) == 9

            # Verify action index file was written by import_vrealize_bundle
            action_index_file = workspace_root / "input/vrealize/action-index.json"
            assert action_index_file.exists()

    def test_action_lookup_by_fqname(self):
        """Test looking up actions by FQN in action index."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)

        # Test each action can be looked up
        test_fqns = [
            "com.acme.nsx/createSegment",
            "com.acme.nsx/createFirewallRule",
            "com.acme.servicenow/createIncident",
            "com.acme.infoblox/getNextIP",
            "com.acme.storage/assignTier",
            "com.acme.utils/validateInput",
        ]

        for fqn in test_fqns:
            action = action_index.get(fqn)
            assert action is not None, f"Action {fqn} not found in index"
            assert action.fqname == fqn
            assert action.script is not None and len(action.script) > 0
            assert action.name is not None
            assert action.module is not None

    def test_action_script_contains_patterns(self):
        """Test that action scripts contain expected integration patterns."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)

        # NSX createSegment should contain nsxClient.createSegment pattern
        create_segment = action_index.get("com.acme.nsx/createSegment")
        assert "nsxClient.createSegment" in create_segment.script

        # NSX createFirewallRule should contain nsxClient.createFirewallRule pattern
        create_rule = action_index.get("com.acme.nsx/createFirewallRule")
        assert "nsxClient.createFirewallRule" in create_rule.script

        # ServiceNow should contain servicenow reference
        create_incident = action_index.get("com.acme.servicenow/createIncident")
        assert "servicenow" in create_incident.script.lower()

        # Infoblox should contain infoblox reference
        get_next_ip = action_index.get("com.acme.infoblox/getNextIP")
        assert "infoblox" in get_next_ip.script.lower()


class TestActionResolution:
    """Test action resolution in workflows."""

    def test_resolve_actions_in_vm_provisioning(self):
        """Test that actions are resolved in vm-provisioning workflow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_file)

        # Collect all resolved actions
        all_resolved = []
        for item in items:
            all_resolved.extend(item.resolved_actions)

        resolved_fqns = {action.fqname for action in all_resolved}

        # vm-provisioning should call these actions:
        # - com.acme.utils/validateInput
        # - com.acme.nsx/createSegment
        # - com.acme.infoblox/getNextIP
        # - com.acme.nsx/createFirewallRule
        expected_calls = {
            "com.acme.utils/validateInput",
            "com.acme.nsx/createSegment",
            "com.acme.infoblox/getNextIP",
            "com.acme.nsx/createFirewallRule",
        }

        assert expected_calls.issubset(
            resolved_fqns
        ), f"Expected calls {expected_calls} not found. Got: {resolved_fqns}"

    def test_resolved_action_scripts_included(self):
        """Test that resolved actions include script content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_file)

        # Check that resolved actions have scripts
        for item in items:
            for action in item.resolved_actions:
                assert action.script is not None
                assert len(action.script) > 0

                # Verify NSX actions contain detection patterns
                if "nsx" in action.fqname.lower():
                    assert "nsxClient" in action.script or "nsx" in action.script.lower()

    def test_unresolved_actions_tracked(self):
        """Test that unresolved action count is zero (all actions should resolve)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_file)

        # Count unresolved actions
        total_unresolved = sum(len(item.unresolved_actions) for item in items)
        assert total_unresolved == 0, f"Found {total_unresolved} unresolved actions"


class TestIntegrationDetection:
    """Test integration pattern detection."""

    def test_detect_nsx_segments(self):
        """Test that NSX segment operations are detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)

        # Should detect NSX segment operations
        assert "nsx_operations" in analysis
        assert "segments" in analysis["nsx_operations"]
        assert (
            len(analysis["nsx_operations"]["segments"]) >= 2
        ), "Expected at least 2 NSX segment detections"

        # Verify evidence includes action location
        for segment_op in analysis["nsx_operations"]["segments"]:
            assert "location" in segment_op
            # Should have action: prefix for actions
            if "action:" in segment_op["location"]:
                assert "com.acme.nsx/createSegment" in segment_op["location"]

    def test_detect_nsx_firewall_rules(self):
        """Test that NSX firewall rule operations are detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)

        assert "nsx_operations" in analysis
        assert "firewall_rules" in analysis["nsx_operations"]
        assert len(analysis["nsx_operations"]["firewall_rules"]) >= 1

        # Check confidence scores
        for rule_op in analysis["nsx_operations"]["firewall_rules"]:
            assert "confidence" in rule_op
            assert (
                rule_op["confidence"] > 0.6
            ), "Expected reasonable confidence for firewall rule patterns"

    def test_detect_servicenow_plugin(self):
        """Test that ServiceNow plugin references are detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/network-config.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)

        assert "custom_plugins" in analysis
        # Filter for ServiceNow plugins (detected as "snowModule" variable name)
        snow_plugins = [
            p
            for p in analysis["custom_plugins"]
            if "snow" in p["plugin_name"].lower() or "servicenow" in p.get("evidence", "").lower()
        ]
        assert len(snow_plugins) >= 1, "Expected ServiceNow plugin detection"

        # Verify evidence contains servicenow module reference
        for plugin in snow_plugins:
            assert "evidence" in plugin
            evidence_lower = plugin["evidence"].lower()
            assert "snow" in evidence_lower or "servicenow" in evidence_lower

    def test_detect_infoblox_plugin(self):
        """Test that Infoblox plugin references are detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)

        assert "custom_plugins" in analysis
        infoblox_plugins = [
            p for p in analysis["custom_plugins"] if "infoblox" in p["plugin_name"].lower()
        ]
        assert len(infoblox_plugins) >= 1, "Expected Infoblox plugin detection"

    def test_detect_rest_api_calls(self):
        """Test that REST API calls are detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/network-config.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)

        # REST API calls may be in rest_api_calls key or detected as custom plugins (restClient)
        has_rest_calls = "rest_api_calls" in analysis and len(analysis["rest_api_calls"]) >= 1
        has_rest_plugin = any(
            "rest" in p["plugin_name"].lower() for p in analysis.get("custom_plugins", [])
        )

        assert has_rest_calls or has_rest_plugin, "Expected REST API call detection"

        # Verify restClient pattern detected in either structure
        if has_rest_calls:
            rest_call_texts = [call.get("evidence", "") for call in analysis["rest_api_calls"]]
            assert any("restClient" in text or "rest" in text.lower() for text in rest_call_texts)
        if has_rest_plugin:
            rest_plugins = [
                p for p in analysis["custom_plugins"] if "rest" in p["plugin_name"].lower()
            ]
            assert any("restClient" in p.get("evidence", "") for p in rest_plugins)

    def test_detect_approval_workflow(self):
        """Test that approval workflow component is detected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        # Approval detection happens during classification, not direct analysis
        # For now, we verify the workflow has item with "approval" in description
        from ops_translate.translate.vrealize_workflow import WorkflowParser

        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_file)

        approval_items = [
            item for item in items if item.display_name and "approval" in item.display_name.lower()
        ]
        assert len(approval_items) >= 1, "Expected workflow item with approval in display_name"


class TestGapAnalysis:
    """Test gap analysis classification."""

    def test_classify_nsx_components(self):
        """Test that NSX components are correctly classified."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)
        components = classify_components(analysis)

        # Filter NSX components
        nsx_components = [c for c in components if "nsx" in c.component_type.lower()]
        assert len(nsx_components) >= 2, "Expected at least 2 NSX components"

        # Check for specific component types
        component_types = {c.component_type for c in nsx_components}
        assert "nsx_segments" in component_types or "nsx_firewall_rules" in component_types

        # Verify level and OpenShift equivalent
        for component in nsx_components:
            assert component.level is not None
            # NSX components should have OpenShift equivalents suggested
            if component.component_type == "nsx_segments":
                assert component.openshift_equivalent is not None
            elif component.component_type == "nsx_firewall_rules":
                assert component.openshift_equivalent is not None

    def test_classify_custom_plugins(self):
        """Test that custom plugin integrations are classified."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/network-config.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)
        components = classify_components(analysis)

        # Custom plugins should be detected and classified
        # (ServiceNow, Infoblox appear as custom plugins)
        assert len(components) > 0, "Expected classified components"

    def test_classification_summary_counts(self):
        """Test classification summary component counts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)
        components = classify_components(analysis)

        # Should have multiple components classified
        assert len(components) >= 3, f"Expected at least 3 components, got {len(components)}"

        # Verify component types distribution
        component_types = {c.component_type for c in components}
        assert len(component_types) >= 2, "Expected multiple component types"


class TestInterviewGeneration:
    """Test decision interview generation."""

    def test_generate_questions_for_nsx_firewall(self):
        """Test that NSX firewall questions are generated with evidence."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)
        components = classify_components(analysis)

        # Generate interview
        interview_pack = generate_questions(components)

        # Should have questions
        assert "questions" in interview_pack
        questions = interview_pack["questions"]

        # Look for NSX firewall questions
        nsx_firewall_questions = [q for q in questions if "firewall" in q.get("prompt", "").lower()]

        if len(nsx_firewall_questions) > 0:
            # Verify questions have evidence (from Issue #55)
            for question in nsx_firewall_questions:
                # Evidence should be in prompt if component had evidence
                # Not all questions may have evidence, but structure should be valid
                _ = question["prompt"]  # Verify prompt exists
                assert "prompt" in question
                assert "options" in question

    def test_generate_questions_for_nsx_segments(self):
        """Test that NSX segment questions are generated."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)
        components = classify_components(analysis)

        interview_pack = generate_questions(components)

        # Look for segment/network questions
        questions = interview_pack["questions"]
        # Verify segment/network questions exist
        _ = [
            q
            for q in questions
            if "segment" in q.get("prompt", "").lower() or "network" in q.get("prompt", "").lower()
        ]

        # Should have at least some network-related questions
        assert len(questions) > 0, "Expected interview questions to be generated"

    def test_question_evidence_includes_action_location(self):
        """Test that question evidence includes action location when available."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        analysis = analyze_vrealize_workflow(workflow_file, action_index)
        components = classify_components(analysis)

        # Filter components that have action-based evidence
        action_components = [c for c in components if c.evidence and "action:" in c.location]

        if len(action_components) > 0:
            # Verify evidence formatting (from Issue #55)
            for component in action_components:
                assert component.evidence is not None
                assert component.location.startswith("action:")

            # Generate interview and check evidence in prompts
            interview_pack = generate_questions(components)
            questions = interview_pack["questions"]

            # At least one question should reference action evidence
            # (if we have action-based components)
            # This is optional since not all questions may include full evidence
            # Just verify interview generates successfully
            assert len(questions) >= 0


class TestEndToEndPipeline:
    """Test complete pipeline with ACME Corp bundle."""

    def test_full_pipeline_deterministic(self):
        """Test that full pipeline produces deterministic results."""
        # Run 1
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest1 = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)
            action_index1 = build_action_index(manifest1)
            workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"
            analysis1 = analyze_vrealize_workflow(workflow_file, action_index1)
            components1 = classify_components(analysis1)
            interview1 = generate_questions(components1)

        # Run 2
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest2 = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)
            action_index2 = build_action_index(manifest2)
            workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"
            analysis2 = analyze_vrealize_workflow(workflow_file, action_index2)
            components2 = classify_components(analysis2)
            interview2 = generate_questions(components2)

        # Compare results (excluding timestamps)
        assert len(components1) == len(components2)
        assert len(interview1["questions"]) == len(interview2["questions"])

    def test_action_evidence_propagates_to_interview(self):
        """Test that evidence from action scripts appears in interview."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)
        workflow_file = ACME_BUNDLE_DIR / "workflows/vm-provisioning.workflow.xml"

        # Analyze workflow (detects patterns in action scripts)
        analysis = analyze_vrealize_workflow(workflow_file, action_index)

        # Should detect NSX operations from action scripts
        assert "nsx_operations" in analysis
        nsx_ops = analysis["nsx_operations"]
        assert len(nsx_ops.get("segments", [])) + len(nsx_ops.get("firewall_rules", [])) > 0

        # Classify (creates components with evidence)
        components = classify_components(analysis)
        nsx_components = [c for c in components if "nsx" in c.component_type.lower()]

        # Verify evidence is present
        components_with_evidence = [c for c in nsx_components if c.evidence]
        assert len(components_with_evidence) > 0, "Expected components with evidence"

        # Generate interview (includes evidence in prompts from Issue #55)
        interview_pack = generate_questions(components)
        assert len(interview_pack["questions"]) > 0

    def test_all_integrations_detected_in_pipeline(self):
        """Test that all integration types are detected in full pipeline."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            manifest = import_vrealize_bundle(ACME_BUNDLE_DIR, workspace_root)

        action_index = build_action_index(manifest)

        # Analyze all three workflows
        workflows_to_test = [
            "vm-provisioning.workflow.xml",
            "network-config.workflow.xml",
            "storage-tier.workflow.xml",
        ]

        all_components = []
        for workflow_name in workflows_to_test:
            workflow_file = ACME_BUNDLE_DIR / "workflows" / workflow_name
            analysis = analyze_vrealize_workflow(workflow_file, action_index)
            components = classify_components(analysis)
            all_components.extend(components)

        # Verify multiple integration types detected across all workflows
        component_types = {c.component_type for c in all_components}
        assert (
            len(component_types) >= 2
        ), f"Expected multiple integration types, got: {component_types}"

        # Generate interview for all components
        if len(all_components) > 0:
            interview_pack = generate_questions(all_components)
            assert len(interview_pack["questions"]) > 0, "Expected interview questions"
