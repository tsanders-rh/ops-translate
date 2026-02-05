"""
Output format handlers for different deployment patterns.

Supports: YAML (default), JSON, Kustomize, ArgoCD
"""

import json
from pathlib import Path

import yaml
from rich.console import Console

from ops_translate.util.files import ensure_dir, write_text

console = Console()


class OutputFormat:
    """Base class for output format handlers."""

    def __init__(self, workspace_root: Path):
        """
        Initialize output format handler.

        Args:
            workspace_root: Path to workspace directory
        """
        self.workspace_root = workspace_root
        self.output_dir = workspace_root / "output"

    def write(self, content: dict, profile: str, context: dict):
        """
        Write output in specific format.

        Args:
            content: Dictionary of file_path -> content
            profile: Profile name being used
            context: Template context with intent/profile data
        """
        raise NotImplementedError


class YAMLFormat(OutputFormat):
    """Standard YAML output (default)."""

    def write(self, content: dict, profile: str, context: dict):
        """Write standard YAML files."""
        for file_path, file_content in content.items():
            full_path = self.output_dir / file_path
            ensure_dir(full_path.parent)
            write_text(full_path, file_content)
            console.print(f"[dim]  Generated: {file_path}[/dim]")


class JSONFormat(OutputFormat):
    """JSON output for API integration and programmatic use."""

    def write(self, content: dict, profile: str, context: dict):
        """Convert YAML to JSON and write."""
        json_dir = self.output_dir / "json"
        ensure_dir(json_dir)

        for file_path, file_content in content.items():
            if file_path.endswith((".yaml", ".yml")):
                # Parse YAML and convert to JSON
                try:
                    # Handle multi-document YAML
                    docs = list(yaml.safe_load_all(file_content))

                    # Generate JSON filename
                    json_filename = Path(file_path).stem + ".json"
                    json_path = json_dir / json_filename

                    if len(docs) == 1:
                        # Single document - write as single JSON
                        json_content = json.dumps(docs[0], indent=2)
                    else:
                        # Multiple documents - write as JSON array
                        json_content = json.dumps(docs, indent=2)

                    write_text(json_path, json_content)
                    console.print(f"[dim]  Generated: json/{json_filename}[/dim]")

                except yaml.YAMLError as e:
                    console.print(f"[yellow]⚠ Could not convert {file_path} to JSON: {e}[/yellow]")


class KustomizeFormat(OutputFormat):
    """Kustomize/GitOps output with base and overlays."""

    def write(self, content: dict, profile: str, context: dict):
        """Write Kustomize structure with base and overlays."""
        # Create base directory
        base_dir = self.output_dir / "base"
        ensure_dir(base_dir)

        # Write base resources
        resources = []
        for file_path, file_content in content.items():
            if file_path.endswith((".yaml", ".yml")) and "ansible" not in file_path:
                # Copy to base
                base_file = base_dir / Path(file_path).name
                write_text(base_file, file_content)
                resources.append(Path(file_path).name)

        # Create base kustomization.yaml
        base_kustomization = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": resources,
            "commonLabels": {
                "app": context["intent"].get("workflow_name", "ops-translate"),
                "managed-by": "ops-translate",
            },
        }

        write_text(base_dir / "kustomization.yaml", yaml.dump(base_kustomization))
        console.print("[dim]  Generated: base/kustomization.yaml[/dim]")

        # Create overlays for different environments
        for env in ["dev", "staging", "prod"]:
            self._create_overlay(env, context, is_prod=(env == "prod"))

    def _create_overlay(self, env: str, context: dict, is_prod: bool = False):
        """Create overlay for specific environment."""
        overlay_dir = self.output_dir / "overlays" / env
        ensure_dir(overlay_dir)

        # Determine resource adjustments based on environment
        if env == "dev":
            memory = "2Gi"
            cpu = 1
        elif env == "staging":
            memory = "4Gi"
            cpu = 2
        else:  # prod
            memory = "8Gi"
            cpu = 4

        # Create overlay kustomization
        overlay_kustomization = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "bases": ["../../base"],
            "commonLabels": {
                "environment": env,
            },
            "patches": [
                {
                    "target": {
                        "kind": "VirtualMachine",
                    },
                    "patch": f"""
- op: replace
  path: /spec/template/spec/domain/resources/requests/memory
  value: {memory}
- op: replace
  path: /spec/template/spec/domain/resources/requests/cpu
  value: {cpu}
- op: add
  path: /metadata/labels/environment
  value: {env}
""",
                }
            ],
        }

        write_text(
            overlay_dir / "kustomization.yaml",
            yaml.dump(overlay_kustomization, sort_keys=False),
        )
        console.print(f"[dim]  Generated: overlays/{env}/kustomization.yaml[/dim]")


class ArgoCDFormat(OutputFormat):
    """ArgoCD Application manifests for GitOps deployment."""

    def write(self, content: dict, profile: str, context: dict):
        """Write ArgoCD Application resources."""
        # First create Kustomize structure (ArgoCD uses it)
        kustomize = KustomizeFormat(self.workspace_root)
        kustomize.write(content, profile, context)

        # Create ArgoCD applications directory
        apps_dir = self.output_dir / "argocd"
        ensure_dir(apps_dir)

        workflow_name = context["intent"].get("workflow_name", "vm-migration")

        # Create applications for each environment
        for env in ["dev", "staging", "prod"]:
            app = self._create_application(env, workflow_name, context)
            app_file = apps_dir / f"{env}-application.yaml"
            write_text(app_file, yaml.dump(app, sort_keys=False))
            console.print(f"[dim]  Generated: argocd/{env}-application.yaml[/dim]")

        # Create AppProject
        project = self._create_project(workflow_name)
        write_text(
            apps_dir / "project.yaml",
            yaml.dump(project, sort_keys=False),
        )
        console.print("[dim]  Generated: argocd/project.yaml[/dim]")

    def _create_application(self, env: str, workflow_name: str, context: dict) -> dict:
        """Create ArgoCD Application manifest."""
        # Determine sync policy based on environment
        if env == "dev":
            automated = {"prune": True, "selfHeal": True}
        elif env == "staging":
            automated = {"prune": True, "selfHeal": False}
        else:  # prod
            automated = None  # Manual sync for prod

        app = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": f"{workflow_name}-{env}",
                "namespace": "argocd",
                "labels": {
                    "environment": env,
                    "workflow": workflow_name,
                },
            },
            "spec": {
                "project": workflow_name,
                "source": {
                    "repoURL": "https://github.com/YOUR-ORG/YOUR-REPO",  # Placeholder
                    "path": f"output/overlays/{env}",
                    "targetRevision": "main",
                },
                "destination": {
                    "server": "https://kubernetes.default.svc",
                    "namespace": context["profile"].get("default_namespace", f"{env}-vms"),
                },
                "syncPolicy": {
                    "syncOptions": ["CreateNamespace=true"],
                },
            },
        }

        if automated:
            app["spec"]["syncPolicy"]["automated"] = automated

        return app

    def _create_project(self, workflow_name: str) -> dict:
        """Create ArgoCD AppProject manifest."""
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "AppProject",
            "metadata": {
                "name": workflow_name,
                "namespace": "argocd",
            },
            "spec": {
                "description": f"VMware migration project: {workflow_name}",
                "sourceRepos": ["*"],
                "destinations": [
                    {
                        "namespace": "*",
                        "server": "https://kubernetes.default.svc",
                    }
                ],
                "clusterResourceWhitelist": [
                    {
                        "group": "*",
                        "kind": "*",
                    }
                ],
            },
        }


def get_format_handler(format_name: str, workspace_root: Path) -> OutputFormat:
    """
    Get output format handler by name.

    Args:
        format_name: Format name (yaml, json, kustomize, argocd)
        workspace_root: Workspace root directory

    Returns:
        OutputFormat instance

    Raises:
        ValueError: If format name is invalid
    """
    formats = {
        "yaml": YAMLFormat,
        "json": JSONFormat,
        "kustomize": KustomizeFormat,
        "gitops": KustomizeFormat,  # Alias
        "argocd": ArgoCDFormat,
    }

    if format_name not in formats:
        raise ValueError(
            f"Invalid format: {format_name}. "
            f"Valid formats: {', '.join(formats.keys())}"
        )

    return formats[format_name](workspace_root)
