"""
File hashing utilities.
"""

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def sha256_string(content: str) -> str:
    """Compute SHA256 hash of a string."""
    return hashlib.sha256(content.encode()).hexdigest()
