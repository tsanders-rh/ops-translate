"""
File utility functions.
"""

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Ensure directory exists, creating if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: str | Path) -> str:
    """Read text file content."""
    return Path(path).read_text()


def write_text(path: str | Path, content: str) -> None:
    """Write text to file, creating parent directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
