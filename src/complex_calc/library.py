"""Library documents (MyLib), like on the handheld.

Every *.txt file in the MyLib folder is a library document. Its name (file
name without extension) is the library name. The file contains statements,
usually  Define LibPub name(...)=...  and  Define LibPriv name(...)=... .
After "Refresh Libraries", objects are used as  libname\\objname(...)  and
libShortcut("libname","short") creates short.objname references.

Folder: $XDG_DATA_HOME/complex_calc/MyLib  (default ~/.local/share/complex_calc/MyLib)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def library_folder() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "complex_calc" / "MyLib"


def load_library(path: Path) -> dict[str, tuple[Any, bool]]:
    """Evaluate one library document; returns {object name: (value, is_public)}."""
    from .core.session import Session

    loader = Session()
    loader.evaluate(path.read_text(encoding="utf-8"))
    from .core.values import UserProgram

    objects = {}
    for name, kind in loader.lib_flags.items():
        if name in loader.variables:
            value = loader.variables[name]
            if isinstance(value, UserProgram):
                value.library = path.stem.lower()
            objects[name] = (value, kind == "LibPub")
    return objects


def refresh_libraries(session, folder: Path | None = None) -> list[str]:
    """Load all library documents into session.libraries; returns messages."""
    folder = folder or library_folder()
    session.libraries = {}
    messages = []
    if not folder.is_dir():
        return [f"No library folder ({folder})"]
    for path in sorted(folder.glob("*.txt")):
        name = path.stem.lower()
        try:
            session.libraries[name] = load_library(path)
            messages.append(f"{name}: {len(session.libraries[name])} objects")
        except Exception as exc:  # noqa: BLE001 - report and continue
            messages.append(f"{name}: error – {exc}")
    return messages
