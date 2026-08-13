---
description: Draft something in the user's voice, then verify it before handing it over
argument-hint: "<what to write>"
allowed-tools: Bash, Read, Write, Edit
---

Write this in their voice: $ARGUMENTS

**Load first.** Read `.being-human/voiceprint.md` before drafting anything. If it
doesn't exist, run `/being-human:learn` first — don't draft from your defaults and
call it their voice.

Pay attention to `## notes` as much as the measured sections. The numbers give
you form; the notes give you what they'd actually say.

**Pick the register.** Most voiceprints have two. A quick reply and a considered
piece are different modes of the same person. Match the one this situation calls
for rather than the average.

**Draft.** Hit the burstiness ratio deliberately — it's the strongest single
tell and the easiest to miss, because even prose reads fine to you. Use their
vocabulary. Avoid the words on the personal avoid list.

**Score it before showing it:**

```bash
python3 scripts/slopscore.py <draft> --in .being-human/
```

**Revise and re-score** until it clears 85, or until what's left is a deliberate
choice you can defend. Then show them the draft and the score together.

Do not hand over an unscored draft. The whole point is that self-assessment
doesn't work here — generated prose reads fluent to the thing that generated it.

## the line

Match the voice. Never bend a fact to fit it.

Don't invent an anecdote because the voice would carry one. Don't add a number
you don't have because specifics score better than abstractions. Don't claim an
experience they haven't described to you.

When the voice wants a concrete detail and you don't have one, ask for it. A
convincing voice wrapped around a fabricated fact is worse than generic prose,
because generic prose doesn't get believed.
