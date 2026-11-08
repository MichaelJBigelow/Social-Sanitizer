"""Runs the classifier on a background thread so the GUI never freezes."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .classifier import Comment, CommentClassifier, KeywordClassifier, LLMClassifier


class ClassifierWorker(QObject):
    """Lives on a QThread. Talk to it only through signals (queued connections)."""

    loading = Signal(str)  # human-readable status while the model loads
    ready = Signal(str)  # description of the active backend
    fell_back = Signal(str)  # why the LLM couldn't load; keyword classifier is used instead
    results = Signal(int, list)  # request id, list[tuple[Comment, Verdict]]
    failed = Signal(int, str)  # request id, error message

    def __init__(self, classifier: CommentClassifier):
        super().__init__()
        self._classifier = classifier

    def describe(self) -> str:
        if isinstance(self._classifier, LLMClassifier):
            return f"LLM: {self._classifier.model_id} on {self._classifier.device}"
        return "Keyword rules (no LLM)"

    @Slot()
    def load(self) -> None:
        if isinstance(self._classifier, LLMClassifier):
            self.loading.emit(
                f"Loading {self._classifier.model_id}… (the first run downloads it, ~3.5 GB)"
            )
        try:
            self._classifier.load()
        except Exception as exc:  # ImportError (no torch), network errors, OOM, …
            self._classifier = KeywordClassifier(threshold=self._classifier.threshold)
            self.fell_back.emit(f"{type(exc).__name__}: {exc}")
        self.ready.emit(self.describe())

    @Slot(int, list)
    def classify(self, request_id: int, comments: list[Comment]) -> None:
        try:
            verdicts = self._classifier.classify_batch([c.text for c in comments])
        except Exception as exc:
            self.failed.emit(request_id, f"{type(exc).__name__}: {exc}")
            return
        self.results.emit(request_id, list(zip(comments, verdicts)))
