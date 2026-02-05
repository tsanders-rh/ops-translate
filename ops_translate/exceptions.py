"""
Custom exceptions for ops-translate with helpful error messages.
"""


class OpsTranslateError(Exception):
    """Base exception for ops-translate errors."""

    def __init__(self, message: str, suggestion: str = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.message)

    def __str__(self):
        if self.suggestion:
            return f"{self.message}\n\nSuggestion: {self.suggestion}"
        return self.message


class WorkspaceError(OpsTranslateError):
    """Errors related to workspace management."""

    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Workspace not found or not initialized."""

    def __init__(self, path: str = None):
        message = "Not in an ops-translate workspace."
        if path:
            message = f"No ops-translate workspace found at: {path}"

        suggestion = (
            "Initialize a new workspace with:\n"
            "  ops-translate init <workspace-dir>\n\n"
            "Or navigate to an existing workspace directory."
        )
        super().__init__(message, suggestion)


class WorkspaceAlreadyExistsError(WorkspaceError):
    """Workspace already exists at target location."""

    def __init__(self, path: str):
        message = f"Workspace already exists at: {path}"
        suggestion = (
            "Choose a different directory or remove the existing workspace:\n" f"  rm -rf {path}"
        )
        super().__init__(message, suggestion)


class ImportError(OpsTranslateError):
    """Errors during file import."""

    pass


class FileNotFoundError(ImportError):
    """Source file not found during import."""

    def __init__(self, file_path: str):
        message = f"File not found: {file_path}"
        suggestion = (
            "Check that the file path is correct and the file exists:\n" f"  ls -l {file_path}"
        )
        super().__init__(message, suggestion)


class InvalidSourceTypeError(ImportError):
    """Invalid source type specified."""

    def __init__(self, source_type: str):
        message = f"Invalid source type: {source_type}"
        suggestion = (
            "Source type must be one of:\n"
            "  - powercli (for PowerCLI scripts)\n"
            "  - vrealize (for vRealize Orchestrator workflows)\n\n"
            "Example:\n"
            "  ops-translate import --source powercli --file script.ps1"
        )
        super().__init__(message, suggestion)


class IntentError(OpsTranslateError):
    """Errors related to intent extraction and management."""

    pass


class IntentValidationError(IntentError):
    """Intent YAML validation failed."""

    def __init__(self, errors: list[str], file_path: str = None):
        error_list = "\n  - ".join(errors)
        message = f"Intent validation failed with {len(errors)} error(s):\n  - {error_list}"

        if file_path:
            message = f"Intent validation failed for {file_path}:\n  - {error_list}"

        suggestion = (
            "Fix the validation errors in your intent file.\n"
            "Common issues:\n"
            "  - Missing required fields (schema_version, type, workflow_name)\n"
            "  - Invalid YAML syntax\n"
            "  - Incorrect data types\n\n"
            "You can edit the intent file with:\n"
            "  ops-translate intent edit"
        )
        super().__init__(message, suggestion)


class IntentNotFoundError(IntentError):
    """Intent file not found."""

    def __init__(self, intent_type: str = None):
        if intent_type:
            message = f"Intent file not found: intent/{intent_type}.intent.yaml"
        else:
            message = "No intent files found in workspace."

        suggestion = (
            "Extract intent from your imported sources first:\n"
            "  ops-translate intent extract\n\n"
            "Or check that you've imported source files:\n"
            "  ops-translate import --source powercli --file <file>"
        )
        super().__init__(message, suggestion)


class MergeConflictError(IntentError):
    """Conflicts detected during intent merge."""

    def __init__(self, conflicts: list[str]):
        conflict_list = "\n  - ".join(conflicts)
        message = f"Merge conflicts detected ({len(conflicts)} conflict(s)):\n  - {conflict_list}"

        suggestion = (
            "Review conflicts in intent/conflicts.md and resolve manually:\n"
            "  cat intent/conflicts.md\n\n"
            "Then either:\n"
            "  1. Edit source intent files to resolve conflicts:\n"
            "     ops-translate intent edit --file intent/powercli.intent.yaml\n\n"
            "  2. Force merge to accept conflicts:\n"
            "     ops-translate intent merge --force"
        )
        super().__init__(message, suggestion)


class LLMError(OpsTranslateError):
    """Errors related to LLM provider operations."""

    pass


class LLMProviderNotAvailableError(LLMError):
    """LLM provider not available (missing API key, etc.)."""

    def __init__(self, provider_name: str, api_key_env: str = None):
        message = f"LLM provider '{provider_name}' is not available."

        if api_key_env:
            suggestion = (
                f"Set the API key environment variable:\n"
                f"  export {api_key_env}=<your-api-key>\n\n"
                f"Or use mock provider for testing:\n"
                f"  Edit ops-translate.yaml and set:\n"
                f"    llm:\n"
                f"      provider: mock"
            )
        else:
            suggestion = (
                "Check your ops-translate.yaml configuration.\n"
                "Ensure the provider is correctly configured."
            )
        super().__init__(message, suggestion)


class LLMAPIError(LLMError):
    """LLM API call failed."""

    def __init__(self, provider_name: str, error_message: str, retry_count: int = 0):
        message = f"{provider_name} API call failed: {error_message}"

        if retry_count > 0:
            message += f" (after {retry_count} retries)"

        suggestion = (
            "This could be due to:\n"
            "  - Network connectivity issues\n"
            "  - API rate limiting\n"
            "  - Invalid API key\n"
            "  - Service outage\n\n"
            "Try:\n"
            "  1. Check your internet connection\n"
            "  2. Verify your API key is valid\n"
            "  3. Wait a few minutes and retry\n"
            "  4. Use --no-ai flag for template-based generation:\n"
            "     ops-translate intent extract --no-ai"
        )
        super().__init__(message, suggestion)


class LLMResponseParsingError(LLMError):
    """Failed to parse LLM response."""

    def __init__(self, error_details: str):
        message = f"Failed to parse LLM response: {error_details}"

        suggestion = (
            "The LLM returned an unexpected format.\n"
            "Try:\n"
            "  1. Re-run the extraction (LLM responses can vary)\n"
            "  2. Use a different model:\n"
            "     Edit ops-translate.yaml and change llm.model\n"
            "  3. Use template-based extraction:\n"
            "     ops-translate intent extract --no-ai"
        )
        super().__init__(message, suggestion)


class GenerationError(OpsTranslateError):
    """Errors during artifact generation."""

    pass


class ProfileNotFoundError(GenerationError):
    """Profile not found in configuration."""

    def __init__(self, profile_name: str, available_profiles: list[str] = None):
        message = f"Profile '{profile_name}' not found in configuration."

        if available_profiles:
            profiles_list = "\n  - ".join(available_profiles)
            suggestion = (
                f"Available profiles:\n  - {profiles_list}\n\n"
                "Use one of these profiles:\n"
                f"  ops-translate generate --profile {available_profiles[0]}\n\n"
                "Or add a new profile to ops-translate.yaml"
            )
        else:
            suggestion = (
                "Add profiles to your ops-translate.yaml:\n"
                "  profiles:\n"
                "    lab:\n"
                "      default_namespace: virt-lab\n"
                "      default_network: lab-network\n"
                "      default_storage_class: nfs"
            )
        super().__init__(message, suggestion)


class ValidationError(OpsTranslateError):
    """Errors during validation."""

    pass


class ArtifactValidationError(ValidationError):
    """Generated artifact validation failed."""

    def __init__(self, artifact_path: str, errors: list[str]):
        error_list = "\n  - ".join(errors)
        message = f"Validation failed for {artifact_path}:\n  - {error_list}"

        suggestion = (
            "The generated artifact has issues.\n"
            "Try:\n"
            "  1. Review the intent file for correctness\n"
            "  2. Re-generate with different settings\n"
            "  3. Report this issue if it persists:\n"
            "     https://github.com/tsanders-rh/ops-translate/issues"
        )
        super().__init__(message, suggestion)


class ConfigurationError(OpsTranslateError):
    """Configuration file errors."""

    pass


class InvalidConfigError(ConfigurationError):
    """Configuration file is invalid."""

    def __init__(self, error_details: str):
        message = f"Invalid configuration file: {error_details}"

        suggestion = (
            "Fix the ops-translate.yaml file.\n"
            "You can regenerate the default configuration:\n"
            "  mv ops-translate.yaml ops-translate.yaml.backup\n"
            "  ops-translate init .\n\n"
            "Then merge your settings back from the backup."
        )
        super().__init__(message, suggestion)


class RetryableError(OpsTranslateError):
    """Error that should be retried."""

    def __init__(self, original_error: Exception, attempt: int, max_attempts: int):
        self.original_error = original_error
        self.attempt = attempt
        self.max_attempts = max_attempts

        message = f"Operation failed (attempt {attempt}/{max_attempts}): " f"{str(original_error)}"
        super().__init__(message)


def format_error_for_cli(error: Exception) -> str:
    """
    Format an exception for CLI display with helpful information.

    Args:
        error: The exception to format

    Returns:
        Formatted error message string
    """
    if isinstance(error, OpsTranslateError):
        # Custom errors have helpful messages and suggestions
        output = f"[red]Error:[/red] {error.message}"
        if error.suggestion:
            output += f"\n\n[yellow]{error.suggestion}[/yellow]"
        return output
    else:
        # Generic errors
        return f"[red]Error:[/red] {str(error)}"
