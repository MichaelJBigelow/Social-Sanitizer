# Social-Sanitizer
The open-source tool that helps women block and report creeps on Instagram. Allies welcome: point it at any woman’s post and report the creeps for her.

## Why this tool exists

Women who post on Instagram often get sexually abusive comments, and Instagram makes
cleaning them up slow and repetitive. That work falls on the women being targeted. As of
November 2026:

- **No automated reporting or blocking.** Instagram's Terms of Use forbid automating
  actions on the platform, and its official API has no way to report a comment or block
  an account. Professional accounts can hide or delete comments on their own posts through
  the API, but that doesn't report the person who wrote the comment.
- **No automated scanning.** The same terms forbid software from scrolling through
  comments and reading them. On a post with hundreds or thousands of comments, someone
  has to scroll through and read every one by hand to find the abusive ones.
- **Blocking closes the post.** After you block one offender, Instagram closes the post.
  You have to reopen it and search the comments from the top again to find the next one,
  once for every offender.
- **One report at a time.** Each report means stepping through several screens to pick a
  reason. The bulk "Manage" comments tool can delete comments or block their authors in
  groups, but it can't report them, so Instagram is never told about the abuse.

### How Social Sanitizer works within these limits

You stay in control: you scroll the post and you file each report or block yourself.
Social Sanitizer only reads comments already loaded on your screen. It never clicks,
reports or blocks anything on Instagram for you. A small AI model runs on your own
computer to flag likely abusive comments and outline them on the page. One click jumps
straight to each one, so after the post closes you can pick up where you left off
instead of reading the whole thread again.

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

### macOS launcher

To get a double-clickable app with no Terminal window, build the launcher after
setting up the venv:

```bash
scripts/make-mac-launcher.sh
```

This creates `~/Applications/Social Sanitizer.app`. To build it somewhere else, pass a
folder, for example `scripts/make-mac-launcher.sh /Applications`. Open the app from Launchpad,
Spotlight or Finder, or drag it to the Dock. It shows up as "Social Sanitizer" with its
own icon. Output goes to `~/Library/Logs/Social Sanitizer/app.log`. The launcher points
at this checkout, so re-run the script if you move the repository.

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
