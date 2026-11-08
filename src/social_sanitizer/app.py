"""Main window: browser on the left, scan results on the right."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QBrush, QCloseEvent, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME
from .browser import BrowserPane, PageComments
from .classifier import DEFAULT_MODEL, Comment, Verdict, create_classifier
from .worker import ClassifierWorker

FLAG_COLOR = QColor("#d93036")
AUTO_SCAN_MS = 4000
_SCORE_ROLE = Qt.ItemDataRole.UserRole
_ID_ROLE = Qt.ItemDataRole.UserRole + 1


@dataclass
class AppSettings:
    start_url: str | QUrl
    profile_dir: Path
    backend: str = "llm"
    model_id: str = DEFAULT_MODEL
    threshold: float = 0.5


class _Row(QTreeWidgetItem):
    """Sorts the score column numerically instead of as text."""

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        tree = self.treeWidget()
        column = tree.sortColumn() if tree else 0
        if column == 0:
            return (self.data(0, _SCORE_ROLE) or -1.0) < (other.data(0, _SCORE_ROLE) or -1.0)
        return self.text(column).lower() < other.text(column).lower()


class MainWindow(QMainWindow):
    classify_requested = Signal(int, list)

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1400, 900)

        self._comments: list[Comment] = []  # comments currently on the page (not the owner's)
        self._verdicts: dict[str, Verdict] = {}  # by comment text, so rescans are free
        self._pending: set[int] = set()
        self._probe_requests: set[int] = set()
        self._next_request = 0
        self._page_key = ""

        self.browser = BrowserPane(settings.profile_dir, self)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.browser)
        splitter.addWidget(self._build_panel(settings.threshold))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1000, 400])
        self.setCentralWidget(splitter)

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(AUTO_SCAN_MS)
        self._auto_timer.timeout.connect(self._auto_scan)

        self._thread = QThread(self)
        self._worker = ClassifierWorker(create_classifier(settings.backend, settings.model_id, settings.threshold))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.load)
        self._thread.finished.connect(self._worker.deleteLater)
        self.classify_requested.connect(self._worker.classify)
        self._worker.loading.connect(self._model_label.setText)
        self._worker.ready.connect(self._on_model_ready)
        self._worker.fell_back.connect(self._on_fell_back)
        self._worker.results.connect(self._on_results)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

        self.browser.url_changed.connect(self._on_url_changed)
        self.browser.load(settings.start_url)

    # -- layout -------------------------------------------------------------------------

    def _build_panel(self, threshold: float) -> QWidget:
        panel = QWidget(self)
        panel.setMinimumWidth(340)
        layout = QVBoxLayout(panel)

        model_box = QGroupBox("Model", panel)
        model_layout = QVBoxLayout(model_box)
        self._model_label = QLabel("Starting…", model_box)
        self._model_label.setWordWrap(True)
        model_layout.addWidget(self._model_label)
        layout.addWidget(model_box)

        controls = QHBoxLayout()
        self._scan_button = QPushButton("Scan comments", panel)
        self._scan_button.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._scan_button.setToolTip("Read the comments on this page and check them (Ctrl+Shift+S)")
        self._scan_button.clicked.connect(self.scan)
        controls.addWidget(self._scan_button)
        self._auto_check = QCheckBox("Auto-scan", panel)
        self._auto_check.setToolTip("Rescan every few seconds to catch comments as they load")
        self._auto_check.toggled.connect(self._on_auto_toggled)
        controls.addWidget(self._auto_check)
        controls.addStretch(1)
        layout.addLayout(controls)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Flag at", panel))
        self._threshold = QDoubleSpinBox(panel)
        self._threshold.setRange(0.05, 0.95)
        self._threshold.setSingleStep(0.05)
        self._threshold.setDecimals(2)
        self._threshold.setValue(threshold)
        self._threshold.setToolTip("Comments scoring at or above this are flagged")
        self._threshold.valueChanged.connect(self._refresh)
        filters.addWidget(self._threshold)
        self._flagged_only = QCheckBox("Flagged only", panel)
        self._flagged_only.toggled.connect(self._render)
        filters.addWidget(self._flagged_only)
        filters.addStretch(1)
        layout.addLayout(filters)

        self._summary = QLabel("Open a post, then press Scan comments.", panel)
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._tree = QTreeWidget(panel)
        self._tree.setHeaderLabels(["Score", "Author", "Comment"])
        self._tree.setRootIsDecorated(False)
        self._tree.setUniformRowHeights(True)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        header = self._tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree, 1)

        probe_box = QGroupBox("Try a comment", panel)
        probe_layout = QVBoxLayout(probe_box)
        self._probe_input = QLineEdit(probe_box)
        self._probe_input.setPlaceholderText("Type a comment and press Enter")
        self._probe_input.returnPressed.connect(self._probe)
        probe_layout.addWidget(self._probe_input)
        self._probe_result = QLabel("", probe_box)
        self._probe_result.setWordWrap(True)
        probe_layout.addWidget(self._probe_result)
        layout.addWidget(probe_box)

        return panel

    # -- scanning -----------------------------------------------------------------------

    def scan(self) -> None:
        self.browser.extract_comments(self._on_extracted)

    def _auto_scan(self) -> None:
        if not self._pending:  # don't pile up work while the model is busy
            self.scan()

    def _on_auto_toggled(self, on: bool) -> None:
        if on:
            self.scan()
            self._auto_timer.start()
        else:
            self._auto_timer.stop()

    def _on_extracted(self, page: PageComments | None) -> None:
        if page is None:
            self.statusBar().showMessage("Couldn't read this page.", 5000)
            return
        self._comments = page.from_others()
        new = [c for c in self._comments if c.text not in self._verdicts]
        # Classify each distinct text once, even if several people posted it.
        unique = list({c.text: c for c in new}.values())
        if unique:
            self._request(unique)
            self.statusBar().showMessage(f"Checking {len(unique)} new comment(s)…")
        elif not self._comments:
            self.statusBar().showMessage("No comments found on this page.", 5000)
        self._refresh()

    def _request(self, comments: list[Comment]) -> int:
        request_id = self._next_request
        self._next_request += 1
        self._pending.add(request_id)
        self.classify_requested.emit(request_id, comments)
        return request_id

    def _probe(self) -> None:
        text = self._probe_input.text().strip()
        if not text:
            return
        self._probe_result.setText("Checking…")
        self._probe_requests.add(self._request([Comment(id="probe", author="", text=text)]))

    # -- worker callbacks ---------------------------------------------------------------

    def _on_model_ready(self, description: str) -> None:
        self._model_label.setText(description)

    def _on_fell_back(self, reason: str) -> None:
        self._model_label.setStyleSheet(f"color: {FLAG_COLOR.name()}")
        self.statusBar().showMessage(f"LLM unavailable, using keyword rules. {reason}")

    def _on_results(self, request_id: int, pairs: list) -> None:
        self._pending.discard(request_id)
        for comment, verdict in pairs:
            self._verdicts[comment.text] = verdict
        if request_id in self._probe_requests:
            self._probe_requests.discard(request_id)
            _, verdict = pairs[0]
            flagged = verdict.score >= self._threshold.value()
            label = "Flagged" if flagged else "Looks OK"
            self._probe_result.setText(f"<b>{label}</b> · score {verdict.score:.0%} ({verdict.backend})")
            return
        if not self._pending:
            self.statusBar().clearMessage()
        self._refresh()

    def _on_failed(self, request_id: int, message: str) -> None:
        self._pending.discard(request_id)
        self._probe_requests.discard(request_id)
        self.statusBar().showMessage(f"Classification failed: {message}", 10000)

    # -- display ------------------------------------------------------------------------

    def _is_flagged(self, verdict: Verdict | None) -> bool:
        return verdict is not None and verdict.score >= self._threshold.value()

    def _refresh(self) -> None:
        self._render()
        self._highlight()

    def _render(self) -> None:
        threshold_flagged = 0
        pending = 0
        self._tree.setSortingEnabled(False)
        self._tree.clear()
        bold = QFont()
        bold.setBold(True)
        for comment in self._comments:
            verdict = self._verdicts.get(comment.text)
            flagged = self._is_flagged(verdict)
            threshold_flagged += flagged
            pending += verdict is None
            if self._flagged_only.isChecked() and not flagged:
                continue
            row = _Row([f"{verdict.score:.0%}" if verdict else "…", comment.author, comment.text])
            row.setData(0, _SCORE_ROLE, verdict.score if verdict else None)
            row.setData(0, _ID_ROLE, comment.id)
            row.setToolTip(2, comment.text)
            if verdict and verdict.reason:
                row.setToolTip(0, verdict.reason)
            if flagged:
                for column in range(3):
                    row.setForeground(column, QBrush(FLAG_COLOR))
                    row.setFont(column, bold)
            self._tree.addTopLevelItem(row)
        self._tree.setSortingEnabled(True)

        if not self._comments:
            self._summary.setText("No comments scanned yet. Open a post, then press Scan comments.")
            return
        parts = [f"{len(self._comments)} comments", f"{threshold_flagged} flagged"]
        if pending:
            parts.append(f"{pending} checking")
        self._summary.setText(" · ".join(parts))

    def _highlight(self) -> None:
        flagged_by_id = {
            c.id: self._is_flagged(self._verdicts[c.text]) for c in self._comments if c.text in self._verdicts
        }
        self.browser.highlight(flagged_by_id)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        comment_id = item.data(0, _ID_ROLE)
        if comment_id:
            self.browser.scroll_to(comment_id)

    def _on_url_changed(self, url: QUrl) -> None:
        # Instagram is a single-page app; a new path means a new post or profile.
        key = f"{url.scheme()}://{url.host()}{url.path()}"
        if key != self._page_key:
            self._page_key = key
            self._comments = []
            self._render()

    # -- shutdown -----------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        self._auto_timer.stop()
        self._thread.quit()
        self._thread.wait(10000)
        self.browser.shutdown()
        super().closeEvent(event)
