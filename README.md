# being-human

**Your assistant writes like a press release because it doesn't know who you
are. This tells it.**

being-human reads the prompts you've already typed, measures how you actually write,
and hands the model a description of your voice specific enough to follow.

It also builds a list of words to avoid. That list is computed by contrast
against the model's own output, so it's personal to you rather than borrowed
from a blog post about ChatGPT tells.

Runs locally. Stdlib Python 3, no dependencies, no network calls. Works with
Claude, ChatGPT, Cursor, Gemini, or anything that accepts a system prompt.

---

## the problem

"Sound more human" doesn't work. It can't, because there's no general human
register to aim at. A model writing with no information about the speaker
produces the average of everything it read, and that average is confident,
evenly paced, structurally symmetrical, and mildly enthusiastic. It reads like
marketing copy because a lot of it was.

"Be more casual" fails the same way. It moves along one axis of the same
average. The output is still nobody, just nobody in a t-shirt.

The only fix is information about a specific person. You've been generating that
information every time you type a prompt.

## what it does

Two halves that need each other.

**The voiceprint.** A measured description of how you write. Sentence rhythm,
casing, punctuation rates, contractions, hedging, how you open, which words you
reach for. Generated from your own writing, not from your description of your
writing. People are unreliable narrators of their own style.

**The slop filter.** A detector that scores a draft against your baseline and
points at the tells, line by line.

## quickstart

```bash
git clone https://github.com/Syedomershah99/being-human && cd being-human

# 1. harvest what you've already written
python3 scripts/harvest.py --source claude-history --out .being-human/
python3 scripts/harvest.py --source claude-projects --out .being-human/ --append --contrast

# 2. measure it
python3 scripts/analyze.py --in .being-human/ --name "Your Name"

# 3. score a draft
python3 scripts/slopscore.py draft.md --in .being-human/
```

No Claude Code history? Point it at anything you've written:

```bash
python3 scripts/harvest.py --source chatgpt --path conversations.json --out .being-human/ --contrast
python3 scripts/harvest.py --source files --path ~/Documents/writing --out .being-human/
```

## what comes out

From my own history, 1,187 messages and 42,477 words:

```
## do

- Write "i" lowercase. They do, 83% of the time.
- Start sentences lowercase. 71% of theirs do. Don't tidy this up.
- Vary sentence length hard. Theirs average 9 words but deviate 8 (ratio 0.89),
  running as long as 81. Put a three-word sentence next to a thirty-word one.
- Their shorthand is fair game: yep, kinda, u, nope, okay, tbh.

## don't

- No exclamation marks. Rate is 0.28 per 1k.
- Don't hedge. Hedge rate is 1.1 per 1k -- they assert.
- Prose, not bullets. Only 1% of their writing uses lists.
```

Instructions with numbers attached, because "be concise" is not actionable and
"your median message is 12 words" is.

## the contrast trick

This is the part I think is actually new.

Your transcripts contain both sides of every conversation. So you can score
every word by log-odds. How much more likely you are to use it than the model
is, measured on the same conversations, about the same topics.

The top of that list is your voice. The bottom is the model's.

Mine came back:

```
never use: actually, clean, both, rather, genuinely, likely, exactly,
           roughly, whole, almost, either, regardless, better, already
```

Not one of those is on any published list of AI words. They're the specific tics
this model has when talking to me. Yours will be different, because the contrast
is against your writing, not against an average.

Two filters make it work. Stylometry says voice lives in function words rather
than content words, because function words don't depend on the topic. So the
contrast runs over stance and discourse markers, not nouns. And a word has to
appear across several separate projects to count as vocabulary; otherwise
`fwhm` showing up 200 times in one repo reads as a personality trait instead of
a subject.

## the impostor test

Every tool in this space builds a profile and then asks you to eyeball whether
the output sounds right. Eyeballing is the one judgment guaranteed to fail here:
a draft reads fine to whoever just read the instructions that produced it.

So there's a second, falsifiable check. Among things you actually wrote, at this
length, how unusual is this text?

```
$ python3 scripts/verify.py draft.md --in .being-human/

  delta 0.89   90th percentile   within your range
  1193 words, against 400 same-length samples of you (median 0.71, p97 1.31)

  what pushed it out:
    it            +3.3 sd  over   draft   20.7/1k   you    6.3/1k
    of            +3.1 sd  over   draft   23.9/1k   you    8.6/1k
```

The distance is Burrows's Delta, the standard authorship-attribution measure.
The part that took work is the reference distribution. Delta has no absolute
scale and is strongly length-dependent, so the null is resampled: for a draft of
N words, draw 400 N-word windows from your own corpus and score the draft
against that distribution. Length is matched by construction.

Getting this wrong inverts the result, which I found out by building it wrong
first. Scored naively against a corpus of uneven short messages, per-word
variance is inflated, every z-score shrinks, and bland average-English prose
lands *closer* to your centroid than your own writing does. Slop wins. The
resampled null fixes it: held-out chunks of real writing now sit at the 49th–60th
percentile, where they should, with a 1–6% false-positive rate above p97.

## two axes, not one

The two checks catch different failures, and passing one says nothing about the
other:

| | |
| --- | --- |
| **`slopscore.py`** | is this generic AI writing? tells, rhythm, structure |
| **`verify.py`** | is this *you*? authorship distance on function words |

Measured on my own corpus:

| | authorship | slop |
| --- | --- | --- |
| my own writing | 6th pct — me | 99/100 |
| a post drafted in my voice | 76th pct — me | 100/100 |
| generic LinkedIn slop | 19th pct — *me?* | 0/100 |
| this README (different person) | 94th pct — not me | 97/100 |

Look at row three. The slop's grammar is unremarkable, so authorship distance
passes it — what gives it away is vocabulary and structure. And row four is clean
prose with no tells that is plainly a different hand.

The bottom row is the case nobody else tests for, and it's the one that actually
bites: writing that is good, passes every slop filter, and still isn't yours.

## scoring

```
$ python3 scripts/slopscore.py post.md --in .being-human/

  0/100   slop
  115 words, 32 tells

  --    sentences are too uniform (ratio 0.46, yours is 0.89)  break one sentence in half
  L3    In today's fast-paced world                            delete the whole clause
  L5    the "not just X, but Y" construction                   pick one. say the Y.
  L7    delve                                                  dig into, look at, get into
  --    9 of 11 paragraphs are a single line                   merge some into real paragraphs
  --    emoji at 38.1 per 1k (yours: 0.4)                      remove them
```

The structural checks matter more than the word list. A draft can contain zero
flagged phrases and still be obviously generated, because every sentence is the
same length. Rhythm survives find-and-replace. Vocabulary doesn't.

Thresholds come from your measured habits, not a global rule. If you genuinely
use em dashes at 6 per thousand words, it won't flag them. It flags the draft
that comes back at 6 when you write at 0.3. That distinction matters. It's why
so many people now get accused of generating their own writing.

Same file, my actual prompts as a control: **99/100**.

## any llm

```bash
python3 scripts/export.py --target chatgpt              # 1500-char box
python3 scripts/export.py --target agents --out AGENTS.md   # Cursor, Codex, Copilot, Zed
python3 scripts/export.py --target cursor --out .cursorrules
python3 scripts/export.py --target system               # raw system prompt
python3 scripts/export.py --target json                 # build your own
```

Each target fills its character budget in priority order and stops, so a small
box gets your most distinctive habits rather than an arbitrary prefix.

## mcp server

For everything that isn't Claude Code. One file, stdlib only, no SDK and no
`pip install` — it speaks JSON-RPC over stdio directly.

```bash
claude mcp add being-human -- python3 /path/to/being-human/mcp/server.py
```

Claude Desktop, Cursor, Codex, and Zed configs are in [mcp/README.md](mcp/README.md).

Six tools (`voice_get`, `voice_score`, `voice_status`, `voice_learn`,
`voice_note`, `voice_export`), two resources, two prompts.

One thing worth knowing about MCP: tools are model-invoked, and nothing forces a
model to call one. That's awkward for a tool whose payload is *instructional* —
the voice rules need to be in context before drafting, not available on request
afterwards. So every tool here returns the rules alongside its actual result.
Call the scorer, get the rules. Check status, get the rules. There's no path
through the server that hands back a score without the target attached.

It's local stdio and single-user by design. The corpus is your raw prompt
history, so hosting it would mean uploading the exact thing this is meant to
keep on your machine.

## claude code plugin

```
/plugin marketplace add Syedomershah99/being-human
/plugin install being-human
```

Adds `/being-human:learn`, `/being-human:check`, `/being-human:write`, `/being-human:export`, and a
`UserPromptSubmit` hook that appends each prompt to the corpus as you work. The
voiceprint sharpens on its own; re-run `analyze.py` to fold in what's new.

The hook is deliberately boring. It never prints, never blocks, and exits 0 on
every failure path. A voice tool has no business standing between you and your
prompt.

The plugin is a wrapper. The scripts are the product, and they don't need it.

## privacy

Everything is local. Grep for `urllib`, `requests`, or `socket` and you'll find
nothing.

Secrets are redacted at harvest time, before anything touches disk: emails, API
keys and tokens, phone numbers, home directory paths, long hex strings.
`.being-human/` is gitignored by default.

The voiceprint is aggregate statistics and a rule list, safe to share. The
corpus it was built from is not. It reconstructs a real portion of your prompt
history. Keep it local.

## limits

Under about 3,000 words the numbers are noisy. Sentence-length variance in
particular needs volume before it settles. There's an interview mode for cold
starts.

A corpus of prompts is a corpus of one register. Prompts are typed fast and
unedited, so they overstate how loose you are in writing you'd actually publish.
Rhythm, vocabulary, and stance carry over well. Dropped punctuation and
lowercase starts are judgment calls, and `references/writing-in-voice.md`
covers where to draw that line.

It matches voice, not facts. Nothing here should be used to invent an anecdote,
add a number you don't have, or write as someone else in order to pass as them.
The skill file says this too, in the place the model will read it.

## how it works

| step | what happens |
| --- | --- |
| `harvest.py` | pulls your writing from history, transcripts, exports, or files. strips harness tags, code fences, shell pastes, and pasted blobs. redacts secrets. dedupes. |
| `analyze.py` | measures rhythm, casing, punctuation, hedging, registers. runs the log-odds contrast. writes `voiceprint.md` and `metrics.json`. |
| `slopscore.py` | lexical pass over `data/slop-lexicon.json` plus structural checks against your baseline. |
| `export.py` | compiles the voiceprint into whatever container your tool reads, under its budget. |

`## notes` in the voiceprint is hand-written and survives every regeneration.
That's where the things measurement can't reach go. What you refuse to say, who
you're writing for, words you've banned. In practice it ends up mattering more
than the numbers.

## prior art

This space got crowded in 2026 and pretending otherwise would be silly.

[`inside-lago-voice-skill`](https://github.com/getlago/inside-lago-voice-skill)
(314★) framed the thesis. [`slop-guard`](https://github.com/eric-tramel/slop-guard)
(160★) is a mature slop linter with its own MCP server.
[`idiolect`](https://github.com/nagisanzenin/idiolect) is architecturally
closest — stdlib engine, line-anchored tell lexicon, and a hook harvesting your
own prompts. [`write-like-me`](https://github.com/Hiro-Inagawa/write-like-me)
does measured profiles with multiple named voices.
[`writer-persona`](https://github.com/cosmos-makers/writer-persona) had the best
idea of the lot: a backtest that drafts from context only, never seeing your real
reply, and scores against your natural range rather than against perfection.

Two things here that I could not find elsewhere:

**The user-vs-model contrast.** Deriving your avoid-list from log-odds between
your words and the model's words in the same transcripts. Others ship curated
tell lists, including era-tagged ones; none compute the list per-user from your
own conversations.

**A deterministic impostor test.** writer-persona validates with an LLM judge
across 8 axes. This is arithmetic — no model, no cost, same answer every time,
and it reports a calibrated percentile with a stated false-positive rate.

Also: thresholds here are personal. `write-like-me` ships a universal baseline;
this flags em dashes relative to *your* measured rate, which is why it doesn't
punish people who genuinely use them.

Burrows's Delta (1) and log-odds with a Dirichlet prior (2) are both established
methods. The claim is the application and the calibration, not the statistics.

1. Burrows, "Delta: a Measure of Stylistic Difference", 2002.
2. Monroe, Colaresi & Quinn, "Fightin' Words", 2008.

## contributing

The tell list is `data/slop-lexicon.json`. If you keep seeing something that
isn't in there, add it. Pattern, severity 1-5, and a plain replacement.

The structural checks in `slopscore.py` are where the real signal is and where
the most room is left. Bullet parallelism, hedge stacking, and paragraph shape
are in. Passive-voice density, sentence-opener repetition, and clause-depth
uniformity aren't yet.

## license

MIT.

---

*written by being-human*
