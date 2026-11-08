# Social-Sanitizer
The open-source tool that helps women block and report creeps on Instagram. Allies welcome: point it at any woman’s post and report the creeps for her.

## Desktop app (early preview)

A Python desktop app with a built-in browser. Log in to Instagram inside it, open a
post, and press **Scan comments**. A small local LLM reads each comment, and the
inappropriate ones are outlined in red on the page and listed in the side panel.
Click a row to jump to that comment. Nothing leaves your computer: the model runs
locally.

### Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[llm,dev]"
```

### Run

```bash
social-sanitizer            # opens instagram.com
social-sanitizer --demo     # offline demo post, no login needed
```

On first run the model, [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B), downloads
(~3.5 GB). After that it loads in a few seconds. It runs on Apple Silicon (MPS), CUDA,
or the CPU.

Options:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--url URL` | `https://www.instagram.com/` | Page to open at start |
| `--demo` | off | Open the bundled offline demo post |
| `--backend {llm,keyword}` | `llm` | `keyword` uses simple rules, with no model or torch needed |
| `--model ID` | `Qwen/Qwen3-1.7B` | Any Hugging Face chat model |
| `--threshold N` | `0.5` | Flag comments scoring at or above this |

If the LLM can't load (for example, torch isn't installed or the download fails), the app
falls back to the keyword rules and shows the reason in the status bar.

Your browser login is stored separately from your normal browser, in the app's
data folder (`~/Library/Application Support/Social Sanitizer` on macOS).

### How it works

- `src/social_sanitizer/browser.py`: a Chromium (QtWebEngine) browser pane with a
  persistent profile and a bridge that runs scripts in an isolated JS world.
- `src/social_sanitizer/js/`: page scripts that extract comments, highlight
  them, and scroll to them. Instagram's class names are obfuscated, so the extractor
  uses page structure instead: a username link, a `<time>` element, and `dir="auto"` text.
  Comments by the post's owner are skipped.
- `src/social_sanitizer/classifier/`: the LLM classifier asks the model a yes/no
  question and reads the probability of the "YES" token from one forward pass, which
  gives a 0–1 score. Comments are scored in batches on a background thread.

### Tests

```bash
pytest                                  # fast tests, including a headless browser test
SOCIAL_SANITIZER_LLM_TESTS=1 pytest     # also runs the real model
```
