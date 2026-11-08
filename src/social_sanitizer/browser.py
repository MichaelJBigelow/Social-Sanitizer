"""Built-in browser pane and the Python <-> page bridge.

The pane is a Chromium-based QWebEngineView with its own persistent profile, so an
Instagram login survives restarts and stays separate from the user's normal browser.
All page scripts run in Qt's isolated ApplicationWorld: they share the DOM with the
page but not its JavaScript globals, so the page can't tamper with them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Callable, Mapping

import shiboken6
from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLineEdit, QToolBar, QVBoxLayout, QWidget

from .classifier import Comment

_ID_RE = re.compile(r"^[0-9a-z]+$")
_WORLD = QWebEngineScript.ScriptWorldId.ApplicationWorld


def load_script(name: str) -> str:
    return resources.files("social_sanitizer").joinpath("js", name).read_text(encoding="utf-8")


@dataclass
class PageComments:
    """What the extractor found on the page."""

    url: str
    owner: str | None
    comments: list[Comment] = field(default_factory=list)

    @classmethod
    def from_json(cls, raw: str) -> "PageComments":
        data = json.loads(raw)
        return cls(
            url=data.get("url", ""),
            owner=data.get("owner"),
            comments=[Comment(id=c["id"], author=c["author"], text=c["text"]) for c in data.get("comments", [])],
        )

    def from_others(self) -> list[Comment]:
        """Comments not written by the post's owner (we never flag the poster herself)."""
        return [c for c in self.comments if c.author != self.owner]


def normalize_url(text: str) -> QUrl:
    text = text.strip()
    if not text:
        return QUrl()
    if "://" not in text and not text.startswith(("about:", "file:")):
        text = "https://" + text
    return QUrl(text)


class BrowserPane(QWidget):
    """A small browser: navigation toolbar plus a web view we can script."""

    url_changed = Signal(QUrl)
    load_finished = Signal(bool)

    def __init__(self, profile_dir: Path, parent: QWidget | None = None):
        super().__init__(parent)

        # A named profile is persistent (cookies, local storage, cache on disk).
        self._profile = QWebEngineProfile("social-sanitizer", self)
        self._profile.setPersistentStoragePath(str(profile_dir / "storage"))
        self._profile.setCachePath(str(profile_dir / "cache"))
        self._profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        self.view = QWebEngineView(self)
        self._page: QWebEnginePage | None = QWebEnginePage(self._profile, self.view)
        self.view.setPage(self._page)

        self._address = QLineEdit(self)
        self._address.setPlaceholderText("Enter a URL or Instagram post link")
        self._address.setClearButtonEnabled(True)
        self._address.returnPressed.connect(lambda: self.load(self._address.text()))

        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        for action, shortcut in (
            (QWebEnginePage.WebAction.Back, QKeySequence.StandardKey.Back),
            (QWebEnginePage.WebAction.Forward, QKeySequence.StandardKey.Forward),
            (QWebEnginePage.WebAction.Reload, QKeySequence.StandardKey.Refresh),
        ):
            qaction = self.view.pageAction(action)
            qaction.setShortcut(shortcut)
            toolbar.addAction(qaction)
        home = QAction("Instagram", self)
        home.triggered.connect(lambda: self.load("https://www.instagram.com/"))
        toolbar.addAction(home)
        toolbar.addWidget(self._address)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self.view, 1)

        self.view.urlChanged.connect(self._on_url_changed)
        self.view.loadFinished.connect(self.load_finished)

    # -- navigation ---------------------------------------------------------------------

    def load(self, url: str | QUrl) -> None:
        qurl = url if isinstance(url, QUrl) else normalize_url(url)
        if qurl.isValid():
            self.view.setUrl(qurl)

    def url(self) -> QUrl:
        return self.view.url()

    def _on_url_changed(self, url: QUrl) -> None:
        self._address.setText(url.toString())
        self.url_changed.emit(url)

    # -- page bridge --------------------------------------------------------------------

    def run_js(self, source: str, callback: Callable[[object], None] | None = None) -> None:
        if callback is None:
            self._page.runJavaScript(source, _WORLD)
        else:
            self._page.runJavaScript(source, _WORLD, callback)

    def extract_comments(self, callback: Callable[[PageComments | None], None]) -> None:
        """Scrape comments from the page; calls back with None if the page couldn't be read."""

        def done(raw: object) -> None:
            try:
                callback(PageComments.from_json(raw) if isinstance(raw, str) else None)
            except (ValueError, KeyError, TypeError):
                callback(None)

        self.run_js(load_script("extract_comments.js"), done)

    def highlight(self, flagged_by_id: Mapping[str, bool], callback: Callable[[object], None] | None = None) -> None:
        """Outline flagged comments on the page; ids missing from the map are cleared."""
        script = load_script("highlight.js").replace("__VERDICTS__", json.dumps(dict(flagged_by_id)))
        self.run_js(script, callback)

    def scroll_to(self, comment_id: str) -> None:
        if _ID_RE.match(comment_id):
            self.run_js(load_script("scroll_to.js").replace("__ID__", comment_id))

    def shutdown(self) -> None:
        """Release the page before its profile, which Qt requires to flush storage cleanly."""
        if self._page is None:
            return
        self.view.setPage(None)
        # Delete now, not via deleteLater(): the profile may be destroyed before the
        # event loop gets another turn.
        shiboken6.delete(self._page)
        self._page = None
