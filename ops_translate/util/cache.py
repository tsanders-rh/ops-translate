"""
Caching utilities for incremental analysis.

Tracks analyzed workflows and their content hashes to enable incremental
re-analysis (only analyze changed files).
"""

import hashlib
import json
from pathlib import Path
from typing import Any


class AnalysisCache:
    """
    Manages cache of analyzed workflows for incremental analysis.

    Tracks file hashes and analysis timestamps to determine which workflows
    need re-analysis.
    """

    def __init__(self, cache_file: Path):
        """
        Initialize analysis cache.

        Args:
            cache_file: Path to cache file (typically .ops-translate/analysis-cache.json)
        """
        self.cache_file = cache_file
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file if it exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                # If cache is corrupt or unreadable, start fresh
                self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self._cache, f, indent=2)

    def get_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks for memory efficiency with large files
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def has_changed(self, file_path: Path) -> bool:
        """
        Check if file has changed since last analysis.

        Args:
            file_path: Path to file to check

        Returns:
            True if file has changed or was never analyzed, False otherwise
        """
        if not file_path.exists():
            return True

        file_key = str(file_path)
        current_hash = self.get_file_hash(file_path)

        # File not in cache or hash changed
        if file_key not in self._cache:
            return True

        cached_hash = self._cache[file_key].get("hash")
        return cached_hash != current_hash

    def mark_analyzed(self, file_path: Path, metadata: dict[str, Any] | None = None) -> None:
        """
        Mark file as analyzed with current hash.

        Args:
            file_path: Path to file that was analyzed
            metadata: Optional metadata to store (e.g., analysis timestamp, component count)
        """
        file_key = str(file_path)
        file_hash = self.get_file_hash(file_path)

        self._cache[file_key] = {
            "hash": file_hash,
            "path": str(file_path),
            **(metadata or {}),
        }

        self._save_cache()

    def get_changed_files(self, file_paths: list[Path]) -> tuple[list[Path], list[Path]]:
        """
        Partition files into changed and unchanged.

        Args:
            file_paths: List of file paths to check

        Returns:
            Tuple of (changed_files, unchanged_files)
        """
        changed = []
        unchanged = []

        for file_path in file_paths:
            if self.has_changed(file_path):
                changed.append(file_path)
            else:
                unchanged.append(file_path)

        return changed, unchanged

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache = {}
        self._save_cache()

    def remove(self, file_path: Path) -> None:
        """
        Remove file from cache.

        Args:
            file_path: Path to file to remove from cache
        """
        file_key = str(file_path)
        if file_key in self._cache:
            del self._cache[file_key]
            self._save_cache()

    def get_metadata(self, file_path: Path) -> dict[str, Any] | None:
        """
        Get cached metadata for file.

        Args:
            file_path: Path to file

        Returns:
            Cached metadata dict or None if not in cache
        """
        file_key = str(file_path)
        return self._cache.get(file_key)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (total files, etc.)
        """
        return {
            "total_files": len(self._cache),
            "cache_file": str(self.cache_file),
        }
