# being-human

**Your assistant writes like a press release because it doesn't know who you
are. This tells it.**

being-human reads the prompts you've already typed, measures how you actually
write, and hands the model a description of your voice specific enough to
follow. It also builds a list of words to avoid, computed by contrast against
the model's own output, so it's personal to you rather than borrowed from a blog
post about ChatGPT tells.

Local, stdlib Python 3, no dependencies, no network calls.

<p align="center">
  <a href="demo/being-human-demo.mp4">
    <img src="demo/being-human-demo.gif" alt="being-human demo" width="480" height="480">
  </a>
</p>

---

## quickstart

```bash
pip install being-human

being-human learn --name "Your Name"     # harvest your writing, measure it
being-human check draft.md               # AI tells
being-human verify draft.md              # is it statistically you?
being-human export --target chatgpt      # or agents, cursor, system, json
```

No Claude Code history? Point it at a ChatGPT export or your own files:

```bash
being-human harvest --source chatgpt --path conversations.json --out .being-human/ --contrast
being-human harvest --source files --path ~/Documents/writing --out .being-human/
```

## what comes out

Instructions with numbers attached, because "be concise" is not actionable and
"your median message is 12 words" is:

```
- Write "i" lowercase. They do, 83% of the time.
- Vary sentence length hard. Theirs average 9 words but deviate 8, up to 81.
- No exclamation marks. Rate is 0.28 per 1k.
- Don't hedge. Hedge rate is 1.1 per 1k -- they assert.
```

## the contrast trick

Your transcripts contain both sides of every conversation. So every word can be
scored by log-odds: how much more likely you are to use it than the model is, on
the same topics, in the same threads. The top of that list is your voice. The
bottom is the model's.

Mine came back `actually, clean, rather, genuinely, exactly, roughly`. None of
those appear on any published list of AI words. They're the specific tics this
model has when talking to me. Yours will differ, because the contrast is against
your writing.

## two checks, not one

They catch different failures, and passing one says nothing about the other:

| | |
| --- | --- |
| `check` | is this generic AI writing? tells, rhythm, structure |
| `verify` | is this *you*? authorship distance, Burrows's Delta against a length-matched null resampled from your own corpus |

Measured on my own corpus:

| | authorship | slop |
| --- | --- | --- |
| my own writing | 6th pct, me | 99/100 |
| generic LinkedIn slop | 19th pct, *me?* | 0/100 |
| a README by someone else | 94th pct, not me | 97/100 |

Row two is the catch: slop has unremarkable grammar, so authorship distance
passes it. Row three is clean prose with no tells that is plainly a different
hand. The second case is the one nobody else tests for, and it's the one that
bites.

Held-out chunks of real writing sit at the 49th to 60th percentile, with a 1-6%
false-positive rate above p97. Thresholds are personal. Em dashes get flagged
against *your* measured rate rather than a universal rule, which is why this
doesn't punish people who genuinely use them.

## mcp server

```bash
claude mcp add being-human -- being-human-mcp
```

Seven tools, two resources, two prompts. Configs for Claude Desktop, Cursor,
Codex and Zed are in [mcp/README.md](mcp/README.md).

MCP tools are model-invoked and nothing forces a model to call one, which is
awkward when the payload is instructional. So every tool returns the voice rules
alongside its own result. There's no path through the server that hands back a
score without the target attached.

There's a Claude Code plugin too, via
`/plugin marketplace add Syedomershah99/being-human`. It adds
`/being-human:learn`, `:check`, `:write`, `:verify`, `:export`, and a hook that
grows the corpus as you type.

## privacy

Everything is local. Grep for `urllib`, `requests` or `socket` and you'll find
nothing. Secrets are redacted at harvest time before anything touches disk, and
`.being-human/` is gitignored. The voiceprint is safe to share. The corpus it was
built from is not.

## prior art

This space got crowded in 2026.
[inside-lago](https://github.com/getlago/inside-lago-voice-skill) framed the
thesis, [slop-guard](https://github.com/eric-tramel/slop-guard) is a mature slop
linter, [idiolect](https://github.com/nagisanzenin/idiolect) is architecturally
closest, and [writer-persona](https://github.com/cosmos-makers/writer-persona)
had the best idea of the lot: validate the profile with a backtest instead of
trusting it.

Two things here I couldn't find elsewhere. The user-vs-model contrast, which
derives the avoid-list from both sides of your own transcripts rather than from a
curated list. And a deterministic impostor test. writer-persona uses an LLM judge
across 8 axes; this is arithmetic, so it costs nothing and returns the same
answer every time.

Burrows's Delta and log-odds with a Dirichlet prior are both established methods.
The claim is the application and the calibration, not the statistics.

## license

MIT. The tell list is [data/slop-lexicon.json](data/slop-lexicon.json). If you
keep seeing something that isn't in there, send a PR.

<sub>mcp-name: io.github.Syedomershah99/being-human</sub>
