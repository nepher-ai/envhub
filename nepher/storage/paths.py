"""
Path safety helpers for untrusted bundle content and environment IDs.
"""

import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Union

_ENV_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def safe_env_id(env_id: str) -> str:
    """Return ``env_id`` if it is a single safe path segment, else raise ValueError."""
    if not isinstance(env_id, str) or not _ENV_ID_RE.match(env_id) or ".." in env_id:
        raise ValueError(f"Invalid environment ID: {env_id!r}")
    return env_id


def resolve_within(base: Path, relative: Union[str, Path]) -> Path:
    """Resolve ``relative`` under ``base``, rejecting absolute paths and escapes."""
    rel = str(relative)
    if PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).is_absolute() or PureWindowsPath(rel).drive:
        raise ValueError(f"Bundle path must be relative: {rel!r}")

    base_resolved = base.resolve()
    target = (base_resolved / rel).resolve()
    if not target.is_relative_to(base_resolved):
        raise ValueError(f"Bundle path escapes the bundle directory: {rel!r}")
    return target
