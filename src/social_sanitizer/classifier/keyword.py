"""Dependency-free keyword classifier.

Used as a fallback when the LLM can't be loaded (no torch installed, no network for
the first model download) and in tests. It's deliberately simple: it catches the
blatant cases and misses anything subtle, which is what the LLM is for.
"""

from __future__ import annotations

import re
from typing import Sequence

from .base import Verdict

# Each pattern is matched case-insensitively against the whole comment.
DEFAULT_PATTERNS: tuple[str, ...] = (
    r"\bsend (me )?(nudes|pics|feet pics)\b",
    r"\bnudes?\b",
    r"\b(dm|message|text|snap|hmu) me\b",
    r"\bcheck (your|ur) (dms?|inbox)\b",
    r"\bsexy\b",
    r"\bboobs?\b|\btits\b|\bass\b|\bbooty\b",
    r"\bwithout (that|the|your) (top|shirt|dress|clothes|bikini)\b",
    r"\b(wanna|want to|gonna|going to) (smash|f+u+c+k|bang|hook ?up)\b",
    r"\bf+u+c+k (you|u|off)\b",
    r"\b(bitch|slut|whore|skank|thot)\b",
    r"\b(ugly|fat|disgusting) (cow|pig|hoe|bitch)\b",
    r"\bkill (yourself|urself|you)\b|\bkys\b",
    r"\bi know where you live\b",
    r"\bsugar ?daddy\b|\bsugar baby\b",
    r"\bonly ?fans\b",
    r"[🍆💦👅🍑]",
)


class KeywordClassifier:
    name = "keyword"

    def __init__(self, patterns: Sequence[str] = DEFAULT_PATTERNS, threshold: float = 0.5):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.threshold = threshold

    def load(self) -> None:  # nothing to load
        pass

    def classify(self, text: str) -> Verdict:
        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                return Verdict(
                    flagged=True,
                    score=1.0,
                    backend=self.name,
                    reason=f"matched '{match.group(0)}'",
                )
        return Verdict(flagged=False, score=0.0, backend=self.name)

    def classify_batch(self, texts: Sequence[str]) -> list[Verdict]:
        return [self.classify(t) for t in texts]
