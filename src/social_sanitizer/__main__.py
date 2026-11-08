"""Entry point: `social-sanitizer` or `python -m social_sanitizer`."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

from platformdirs import user_data_dir

from . import APP_NAME, __version__, desktop
from .classifier import BACKENDS, DEFAULT_MODEL


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="social-sanitizer", description=APP_NAME)
    parser.add_argument("--url", default="https://www.instagram.com/", help="page to open at start")
    parser.add_argument("--demo", action="store_true", help="open the built-in offline demo post")
    parser.add_argument("--backend", choices=BACKENDS, default="llm", help="comment classifier (default: llm)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Hugging Face model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--threshold", type=float, default=0.5, help="flag comments scoring at or above this")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    desktop.ensure_output_streams()  # first, so even argparse errors have somewhere to go
    args = parse_args(argv)
    desktop.set_windows_app_id()  # must happen before any window is created

    # QtWebEngine must be imported before the QApplication exists.
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QIcon
    from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    from PySide6.QtWidgets import QApplication

    from .app import AppSettings, MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(desktop.DESKTOP_FILE_NAME)
    app.setWindowIcon(QIcon(str(desktop.icon_path())))

    if args.demo:
        demo = resources.files("social_sanitizer").joinpath("demo", "mock_post.html")
        start_url: str | QUrl = QUrl.fromLocalFile(str(demo))
    else:
        start_url = args.url

    settings = AppSettings(
        start_url=start_url,
        profile_dir=Path(user_data_dir(APP_NAME, appauthor=False)),
        backend=args.backend,
        model_id=args.model,
        threshold=args.threshold,
    )
    window = MainWindow(settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
