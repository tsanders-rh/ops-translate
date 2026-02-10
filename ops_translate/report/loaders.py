"""
Data loading components for report generation.

This module provides decoupled components for locating, loading, and processing
report data files. This separation of concerns improves testability and maintainability.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

from ops_translate.workspace import Workspace

logger = logging.getLogger(__name__)


class ReportFileLocator:
    """
    Locates report-related files in workspace.

    Knows WHERE files are located but not HOW to load them.
    This separation allows for:
    - Easy testing (mock file locations)
    - Flexibility (change file structure without touching loaders)
    - Clarity (one place to look for file paths)

    Example:
        >>> locator = ReportFileLocator(workspace)
        >>> if gaps_file := locator.gaps_file():
        ...     # Load gaps data
        ...     pass
    """

    def __init__(self, workspace: Workspace):
        """
        Initialize file locator with workspace.

        Args:
            workspace: Workspace instance containing report files
        """
        self.workspace = workspace

    def gaps_file(self) -> Path | None:
        """
        Locate gaps.json file.

        Returns:
            Path to gaps.json if it exists, None otherwise
        """
        path = self.workspace.root / "intent/gaps.json"
        return path if path.exists() else None

    def recommendations_file(self) -> Path | None:
        """
        Locate recommendations.json file.

        Returns:
            Path to recommendations.json if it exists, None otherwise
        """
        path = self.workspace.root / "intent/recommendations.json"
        return path if path.exists() else None

    def decisions_file(self) -> Path | None:
        """
        Locate decisions.yaml file.

        Returns:
            Path to decisions.yaml if it exists, None otherwise
        """
        path = self.workspace.root / "intent/decisions.yaml"
        return path if path.exists() else None

    def questions_file(self) -> Path | None:
        """
        Locate questions.json file.

        Returns:
            Path to questions.json if it exists, None otherwise
        """
        path = self.workspace.root / "intent/questions.json"
        return path if path.exists() else None

    def intent_file(self) -> Path | None:
        """
        Locate merged intent.yaml file.

        Returns:
            Path to intent.yaml if it exists, None otherwise
        """
        path = self.workspace.root / "intent/intent.yaml"
        return path if path.exists() else None

    def assumptions_file(self) -> Path | None:
        """
        Locate assumptions.md file.

        Returns:
            Path to assumptions.md if it exists, None otherwise
        """
        path = self.workspace.root / "intent/assumptions.md"
        return path if path.exists() else None

    def conflicts_file(self) -> Path | None:
        """
        Locate conflicts.md file.

        Returns:
            Path to conflicts.md if it exists, None otherwise
        """
        path = self.workspace.root / "intent/conflicts.md"
        return path if path.exists() else None

    def input_files(self, pattern: str = "*") -> list[Path]:
        """
        Locate input files matching pattern.

        Args:
            pattern: Glob pattern for matching files (default: all files)

        Returns:
            List of paths to matching input files
        """
        input_dir = self.workspace.root / "input"
        if not input_dir.exists():
            return []
        return sorted(input_dir.glob(pattern))


class ReportDataLoader:
    """
    Loads and parses report data files.

    Knows HOW to load different file formats but not WHERE they are located.
    This separation allows for:
    - Consistent error handling across all file types
    - Easy testing (pass in-memory file paths or mock paths)
    - Reusability (use in different contexts)

    Example:
        >>> loader = ReportDataLoader()
        >>> if gaps_file:
        ...     gaps_data = loader.load_json(gaps_file)
    """

    def load_json(self, file_path: Path) -> dict[str, Any]:
        """
        Load and parse JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data as dict, or empty dict on error

        Example:
            >>> loader = ReportDataLoader()
            >>> data = loader.load_json(Path("gaps.json"))
        """
        try:
            return cast(dict[str, Any], json.loads(file_path.read_text()))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON file {file_path}: {e}")
            return {}
        except OSError as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return {}

    def load_yaml(self, file_path: Path) -> dict[str, Any]:
        """
        Load and parse YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML data as dict, or empty dict on error

        Example:
            >>> loader = ReportDataLoader()
            >>> data = loader.load_yaml(Path("decisions.yaml"))
        """
        try:
            return cast(dict[str, Any], yaml.safe_load(file_path.read_text()))
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML file {file_path}: {e}")
            return {}
        except OSError as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return {}

    def load_text(self, file_path: Path) -> str:
        """
        Load text file.

        Args:
            file_path: Path to text file

        Returns:
            File contents as string, or empty string on error

        Example:
            >>> loader = ReportDataLoader()
            >>> content = loader.load_text(Path("assumptions.md"))
        """
        try:
            return file_path.read_text().strip()
        except OSError as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return ""


class ReportContextBuilder:
    """
    Builds template context from loaded data.

    Knows HOW to assemble context from data but not WHERE data comes from.
    This separation allows for:
    - Easy testing (pass in mock data)
    - Flexibility (use different data sources)
    - Clarity (one place for context assembly logic)

    Example:
        >>> builder = ReportContextBuilder()
        >>> context = builder.build(
        ...     workspace_name="my-workspace",
        ...     workspace_path="/path/to/workspace",
        ...     profile="lab",
        ...     profile_config={"namespace": "virt-lab"},
        ...     gaps_data=gaps,
        ...     recommendations_data=recommendations,
        ...     # ... other data
        ... )
    """

    def build(
        self,
        workspace_name: str,
        workspace_path: str,
        profile: str,
        profile_config: dict[str, Any],
        gaps_data: dict[str, Any] | None = None,
        recommendations_data: dict[str, Any] | None = None,
        decisions_data: dict[str, Any] | None = None,
        questions_data: dict[str, Any] | None = None,
        intent_data: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
        assumptions_md: str | None = None,
        conflicts_md: str | None = None,
        artifacts: dict[str, Any] | None = None,
        executive_summary: str | None = None,
        consolidated_supported: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Build report template context from loaded data.

        Args:
            workspace_name: Name of the workspace
            workspace_path: Path to the workspace
            profile: Name of the profile being used
            profile_config: Configuration dict for the profile
            gaps_data: Gap analysis data (optional)
            recommendations_data: Expert recommendations data (optional)
            decisions_data: User decisions data (optional)
            questions_data: Interview questions data (optional)
            intent_data: Parsed intent data (optional)
            sources: List of source files (optional)
            assumptions_md: Markdown assumptions content (optional)
            conflicts_md: Markdown conflicts content (optional)
            artifacts: Generated artifacts info (optional)
            executive_summary: Executive summary text (optional)
            consolidated_supported: Consolidated SUPPORTED patterns (optional)

        Returns:
            Dictionary with all context data for template rendering

        Example:
            >>> builder = ReportContextBuilder()
            >>> context = builder.build(
            ...     workspace_name="demo",
            ...     workspace_path="/workspace/demo",
            ...     profile="lab",
            ...     profile_config={"namespace": "virt-lab"},
            ...     gaps_data=gaps,
            ... )
        """
        context: dict[str, Any] = {
            "workspace": {
                "name": workspace_name,
                "path": workspace_path,
                "timestamp": datetime.now().isoformat(),
            },
            "profile": {
                "name": profile,
                "config": profile_config,
            },
            "sources": sources or [],
            "intent": intent_data,
            "gaps": gaps_data,
            "recommendations": recommendations_data,
            "decisions": decisions_data,
            "questions": questions_data,
            "assumptions_md": assumptions_md,
            "conflicts_md": conflicts_md,
            "artifacts": artifacts or {},
            "summary": {},  # Will be populated from gaps
        }

        # Build summary from gaps if available
        if gaps_data:
            context["summary"] = gaps_data.get("summary", {})
        else:
            # Fallback summary if no gaps
            context["summary"] = {
                "total_components": 0,
                "overall_assessment": "UNKNOWN",
                "counts": {"SUPPORTED": 0, "PARTIAL": 0, "BLOCKED": 0, "MANUAL": 0},
                "has_blocking_issues": False,
                "requires_manual_work": False,
            }

        # Add executive summary (passed in or will be generated by html.py)
        context["executive_summary"] = executive_summary or ""

        # Add consolidated supported patterns (passed in or will be generated by html.py)
        context["consolidated_supported"] = consolidated_supported or []

        # Build questions lookup by component location
        context["questions_by_location"] = self._build_questions_lookup(questions_data)

        # Build recommendations lookup by component name
        context["recommendations_by_component"] = self._build_recommendations_lookup(
            recommendations_data
        )

        return context

    def _build_questions_lookup(
        self, questions_data: dict[str, Any] | None
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Build lookup dict of questions by component location.

        Args:
            questions_data: Questions data dict with 'questions' list

        Returns:
            Dict mapping location to list of questions for that location
        """
        if not questions_data or "questions" not in questions_data:
            return {}

        questions_by_location: dict[str, list[dict[str, Any]]] = {}
        for question in questions_data["questions"]:
            location = question.get("location")
            if location:
                if location not in questions_by_location:
                    questions_by_location[location] = []
                questions_by_location[location].append(question)

        return questions_by_location

    def _build_recommendations_lookup(
        self, recommendations_data: dict[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        """
        Build lookup dict of recommendations by component name.

        Args:
            recommendations_data: Recommendations data dict with 'recommendations' list

        Returns:
            Dict mapping component name to recommendation dict
        """
        if not recommendations_data or "recommendations" not in recommendations_data:
            return {}

        recommendations_by_component: dict[str, dict[str, Any]] = {}
        for rec in recommendations_data["recommendations"]:
            component_name = rec.get("component_name")
            if component_name:
                recommendations_by_component[component_name] = rec

        return recommendations_by_component
