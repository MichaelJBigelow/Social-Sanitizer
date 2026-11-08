import pytest

from social_sanitizer.classifier import KeywordClassifier, create_classifier


@pytest.mark.parametrize(
    "text",
    [
        "hey sexy",
        "check ur dms 😉",
        "send nudes",
        "you'd look better without that top",
        "kys",
        "DM me for a sugar daddy arrangement",
    ],
)
def test_flags_blatant_comments(text):
    verdict = KeywordClassifier().classify(text)
    assert verdict.flagged
    assert verdict.score == 1.0
    assert verdict.reason.startswith("matched")


@pytest.mark.parametrize(
    "text",
    [
        "Love this outfit!",
        "Where was this taken?",
        "Congrats on the new job 🎉",
        "Assassin's Creed fan art?",  # 'ass' inside a word
        "Essex is lovely this time of year",
    ],
)
def test_leaves_normal_comments_alone(text):
    verdict = KeywordClassifier().classify(text)
    assert not verdict.flagged
    assert verdict.score == 0.0


def test_batch_keeps_order():
    verdicts = KeywordClassifier().classify_batch(["nice pic", "hey sexy", "cool"])
    assert [v.flagged for v in verdicts] == [False, True, False]


def test_factory():
    assert create_classifier("keyword").name == "keyword"
    assert create_classifier("llm").name == "llm"
    with pytest.raises(ValueError):
        create_classifier("nope")
