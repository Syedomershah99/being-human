---
description: Score a draft for AI tells against the user's own voiceprint
argument-hint: "<file, or paste the text>"
allowed-tools: Bash, Read, Write, Edit
---

Score this for AI tells: $ARGUMENTS

If it's a file path:

```bash
python3 scripts/slopscore.py "$ARGUMENTS" --in .being-human/
```

If they pasted text instead, write it to a scratch file first and score that.

Then work through the output with them:

- Lead with the score and what it means. Above 85 reads human, below 50 is slop,
  in between is a draft with tells.
- Take the structural findings first — rhythm, paragraph shape, bullet symmetry.
  Those matter more than any single word, and fixing them changes how the whole
  piece reads. A draft can have zero flagged phrases and still be obviously
  generated because every sentence is the same length.
- Then the phrase-level hits, grouped rather than listed one by one.
- If `.being-human/metrics.json` is missing, the thresholds were generic. Say so —
  the em dash and exclamation checks are only meaningful against their measured
  baseline, and a generic run will flag people who legitimately use both.

Offer to fix it rather than just reporting. If they say yes, rewrite and score
again — don't hand back an unverified revision.

One thing to hold to: fix the writing, not the score. Swapping flagged words for
unflagged synonyms raises the number without making the text any more theirs.
If a passage is generic because it has nothing specific in it, the fix is a
specific detail, and if you don't have one, ask.
