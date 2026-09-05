"""User-owned approvals for repository-controlled verifier configuration.

Only the interactive approval command writes these records. The Stop hook reads
an exact configuration snapshot and never creates an approval directory or file.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

CONFIG_NAME = ".loopgain-goal.json"


def read_goal(project: Path) -> tuple[bytes, dict]:
    with (project / CONFIG_NAME).open("rb") as stream:
        raw = stream.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024:
        raise ValueError("configuration exceeds 64 KiB")
    config = json.loads(raw)
    if not isinstance(config, dict):
        raise ValueError("configuration must be an object")
    for key in ("verify_command", "error_pattern"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    return raw, config


def approval_record(project: Path, raw: bytes) -> dict:
    return {
        "version": 1,
        "project": str(project.resolve(strict=True)),
        "config_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _private(path: Path, directory: bool) -> None:
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError(f"Approval storage must be private, user-owned, and not a symlink: {path}")


def _approval_path(project: Path, create: bool = False) -> Path:
    root = Path.home() / ".loopgain"
    directory = root / "goal-approvals"
    # Never accept an approval store inside the project being authorized.
    for path in (root, directory):
        if path.resolve().is_relative_to(project.resolve()):
            raise ValueError("Approval storage cannot be inside the project")
        if create:
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass
        _private(path, directory=True)
    key = hashlib.sha256(os.fsencode(project.resolve(strict=True))).hexdigest()
    return directory / f"{key}.json"


def is_approved(project: Path, raw: bytes) -> bool:
    try:
        path = _approval_path(project)
        # O_NOFOLLOW and descriptor checks prevent following a swapped symlink.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                return False
            saved = json.loads(stream.read(4096))
        return saved == approval_record(project, raw)
    except (OSError, ValueError, TypeError):
        return False


def write_approval(project: Path, raw: bytes) -> None:
    """Called by the explicit interactive CLI, never by the hook."""
    path = _approval_path(project, create=True)
    # Replacing the directory entry never follows an existing record symlink.
    import tempfile
    fd, temporary = tempfile.mkstemp(prefix=".approval-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(approval_record(project, raw), stream)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
