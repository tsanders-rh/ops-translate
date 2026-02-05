"""
Base classifier interface for external dependency classification.

This module defines the abstract base class that all classifier plugins must inherit from.
Classifiers determine translatability levels for detected external dependencies.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseClassifier(ABC):
    """
    Abstract base class for all external dependency classifiers.

    Each classifier plugin (NSX, ServiceNow, plugins, etc.) must inherit from this
    class and implement the required methods. This ensures a consistent interface
    for classification and enables auto-discovery of classifier plugins.

    Example:
        >>> class MyClassifier(BaseClassifier):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_system"
        ...
        ...     def can_classify(self, analysis: dict) -> bool:
        ...         return bool(analysis.get("my_system_operations"))
        ...
        ...     def classify(self, analysis: dict) -> list:
        ...         # Classification logic here
        ...         return classified_components
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the classifier name (lowercase, underscore-separated).

        This is used for identification, logging, and auto-discovery.

        Examples:
            - "nsx" for NSX-T classifier
            - "servicenow" for ServiceNow classifier
            - "custom_plugins" for custom vRO plugins

        Returns:
            Classifier name string
        """
        pass

    @property
    def priority(self) -> int:
        """
        Return the priority for this classifier (lower = higher priority).

        Classifiers are run in priority order. This allows you to control
        which classifier runs first when there might be overlap.

        Default priority is 50 (medium). Override to change.

        Returns:
            Priority value (0-100, where 0 is highest priority)

        Example:
            >>> class HighPriorityClassifier(BaseClassifier):
            ...     @property
            ...     def priority(self) -> int:
            ...         return 10  # Run early
        """
        return 50  # Default medium priority

    @abstractmethod
    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Return True if this classifier can handle the analysis data.

        This method is called before classify() to determine if this classifier
        is applicable. It should check for the presence of relevant data in the
        analysis dictionary.

        Args:
            analysis: Analysis results from ops_translate.analyze.vrealize

        Returns:
            True if this classifier should process this analysis, False otherwise

        Example:
            >>> def can_classify(self, analysis: dict) -> bool:
            ...     # Only classify if NSX operations detected
            ...     return bool(analysis.get("nsx_operations"))
        """
        pass

    @abstractmethod
    def classify(self, analysis: dict[str, Any]) -> list:
        """
        Classify detected components and return ClassifiedComponent instances.

        This is the main classification method. It should analyze the detection
        results and return a list of ClassifiedComponent instances with appropriate
        translatability levels, migration paths, and recommendations.

        Args:
            analysis: Analysis results containing detected components

        Returns:
            List of ClassifiedComponent instances

        Raises:
            May raise exceptions for invalid analysis data (should be caught by caller)

        Example:
            >>> def classify(self, analysis: dict) -> list:
            ...     components = []
            ...     for category, ops in analysis.get("nsx_operations", {}).items():
            ...         for op in ops:
            ...             component = ClassifiedComponent(
            ...                 name=op["name"],
            ...                 component_type=f"nsx_{category}",
            ...                 level=self._determine_level(category),
            ...                 reason=self._get_reason(category),
            ...                 ...
            ...             )
            ...             components.append(component)
            ...     return components
        """
        pass

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"<{self.__class__.__name__}(name='{self.name}', priority={self.priority})>"

    def __str__(self) -> str:
        """Return human-readable string."""
        return f"{self.name} classifier"
