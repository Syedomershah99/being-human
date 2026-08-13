---
name: being-human
description: Write in the user's own voice instead of generic assistant prose. Use whenever drafting anything the user will publish or send under their own name -- posts, emails, replies, docs, commit messages, bios, cover letters -- or when they say their writing sounds like AI, sounds generic, or ask to make something sound human, sound like them, or match their voice.
---

# being-human

Generic AI prose is not a style. It's the absence of one. It happens because a
model with no information about who is speaking falls back to the average of
everyone, and the average of everyone reads like a press release.

The fix is information. This skill supplies it: a **voiceprint** measured from
the user's own writing, and a **slop filter** built by contrast.

## the loop

**Learn.** Harvest their writing into a corpus, measure it, write a voiceprint.
Once. Then it improves on its own as they keep typing.

**Write.** Draft with the voiceprint loaded, not from your defaults.

**Check, twice.** Two different failures, two different tests:

- `slopscore.py` asks *is this generic AI writing?* -- tells, rhythm, structure.
- `verify.py` asks *is this THIS PERSON?* -- authorship distance against a null
  resampled from their own writing.

A draft has to pass both, because passing one says nothing about the other. Clean
well-written prose by an obviously different hand scores 97/100 on slop and 94th
percentile on authorship. Generic slop can score 0/100 on tells while sitting at
the 19th percentile on authorship, because its grammar is unremarkable and what
betrays it is vocabulary and structure.

**Revise.** Fix what they flagged. Run both again. Repeat until both pass.

Do not skip these. You are a poor judge of your own slop -- it reads fluent to
you because fluent is what you optimized for. The detectors don't care how it
reads.

## running it

Setup, once:

```bash
python3 scripts/harvest.py --source claude-history --out .being-human/
python3 scripts/harvest.py --source claude-projects --out .being-human/ --append --contrast
python3 scripts/analyze.py --in .being-human/ --name "Their Name"
```

`--contrast` is what makes the slop list personal. It collects the model's own
replies alongside the user's messages, then scores every word by log-odds. Words
the user reaches for and the model doesn't are their voice. Words the model
leans on and they never use are the slop -- measured against *this* person, not
a list someone published on the internet.

Then, on any draft:

```bash
python3 scripts/slopscore.py draft.md --in .being-human/   # AI tells
python3 scripts/verify.py   draft.md --in .being-human/   # is it them?
```

Slop score: above 85 reads human, below 50 is slop, between is a draft with
tells.

Authorship percentile: under 75 is indistinguishable from their writing, over 97
means it reads as someone else. The percentile is against a null resampled from
their own corpus at the same length, so a 60th percentile means *more typical of
them than 40% of what they actually wrote*. `verify.py` also names the specific
words that pushed a draft out of range, which is usually the fastest way to fix
it.

Before you write, read `.being-human/voiceprint.md`. If it doesn't exist, run the
setup. If the user has no usable history, fall back to **interview mode** below.

## how to actually write in voice

The voiceprint gives you casing, punctuation, rhythm, and vocabulary. Those are
necessary and not sufficient. What follows is the part that isn't measurable.

**Rhythm is the loudest tell.** Not word choice. Models write sentences of
remarkably even length because each one is generated under the same pressure.
People don't. They run long when they're working something out, then stop short.
A four-word sentence after a thirty-word one does more for believability than
any vocabulary swap. Check the burstiness ratio in the voiceprint and actually
hit it.

**Cut the scaffolding.** Models open by restating the question and close by
summarizing what they just said. People start in the middle and stop when
they're done. Delete your first sentence and your last one, then see if anything
was lost. Usually nothing was.

**Specifics, not categories.** "Significant performance improvements" is what
you write when you don't know the number. "Went from 40 seconds to 4" is what
someone writes when they were there. If you don't have the specific, say you
don't have it -- don't paper over it with an adjective.

**Commit to the claim.** The instinct to balance every statement with its
counter-statement is a model habit, not a thinking habit. If the user's hedge
rate is low, one clear assertion beats a hedged one every time.

**Break the triad.** Three parallel items is the most seductive shape in
generated text and it almost never occurs naturally three times in a row. Use
two. Use four. Let one item be a different length than the others.

**No "not just X, but Y".** It's the single most recognizable construction in AI
writing. Say Y. If X mattered you'd have led with it.

**Use their words.** The voiceprint has a list of words the user actually
reaches for. Prefer them. And check the avoid list -- those words tested as
model tics against this specific person, which is stronger evidence than any
general rule.

**Match the register.** Most voiceprints detect more than one. A three-line
Slack reply and a considered email are different modes of the same person. Look
at which one the situation calls for and match that, not the average of both.

## reading the two scores together

|  | slop score high | slop score low |
| --- | --- | --- |
| **authorship in range** | ship it | their grammar, robot vocabulary -- cut the tells |
| **authorship out of range** | clean, well-written, not them -- rework toward their habits | start over |

The bottom-left cell is the one that matters and the one no eyeballing catches.
Prose can be genuinely good, free of every listed tell, and still obviously not
the person whose name goes on it.

## the honesty line

This changes how something is said. It never changes whether it's true.

Do not invent an anecdote because the voice would carry one well. Do not add a
number you don't have because specifics score better. Do not claim an experience
the user didn't describe. If the voice wants a concrete detail and you don't
have one, ask for it or leave the sentence plain.

A convincing voice attached to a fabricated fact is worse than generic prose,
because it will be believed.

If the user asks for writing that impersonates someone else in a way meant to
deceive, don't. Writing in your own voice is the point. Writing in someone
else's, to pass as them, is a different thing.

## interview mode

No corpus, or under ~3,000 words? Measurement won't be stable. Ask instead, and
keep it to a handful of questions -- this should feel like a conversation, not
a form:

1. Paste three things you've written that sound like you. Anything -- a Slack
   message, an email, a comment you left somewhere.
2. What words do people say you overuse?
3. What phrasing makes you cringe when you see it in your own drafts?
4. When you're writing fast and not editing, what do you sound like?
5. Who are you usually writing for?

Write those into `.being-human/voiceprint.md` under `## notes`. That section survives
every re-run of `analyze.py` -- everything above it gets regenerated, the notes
stay. As real history accumulates, the measured sections fill in around them.

## when the user corrects you

A correction is the highest-value signal available, worth more than a hundred
harvested prompts, because it's labeled. They're telling you exactly what was
wrong.

When they rewrite something you drafted, or say "too formal", "too long", "i
wouldn't say that" -- don't just fix that draft. Compare their version to yours,
find the specific habit behind the change, and append it to `## notes` in the
voiceprint as a rule. Next time it's already loaded.

Watch for the difference between "this is wrong" and "this isn't me". The second
one is voiceprint material. The first one isn't.

## portability

The voiceprint is plain markdown and the scripts are stdlib Python. Nothing here
is specific to one assistant.

```bash
python3 scripts/export.py --in .being-human/ --target chatgpt   # 1500-char box
python3 scripts/export.py --in .being-human/ --target agents --out AGENTS.md
python3 scripts/export.py --in .being-human/ --target cursor --out .cursorrules
python3 scripts/export.py --in .being-human/ --target system    # raw system prompt
python3 scripts/export.py --in .being-human/ --target json      # build your own
```

Each target fills its character budget in priority order and stops, so the
smallest box still gets the most distinctive habits rather than an arbitrary
prefix.

## reference

- `references/writing-in-voice.md` -- the craft notes, at length
- `references/portability.md` -- using this outside Claude Code
- `data/slop-lexicon.json` -- the tell list, editable, PRs welcome
