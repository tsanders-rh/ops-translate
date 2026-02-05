"""
Template loading and rendering utilities using Jinja2.
"""

import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

# Get project root to find default templates
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TemplateLoader:
    """
    Loads and renders Jinja2 templates.

    Supports custom templates in workspace with fallback to defaults.
    """

    def __init__(self, workspace_root: Path):
        """
        Initialize template loader.

        Args:
            workspace_root: Path to workspace directory
        """
        self.workspace_root = workspace_root
        self.workspace_templates = workspace_root / "templates"
        self.default_templates = PROJECT_ROOT / "templates"
        self._env: Environment | None = None
        self._template_cache: dict[str, Template] = {}

    def has_custom_templates(self) -> bool:
        """Check if workspace has custom templates."""
        return self.workspace_templates.exists()

    @property
    def env(self) -> Environment:
        """
        Get or create Jinja2 environment (cached).

        Returns:
            Cached Jinja2 Environment configured for template loading
        """
        if self._env is None:
            template_dirs = []

            # Check workspace templates first
            if self.workspace_templates.exists():
                template_dirs.append(str(self.workspace_templates))

            # Fall back to package templates
            if self.default_templates.exists():
                template_dirs.append(str(self.default_templates))

            if not template_dirs:
                raise FileNotFoundError("No template directories found")

            self._env = Environment(
                loader=FileSystemLoader(template_dirs),
                trim_blocks=True,
                lstrip_blocks=True,
            )

            # Add custom filters
            self._env.filters["to_yaml_value"] = lambda x: (
                str(x).lower() if isinstance(x, bool) else str(x)
            )

        return self._env

    def get_template_path(self, template_name: str) -> Path:
        """
        Get path to template file, preferring workspace over defaults.

        Args:
            template_name: Template name (e.g., "ansible/playbook.yml.j2")

        Returns:
            Path to template file
        """
        # Check workspace first
        workspace_template = self.workspace_templates / template_name
        if workspace_template.exists():
            return workspace_template

        # Fall back to defaults
        default_template = self.default_templates / template_name
        if default_template.exists():
            return default_template

        raise FileNotFoundError(f"Template '{template_name}' not found in workspace or defaults")

    def load_template(self, template_name: str) -> Template:
        """
        Load a Jinja2 template with caching.

        Args:
            template_name: Template name (e.g., "ansible/playbook.yml.j2")

        Returns:
            Cached Jinja2 Template object
        """
        if template_name not in self._template_cache:
            # Verify template exists (will raise if not found)
            self.get_template_path(template_name)
            # Load template using cached environment
            self._template_cache[template_name] = self.env.get_template(template_name)

        return self._template_cache[template_name]

    def render_template(self, template_name: str, context: dict, output_file: Path) -> None:
        """
        Render a template and write to file.

        Args:
            template_name: Template name (e.g., "ansible/playbook.yml.j2")
            context: Dictionary of template variables
            output_file: Path to write rendered output
        """
        template = self.load_template(template_name)

        # Add timestamp to context
        if "timestamp" not in context:
            context["timestamp"] = datetime.now().isoformat()

        # Render template
        rendered = template.render(**context)

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        output_file.write_text(rendered)

    def copy_default_templates_to_workspace(self) -> None:
        """
        Copy default templates to workspace for customization.

        Creates templates/ directory in workspace with all default templates.
        """
        if not self.default_templates.exists():
            raise FileNotFoundError(f"Default templates not found at {self.default_templates}")

        # Copy entire templates directory
        if self.workspace_templates.exists():
            # Backup existing templates
            backup_dir = self.workspace_root / "templates.backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(str(self.workspace_templates), str(backup_dir))

        shutil.copytree(str(self.default_templates), str(self.workspace_templates))

    def list_available_templates(self) -> list[tuple[str, str]]:
        """
        List all available templates.

        Returns:
            List of (source, template_name) tuples where source is "workspace" or "default"
        """
        templates = []

        # Check workspace templates
        if self.workspace_templates.exists():
            for template_file in self.workspace_templates.rglob("*.j2"):
                rel_path = template_file.relative_to(self.workspace_templates)
                templates.append(("workspace", str(rel_path)))

        # Check default templates
        if self.default_templates.exists():
            for template_file in self.default_templates.rglob("*.j2"):
                rel_path = template_file.relative_to(self.default_templates)
                # Only add if not already in workspace
                if not any(t[1] == str(rel_path) for t in templates):
                    templates.append(("default", str(rel_path)))

        return templates


def create_template_context(intent: dict, profile: dict, profile_name: str) -> dict:
    """
    Create template rendering context from intent and profile.

    Args:
        intent: Intent data dictionary
        profile: Profile configuration
        profile_name: Name of the profile being used

    Returns:
        Dictionary of template variables
    """
    return {
        "intent": intent.get("intent", {}),
        "profile": profile,
        "profile_name": profile_name,
        "sources": intent.get("sources", []),
        "schema_version": intent.get("schema_version", 1),
        "cloud_init_data": "",  # Placeholder for cloud-init
    }
