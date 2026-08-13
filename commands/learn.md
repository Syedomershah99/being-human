---
description: Build or refresh the voiceprint from the user's own writing
argument-hint: "[optional: their name]"
allowed-tools: Bash, Read, Write, Edit
---

Build or refresh the voiceprint.

If `.being-human/corpus.jsonl` does not exist, this is a first run. Do the full setup:

```bash
python3 scripts/harvest.py --source claude-history --out .being-human/
python3 scripts/harvest.py --source claude-projects --out .being-human/ --append --contrast
python3 scripts/analyze.py --in .being-human/ --name "$ARGUMENTS"
```

If it does exist, this is a refresh. Re-harvest with `--append` to pick up
anything new, then re-analyze. The `## notes` section of the existing voiceprint
is preserved automatically — don't recreate it.

Then read `.being-human/voiceprint.md` and report back, in this order:

1. The three or four habits that are most distinctive about how they write.
   Not the full table — the things that would let someone recognize their
   writing in a lineup.
2. What the contrast pass found. Which words the model has been using with them
   that they never use. This tends to be the part people find striking, because
   it's specific to them rather than a list off the internet.
3. Anything the numbers look shaky on. Under ~3,000 words, or a corpus that's
   all short prompts, means the sentence-rhythm figures aren't stable yet. Say
   so rather than presenting them as settled.

Then ask whether anything is missing — words they've banned, people they're
usually writing for, a habit the numbers wouldn't catch. Write what they say
into `## notes` in the voiceprint. That section survives every re-run.

If there's no usable history, don't force it. Switch to interview mode from the
skill and ask them the five questions instead.
