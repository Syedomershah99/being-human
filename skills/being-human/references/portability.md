# using being-human outside Claude Code

Nothing in the core is Claude-specific. The voiceprint is markdown, the scripts
are stdlib Python 3, and the output is text. The Claude Code plugin is a
convenience wrapper, not the product.

## the general shape

1. Get your writing into `corpus.jsonl` — one JSON object per line, `{"text": "..."}`.
2. Run `analyze.py` to produce `voiceprint.md` and `metrics.json`.
3. Run `export.py --target <tool>` to get it into whatever container that tool reads.
4. Run `slopscore.py` on drafts.

Step 1 is the only part that varies by platform.

## ChatGPT

Export your data (Settings → Data controls → Export), unzip, then:

```bash
python3 scripts/harvest.py --source chatgpt --path conversations.json --out .being-human/ --contrast
python3 scripts/analyze.py --in .being-human/
python3 scripts/export.py --in .being-human/ --target chatgpt
```

Paste the output into Settings → Personalization → Custom instructions. The
export is budgeted to ~1500 characters and fills that budget in priority order,
so the most distinctive habits survive the cut.

`--contrast` works here too — the export contains the assistant's replies, so
the personal slop list can be computed the same way.

## Cursor, Codex, Copilot, Zed, Aider, Windsurf

These read a rules file from the repo root.

```bash
python3 scripts/export.py --in .being-human/ --target agents --out AGENTS.md
python3 scripts/export.py --in .being-human/ --target cursor --out .cursorrules
```

Use `--append` to add the voice block to a file that already has content.

Note that these apply to *prose* the agent writes — commit messages, PR
descriptions, docs, comments, replies to you. Not to code. The export says so
explicitly, because otherwise you get variable names in your voice, which nobody
wants.

## Gemini, Llama, Mistral, or any API

```bash
python3 scripts/export.py --in .being-human/ --target system
```

Prepend to your system prompt. It's under 6000 characters by default; pass
`--budget N` to fit a tighter context.

```python
import subprocess
voice = subprocess.run(
    ["python3", "scripts/export.py", "--in", ".being-human/", "--target", "system"],
    capture_output=True, text=True).stdout

messages = [{"role": "system", "content": voice + "\n\n" + your_task_prompt}]
```

## building on it directly

```bash
python3 scripts/export.py --in .being-human/ --target json
```

Gives you the rules as a list plus the full metrics object. `metrics.json` in
the output directory has everything: per-register measurements, the log-odds
tables with z-scores and raw counts, openers, bigrams.

`slopscore.py --json` returns structured findings with line numbers, weights,
and suggested fixes — usable as a CI check or a pre-commit hook:

```bash
python3 scripts/slopscore.py README.md --fail-under 70
```

Exits non-zero below the threshold.

## no history at all

If you're starting cold, point `harvest.py` at anything you've written:

```bash
python3 scripts/harvest.py --source files --path ~/Documents/writing --out .being-human/
cat some_draft.md | python3 scripts/harvest.py --source stdin --out .being-human/ --append
```

Below about 3,000 words the measurements are noisy — sentence-length variance in
particular needs volume before it stabilizes. Use interview mode (see
`SKILL.md`) to bootstrap `## notes` by hand, and let the measured sections fill
in as the corpus grows.

## privacy

Everything runs locally. There are no network calls in any script — grep for
`urllib`, `requests`, or `socket` and you'll find nothing.

Secrets are redacted at harvest time before anything is written to disk: emails,
API keys and tokens, phone numbers, home directory paths, long hex strings.
`--no-redact` disables it, which you shouldn't do if the corpus will ever be
shared.

Add `.being-human/` to `.gitignore`. It's your writing, and the corpus reconstructs a
meaningful portion of your prompt history. The voiceprint itself is safe to
share — it's aggregate statistics and a rule list — but the corpus it was built
from is not.
