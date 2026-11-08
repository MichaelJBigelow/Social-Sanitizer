"""Shared types for comment classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Comment:
    """One comment scraped from the page."""

    id: str
    author: str
    text: str


@dataclass(frozen=True)
class Verdict:
    """A classifier's decision about one comment."""

    flagged: bool
    score: float  # 0.0 = clearly fine, 1.0 = clearly inappropriate
    backend: str
    reason: str = ""


class CommentClassifier(Protocol):
    """Anything that can decide whether comments are inappropriate."""

    name: str
    threshold: float

    def load(self) -> None:
        """Do any slow setup (model download/load). Safe to call more than once."""

    def classify_batch(self, texts: Sequence[str]) -> list[Verdict]:
        """Classify several comments at once, returning one verdict per text, in order."""

    def classify(self, text: str) -> Verdict:
        """Classify a single comment."""
