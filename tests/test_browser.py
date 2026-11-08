"""Loads the demo post in a real (offscreen) QtWebEngine and checks the page bridge."""

import os
from importlib import resources

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer, QUrl  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402, F401
from PySide6.QtWidgets import QApplication  # noqa: E402

from social_sanitizer.browser import BrowserPane, PageComments, normalize_url  # noqa: E402

DEMO = resources.files("social_sanitizer").joinpath("demo", "mock_post.html")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(signal_or_callback_setup, timeout_ms=15000):
    """Run an event loop until the callback passed to `signal_or_callback_setup` fires."""
    loop = QEventLoop()
    box = {}

    def done(*args):
        box["value"] = args[0] if len(args) == 1 else args
        loop.quit()

    signal_or_callback_setup(done)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if "value" not in box:
        pytest.fail("timed out waiting for the page")
    return box["value"]


@pytest.fixture
def pane(app, tmp_path):
    pane = BrowserPane(tmp_path)
    assert wait_for(lambda done: (pane.load_finished.connect(done), pane.load(QUrl.fromLocalFile(str(DEMO)))))
    yield pane
    pane.shutdown()
    pane.deleteLater()


def test_extracts_comments_and_owner(pane):
    page: PageComments = wait_for(pane.extract_comments)
    assert page is not None
    assert page.owner == "maya.paints"

    by_author = {c.author: c.text for c in page.comments}
    assert by_author["jordan_r"] == "These colors are incredible, do you sell prints?"
    assert by_author["xx_dave_xx"].startswith("forget the prints")  # nested reply
    assert by_author["sam.k"].startswith("Which brushes")  # @mention link didn't confuse it
    assert len(page.comments) == 9  # 7 visitors + owner's caption + owner's reply

    others = page.from_others()
    assert len(others) == 7
    assert all(c.author != "maya.paints" for c in others)
    assert len({c.id for c in others}) == 7

    # UI chrome must never be mistaken for comment text.
    texts = {c.text for c in page.comments}
    assert not texts & {"Reply", "See translation", "3 likes", "5d"}


def test_highlight_and_scroll(pane):
    page = wait_for(pane.extract_comments)
    dave = next(c for c in page.comments if c.author == "xx_dave_xx")
    jordan = next(c for c in page.comments if c.author == "jordan_r")

    count = wait_for(lambda done: pane.highlight({dave.id: True, jordan.id: False}, done))
    assert count == 1
    state = wait_for(
        lambda done: pane.run_js(
            f'document.querySelector(\'[data-ss-id="{dave.id}"]\').getAttribute("data-ss-state")', done
        )
    )
    assert state == "flagged"

    pane.scroll_to(dave.id)
    focused = wait_for(lambda done: pane.run_js("document.querySelectorAll('[data-ss-focus]').length", done))
    assert focused == 1


def test_scroll_to_rejects_odd_ids(pane):
    pane.scroll_to('x"]); alert(1); //')  # must be ignored, not injected
    focused = wait_for(lambda done: pane.run_js("document.querySelectorAll('[data-ss-focus]').length", done))
    assert focused == 0


def test_normalize_url():
    assert normalize_url("instagram.com/p/abc").toString() == "https://instagram.com/p/abc"
    assert normalize_url("http://example.com").toString() == "http://example.com"
    assert not normalize_url("  ").isValid()
