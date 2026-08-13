# writing in voice

The long version. `SKILL.md` has the working summary; this is the reasoning
behind it and the cases that need more than a line.

## why generic prose happens

A model writing without information about the speaker produces the conditional
mean of its training distribution. That output isn't neutral — it's the specific
register that dominates instructional and promotional text on the internet.
Confident, balanced, evenly paced, mildly enthusiastic, structurally symmetrical.

It reads like a press release because a great deal of it was.

So "sound more human" is not a useful instruction. There is no general human
register to aim at. There is only *some particular person's* register, and the
model doesn't have one unless you give it one. Every fix that doesn't supply
information about a specific person is cosmetic.

This is also why "be more casual" fails. It moves along one axis of the same
average. The output is still nobody, just nobody in a t-shirt.

## the hierarchy of tells

Ordered by how much they give away, most to least. Fix from the top.

**1. Rhythm.** Sentence length variance. Generated prose clusters tightly around
its mean because every sentence is produced under identical constraints. Human
prose has high variance, driven by thought: a long clause while working an idea
out, then a short one landing it.

The measurable version is the ratio of standard deviation to mean sentence
length. Under 0.45 reads mechanical almost regardless of content. Most people
sit between 0.6 and 0.9. The voiceprint records the user's actual figure.

This is first because it survives every other edit. You can replace every
flagged word and still be caught by the metronome underneath.

**2. Structural symmetry.** Paragraphs of equal length. Bullets of equal length.
Every section with the same number of sub-points. Every paragraph opening with
the same grammatical shape. Real writing is lumpy — one paragraph runs six
sentences because there was more to say, the next is one line.

**3. Scaffolding.** The restated premise at the start, the summary at the end,
the transitional sentence announcing what comes next. These are artifacts of
generating text without knowing where it's going. A writer who already knows
starts at the point.

Test: delete the first and last sentence of any section. If nothing is lost,
they were scaffolding.

**4. Abstraction where a specific belongs.** "Significant improvements",
"various stakeholders", "a range of factors". These are what gets written when
the specific isn't available. They read as evasion even when nothing is being
evaded.

**5. Compulsive balance.** Every claim paired with its qualification. Sometimes
appropriate, but as a reflex it reads as having no position. People writing
about their own work have positions.

**6. Vocabulary.** The famous ones — delve, tapestry, testament, navigate the
complexities. Last on the list, not first, because they're the easiest to
find-and-replace and the least load-bearing. Fixing only these produces text
that is still obviously generated, just without the word "delve".

## constructions worth naming

**"It's not just X, but Y."** The most recognizable sentence shape in AI
writing. It performs insight without adding any: X is introduced solely to be
dismissed. Say Y.

**"It isn't X. It's Y."** The two-sentence version. Same problem, more drama.

**The rule of three.** Three parallel items, endlessly. Occasionally three
things really are the count. Usually the third exists because the rhythm wanted
it. Cut to two and see if anything was lost.

**The one-word question.** "The result?" "The problem?" A setup with no content,
borrowed from ad copy.

**Escalating one-line paragraphs.** LinkedIn broetry. Each line its own
paragraph, building to a reveal. Instantly recognizable, and it now reads as
generated even when a human wrote it.

**The closing question.** "What are your thoughts?" "Agree?" Engagement bait
that signals the writer had nothing further to say. If a question belongs at the
end, it should be one only this person would ask.

## em dashes

Worth separating from the rest, because the discourse around it has gotten
confused.

Em dashes are not inherently AI. Plenty of people use them heavily and always
have. What's diagnostic is *deviation from the writer's own baseline*: if
someone's corpus shows 0.3 per thousand words and a draft comes back at 6, the
draft isn't theirs — regardless of whether any individual dash is defensible.

This is why the detector compares against the measured personal rate rather than
a fixed threshold. A universal "no em dashes" rule is wrong for the people who
genuinely use them, and it's the reason so many humans now get accused of
generating their own writing.

The same logic applies to exclamation marks, emoji, and bullet density. Personal
baseline, not global rule.

## register

Nobody has one voice. The same person writes differently in a Slack reply, a
performance review, a text to a friend, and a cover letter — and all four are
authentically them.

`analyze.py` splits the corpus at 25 words and reports two registers: quick and
considered. It's a crude cut, and it works, because message length correlates
strongly with how much editing happened. Short messages are unedited and show
the most idiosyncrasy. Long ones are composed and show the writer's formal mode.

Match the register the situation calls for. Don't average them — the average is
a person who exists in no context.

If a user needs finer control (a LinkedIn voice distinct from an email voice),
harvest into separate directories and keep separate voiceprints:

```bash
python3 scripts/harvest.py --source files --path ~/writing/posts --out .being-human/linkedin/
python3 scripts/analyze.py --in .being-human/linkedin/ --name "Name (linkedin)"
```

## what measurement can't reach

The voiceprint captures form. It cannot capture what someone finds funny, what
they refuse to say, what they're insecure about, which of their own opinions
they'd defend and which they'd drop. Those live in `## notes`, hand-written,
preserved across regeneration.

The notes section usually ends up mattering more than the numbers. It's worth
telling the user that, and prompting them to fill it in when a correction
reveals something the metrics missed.

## the failure mode to avoid

Over-fitting to tics. If someone types fast and drops apostrophes in their
prompts, that is not a license to write their conference talk without
apostrophes. Prompt-writing is a low-stakes register; publishing is not.

The rule: carry over rhythm, vocabulary, stance, and structure. Be cautious
about carrying over artifacts of typing speed — dropped punctuation, typos,
missing capitalization at the start of a hurried message.

Casing is the judgment call. Someone who writes lowercase "i" in every context,
including deliberate published writing, means it. Someone who does it only when
typing fast doesn't. When the corpus is all prompts, ask before carrying
lowercase into something they'll publish under their name.
