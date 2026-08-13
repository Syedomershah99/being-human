---
description: Compile the voiceprint for ChatGPT, Cursor, AGENTS.md, or a raw system prompt
argument-hint: "[chatgpt | claude | agents | cursor | system | json]"
allowed-tools: Bash, Read, Write, Edit
---

Export the voiceprint for: $ARGUMENTS

```bash
python3 scripts/export.py --in .being-human/ --target <target>
```

Targets:

| target | goes where |
| --- | --- |
| `chatgpt` | Settings → Personalization → Custom instructions (~1500 char budget) |
| `claude` | a block in `CLAUDE.md` |
| `agents` | a block in `AGENTS.md` — Cursor, Codex, Copilot, Zed, Aider |
| `cursor` | `.cursorrules` |
| `system` | raw system prompt for API calls |
| `json` | machine-readable, for building on |

Use `--out <file>` to write directly, and `--append` if the file already has
content you don't want replaced.

If they didn't name a target, ask which tool they're setting up rather than
guessing — the containers differ enough that the wrong one is just noise in
their config.

For `chatgpt`, print the output in a code block so they can copy it cleanly, and
mention the character count against the budget. The export fills the budget in
priority order and stops, so if it's near the ceiling some lower-priority rules
were dropped. That's by design, but worth saying out loud.
