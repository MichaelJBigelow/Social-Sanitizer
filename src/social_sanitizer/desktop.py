"""Small per-OS touches so the app behaves like a native desktop app on macOS,
Windows and Linux."""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

from platformdirs import user_log_dir

from . import APP_NAME

# Matches the .desktop file the Linux launcher installs (Wayland uses it to find the icon).
DESKTOP_FILE_NAME = "social-sanitizer"
WINDOWS_APP_ID = "SocialSanitizer.App"


def log_file() -> Path:
    return Path(user_log_dir(APP_NAME, appauthor=False)) / "app.log"


def ensure_output_streams() -> None:
    """Give the app somewhere to write when it has no console.

    Windows starts GUI apps with pythonw.exe, where sys.stdout and sys.stderr are None.
    Anything that prints (model download progress bars, warnings) would then crash, so
    send that output to a log file instead.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    path = log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = open(path, "a", encoding="utf-8", errors="replace", buffering=1)  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def set_windows_app_id() -> None:
    """Group the app under its own taskbar button and icon instead of pythonw.exe's."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        pass


def icon_path() -> Path:
    return Path(str(resources.files("social_sanitizer").joinpath("assets", "icon.png")))
