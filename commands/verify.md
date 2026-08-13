---
description: The impostor test — is this text statistically a plausible sample of the user?
argument-hint: "<file, or paste the text>"
allowed-tools: Bash, Read, Write, Edit
---

Run the impostor test on: $ARGUMENTS

```bash
python3 scripts/verify.py "$ARGUMENTS" --in .being-human/
```

If they pasted text rather than a path, write it to a scratch file and test that.

This asks a different question from `/being-human:check`. That one looks for AI
tells. This one asks whether the text is a plausible sample of *this person*,
using authorship distance against a null resampled from their own writing at the
same length.

Reading the result:

- **under 75th percentile** — indistinguishable from their writing
- **75–90** — within range
- **90–97** — unusual for them
- **over 97** — reads as a different hand

The percentile is what matters, not the raw delta, which has no absolute scale.
A 60th percentile means the draft is more typical of them than 40% of what they
actually wrote — that's a pass, not a near-miss.

The `what pushed it out` list is the actionable part. It names the exact function
words that are over- or under-used against their baseline, with the rates. Fixing
two or three of those usually moves the percentile more than any amount of
rewriting by feel.

Two things to be straight about:

Both checks are needed. A draft can clear this one and still be full of tells,
because authorship distance keys on function-word distribution and generic prose
often has unremarkable grammar. Run `/being-human:check` too.

And below about 40 words the number is noise — there isn't enough text for word
frequencies to mean anything. Say so rather than reporting a percentile as if it
were solid.
