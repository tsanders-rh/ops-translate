"""
Tests for profile-driven adapter selection in vRealize workflow translation.

Validates that integrations generate:
- include_tasks to adapters when profile is configured
- BLOCKED fail tasks when profile is missing
"""

import pytest

from ops_translate.models.profile import (
    DNSConfig,
    IPAMConfig,
    ITSMConfig,
    NetworkSecurityConfig,
    ProfileSchema,
)
from ops_translate.translate.vrealize_workflow import (
    JavaScriptToAnsibleTranslator,
    WorkflowItem,
)


class TestProfileDrivenAdapterSelection:
    """Test profile-driven adapter selection for integrations."""

    def test_servicenow_without_profile_generates_blocked(self):
        """Test that ServiceNow integration without profile generates BLOCKED task."""
        # Create translator without profile
        translator = JavaScriptToAnsibleTranslator(profile=None)

        # Create a workflow item with ServiceNow integration call
        script = """
var incident = ServiceNow.createIncident(
    "Test incident",
    "Description of the incident",
    "3"
);
"""
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Create ServiceNow Incident",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the ServiceNow task
        snow_tasks = [t for t in tasks if "servicenow" in t.get("name", "").lower()]
        assert (
            len(snow_tasks) > 0
        ), f"Should generate a ServiceNow task. Got tasks: {[t.get('name') for t in tasks]}"

        snow_task = snow_tasks[0]
        assert "BLOCKED" in snow_task["name"], "Task should be BLOCKED without profile"
        assert "ansible.builtin.fail" in snow_task, "Should use fail module"
        assert "itsm" in snow_task["ansible.builtin.fail"]["msg"].lower()

    def test_servicenow_with_profile_generates_adapter_include(self):
        """Test that ServiceNow integration with profile generates adapter include."""
        # Create profile with ITSM configuration
        profile = ProfileSchema(
            name="test-profile",
            itsm=ITSMConfig(
                provider="servicenow",
                endpoint="https://test.service-now.com",
                username_var="snow_user",
                password_var="snow_pass",
            ),
        )

        # Create translator with profile
        translator = JavaScriptToAnsibleTranslator(profile=profile)

        # Create a workflow item with ServiceNow integration call
        script = """
var incident = ServiceNow.createIncident(
    "Test incident",
    "Description of the incident",
    "3"
);
"""
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Create ServiceNow Incident",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the ServiceNow task
        snow_tasks = [t for t in tasks if "servicenow" in t.get("name", "").lower()]
        assert (
            len(snow_tasks) > 0
        ), f"Should generate a ServiceNow task. Got tasks: {[t.get('name') for t in tasks]}"

        snow_task = snow_tasks[0]
        assert "BLOCKED" not in snow_task["name"], "Task should not be BLOCKED with profile"
        assert (
            "ansible.builtin.include_tasks" in snow_task
        ), f"Should use include_tasks module. Got: {snow_task}"
        assert (
            "servicenow/create_incident.yml" in snow_task["ansible.builtin.include_tasks"]["file"]
        )

    def test_nsx_without_profile_generates_blocked(self):
        """Test that NSX integration without profile generates BLOCKED task."""
        # Create translator without profile
        translator = JavaScriptToAnsibleTranslator(profile=None)

        # Create a workflow item with NSX integration call
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Create NSX Segment",
            script="NSX.createSegment('test-segment', 'overlay-tz');",
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the NSX task
        nsx_tasks = [t for t in tasks if "Nsxt" in t.get("name", "") or "NSX" in t.get("name", "")]
        assert len(nsx_tasks) > 0, "Should generate an NSX task"

        nsx_task = nsx_tasks[0]
        assert "BLOCKED" in nsx_task["name"], "Task should be BLOCKED without profile"
        assert "ansible.builtin.fail" in nsx_task, "Should use fail module"
        assert "network_security" in nsx_task["ansible.builtin.fail"]["msg"].lower()

    def test_nsx_with_profile_generates_adapter_include(self):
        """Test that NSX integration with profile generates adapter include."""
        # Create profile with network security configuration
        profile = ProfileSchema(
            name="test-profile",
            network_security=NetworkSecurityConfig(
                model="networkpolicy", default_isolation="namespace"
            ),
        )

        # Create translator with profile
        translator = JavaScriptToAnsibleTranslator(profile=profile)

        # Create a workflow item with NSX integration call
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Create NSX Segment",
            script="NSX.createSegment('test-segment', 'overlay-tz');",
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the NSX task
        nsx_tasks = [t for t in tasks if "Nsxt" in t.get("name", "") or "NSX" in t.get("name", "")]
        assert len(nsx_tasks) > 0, "Should generate an NSX task"

        nsx_task = nsx_tasks[0]
        assert "BLOCKED" not in nsx_task["name"], "Task should not be BLOCKED with profile"
        assert "ansible.builtin.include_tasks" in nsx_task, "Should use include_tasks module"
        assert "nsx/create_segment.yml" in nsx_task["ansible.builtin.include_tasks"]["file"]

    def test_dns_without_profile_generates_blocked(self):
        """Test that DNS integration without profile generates BLOCKED task."""
        # Create translator without profile
        translator = JavaScriptToAnsibleTranslator(profile=None)

        # Create a workflow item with Infoblox DNS integration call
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Create DNS Record",
            script="Infoblox.createHostRecord('test.example.com', '10.0.0.100');",
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the Infoblox task
        dns_tasks = [t for t in tasks if "Infoblox" in t.get("name", "")]
        assert len(dns_tasks) > 0, "Should generate an Infoblox task"

        dns_task = dns_tasks[0]
        assert "BLOCKED" in dns_task["name"], "Task should be BLOCKED without profile"
        assert "ansible.builtin.fail" in dns_task, "Should use fail module"
        assert "dns" in dns_task["ansible.builtin.fail"]["msg"].lower()

    def test_dns_with_profile_generates_adapter_include(self):
        """Test that DNS integration with profile generates adapter include."""
        # Create profile with DNS configuration
        profile = ProfileSchema(
            name="test-profile",
            dns=DNSConfig(
                provider="infoblox",
                endpoint="https://infoblox.example.com",
                credentials_var="infoblox_creds",
            ),
        )

        # Create translator with profile
        translator = JavaScriptToAnsibleTranslator(profile=profile)

        # Create a workflow item with Infoblox DNS integration call
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Create DNS Record",
            script="Infoblox.createHostRecord('test.example.com', '10.0.0.100');",
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the Infoblox task
        dns_tasks = [t for t in tasks if "Infoblox" in t.get("name", "")]
        assert len(dns_tasks) > 0, "Should generate an Infoblox task"

        dns_task = dns_tasks[0]
        assert "BLOCKED" not in dns_task["name"], "Task should not be BLOCKED with profile"
        assert "ansible.builtin.include_tasks" in dns_task, "Should use include_tasks module"
        assert "dns/create_record.yml" in dns_task["ansible.builtin.include_tasks"]["file"]

    def test_ipam_without_profile_generates_blocked(self):
        """Test that IPAM integration without profile generates BLOCKED task."""
        # Create translator without profile
        translator = JavaScriptToAnsibleTranslator(profile=None)

        # Create a workflow item with Infoblox IPAM integration call
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Get Next IP",
            script="Infoblox.getNextAvailableIP('10.0.0.0/24');",
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the Infoblox task
        ipam_tasks = [t for t in tasks if "Infoblox" in t.get("name", "")]
        assert len(ipam_tasks) > 0, "Should generate an Infoblox task"

        ipam_task = ipam_tasks[0]
        assert "BLOCKED" in ipam_task["name"], "Task should be BLOCKED without profile"
        assert "ansible.builtin.fail" in ipam_task, "Should use fail module"
        assert "ipam" in ipam_task["ansible.builtin.fail"]["msg"].lower()

    def test_ipam_with_profile_generates_adapter_include(self):
        """Test that IPAM integration with profile generates adapter include."""
        # Create profile with IPAM configuration
        profile = ProfileSchema(
            name="test-profile",
            ipam=IPAMConfig(
                provider="infoblox",
                endpoint="https://infoblox.example.com",
                credentials_var="infoblox_creds",
            ),
        )

        # Create translator with profile
        translator = JavaScriptToAnsibleTranslator(profile=profile)

        # Create a workflow item with Infoblox IPAM integration call
        item = WorkflowItem(
            name="test-item",
            item_type="task",
            display_name="Get Next IP",
            script="Infoblox.getNextAvailableIP('10.0.0.0/24');",
            in_bindings=[],
            out_bindings=[],
            out_name=None,
            position=(0, 0),
        )

        # Translate the script
        tasks = translator.translate_script(item.script, item)

        # Find the Infoblox task
        ipam_tasks = [t for t in tasks if "Infoblox" in t.get("name", "")]
        assert len(ipam_tasks) > 0, "Should generate an Infoblox task"

        ipam_task = ipam_tasks[0]
        assert "BLOCKED" not in ipam_task["name"], "Task should not be BLOCKED with profile"
        assert "ansible.builtin.include_tasks" in ipam_task, "Should use include_tasks module"
        assert "ipam/reserve_ip.yml" in ipam_task["ansible.builtin.include_tasks"]["file"]

    def test_profile_has_config_method(self):
        """Test _profile_has_config helper method."""
        # Create profile with various configurations
        profile = ProfileSchema(
            name="test-profile",
            itsm=ITSMConfig(provider="servicenow", endpoint="https://test.service-now.com"),
            network_security=NetworkSecurityConfig(model="networkpolicy"),
        )

        translator = JavaScriptToAnsibleTranslator(profile=profile)

        # Test positive cases
        assert translator._profile_has_config(["profile.itsm.provider"])
        assert translator._profile_has_config(["profile.itsm.endpoint"])
        assert translator._profile_has_config(["profile.network_security.model"])
        assert translator._profile_has_config(["profile.itsm.provider", "profile.itsm.endpoint"])

        # Test negative cases
        assert not translator._profile_has_config(["profile.dns.provider"])
        assert not translator._profile_has_config(["profile.ipam.endpoint"])
        assert not translator._profile_has_config(["profile.itsm.provider", "profile.dns.provider"])

    def test_profile_has_config_without_profile(self):
        """Test _profile_has_config returns False when no profile."""
        translator = JavaScriptToAnsibleTranslator(profile=None)

        assert not translator._profile_has_config(["profile.itsm.provider"])
        assert not translator._profile_has_config(["profile.network_security.model"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
