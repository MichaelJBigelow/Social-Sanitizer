"""Small local LLM classifier.

Rather than letting the model generate free text, we ask a yes/no question and read the
probabilities of the "YES" and "NO" tokens from a single forward pass. That gives a
calibrated-ish 0..1 score, needs no output parsing, and costs one pass per batch.

The default model is Qwen3-1.7B (~3.5 GB download, Apache-2.0, no Hugging Face login
needed). In testing it cleanly separated creepy from friendly comments, while the
sub-1B models we tried (Qwen2.5-0.5B, Qwen3-0.6B) could not. Any chat model with a
chat template should work; pass --model to try another.
"""

from __future__ import annotations

import threading
from typing import Sequence

from .base import Verdict

DEFAULT_MODEL = "Qwen/Qwen3-1.7B"
MAX_COMMENT_CHARS = 600

SYSTEM_PROMPT = """You moderate comments left on a woman's public Instagram post.
Decide if a comment is INAPPROPRIATE. Inappropriate means any of:
- sexual remarks, innuendo, or comments about her body
- unwanted advances: asking her to DM, text, meet up, or "be his girl"
- requests for photos, nudes, or private content
- insults, slurs, degrading or misogynistic language
- threats, stalking, or saying they know where she is
- spam/scams such as sugar-daddy offers or "investment" pitches

Respectful compliments, questions about the post, jokes between friends, and
support are NOT inappropriate.

Answer with exactly one word: YES if the comment is inappropriate, NO if it is not."""

# A few labelled examples sharply improve a 0.5B model's consistency.
FEW_SHOT: tuple[tuple[str, str], ...] = (
    ("Love this outfit, where is the jacket from?", "NO"),
    ("dm me beautiful 😘 I wanna get to know u better", "YES"),
    ("Congrats on the new job!! So proud of you", "NO"),
    ("you'd look even better without that top", "YES"),
    ("Stunning view, which beach is this? @lena.travels we should go", "NO"),
    ("nobody cares, ugly attention seeker", "YES"),
    ("you awake? 😏 wanna have some fun later", "YES"),
)


def _user_turn(text: str) -> str:
    return f"Comment: {text[:MAX_COMMENT_CHARS]}"


class LLMClassifier:
    name = "llm"

    def __init__(self, model_id: str = DEFAULT_MODEL, threshold: float = 0.5, device: str | None = None):
        self.model_id = model_id
        self.threshold = threshold
        self._device = device
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None
        self._yes_id: int | None = None
        self._no_id: int | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def device(self) -> str | None:
        """The torch device in use ("mps", "cuda", "cpu"), or None before loading."""
        return self._device if self.loaded else None

    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            # Imported lazily so the rest of the app works without torch installed.
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            device = self._device
            if device is None:
                if torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
                else:
                    device = "cpu"

            tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            tokenizer.padding_side = "left"  # so the last position is the next-token slot
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # bfloat16 halves memory on GPUs (~3.5 GB for the 1.7B default); CPUs get float32
            # because bf16 matmuls are slow there.
            dtype = torch.float32 if device == "cpu" else torch.bfloat16
            model = AutoModelForCausalLM.from_pretrained(self.model_id, dtype=dtype)
            model.to(device)
            model.eval()

            self._yes_id = self._first_token_id(tokenizer, "YES")
            self._no_id = self._first_token_id(tokenizer, "NO")
            self._device = device
            self._tokenizer = tokenizer
            self._model = model

    @staticmethod
    def _first_token_id(tokenizer, word: str) -> int:
        ids = tokenizer.encode(word, add_special_tokens=False)
        if not ids:
            raise ValueError(f"Tokenizer can't encode {word!r}")
        return ids[0]

    def _prompt(self, text: str) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for example, answer in FEW_SHOT:
            messages.append({"role": "user", "content": _user_turn(example)})
            messages.append({"role": "assistant", "content": answer})
        messages.append({"role": "user", "content": _user_turn(text)})
        # enable_thinking=False turns off Qwen3-style reasoning; other templates ignore it.
        return self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )

    def classify_batch(self, texts: Sequence[str], batch_size: int = 8) -> list[Verdict]:
        if not texts:
            return []
        self.load()
        import torch

        verdicts: list[Verdict] = []
        with self._lock, torch.inference_mode():
            for start in range(0, len(texts), batch_size):
                chunk = texts[start : start + batch_size]
                prompts = [self._prompt(t) for t in chunk]
                inputs = self._tokenizer(prompts, return_tensors="pt", padding=True).to(self._device)
                logits = self._model(**inputs).logits[:, -1, :]
                pair = torch.stack([logits[:, self._yes_id], logits[:, self._no_id]], dim=-1)
                p_yes = torch.softmax(pair.float(), dim=-1)[:, 0].tolist()
                for score in p_yes:
                    verdicts.append(
                        Verdict(
                            flagged=score >= self.threshold,
                            score=score,
                            backend=self.name,
                            reason=f"{score:.0%} likely inappropriate",
                        )
                    )
        return verdicts

    def classify(self, text: str) -> Verdict:
        return self.classify_batch([text])[0]
