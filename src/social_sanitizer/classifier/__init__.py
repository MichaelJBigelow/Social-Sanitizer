"""Comment classifiers. `create_classifier` picks one by backend name."""

from __future__ import annotations

from .base import Comment, CommentClassifier, Verdict
from .keyword import KeywordClassifier
from .llm import DEFAULT_MODEL, LLMClassifier

BACKENDS = ("llm", "keyword")


def create_classifier(backend: str = "llm", model_id: str = DEFAULT_MODEL, threshold: float = 0.5) -> CommentClassifier:
    if backend == "llm":
        return LLMClassifier(model_id=model_id, threshold=threshold)
    if backend == "keyword":
        return KeywordClassifier(threshold=threshold)
    raise ValueError(f"Unknown classifier backend {backend!r}; choose from {BACKENDS}")


__all__ = [
    "BACKENDS",
    "Comment",
    "CommentClassifier",
    "DEFAULT_MODEL",
    "KeywordClassifier",
    "LLMClassifier",
    "Verdict",
    "create_classifier",
]
