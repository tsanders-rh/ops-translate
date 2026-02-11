"""
Tests for vRO error handling translation to Ansible block/rescue/always.

Validates translation of try/catch/finally blocks with automatic rollback
task generation.
"""

from ops_translate.translate.vrealize_workflow import (
    JavaScriptToAnsibleTranslator,
    WorkflowItem,
)


class TestErrorHandlingDetection:
    """Tests for detecting try/catch/finally patterns."""

    def test_detect_try_catch(self):
        """Test detection of try/catch block."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    createVM();
} catch (e) {
    deleteVM();
}
"""
        error_handling = translator._extract_error_handling(script)

        assert error_handling is not None
        assert "createVM()" in error_handling["try_block"]
        assert error_handling["catch_var"] == "e"
        assert "deleteVM()" in error_handling["catch_block"]
        assert error_handling["finally_block"] is None

    def test_detect_try_catch_finally(self):
        """Test detection of try/catch/finally block."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    createResource();
} catch (e) {
    rollback();
} finally {
    cleanup();
}
"""
        error_handling = translator._extract_error_handling(script)

        assert error_handling is not None
        assert "createResource()" in error_handling["try_block"]
        assert "rollback()" in error_handling["catch_block"]
        assert "cleanup()" in error_handling["finally_block"]

    def test_no_error_handling(self):
        """Test that normal script returns None."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var vm = createVM();
System.log("VM created");
"""
        error_handling = translator._extract_error_handling(script)

        assert error_handling is None

    def test_multiline_error_handling(self):
        """Test detection with complex multi-line blocks."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    var vm = createVM(vmName, cpuCount, memoryGB);
    var ip = assignIP(vm, network);
    registerDNS(vmName, ip);
} catch (e) {
    System.error("Failed: " + e);
    if (ip) releaseIP(ip);
    if (vm) deleteVM(vm);
    throw e;
} finally {
    cleanupTempFiles();
}
"""
        error_handling = translator._extract_error_handling(script)

        assert error_handling is not None
        assert "createVM" in error_handling["try_block"]
        assert "registerDNS" in error_handling["try_block"]
        assert "releaseIP" in error_handling["catch_block"]
        assert "deleteVM" in error_handling["catch_block"]
        assert "throw" in error_handling["catch_block"]
        assert "cleanupTempFiles" in error_handling["finally_block"]


class TestBlockRescueAlwaysTranslation:
    """Tests for translating to block/rescue/always structure."""

    def test_translate_try_catch_to_block_rescue(self):
        """Test translating try/catch to block/rescue."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    System.log("Creating VM");
    var vm = createVM();
} catch (e) {
    System.log("Rolling back");
    deleteVM();
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Provision with Rollback",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate a single block task
        assert len(tasks) == 1
        block_task = tasks[0]

        # Should have block and rescue
        assert "block" in block_task
        assert "rescue" in block_task
        assert "name" in block_task

        # Block should contain try block tasks
        block_tasks = block_task["block"]
        assert len(block_tasks) > 0
        assert any("Creating VM" in str(t) for t in block_tasks)

        # Rescue should contain catch block tasks
        rescue_tasks = block_task["rescue"]
        assert len(rescue_tasks) > 0
        assert any("Rolling back" in str(t) for t in rescue_tasks)

    def test_translate_with_finally_block(self):
        """Test translating try/catch/finally to block/rescue/always."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    provisionVM();
} catch (e) {
    rollback();
} finally {
    cleanup();
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        assert len(tasks) == 1
        block_task = tasks[0]

        # Should have block, rescue, and always
        assert "block" in block_task
        assert "rescue" in block_task
        assert "always" in block_task

        # Always block should contain cleanup tasks
        always_tasks = block_task["always"]
        assert len(always_tasks) > 0

    def test_reraise_error_in_rescue(self):
        """Test that throw in catch block generates fail task."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    createResource();
} catch (e) {
    System.error("Failed: " + e);
    rollbackResource();
    throw e;
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        block_task = tasks[0]
        rescue_tasks = block_task["rescue"]

        # Should have a fail task to re-raise
        fail_tasks = [t for t in rescue_tasks if "ansible.builtin.fail" in t]
        assert len(fail_tasks) == 1
        assert "Re-raise" in fail_tasks[0]["name"]


class TestRollbackLogic:
    """Tests for automatic rollback task generation."""

    def test_rollback_preserves_catch_block_logic(self):
        """Test that catch block logic is preserved in rescue."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    var vm = createVM();
    var ip = assignIP();
} catch (e) {
    if (ip) releaseIP(ip);
    if (vm) deleteVM(vm);
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        block_task = tasks[0]
        rescue_tasks = block_task["rescue"]

        # Should include the catch block logic
        # (exact tasks depend on translation implementation)
        assert len(rescue_tasks) > 0

    def test_error_logging_in_rescue(self):
        """Test that rescue block includes error logging."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    doSomething();
} catch (e) {
    System.error("Error: " + e);
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        block_task = tasks[0]
        rescue_tasks = block_task["rescue"]

        # Should have error logging tasks
        debug_tasks = [t for t in rescue_tasks if "ansible.builtin.debug" in t]
        assert len(debug_tasks) > 0


class TestComplexErrorHandling:
    """Tests for complex error handling scenarios."""

    def test_error_handling_with_integrations(self):
        """Test error handling with integration calls."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    var vm = createVM();
    var ticket = ServiceNow.createIncident("VM provisioning", "Creating VM", "3");
} catch (e) {
    System.error("Failed: " + e);
    if (ticket) ServiceNow.updateIncident(ticket, "Failed");
    if (vm) deleteVM(vm);
    throw e;
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Provision with ServiceNow",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        block_task = tasks[0]

        # Block should contain ServiceNow integration task
        block_tasks = block_task["block"]
        # Should have integration tasks
        assert any("ServiceNow" in str(t) or "DECISION REQUIRED" in str(t) for t in block_tasks)

        # Rescue should also handle ServiceNow cleanup
        rescue_tasks = block_task["rescue"]
        assert len(rescue_tasks) > 0

    def test_no_finally_block(self):
        """Test that missing finally block works correctly."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    doSomething();
} catch (e) {
    handleError();
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        block_task = tasks[0]

        # Should have block and rescue but not always
        assert "block" in block_task
        assert "rescue" in block_task
        assert "always" not in block_task

    def test_empty_catch_block(self):
        """Test handling of empty catch block."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
try {
    doSomething();
} catch (e) {
    // Empty catch - just suppress error
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        block_task = tasks[0]

        # Should still have rescue block (at least error logging)
        assert "rescue" in block_task
        assert len(block_task["rescue"]) > 0


class TestBackwardsCompatibility:
    """Tests to ensure error handling doesn't break existing functionality."""

    def test_normal_script_without_error_handling(self):
        """Test that scripts without error handling still work."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
System.log("Starting");
var vm = createVM();
System.log("Done");
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate normal tasks (not block/rescue structure)
        assert all("block" not in t for t in tasks)
        assert all("rescue" not in t for t in tasks)

        # Should have debug tasks for System.log
        debug_tasks = [t for t in tasks if "ansible.builtin.debug" in t]
        assert len(debug_tasks) >= 2

    def test_validation_tasks_still_work(self):
        """Test that validation (throw) outside try/catch still works."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
if (cpuCount > 16) {
    throw "CPU quota exceeded";
}
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate assert task
        assert_tasks = [t for t in tasks if "ansible.builtin.assert" in t]
        assert len(assert_tasks) == 1
