"""Runs the real model. Opt in with SOCIAL_SANITIZER_LLM_TESTS=1 (needs torch and the
model download, ~3.5 GB on first run)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SOCIAL_SANITIZER_LLM_TESTS") != "1",
    reason="set SOCIAL_SANITIZER_LLM_TESTS=1 to run the LLM tests",
)

INAPPROPRIATE = [
    "hey sexy check ur dm",
    "you look like a whore in that dress",
    "send me pics of your feet I pay",
    "I know where you live now 😉",
    "Those legs tho 🤤",
    "wyd tonight? come over",
]
FINE = [
    "Gorgeous sunset! Where was this taken?",
    "Happy birthday girl!! 🎉",
    "what camera do you use?",
    "You inspire me so much, thank you for sharing",
    "lol same, my cat does that too",
]


@pytest.fixture(scope="module")
def classifier():
    from social_sanitizer.classifier import LLMClassifier

    c = LLMClassifier()
    c.load()
    return c


def test_flags_inappropriate(classifier):
    verdicts = classifier.classify_batch(INAPPROPRIATE)
    missed = [t for t, v in zip(INAPPROPRIATE, verdicts) if not v.flagged]
    assert not missed


def test_passes_fine(classifier):
    verdicts = classifier.classify_batch(FINE)
    wrongly_flagged = [t for t, v in zip(FINE, verdicts) if v.flagged]
    assert not wrongly_flagged


def test_batched_matches_single(classifier):
    text = INAPPROPRIATE[0]
    batched = classifier.classify_batch([FINE[0], text, FINE[1]])[1]
    single = classifier.classify(text)
    assert abs(batched.score - single.score) < 0.05
